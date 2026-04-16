# optimizers/compare_runs.py
"""Cross-mode comparison: Pareto overlay + summary table."""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path

import yaml

from optimizers.analytics.loaders import iter_jsonl
from optimizers.analytics.pareto import pareto_front_indices
from visualization.figures.pareto import render_pareto_front


def _extract_final_front(run_root: Path) -> list[tuple[float, float]]:
    events = list(iter_jsonl(run_root / "traces" / "evaluation_events.jsonl"))
    feasible = [e for e in events if e.get("status") == "ok" and e.get("objectives")]
    points = [
        (float(e["objectives"]["temperature_max"]), float(e["objectives"]["temperature_gradient_rms"]))
        for e in feasible
    ]
    if not points:
        return []
    idx = pareto_front_indices(points)
    return [points[i] for i in idx]


def _mode_of(run_root: Path) -> str:
    name = run_root.name
    return name.split("__", 1)[-1] if "__" in name else name


def compare_runs(*, runs: Sequence[Path], output: Path) -> None:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)

    fronts: dict[str, list[tuple[float, float]]] = {}
    rows: list[dict] = []
    for run_root in runs:
        mode = _mode_of(Path(run_root))
        front = _extract_final_front(Path(run_root))
        fronts[mode] = front
        if front:
            t_min = min(p[0] for p in front)
            g_min = min(p[1] for p in front)
            rows.append({"mode": mode, "run": str(run_root), "t_max_min": t_min, "grad_rms_min": g_min, "front_size": len(front)})
        else:
            rows.append({"mode": mode, "run": str(run_root), "t_max_min": None, "grad_rms_min": None, "front_size": 0})

    render_pareto_front(fronts=fronts, output=output / "pareto_overlay.png")

    with (output / "summary_table.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["mode", "run", "t_max_min", "grad_rms_min", "front_size"])
        writer.writeheader()
        writer.writerows(rows)

    (output / "inputs.yaml").write_text(
        yaml.safe_dump({"runs": [str(r) for r in runs]}, sort_keys=False),
        encoding="utf-8",
    )
