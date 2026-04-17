import pytest

from core.schema.validation import (
    SchemaValidationError,
    _validate_background_boundary_cooling,
    validate_scenario_template_payload,
    validate_thermal_case_payload,
)


def _base_template_payload() -> dict:
    return {
        "schema_version": "1.0",
        "template_meta": {
            "template_id": "s1_typical",
            "description": "Single-case s1_typical template.",
        },
        "coordinate_system": {"plane": "panel_xy"},
        "panel_domain": {"width": 1.0, "height": 0.8},
        "placement_regions": [],
        "keep_out_regions": [],
        "component_families": [],
        "boundary_feature_families": [],
        "load_rules": [],
        "material_rules": [
            {"material_id": "panel_substrate", "conductivity": 205.0, "emissivity": 0.78},
        ],
        "physics": {"kind": "steady_heat_radiation", "ambient_temperature": 290.0},
        "mesh_profile": {"nx": 32, "ny": 24},
        "solver_profile": {"nonlinear_solver": "snes"},
        "generation_rules": {"seed_policy": "external"},
    }


def _single_case_template_payload() -> dict:
    return _base_template_payload()


def _base_case_payload() -> dict:
    return {
        "schema_version": "1.0",
        "case_meta": {"case_id": "case-001", "scenario_id": "panel-baseline"},
        "coordinate_system": {"plane": "panel_xy"},
        "panel_domain": {"width": 1.0, "height": 0.8},
        "panel_material_ref": "aluminum",
        "materials": {
            "aluminum": {"conductivity": 205.0, "emissivity": 0.78},
        },
        "components": [
            {
                "component_id": "comp-001",
                "role": "payload",
                "shape": "rect",
                "pose": {"x": 0.3, "y": 0.4, "rotation_deg": 0.0},
                "geometry": {"width": 0.2, "height": 0.1},
                "material_ref": "aluminum",
            }
        ],
        "boundary_features": [
            {
                "feature_id": "sink-top",
                "kind": "line_sink",
                "edge": "top",
                "start": 0.2,
                "end": 0.8,
                "sink_temperature": 280.0,
                "transfer_coefficient": 12.5,
            }
        ],
        "loads": [],
        "physics": {"kind": "steady_heat_radiation"},
        "mesh_profile": {"nx": 32, "ny": 24},
        "solver_profile": {"nonlinear_solver": "snes"},
        "provenance": {"source": "unit-test"},
    }


def test_validate_thermal_case_accepts_supported_shapes_and_line_sink() -> None:
    payload = _base_case_payload()
    payload["components"] = [
        {
            "component_id": "rect-001",
            "role": "payload",
            "shape": "rect",
            "pose": {"x": 0.3, "y": 0.4, "rotation_deg": 0.0},
            "geometry": {"width": 0.2, "height": 0.1},
            "material_ref": "aluminum",
        },
        {
            "component_id": "circle-001",
            "role": "sensor",
            "shape": "circle",
            "pose": {"x": 0.6, "y": 0.3, "rotation_deg": 0.0},
            "geometry": {"radius": 0.05},
            "material_ref": "aluminum",
        },
        {
            "component_id": "capsule-001",
            "role": "battery",
            "shape": "capsule",
            "pose": {"x": 0.7, "y": 0.55, "rotation_deg": 15.0},
            "geometry": {"length": 0.18, "radius": 0.03},
            "material_ref": "aluminum",
        },
        {
            "component_id": "polygon-001",
            "role": "bracket",
            "shape": "polygon",
            "pose": {"x": 0.2, "y": 0.2, "rotation_deg": 0.0},
            "geometry": {"vertices": [[0.0, 0.0], [0.08, 0.0], [0.04, 0.06]]},
            "material_ref": "aluminum",
        },
        {
            "component_id": "slot-001",
            "role": "mount",
            "shape": "slot",
            "pose": {"x": 0.5, "y": 0.65, "rotation_deg": 0.0},
            "geometry": {"length": 0.16, "width": 0.04},
            "material_ref": "aluminum",
        },
    ]

    validate_thermal_case_payload(payload)


def test_validate_thermal_case_rejects_unknown_panel_material_ref() -> None:
    payload = _base_case_payload()
    payload["panel_material_ref"] = "panel_substrate"

    with pytest.raises(SchemaValidationError, match="panel_material_ref"):
        validate_thermal_case_payload(payload)


def test_validate_thermal_case_rejects_unsupported_shape() -> None:
    payload = _base_case_payload()
    payload["components"][0]["shape"] = "triangle"

    with pytest.raises(SchemaValidationError, match="Unsupported shape"):
        validate_thermal_case_payload(payload)


def test_validate_thermal_case_rejects_invalid_polygon_vertices() -> None:
    payload = _base_case_payload()
    payload["components"][0]["shape"] = "polygon"
    payload["components"][0]["geometry"] = {"vertices": [[0.0, 0.0], [0.1, 0.0]]}

    with pytest.raises(SchemaValidationError, match="Polygon"):
        validate_thermal_case_payload(payload)


def test_validate_thermal_case_rejects_invalid_slot_dimensions() -> None:
    payload = _base_case_payload()
    payload["components"][0]["shape"] = "slot"
    payload["components"][0]["geometry"] = {"length": 0.2, "width": 0.0}

    with pytest.raises(SchemaValidationError, match="Slot"):
        validate_thermal_case_payload(payload)


def test_validate_thermal_case_rejects_invalid_line_sink_support() -> None:
    payload = _base_case_payload()
    payload["boundary_features"][0]["end"] = 0.1

    with pytest.raises(SchemaValidationError, match="line_sink"):
        validate_thermal_case_payload(payload)


def test_validate_scenario_template_accepts_single_case_templates_without_operating_case_profiles() -> None:
    payload = _base_template_payload()

    validate_scenario_template_payload(payload)


def test_validate_scenario_template_rejects_legacy_operating_case_profiles() -> None:
    payload = _base_template_payload()
    payload["operating_case_profiles"] = []

    with pytest.raises(SchemaValidationError, match="operating_case_profiles"):
        validate_scenario_template_payload(payload)


def test_validate_scenario_template_accepts_layout_strategy_zones_and_source_area_ratio() -> None:
    payload = _base_template_payload()
    payload["generation_rules"] = {
        "seed_policy": "external",
        "layout_strategy": {
            "kind": "legacy_aligned_dense_core_v1",
            "zones": {
                "dense_core": {"x_min": 0.2, "x_max": 0.8, "y_min": 0.12, "y_max": 0.62},
                "top_sink_band": {"x_min": 0.18, "x_max": 0.82, "y_min": 0.54, "y_max": 0.72},
                "left_io_edge": {"x_min": 0.05, "x_max": 0.18, "y_min": 0.08, "y_max": 0.68},
                "right_service_edge": {"x_min": 0.82, "x_max": 0.95, "y_min": 0.08, "y_max": 0.68},
            },
        },
    }
    payload["load_rules"] = [{"target_family": "c01", "total_power": 12.0, "source_area_ratio": 0.25}]

    validate_scenario_template_payload(payload)


def test_validate_scenario_template_rejects_invalid_source_area_ratio() -> None:
    payload = _base_template_payload()
    payload["load_rules"] = [{"target_family": "c01", "total_power": 12.0, "source_area_ratio": 1.25}]

    with pytest.raises(SchemaValidationError, match="source_area_ratio"):
        validate_scenario_template_payload(payload)


def test_validate_scenario_template_accepts_background_boundary_cooling() -> None:
    payload = _base_template_payload()
    payload["physics"] = {
        "kind": "steady_heat_radiation",
        "ambient_temperature": 292.0,
        "background_boundary_cooling": {
            "transfer_coefficient": 1.2,
            "emissivity": 0.72,
        },
    }
    payload["load_rules"] = [
        {"target_family": "c01", "total_power": 8.0, "source_area_ratio": 0.35}
    ]

    validate_scenario_template_payload(payload)


def test_validate_scenario_template_rejects_invalid_background_boundary_emissivity() -> None:
    payload = _base_template_payload()
    payload["physics"] = {
        "kind": "steady_heat_radiation",
        "ambient_temperature": 292.0,
        "background_boundary_cooling": {
            "transfer_coefficient": 1.2,
            "emissivity": 1.5,
        },
    }

    with pytest.raises(SchemaValidationError, match="background_boundary_cooling"):
        validate_scenario_template_payload(payload)


def test_background_boundary_cooling_accepts_zero_transfer_coefficient() -> None:
    """transfer_coefficient=0 is a legitimate 'no convective cooling' configuration and must be accepted."""
    payload = {"transfer_coefficient": 0.0, "emissivity": 0.02}
    _validate_background_boundary_cooling(payload, "physics.background_boundary_cooling")


def test_background_boundary_cooling_rejects_negative_transfer_coefficient() -> None:
    payload = {"transfer_coefficient": -0.1, "emissivity": 0.02}
    with pytest.raises(SchemaValidationError, match="transfer_coefficient"):
        _validate_background_boundary_cooling(payload, "physics.background_boundary_cooling")
