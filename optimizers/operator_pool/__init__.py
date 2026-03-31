"""Algorithm-agnostic shared operator-pool proposal layer."""

from optimizers.operator_pool.controllers import build_controller, list_registered_controller_ids, select_controller_decision
from optimizers.operator_pool.decisions import ControllerDecision
from optimizers.operator_pool.layout import VariableLayout, VariableSlot
from optimizers.operator_pool.llm_controller import LLMOperatorController
from optimizers.operator_pool.models import ParentBundle
from optimizers.operator_pool.operators import (
    OperatorDefinition,
    approved_union_operator_ids_for_backbone,
    get_operator_definition,
    list_registered_operator_ids,
    native_operator_id_for_backbone,
)
from optimizers.operator_pool.random_controller import RandomUniformController
from optimizers.operator_pool.reflection import summarize_operator_history
from optimizers.operator_pool.state import ControllerState
from optimizers.operator_pool.state_builder import build_controller_state
from optimizers.operator_pool.trace import ControllerTraceRow, OperatorTraceRow

__all__ = [
    "build_controller",
    "build_controller_state",
    "ControllerDecision",
    "ControllerState",
    "ControllerTraceRow",
    "LLMOperatorController",
    "approved_union_operator_ids_for_backbone",
    "get_operator_definition",
    "list_registered_controller_ids",
    "list_registered_operator_ids",
    "native_operator_id_for_backbone",
    "OperatorDefinition",
    "OperatorTraceRow",
    "ParentBundle",
    "RandomUniformController",
    "select_controller_decision",
    "summarize_operator_history",
    "VariableLayout",
    "VariableSlot",
]
