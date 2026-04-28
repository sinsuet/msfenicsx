"""Validation helpers for canonical schema payloads."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from numbers import Real
from typing import Any


class SchemaValidationError(ValueError):
    """Raised when a canonical schema payload is invalid."""


SUPPORTED_COMPONENT_SHAPES = {"rect", "circle", "capsule", "polygon", "slot"}
SUPPORTED_LINE_SINK_EDGES = {"left", "right", "top", "bottom"}


def validate_scenario_template_payload(payload: Mapping[str, Any]) -> None:
    required_keys = (
        "schema_version",
        "template_meta",
        "coordinate_system",
        "panel_domain",
        "placement_regions",
        "keep_out_regions",
        "component_families",
        "boundary_feature_families",
        "load_rules",
        "material_rules",
        "physics",
        "mesh_profile",
        "solver_profile",
        "generation_rules",
    )
    _require_mapping(payload, "ScenarioTemplate")
    _require_required_keys(payload, required_keys, "ScenarioTemplate")
    _require_mapping(payload["template_meta"], "template_meta")
    _require_mapping(payload["coordinate_system"], "coordinate_system")
    _validate_panel_domain(payload["panel_domain"])
    _require_sequence(payload["placement_regions"], "placement_regions")
    _require_sequence(payload["keep_out_regions"], "keep_out_regions")
    _require_sequence(payload["component_families"], "component_families")
    _require_sequence(payload["boundary_feature_families"], "boundary_feature_families")
    _require_sequence(payload["load_rules"], "load_rules")
    _require_sequence(payload["material_rules"], "material_rules")
    _require_mapping(payload["physics"], "physics")
    _require_mapping(payload["mesh_profile"], "mesh_profile")
    _require_mapping(payload["solver_profile"], "solver_profile")
    _require_mapping(payload["generation_rules"], "generation_rules")
    if "operating_case_profiles" in payload:
        raise SchemaValidationError(
            "ScenarioTemplate.operating_case_profiles has been retired; use single-case templates only."
        )
    for family in payload["component_families"]:
        _validate_component_family(family)
    for family in payload["boundary_feature_families"]:
        _validate_boundary_feature_family(family)
    for load_rule in payload["load_rules"]:
        _validate_load_rule(load_rule)
    _validate_physics(payload["physics"], "physics")
    _validate_generation_rules(payload["generation_rules"])


def validate_thermal_case_payload(payload: Mapping[str, Any]) -> None:
    required_keys = (
        "schema_version",
        "case_meta",
        "coordinate_system",
        "panel_domain",
        "panel_material_ref",
        "materials",
        "components",
        "boundary_features",
        "loads",
        "physics",
        "mesh_profile",
        "solver_profile",
        "provenance",
    )
    _require_mapping(payload, "ThermalCase")
    _require_required_keys(payload, required_keys, "ThermalCase")
    _require_mapping(payload["case_meta"], "case_meta")
    _require_mapping(payload["coordinate_system"], "coordinate_system")
    _validate_panel_domain(payload["panel_domain"])
    _require_mapping(payload["materials"], "materials")
    panel_material_ref = payload["panel_material_ref"]
    if not isinstance(panel_material_ref, str) or not panel_material_ref:
        raise SchemaValidationError("panel_material_ref must be a non-empty string.")
    if panel_material_ref not in payload["materials"]:
        raise SchemaValidationError(f"panel_material_ref '{panel_material_ref}' is not defined in materials.")
    _require_sequence(payload["components"], "components")
    _require_sequence(payload["boundary_features"], "boundary_features")
    _require_sequence(payload["loads"], "loads")
    _require_mapping(payload["physics"], "physics")
    _require_mapping(payload["mesh_profile"], "mesh_profile")
    _require_mapping(payload["solver_profile"], "solver_profile")
    _require_mapping(payload["provenance"], "provenance")
    for component in payload["components"]:
        _validate_component(component)
    for feature in payload["boundary_features"]:
        _validate_boundary_feature(feature)
    _validate_physics(payload["physics"], "physics")


def validate_thermal_solution_payload(payload: Mapping[str, Any]) -> None:
    required_keys = (
        "schema_version",
        "solution_meta",
        "solver_diagnostics",
        "field_records",
        "summary_metrics",
        "component_summaries",
        "provenance",
    )
    _require_mapping(payload, "ThermalSolution")
    _require_required_keys(payload, required_keys, "ThermalSolution")
    _require_mapping(payload["solution_meta"], "solution_meta")
    _require_mapping(payload["solver_diagnostics"], "solver_diagnostics")
    _require_mapping(payload["field_records"], "field_records")
    _require_mapping(payload["summary_metrics"], "summary_metrics")
    _require_sequence(payload["component_summaries"], "component_summaries")
    _require_mapping(payload["provenance"], "provenance")


def _validate_panel_domain(panel_domain: Any) -> None:
    _require_mapping(panel_domain, "panel_domain")
    width = _require_positive_real(panel_domain.get("width"), "panel_domain.width")
    height = _require_positive_real(panel_domain.get("height"), "panel_domain.height")
    if width <= 0 or height <= 0:
        raise SchemaValidationError("panel_domain must provide positive width and height.")


def _validate_component_family(family: Any) -> None:
    _require_mapping(family, "component_family")
    shape = family.get("shape")
    if shape is not None and shape not in SUPPORTED_COMPONENT_SHAPES:
        raise SchemaValidationError(f"Unsupported shape '{shape}' in component family.")
    layout_tags = family.get("layout_tags", [])
    if not isinstance(layout_tags, Sequence) or isinstance(layout_tags, (str, bytes, bytearray)):
        raise SchemaValidationError("component_family.layout_tags must be a sequence when provided.")
    for tag in layout_tags:
        if not isinstance(tag, str) or not tag:
            raise SchemaValidationError("component_family.layout_tags entries must be non-empty strings.")
    placement_hint = family.get("placement_hint")
    if placement_hint is not None and (not isinstance(placement_hint, str) or not placement_hint):
        raise SchemaValidationError("component_family.placement_hint must be a non-empty string when provided.")
    pose_hint = family.get("pose_hint")
    if pose_hint is not None:
        _require_mapping(pose_hint, "component_family.pose_hint")
        _require_real(pose_hint.get("x"), "component_family.pose_hint.x")
        _require_real(pose_hint.get("y"), "component_family.pose_hint.y")
    adjacency_group = family.get("adjacency_group")
    if adjacency_group is not None and (not isinstance(adjacency_group, str) or not adjacency_group):
        raise SchemaValidationError("component_family.adjacency_group must be a non-empty string when provided.")
    clearance = family.get("clearance")
    if clearance is not None:
        _require_positive_real(clearance, "component_family.clearance")


def _validate_boundary_feature_family(family: Any) -> None:
    _require_mapping(family, "boundary_feature_family")
    kind = family.get("kind")
    if kind is not None and kind != "line_sink":
        raise SchemaValidationError(f"Unsupported boundary feature kind '{kind}'.")


def _validate_load_rule(rule: Any) -> None:
    _require_mapping(rule, "load_rule")
    target_family = rule.get("target_family")
    if not isinstance(target_family, str) or not target_family:
        raise SchemaValidationError("load_rule.target_family must be a non-empty string.")
    _require_positive_spec(rule.get("total_power"), f"load_rule.total_power for {target_family}")
    if "source_area_ratio" in rule:
        _require_ratio_spec(rule.get("source_area_ratio"), f"load_rule.source_area_ratio for {target_family}")


def _validate_generation_rules(generation_rules: Mapping[str, Any]) -> None:
    layout_strategy = generation_rules.get("layout_strategy")
    if layout_strategy is None:
        return
    _require_mapping(layout_strategy, "generation_rules.layout_strategy")
    kind = layout_strategy.get("kind")
    if not isinstance(kind, str) or not kind:
        raise SchemaValidationError("generation_rules.layout_strategy.kind must be a non-empty string.")
    zones = layout_strategy.get("zones")
    _require_mapping(zones, "generation_rules.layout_strategy.zones")
    for zone_name, zone in zones.items():
        if not isinstance(zone_name, str) or not zone_name:
            raise SchemaValidationError("generation_rules.layout_strategy.zones keys must be non-empty strings.")
        _validate_rect_region(zone, f"generation_rules.layout_strategy.zones[{zone_name}]")


def _validate_physics(payload: Any, label: str) -> None:
    _require_mapping(payload, label)
    kind = payload.get("kind")
    if not isinstance(kind, str) or not kind:
        raise SchemaValidationError(f"{label}.kind must be a non-empty string.")
    ambient_temperature = payload.get("ambient_temperature")
    if ambient_temperature is not None:
        _require_positive_real(ambient_temperature, f"{label}.ambient_temperature")
    background_boundary_cooling = payload.get("background_boundary_cooling")
    if background_boundary_cooling is not None:
        _validate_background_boundary_cooling(
            background_boundary_cooling,
            f"{label}.background_boundary_cooling",
        )


def _validate_background_boundary_cooling(payload: Any, label: str) -> None:
    _require_mapping(payload, label)
    transfer_coefficient = _require_real(
        payload.get("transfer_coefficient"), f"{label}.transfer_coefficient"
    )
    if transfer_coefficient < 0.0:
        raise SchemaValidationError(f"{label}.transfer_coefficient must be >= 0.")
    emissivity = _require_real(payload.get("emissivity"), f"{label}.emissivity")
    if not 0.0 < emissivity <= 1.0:
        raise SchemaValidationError(f"{label}.emissivity must satisfy 0 < value <= 1.")


def _validate_component(component: Any) -> None:
    _require_mapping(component, "component")
    required_keys = ("component_id", "role", "shape", "pose", "geometry", "material_ref")
    _require_required_keys(component, required_keys, "component")
    shape = component["shape"]
    if shape not in SUPPORTED_COMPONENT_SHAPES:
        raise SchemaValidationError(f"Unsupported shape '{shape}' for component {component['component_id']}.")
    _validate_pose(component["pose"], component["component_id"])
    geometry = component["geometry"]
    _require_mapping(geometry, f"geometry for component {component['component_id']}")
    if shape == "rect":
        _require_positive_real(geometry.get("width"), "Rect geometry width")
        _require_positive_real(geometry.get("height"), "Rect geometry height")
    elif shape == "circle":
        _require_positive_real(geometry.get("radius"), "Circle geometry radius")
    elif shape == "capsule":
        _require_positive_real(geometry.get("length"), "Capsule geometry length")
        _require_positive_real(geometry.get("radius"), "Capsule geometry radius")
    elif shape == "polygon":
        vertices = geometry.get("vertices")
        if not isinstance(vertices, Sequence) or isinstance(vertices, (str, bytes)) or len(vertices) < 3:
            raise SchemaValidationError(
                f"Polygon geometry for component {component['component_id']} must define at least three 2D vertices."
            )
        for vertex in vertices:
            if not isinstance(vertex, Sequence) or len(vertex) != 2:
                raise SchemaValidationError(
                    f"Polygon geometry for component {component['component_id']} must define 2D vertices."
                )
            _require_real(vertex[0], "Polygon vertex x")
            _require_real(vertex[1], "Polygon vertex y")
    elif shape == "slot":
        length = _require_positive_real(geometry.get("length"), "Slot geometry length")
        width = _require_positive_real(geometry.get("width"), "Slot geometry width")
        if width > length:
            raise SchemaValidationError(
                f"Slot geometry for component {component['component_id']} must have width <= length."
            )


def _validate_pose(pose: Any, component_id: str) -> None:
    _require_mapping(pose, f"pose for component {component_id}")
    _require_real(pose.get("x"), f"pose.x for component {component_id}")
    _require_real(pose.get("y"), f"pose.y for component {component_id}")
    _require_real(pose.get("rotation_deg"), f"pose.rotation_deg for component {component_id}")


def _validate_boundary_feature(feature: Any) -> None:
    _require_mapping(feature, "boundary_feature")
    required_keys = (
        "feature_id",
        "kind",
        "edge",
        "start",
        "end",
        "sink_temperature",
        "transfer_coefficient",
    )
    _require_required_keys(feature, required_keys, "boundary_feature")
    if feature["kind"] != "line_sink":
        raise SchemaValidationError(f"Unsupported boundary feature kind '{feature['kind']}'.")
    if feature["edge"] not in SUPPORTED_LINE_SINK_EDGES:
        raise SchemaValidationError(
            f"line_sink feature {feature['feature_id']} must use one of {sorted(SUPPORTED_LINE_SINK_EDGES)}."
        )
    start = _require_real(feature["start"], f"line_sink start for {feature['feature_id']}")
    end = _require_real(feature["end"], f"line_sink end for {feature['feature_id']}")
    if not 0.0 <= start < end <= 1.0:
        raise SchemaValidationError(
            f"line_sink feature {feature['feature_id']} must satisfy 0 <= start < end <= 1."
        )
    _require_positive_real(feature["sink_temperature"], f"line_sink sink_temperature for {feature['feature_id']}")
    _require_positive_real(
        feature["transfer_coefficient"],
        f"line_sink transfer_coefficient for {feature['feature_id']}",
    )


def _validate_rect_region(region: Any, label: str) -> None:
    _require_mapping(region, label)
    x_min = _require_real(region.get("x_min"), f"{label}.x_min")
    x_max = _require_real(region.get("x_max"), f"{label}.x_max")
    y_min = _require_real(region.get("y_min"), f"{label}.y_min")
    y_max = _require_real(region.get("y_max"), f"{label}.y_max")
    if x_min >= x_max:
        raise SchemaValidationError(f"{label} must satisfy x_min < x_max.")
    if y_min >= y_max:
        raise SchemaValidationError(f"{label} must satisfy y_min < y_max.")


def _require_positive_spec(value: Any, label: str) -> None:
    if isinstance(value, Mapping):
        minimum = _require_positive_real(value.get("min"), f"{label}.min")
        maximum = _require_positive_real(value.get("max"), f"{label}.max")
        if minimum > maximum:
            raise SchemaValidationError(f"{label} must satisfy min <= max.")
        return
    _require_positive_real(value, label)


def _require_ratio_spec(value: Any, label: str) -> None:
    if isinstance(value, Mapping):
        minimum = _require_real(value.get("min"), f"{label}.min")
        maximum = _require_real(value.get("max"), f"{label}.max")
        if not 0.0 < minimum <= maximum <= 1.0:
            raise SchemaValidationError(f"{label} must satisfy 0 < min <= max <= 1.")
        return
    numeric_value = _require_real(value, label)
    if not 0.0 < numeric_value <= 1.0:
        raise SchemaValidationError(f"{label} must satisfy 0 < value <= 1.")


def _require_required_keys(payload: Mapping[str, Any], required_keys: Sequence[str], label: str) -> None:
    missing = [key for key in required_keys if key not in payload]
    if missing:
        raise SchemaValidationError(f"{label} is missing required keys: {', '.join(missing)}.")


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(f"{label} must be a mapping.")
    return value


def _require_sequence(value: Any, label: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise SchemaValidationError(f"{label} must be a sequence.")
    return value


def _require_real(value: Any, label: str) -> float:
    if not isinstance(value, Real):
        raise SchemaValidationError(f"{label} must be a real number.")
    return float(value)


def _require_positive_real(value: Any, label: str) -> float:
    numeric_value = _require_real(value, label)
    if numeric_value <= 0.0:
        raise SchemaValidationError(f"{label} must be positive.")
    return numeric_value
