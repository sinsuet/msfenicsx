"""Algorithm-agnostic shared operator-pool proposal layer."""

from optimizers.operator_pool.controllers import build_controller, list_registered_controller_ids
from optimizers.operator_pool.layout import VariableLayout, VariableSlot
from optimizers.operator_pool.models import ParentBundle
from optimizers.operator_pool.operators import (
    OperatorDefinition,
    approved_union_operator_ids_for_backbone,
    get_operator_definition,
    list_registered_operator_ids,
    native_operator_id_for_backbone,
)
from optimizers.operator_pool.random_controller import RandomUniformController
from optimizers.operator_pool.state import ControllerState
from optimizers.operator_pool.trace import ControllerTraceRow, OperatorTraceRow

__all__ = [
    "build_controller",
    "ControllerState",
    "ControllerTraceRow",
    "approved_union_operator_ids_for_backbone",
    "get_operator_definition",
    "list_registered_controller_ids",
    "list_registered_operator_ids",
    "native_operator_id_for_backbone",
    "OperatorDefinition",
    "OperatorTraceRow",
    "ParentBundle",
    "RandomUniformController",
    "VariableLayout",
    "VariableSlot",
]
