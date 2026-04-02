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
    _require_mapping(payload["mesh_profile"], "mesh_profile")
    _require_mapping(payload["solver_profile"], "solver_profile")
    _require_mapping(payload["generation_rules"], "generation_rules")
    for family in payload["component_families"]:
        _validate_component_family(family)
    for family in payload["boundary_feature_families"]:
        _validate_boundary_feature_family(family)
    operating_case_profiles = payload.get("operating_case_profiles", [])
    _require_sequence(operating_case_profiles, "operating_case_profiles")
    _validate_operating_case_profiles(operating_case_profiles)


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


def _validate_boundary_feature_family(family: Any) -> None:
    _require_mapping(family, "boundary_feature_family")
    kind = family.get("kind")
    if kind is not None and kind != "line_sink":
        raise SchemaValidationError(f"Unsupported boundary feature kind '{kind}'.")


def _validate_operating_case_profiles(profiles: Sequence[Any]) -> None:
    operating_case_ids: set[str] = set()
    for profile in profiles:
        _require_mapping(profile, "operating_case_profile")
        operating_case_id = profile.get("operating_case_id")
        if not isinstance(operating_case_id, str) or not operating_case_id:
            raise SchemaValidationError("operating_case_profile.operating_case_id must be a non-empty string.")
        if operating_case_id in operating_case_ids:
            raise SchemaValidationError(f"Duplicate operating_case_id '{operating_case_id}' in operating_case_profiles.")
        operating_case_ids.add(operating_case_id)
        _require_positive_real(profile.get("ambient_temperature"), f"ambient_temperature for {operating_case_id}")
        component_power_overrides = profile.get("component_power_overrides")
        boundary_feature_overrides = profile.get("boundary_feature_overrides")
        _require_mapping(component_power_overrides, f"component_power_overrides for {operating_case_id}")
        _require_mapping(boundary_feature_overrides, f"boundary_feature_overrides for {operating_case_id}")


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
