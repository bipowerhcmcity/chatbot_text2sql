"""
Teacher Bot - Main Entry Point
A separate FastAPI application for evaluating the Text-to-SQL chatbot.

Usage:
    1. Start the main chatbot: python main.py (runs on port 8000)
    2. Start the teacher bot: python teacher_bot_app.py (runs on port 8001)
    3. Open http://localhost:8001 in browser
    4. Upload Question List CSV, configure chatbot API URL
    5. Run evaluation and download reports
"""

import os
import sys
import json
import asyncio
import shutil
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pydantic import BaseModel

from teacher_bot.input_processor import InputProcessor
from teacher_bot.evaluator import ChatbotEvaluator, EvaluationResult
from teacher_bot.scoring_engine import ScoringEngine
from teacher_bot.error_analyzer import ErrorAnalyzer
from teacher_bot.report_generator import ReportGenerator

# ─── App setup ───────────────────────────────────────────────────────
app = FastAPI(
    title="Teacher Bot - Chatbot Evaluation Framework",
    description="Automated scoring framework for evaluating Text-to-SQL chatbot performance",
    version="1.0.0",
)

# Mount static files for the teacher bot UI
os.makedirs("teacher_bot/static", exist_ok=True)
os.makedirs("teacher_bot/reports", exist_ok=True)
os.makedirs("teacher_bot/uploads", exist_ok=True)

app.mount("/static", StaticFiles(directory="teacher_bot/static"), name="static")

# ─── In-memory state ─────────────────────────────────────────────────

# Store evaluation jobs
evaluation_jobs: Dict[str, Dict[str, Any]] = {}


# ─── Pydantic Models ─────────────────────────────────────────────────

class EvaluationConfig(BaseModel):
    chatbot_api_url: str = "http://localhost:8000"
    execute_and_compare: bool = True
    use_llm_scoring: bool = True
    use_llm_error_analysis: bool = True
    generate_pdf: bool = False


class SingleQuestionRequest(BaseModel):
    question: str
    expected_sql: str = ""
    chatbot_api_url: str = "http://localhost:8000"


# ─── Routes ──────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the Teacher Bot UI."""
    try:
        with open("teacher_bot/static/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Teacher Bot</h1><p>Frontend files not found. Please check teacher_bot/static/index.html</p>",
            status_code=404,
        )


@app.get("/health")
async def health_check():
    """Health check for Teacher Bot."""
    return {"status": "healthy", "service": "teacher_bot"}


@app.post("/api/check-chatbot")
async def check_chatbot(config: EvaluationConfig):
    """Check if the chatbot API is reachable."""
    evaluator = ChatbotEvaluator(config.chatbot_api_url)
    is_healthy = await evaluator.check_chatbot_health()
    return {
        "url": config.chatbot_api_url,
        "is_healthy": is_healthy,
        "message": "Chatbot API is reachable" if is_healthy else "Cannot reach chatbot API",
    }


@app.post("/api/upload-questions")
async def upload_questions(file: UploadFile = File(...)):
    """Upload a Question List CSV file."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    # Save uploaded file
    upload_id = str(uuid.uuid4())[:8]
    upload_path = f"teacher_bot/uploads/{upload_id}_{file.filename}"
    with open(upload_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Parse and validate
    try:
        processor = InputProcessor()
        df = processor.load_question_list(upload_path)
        questions = processor.get_questions()
        validation = processor.validate_inputs()

        return {
            "upload_id": upload_id,
            "file_path": upload_path,
            "filename": file.filename,
            "total_questions": len(questions),
            "questions": questions,
            "validation": validation,
        }
    except Exception as e:
        # Clean up on error
        if os.path.exists(upload_path):
            os.remove(upload_path)
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/upload-scorer")
async def upload_scorer(file: UploadFile = File(...)):
    """Upload a Scoring Framework CSV file."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    upload_id = str(uuid.uuid4())[:8]
    upload_path = f"teacher_bot/uploads/{upload_id}_{file.filename}"
    with open(upload_path, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        processor = InputProcessor()
        df = processor.load_scorer_framework(upload_path)
        return {
            "upload_id": upload_id,
            "file_path": upload_path,
            "filename": file.filename,
            "rows": len(df),
        }
    except Exception as e:
        if os.path.exists(upload_path):
            os.remove(upload_path)
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/evaluate-single")
async def evaluate_single_question(request: SingleQuestionRequest):
    """Evaluate a single question against the chatbot."""
    evaluator = ChatbotEvaluator(request.chatbot_api_url)

    # Check chatbot health first
    is_healthy = await evaluator.check_chatbot_health()
    if not is_healthy:
        raise HTTPException(
            status_code=503,
            detail=f"Chatbot API not reachable at {request.chatbot_api_url}",
        )

    result = await evaluator.evaluate_single_question(
        question=request.question,
        expected_sql=request.expected_sql,
        execute_and_compare=bool(request.expected_sql),
    )

    # Score the result
    scoring_engine = ScoringEngine(use_llm=True)
    sql_to_score = result.bot_sql or request.expected_sql
    score = scoring_engine.score_question(request.question, sql_to_score)

    # Analyze errors if incorrect
    error_analysis = {"error_group": "None", "error_labels": [], "analysis": ""}
    if result.is_correct is False:
        analyzer = ErrorAnalyzer(use_llm=True)
        error_analysis = analyzer.analyze_error(
            question=request.question,
            expected_sql=request.expected_sql,
            bot_sql=result.bot_sql,
            is_correct=False,
            error_message=result.error_message,
        )

    return {
        "question": result.question,
        "bot_sql": result.bot_sql,
        "bot_raw_response": result.bot_raw_response,
        "expected_sql": request.expected_sql,
        "is_correct": result.is_correct,
        "error_message": result.error_message,
        "elapsed_time": result.elapsed_time,
        "score": score,
        "error_analysis": error_analysis,
    }


async def _run_evaluation_job(
    job_id: str,
    questions: List[Dict[str, str]],
    config: Dict[str, Any],
):
    """Background task to run the full evaluation pipeline."""
    try:
        evaluation_jobs[job_id]["status"] = "running"
        evaluation_jobs[job_id]["started_at"] = datetime.now().isoformat()

        chatbot_url = config.get("chatbot_api_url", "http://localhost:8000")
        evaluator = ChatbotEvaluator(chatbot_url)
        scoring_engine = ScoringEngine(use_llm=config.get("use_llm_scoring", True))
        error_analyzer = ErrorAnalyzer(use_llm=config.get("use_llm_error_analysis", True))
        report_gen = ReportGenerator()

        total = len(questions)

        # Step 1: Evaluate all questions
        def progress_callback(current, total, question):
            evaluation_jobs[job_id]["progress"] = {
                "current": current,
                "total": total,
                "percentage": round(current / total * 100, 1),
                "current_question": question[:80],
            }

        eval_results = await evaluator.evaluate_all_questions(
            questions,
            execute_and_compare=config.get("execute_and_compare", True),
            progress_callback=progress_callback,
        )

        # Step 2: Score each result
        evaluation_jobs[job_id]["status"] = "scoring"
        scored_results = []
        for r in eval_results:
            sql_to_score = r.bot_sql or r.expected_sql
            score = scoring_engine.score_question(r.question, sql_to_score)
            scored_results.append({
                "question": r.question,
                "level": r.level,
                "expected_sql": r.expected_sql,
                "bot_sql": r.bot_sql,
                "bot_raw_response": r.bot_raw_response,
                "is_correct": r.is_correct,
                "error_message": r.error_message,
                "elapsed_time": r.elapsed_time,
                "score": score,
            })

        # Step 3: Error analysis
        evaluation_jobs[job_id]["status"] = "analyzing_errors"
        analyzed_results = error_analyzer.analyze_batch(scored_results)

        # Step 4: Generate reports
        evaluation_jobs[job_id]["status"] = "generating_reports"
        summary = evaluator.get_summary()
        error_dist = error_analyzer.get_error_distribution(analyzed_results)

        # Generate text report
        text_report, text_path = report_gen.generate_text_report(
            analyzed_results, summary, error_dist, chatbot_url
        )

        # Generate JSON report
        json_report, json_path = report_gen.generate_json_report(
            analyzed_results, summary, error_dist, chatbot_url
        )

        # Generate CSV report
        csv_path = report_gen.generate_csv_report(analyzed_results)

        # Always generate PDF report
        pdf_path = report_gen.generate_pdf_report(
            analyzed_results, summary, error_dist, chatbot_url
        )

        # Update job with results
        evaluation_jobs[job_id]["status"] = "completed"
        evaluation_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        evaluation_jobs[job_id]["results"] = analyzed_results
        evaluation_jobs[job_id]["summary"] = summary
        evaluation_jobs[job_id]["error_distribution"] = error_dist
        evaluation_jobs[job_id]["reports"] = {
            "text": text_path,
            "json": json_path,
            "csv": csv_path,
            "pdf": pdf_path,
        }

    except Exception as e:
        evaluation_jobs[job_id]["status"] = "failed"
        evaluation_jobs[job_id]["error"] = str(e)
        print(f"Evaluation job {job_id} failed: {e}")
        import traceback
        traceback.print_exc()


@app.post("/api/evaluate-batch")
async def evaluate_batch(
    background_tasks: BackgroundTasks,
    questions_file: str = Form(...),
    chatbot_api_url: str = Form("http://localhost:8000"),
    execute_and_compare: bool = Form(True),
    use_llm_scoring: bool = Form(True),
    use_llm_error_analysis: bool = Form(True),
    generate_pdf: bool = Form(False),
):
    """Start a batch evaluation job (runs in background)."""
    # Load questions from uploaded file
    try:
        processor = InputProcessor()
        processor.load_question_list(questions_file)
        questions = processor.get_questions()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error loading questions: {str(e)}")

    if not questions:
        raise HTTPException(status_code=400, detail="No questions found in the uploaded file")

    # Create job
    job_id = str(uuid.uuid4())[:8]
    evaluation_jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "total_questions": len(questions),
        "progress": {"current": 0, "total": len(questions), "percentage": 0},
        "config": {
            "chatbot_api_url": chatbot_api_url,
            "execute_and_compare": execute_and_compare,
            "use_llm_scoring": use_llm_scoring,
            "use_llm_error_analysis": use_llm_error_analysis,
            "generate_pdf": generate_pdf,
        },
    }

    # Run evaluation in background
    config = {
        "chatbot_api_url": chatbot_api_url,
        "execute_and_compare": execute_and_compare,
        "use_llm_scoring": use_llm_scoring,
        "use_llm_error_analysis": use_llm_error_analysis,
        "generate_pdf": generate_pdf,
    }
    background_tasks.add_task(_run_evaluation_job, job_id, questions, config)

    return {
        "job_id": job_id,
        "status": "pending",
        "total_questions": len(questions),
        "message": "Evaluation job started. Use /api/job/{job_id} to check status.",
    }


@app.get("/api/job/{job_id}")
async def get_job_status(job_id: str):
    """Get the status and results of an evaluation job."""
    if job_id not in evaluation_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job = evaluation_jobs[job_id]

    # Return a lighter response if still running
    if job["status"] in ["pending", "running", "scoring", "analyzing_errors", "generating_reports"]:
        return {
            "job_id": job["job_id"],
            "status": job["status"],
            "progress": job.get("progress", {}),
            "created_at": job.get("created_at"),
            "started_at": job.get("started_at"),
        }

    # Return full results when completed
    return job


@app.get("/api/job/{job_id}/report/{format}")
async def download_report(job_id: str, format: str):
    """Download a generated report."""
    if job_id not in evaluation_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job = evaluation_jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not yet completed")

    reports = job.get("reports", {})
    report_path = reports.get(format, "")

    if not report_path or not os.path.exists(report_path):
        raise HTTPException(
            status_code=404,
            detail=f"Report in format '{format}' not available. Available: {list(reports.keys())}",
        )

    media_types = {
        "text": "text/plain",
        "json": "application/json",
        "csv": "text/csv",
        "pdf": "application/pdf",
    }

    return FileResponse(
        path=report_path,
        media_type=media_types.get(format, "application/octet-stream"),
        filename=os.path.basename(report_path),
    )


@app.get("/api/jobs")
async def list_jobs():
    """List all evaluation jobs."""
    jobs = []
    for job_id, job in evaluation_jobs.items():
        jobs.append({
            "job_id": job["job_id"],
            "status": job["status"],
            "total_questions": job.get("total_questions", 0),
            "created_at": job.get("created_at"),
            "progress": job.get("progress", {}),
        })
    return {"jobs": jobs}


@app.delete("/api/job/{job_id}")
async def delete_job(job_id: str):
    """Delete an evaluation job."""
    if job_id not in evaluation_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Clean up report files
    job = evaluation_jobs[job_id]
    reports = job.get("reports", {})
    for fmt, path in reports.items():
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

    del evaluation_jobs[job_id]
    return {"message": f"Job {job_id} deleted"}


@app.get("/api/error-labels")
async def get_error_labels():
    """Get the error label definitions."""
    from teacher_bot.error_analyzer import ERROR_LABELS
    return {"error_labels": ERROR_LABELS}


@app.get("/api/scoring-framework")
async def get_scoring_framework():
    """Get the scoring framework definition."""
    from teacher_bot.scoring_engine import SQL_PATTERN_SCORES
    return {
        "sql_pattern_scores": SQL_PATTERN_SCORES,
        "d_score_rules": {
            1: "1 table",
            2: "2 tables",
            3: "3+ tables",
        },
        "b_score_rules": {
            0: "Direct mapping from schema/docs",
            1: "Requires additional business meaning / semantic",
        },
        "level_rules": {
            "Dễ": "Total Score 0-4, no override",
            "Trung bình": "Total Score 5-7, or bumped from Dễ",
            "Khó": "Total Score >=8, or has sequence, or (set_diff + B=1), or (D=3 and P>=4)",
        },
    }


# ─── Startup ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  Teacher Bot - Chatbot Evaluation Framework")
    print("  Starting on http://localhost:8001")
    print("=" * 60)
    print("  Make sure the chatbot is running on http://localhost:8000")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8001)
