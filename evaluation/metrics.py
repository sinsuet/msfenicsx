"""Metric extraction for evaluation specs."""

from __future__ import annotations

from collections.abc import Mapping
from numbers import Real
from typing import Any


class MetricResolutionError(ValueError):
    """Raised when an evaluation metric key cannot be resolved."""


BASE_METRIC_KEYS = {
    "case.total_radiator_span",
    "case.component_count",
    "case.panel_area",
    "case.power_density",
    "case.total_power",
    "components.max_temperature_spread",
    "solver.iterations",
    "summary.temperature_max",
    "summary.temperature_mean",
    "summary.temperature_min",
    "summary.temperature_span",
}


def resolve_metric_value(case_payload: Mapping[str, Any], solution_payload: Mapping[str, Any], metric_key: str) -> float:
    parts = metric_key.split(".")
    if parts[0] == "summary" and len(parts) == 2:
        return _resolve_summary_metric(case_payload, solution_payload, parts[1], metric_key)
    if parts[0] == "solver" and len(parts) == 2:
        return _require_numeric(solution_payload["solver_diagnostics"].get(parts[1]), metric_key)
    if parts[0] == "component" and len(parts) == 3:
        component = _find_component_summary(case_payload["components"], solution_payload["component_summaries"], parts[1])
        return _require_numeric(component.get(parts[2]), metric_key)
    if parts[0] == "components" and len(parts) == 2:
        return _resolve_components_metric(solution_payload["component_summaries"], parts[1], metric_key)
    if parts[0] == "case" and len(parts) == 2:
        return _resolve_case_metric(case_payload, parts[1], metric_key)
    raise MetricResolutionError(f"Unsupported metric key '{metric_key}'.")


def build_metric_values(
    case_payload: Mapping[str, Any],
    solution_payload: Mapping[str, Any],
    required_metric_keys: set[str],
) -> dict[str, float]:
    metric_keys = BASE_METRIC_KEYS | required_metric_keys
    return {
        metric_key: resolve_metric_value(case_payload, solution_payload, metric_key)
        for metric_key in sorted(metric_keys)
    }


def build_derived_signals(case_payload: Mapping[str, Any], solution_payload: Mapping[str, Any]) -> dict[str, Any]:
    component_summaries = solution_payload["component_summaries"]
    hotspot_component_id = None
    hotspot_temperature_max = float(solution_payload["summary_metrics"]["temperature_max"])
    if component_summaries:
        hottest_component = max(component_summaries, key=lambda item: float(item["temperature_max"]))
        hotspot_component_id = hottest_component["component_id"]
        hotspot_temperature_max = float(hottest_component["temperature_max"])
    panel_area = resolve_metric_value(case_payload, solution_payload, "case.panel_area")
    total_power = resolve_metric_value(case_payload, solution_payload, "case.total_power")
    power_density = resolve_metric_value(case_payload, solution_payload, "case.power_density")
    return {
        "hotspot_component_id": hotspot_component_id,
        "hotspot_temperature_max": hotspot_temperature_max,
        "panel_area": panel_area,
        "total_power": total_power,
        "power_density": power_density,
    }


def _resolve_case_metric(case_payload: Mapping[str, Any], field: str, metric_key: str) -> float:
    if field == "component_count":
        return float(len(case_payload["components"]))
    if field == "panel_area":
        panel_domain = case_payload["panel_domain"]
        return float(panel_domain["width"]) * float(panel_domain["height"])
    if field == "total_power":
        return float(sum(float(load["total_power"]) for load in case_payload["loads"]))
    if field == "power_density":
        panel_area = _resolve_case_metric(case_payload, "panel_area", metric_key)
        if panel_area <= 0.0:
            raise MetricResolutionError("case.panel_area must be positive to derive case.power_density.")
        total_power = _resolve_case_metric(case_payload, "total_power", metric_key)
        return total_power / panel_area
    if field == "total_radiator_span":
        return float(
            sum(
                float(feature["end"]) - float(feature["start"])
                for feature in case_payload["boundary_features"]
                if feature.get("kind") == "line_sink"
            )
        )
    raise MetricResolutionError(f"Unsupported case metric key '{metric_key}'.")


def _resolve_summary_metric(
    case_payload: Mapping[str, Any],
    solution_payload: Mapping[str, Any],
    field: str,
    metric_key: str,
) -> float:
    if field in {"temperature_min", "temperature_mean", "temperature_max"}:
        return _require_numeric(solution_payload["summary_metrics"].get(field), metric_key)
    if field == "temperature_span":
        return _require_numeric(solution_payload["summary_metrics"].get("temperature_max"), metric_key) - _require_numeric(
            solution_payload["summary_metrics"].get("temperature_min"), metric_key
        )
    if field == "temperature_rise":
        ambient_temperature = _require_numeric(case_payload["physics"].get("ambient_temperature"), "physics.ambient_temperature")
        return _require_numeric(solution_payload["summary_metrics"].get("temperature_max"), metric_key) - ambient_temperature
    raise MetricResolutionError(f"Unsupported summary metric key '{metric_key}'.")


def _resolve_components_metric(component_summaries: list[dict[str, Any]], field: str, metric_key: str) -> float:
    if field != "max_temperature_spread":
        raise MetricResolutionError(f"Unsupported components metric key '{metric_key}'.")
    if not component_summaries:
        return 0.0
    means = [float(component["temperature_mean"]) for component in component_summaries]
    return float(max(means) - min(means))


def _find_component_summary(
    case_components: list[dict[str, Any]],
    component_summaries: list[dict[str, Any]],
    component_selector: str,
) -> Mapping[str, Any]:
    for component_summary in component_summaries:
        if component_summary.get("component_id") == component_selector:
            return component_summary

    matching_components = [component for component in case_components if component.get("role") == component_selector]
    if len(matching_components) == 1:
        component_id = matching_components[0]["component_id"]
        for component_summary in component_summaries:
            if component_summary.get("component_id") == component_id:
                return component_summary
        raise MetricResolutionError(f"Component summary '{component_id}' is not available in thermal_solution.")
    if len(matching_components) > 1:
        raise MetricResolutionError(
            f"Component selector '{component_selector}' matches multiple case components; use component_id instead."
        )
    for component_summary in component_summaries:
        if component_summary.get("component_id") == component_selector:
            return component_summary
    raise MetricResolutionError(f"Component summary '{component_selector}' is not available in thermal_solution.")


def _require_numeric(value: Any, metric_key: str) -> float:
    if not isinstance(value, Real):
        raise MetricResolutionError(f"Metric '{metric_key}' did not resolve to a numeric value.")
    return float(value)
