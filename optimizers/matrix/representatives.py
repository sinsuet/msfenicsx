from __future__ import annotations

from collections import defaultdict
from math import sqrt
from typing import Iterable


def select_best_hv_representatives(rows: Iterable[dict[str, str]]) -> list[dict[str, float | str]]:
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("status") != "completed":
            continue
        if not str(row.get("final_hypervolume", "")).strip():
            continue
        groups[(row["scenario_id"], row["method_id"])].append(row)

    selected: list[dict[str, float | str]] = []
    for (scenario_id, method_id), group_rows in sorted(groups.items()):
        best = max(group_rows, key=lambda row: float(row["final_hypervolume"]))
        selected.append(
            {
                "scenario_id": scenario_id,
                "method_id": method_id,
                "run_root": best["run_root"],
                "final_hypervolume": float(best["final_hypervolume"]),
            }
        )
    return selected


def select_knee_point(points: Iterable[dict[str, str]]) -> str:
    candidates = list(points)
    temps = [float(point["temperature_max"]) for point in candidates]
    grads = [float(point["gradient_rms"]) for point in candidates]
    temp_min, temp_max = min(temps), max(temps)
    grad_min, grad_max = min(grads), max(grads)

    def score(point: dict[str, str]) -> float:
        temp = _scale(float(point["temperature_max"]), temp_min, temp_max)
        grad = _scale(float(point["gradient_rms"]), grad_min, grad_max)
        return sqrt(temp * temp + grad * grad)

    return str(min(candidates, key=score)["candidate_id"])


def plan_compare_bundles(representatives: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    by_scenario: dict[str, dict[str, str]] = defaultdict(dict)
    for row in representatives:
        by_scenario[row["scenario_id"]][row["method_id"]] = row["run_root"]
    plans: list[dict[str, str]] = []
    for scenario_id, methods in sorted(by_scenario.items()):
        pairs = [("nsga2_raw", "nsga2_union")]
        pairs.extend(("nsga2_union", method_id) for method_id in sorted(methods) if method_id.startswith("nsga2_llm_"))
        for baseline, candidate in pairs:
            if baseline not in methods or candidate not in methods:
                continue
            plans.append(
                {
                    "scenario_id": scenario_id,
                    "baseline_run": methods[baseline],
                    "candidate_run": methods[candidate],
                    "compare_id": f"{scenario_id}__{baseline}__vs__{candidate}",
                }
            )
    return plans


def _scale(value: float, minimum: float, maximum: float) -> float:
    if maximum == minimum:
        return 0.0
    return (value - minimum) / (maximum - minimum)
