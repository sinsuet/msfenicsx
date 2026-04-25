"""Approved union-action registry for numeric decision-vector proposals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from optimizers.cheap_constraints import project_sink_interval
from optimizers.operator_pool.assisted_registry import ASSISTED_OPERATOR_IDS
from optimizers.operator_pool.layout import VariableLayout
from optimizers.operator_pool.models import ParentBundle
from optimizers.operator_pool.primitive_registry import PRIMITIVE_OPERATOR_IDS
from optimizers.operator_pool.state import ControllerState


ProposalFn = Callable[[ParentBundle, ControllerState, VariableLayout, np.random.Generator], np.ndarray]


APPROVED_SHARED_OPERATOR_IDS = ASSISTED_OPERATOR_IDS
APPROVED_UNION_OPERATOR_IDS = (*PRIMITIVE_OPERATOR_IDS, *ASSISTED_OPERATOR_IDS)

APPROVED_NATIVE_OPERATOR_IDS_BY_BACKBONE = {
    ("genetic", "nsga2"): "native_sbx_pm",
    ("genetic", "nsga3"): "native_sbx_pm",
    ("genetic", "ctaea"): "native_sbx_pm",
    ("genetic", "rvea"): "native_sbx_pm",
    ("decomposition", "moead"): "native_moead",
    ("swarm", "cmopso"): "native_cmopso",
}

_MIN_SINK_SPAN = 0.15


def approved_operator_pool(registry_profile: str) -> tuple[str, ...]:
    if registry_profile == "primitive_clean":
        return PRIMITIVE_OPERATOR_IDS
    if registry_profile == "primitive_plus_assisted":
        return (*PRIMITIVE_OPERATOR_IDS, *ASSISTED_OPERATOR_IDS)
    raise KeyError(f"Unsupported registry profile: {registry_profile!r}")


@dataclass(frozen=True, slots=True)
class OperatorDefinition:
    operator_id: str
    propose: ProposalFn


@dataclass(frozen=True, slots=True)
class OperatorBehaviorProfile:
    operator_id: str
    family: str
    role: str
    exploration_class: str


@dataclass(frozen=True, slots=True)
class ComponentAxes:
    component_id: str
    x_id: str
    y_id: str


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


def _component_axes(layout: VariableLayout) -> tuple[ComponentAxes, ...]:
    slots_by_id = {slot.variable_id: slot for slot in layout.slots}
    pairs: list[ComponentAxes] = []
    for slot in layout.slots:
        if not slot.variable_id.endswith("_x"):
            continue
        component_id = slot.variable_id[:-2]
        y_id = f"{component_id}_y"
        if y_id not in slots_by_id:
            continue
        pairs.append(ComponentAxes(component_id=component_id, x_id=slot.variable_id, y_id=y_id))
    if not pairs:
        raise ValueError("Semantic union operators require paired '<component>_x' / '<component>_y' variables.")
    return tuple(pairs)


def _sink_variable_ids(layout: VariableLayout) -> tuple[str, str] | None:
    start_id = None
    end_id = None
    for slot in layout.slots:
        if slot.variable_id == "sink_start" or slot.path.endswith(".start"):
            start_id = slot.variable_id if start_id is None else start_id
        if slot.variable_id == "sink_end" or slot.path.endswith(".end"):
            end_id = slot.variable_id if end_id is None else end_id
    if start_id is None or end_id is None:
        return None
    return start_id, end_id


def _component_points(vector: np.ndarray, layout: VariableLayout, components: tuple[ComponentAxes, ...]) -> np.ndarray:
    return np.asarray(
        [[_value(vector, layout, component.x_id), _value(vector, layout, component.y_id)] for component in components],
        dtype=np.float64,
    )


def _component_centroid(points: np.ndarray, indices: list[int] | tuple[int, ...] | None = None) -> np.ndarray:
    if points.size == 0:
        return np.asarray([0.5, 0.5], dtype=np.float64)
    if not indices:
        return np.mean(points, axis=0)
    selected = points[np.asarray(indices, dtype=np.int64)]
    return np.mean(selected, axis=0)


def _normalized(values: np.ndarray) -> np.ndarray:
    if values.size == 0:
        return values
    span = float(np.max(values) - np.min(values))
    if span <= 1.0e-12:
        return np.zeros_like(values)
    return (values - float(np.min(values))) / span


def _nearest_neighbor_distances(points: np.ndarray) -> np.ndarray:
    count = int(points.shape[0])
    if count <= 1:
        return np.ones(count, dtype=np.float64)
    distances = np.full(count, np.inf, dtype=np.float64)
    for index in range(count):
        delta = points - points[index]
        norms = np.linalg.norm(delta, axis=1)
        norms[index] = np.inf
        distances[index] = float(np.min(norms))
    distances[~np.isfinite(distances)] = 1.0
    return distances


def _sink_state(
    vector: np.ndarray,
    layout: VariableLayout,
) -> tuple[str, str, float, float, float] | None:
    sink_ids = _sink_variable_ids(layout)
    if sink_ids is None:
        return None
    start_id, end_id = sink_ids
    start = _value(vector, layout, start_id)
    end = _value(vector, layout, end_id)
    return start_id, end_id, start, end, 0.5 * (start + end)


def _resolve_sink_budget_limit(
    state: ControllerState,
    layout: VariableLayout,
    *,
    start_id: str,
    end_id: str,
    current_span: float,
) -> float:
    raw_limit = state.metadata.get("radiator_span_max")
    if raw_limit is None:
        raw_limit = state.metadata.get("sink_budget_limit")
    if raw_limit is not None:
        return float(max(_MIN_SINK_SPAN, float(raw_limit)))
    start_slot = layout.slot_for(start_id)
    end_slot = layout.slot_for(end_id)
    return float(max(_MIN_SINK_SPAN, min(end_slot.upper_bound - start_slot.lower_bound, current_span)))


def _sink_target_center_jitter(
    proposal: np.ndarray,
    layout: VariableLayout,
    *,
    rng: np.random.Generator,
) -> float:
    sink_state = _sink_state(proposal, layout)
    if sink_state is None:
        return 0.0
    start_id, end_id, start, end, _ = sink_state
    start_slot = layout.slot_for(start_id)
    end_slot = layout.slot_for(end_id)
    current_span = max(_MIN_SINK_SPAN, float(end - start))
    usable_width = max(current_span, float(end_slot.upper_bound - start_slot.lower_bound))
    jitter_radius = max(0.01 * usable_width, min(0.08 * current_span, 0.04 * usable_width))
    return float(rng.uniform(-jitter_radius, jitter_radius))


def _slide_sink_to_center(
    proposal: np.ndarray,
    state: ControllerState,
    layout: VariableLayout,
    *,
    target_center: float,
    preserve_span: bool,
    span_override: float | None = None,
) -> None:
    sink_state = _sink_state(proposal, layout)
    if sink_state is None:
        return
    start_id, end_id, start, end, current_center = sink_state
    start_slot = layout.slot_for(start_id)
    end_slot = layout.slot_for(end_id)
    current_span = max(_MIN_SINK_SPAN, float(end - start))
    target_span = current_span if preserve_span else (
        current_span if span_override is None else max(_MIN_SINK_SPAN, float(span_override))
    )
    sink_budget_limit = _resolve_sink_budget_limit(
        state,
        layout,
        start_id=start_id,
        end_id=end_id,
        current_span=target_span,
    )
    desired_center = current_center + 0.65 * (float(target_center) - current_center)
    projected = project_sink_interval(
        start=desired_center - 0.5 * target_span,
        end=desired_center + 0.5 * target_span,
        span_max=sink_budget_limit,
        lower_bound=float(start_slot.lower_bound),
        upper_bound=float(end_slot.upper_bound),
        min_span=_MIN_SINK_SPAN,
        start_bounds=(float(start_slot.lower_bound), float(start_slot.upper_bound)),
        end_bounds=(float(end_slot.lower_bound), float(end_slot.upper_bound)),
    )
    _set_clipped(proposal, layout, start_id, projected.start)
    _set_clipped(proposal, layout, end_id, projected.end)


def _select_hot_cluster_indices(
    proposal: np.ndarray,
    layout: VariableLayout,
    components: tuple[ComponentAxes, ...],
) -> list[int]:
    points = _component_points(proposal, layout, components)
    nearest_neighbor_distances = _nearest_neighbor_distances(points)
    crowding = 1.0 / np.maximum(nearest_neighbor_distances, 1.0e-6)
    sink_state = _sink_state(proposal, layout)
    sink_center = 0.5 if sink_state is None else sink_state[-1]
    x_alignment = np.abs(points[:, 0] - sink_center)
    y_distance_from_sink = np.asarray(
        [
            layout.slot_for(component.y_id).upper_bound - float(points[index, 1])
            for index, component in enumerate(components)
        ],
        dtype=np.float64,
    )
    scores = (
        0.5 * _normalized(crowding)
        + 0.35 * _normalized(y_distance_from_sink)
        + 0.15 * _normalized(x_alignment)
    )
    cluster_size = min(max(2, len(components) // 5 + 1), len(components))
    ranked_indices = np.argsort(scores)[::-1]
    return [int(index) for index in ranked_indices[:cluster_size]]


def _closest_pair_indices(points: np.ndarray) -> tuple[int, int] | None:
    if int(points.shape[0]) < 2:
        return None
    best_pair = None
    best_distance = float("inf")
    for left_index in range(points.shape[0]):
        for right_index in range(left_index + 1, points.shape[0]):
            distance = float(np.linalg.norm(points[right_index] - points[left_index]))
            if distance < best_distance:
                best_distance = distance
                best_pair = (left_index, right_index)
    return best_pair


def _apply_component_shift(
    proposal: np.ndarray,
    layout: VariableLayout,
    component: ComponentAxes,
    *,
    dx: float = 0.0,
    dy: float = 0.0,
) -> None:
    _set_clipped(proposal, layout, component.x_id, _value(proposal, layout, component.x_id) + float(dx))
    _set_clipped(proposal, layout, component.y_id, _value(proposal, layout, component.y_id) + float(dy))


def _apply_component_target(
    proposal: np.ndarray,
    layout: VariableLayout,
    component: ComponentAxes,
    *,
    target_x: float | None = None,
    target_y: float | None = None,
    blend: float,
) -> None:
    if target_x is not None:
        current_x = _value(proposal, layout, component.x_id)
        _set_clipped(proposal, layout, component.x_id, current_x + float(blend) * (float(target_x) - current_x))
    if target_y is not None:
        current_y = _value(proposal, layout, component.y_id)
        _set_clipped(proposal, layout, component.y_id, current_y + float(blend) * (float(target_y) - current_y))


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


def _component_jitter_1(
    parents: ParentBundle,
    state: ControllerState,
    variable_layout: VariableLayout,
    rng: np.random.Generator,
) -> np.ndarray:
    del state
    proposal = _copy_primary(parents)
    component_pairs = _component_axes(variable_layout)
    component = component_pairs[int(rng.integers(0, len(component_pairs)))]
    x_slot = variable_layout.slot_for(component.x_id)
    y_slot = variable_layout.slot_for(component.y_id)
    proposal[x_slot.index] = float(
        np.clip(
            proposal[x_slot.index] + rng.normal(loc=0.0, scale=0.02 * (x_slot.upper_bound - x_slot.lower_bound)),
            x_slot.lower_bound,
            x_slot.upper_bound,
        )
    )
    proposal[y_slot.index] = float(
        np.clip(
            proposal[y_slot.index] + rng.normal(loc=0.0, scale=0.02 * (y_slot.upper_bound - y_slot.lower_bound)),
            y_slot.lower_bound,
            y_slot.upper_bound,
        )
    )
    return variable_layout.clip(proposal)


def _component_relocate_1(
    parents: ParentBundle,
    state: ControllerState,
    variable_layout: VariableLayout,
    rng: np.random.Generator,
) -> np.ndarray:
    del state
    proposal = _copy_primary(parents)
    component_pairs = _component_axes(variable_layout)
    component = component_pairs[int(rng.integers(0, len(component_pairs)))]
    x_slot = variable_layout.slot_for(component.x_id)
    y_slot = variable_layout.slot_for(component.y_id)
    proposal[x_slot.index] = float(rng.uniform(x_slot.lower_bound, x_slot.upper_bound))
    proposal[y_slot.index] = float(rng.uniform(y_slot.lower_bound, y_slot.upper_bound))
    return variable_layout.clip(proposal)


def _component_swap_2(
    parents: ParentBundle,
    state: ControllerState,
    variable_layout: VariableLayout,
    rng: np.random.Generator,
) -> np.ndarray:
    del state
    proposal = _copy_primary(parents)
    component_pairs = _component_axes(variable_layout)
    left_index, right_index = rng.choice(len(component_pairs), size=2, replace=False)
    left = component_pairs[int(left_index)]
    right = component_pairs[int(right_index)]
    left_x = proposal[variable_layout.index_of(left.x_id)]
    left_y = proposal[variable_layout.index_of(left.y_id)]
    proposal[variable_layout.index_of(left.x_id)] = proposal[variable_layout.index_of(right.x_id)]
    proposal[variable_layout.index_of(left.y_id)] = proposal[variable_layout.index_of(right.y_id)]
    proposal[variable_layout.index_of(right.x_id)] = left_x
    proposal[variable_layout.index_of(right.y_id)] = left_y
    return variable_layout.clip(proposal)


def _sink_shift(
    parents: ParentBundle,
    state: ControllerState,
    variable_layout: VariableLayout,
    rng: np.random.Generator,
) -> np.ndarray:
    proposal = _copy_primary(parents)
    sink_state = _sink_state(proposal, variable_layout)
    if sink_state is None:
        return variable_layout.clip(proposal)
    _, _, start, end, center = sink_state
    span = max(_MIN_SINK_SPAN, float(end - start))
    shift = float(rng.normal(loc=0.0, scale=0.03 * span))
    _slide_sink_to_center(
        proposal,
        state,
        variable_layout,
        target_center=center + shift,
        preserve_span=True,
    )
    return variable_layout.clip(proposal)


def _sink_resize(
    parents: ParentBundle,
    state: ControllerState,
    variable_layout: VariableLayout,
    rng: np.random.Generator,
) -> np.ndarray:
    proposal = _copy_primary(parents)
    sink_state = _sink_state(proposal, variable_layout)
    if sink_state is None:
        return variable_layout.clip(proposal)
    _, _, start, end, center = sink_state
    span = max(_MIN_SINK_SPAN, float(end - start))
    target_span = max(_MIN_SINK_SPAN, span * float(1.0 + rng.normal(loc=0.0, scale=0.12)))
    _slide_sink_to_center(
        proposal,
        state,
        variable_layout,
        target_center=center,
        preserve_span=False,
        span_override=target_span,
    )
    return variable_layout.clip(proposal)


def _global_explore(
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
    proposal = _copy_primary(parents)
    components = _component_axes(variable_layout)
    cluster_indices = _select_hot_cluster_indices(proposal, variable_layout, components)
    for component_index in cluster_indices[: min(3, len(cluster_indices))]:
        component = components[component_index]
        x_slot = variable_layout.slot_for(component.x_id)
        y_slot = variable_layout.slot_for(component.y_id)
        _apply_component_shift(
            proposal,
            variable_layout,
            component,
            dx=float(rng.normal(loc=0.0, scale=0.015 * (x_slot.upper_bound - x_slot.lower_bound))),
            dy=float(rng.normal(loc=0.0, scale=0.015 * (y_slot.upper_bound - y_slot.lower_bound))),
        )
    centroid = _component_centroid(_component_points(proposal, variable_layout, components), cluster_indices)
    _slide_sink_to_center(
        proposal,
        state,
        variable_layout,
        target_center=float(centroid[0]),
        preserve_span=True,
    )
    return variable_layout.clip(proposal)


def _move_hottest_cluster_toward_sink(
    parents: ParentBundle,
    state: ControllerState,
    variable_layout: VariableLayout,
    rng: np.random.Generator,
) -> np.ndarray:
    proposal = _copy_primary(parents)
    components = _component_axes(variable_layout)
    cluster_indices = _select_hot_cluster_indices(proposal, variable_layout, components)
    sink_state = _sink_state(proposal, variable_layout)
    sink_center = 0.5 if sink_state is None else float(sink_state[-1])
    for component_index in cluster_indices:
        component = components[component_index]
        y_slot = variable_layout.slot_for(component.y_id)
        blend = 0.2 + 0.15 * float(rng.random())
        _apply_component_target(
            proposal,
            variable_layout,
            component,
            target_x=sink_center,
            target_y=float(y_slot.upper_bound),
            blend=blend,
        )
    return variable_layout.clip(proposal)


def _spread_hottest_cluster(
    parents: ParentBundle,
    state: ControllerState,
    variable_layout: VariableLayout,
    rng: np.random.Generator,
) -> np.ndarray:
    del state
    proposal = _copy_primary(parents)
    components = _component_axes(variable_layout)
    cluster_indices = _select_hot_cluster_indices(proposal, variable_layout, components)
    points = _component_points(proposal, variable_layout, components)
    cluster_center = _component_centroid(points, cluster_indices)
    average_x_span = float(
        np.mean(
            [
                variable_layout.slot_for(components[index].x_id).upper_bound
                - variable_layout.slot_for(components[index].x_id).lower_bound
                for index in cluster_indices
            ]
        )
    )
    spread_step = (0.08 + 0.06 * float(rng.random())) * average_x_span
    ordered_indices = sorted(cluster_indices, key=lambda index: float(points[index, 0]))
    offsets = np.linspace(
        -0.5 * (len(ordered_indices) - 1),
        0.5 * (len(ordered_indices) - 1),
        num=len(ordered_indices),
        dtype=np.float64,
    )
    for component_index, offset in zip(ordered_indices, offsets, strict=True):
        component = components[component_index]
        y_slot = variable_layout.slot_for(component.y_id)
        _apply_component_target(
            proposal,
            variable_layout,
            component,
            target_x=float(cluster_center[0] + float(offset) * spread_step),
            target_y=float(_value(proposal, variable_layout, component.y_id) + 0.18 * (y_slot.upper_bound - _value(proposal, variable_layout, component.y_id))),
            blend=0.6,
        )
    return variable_layout.clip(proposal)


def _smooth_high_gradient_band(
    parents: ParentBundle,
    state: ControllerState,
    variable_layout: VariableLayout,
    rng: np.random.Generator,
) -> np.ndarray:
    proposal = _copy_primary(parents)
    components = _component_axes(variable_layout)
    cluster_indices = _select_hot_cluster_indices(proposal, variable_layout, components)
    points = _component_points(proposal, variable_layout, components)
    cluster_center = _component_centroid(points, cluster_indices)
    sink_state = _sink_state(proposal, variable_layout)
    sink_center = float(cluster_center[0]) if sink_state is None else float(sink_state[-1])
    target_x = 0.65 * float(cluster_center[0]) + 0.35 * sink_center
    for component_index in cluster_indices:
        component = components[component_index]
        y_slot = variable_layout.slot_for(component.y_id)
        target_y = 0.7 * float(cluster_center[1]) + 0.3 * float(y_slot.upper_bound)
        _apply_component_target(
            proposal,
            variable_layout,
            component,
            target_x=target_x,
            target_y=target_y,
            blend=0.45 + 0.1 * float(rng.random()),
        )
    return variable_layout.clip(proposal)


def _reduce_local_congestion(
    parents: ParentBundle,
    state: ControllerState,
    variable_layout: VariableLayout,
    rng: np.random.Generator,
) -> np.ndarray:
    del state
    proposal = _copy_primary(parents)
    components = _component_axes(variable_layout)
    points = _component_points(proposal, variable_layout, components)
    pair = _closest_pair_indices(points)
    if pair is None:
        return variable_layout.clip(proposal)
    left_index, right_index = pair
    delta = points[right_index] - points[left_index]
    norm = float(np.linalg.norm(delta))
    if norm <= 1.0e-9:
        delta = np.asarray([1.0, 0.0], dtype=np.float64)
        norm = 1.0
    direction = delta / norm
    left_component = components[left_index]
    right_component = components[right_index]
    x_span = min(
        variable_layout.slot_for(left_component.x_id).upper_bound - variable_layout.slot_for(left_component.x_id).lower_bound,
        variable_layout.slot_for(right_component.x_id).upper_bound - variable_layout.slot_for(right_component.x_id).lower_bound,
    )
    y_span = min(
        variable_layout.slot_for(left_component.y_id).upper_bound - variable_layout.slot_for(left_component.y_id).lower_bound,
        variable_layout.slot_for(right_component.y_id).upper_bound - variable_layout.slot_for(right_component.y_id).lower_bound,
    )
    separation_scale = 0.07 + 0.04 * float(rng.random())
    shift = np.asarray([direction[0] * x_span, direction[1] * y_span], dtype=np.float64) * separation_scale
    _apply_component_shift(
        proposal,
        variable_layout,
        left_component,
        dx=-0.5 * float(shift[0]),
        dy=-0.5 * float(shift[1]),
    )
    _apply_component_shift(
        proposal,
        variable_layout,
        right_component,
        dx=0.5 * float(shift[0]),
        dy=0.5 * float(shift[1]),
    )
    return variable_layout.clip(proposal)


def _repair_sink_budget(
    parents: ParentBundle,
    state: ControllerState,
    variable_layout: VariableLayout,
    rng: np.random.Generator,
) -> np.ndarray:
    proposal = _copy_primary(parents)
    components = _component_axes(variable_layout)
    cluster_indices = _select_hot_cluster_indices(proposal, variable_layout, components)
    cluster_center = _component_centroid(_component_points(proposal, variable_layout, components), cluster_indices)
    sink_state = _sink_state(proposal, variable_layout)
    if sink_state is None:
        return variable_layout.clip(proposal)
    start_id, end_id, start, end, _ = sink_state
    sink_budget_limit = _resolve_sink_budget_limit(
        state,
        variable_layout,
        start_id=start_id,
        end_id=end_id,
        current_span=float(end - start),
    )
    target_span = max(_MIN_SINK_SPAN, min(float(end - start), sink_budget_limit))
    target_span *= 0.92 + 0.08 * float(rng.random())
    _slide_sink_to_center(
        proposal,
        state,
        variable_layout,
        target_center=float(cluster_center[0]) + _sink_target_center_jitter(
            proposal,
            variable_layout,
            rng=rng,
        ),
        preserve_span=False,
        span_override=min(target_span, sink_budget_limit),
    )
    return variable_layout.clip(proposal)


def _slide_sink(
    parents: ParentBundle,
    state: ControllerState,
    variable_layout: VariableLayout,
    rng: np.random.Generator,
) -> np.ndarray:
    proposal = _copy_primary(parents)
    components = _component_axes(variable_layout)
    cluster_indices = _select_hot_cluster_indices(proposal, variable_layout, components)
    cluster_center = _component_centroid(_component_points(proposal, variable_layout, components), cluster_indices)
    _slide_sink_to_center(
        proposal,
        state,
        variable_layout,
        target_center=float(cluster_center[0]) + _sink_target_center_jitter(
            proposal,
            variable_layout,
            rng=rng,
        ),
        preserve_span=True,
    )
    return variable_layout.clip(proposal)


def _rebalance_layout(
    parents: ParentBundle,
    state: ControllerState,
    variable_layout: VariableLayout,
    rng: np.random.Generator,
) -> np.ndarray:
    proposal = _copy_primary(parents)
    components = _component_axes(variable_layout)
    points = _component_points(proposal, variable_layout, components)
    centroid = _component_centroid(points)
    panel_center_x = float(
        np.mean(
            [
                0.5 * (
                    variable_layout.slot_for(component.x_id).lower_bound
                    + variable_layout.slot_for(component.x_id).upper_bound
                )
                for component in components
            ]
        )
    )
    panel_center_y = float(
        np.mean(
            [
                0.5 * (
                    variable_layout.slot_for(component.y_id).lower_bound
                    + variable_layout.slot_for(component.y_id).upper_bound
                )
                for component in components
            ]
        )
    )
    shift_x = (0.15 + 0.05 * float(rng.random())) * (panel_center_x - float(centroid[0]))
    shift_y = (0.10 + 0.05 * float(rng.random())) * (panel_center_y - float(centroid[1]))
    for component_index, component in enumerate(components):
        x_slot = variable_layout.slot_for(component.x_id)
        alternating_x = (-1.0 if component_index % 2 == 0 else 1.0) * 0.02 * (x_slot.upper_bound - x_slot.lower_bound)
        _apply_component_shift(
            proposal,
            variable_layout,
            component,
            dx=shift_x + 0.5 * alternating_x,
            dy=shift_y,
        )
    _slide_sink_to_center(
        proposal,
        state,
        variable_layout,
        target_center=panel_center_x,
        preserve_span=True,
    )
    return variable_layout.clip(proposal)


_REGISTERED_OPERATORS = (
    OperatorDefinition("vector_sbx_pm", _native_sbx_pm),
    OperatorDefinition("component_jitter_1", _component_jitter_1),
    OperatorDefinition("component_relocate_1", _component_relocate_1),
    OperatorDefinition("component_swap_2", _component_swap_2),
    OperatorDefinition("sink_shift", _sink_shift),
    OperatorDefinition("sink_resize", _sink_resize),
    OperatorDefinition("hotspot_pull_toward_sink", _move_hottest_cluster_toward_sink),
    OperatorDefinition("hotspot_spread", _spread_hottest_cluster),
    OperatorDefinition("gradient_band_smooth", _smooth_high_gradient_band),
    OperatorDefinition("congestion_relief", _reduce_local_congestion),
    OperatorDefinition("sink_retarget", _slide_sink),
    OperatorDefinition("layout_rebalance", _rebalance_layout),
)

_REGISTERED_OPERATOR_MAP = {definition.operator_id: definition for definition in _REGISTERED_OPERATORS}
_OPERATOR_BEHAVIOR_PROFILES = {
    "vector_sbx_pm": OperatorBehaviorProfile(
        operator_id="vector_sbx_pm",
        family="native_baseline",
        role="native_baseline",
        exploration_class="stable",
    ),
    "component_jitter_1": OperatorBehaviorProfile(
        operator_id="component_jitter_1",
        family="primitive_component",
        role="component_jitter",
        exploration_class="stable",
    ),
    "component_relocate_1": OperatorBehaviorProfile(
        operator_id="component_relocate_1",
        family="primitive_component",
        role="component_relocate",
        exploration_class="stable",
    ),
    "component_swap_2": OperatorBehaviorProfile(
        operator_id="component_swap_2",
        family="primitive_component",
        role="component_swap",
        exploration_class="stable",
    ),
    "sink_shift": OperatorBehaviorProfile(
        operator_id="sink_shift",
        family="primitive_sink",
        role="sink_shift",
        exploration_class="stable",
    ),
    "sink_resize": OperatorBehaviorProfile(
        operator_id="sink_resize",
        family="primitive_sink",
        role="sink_resize",
        exploration_class="stable",
    ),
    "hotspot_pull_toward_sink": OperatorBehaviorProfile(
        operator_id="hotspot_pull_toward_sink",
        family="assisted_hotspot",
        role="hotspot_pull_toward_sink",
        exploration_class="custom",
    ),
    "hotspot_spread": OperatorBehaviorProfile(
        operator_id="hotspot_spread",
        family="assisted_hotspot",
        role="hotspot_spread",
        exploration_class="custom",
    ),
    "gradient_band_smooth": OperatorBehaviorProfile(
        operator_id="gradient_band_smooth",
        family="assisted_gradient",
        role="gradient_band_smooth",
        exploration_class="custom",
    ),
    "congestion_relief": OperatorBehaviorProfile(
        operator_id="congestion_relief",
        family="assisted_congestion",
        role="congestion_relief",
        exploration_class="custom",
    ),
    "sink_retarget": OperatorBehaviorProfile(
        operator_id="sink_retarget",
        family="assisted_sink",
        role="sink_retarget",
        exploration_class="custom",
    ),
    "layout_rebalance": OperatorBehaviorProfile(
        operator_id="layout_rebalance",
        family="assisted_layout",
        role="layout_rebalance",
        exploration_class="custom",
    ),
    "native_sbx_pm": OperatorBehaviorProfile(
        operator_id="native_sbx_pm",
        family="native_baseline",
        role="native_baseline",
        exploration_class="stable",
    ),
    "native_moead": OperatorBehaviorProfile(
        operator_id="native_moead",
        family="native_baseline",
        role="native_baseline",
        exploration_class="stable",
    ),
    "native_cmopso": OperatorBehaviorProfile(
        operator_id="native_cmopso",
        family="native_baseline",
        role="native_baseline",
        exploration_class="stable",
    ),
    "global_explore": OperatorBehaviorProfile(
        operator_id="global_explore",
        family="global_explore",
        role="global_explore",
        exploration_class="stable",
    ),
    "local_refine": OperatorBehaviorProfile(
        operator_id="local_refine",
        family="local_refine",
        role="local_refine",
        exploration_class="stable",
    ),
    "move_hottest_cluster_toward_sink": OperatorBehaviorProfile(
        operator_id="move_hottest_cluster_toward_sink",
        family="speculative_custom",
        role="speculative_custom",
        exploration_class="custom",
    ),
    "spread_hottest_cluster": OperatorBehaviorProfile(
        operator_id="spread_hottest_cluster",
        family="speculative_custom",
        role="speculative_custom",
        exploration_class="custom",
    ),
    "smooth_high_gradient_band": OperatorBehaviorProfile(
        operator_id="smooth_high_gradient_band",
        family="speculative_custom",
        role="speculative_custom",
        exploration_class="custom",
    ),
    "reduce_local_congestion": OperatorBehaviorProfile(
        operator_id="reduce_local_congestion",
        family="speculative_custom",
        role="speculative_custom",
        exploration_class="custom",
    ),
    "repair_sink_budget": OperatorBehaviorProfile(
        operator_id="repair_sink_budget",
        family="speculative_custom",
        role="speculative_custom",
        exploration_class="custom",
    ),
    "slide_sink": OperatorBehaviorProfile(
        operator_id="slide_sink",
        family="speculative_custom",
        role="speculative_custom",
        exploration_class="custom",
    ),
    "rebalance_layout": OperatorBehaviorProfile(
        operator_id="rebalance_layout",
        family="speculative_custom",
        role="speculative_custom",
        exploration_class="custom",
    ),
}


def list_registered_operator_ids() -> list[str]:
    return [definition.operator_id for definition in _REGISTERED_OPERATORS]


def native_operator_id_for_backbone(family: str, backbone: str) -> str:
    key = (str(family), str(backbone))
    if key not in APPROVED_NATIVE_OPERATOR_IDS_BY_BACKBONE:
        raise KeyError(f"Unsupported union native-operator backbone family={family!r}, backbone={backbone!r}.")
    return APPROVED_NATIVE_OPERATOR_IDS_BY_BACKBONE[key]


def approved_union_operator_ids_for_backbone(family: str, backbone: str) -> tuple[str, ...]:
    native_operator_id_for_backbone(family, backbone)
    return approved_operator_pool("primitive_clean")


def get_operator_definition(operator_id: str) -> OperatorDefinition:
    if operator_id not in _REGISTERED_OPERATOR_MAP:
        raise KeyError(f"Unsupported union operator '{operator_id}'.")
    return _REGISTERED_OPERATOR_MAP[operator_id]


def get_operator_behavior_profile(operator_id: str) -> OperatorBehaviorProfile:
    if operator_id not in _OPERATOR_BEHAVIOR_PROFILES:
        raise KeyError(f"Unsupported union operator behavior profile '{operator_id}'.")
    return _OPERATOR_BEHAVIOR_PROFILES[operator_id]
