"""Algorithm-agnostic random controller for the shared operator pool."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from optimizers.operator_pool.decisions import ControllerDecision
from optimizers.operator_pool.state import ControllerState


class RandomUniformController:
    controller_id = "random_uniform"

    def _sample_operator_id(
        self,
        operator_ids: Sequence[str],
        rng: np.random.Generator,
    ) -> str:
        candidates = [str(operator_id) for operator_id in operator_ids]
        if not candidates:
            raise ValueError("RandomUniformController requires at least one candidate operator.")
        return candidates[int(rng.integers(0, len(candidates)))]

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
