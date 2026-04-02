"""Deterministic LLM summary reports for the new run tree."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from optimizers.llm_decision_summary import build_llm_decision_summaries
from optimizers.llm_summary import build_mode_llm_summaries
from visualization.static_assets import dashboard_style, html_section, write_dashboard


def render_llm_reports(mode_root: str | Path, comparison_root: str | Path | None) -> dict[str, Path]:
    root = Path(mode_root)
    reports_root = root / "reports"
    reports_root.mkdir(parents=True, exist_ok=True)
    summaries_root = root / "summaries"
    if not (summaries_root / "llm_decision_log.jsonl").exists():
        build_llm_decision_summaries(root)
    if not (summaries_root / "llm_runtime_summary.json").exists():
        build_mode_llm_summaries(root)

    runtime_summary = _load_json(summaries_root / "llm_runtime_summary.json")
    decision_summary = _load_json(summaries_root / "llm_decision_summary.json")
    key_decisions = _load_json(summaries_root / "llm_key_decisions.json")
    markdown = _build_markdown_report(root.name, runtime_summary, decision_summary, key_decisions)
    markdown_path = reports_root / "llm_experiment_summary.md"
    markdown_path.write_text(markdown, encoding="utf-8")
    html_path = write_dashboard(
        reports_root / "llm_experiment_summary.html",
        "LLM Experiment Summary",
        "<main>"
        + html_section("Summary Table", _markdown_table_to_html(markdown))
        + html_section("Key Improvement Points", "<p>Key Improvement Points</p>")
        + html_section("Risk", "<p>Risk</p>")
        + "</main>",
        style=dashboard_style(),
    )

    outputs = {
        "markdown": markdown_path,
        "html": html_path,
    }
    if comparison_root is not None:
        comparison_reports_root = Path(comparison_root) / "reports"
        comparison_reports_root.mkdir(parents=True, exist_ok=True)
        comparison_markdown_path = comparison_reports_root / "llm_vs_union_vs_raw_summary.md"
        comparison_markdown_path.write_text(markdown, encoding="utf-8")
        outputs["comparison_markdown"] = comparison_markdown_path
    return outputs


def _build_markdown_report(
    mode_id: str,
    runtime_summary: dict[str, Any],
    decision_summary: dict[str, Any],
    key_decisions: dict[str, Any],
) -> str:
    lines = [
        "# LLM Experiment Summary",
        "",
        "| Mode | Requests | Responses | Fallbacks | Decisions |",
        "| --- | ---: | ---: | ---: | ---: |",
        (
            f"| {mode_id} | {runtime_summary.get('request_count', 0)} | "
            f"{runtime_summary.get('response_count', 0)} | {runtime_summary.get('fallback_count', 0)} | "
            f"{decision_summary.get('decision_count', 0)} |"
        ),
        "",
        "## Key Improvement Points",
        "",
        f"- First feasible and Pareto-expansion triggers detected: {key_decisions.get('row_count', 0)}",
        f"- Dominant selected operators: {', '.join(sorted(dict(decision_summary.get('operator_counts', {})).keys())) or 'n/a'}",
        "",
        "## Risk",
        "",
        f"- Fallback selections: {decision_summary.get('fallback_selection_count', 0)}",
        f"- Invalid responses observed: {runtime_summary.get('invalid_response_count', 0)}",
    ]
    return "\n".join(lines) + "\n"


def _markdown_table_to_html(markdown: str) -> str:
    table_lines = [line for line in markdown.splitlines() if line.startswith("|")]
    if len(table_lines) < 3:
        return "<p>No table</p>"
    headers = [item.strip() for item in table_lines[0].strip("|").split("|")]
    values = [item.strip() for item in table_lines[2].strip("|").split("|")]
    rows = ["<tr>" + "".join(f"<th>{header}</th>" for header in headers) + "</tr>"]
    rows.append("<tr>" + "".join(f"<td>{value}</td>" for value in values) + "</tr>")
    return "<table>" + "".join(rows) + "</table>"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
