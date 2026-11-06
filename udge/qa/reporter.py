"""Validation reporter for generating JSON and Markdown audit reports."""
import json
from pathlib import Path
from udge.core.models import ValidationReport

class ValidationReporter:
    """Generates machine-readable and human-readable QA audit reports."""

    def save_json(self, report: ValidationReport, output_path: Path) -> Path:
        """Saves validation report as formatted JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = report.model_dump(mode="json")
        output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return output_path

    def save_markdown(self, report: ValidationReport, output_path: Path) -> Path:
        """Saves validation report as GitHub-Flavored Markdown."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        status_badge = "✅ PASSED" if report.passed else "❌ FAILED"
        lines = [
            "# UDGE Document Validation & QA Report",
            "",
            f"**Status**: {status_badge}  ",
            f"**Summary**: {report.summary}  ",
            f"**Date**: {report.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
            "",
            "## Summary Metrics",
            f"- **Total Rules Checked**: {report.total_checks}",
            f"- **Errors (Blockers)**: {len(report.errors)}",
            f"- **Warnings**: {len(report.warnings)}",
            f"- **Data Gap Notices**: {len(report.info)}",
            ""
        ]

        if report.errors:
            lines.append("## ❌ Errors")
            lines.append("| Code | Message | Section |")
            lines.append("| :--- | :--- | :--- |")
            for e in report.errors:
                sec = e.section_id or "General"
                lines.append(f"| `{e.code}` | {e.message} | `{sec}` |")
            lines.append("")

        if report.warnings:
            lines.append("## ⚠️ Warnings")
            lines.append("| Code | Message | Section |")
            lines.append("| :--- | :--- | :--- |")
            for w in report.warnings:
                sec = w.section_id or "General"
                lines.append(f"| `{w.code}` | {w.message} | `{sec}` |")
            lines.append("")

        if report.info:
            lines.append("## ℹ️ Missing Information & Gaps")
            lines.append("| Code | Message | Section |")
            lines.append("| :--- | :--- | :--- |")
            for i in report.info:
                sec = i.section_id or "General"
                lines.append(f"| `{i.code}` | {i.message} | `{sec}` |")
            lines.append("")

        lines.append("---")
        lines.append("*Generated automatically by Universal Document Generation Engine (UDGE) QA Agent.*")

        output_path.write_text("\n".join(lines), encoding="utf-8")
        return output_path
