"""Mechanism dashboard rendering for union and LLM experiment containers."""

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


def render_controller_mechanism(experiment_root: str | Path) -> Path:
    root = Path(experiment_root)
    controller_summary = load_json(root / "summaries" / "controller_trace_summary.json")
    operator_summary = load_json(root / "summaries" / "operator_summary.json")
    regime_summary = load_json(root / "summaries" / "regime_operator_summary.json")

    operator_rows = "".join(
        "<tr>"
        f"<td>{html.escape(operator_id)}</td>"
        f"<td>{int(summary.get('selection_count', 0))}</td>"
        f"<td>{int(summary.get('proposal_count', 0))}</td>"
        f"<td>{int(summary.get('feasible_entry_count', 0))}</td>"
        f"<td>{int(summary.get('feasible_preservation_count', 0))}</td>"
        f"<td>{float(summary.get('avg_total_violation_delta', 0.0)):.4f}</td>"
        "</tr>"
        for operator_id, summary in sorted(operator_summary.items())
    )
    body = (
        "<h1>Controller Mechanism</h1>"
        "<h2>Controller Trace Summary</h2>"
        f"<pre>{html.escape(json.dumps(controller_summary, indent=2))}</pre>"
        "<h2>Operator Summary</h2>"
        "<table><thead><tr><th>Operator</th><th>Selections</th><th>Proposals</th><th>Feasible Entries</th><th>Feasible Preservation</th><th>Mean Violation Delta</th></tr></thead>"
        f"<tbody>{operator_rows}</tbody></table>"
        "<h2>Regime Operator Summary</h2>"
        f"<pre>{html.escape(json.dumps(regime_summary, indent=2))}</pre>"
    )
    dashboard_path = write_dashboard(
        root / "dashboards" / "mechanism.html",
        "Controller Mechanism",
        body,
        style=(
            "body{font-family:Georgia,serif;margin:32px;background:#f7f2e7;color:#23303b}"
            "table{border-collapse:collapse;width:100%;margin:12px 0}"
            "th,td{border:1px solid #c8bea7;padding:8px;text-align:left}"
            "pre{background:#fffaf2;border:1px solid #d9cfba;padding:12px;overflow:auto}"
        ),
    )

    figure_payload = {
        "controller_trace_summary": controller_summary,
        "operator_summary": operator_summary,
        "regime_operator_summary": regime_summary,
    }
    write_json(root / "figures" / "mechanism.json", figure_payload)
    (root / "figures" / "mechanism.svg").write_text(
        _build_mechanism_svg(
            controller_summary=controller_summary,
            operator_summary=operator_summary,
            regime_summary=regime_summary,
        ),
        encoding="utf-8",
    )
    refresh_experiment_index(root)
    return dashboard_path


def _build_mechanism_svg(
    *,
    controller_summary: dict[str, Any],
    operator_summary: dict[str, dict[str, Any]],
    regime_summary: dict[str, Any],
) -> str:
    aggregate = dict(controller_summary.get("aggregate", {}))
    prefeasible = dict(controller_summary.get("prefeasible", {}))
    cards = [
        ("Decisions", str(int(aggregate.get("decision_count", 0)))),
        ("Fallbacks", str(int(aggregate.get("fallback_count", 0)))),
        ("Valid controller", str(int(aggregate.get("llm_valid_count", 0)))),
        ("Forced resets", str(int(prefeasible.get("forced_reset_count", 0)))),
    ]
    selection_items = [
        (operator_id, float(summary.get("selection_count", 0)))
        for operator_id, summary in sorted(
            operator_summary.items(),
            key=lambda item: (-int(item[1].get("selection_count", 0)), str(item[0])),
        )
    ]
    violation_items = [
        (operator_id, abs(float(summary.get("avg_total_violation_delta", 0.0))))
        for operator_id, summary in sorted(
            operator_summary.items(),
            key=lambda item: abs(float(item[1].get("avg_total_violation_delta", 0.0))),
            reverse=True,
        )
    ]
    regime_rows = [
        (
            f"{row['phase']} | {row['dominant_constraint_family']} | {row['operator_id']}"
            f" | proposals={int(row['proposal_count'])} | mean_dcv={float(row['mean_total_violation_delta']):.3f}"
        )
        for row in regime_summary.get("rows", [])[:8]
    ]
    body = (
        svg_text(48.0, 58.0, "Controller Mechanism", fill="#20303b", size=28, weight="700")
        + svg_text(48.0, 86.0, "Shared union action space summary", fill="#5a6775", size=15, weight="600")
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
            title="Operator selections",
            items=selection_items,
            x=48.0,
            y=246.0,
            width=540.0,
            height=248.0,
            panel_fill="#fff9f1",
            panel_stroke="#d8ccb8",
            bar_fill="#8c5a3a",
            value_formatter=lambda value: str(int(value)),
        )
        + render_horizontal_bar_panel(
            title="Absolute mean violation delta",
            items=violation_items,
            x=612.0,
            y=246.0,
            width=540.0,
            height=248.0,
            panel_fill="#fff9f1",
            panel_stroke="#d8ccb8",
            bar_fill="#557a6b",
            value_formatter=format_scalar,
        )
        + render_text_panel(
            title="Regime / operator highlights",
            rows=regime_rows,
            x=48.0,
            y=522.0,
            width=1104.0,
            height=210.0,
            panel_fill="#fff9f1",
            panel_stroke="#d8ccb8",
        )
    )
    return svg_document(
        title="Controller mechanism figure",
        width=1200,
        height=760,
        body=body,
        background="#f3ede2",
    )
