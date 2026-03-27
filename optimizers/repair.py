"""Geometry and radiator repair helpers for optimizer-generated cases."""

from __future__ import annotations

from itertools import combinations
from typing import Any

import numpy as np

from core.schema.models import ThermalCase
from optimizers.codec import apply_decision_vector


MIN_RADIATOR_SPAN = 0.15
REPAIR_EPSILON = 1.0e-4
MAX_SEPARATION_PASSES = 24


def repair_case_from_vector(base_case: Any, optimization_spec: Any, vector: np.ndarray) -> ThermalCase:
    spec_payload = optimization_spec.to_dict() if hasattr(optimization_spec, "to_dict") else dict(optimization_spec)
    candidate_case = apply_decision_vector(base_case, spec_payload, vector)
    payload = candidate_case.to_dict()
    component_bounds, radiator_bounds = _collect_variable_bounds(spec_payload)
    _clamp_target_components(payload["components"], component_bounds)
    _repair_radiator_intervals(payload["boundary_features"], radiator_bounds)
    _resolve_component_overlaps(payload["components"], component_bounds)
    return ThermalCase.from_dict(payload)


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
) -> None:
    for feature_index, fields in radiator_bounds.items():
        feature = boundary_features[feature_index]
        start_bounds = fields.get("start")
        end_bounds = fields.get("end")
        if start_bounds is None or end_bounds is None:
            continue
        start = _clamp(float(feature["start"]), *start_bounds)
        end = _clamp(float(feature["end"]), *end_bounds)
        if end - start < MIN_RADIATOR_SPAN:
            midpoint = 0.5 * (start + end)
            start = _clamp(midpoint - 0.5 * MIN_RADIATOR_SPAN, *start_bounds)
            end = _clamp(midpoint + 0.5 * MIN_RADIATOR_SPAN, *end_bounds)
            if end - start < MIN_RADIATOR_SPAN:
                start = _clamp(end - MIN_RADIATOR_SPAN, *start_bounds)
                end = _clamp(start + MIN_RADIATOR_SPAN, *end_bounds)
        feature["start"] = float(start)
        feature["end"] = float(end)


def _resolve_component_overlaps(
    components: list[dict[str, Any]],
    component_bounds: dict[int, dict[str, tuple[float, float]]],
) -> None:
    movable_indices = set(component_bounds)
    for _ in range(MAX_SEPARATION_PASSES):
        changed = False
        for left_index, right_index in combinations(range(len(components)), 2):
            left = components[left_index]
            right = components[right_index]
            overlap_x = _axis_overlap(
                float(left["pose"]["x"]),
                float(left["geometry"]["width"]),
                float(right["pose"]["x"]),
                float(right["geometry"]["width"]),
            )
            overlap_y = _axis_overlap(
                float(left["pose"]["y"]),
                float(left["geometry"]["height"]),
                float(right["pose"]["y"]),
                float(right["geometry"]["height"]),
            )
            if overlap_x <= 0.0 or overlap_y <= 0.0:
                continue
            changed = True
            if overlap_x <= overlap_y:
                _separate_pair(components, left_index, right_index, movable_indices, component_bounds, axis="x", delta=overlap_x)
            else:
                _separate_pair(components, left_index, right_index, movable_indices, component_bounds, axis="y", delta=overlap_y)
        if not changed:
            return


def _separate_pair(
    components: list[dict[str, Any]],
    left_index: int,
    right_index: int,
    movable_indices: set[int],
    component_bounds: dict[int, dict[str, tuple[float, float]]],
    *,
    axis: str,
    delta: float,
) -> None:
    left = components[left_index]
    right = components[right_index]
    left_value = float(left["pose"][axis])
    right_value = float(right["pose"][axis])
    direction = 1.0 if right_value >= left_value else -1.0
    shift = float(delta) + REPAIR_EPSILON
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


def _axis_overlap(center_a: float, size_a: float, center_b: float, size_b: float) -> float:
    return 0.5 * (size_a + size_b) - abs(center_b - center_a)


def _clamp(value: float, lower_bound: float, upper_bound: float) -> float:
    return max(lower_bound, min(upper_bound, float(value)))
