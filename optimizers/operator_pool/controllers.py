"""Controller contracts and registry helpers for proposal-layer action selection."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

import numpy as np

from optimizers.operator_pool.decisions import ControllerDecision
from optimizers.operator_pool.state import ControllerState


class OperatorController(Protocol):
    controller_id: str

    def select_operator(
        self,
        state: ControllerState,
        operator_ids: Sequence[str],
        rng: np.random.Generator,
    ) -> str: ...

    def select_decision(
        self,
        state: ControllerState,
        operator_ids: Sequence[str],
        rng: np.random.Generator,
    ) -> ControllerDecision: ...


def list_registered_controller_ids() -> list[str]:
    return ["random_uniform", "llm"]


def build_controller(controller_id: str, controller_parameters: dict[str, Any] | None = None) -> OperatorController:
    if controller_id == "random_uniform":
        from optimizers.operator_pool.random_controller import RandomUniformController

        return RandomUniformController()
    if controller_id == "llm":
        from optimizers.operator_pool.llm_controller import LLMOperatorController

        if controller_parameters is None:
            raise ValueError("The llm controller requires controller_parameters.")
        return LLMOperatorController(controller_parameters=controller_parameters)
    raise KeyError(f"Unsupported operator-pool controller '{controller_id}'.")


def select_controller_decision(
    controller: OperatorController,
    state: ControllerState,
    operator_ids: Sequence[str],
    rng: np.random.Generator,
) -> ControllerDecision:
    if hasattr(controller, "select_decision"):
        return controller.select_decision(state, operator_ids, rng)
    return ControllerDecision(selected_operator_id=controller.select_operator(state, operator_ids, rng))
