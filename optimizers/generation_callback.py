"""Compact generation-level telemetry for optimizer runs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
from pymoo.core.callback import Callback
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting

from optimizers.operator_pool.domain_state import total_violation
from optimizers.problem import objective_to_minimization


class GenerationSummaryCallback(Callback):
    def __init__(
        self,
        *,
        objective_definitions: Sequence[Mapping[str, Any]] | None = None,
        objective_ids: Sequence[str] | None = None,
    ) -> None:
        super().__init__()
        self.rows: list[dict[str, Any]] = []
        self._last_history_count = 0
        if objective_definitions is None:
            derived_ids = [] if objective_ids is None else list(objective_ids)
            objective_definitions = [
                {
                    "objective_id": str(objective_id),
                    "sense": "maximize" if str(objective_id).startswith("maximize_") else "minimize",
                }
                for objective_id in derived_ids
            ]
        self.objective_definitions = [
            {
                "objective_id": str(item["objective_id"]),
                "sense": str(item.get("sense", "minimize")),
            }
            for item in objective_definitions
        ]

    def notify(self, algorithm: Any) -> None:
        pop = getattr(algorithm, "pop", None)
        if pop is None or len(pop) <= 0:
            return

        objective_matrix = np.asarray(pop.get("F"), dtype=np.float64)
        if objective_matrix.ndim == 1:
            objective_matrix = objective_matrix.reshape(1, -1)

        constraint_matrix = pop.get("G") if hasattr(pop, "get") else None
        if constraint_matrix is None:
            constraint_matrix = np.zeros((len(objective_matrix), 0), dtype=np.float64)
        constraint_matrix = np.asarray(constraint_matrix, dtype=np.float64)
        if constraint_matrix.ndim == 1:
            constraint_matrix = constraint_matrix.reshape(len(objective_matrix), -1)

        total_constraint_violation = (
            np.maximum(constraint_matrix, 0.0).sum(axis=1)
            if constraint_matrix.size
            else np.zeros(len(objective_matrix), dtype=np.float64)
        )
        feasible_mask = total_constraint_violation <= 1.0e-12
        history = list(getattr(getattr(algorithm, "problem", None), "history", []))
        new_history = history[self._last_history_count :]
        self._last_history_count = len(history)
        row = {
            "generation_index": int(max(0, int(getattr(algorithm, "n_iter", 0)))),
            "num_evaluations_so_far": int(len(history)),
            "feasible_fraction": (
                0.0 if len(objective_matrix) <= 0 else float(np.mean(feasible_mask.astype(np.float64)))
            ),
            "best_total_constraint_violation": (
                0.0 if len(total_constraint_violation) <= 0 else float(np.min(total_constraint_violation))
            ),
            "best_hot_pa_peak": self._best_objective_value(objective_matrix, "minimize_hot_pa_peak"),
            "best_cold_battery_min": self._best_objective_value(objective_matrix, "maximize_cold_battery_min"),
            "best_radiator_resource": self._best_objective_value(objective_matrix, "minimize_radiator_resource"),
            "pareto_size": self._pareto_size(objective_matrix, feasible_mask),
            "new_feasible_entries": int(sum(1 for record in new_history if bool(record.get("feasible", False)))),
            "new_pareto_entries": int(
                sum(
                    1
                    for record in _pareto_front(history, self.objective_definitions)
                    if record in new_history
                )
            ),
        }
        self.rows.append(row)

    def _best_objective_value(self, objective_matrix: np.ndarray, objective_id: str) -> float | None:
        objective_index = next(
            (
                index
                for index, definition in enumerate(self.objective_definitions)
                if definition["objective_id"] == objective_id
            ),
            None,
        )
        if objective_index is None or objective_matrix.size == 0:
            return None
        values = objective_matrix[:, objective_index]
        sense = str(self.objective_definitions[objective_index]["sense"])
        if sense == "maximize":
            return float(np.max(-values))
        return float(np.min(values))

    @staticmethod
    def _pareto_size(objective_matrix: np.ndarray, feasible_mask: np.ndarray) -> int:
        feasible_objectives = objective_matrix[feasible_mask]
        if len(feasible_objectives) <= 0:
            return 0
        fronts = NonDominatedSorting().do(feasible_objectives, only_non_dominated_front=True)
        return int(len(fronts))


def _pareto_front(
    history: Sequence[Mapping[str, Any]],
    objective_definitions: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    feasible_records = [record for record in history if bool(record.get("feasible", False))]
    pareto_front: list[Mapping[str, Any]] = []
    for candidate in feasible_records:
        dominated = False
        for incumbent in feasible_records:
            if candidate is incumbent:
                continue
            if _dominates(incumbent, candidate, objective_definitions):
                dominated = True
                break
        if not dominated:
            pareto_front.append(candidate)
    return pareto_front


def _dominates(
    candidate: Mapping[str, Any],
    incumbent: Mapping[str, Any],
    objective_definitions: Sequence[Mapping[str, Any]],
) -> bool:
    candidate_tuple = tuple(
        objective_to_minimization(
            float(candidate["objective_values"][definition["objective_id"]]),
            str(definition["sense"]),
        )
        for definition in objective_definitions
    )
    incumbent_tuple = tuple(
        objective_to_minimization(
            float(incumbent["objective_values"][definition["objective_id"]]),
            str(definition["sense"]),
        )
        for definition in objective_definitions
    )
    return all(left <= right for left, right in zip(candidate_tuple, incumbent_tuple, strict=True)) and any(
        left < right for left, right in zip(candidate_tuple, incumbent_tuple, strict=True)
    )
