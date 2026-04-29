from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean, median, stdev
from typing import Iterable

import numpy as np


def summarize_outcomes(rows: Iterable[dict[str, str]], *, metric: str) -> list[dict[str, float | int | str]]:
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[(row["scenario_id"], row["method_id"])].append(row)
    summaries: list[dict[str, float | int | str]] = []
    for (scenario_id, method_id), group_rows in sorted(groups.items()):
        values = [float(row[metric]) for row in group_rows if str(row.get(metric, "")).strip()]
        feasible_values = [_is_true(row.get("feasible", "false")) for row in group_rows]
        if not values:
            continue
        summaries.append(
            {
                "scenario_id": scenario_id,
                "method_id": method_id,
                "metric": metric,
                "n_runs": len(group_rows),
                "median": float(median(values)),
                "q1": float(np.quantile(values, 0.25)),
                "q3": float(np.quantile(values, 0.75)),
                "mean": float(mean(values)),
                "std": float(stdev(values)) if len(values) >= 2 else 0.0,
                "best": float(min(values)),
                "worst": float(max(values)),
                "feasible_count": int(sum(feasible_values)),
                "feasible_rate": float(sum(feasible_values) / max(1, len(group_rows))),
            }
        )
    return summaries


def paired_differences(
    rows: Iterable[dict[str, str]],
    *,
    baseline_method: str,
    candidate_method: str,
    metric: str,
) -> list[dict[str, float | str]]:
    values: dict[tuple[str, str, str], float] = {}
    for row in rows:
        if row["method_id"] not in {baseline_method, candidate_method}:
            continue
        value = str(row.get(metric, "")).strip()
        if not value:
            continue
        key = (row["scenario_id"], row["replicate_seed"], row["method_id"])
        values[key] = float(value)
    outputs: list[dict[str, float | str]] = []
    scenario_seed_pairs = sorted({(scenario_id, seed) for scenario_id, seed, _ in values})
    for scenario_id, replicate_seed in scenario_seed_pairs:
        baseline_key = (scenario_id, replicate_seed, baseline_method)
        candidate_key = (scenario_id, replicate_seed, candidate_method)
        if baseline_key not in values or candidate_key not in values:
            continue
        baseline_value = values[baseline_key]
        candidate_value = values[candidate_key]
        outputs.append(
            {
                "scenario_id": scenario_id,
                "replicate_seed": replicate_seed,
                "baseline_method": baseline_method,
                "candidate_method": candidate_method,
                "baseline_value": baseline_value,
                "candidate_value": candidate_value,
                "difference": candidate_value - baseline_value,
            }
        )
    return outputs


def _is_true(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def aggregate_matrix(index_path: str | Path, *, output_root: str | Path) -> list[Path]:
    from optimizers.matrix.index import read_run_index

    rows = read_run_index(index_path)
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for metric in ("best_temperature_max", "best_gradient_rms", "final_hypervolume"):
        summary_rows = summarize_outcomes(rows, metric=metric)
        output = root / f"{metric}_summary.csv"
        _write_dict_rows(output, summary_rows)
        outputs.append(output)
    return outputs


def _write_dict_rows(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("\n", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
