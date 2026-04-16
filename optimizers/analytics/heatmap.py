"""Operator x controller-phase usage grid."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any


def operator_phase_heatmap(
    operator_rows: Iterable[dict[str, Any]],
    controller_rows: Iterable[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    """Build `{operator: {phase: count}}` indexed via decision_id."""
    phase_by_decision: dict[str, str] = {
        str(row["decision_id"]): str(row.get("phase", "n/a"))
        for row in controller_rows
        if row.get("decision_id")
    }
    grid: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for op_row in operator_rows:
        operator = str(op_row["operator_name"])
        decision_id = op_row.get("decision_id")
        phase = phase_by_decision.get(str(decision_id), "n/a") if decision_id else "n/a"
        grid[operator][phase] += 1
    return {op: dict(counts) for op, counts in grid.items()}
