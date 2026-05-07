"""Algorithm-agnostic random controller for the shared operator pool."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from optimizers.operator_pool.decisions import ControllerDecision
from optimizers.operator_pool.state import ControllerState


class RandomUniformController:
    controller_id = "random_uniform"

    def __init__(self, operator_weights: Mapping[str, Any] | None = None) -> None:
        self.operator_weights = {
            str(operator_id): float(weight)
            for operator_id, weight in dict(operator_weights or {}).items()
        }

    def _sample_operator_id(
        self,
        operator_ids: Sequence[str],
        rng: np.random.Generator,
    ) -> str:
        candidates = [str(operator_id) for operator_id in operator_ids]
        if not candidates:
            raise ValueError("RandomUniformController requires at least one candidate operator.")
        probabilities = self._probabilities(candidates)
        if probabilities is not None:
            return str(rng.choice(candidates, p=probabilities))
        return candidates[int(rng.integers(0, len(candidates)))]

    def _probabilities(self, candidates: Sequence[str]) -> list[float] | None:
        if not self.operator_weights:
            return None
        weights = []
        for operator_id in candidates:
            weight = float(self.operator_weights.get(str(operator_id), 0.0))
            if weight < 0.0:
                raise ValueError(f"operator weight for {operator_id!r} must be non-negative.")
            weights.append(weight)
        total = float(sum(weights))
        if total <= 0.0:
            raise ValueError("RandomUniformController operator_weights must assign positive mass to candidates.")
        return [float(weight) / total for weight in weights]

    def select_operator(
        self,
        state: ControllerState,
        operator_ids: Sequence[str],
        rng: np.random.Generator,
    ) -> str:
        del state
        return self._sample_operator_id(operator_ids, rng)

    def select_decision(
        self,
        state: ControllerState,
        operator_ids: Sequence[str],
        rng: np.random.Generator,
    ) -> ControllerDecision:
        return ControllerDecision(selected_operator_id=self.select_operator(state, operator_ids, rng))
