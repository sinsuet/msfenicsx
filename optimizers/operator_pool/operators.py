"""Approved union-action registry for numeric decision-vector proposals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from optimizers.operator_pool.layout import VariableLayout
from optimizers.operator_pool.models import ParentBundle
from optimizers.operator_pool.state import ControllerState


ProposalFn = Callable[[ParentBundle, ControllerState, VariableLayout, np.random.Generator], np.ndarray]


APPROVED_SHARED_OPERATOR_IDS = (
    "sbx_pm_global",
    "local_refine",
    "hot_pair_to_sink",
    "hot_pair_separate",
    "battery_to_warm_zone",
    "radiator_align_hot_pair",
    "radiator_expand",
    "radiator_contract",
)

APPROVED_UNION_OPERATOR_IDS = ("native_sbx_pm", *APPROVED_SHARED_OPERATOR_IDS)

APPROVED_NATIVE_OPERATOR_IDS_BY_BACKBONE = {
    ("genetic", "nsga2"): "native_sbx_pm",
    ("genetic", "nsga3"): "native_sbx_pm",
    ("genetic", "ctaea"): "native_sbx_pm",
    ("genetic", "rvea"): "native_sbx_pm",
    ("decomposition", "moead"): "native_moead",
    ("swarm", "cmopso"): "native_cmopso",
}


@dataclass(frozen=True, slots=True)
class OperatorDefinition:
    operator_id: str
    propose: ProposalFn


def _copy_primary(parents: ParentBundle) -> np.ndarray:
    return np.array(parents.primary, dtype=np.float64, copy=True)


def _index(layout: VariableLayout, variable_id: str) -> int:
    return layout.index_of(variable_id)


def _value(vector: np.ndarray, layout: VariableLayout, variable_id: str) -> float:
    return float(vector[_index(layout, variable_id)])


def _set_clipped(vector: np.ndarray, layout: VariableLayout, variable_id: str, value: float) -> None:
    slot = layout.slot_for(variable_id)
    vector[slot.index] = min(max(float(value), slot.lower_bound), slot.upper_bound)


def _resolve_native_parameters(state: ControllerState) -> tuple[float, float, float, float | None]:
    native_parameters = state.metadata.get("native_parameters", {})
    crossover = native_parameters.get("crossover", {})
    mutation = native_parameters.get("mutation", {})
    eta_c = float(crossover.get("eta", 15.0))
    prob_c = float(crossover.get("prob", 0.9))
    eta_m = float(mutation.get("eta", 20.0))
    prob_var = mutation.get("prob_var")
    return eta_c, prob_c, eta_m, None if prob_var is None else float(prob_var)


def _sbx_pm_numeric(
    *,
    parents: ParentBundle,
    variable_layout: VariableLayout,
    rng: np.random.Generator,
    eta_c: float,
    crossover_prob: float,
    eta_m: float,
    mutation_prob_var: float | None,
) -> np.ndarray:
    primary = np.array(parents.primary, dtype=np.float64, copy=False)
    secondary = np.array(parents.secondary, dtype=np.float64, copy=False)
    child = primary.copy()

    if float(rng.random()) < crossover_prob:
        for index in range(variable_layout.vector_size):
            lower_bound = float(variable_layout.lower_bounds[index])
            upper_bound = float(variable_layout.upper_bounds[index])
            x1 = float(primary[index])
            x2 = float(secondary[index])
            u = float(rng.random())
            beta = (
                (2.0 * u) ** (1.0 / (eta_c + 1.0))
                if u <= 0.5
                else (1.0 / (2.0 * (1.0 - u))) ** (1.0 / (eta_c + 1.0))
            )
            child[index] = min(max(0.5 * ((1.0 + beta) * x1 + (1.0 - beta) * x2), lower_bound), upper_bound)

    mutation_rate = 1.0 / variable_layout.vector_size if mutation_prob_var is None else mutation_prob_var
    for index in range(variable_layout.vector_size):
        lower_bound = float(variable_layout.lower_bounds[index])
        upper_bound = float(variable_layout.upper_bounds[index])
        if float(rng.random()) < mutation_rate:
            span = upper_bound - lower_bound
            if span <= 0.0:
                continue
            value = float(child[index])
            delta_1 = (value - lower_bound) / span
            delta_2 = (upper_bound - value) / span
            u_mut = float(rng.random())
            mut_pow = 1.0 / (eta_m + 1.0)
            if u_mut < 0.5:
                xy = 1.0 - delta_1
                val = 2.0 * u_mut + (1.0 - 2.0 * u_mut) * (xy ** (eta_m + 1.0))
                delta_q = val**mut_pow - 1.0
            else:
                xy = 1.0 - delta_2
                val = 2.0 * (1.0 - u_mut) + 2.0 * (u_mut - 0.5) * (xy ** (eta_m + 1.0))
                delta_q = 1.0 - val**mut_pow
            child[index] = value + delta_q * span

    return variable_layout.clip(child)


def _native_sbx_pm(
    parents: ParentBundle,
    state: ControllerState,
    variable_layout: VariableLayout,
    rng: np.random.Generator,
) -> np.ndarray:
    eta_c, prob_c, eta_m, prob_var = _resolve_native_parameters(state)
    return _sbx_pm_numeric(
        parents=parents,
        variable_layout=variable_layout,
        rng=rng,
        eta_c=eta_c,
        crossover_prob=prob_c,
        eta_m=eta_m,
        mutation_prob_var=prob_var,
    )


def _sbx_pm_global(
    parents: ParentBundle,
    state: ControllerState,
    variable_layout: VariableLayout,
    rng: np.random.Generator,
) -> np.ndarray:
    del state
    return _sbx_pm_numeric(
        parents=parents,
        variable_layout=variable_layout,
        rng=rng,
        eta_c=10.0,
        crossover_prob=1.0,
        eta_m=15.0,
        mutation_prob_var=None,
    )


def _local_refine(
    parents: ParentBundle,
    state: ControllerState,
    variable_layout: VariableLayout,
    rng: np.random.Generator,
) -> np.ndarray:
    del state
    proposal = _copy_primary(parents)
    hot_center_x = 0.5 * (
        _value(proposal, variable_layout, "processor_x") + _value(proposal, variable_layout, "rf_power_amp_x")
    )
    hot_avg_y = 0.5 * (
        _value(proposal, variable_layout, "processor_y") + _value(proposal, variable_layout, "rf_power_amp_y")
    )
    hot_max_y = max(
        _value(proposal, variable_layout, "processor_y"),
        _value(proposal, variable_layout, "rf_power_amp_y"),
    )
    battery_x = _value(proposal, variable_layout, "battery_pack_x")
    battery_y = _value(proposal, variable_layout, "battery_pack_y")
    _set_clipped(
        proposal,
        variable_layout,
        "battery_pack_x",
        battery_x + (0.05 * float(rng.random())) * (hot_center_x - battery_x),
    )
    _set_clipped(
        proposal,
        variable_layout,
        "battery_pack_y",
        battery_y + (0.18 + 0.08 * float(rng.random())) * ((0.4 * hot_avg_y + 0.6 * hot_max_y) - battery_y),
    )

    protected_indices = {
        _index(variable_layout, "battery_pack_x"),
        _index(variable_layout, "battery_pack_y"),
    }
    candidate_indices = [index for index in range(variable_layout.vector_size) if index not in protected_indices]
    num_updates = min(2, len(candidate_indices))
    selected_indices = rng.choice(candidate_indices, size=num_updates, replace=False)
    for index in np.asarray(selected_indices, dtype=np.int64).tolist():
        span = float(variable_layout.upper_bounds[index] - variable_layout.lower_bounds[index])
        proposal[index] += float(rng.normal(loc=0.0, scale=0.02 * span))
    return variable_layout.clip(proposal)


def _hot_pair_to_sink(
    parents: ParentBundle,
    state: ControllerState,
    variable_layout: VariableLayout,
    rng: np.random.Generator,
) -> np.ndarray:
    del state
    proposal = _copy_primary(parents)
    for variable_id in ("processor_y", "rf_power_amp_y"):
        current = _value(proposal, variable_layout, variable_id)
        upper = variable_layout.slot_for(variable_id).upper_bound
        fraction = 0.08 + 0.12 * float(rng.random())
        _set_clipped(proposal, variable_layout, variable_id, current + fraction * (upper - current))
    return variable_layout.clip(proposal)


def _hot_pair_separate(
    parents: ParentBundle,
    state: ControllerState,
    variable_layout: VariableLayout,
    rng: np.random.Generator,
) -> np.ndarray:
    del state
    proposal = _copy_primary(parents)
    processor_x = _value(proposal, variable_layout, "processor_x")
    processor_y = _value(proposal, variable_layout, "processor_y")
    rf_x = _value(proposal, variable_layout, "rf_power_amp_x")
    rf_y = _value(proposal, variable_layout, "rf_power_amp_y")

    axis = "x" if abs(rf_x - processor_x) >= abs(rf_y - processor_y) else "y"
    left_id, right_id = ("processor_x", "rf_power_amp_x") if axis == "x" else ("processor_y", "rf_power_amp_y")
    left = _value(proposal, variable_layout, left_id)
    right = _value(proposal, variable_layout, right_id)
    left_slot = variable_layout.slot_for(left_id)
    right_slot = variable_layout.slot_for(right_id)
    span = min(left_slot.upper_bound - left_slot.lower_bound, right_slot.upper_bound - right_slot.lower_bound)
    midpoint = 0.5 * (left + right)
    direction = 1.0 if right >= left else -1.0
    separation = abs(right - left) + (0.02 + 0.03 * float(rng.random())) * span
    _set_clipped(proposal, variable_layout, left_id, midpoint - direction * 0.5 * separation)
    _set_clipped(proposal, variable_layout, right_id, midpoint + direction * 0.5 * separation)
    return variable_layout.clip(proposal)


def _battery_to_warm_zone(
    parents: ParentBundle,
    state: ControllerState,
    variable_layout: VariableLayout,
    rng: np.random.Generator,
) -> np.ndarray:
    del state
    proposal = _copy_primary(parents)
    target_x = 0.5 * (
        _value(proposal, variable_layout, "processor_x") + _value(proposal, variable_layout, "rf_power_amp_x")
    )
    target_y = 0.5 * (
        _value(proposal, variable_layout, "processor_y") + _value(proposal, variable_layout, "rf_power_amp_y")
    )
    hot_max_y = max(
        _value(proposal, variable_layout, "processor_y"),
        _value(proposal, variable_layout, "rf_power_amp_y"),
    )
    target_y = 0.35 * target_y + 0.65 * hot_max_y
    battery_x = _value(proposal, variable_layout, "battery_pack_x")
    battery_y = _value(proposal, variable_layout, "battery_pack_y")
    _set_clipped(
        proposal,
        variable_layout,
        "battery_pack_x",
        battery_x + (0.08 * float(rng.random())) * (target_x - battery_x),
    )
    _set_clipped(
        proposal,
        variable_layout,
        "battery_pack_y",
        battery_y + (0.55 + 0.12 * float(rng.random())) * (target_y - battery_y),
    )
    return variable_layout.clip(proposal)


def _radiator_align_hot_pair(
    parents: ParentBundle,
    state: ControllerState,
    variable_layout: VariableLayout,
    rng: np.random.Generator,
) -> np.ndarray:
    del state
    proposal = _copy_primary(parents)
    hot_center = 0.5 * (
        _value(proposal, variable_layout, "processor_x") + _value(proposal, variable_layout, "rf_power_amp_x")
    )
    start = _value(proposal, variable_layout, "radiator_start")
    end = _value(proposal, variable_layout, "radiator_end")
    current_center = 0.5 * (start + end)
    span = end - start
    fraction = 0.35 + 0.3 * float(rng.random())
    new_center = current_center + fraction * (hot_center - current_center)
    _set_clipped(proposal, variable_layout, "radiator_start", new_center - 0.5 * span)
    _set_clipped(proposal, variable_layout, "radiator_end", new_center + 0.5 * span)
    return variable_layout.clip(proposal)


def _radiator_expand(
    parents: ParentBundle,
    state: ControllerState,
    variable_layout: VariableLayout,
    rng: np.random.Generator,
) -> np.ndarray:
    del state
    proposal = _copy_primary(parents)
    start = _value(proposal, variable_layout, "radiator_start")
    end = _value(proposal, variable_layout, "radiator_end")
    start_slot = variable_layout.slot_for("radiator_start")
    end_slot = variable_layout.slot_for("radiator_end")
    left_room = start - start_slot.lower_bound
    right_room = end_slot.upper_bound - end
    fraction = 0.08 + 0.22 * float(rng.random())
    _set_clipped(proposal, variable_layout, "radiator_start", start - fraction * left_room)
    _set_clipped(proposal, variable_layout, "radiator_end", end + fraction * right_room)
    return variable_layout.clip(proposal)


def _radiator_contract(
    parents: ParentBundle,
    state: ControllerState,
    variable_layout: VariableLayout,
    rng: np.random.Generator,
) -> np.ndarray:
    del state
    proposal = _copy_primary(parents)
    start = _value(proposal, variable_layout, "radiator_start")
    end = _value(proposal, variable_layout, "radiator_end")
    span = end - start
    delta = (0.04 + 0.10 * float(rng.random())) * span
    _set_clipped(proposal, variable_layout, "radiator_start", start + 0.5 * delta)
    _set_clipped(proposal, variable_layout, "radiator_end", end - 0.5 * delta)
    return variable_layout.clip(proposal)


_REGISTERED_OPERATORS = (
    OperatorDefinition("native_sbx_pm", _native_sbx_pm),
    OperatorDefinition("sbx_pm_global", _sbx_pm_global),
    OperatorDefinition("local_refine", _local_refine),
    OperatorDefinition("hot_pair_to_sink", _hot_pair_to_sink),
    OperatorDefinition("hot_pair_separate", _hot_pair_separate),
    OperatorDefinition("battery_to_warm_zone", _battery_to_warm_zone),
    OperatorDefinition("radiator_align_hot_pair", _radiator_align_hot_pair),
    OperatorDefinition("radiator_expand", _radiator_expand),
    OperatorDefinition("radiator_contract", _radiator_contract),
)

_REGISTERED_OPERATOR_MAP = {definition.operator_id: definition for definition in _REGISTERED_OPERATORS}


def list_registered_operator_ids() -> list[str]:
    return [definition.operator_id for definition in _REGISTERED_OPERATORS]


def native_operator_id_for_backbone(family: str, backbone: str) -> str:
    key = (str(family), str(backbone))
    if key not in APPROVED_NATIVE_OPERATOR_IDS_BY_BACKBONE:
        raise KeyError(f"Unsupported union native-operator backbone family={family!r}, backbone={backbone!r}.")
    return APPROVED_NATIVE_OPERATOR_IDS_BY_BACKBONE[key]


def approved_union_operator_ids_for_backbone(family: str, backbone: str) -> tuple[str, ...]:
    return (native_operator_id_for_backbone(family, backbone), *APPROVED_SHARED_OPERATOR_IDS)


def get_operator_definition(operator_id: str) -> OperatorDefinition:
    if operator_id not in _REGISTERED_OPERATOR_MAP:
        raise KeyError(f"Unsupported union operator '{operator_id}'.")
    return _REGISTERED_OPERATOR_MAP[operator_id]
