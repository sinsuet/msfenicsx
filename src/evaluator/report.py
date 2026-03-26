from __future__ import annotations

from typing import Any

from .constraints import evaluate_constraints
from .objectives import summarize_objectives


def _build_priority_actions(violations: list[dict[str, Any]]) -> list[str]:
    actions: list[str] = []
    for violation in violations:
        name = violation["name"]
        if name.endswith("_max_temperature"):
            component_name = name.removesuffix("_max_temperature")
            actions.append(
                f"lower {component_name} peak temperature from {violation['actual']:.4f} to <= {violation['limit']:.4f}"
            )
        elif name.endswith("_min_temperature"):
            component_name = name.removesuffix("_min_temperature")
            actions.append(
                f"raise {component_name} minimum temperature from {violation['actual']:.4f} to >= {violation['limit']:.4f}"
            )
        else:
            actions.append(
                f"adjust {name} so that {violation['actual']:.4f} satisfies {violation['op']} {violation['limit']:.4f}"
            )
    return actions


def evaluate_case(state, metrics: dict[str, Any]) -> dict[str, Any]:
    violations = evaluate_constraints(state, metrics)
    objective_summary = summarize_objectives(state, metrics)

    return {
        "feasible": len(violations) == 0,
        "violations": violations,
        "objective_summary": objective_summary,
        "priority_actions": _build_priority_actions(violations),
        "temperature_min": metrics.get("temperature_min"),
        "temperature_max": metrics.get("temperature_max"),
        "mesh": metrics.get("mesh", {}),
    }
