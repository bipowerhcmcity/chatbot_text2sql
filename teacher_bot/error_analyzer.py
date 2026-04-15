"""
Error Analyzer Module
Identifies and labels errors in the chatbot's SQL queries using the Error Labels framework.

Error Groups:
- G1: Question Understanding (Bot misunderstands the question)
- G2: Business Rule Mapping (Bot understands the question but maps business rules incorrectly)
- G3: Schema Mapping (Bot selects wrong tables, columns, keys, joins, or filter fields)
- G4: Calculation Logic (Bot makes errors in counting, aggregation, ratios)

Priority: G1 → G2 → G3 → G4
"""

import os
import re
import json
from typing import Dict, List, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Error label definitions
ERROR_LABELS = {
    "G1": {
        "name": "Question Understanding",
        "name_vi": "Hiểu sai câu hỏi",
        "description": "Bot misunderstands the analytical requirement of the question",
        "sub_labels": {
            "G1.1": {
                "name": "Wrong Analytical Task",
                "name_vi": "Hiểu sai loại yêu cầu phân tích",
                "description": "Bot misunderstands what the user wants: count, compare, rank, ratio, trend...",
            },
            "G1.2": {
                "name": "Wrong Analysis Scope",
                "name_vi": "Hiểu sai phạm vi phân tích",
                "description": "Bot misunderstands what/at what level/in which dimension to analyze",
            },
            "G1.3": {
                "name": "Incomplete Requirement Capture",
                "name_vi": "Hiểu thiếu yêu cầu câu hỏi",
                "description": "Bot understands the main part but misses a component of the requirement",
            },
        },
    },
    "G2": {
        "name": "Business Rule Mapping",
        "name_vi": "Map sai rule nghiệp vụ",
        "description": "Bot understands the question but doesn't correctly convert business concepts to data logic",
        "sub_labels": {
            "G2.1": {
                "name": "Wrong Business Definition",
                "name_vi": "Hiểu / dùng sai định nghĩa nghiệp vụ",
                "description": "Bot maps a business concept to the wrong data rule, or uses it differently from the agreed definition",
            },
            "G2.2": {
                "name": "Missing Valid Scenario",
                "name_vi": "Thiếu trường hợp hợp lệ trong rule",
                "description": "Rule is correct in direction but doesn't cover all valid behaviors/flows/conditions",
            },
            "G2.3": {
                "name": "Included Invalid Scenario",
                "name_vi": "Thêm trường hợp không hợp lệ vào rule",
                "description": "Rule is too broad, including behaviors/flows that don't belong to the business concept",
            },
        },
    },
    "G3": {
        "name": "Schema Mapping",
        "name_vi": "Sai mapping schema",
        "description": "Bot selects wrong tables, columns, keys, joins, or filter fields",
        "sub_labels": {
            "G3.1": {
                "name": "Wrong Join Logic",
                "name_vi": "Sai logic join",
                "description": "Correct entities identified but wrong join key/missing join/wrong join path",
            },
            "G3.2": {
                "name": "Schema Hallucination",
                "name_vi": "Tự tạo schema",
                "description": "Uses tables/columns/keys that don't exist",
            },
        },
    },
    "G4": {
        "name": "Calculation Logic",
        "name_vi": "Sai logic tính toán",
        "description": "Bot makes errors in counting, aggregation, or ratio calculation",
        "sub_labels": {},
    },
}


class ErrorAnalyzer:
    """Analyzes errors in chatbot SQL queries and assigns error labels."""

    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm
        if use_llm:
            api_key = os.getenv("OPENAI_API_KEY")
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = None

    def get_error_labels_description(self) -> str:
        """Get a formatted description of all error labels for the LLM prompt."""
        desc = "Error Label Definitions (Priority: G1 → G2 → G3 → G4):\n\n"
        for group_id, group in ERROR_LABELS.items():
            desc += f"{group_id}. {group['name']} ({group['name_vi']})\n"
            desc += f"   Description: {group['description']}\n"
            for sub_id, sub in group.get("sub_labels", {}).items():
                desc += f"   {sub_id}: {sub['name']} ({sub['name_vi']})\n"
                desc += f"      {sub['description']}\n"
            desc += "\n"
        return desc

    def analyze_error_with_llm(
        self,
        question: str,
        expected_sql: str,
        bot_sql: str,
        error_message: str = "",
    ) -> Dict[str, Any]:
        """Use LLM to analyze the error and assign labels."""
        if not self.client:
            return {"error_group": "", "error_labels": [], "analysis": "LLM not configured"}

        error_labels_desc = self.get_error_labels_description()

        prompt = f"""You are an expert SQL error analyst for a Text-to-SQL chatbot evaluation system.

Your task is to compare the bot's generated SQL with the expected SQL and identify the type of error.

{error_labels_desc}

IMPORTANT RULES:
1. Apply the priority rule: G1 → G2 → G3 → G4 (assign the highest priority error group that applies)
2. A question can have multiple sub-labels but should primarily belong to ONE error group
3. If the SQL is correct (matches expected results), return "None" for error group
4. Analyze based on the SEMANTIC difference, not just syntactic differences

Question: "{question}"

Expected SQL:
```sql
{expected_sql}
```

Bot SQL:
```sql
{bot_sql}
```

{f'Error Message: {error_message}' if error_message else ''}

Return ONLY a JSON object:
{{
    "error_group": "G1" | "G2" | "G3" | "G4" | "None",
    "error_labels": ["G1.1", "G3.2", ...],
    "primary_label": "G1.1" | "None",
    "analysis": "Brief explanation of the error in Vietnamese",
    "severity": "high" | "medium" | "low" | "none"
}}
"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            content = response.choices[0].message.content.strip()

            # Parse JSON response
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
                if match:
                    result = json.loads(match.group())
                else:
                    result = {
                        "error_group": "Unknown",
                        "error_labels": [],
                        "primary_label": "Unknown",
                        "analysis": content,
                        "severity": "medium",
                    }

            return result

        except Exception as e:
            print(f"Error in LLM error analysis: {e}")
            return {
                "error_group": "Unknown",
                "error_labels": [],
                "primary_label": "Unknown",
                "analysis": f"LLM analysis failed: {str(e)}",
                "severity": "unknown",
            }

    def analyze_error_heuristic(
        self,
        question: str,
        expected_sql: str,
        bot_sql: str,
        error_message: str = "",
    ) -> Dict[str, Any]:
        """Use heuristic rules to analyze errors (fallback when LLM is not available)."""
        if not bot_sql:
            return {
                "error_group": "G1",
                "error_labels": ["G1.1"],
                "primary_label": "G1.1",
                "analysis": "Bot did not generate any SQL query",
                "severity": "high",
            }

        bot_lower = bot_sql.lower()
        expected_lower = (expected_sql or "").lower()

        labels = []
        analysis_parts = []

        # Check for schema hallucination (tables/columns that don't exist in expected)
        if error_message and ("no such table" in error_message.lower() or "no such column" in error_message.lower()):
            labels.append("G3.2")
            analysis_parts.append("Schema hallucination detected - using non-existent tables/columns")

        # Check for wrong joins
        bot_joins = set(re.findall(r'join\s+"?([^"\s]+)"?', bot_lower))
        expected_joins = set(re.findall(r'join\s+"?([^"\s]+)"?', expected_lower))
        if bot_joins != expected_joins and expected_joins:
            labels.append("G3.1")
            analysis_parts.append(f"Different join tables: bot={bot_joins}, expected={expected_joins}")

        # Check for wrong aggregation
        bot_aggs = set(re.findall(r'(count|sum|avg|min|max)\s*\(', bot_lower))
        expected_aggs = set(re.findall(r'(count|sum|avg|min|max)\s*\(', expected_lower))
        if bot_aggs != expected_aggs and expected_aggs:
            labels.append("G4")
            analysis_parts.append(f"Different aggregations: bot={bot_aggs}, expected={expected_aggs}")

        # Determine primary error group based on priority
        if not labels:
            # Generic classification based on overall structure
            if error_message:
                labels.append("G4")
                analysis_parts.append("SQL execution error suggesting calculation logic issue")
            else:
                labels.append("G4")
                analysis_parts.append("Result mismatch suggesting calculation logic issue")

        # Determine error group from highest priority label
        error_group = "None"
        for group in ["G1", "G2", "G3", "G4"]:
            if any(l.startswith(group) for l in labels):
                error_group = group
                break

        primary_label = labels[0] if labels else "None"

        return {
            "error_group": error_group,
            "error_labels": labels,
            "primary_label": primary_label,
            "analysis": "; ".join(analysis_parts) if analysis_parts else "No specific error detected",
            "severity": "high" if error_group in ["G1", "G2"] else "medium",
        }

    def analyze_error(
        self,
        question: str,
        expected_sql: str,
        bot_sql: str,
        is_correct: bool = False,
        error_message: str = "",
    ) -> Dict[str, Any]:
        """Main method to analyze errors. Uses LLM if available, falls back to heuristics."""
        # If the answer is correct, no error
        if is_correct:
            return {
                "error_group": "None",
                "error_labels": [],
                "primary_label": "None",
                "analysis": "Câu trả lời đúng - không có lỗi",
                "severity": "none",
            }

        if self.use_llm and self.client:
            return self.analyze_error_with_llm(
                question, expected_sql, bot_sql, error_message
            )
        else:
            return self.analyze_error_heuristic(
                question, expected_sql, bot_sql, error_message
            )

    def analyze_batch(
        self, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Analyze errors for a batch of evaluation results."""
        analyzed = []
        for r in results:
            error_analysis = self.analyze_error(
                question=r.get("question", ""),
                expected_sql=r.get("expected_sql", ""),
                bot_sql=r.get("bot_sql", ""),
                is_correct=r.get("is_correct", False),
                error_message=r.get("error_message", ""),
            )
            analyzed.append({**r, "error_analysis": error_analysis})
        return analyzed

    def get_error_distribution(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get distribution of errors by group and label."""
        group_counts = {}
        label_counts = {}
        severity_counts = {}

        for r in results:
            ea = r.get("error_analysis", {})
            group = ea.get("error_group", "Unknown")
            labels = ea.get("error_labels", [])
            severity = ea.get("severity", "unknown")

            group_counts[group] = group_counts.get(group, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

            for label in labels:
                label_counts[label] = label_counts.get(label, 0) + 1

        return {
            "by_group": group_counts,
            "by_label": label_counts,
            "by_severity": severity_counts,
        }
