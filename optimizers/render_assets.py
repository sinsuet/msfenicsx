# optimizers/render_assets.py
"""Read traces, compute analytics, render figures and tables."""

from __future__ import annotations

import csv
from pathlib import Path

from optimizers.analytics.heatmap import operator_phase_heatmap
from optimizers.analytics.loaders import iter_jsonl
from optimizers.analytics.rollups import rollup_per_generation
from visualization.figures.hypervolume import render_hypervolume_progress
from visualization.figures.operator_heatmap import render_operator_heatmap

REFERENCE_POINT = (400.0, 20.0)   # § 5 reference point for s1_typical


def render_run_assets(run_root: Path, *, hires: bool = False) -> None:
    run_root = Path(run_root)
    traces = run_root / "traces"
    analytics = run_root / "analytics"
    figures = run_root / "figures"
    analytics.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    events = list(iter_jsonl(traces / "evaluation_events.jsonl"))
    summaries = rollup_per_generation(events, reference_point=REFERENCE_POINT)

    with (analytics / "hypervolume.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["generation", "hypervolume"])
        for summary in summaries:
            writer.writerow([summary["generation"], summary["hypervolume"]])

    render_hypervolume_progress(
        series={run_root.name.split("__", 1)[-1]: [(s["generation"], s["hypervolume"]) for s in summaries]},
        output=figures / "hypervolume_progress.png",
        hires=hires,
    )

    operator_rows = list(iter_jsonl(traces / "operator_trace.jsonl"))
    controller_rows = list(iter_jsonl(traces / "controller_trace.jsonl"))
    grid = operator_phase_heatmap(operator_rows, controller_rows)

    with (analytics / "operator_phase_heatmap.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        phases: list[str] = []
        for counts in grid.values():
            for phase in counts:
                if phase not in phases:
                    phases.append(phase)
        writer.writerow(["operator", *phases])
        for operator, counts in sorted(grid.items()):
            writer.writerow([operator, *(counts.get(p, 0) for p in phases)])

    if grid:
        render_operator_heatmap(grid=grid, output=figures / "operator_phase_heatmap.png", hires=hires)
