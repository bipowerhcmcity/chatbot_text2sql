"""
Scoring Engine Module
Calculates difficulty scores based on D (Data Scope), P (SQL Pattern), B (Business Rule)
and applies override rules to determine the final difficulty level.
"""

import re
import os
from typing import Dict, Any, List, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


# SQL Pattern tags and their scores
SQL_PATTERN_SCORES = {
    "agg": 1,           # COUNT, SUM, AVG, MIN, MAX
    "group": 1,         # GROUP BY
    "distinct": 1,      # DISTINCT counting
    "time_condition": 1, # Time-based WHERE conditions
    "ratio": 2,         # Percentage / ratio calculations
    "comparison": 2,    # Comparing groups / time periods
    "rank": 2,          # TOP / BOTTOM / ORDER BY LIMIT
    "join": 2,          # JOIN operations
    "set_diff": 2,      # Set difference (A but not B)
    "sequence": 3,      # Sequence / funnel / window operations
}


class ScoringEngine:
    """Calculates scores and assigns difficulty levels to questions."""

    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm
        if use_llm:
            api_key = os.getenv("OPENAI_API_KEY")
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = None

    def analyze_sql_patterns(self, sql: str) -> Dict[str, int]:
        """Analyze a SQL query for pattern tags using regex heuristics."""
        if not sql:
            return {k: 0 for k in SQL_PATTERN_SCORES}

        sql_lower = sql.lower()
        sql_upper = sql.upper()
        patterns = {}

        # agg: aggregate functions
        agg_funcs = re.findall(
            r'\b(count|sum|avg|min|max)\s*\(', sql_lower
        )
        patterns["agg"] = 1 if agg_funcs else 0

        # group: GROUP BY
        patterns["group"] = 1 if re.search(r'\bgroup\s+by\b', sql_lower) else 0

        # distinct: DISTINCT
        patterns["distinct"] = 1 if re.search(r'\bdistinct\b', sql_lower) else 0

        # time_condition: time-based WHERE (date, month, year, LIKE '%/2026')
        time_patterns = [
            r"'\d{1,2}/\d{1,2}/\d{4}'",  # '3/15/2026'
            r"like\s+'%?/\d{4}'",          # LIKE '%/2026'
            r"like\s+'\d{1,2}/%/\d{4}'",   # LIKE '3/%/2026'
            r"\bbetween\b.*\band\b",        # BETWEEN ... AND
            r"\bstrftime\b",               # strftime
            r"\bjulianday\b",              # julianday
            r"\bdate\b",                   # date function
            r"\byear\b",                   # year
            r"\bmonth\b",                  # month
        ]
        patterns["time_condition"] = 1 if any(
            re.search(p, sql_lower) for p in time_patterns
        ) else 0

        # ratio: percentage / ratio calculations
        ratio_patterns = [
            r'\b100\.0\s*\*',
            r'\bround\s*\(.+/\s*.+\)',
            r'\bpercent',
            r'\bratio\b',
            r'\* 100\b',
        ]
        patterns["ratio"] = 2 if any(
            re.search(p, sql_lower) for p in ratio_patterns
        ) else 0

        # comparison: comparing groups or time periods (CASE WHEN, UNION, subqueries)
        comparison_patterns = [
            r'\bcase\s+when\b.*\bthen\b',
            r'\bunion\b',
        ]
        # Also check for multiple time conditions (comparing periods)
        time_literals = re.findall(r"like\s+'(\d{1,2})/%/\d{4}'", sql_lower)
        has_comparison = any(re.search(p, sql_lower) for p in comparison_patterns) or len(set(time_literals)) > 1
        patterns["comparison"] = 2 if has_comparison else 0

        # rank: TOP / LIMIT / ORDER BY with LIMIT
        rank_patterns = [
            r'\blimit\s+\d+',
            r'\btop\s+\d+',
            r'\brow_number\b',
            r'\brank\b',
            r'\bdense_rank\b',
        ]
        patterns["rank"] = 2 if (
            any(re.search(p, sql_lower) for p in rank_patterns)
            and re.search(r'\border\s+by\b', sql_lower)
        ) else 0

        # join: JOIN operations
        join_count = len(re.findall(r'\bjoin\b', sql_lower))
        patterns["join"] = 2 if join_count > 0 else 0

        # set_diff: set difference (NOT IN, NOT EXISTS, LEFT JOIN ... IS NULL)
        set_diff_patterns = [
            r'\bnot\s+in\b',
            r'\bnot\s+exists\b',
            r'\bleft\s+join\b.*\bis\s+null\b',
            r'\bexcept\b',
        ]
        patterns["set_diff"] = 2 if any(
            re.search(p, sql_lower, re.DOTALL) for p in set_diff_patterns
        ) else 0

        # sequence: window functions, CTEs with sequential logic, julianday diffs
        sequence_patterns = [
            r'\bover\s*\(',
            r'\blead\b',
            r'\blag\b',
            r'\bwith\b.*\bas\s*\(',
            r'\bjulianday\b.*-\s*julianday\b',
        ]
        patterns["sequence"] = 3 if any(
            re.search(p, sql_lower, re.DOTALL) for p in sequence_patterns
        ) else 0

        return patterns

    def count_tables(self, sql: str) -> int:
        """Count the number of distinct tables referenced in a SQL query."""
        if not sql:
            return 0

        # Extract table names from FROM and JOIN clauses
        # Pattern matches table names (possibly quoted with double quotes)
        tables = set()

        # FROM clause
        from_matches = re.findall(
            r'\bfrom\s+"([^"]+)"|\bfrom\s+(\w+)', sql.lower()
        )
        for m in from_matches:
            table = m[0] or m[1]
            if table and table not in ('select', 'where', 'group', 'order', 'having'):
                tables.add(table)

        # JOIN clause
        join_matches = re.findall(
            r'\bjoin\s+"([^"]+)"|\bjoin\s+(\w+)', sql.lower()
        )
        for m in join_matches:
            table = m[0] or m[1]
            if table:
                tables.add(table)

        return max(1, len(tables))

    def calculate_d_score(self, sql: str) -> int:
        """Calculate D (Data Scope) score based on number of tables."""
        table_count = self.count_tables(sql)
        if table_count <= 1:
            return 1
        elif table_count == 2:
            return 2
        else:
            return 3

    def calculate_p_score(self, patterns: Dict[str, int]) -> int:
        """Calculate P (SQL Pattern) score as sum of pattern scores."""
        return sum(patterns.values())

    def calculate_b_score_with_llm(self, question: str) -> int:
        """Use LLM to determine B (Business Rule) score."""
        if not self.client:
            return 0

        prompt = f"""You are evaluating whether a data analytics question requires business semantic mapping 
beyond what's directly available in database schema/documentation.

Question: "{question}"

Scoring rules for B (Business Rule Mapping):
- B = 0: The question can be answered by mapping directly to schema columns/tables. 
  The metric or field is clearly available. (e.g., "count of orders", "total revenue")
- B = 1: The question requires additional business meaning or semantic interpretation 
  beyond schema/docs. The concept is derived, involves business-specific terminology, 
  or requires understanding of implicit rules. (e.g., "repeat customers", "conversion rate", 
  "active users", age group classification)

Return ONLY a JSON object:
{{"b_score": 0 or 1, "reason": "brief explanation"}}
"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            content = response.choices[0].message.content.strip()
            # Extract JSON
            import json
            # Try to parse directly
            try:
                result = json.loads(content)
                return result.get("b_score", 0)
            except json.JSONDecodeError:
                # Try to extract from code block
                match = re.search(r'\{[^}]+\}', content)
                if match:
                    result = json.loads(match.group())
                    return result.get("b_score", 0)
                return 0
        except Exception as e:
            print(f"Error calculating B score with LLM: {e}")
            return 0

    def determine_level(
        self,
        total_score: int,
        d_score: int,
        b_score: int,
        p_score: int,
        patterns: Dict[str, int],
    ) -> tuple:
        """Determine the difficulty level based on scores and override rules.

        Returns:
            tuple: (level: str, override_rule: str)
        """
        has_sequence = patterns.get("sequence", 0) > 0
        has_set_diff = patterns.get("set_diff", 0) > 0
        has_comparison = patterns.get("comparison", 0) > 0

        # Priority 1: Check "Khó" (Hard) rules first
        if has_sequence:
            return "Khó", "Has sequence → Khó"
        if has_set_diff and b_score >= 1:
            return "Khó", "set_diff + B=1 → Khó"
        if d_score >= 3 and p_score >= 4:
            return "Khó", "D=3 and P>=4 → Khó"
        if total_score >= 8:
            return "Khó", "Total Score >=8 → Khó"

        # Priority 2: Determine base level from total score
        if total_score <= 4:
            base_level = "Dễ"
        elif total_score <= 7:
            base_level = "Trung bình"
        else:
            base_level = "Khó"

        # Priority 3: Check override rules for bumping Dễ → Trung bình
        if base_level == "Dễ":
            if b_score >= 1:
                return "Trung bình", "B=1 and base=Dễ → Trung bình"
            if has_comparison:
                return "Trung bình", "Has comparison and base=Dễ → Trung bình"
            if has_set_diff:
                return "Trung bình", "Has set_diff and base=Dễ → Trung bình"

        override_rule = "No" if base_level == "Dễ" or (base_level == "Trung bình" and 5 <= total_score <= 7) else ""
        return base_level, override_rule

    def score_question(
        self,
        question: str,
        sql: str,
        use_llm_for_b: bool = True,
    ) -> Dict[str, Any]:
        """Calculate the complete score for a question/SQL pair."""
        # D Score
        d_score = self.calculate_d_score(sql)

        # B Score
        if use_llm_for_b and self.use_llm:
            b_score = self.calculate_b_score_with_llm(question)
        else:
            b_score = 0

        # SQL Patterns
        patterns = self.analyze_sql_patterns(sql)
        p_score = self.calculate_p_score(patterns)

        # Total Score
        total_score = d_score + b_score + p_score

        # Determine Level
        level, override_rule = self.determine_level(
            total_score, d_score, b_score, p_score, patterns
        )

        return {
            "d_score": d_score,
            "b_score": b_score,
            "p_score": p_score,
            "total_score": total_score,
            "patterns": patterns,
            "level": level,
            "override_rule": override_rule,
        }

    def score_questions_batch(
        self,
        questions: List[Dict[str, Any]],
        use_llm_for_b: bool = True,
    ) -> List[Dict[str, Any]]:
        """Score a batch of questions."""
        results = []
        for q in questions:
            # Use bot SQL if available, otherwise expected SQL
            sql = q.get("bot_sql", "") or q.get("expected_sql", "")
            score = self.score_question(
                question=q["question"],
                sql=sql,
                use_llm_for_b=use_llm_for_b,
            )
            result = {**q, "score": score}
            results.append(result)
        return results
