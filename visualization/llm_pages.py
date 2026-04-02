"""LLM decision-page renderers for the new run tree."""

from __future__ import annotations

from pathlib import Path

from optimizers.llm_decision_summary import build_llm_decision_summaries
from optimizers.run_telemetry import load_jsonl_rows
from visualization.static_assets import dashboard_style, html_section, html_table, write_dashboard


def render_llm_pages(mode_root: str | Path) -> dict[str, Path]:
    root = Path(mode_root)
    summaries_root = root / "summaries"
    pages_root = root / "pages"
    pages_root.mkdir(parents=True, exist_ok=True)
    if not (summaries_root / "llm_decision_log.jsonl").exists():
        build_llm_decision_summaries(root)
    decision_rows = load_jsonl_rows(summaries_root / "llm_decision_log.jsonl")
    key_decisions = _load_json(summaries_root / "llm_key_decisions.json")

    decisions_page = write_dashboard(
        pages_root / "llm_decisions.html",
        "LLM Decisions",
        "<main>"
        + html_section(
            "System Prompt And Selected Operator",
            html_table(
                ["Eval", "Selected Operator", "System Prompt", "User Prompt", "Response"],
                [
                    [
                        str(row.get("evaluation_index", "")),
                        str(row.get("selected_operator_id", "")),
                        str(row.get("system_prompt", "")),
                        str(row.get("user_prompt", "")),
                        str(row.get("response_text", "")),
                    ]
                    for row in decision_rows
                ],
            ),
        )
        + "</main>",
        style=dashboard_style(),
    )
    key_decisions_page = write_dashboard(
        pages_root / "llm_key_decisions.html",
        "LLM Key Decisions",
        "<main>"
        + html_section(
            "Key Decision Triggers",
            html_table(
                ["Trigger", "Eval", "Operator", "Prompt Ref"],
                [
                    [
                        str(row.get("trigger_type", "")),
                        str(row.get("evaluation_index", "")),
                        str(row.get("selected_operator_id", "")),
                        str(row.get("prompt_ref", "")),
                    ]
                    for row in key_decisions.get("rows", [])
                ],
            ),
        )
        + "</main>",
        style=dashboard_style(),
    )
    return {
        "decisions": decisions_page,
        "key_decisions": key_decisions_page,
    }


def _load_json(path: Path) -> dict:
    import json

    return json.loads(path.read_text(encoding="utf-8"))
