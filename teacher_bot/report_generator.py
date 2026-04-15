"""
Report Generator Module
Generates detailed evaluation reports in text and PDF format.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional


class ReportGenerator:
    """Generates evaluation reports in various formats."""

    def __init__(self, output_dir: str = "teacher_bot/reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def _timestamp(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _format_sql(self, sql: str, indent: int = 4) -> str:
        """Format SQL for display in reports."""
        if not sql:
            return " " * indent + "(No SQL)"
        lines = sql.strip().split("\n")
        return "\n".join(" " * indent + line for line in lines)

    def _level_emoji(self, level: str) -> str:
        mapping = {
            "Dễ": "🟢",
            "Trung bình": "🟡",
            "Khó": "🔴",
        }
        return mapping.get(level, "⚪")

    def _result_emoji(self, is_correct: Optional[bool]) -> str:
        if is_correct is True:
            return "✅"
        elif is_correct is False:
            return "❌"
        return "❓"

    def generate_text_report(
        self,
        results: List[Dict[str, Any]],
        summary: Dict[str, Any],
        error_distribution: Dict[str, Any],
        chatbot_url: str = "",
    ) -> str:
        """Generate a detailed text report."""
        ts = self._timestamp()
        lines = []

        # Header
        lines.append("=" * 80)
        lines.append("  TEACHER BOT - CHATBOT EVALUATION REPORT")
        lines.append("=" * 80)
        lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if chatbot_url:
            lines.append(f"  Chatbot API: {chatbot_url}")
        lines.append(f"  Total Questions: {summary.get('total', 0)}")
        lines.append("=" * 80)
        lines.append("")

        # Executive Summary
        lines.append("📊 EXECUTIVE SUMMARY")
        lines.append("-" * 40)
        total = summary.get("total", 0)
        correct = summary.get("correct", 0)
        incorrect = summary.get("incorrect", 0)
        unknown = summary.get("unknown", 0)
        pass_rate = summary.get("pass_rate", 0)
        avg_time = summary.get("avg_response_time", 0)

        lines.append(f"  Total Questions:      {total}")
        lines.append(f"  Correct (✅):         {correct}")
        lines.append(f"  Incorrect (❌):       {incorrect}")
        lines.append(f"  Unknown (❓):         {unknown}")
        lines.append(f"  Pass Rate:            {pass_rate}%")
        lines.append(f"  Avg Response Time:    {avg_time}s")
        lines.append("")

        # Performance by Difficulty Level
        lines.append("📈 PERFORMANCE BY DIFFICULTY LEVEL")
        lines.append("-" * 40)
        level_stats = summary.get("level_stats", {})
        for level, stats in level_stats.items():
            level_total = stats["total"]
            level_correct = stats["correct"]
            level_rate = round(level_correct / level_total * 100, 1) if level_total > 0 else 0
            emoji = self._level_emoji(level)
            lines.append(f"  {emoji} {level}: {level_correct}/{level_total} ({level_rate}%)")
        lines.append("")

        # Error Distribution
        lines.append("🔍 ERROR DISTRIBUTION")
        lines.append("-" * 40)
        by_group = error_distribution.get("by_group", {})
        for group, count in sorted(by_group.items()):
            if group != "None":
                lines.append(f"  {group}: {count} errors")
        
        by_label = error_distribution.get("by_label", {})
        if by_label:
            lines.append("")
            lines.append("  Detailed Error Labels:")
            for label, count in sorted(by_label.items()):
                lines.append(f"    {label}: {count}")
        lines.append("")

        # Detailed Results
        lines.append("=" * 80)
        lines.append("  DETAILED EVALUATION RESULTS")
        lines.append("=" * 80)
        lines.append("")

        for idx, r in enumerate(results, 1):
            is_correct = r.get("is_correct")
            result_emoji = self._result_emoji(is_correct)
            level = r.get("level", "")
            level_emoji = self._level_emoji(level)

            lines.append(f"{'─' * 60}")
            lines.append(f"  Q{idx}: {r.get('question', '')}")
            lines.append(f"  Level: {level_emoji} {level}")
            lines.append(f"  Result: {result_emoji} {'PASS' if is_correct else 'FAIL' if is_correct is False else 'UNKNOWN'}")
            lines.append(f"  Response Time: {r.get('elapsed_time', 0):.2f}s")

            # Score
            score = r.get("score", {})
            if score:
                lines.append(f"  Score: D={score.get('d_score', 0)} + B={score.get('b_score', 0)} + P={score.get('p_score', 0)} = {score.get('total_score', 0)}")
                lines.append(f"  Calculated Level: {score.get('level', '')}")
                if score.get('override_rule') and score.get('override_rule') != 'No':
                    lines.append(f"  Override Rule: {score.get('override_rule', '')}")
                
                # Pattern details
                patterns = score.get("patterns", {})
                active_patterns = [k for k, v in patterns.items() if v > 0]
                if active_patterns:
                    lines.append(f"  SQL Patterns: {', '.join(active_patterns)}")

            # Error Analysis
            ea = r.get("error_analysis", {})
            if ea and ea.get("error_group") != "None":
                lines.append(f"  Error Group: {ea.get('error_group', '')}")
                lines.append(f"  Error Labels: {', '.join(ea.get('error_labels', []))}")
                lines.append(f"  Analysis: {ea.get('analysis', '')}")
                lines.append(f"  Severity: {ea.get('severity', '')}")

            # SQL Queries
            lines.append("")
            lines.append("  Expected SQL:")
            lines.append(self._format_sql(r.get("expected_sql", ""), 6))
            lines.append("")
            lines.append("  Bot SQL:")
            lines.append(self._format_sql(r.get("bot_sql", ""), 6))

            if r.get("error_message"):
                lines.append("")
                lines.append(f"  Error: {r.get('error_message', '')}")

            lines.append("")

        # Recommendations
        lines.append("=" * 80)
        lines.append("  RECOMMENDATIONS")
        lines.append("=" * 80)
        lines.append("")
        recommendations = self._generate_recommendations(results, summary, error_distribution)
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"  {i}. {rec}")
        lines.append("")
        lines.append("=" * 80)
        lines.append("  END OF REPORT")
        lines.append("=" * 80)

        report_text = "\n".join(lines)

        # Save to file
        filepath = os.path.join(self.output_dir, f"report_{ts}.txt")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report_text)

        return report_text, filepath

    def generate_json_report(
        self,
        results: List[Dict[str, Any]],
        summary: Dict[str, Any],
        error_distribution: Dict[str, Any],
        chatbot_url: str = "",
    ) -> tuple:
        """Generate a JSON report for programmatic consumption."""
        ts = self._timestamp()

        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "chatbot_url": chatbot_url,
                "total_questions": summary.get("total", 0),
            },
            "summary": summary,
            "error_distribution": error_distribution,
            "results": results,
            "recommendations": self._generate_recommendations(results, summary, error_distribution),
        }

        filepath = os.path.join(self.output_dir, f"report_{ts}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)

        return report, filepath

    def generate_csv_report(
        self,
        results: List[Dict[str, Any]],
    ) -> str:
        """Generate a CSV summary report."""
        import csv
        import io

        ts = self._timestamp()
        filepath = os.path.join(self.output_dir, f"report_{ts}.csv")

        rows = []
        for idx, r in enumerate(results, 1):
            score = r.get("score", {})
            ea = r.get("error_analysis", {})
            rows.append({
                "#": idx,
                "Question": r.get("question", ""),
                "Level": r.get("level", ""),
                "Is Correct": r.get("is_correct", ""),
                "D Score": score.get("d_score", ""),
                "B Score": score.get("b_score", ""),
                "P Score": score.get("p_score", ""),
                "Total Score": score.get("total_score", ""),
                "Calculated Level": score.get("level", ""),
                "Override Rule": score.get("override_rule", ""),
                "Error Group": ea.get("error_group", ""),
                "Error Labels": ", ".join(ea.get("error_labels", [])),
                "Error Analysis": ea.get("analysis", ""),
                "Severity": ea.get("severity", ""),
                "Response Time (s)": round(r.get("elapsed_time", 0), 2),
                "Expected SQL": r.get("expected_sql", ""),
                "Bot SQL": r.get("bot_sql", ""),
                "Error Message": r.get("error_message", ""),
            })

        with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
            if rows:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)

        return filepath

    def generate_pdf_report(
        self,
        results: List[Dict[str, Any]],
        summary: Dict[str, Any],
        error_distribution: Dict[str, Any],
        chatbot_url: str = "",
    ) -> str:
        """Generate a PDF report. Requires fpdf2 package."""
        try:
            from fpdf import FPDF
        except ImportError:
            print("Warning: fpdf2 not installed. Skipping PDF generation.")
            return ""

        ts = self._timestamp()
        filepath = os.path.join(self.output_dir, f"report_{ts}.pdf")

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Add Unicode font
        font_path = self._get_unicode_font_path()
        if font_path:
            pdf.add_font("NotoSans", "", font_path, uni=True)
            pdf.add_font("NotoSans", "B", font_path, uni=True)
            font_name = "NotoSans"
        else:
            font_name = "Helvetica"

        # Title Page
        pdf.add_page()
        pdf.set_font(font_name, "B", 20)
        pdf.cell(0, 40, "", ln=True)
        pdf.cell(0, 15, "Teacher Bot", ln=True, align="C")
        pdf.set_font(font_name, "", 14)
        pdf.cell(0, 10, "Chatbot Evaluation Report", ln=True, align="C")
        pdf.set_font(font_name, "", 10)
        pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
        if chatbot_url:
            pdf.cell(0, 8, f"API: {chatbot_url}", ln=True, align="C")

        # Summary Page
        pdf.add_page()
        pdf.set_font(font_name, "B", 16)
        pdf.cell(0, 10, "Executive Summary", ln=True)
        pdf.set_font(font_name, "", 11)
        pdf.ln(5)

        total = summary.get("total", 0)
        correct = summary.get("correct", 0)
        pass_rate = summary.get("pass_rate", 0)

        summary_lines = [
            f"Total Questions: {total}",
            f"Correct: {correct}",
            f"Incorrect: {summary.get('incorrect', 0)}",
            f"Pass Rate: {pass_rate}%",
            f"Avg Response Time: {summary.get('avg_response_time', 0)}s",
        ]
        for line in summary_lines:
            pdf.cell(0, 7, line, ln=True)

        # Level stats
        pdf.ln(5)
        pdf.set_font(font_name, "B", 12)
        pdf.cell(0, 10, "Performance by Level", ln=True)
        pdf.set_font(font_name, "", 10)

        level_stats = summary.get("level_stats", {})
        for level, stats in level_stats.items():
            lt = stats["total"]
            lc = stats["correct"]
            lr = round(lc / lt * 100, 1) if lt > 0 else 0
            pdf.cell(0, 7, f"  {level}: {lc}/{lt} ({lr}%)", ln=True)

        # Error Distribution
        pdf.ln(5)
        pdf.set_font(font_name, "B", 12)
        pdf.cell(0, 10, "Error Distribution", ln=True)
        pdf.set_font(font_name, "", 10)

        by_group = error_distribution.get("by_group", {})
        for group, count in sorted(by_group.items()):
            if group != "None":
                pdf.cell(0, 7, f"  {group}: {count} errors", ln=True)

        # Detailed Results
        pdf.add_page()
        pdf.set_font(font_name, "B", 16)
        pdf.cell(0, 10, "Detailed Results", ln=True)

        for idx, r in enumerate(results, 1):
            is_correct = r.get("is_correct")
            status = "PASS" if is_correct else "FAIL" if is_correct is False else "UNKNOWN"

            pdf.ln(3)
            pdf.set_font(font_name, "B", 10)
            q_text = f"Q{idx}: {r.get('question', '')[:80]}"
            pdf.cell(0, 7, q_text, ln=True)
            pdf.set_font(font_name, "", 9)
            pdf.cell(0, 6, f"  Level: {r.get('level', '')} | Result: {status} | Time: {r.get('elapsed_time', 0):.2f}s", ln=True)

            score = r.get("score", {})
            if score:
                pdf.cell(0, 6, f"  Score: D={score.get('d_score', 0)} B={score.get('b_score', 0)} P={score.get('p_score', 0)} Total={score.get('total_score', 0)}", ln=True)

            ea = r.get("error_analysis", {})
            if ea and ea.get("error_group") != "None":
                pdf.cell(0, 6, f"  Error: {ea.get('error_group', '')} - {', '.join(ea.get('error_labels', []))}", ln=True)
                analysis_text = ea.get("analysis", "")[:100]
                pdf.cell(0, 6, f"  Analysis: {analysis_text}", ln=True)

            # Check if we need a new page
            if pdf.get_y() > 250:
                pdf.add_page()

        # Recommendations
        pdf.add_page()
        pdf.set_font(font_name, "B", 16)
        pdf.cell(0, 10, "Recommendations", ln=True)
        pdf.set_font(font_name, "", 10)
        pdf.ln(5)

        recommendations = self._generate_recommendations(results, summary, error_distribution)
        for i, rec in enumerate(recommendations, 1):
            pdf.multi_cell(0, 7, f"{i}. {rec}")
            pdf.ln(2)

        pdf.output(filepath)
        return filepath

    def _get_unicode_font_path(self) -> Optional[str]:
        """Try to find a Unicode-capable font on the system."""
        possible_paths = [
            # macOS
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/Library/Fonts/Arial Unicode.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            # Linux
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            # Windows
            "C:/Windows/Fonts/arial.ttf",
        ]
        for p in possible_paths:
            if os.path.exists(p):
                return p
        return None

    def _generate_recommendations(
        self,
        results: List[Dict[str, Any]],
        summary: Dict[str, Any],
        error_distribution: Dict[str, Any],
    ) -> List[str]:
        """Generate improvement recommendations based on evaluation results."""
        recommendations = []

        pass_rate = summary.get("pass_rate", 0)
        total = summary.get("total", 0)
        by_group = error_distribution.get("by_group", {})
        level_stats = summary.get("level_stats", {})

        # Overall performance
        if pass_rate < 50:
            recommendations.append(
                f"Overall pass rate is low ({pass_rate}%). Consider reviewing the chatbot's "
                "prompt engineering, schema documentation, and business rules coverage."
            )
        elif pass_rate < 80:
            recommendations.append(
                f"Pass rate is moderate ({pass_rate}%). Focus on the specific error types "
                "identified below to improve accuracy."
            )
        else:
            recommendations.append(
                f"Pass rate is good ({pass_rate}%). Continue monitoring and focus on "
                "edge cases and hard questions."
            )

        # Error group recommendations
        if by_group.get("G1", 0) > 0:
            recommendations.append(
                f"G1 (Question Understanding): {by_group['G1']} errors. "
                "Improve the query rewriting/understanding prompt. Consider adding more "
                "examples of analytical task types (count, compare, rank, ratio, trend)."
            )

        if by_group.get("G2", 0) > 0:
            recommendations.append(
                f"G2 (Business Rule Mapping): {by_group['G2']} errors. "
                "Review and expand business rules documentation. Ensure all business "
                "definitions are clearly specified in the RAG knowledge base."
            )

        if by_group.get("G3", 0) > 0:
            recommendations.append(
                f"G3 (Schema Mapping): {by_group['G3']} errors. "
                "Improve schema metadata quality. Verify join maps are complete and "
                "table descriptions clearly indicate relationships."
            )

        if by_group.get("G4", 0) > 0:
            recommendations.append(
                f"G4 (Calculation Logic): {by_group['G4']} errors. "
                "Review the SQL generation prompts for aggregation rules. Add more "
                "examples of complex calculations (ratios, subqueries, window functions)."
            )

        # Level-specific recommendations
        for level, stats in level_stats.items():
            lt = stats["total"]
            lc = stats["correct"]
            if lt > 0 and lc / lt < 0.5:
                recommendations.append(
                    f"Performance on '{level}' questions is low ({lc}/{lt}). "
                    f"Focus on improving the chatbot's handling of {level.lower()}-level queries."
                )

        # Response time
        avg_time = summary.get("avg_response_time", 0)
        if avg_time > 30:
            recommendations.append(
                f"Average response time is {avg_time}s. Consider optimizing the "
                "chatbot pipeline (RAG retrieval, prompt size, model selection)."
            )

        return recommendations if recommendations else ["No specific recommendations. The chatbot is performing well."]
