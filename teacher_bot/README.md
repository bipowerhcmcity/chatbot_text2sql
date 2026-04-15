# Teacher Bot - Chatbot Evaluation Framework

A comprehensive scoring and evaluation framework for the Text-to-SQL chatbot. This is a **separate application** that runs independently from the main chatbot.

## Architecture

```
teacher_bot/
├── __init__.py              # Package init
├── input_processor.py       # CSV file reader & validator
├── evaluator.py             # Chatbot API caller & result comparator
├── scoring_engine.py        # D + P + B scoring with override rules
├── error_analyzer.py        # G1-G4 error classification (LLM-powered)
├── report_generator.py      # Text, CSV, JSON, PDF report generation
├── requirements.txt         # Additional dependencies
├── static/
│   ├── index.html           # Web UI
│   ├── styles.css           # Styles
│   └── script.js            # Frontend logic
├── reports/                 # Generated reports (auto-created)
└── uploads/                 # Uploaded CSVs (auto-created)

teacher_bot_app.py           # Entry point (FastAPI, port 8001)
```

## Quick Start

### 1. Install additional dependencies

```bash
pip install httpx fpdf2
```

### 2. Start the main chatbot (port 8000)

```bash
python main.py
```

### 3. Start the Teacher Bot (port 8001)

```bash
python teacher_bot_app.py
```

### 4. Open the Teacher Bot UI

Navigate to **http://localhost:8001** in your browser.

## Usage

### Web UI
1. Enter the Chatbot API URL (default: `http://localhost:8000`)
2. Click "Check Connection" to verify connectivity
3. Upload a **Question List CSV** file
4. Configure evaluation options
5. Click **Start Evaluation**
6. View results, error analysis, and download reports

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Teacher Bot Web UI |
| `/health` | GET | Health check |
| `/api/check-chatbot` | POST | Check chatbot API connectivity |
| `/api/upload-questions` | POST | Upload Question List CSV |
| `/api/evaluate-single` | POST | Evaluate a single question |
| `/api/evaluate-batch` | POST | Start batch evaluation (background) |
| `/api/job/{job_id}` | GET | Get job status & results |
| `/api/job/{job_id}/report/{format}` | GET | Download report (text/csv/json/pdf) |
| `/api/jobs` | GET | List all evaluation jobs |
| `/api/error-labels` | GET | Get error label definitions |
| `/api/scoring-framework` | GET | Get scoring framework rules |

### Quick Test (Single Question)
```bash
curl -X POST http://localhost:8001/api/evaluate-single \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Trong tháng 03/2026 có bao nhiêu mũi vaccine đã được tiêm thành công?",
    "expected_sql": "SELECT COUNT(*) FROM vaccine_record WHERE ...",
    "chatbot_api_url": "http://localhost:8000"
  }'
```

## Scoring Framework

### Total Score = D + P + B

**D (Data Scope):**
| Score | Meaning |
|-------|---------|
| 1 | 1 table |
| 2 | 2 tables |
| 3 | 3+ tables |

**P (SQL Pattern):**
| Tag | Score | When |
|-----|-------|------|
| agg | 1 | COUNT, SUM, AVG, MIN, MAX |
| group | 1 | GROUP BY |
| distinct | 1 | DISTINCT counting |
| time_condition | 1 | Time-based WHERE |
| ratio | 2 | Percentage / ratio |
| comparison | 2 | Comparing groups/periods |
| rank | 2 | TOP / BOTTOM / ORDER BY LIMIT |
| join | 2 | JOIN operations |
| set_diff | 2 | Set difference (A but not B) |
| sequence | 3 | Window / CTE / sequential logic |

**B (Business Rule):**
| Score | Meaning |
|-------|---------|
| 0 | Direct mapping from schema |
| 1 | Requires business semantic |

### Level Assignment

| Level | Rule |
|-------|------|
| Dễ | Total Score 0–4, no override |
| Trung bình | Total Score 5–7, or bumped from Dễ |
| Khó | Total Score ≥8, or has sequence, or (set_diff + B=1), or (D=3 and P≥4) |

## Error Labels

| Group | Name | Description |
|-------|------|-------------|
| G1 | Question Understanding | Bot misunderstands the question |
| G1.1 | Wrong Analytical Task | Misunderstands count/compare/rank/etc |
| G1.2 | Wrong Analysis Scope | Wrong level/dimension |
| G1.3 | Incomplete Requirement | Missing part of the requirement |
| G2 | Business Rule Mapping | Wrong business-to-data mapping |
| G2.1 | Wrong Business Definition | Wrong definition mapping |
| G2.2 | Missing Valid Scenario | Missing valid flows |
| G2.3 | Included Invalid Scenario | Too broad |
| G3 | Schema Mapping | Wrong tables/columns/joins |
| G3.1 | Wrong Join Logic | Wrong join keys/paths |
| G3.2 | Schema Hallucination | Non-existent tables/columns |
| G4 | Calculation Logic | Wrong aggregation/counting |

Priority: G1 → G2 → G3 → G4

## Question List CSV Format

Required columns:
- `Question`: The analytical question
- `Level`: Difficulty level (Dễ, Trung bình, Khó)

Optional columns:
- `Expected SQL`: Expected SQL query
- `Answer (Bot)`: Pre-existing bot answer
- `Evaluation`: TRUE/FALSE
- `Problem Type`: Error classification
