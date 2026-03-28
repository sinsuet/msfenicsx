"""Controller contracts and registry helpers for proposal-layer action selection."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

import numpy as np

from optimizers.operator_pool.state import ControllerState


class OperatorController(Protocol):
    controller_id: str

    def select_operator(
        self,
        state: ControllerState,
        operator_ids: Sequence[str],
        rng: np.random.Generator,
    ) -> str: ...


def list_registered_controller_ids() -> list[str]:
    return ["random_uniform", "llm"]


def build_controller(controller_id: str) -> OperatorController:
    if controller_id == "random_uniform":
        from optimizers.operator_pool.random_controller import RandomUniformController

        return RandomUniformController()
    if controller_id == "llm":
        raise NotImplementedError("The llm controller is reserved for a later implementation phase.")
    raise KeyError(f"Unsupported operator-pool controller '{controller_id}'.")
