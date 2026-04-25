"""Geometry and radiator repair helpers for optimizer-generated cases."""

from __future__ import annotations

from copy import deepcopy
from itertools import combinations
from typing import Any

import numpy as np

from core.generator.layout_metrics import measure_case_layout_metrics
from core.geometry.layout_rules import (
    component_polygon,
    component_within_domain,
    components_violate_clearance,
    required_clearance_gap,
)
from core.schema.models import ThermalCase
from optimizers.codec import DecisionVectorError, _set_path_value
from optimizers.cheap_constraints import project_sink_interval


MIN_RADIATOR_SPAN = 0.15
REPAIR_EPSILON = 1.0e-4
MAX_SEPARATION_PASSES = 24
LOCAL_RESTORE_GRID_STEPS = 9
MAX_LOCAL_RESTORE_PASSES = 24


def repair_case_from_vector(
    base_case: Any,
    optimization_spec: Any,
    vector: np.ndarray,
    *,
    radiator_span_max: float | None = None,
) -> ThermalCase:
    payload = repair_case_payload_from_vector(
        base_case,
        optimization_spec,
        vector,
        radiator_span_max=radiator_span_max,
    )
    return ThermalCase.from_dict(payload)


def repair_case_payload_from_vector(
    base_case: Any,
    optimization_spec: Any,
    vector: np.ndarray,
    *,
    radiator_span_max: float | None = None,
) -> dict[str, Any]:
    payload = project_case_payload_from_vector(
        base_case,
        optimization_spec,
        vector,
        radiator_span_max=radiator_span_max,
    )
    spec_payload = optimization_spec.to_dict() if hasattr(optimization_spec, "to_dict") else dict(optimization_spec)
    component_bounds, _ = _collect_variable_bounds(spec_payload)
    clearance_by_family = {
        str(component.get("family_id", "")): float(component.get("clearance", 0.0))
        for component in payload["components"]
        if component.get("family_id") is not None
    }
    _resolve_component_overlaps(
        payload["components"],
        component_bounds,
        panel_domain=payload["panel_domain"],
        clearance_by_family=clearance_by_family,
    )
    _refresh_layout_metrics(payload)
    return payload


def project_case_payload_from_vector(
    base_case: Any,
    optimization_spec: Any,
    vector: np.ndarray,
    *,
    radiator_span_max: float | None = None,
) -> dict[str, Any]:
    spec_payload = optimization_spec.to_dict() if hasattr(optimization_spec, "to_dict") else dict(optimization_spec)
    payload = _apply_vector_without_case_validation(base_case, spec_payload, vector)
    component_bounds, radiator_bounds = _collect_variable_bounds(spec_payload)
    _clamp_target_components(payload["components"], component_bounds)
    _repair_radiator_intervals(
        payload["boundary_features"],
        radiator_bounds,
        radiator_span_max=radiator_span_max,
    )
    return payload


def _refresh_layout_metrics(payload: dict[str, Any]) -> None:
    provenance = payload.setdefault("provenance", {})
    layout_context = provenance.get("layout_context")
    if isinstance(layout_context, dict):
        layout_metrics = measure_case_layout_metrics(payload, layout_context=layout_context)
        if layout_metrics is not None:
            provenance["layout_metrics"] = layout_metrics


def _apply_vector_without_case_validation(base_case: Any, optimization_spec: dict[str, Any], vector: np.ndarray) -> dict[str, Any]:
    case_payload = base_case.to_dict() if hasattr(base_case, "to_dict") else dict(base_case)
    values = np.asarray(vector, dtype=np.float64)
    design_variables = optimization_spec["design_variables"]
    if values.size != len(design_variables):
        raise DecisionVectorError(
            f"Decision vector length {values.size} does not match {len(design_variables)} design variables."
        )
    mutated_payload = deepcopy(case_payload)
    for variable, value in zip(design_variables, values.tolist(), strict=True):
        lower_bound = float(variable["lower_bound"])
        upper_bound = float(variable["upper_bound"])
        _set_path_value(mutated_payload, variable["path"], _clamp(float(value), lower_bound, upper_bound))
    return mutated_payload


def _collect_variable_bounds(
    optimization_spec: dict[str, Any],
) -> tuple[dict[int, dict[str, tuple[float, float]]], dict[int, dict[str, tuple[float, float]]]]:
    component_bounds: dict[int, dict[str, tuple[float, float]]] = {}
    radiator_bounds: dict[int, dict[str, tuple[float, float]]] = {}
    for variable in optimization_spec["design_variables"]:
        path = variable["path"]
        lower_upper = (float(variable["lower_bound"]), float(variable["upper_bound"]))
        if path.startswith("components[") and ".pose." in path:
            component_index = int(path.split("[", 1)[1].split("]", 1)[0])
            axis = path.rsplit(".", 1)[1]
            component_bounds.setdefault(component_index, {})[axis] = lower_upper
        if path.startswith("boundary_features[") and path.rsplit(".", 1)[1] in {"start", "end"}:
            feature_index = int(path.split("[", 1)[1].split("]", 1)[0])
            field = path.rsplit(".", 1)[1]
            radiator_bounds.setdefault(feature_index, {})[field] = lower_upper
    return component_bounds, radiator_bounds


def _clamp_target_components(
    components: list[dict[str, Any]],
    component_bounds: dict[int, dict[str, tuple[float, float]]],
) -> None:
    for component_index, axes in component_bounds.items():
        pose = components[component_index]["pose"]
        for axis, (lower_bound, upper_bound) in axes.items():
            pose[axis] = _clamp(float(pose[axis]), lower_bound, upper_bound)


def _repair_radiator_intervals(
    boundary_features: list[dict[str, Any]],
    radiator_bounds: dict[int, dict[str, tuple[float, float]]],
    *,
    radiator_span_max: float | None,
) -> None:
    for feature_index, fields in radiator_bounds.items():
        feature = boundary_features[feature_index]
        start_bounds = fields.get("start")
        end_bounds = fields.get("end")
        if start_bounds is None or end_bounds is None:
            continue
        start = _clamp(float(feature["start"]), *start_bounds)
        end = _clamp(float(feature["end"]), *end_bounds)
        upper_span = (
            float(radiator_span_max)
            if radiator_span_max is not None
            else max(float(end_bounds[1]) - float(start_bounds[0]), end - start, MIN_RADIATOR_SPAN)
        )
        projected = project_sink_interval(
            start=start,
            end=end,
            span_max=upper_span,
            lower_bound=float(start_bounds[0]),
            upper_bound=float(end_bounds[1]),
            min_span=MIN_RADIATOR_SPAN,
            start_bounds=start_bounds,
            end_bounds=end_bounds,
        )
        feature["start"] = float(projected.start)
        feature["end"] = float(projected.end)


def _resolve_component_overlaps(
    components: list[dict[str, Any]],
    component_bounds: dict[int, dict[str, tuple[float, float]]],
    *,
    panel_domain: dict[str, Any],
    clearance_by_family: dict[str, float],
) -> None:
    movable_indices = set(component_bounds)
    for _ in range(MAX_SEPARATION_PASSES):
        changed = False
        for left_index, right_index in combinations(range(len(components)), 2):
            left = components[left_index]
            right = components[right_index]
            overlap_x, overlap_y = _component_overlap_deltas(left, right)
            shortfall = max(0.0, -required_clearance_gap(left, right, clearance_by_family))
            if overlap_x <= 0.0 or overlap_y <= 0.0:
                if shortfall <= 0.0:
                    continue
                primary_axis = "x" if abs(overlap_x) <= abs(overlap_y) else "y"
                secondary_axis = "y" if primary_axis == "x" else "x"
                primary_delta = shortfall
                secondary_delta = shortfall
            else:
                primary_axis = "x" if overlap_x <= overlap_y else "y"
                secondary_axis = "y" if primary_axis == "x" else "x"
                primary_delta = overlap_x if primary_axis == "x" else overlap_y
                secondary_delta = overlap_y if secondary_axis == "y" else overlap_x
            if primary_delta <= 0.0 and secondary_delta <= 0.0:
                continue
            changed = True
            _separate_pair(
                components,
                left_index,
                right_index,
                movable_indices,
                component_bounds,
                axis=primary_axis,
                delta=primary_delta,
                clearance_by_family=clearance_by_family,
            )
            updated_left = components[left_index]
            updated_right = components[right_index]
            retry_shortfall = max(0.0, -required_clearance_gap(updated_left, updated_right, clearance_by_family))
            retry_overlap_x, retry_overlap_y = _component_overlap_deltas(updated_left, updated_right)
            if retry_shortfall > 0.0 or (retry_overlap_x > 0.0 and retry_overlap_y > 0.0):
                _separate_pair(
                    components,
                    left_index,
                    right_index,
                    movable_indices,
                    component_bounds,
                    axis=secondary_axis,
                    delta=secondary_delta,
                    clearance_by_family=clearance_by_family,
                )
        if not changed:
            break
    _restore_local_legality(components, component_bounds, panel_domain, clearance_by_family)


def _separate_pair(
    components: list[dict[str, Any]],
    left_index: int,
    right_index: int,
    movable_indices: set[int],
    component_bounds: dict[int, dict[str, tuple[float, float]]],
    *,
    axis: str,
    delta: float,
    clearance_by_family: dict[str, float],
) -> None:
    left = components[left_index]
    right = components[right_index]
    left_value = float(left["pose"][axis])
    right_value = float(right["pose"][axis])
    direction = 1.0 if right_value >= left_value else -1.0
    shortfall = max(0.0, -required_clearance_gap(left, right, clearance_by_family))
    shift = max(float(delta), shortfall) + REPAIR_EPSILON
    left_movable = left_index in movable_indices
    right_movable = right_index in movable_indices
    if left_movable and right_movable:
        _set_component_axis(components[left_index], axis, left_value - direction * shift * 0.5, component_bounds[left_index])
        _set_component_axis(components[right_index], axis, right_value + direction * shift * 0.5, component_bounds[right_index])
        return
    if left_movable:
        _set_component_axis(components[left_index], axis, left_value - direction * shift, component_bounds[left_index])
        return
    if right_movable:
        _set_component_axis(components[right_index], axis, right_value + direction * shift, component_bounds[right_index])


def _set_component_axis(component: dict[str, Any], axis: str, value: float, bounds: dict[str, tuple[float, float]]) -> None:
    lower_bound, upper_bound = bounds[axis]
    component["pose"][axis] = _clamp(value, lower_bound, upper_bound)


def _restore_local_legality(
    components: list[dict[str, Any]],
    component_bounds: dict[int, dict[str, tuple[float, float]]],
    panel_domain: dict[str, Any],
    clearance_by_family: dict[str, float],
) -> None:
    movable_indices = set(component_bounds)
    for _ in range(MAX_LOCAL_RESTORE_PASSES):
        illegal_pairs = _illegal_pairs(components, clearance_by_family)
        if not illegal_pairs:
            return
        offender = _select_worst_offender(illegal_pairs, movable_indices)
        if offender is None:
            return
        if not _reposition_component(
            components,
            offender,
            component_bounds[offender],
            panel_domain,
            clearance_by_family,
        ):
            return


def _illegal_pairs(components: list[dict[str, Any]], clearance_by_family: dict[str, float]) -> list[tuple[int, int]]:
    pairs: list[tuple[int, int]] = []
    for left_index, right_index in combinations(range(len(components)), 2):
        if components_violate_clearance(components[left_index], components[right_index], clearance_by_family):
            pairs.append((left_index, right_index))
    return pairs


def _select_worst_offender(overlap_pairs: list[tuple[int, int]], movable_indices: set[int]) -> int | None:
    overlap_counts: dict[int, int] = {}
    for left_index, right_index in overlap_pairs:
        if left_index in movable_indices:
            overlap_counts[left_index] = overlap_counts.get(left_index, 0) + 1
        if right_index in movable_indices:
            overlap_counts[right_index] = overlap_counts.get(right_index, 0) + 1
    if not overlap_counts:
        return None
    return max(overlap_counts.items(), key=lambda item: (item[1], -item[0]))[0]


def _reposition_component(
    components: list[dict[str, Any]],
    component_index: int,
    bounds: dict[str, tuple[float, float]],
    panel_domain: dict[str, Any],
    clearance_by_family: dict[str, float],
) -> bool:
    component = components[component_index]
    original_x = float(component["pose"]["x"])
    original_y = float(component["pose"]["y"])
    x_candidates = _axis_candidates(original_x, bounds["x"])
    y_candidates = _axis_candidates(original_y, bounds["y"])
    candidates = sorted(
        (
            (x_value, y_value)
            for x_value in x_candidates
            for y_value in y_candidates
        ),
        key=lambda point: (point[0] - original_x) ** 2 + (point[1] - original_y) ** 2,
    )
    for x_value, y_value in candidates:
        component["pose"]["x"] = float(x_value)
        component["pose"]["y"] = float(y_value)
        if not component_within_domain(component, panel_domain):
            continue
        if any(
            components_violate_clearance(component, other, clearance_by_family)
            for other_index, other in enumerate(components)
            if other_index != component_index
        ):
            continue
        return True
    component["pose"]["x"] = original_x
    component["pose"]["y"] = original_y
    return False


def _axis_candidates(current_value: float, bounds: tuple[float, float]) -> list[float]:
    lower_bound, upper_bound = bounds
    if upper_bound <= lower_bound:
        return [float(lower_bound)]
    raw_values = np.linspace(lower_bound, upper_bound, num=LOCAL_RESTORE_GRID_STEPS, dtype=np.float64).tolist()
    raw_values.extend([lower_bound, upper_bound, _clamp(current_value, lower_bound, upper_bound)])
    unique_values = sorted({round(float(value), 12) for value in raw_values})
    return [float(value) for value in unique_values]


def _axis_overlap(center_a: float, size_a: float, center_b: float, size_b: float) -> float:
    return 0.5 * (size_a + size_b) - abs(center_b - center_a)


def _component_overlap_deltas(left: dict[str, Any], right: dict[str, Any]) -> tuple[float, float]:
    left_min_x, left_min_y, left_max_x, left_max_y = component_polygon(left).bounds
    right_min_x, right_min_y, right_max_x, right_max_y = component_polygon(right).bounds
    left_width = float(left_max_x) - float(left_min_x)
    left_height = float(left_max_y) - float(left_min_y)
    right_width = float(right_max_x) - float(right_min_x)
    right_height = float(right_max_y) - float(right_min_y)
    overlap_x = _axis_overlap(
        0.5 * (float(left_min_x) + float(left_max_x)),
        left_width,
        0.5 * (float(right_min_x) + float(right_max_x)),
        right_width,
    )
    overlap_y = _axis_overlap(
        0.5 * (float(left_min_y) + float(left_max_y)),
        left_height,
        0.5 * (float(right_min_y) + float(right_max_y)),
        right_height,
    )
    return overlap_x, overlap_y


def _clamp(value: float, lower_bound: float, upper_bound: float) -> float:
    return max(lower_bound, min(upper_bound, float(value)))
