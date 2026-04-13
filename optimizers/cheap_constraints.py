"""Cheap legality screening helpers that run before PDE solves."""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import Any

from core.geometry.layout_rules import (
    component_within_domain,
    components_violate_clearance,
    validate_line_sink_edge_segment,
)


@dataclass(slots=True, frozen=True)
class SinkInterval:
    start: float
    end: float


@dataclass(slots=True)
class CheapConstraintResult:
    feasible: bool
    constraint_values: dict[str, float] = field(default_factory=dict)
    geometry_issues: list[str] = field(default_factory=list)


def resolve_radiator_span_max(evaluation_spec: Any) -> float | None:
    spec_payload = evaluation_spec.to_dict() if hasattr(evaluation_spec, "to_dict") else dict(evaluation_spec)
    limits = [
        float(constraint["limit"])
        for constraint in spec_payload.get("constraints", [])
        if constraint.get("metric") == "case.total_radiator_span" and constraint.get("relation") == "<="
    ]
    if not limits:
        return None
    return min(limits)


def project_sink_interval(
    start: float,
    end: float,
    span_max: float,
    *,
    lower_bound: float = 0.0,
    upper_bound: float = 1.0,
    min_span: float = 0.0,
    start_bounds: tuple[float, float] | None = None,
    end_bounds: tuple[float, float] | None = None,
) -> SinkInterval:
    ordered_start = min(float(start), float(end))
    ordered_end = max(float(start), float(end))
    lower_bound = float(lower_bound)
    upper_bound = float(upper_bound)
    start_lower, start_upper = (
        (float(start_bounds[0]), float(start_bounds[1]))
        if start_bounds is not None
        else (lower_bound, upper_bound)
    )
    end_lower, end_upper = (
        (float(end_bounds[0]), float(end_bounds[1]))
        if end_bounds is not None
        else (lower_bound, upper_bound)
    )
    interval_width = max(0.0, min(upper_bound, end_upper) - max(lower_bound, start_lower))
    span_floor = max(0.0, float(min_span))
    span_ceiling = max(0.0, float(span_max))
    max_feasible_span = max(0.0, min(span_ceiling, end_upper - start_lower, upper_bound - lower_bound))
    if span_ceiling < span_floor:
        target_span = min(max_feasible_span, interval_width)
    else:
        target_span = min(max(ordered_end - ordered_start, span_floor), max_feasible_span, interval_width)
    midpoint = 0.5 * (ordered_start + ordered_end)
    feasible_start_lower = max(lower_bound, start_lower, end_lower - target_span)
    feasible_start_upper = min(start_upper, upper_bound - target_span, end_upper - target_span)
    if feasible_start_upper < feasible_start_lower:
        projected_start = float(feasible_start_lower)
    else:
        desired_start = midpoint - 0.5 * target_span
        projected_start = min(max(desired_start, feasible_start_lower), feasible_start_upper)
    projected_end = projected_start + target_span
    return SinkInterval(start=float(projected_start), end=float(projected_end))


def evaluate_cheap_constraints(case: Any, evaluation_spec: Any) -> CheapConstraintResult:
    case_payload = case.to_dict() if hasattr(case, "to_dict") else dict(case)
    spec_payload = evaluation_spec.to_dict() if hasattr(evaluation_spec, "to_dict") else dict(evaluation_spec)
    geometry_issues = _geometry_issues(case_payload)
    constraint_values: dict[str, float] = {}
    for constraint in spec_payload.get("constraints", []):
        if constraint.get("metric") != "case.total_radiator_span":
            continue
        actual = _total_radiator_span(case_payload)
        limit = float(constraint["limit"])
        relation = str(constraint["relation"])
        if relation == "<=":
            violation = max(0.0, actual - limit)
        elif relation == ">=":
            violation = max(0.0, limit - actual)
        else:
            raise ValueError(f"Unsupported cheap constraint relation '{relation}'.")
        constraint_values[str(constraint["constraint_id"])] = float(violation)
    feasible = not geometry_issues and all(value <= 1.0e-12 for value in constraint_values.values())
    return CheapConstraintResult(
        feasible=feasible,
        constraint_values=constraint_values,
        geometry_issues=geometry_issues,
    )


def _total_radiator_span(case_payload: dict[str, Any]) -> float:
    return float(
        sum(
            float(feature["end"]) - float(feature["start"])
            for feature in case_payload.get("boundary_features", [])
            if feature.get("kind") == "line_sink"
        )
    )


def _geometry_issues(case_payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    panel_domain = case_payload["panel_domain"]
    components = case_payload.get("components", [])
    clearance_by_family = {
        str(component.get("family_id", "")): float(component.get("clearance", 0.0))
        for component in components
        if component.get("family_id") is not None
    }
    for component in components:
        component_id = str(component.get("component_id", "unknown"))
        if not component_within_domain(component, panel_domain):
            issues.append(f"component_outside_domain:{component_id}")
    for left, right in combinations(components, 2):
        if components_violate_clearance(left, right, clearance_by_family):
            issues.append(f"clearance_violation:{left['component_id']}:{right['component_id']}")
    for feature in case_payload.get("boundary_features", []):
        if not validate_line_sink_edge_segment(feature):
            issues.append(f"invalid_line_sink:{feature['feature_id']}")
    return issues
