"""
Chatbot Evaluator Module
Calls the chatbot API to generate SQL queries and compares them with expected results.
"""

import httpx
import asyncio
import re
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class EvaluationResult:
    """Result of evaluating a single question."""
    question: str
    level: str
    expected_sql: str
    bot_sql: str
    bot_raw_response: str
    is_correct: Optional[bool] = None
    sql_execution_result: Optional[Any] = None
    expected_execution_result: Optional[Any] = None
    error_message: str = ""
    elapsed_time: float = 0.0
    problem_type: str = ""
    score: Optional[Dict[str, Any]] = None
    error_labels: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "level": self.level,
            "expected_sql": self.expected_sql,
            "bot_sql": self.bot_sql,
            "bot_raw_response": self.bot_raw_response,
            "is_correct": self.is_correct,
            "error_message": self.error_message,
            "elapsed_time": self.elapsed_time,
            "problem_type": self.problem_type,
            "score": self.score,
            "error_labels": self.error_labels,
        }


class ChatbotEvaluator:
    """Evaluates the chatbot by calling its API and comparing outputs."""

    def __init__(self, chatbot_api_url: str = "http://localhost:8000"):
        self.chatbot_api_url = chatbot_api_url.rstrip("/")
        self.chat_endpoint = f"{self.chatbot_api_url}/api/chat"
        self.run_sql_endpoint = f"{self.chatbot_api_url}/api/run_sql"
        self.results: List[EvaluationResult] = []

    async def check_chatbot_health(self) -> bool:
        """Check if the chatbot API is healthy."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.chatbot_api_url}/health")
                return response.status_code == 200
        except Exception:
            return False

    def extract_sql_from_response(self, response_text: str) -> str:
        """Extract SQL query from the chatbot's response text."""
        if not response_text:
            return ""

        # Try to extract from ```sql ... ``` code block
        sql_match = re.search(r"```sql\s+(.*?)\s+```", response_text, re.DOTALL)
        if sql_match:
            return sql_match.group(1).strip()

        # Try to extract from ``` ... ``` code block
        code_match = re.search(r"```\s+(.*?)\s+```", response_text, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        # If no code blocks, try to find SELECT statement
        select_match = re.search(
            r"(SELECT\s+.*?)(?:\n\n|\Z)", response_text, re.DOTALL | re.IGNORECASE
        )
        if select_match:
            return select_match.group(1).strip()

        return response_text.strip()

    async def call_chatbot(self, question: str) -> Dict[str, str]:
        """Call the chatbot API with a question and return the response."""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                payload = {"message": question}
                start_time = time.time()
                response = await client.post(self.chat_endpoint, json=payload)
                elapsed = time.time() - start_time

                if response.status_code == 200:
                    data = response.json()
                    raw_response = data.get("response", "")
                    sql = self.extract_sql_from_response(raw_response)
                    return {
                        "raw_response": raw_response,
                        "sql": sql,
                        "elapsed_time": elapsed,
                        "error": "",
                    }
                else:
                    return {
                        "raw_response": "",
                        "sql": "",
                        "elapsed_time": elapsed,
                        "error": f"HTTP {response.status_code}: {response.text}",
                    }
        except Exception as e:
            return {
                "raw_response": "",
                "sql": "",
                "elapsed_time": 0.0,
                "error": str(e),
            }

    async def execute_sql(self, sql: str) -> Dict[str, Any]:
        """Execute a SQL query through the chatbot's run_sql endpoint."""
        if not sql or not sql.strip():
            return {"rows": [], "error": "Empty SQL query"}

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                payload = {"sql": sql}
                response = await client.post(self.run_sql_endpoint, json=payload)
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"rows": [], "error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            return {"rows": [], "error": str(e)}

    def normalize_sql(self, sql: str) -> str:
        """Normalize SQL for comparison (remove whitespace, lowercase)."""
        if not sql:
            return ""
        # Remove comments
        sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        # Normalize whitespace
        sql = re.sub(r'\s+', ' ', sql).strip().lower()
        # Remove trailing semicolons
        sql = sql.rstrip(';').strip()
        return sql

    def compare_results(
        self, expected_result: Any, bot_result: Any
    ) -> bool:
        """Compare execution results of expected and bot SQL queries."""
        if expected_result is None and bot_result is None:
            return True
        if expected_result is None or bot_result is None:
            return False

        expected_rows = expected_result.get("rows", []) if isinstance(expected_result, dict) else []
        bot_rows = bot_result.get("rows", []) if isinstance(bot_result, dict) else []

        # Check for errors
        if expected_result.get("error") or bot_result.get("error"):
            return False

        # Compare row counts
        if len(expected_rows) != len(bot_rows):
            return False

        # Compare values (order may differ, so sort)
        try:
            def sort_rows(rows):
                return sorted(
                    [tuple(sorted(r.items())) for r in rows]
                )
            return sort_rows(expected_rows) == sort_rows(bot_rows)
        except Exception:
            return str(expected_rows) == str(bot_rows)

    async def evaluate_single_question(
        self,
        question: str,
        level: str = "",
        expected_sql: str = "",
        execute_and_compare: bool = True,
    ) -> EvaluationResult:
        """Evaluate a single question against the chatbot."""
        result = EvaluationResult(
            question=question,
            level=level,
            expected_sql=expected_sql,
            bot_sql="",
            bot_raw_response="",
        )

        # Call the chatbot
        bot_response = await self.call_chatbot(question)
        result.bot_raw_response = bot_response["raw_response"]
        result.bot_sql = bot_response["sql"]
        result.elapsed_time = bot_response["elapsed_time"]

        if bot_response["error"]:
            result.error_message = bot_response["error"]
            result.is_correct = False
            return result

        # Compare by execution results if expected SQL is available
        if execute_and_compare and expected_sql and expected_sql.strip():
            expected_result = await self.execute_sql(expected_sql)
            bot_result = await self.execute_sql(result.bot_sql)

            result.expected_execution_result = expected_result
            result.sql_execution_result = bot_result

            if bot_result.get("error"):
                result.error_message = f"Bot SQL execution error: {bot_result['error']}"
                result.is_correct = False
            elif expected_result.get("error"):
                result.error_message = f"Expected SQL execution error: {expected_result['error']}"
                result.is_correct = None  # Can't determine
            else:
                result.is_correct = self.compare_results(expected_result, bot_result)
        elif result.bot_sql:
            # Try just executing the bot SQL to see if it's valid
            bot_result = await self.execute_sql(result.bot_sql)
            result.sql_execution_result = bot_result
            if bot_result.get("error"):
                result.error_message = f"Bot SQL execution error: {bot_result['error']}"
                result.is_correct = False
            else:
                result.is_correct = None  # No expected SQL to compare against

        return result

    async def evaluate_all_questions(
        self,
        questions: List[Dict[str, str]],
        execute_and_compare: bool = True,
        progress_callback=None,
    ) -> List[EvaluationResult]:
        """Evaluate all questions sequentially (to avoid overwhelming the chatbot)."""
        self.results = []
        total = len(questions)

        for idx, q in enumerate(questions):
            if progress_callback:
                progress_callback(idx + 1, total, q["question"])

            result = await self.evaluate_single_question(
                question=q["question"],
                level=q.get("level", ""),
                expected_sql=q.get("expected_sql", ""),
                execute_and_compare=execute_and_compare,
            )
            self.results.append(result)

            # Small delay between requests to avoid overwhelming the API
            await asyncio.sleep(0.5)

        return self.results

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all evaluation results."""
        if not self.results:
            return {"total": 0}

        total = len(self.results)
        correct = sum(1 for r in self.results if r.is_correct is True)
        incorrect = sum(1 for r in self.results if r.is_correct is False)
        unknown = sum(1 for r in self.results if r.is_correct is None)
        errors = sum(1 for r in self.results if r.error_message)
        avg_time = sum(r.elapsed_time for r in self.results) / total if total > 0 else 0

        # By difficulty level
        level_stats = {}
        for r in self.results:
            level = r.level or "Unknown"
            if level not in level_stats:
                level_stats[level] = {"total": 0, "correct": 0, "incorrect": 0, "unknown": 0}
            level_stats[level]["total"] += 1
            if r.is_correct is True:
                level_stats[level]["correct"] += 1
            elif r.is_correct is False:
                level_stats[level]["incorrect"] += 1
            else:
                level_stats[level]["unknown"] += 1

        return {
            "total": total,
            "correct": correct,
            "incorrect": incorrect,
            "unknown": unknown,
            "pass_rate": round(correct / total * 100, 2) if total > 0 else 0,
            "fail_rate": round(incorrect / total * 100, 2) if total > 0 else 0,
            "error_count": errors,
            "avg_response_time": round(avg_time, 2),
            "level_stats": level_stats,
        }
