"""LLM-specific dashboard rendering for experiment containers."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from optimizers.experiment_index import refresh_experiment_index
from visualization.static_assets import (
    format_scalar,
    load_json,
    render_horizontal_bar_panel,
    render_metric_cards,
    render_text_panel,
    svg_document,
    svg_text,
    write_dashboard,
    write_json,
)


def render_llm_dashboard(experiment_root: str | Path) -> Path:
    root = Path(experiment_root)
    runtime_summary = load_json(root / "summaries" / "llm_runtime_summary.json")
    decision_summary = load_json(root / "summaries" / "llm_decision_summary.json")
    prompt_summary = load_json(root / "summaries" / "llm_prompt_summary.json")
    reflection_path = root / "summaries" / "llm_reflection_summary.json"
    reflection_summary = None if not reflection_path.exists() else load_json(reflection_path)

    body = (
        "<h1>LLM Dashboard</h1>"
        "<h2>Runtime Summary</h2>"
        f"<pre>{html.escape(json.dumps(runtime_summary, indent=2))}</pre>"
        "<h2>Decision Summary</h2>"
        f"<pre>{html.escape(json.dumps(decision_summary, indent=2))}</pre>"
        "<h2>Prompt Summary</h2>"
        f"<pre>{html.escape(json.dumps(prompt_summary, indent=2))}</pre>"
    )
    if reflection_summary is not None:
        body += "<h2>Reflection Summary</h2>" f"<pre>{html.escape(json.dumps(reflection_summary, indent=2))}</pre>"
    dashboard_path = write_dashboard(
        root / "dashboards" / "llm.html",
        "LLM Dashboard",
        body,
        style=(
            "body{font-family:Georgia,serif;margin:32px;background:#f3efe3;color:#202c35}"
            "pre{background:#fffaf0;border:1px solid #d7cdb7;padding:12px;overflow:auto}"
        ),
    )

    figure_payload = {
        "llm_runtime_summary": runtime_summary,
        "llm_decision_summary": decision_summary,
        "llm_prompt_summary": prompt_summary,
        "llm_reflection_summary": reflection_summary,
    }
    write_json(root / "figures" / "llm.json", figure_payload)
    (root / "figures" / "llm.svg").write_text(
        _build_llm_svg(
            runtime_summary=runtime_summary,
            decision_summary=decision_summary,
            prompt_summary=prompt_summary,
            reflection_summary=reflection_summary,
        ),
        encoding="utf-8",
    )
    refresh_experiment_index(root)
    return dashboard_path


def _build_llm_svg(
    *,
    runtime_summary: dict[str, Any],
    decision_summary: dict[str, Any],
    prompt_summary: dict[str, Any],
    reflection_summary: dict[str, Any] | None,
) -> str:
    cards = [
        ("Requests", str(int(runtime_summary.get("request_count", 0)))),
        ("Responses", str(int(runtime_summary.get("response_count", 0)))),
        ("Fallbacks", str(int(runtime_summary.get("fallback_count", 0)))),
        ("Elapsed total (s)", format_scalar(runtime_summary.get("elapsed_seconds_total"))),
    ]
    operator_items = [
        (operator_id, float(count))
        for operator_id, count in sorted(
            dict(decision_summary.get("operator_counts", {})).items(),
            key=lambda item: (-int(item[1]), str(item[0])),
        )
    ]
    phase_items = [
        (phase, float(count))
        for phase, count in sorted(
            dict(decision_summary.get("phase_counts", {})).items(),
            key=lambda item: (-int(item[1]), str(item[0])),
        )
    ]
    prompt_rows = [
        f"provider={runtime_summary.get('provider')} model={runtime_summary.get('model')}",
        f"capability={runtime_summary.get('capability_profile')} perf={runtime_summary.get('performance_profile')}",
        (
            f"avg candidates={float(prompt_summary.get('avg_candidate_operator_count', 0.0)):.2f}"
            f" | mean system chars={float(prompt_summary.get('mean_system_prompt_length', 0.0)):.1f}"
        ),
        (
            f"mean user chars={float(prompt_summary.get('mean_user_prompt_length', 0.0)):.1f}"
            f" | retries={int(runtime_summary.get('retry_count', 0))}"
        ),
    ]
    if reflection_summary is not None:
        prompt_rows.append(f"reflection rows={int(reflection_summary.get('reflection_count', 0))}")
    body = (
        svg_text(48.0, 58.0, "LLM Controller Runtime", fill="#20303b", size=28, weight="700")
        + svg_text(48.0, 86.0, "OpenAI-compatible runtime and decision summary", fill="#5a6775", size=15, weight="600")
        + render_metric_cards(
            cards,
            x=48.0,
            y=112.0,
            width=1104.0,
            card_height=102.0,
            fill="#fff9f1",
            stroke="#d8ccb8",
        )
        + render_horizontal_bar_panel(
            title="Selected operator counts",
            items=operator_items,
            x=48.0,
            y=246.0,
            width=540.0,
            height=248.0,
            panel_fill="#fff9f1",
            panel_stroke="#d8ccb8",
            bar_fill="#8d5338",
            value_formatter=lambda value: str(int(value)),
        )
        + render_horizontal_bar_panel(
            title="Phase counts",
            items=phase_items,
            x=612.0,
            y=246.0,
            width=540.0,
            height=248.0,
            panel_fill="#fff9f1",
            panel_stroke="#d8ccb8",
            bar_fill="#567a6a",
            value_formatter=lambda value: str(int(value)),
        )
        + render_text_panel(
            title="Prompt and runtime notes",
            rows=prompt_rows,
            x=48.0,
            y=522.0,
            width=1104.0,
            height=186.0,
            panel_fill="#fff9f1",
            panel_stroke="#d8ccb8",
        )
    )
    return svg_document(
        title="LLM dashboard figure",
        width=1200,
        height=736,
        body=body,
        background="#f3ede2",
    )
