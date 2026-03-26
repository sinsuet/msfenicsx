from __future__ import annotations

from typing import Any


def extract_metric_value(metric_name: str, metrics: dict[str, Any]) -> float:
    if metric_name == "global_max_temperature":
        return float(metrics["temperature_max"])
    if metric_name == "global_min_temperature":
        return float(metrics["temperature_min"])
    if metric_name == "mesh_num_cells":
        return float(metrics["mesh"]["num_cells"])

    parts = metric_name.split("_")
    if len(parts) >= 3 and parts[-1] == "temperature":
        component_name = "_".join(parts[:-2])
        statistic = parts[-2]
        component_summary = metrics.get("component_summary", {})
        if component_name not in component_summary:
            raise KeyError(f"Missing component metric for '{component_name}'.")
        return float(component_summary[component_name][statistic])

    raise KeyError(f"Unsupported metric name '{metric_name}'.")


def compare_constraint(actual: float, op: str, target: float) -> bool:
    if op == "<=":
        return actual <= target
    if op == ">=":
        return actual >= target
    raise ValueError(f"Unsupported constraint operator '{op}'.")


def evaluate_constraints(state, metrics: dict[str, Any]) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    for constraint in state.constraints:
        actual = extract_metric_value(constraint.name, metrics)
        satisfied = compare_constraint(actual, constraint.op, constraint.value)
        if satisfied:
            continue

        if constraint.op == "<=":
            margin = constraint.value - actual
        else:
            margin = actual - constraint.value

        violations.append(
            {
                "name": constraint.name,
                "op": constraint.op,
                "limit": float(constraint.value),
                "actual": float(actual),
                "margin": float(margin),
                "severity": "high",
            }
        )
    return violations
