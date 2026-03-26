import pytest

from core.schema.validation import SchemaValidationError, validate_thermal_case_payload


def _base_case_payload() -> dict:
    return {
        "schema_version": "1.0",
        "case_meta": {"case_id": "case-001", "scenario_id": "panel-baseline"},
        "coordinate_system": {"plane": "panel_xy"},
        "panel_domain": {"width": 1.0, "height": 0.8},
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
