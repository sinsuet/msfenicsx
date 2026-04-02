"""Overview dashboard rendering for single-mode experiment containers."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from optimizers.experiment_index import refresh_experiment_index
from visualization.static_assets import (
    format_scalar,
    load_json,
    render_line_panel,
    render_metric_cards,
    render_text_panel,
    render_vertical_bar_panel,
    svg_document,
    svg_text,
    write_dashboard,
    write_json,
)


def render_optimizer_overview(experiment_root: str | Path) -> Path:
    root = Path(experiment_root)
    if not (root / "summaries" / "run_index.json").exists():
        from optimizers.experiment_summary import build_experiment_summaries

        build_experiment_summaries(root)
    manifest = load_json(root / "manifest.json")
    run_index = load_json(root / "summaries" / "run_index.json")
    aggregate_summary = load_json(root / "summaries" / "aggregate_summary.json")
    constraint_summary = load_json(root / "summaries" / "constraint_summary.json")
    generation_summary = load_json(root / "summaries" / "generation_summary.json")

    rows_html = "".join(
        "<tr>"
        f"<td>{int(row['seed'])}</td>"
        f"<td>{html.escape(str(row['run_id']))}</td>"
        f"<td>{int(row['num_evaluations'])}</td>"
        f"<td>{float(row['feasible_rate']):.3f}</td>"
        f"<td>{html.escape(str(row['first_feasible_eval']))}</td>"
        f"<td>{int(row['pareto_size'])}</td>"
        "</tr>"
        for row in run_index
    )
    body = (
        f"<h1>Overview: {html.escape(str(manifest['mode_id']))}</h1>"
        f"<p>Template: {html.escape(str(manifest['scenario_template_id']))}</p>"
        f"<p>Seeds: {', '.join(str(seed) for seed in manifest.get('benchmark_seeds', []))}</p>"
        "<h2>Run Index</h2>"
        "<table><thead><tr><th>Seed</th><th>Run ID</th><th>Evaluations</th><th>Feasible Rate</th><th>First Feasible</th><th>Pareto Size</th></tr></thead>"
        f"<tbody>{rows_html}</tbody></table>"
        "<h2>Aggregate Summary</h2>"
        f"<pre>{html.escape(json.dumps(aggregate_summary, indent=2))}</pre>"
        "<h2>Constraint Summary</h2>"
        f"<pre>{html.escape(json.dumps(constraint_summary, indent=2))}</pre>"
        "<h2>Generation Summary</h2>"
        f"<pre>{html.escape(json.dumps(generation_summary, indent=2))}</pre>"
    )
    dashboard_path = write_dashboard(
        root / "dashboards" / "overview.html",
        "Optimizer Overview",
        body,
        style=(
            "body{font-family:Georgia,serif;margin:32px;background:#f5f1e8;color:#1f2933}"
            "table{border-collapse:collapse;width:100%;margin:12px 0}"
            "th,td{border:1px solid #c6b89e;padding:8px;text-align:left}"
            "pre{background:#fffaf0;border:1px solid #d8ccb3;padding:12px;overflow:auto}"
        ),
    )

    figure_payload = {
        "manifest": {
            "scenario_template_id": manifest.get("scenario_template_id"),
            "mode_id": manifest.get("mode_id"),
            "benchmark_seeds": list(manifest.get("benchmark_seeds", [])),
        },
        "run_index": run_index,
        "aggregate_summary": aggregate_summary,
        "constraint_summary": constraint_summary,
        "generation_summary": generation_summary,
    }
    write_json(root / "figures" / "overview.json", figure_payload)
    (root / "figures" / "overview.svg").write_text(
        _build_overview_svg(
            manifest=manifest,
            run_index=run_index,
            aggregate_summary=aggregate_summary,
            constraint_summary=constraint_summary,
            generation_summary=generation_summary,
        ),
        encoding="utf-8",
    )
    refresh_experiment_index(root)
    return dashboard_path


def _build_overview_svg(
    *,
    manifest: dict[str, Any],
    run_index: list[dict[str, Any]],
    aggregate_summary: dict[str, Any],
    constraint_summary: dict[str, Any],
    generation_summary: dict[str, Any],
) -> str:
    feasible_mean = _metric_mean(aggregate_summary, "feasible_rate")
    pareto_mean = _metric_mean(aggregate_summary, "pareto_size")
    cards = [
        ("Runs", str(int(aggregate_summary.get("num_runs", len(run_index))))),
        ("Mean feasible", _format_percent(feasible_mean)),
        ("Mean pareto", format_scalar(pareto_mean)),
        ("No feasible runs", str(len(aggregate_summary.get("no_feasible_solution_runs", [])))),
    ]
    seed_feasible_items = [
        (f"seed-{int(row['seed'])}", float(row["feasible_rate"]))
        for row in run_index
    ]
    seed_cv_items = [
        (f"seed-{int(row['seed'])}", row.get("best_total_cv_among_infeasible"))
        for row in run_index
    ]
    generation_feasible_points = [
        (float(row["generation_index"]), row.get("mean_feasible_fraction"))
        for row in generation_summary.get("generations", [])
    ]
    generation_cv_points = [
        (float(row["generation_index"]), row.get("mean_best_total_constraint_violation"))
        for row in generation_summary.get("generations", [])
    ]
    constraint_rows = [
        (
            f"{constraint_id}: activation={summary.get('activation_frequency', 0.0):.2f}"
            f" mean={summary.get('mean_violation', 0.0):.3f}"
        )
        for constraint_id, summary in sorted(constraint_summary.get("per_constraint", {}).items())
    ]
    body = (
        svg_text(48.0, 58.0, "NSGA-II Experiment Overview", fill="#1d2a33", size=28, weight="700")
        + svg_text(
            48.0,
            86.0,
            f"{manifest.get('scenario_template_id')} | {manifest.get('mode_id')}",
            fill="#5a6775",
            size=15,
            weight="600",
        )
        + render_metric_cards(
            cards,
            x=48.0,
            y=112.0,
            width=1104.0,
            card_height=102.0,
            fill="#fffaf2",
            stroke="#d8ccb8",
        )
        + render_vertical_bar_panel(
            title="Feasible rate by seed",
            items=seed_feasible_items,
            x=48.0,
            y=246.0,
            width=350.0,
            height=256.0,
            panel_fill="#fffaf2",
            panel_stroke="#d8ccb8",
            bar_fill="#a75b35",
            value_formatter=_format_percent,
        )
        + render_vertical_bar_panel(
            title="Best total CV among infeasible",
            items=seed_cv_items,
            x=425.0,
            y=246.0,
            width=350.0,
            height=256.0,
            panel_fill="#fffaf2",
            panel_stroke="#d8ccb8",
            bar_fill="#6c8c7b",
        )
        + render_text_panel(
            title="Constraint pulse",
            rows=constraint_rows,
            x=802.0,
            y=246.0,
            width=350.0,
            height=256.0,
            panel_fill="#fffaf2",
            panel_stroke="#d8ccb8",
        )
        + render_line_panel(
            title="Generation feasible fraction",
            points=generation_feasible_points,
            x=48.0,
            y=530.0,
            width=540.0,
            height=220.0,
            panel_fill="#fffaf2",
            panel_stroke="#d8ccb8",
            line_color="#8a3f2d",
            value_formatter=_format_percent,
        )
        + render_line_panel(
            title="Generation best total CV",
            points=generation_cv_points,
            x=612.0,
            y=530.0,
            width=540.0,
            height=220.0,
            panel_fill="#fffaf2",
            panel_stroke="#d8ccb8",
            line_color="#476c5e",
        )
    )
    return svg_document(
        title="NSGA-II experiment overview",
        width=1200,
        height=780,
        body=body,
        background="#f4efe4",
    )


def _metric_mean(aggregate_summary: dict[str, Any], metric_name: str) -> float | None:
    metrics = dict(aggregate_summary.get("metrics", {}))
    value = metrics.get(metric_name, {})
    if not isinstance(value, dict):
        return None
    raw_mean = value.get("mean")
    return None if raw_mean is None else float(raw_mean)


def _format_percent(value: float | int | None) -> str:
    if value is None:
        return "NA"
    return f"{float(value) * 100.0:.1f}%"
