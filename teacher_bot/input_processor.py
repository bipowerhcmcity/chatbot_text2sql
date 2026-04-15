"""
Input Processor Module
Reads and validates Question List CSV and Scoring Framework CSV files.

Handles real-world CSV quirks:
- Trailing commas that create phantom 'Unnamed' columns
- NaN / missing values in optional columns
- Boolean 'Evaluation' column (numpy bool → Python bool)
- Multiline SQL strings inside quoted cells
"""

import math
import pandas as pd
import numpy as np
import os
from typing import Optional, Dict, Any, List


def _sanitize_value(val):
    """Convert a single value to a JSON-safe Python primitive."""
    if val is None:
        return ""
    if isinstance(val, (bool, np.bool_)):
        return bool(val)
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return ""
        return val
    if isinstance(val, np.integer):
        return int(val)
    if isinstance(val, np.floating):
        v = float(val)
        if math.isnan(v) or math.isinf(v):
            return ""
        return v
    # Catch pandas NA / NaT
    try:
        if pd.isna(val):
            return ""
    except (TypeError, ValueError):
        pass
    return str(val).strip()


class InputProcessor:
    """Reads, validates, and preprocesses input CSV files."""

    # Expected columns for Question List CSV
    QUESTION_LIST_REQUIRED_COLS = ["Question", "Level"]
    QUESTION_LIST_OPTIONAL_COLS = [
        "Expected SQL", "Answer (Bot)", "Evaluation", "Problem Type"
    ]

    def __init__(self):
        self.question_df: Optional[pd.DataFrame] = None
        self.scorer_df: Optional[pd.DataFrame] = None
        self.error_labels_df: Optional[pd.DataFrame] = None

    # ------------------------------------------------------------------
    # Question List
    # ------------------------------------------------------------------
    def load_question_list(self, file_path: str) -> pd.DataFrame:
        """Load and validate the Question List CSV.

        Handles:
        - trailing-comma phantom columns (``Unnamed: *``)
        - NaN in string columns → empty string
        - numpy bool ``Evaluation`` → Python bool
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Question list file not found: {file_path}")

        df = pd.read_csv(file_path, encoding="utf-8")

        # 1. Drop phantom columns created by trailing commas
        unnamed_cols = [c for c in df.columns if c.startswith("Unnamed")]
        if unnamed_cols:
            df = df.drop(columns=unnamed_cols)

        # 2. Strip whitespace from column names
        df.columns = [c.strip() for c in df.columns]

        # 3. Validate required columns
        missing_cols = [
            col for col in self.QUESTION_LIST_REQUIRED_COLS if col not in df.columns
        ]
        if missing_cols:
            raise ValueError(
                f"Question list CSV missing required columns: {missing_cols}. "
                f"Found columns: {list(df.columns)}"
            )

        # 4. Clean 'Question' column – drop empty rows
        df["Question"] = df["Question"].astype(str).str.strip()
        df = df[
            df["Question"].notna()
            & (df["Question"] != "")
            & (df["Question"] != "nan")
        ]

        # 5. Ensure optional columns exist with safe defaults
        for col in self.QUESTION_LIST_OPTIONAL_COLS:
            if col not in df.columns:
                df[col] = "" if col != "Evaluation" else False

        # 6. Sanitize each column to avoid NaN / numpy types
        #    - Evaluation → bool
        #    - Everything else → string (empty string for NaN)
        for col in df.columns:
            if col == "Evaluation":
                df[col] = df[col].apply(
                    lambda v: bool(v) if not (isinstance(v, float) and math.isnan(v)) else False
                )
            else:
                df[col] = df[col].apply(
                    lambda v: "" if (isinstance(v, float) and math.isnan(v)) else str(v).strip()
                )

        self.question_df = df.reset_index(drop=True)
        return self.question_df

    def load_scorer_framework(self, file_path: str) -> pd.DataFrame:
        """Load and validate the Scoring Framework / Question Scorer CSV."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Scorer framework file not found: {file_path}")

        df = pd.read_csv(file_path, encoding="utf-8")

        # The scorer CSV has a header row then scoring data
        # Try to find the row that starts the actual data
        # Look for a column named "Question"
        if "Question" in df.columns:
            # Filter out summary/metadata rows
            scorer_cols = [
                "Question", "D Score", "B Score", "agg", "group", "distinct",
                "time\ncondition", "ratio", "comparison", "rank", "join",
                "set\ndiff", "sequence", "P Score", "Total Score",
                "Override Rule", "Level"
            ]
            # Try alternate column names
            available_cols = []
            for col in scorer_cols:
                if col in df.columns:
                    available_cols.append(col)
                else:
                    # Try without newline
                    alt_col = col.replace("\n", " ")
                    if alt_col in df.columns:
                        available_cols.append(alt_col)

            if available_cols:
                df = df[available_cols].copy()
                df = df[df["Question"].notna() & (df["Question"].astype(str).str.strip() != "")]
                df = df.reset_index(drop=True)

        self.scorer_df = df
        return self.scorer_df

    def load_error_labels(self, file_path: str) -> pd.DataFrame:
        """Load the Error Labels CSV."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Error labels file not found: {file_path}")

        df = pd.read_csv(file_path, encoding="utf-8")
        self.error_labels_df = df
        return self.error_labels_df

    def get_questions(self) -> List[Dict[str, Any]]:
        """Return list of question dicts from loaded question list.

        Every value is guaranteed to be a JSON-safe Python primitive
        (str, bool, int, float – no NaN / numpy types).
        """
        if self.question_df is None:
            raise RuntimeError("Question list not loaded. Call load_question_list first.")

        questions: List[Dict[str, Any]] = []
        for _, row in self.question_df.iterrows():
            questions.append({
                "question": _sanitize_value(row.get("Question", "")),
                "level": _sanitize_value(row.get("Level", "")),
                "expected_sql": _sanitize_value(row.get("Expected SQL", "")),
                "bot_answer": _sanitize_value(row.get("Answer (Bot)", "")),
                "evaluation": bool(row.get("Evaluation", False))
                    if not (isinstance(row.get("Evaluation"), float) and math.isnan(row.get("Evaluation")))
                    else False,
                "problem_type": _sanitize_value(row.get("Problem Type", "")),
            })
        return questions

    def validate_inputs(self) -> Dict[str, Any]:
        """Validate all loaded inputs and return a JSON-safe summary."""
        summary: Dict[str, Any] = {
            "question_list_loaded": self.question_df is not None,
            "scorer_loaded": self.scorer_df is not None,
            "error_labels_loaded": self.error_labels_df is not None,
            "total_questions": len(self.question_df) if self.question_df is not None else 0,
            "difficulty_distribution": {},
            "errors": [],
        }

        if self.question_df is not None:
            # Build distribution with plain Python types
            level_counts = self.question_df["Level"].value_counts()
            summary["difficulty_distribution"] = {
                str(k): int(v) for k, v in level_counts.items()
            }

            # Check for questions without expected SQL
            no_sql_mask = (
                self.question_df["Expected SQL"].isna()
                | (self.question_df["Expected SQL"].astype(str).str.strip() == "")
            )
            no_sql_count = int(no_sql_mask.sum())
            if no_sql_count > 0:
                summary["errors"].append(
                    f"{no_sql_count} questions have no Expected SQL defined"
                )

        return summary
