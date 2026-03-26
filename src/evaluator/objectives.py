from __future__ import annotations

from typing import Any

from .constraints import extract_metric_value


def summarize_objectives(state, metrics: dict[str, Any]) -> dict[str, float]:
    summary: dict[str, float] = {}
    for objective in state.objectives:
        summary[objective.name] = extract_metric_value(objective.name, metrics)
    return summary
