import pytest

from core.schema.models import ThermalCase
from core.solver.case_to_geometry import interpret_case


def _case_with_source_ratio(ratio: float) -> ThermalCase:
    return ThermalCase.from_dict(
        {
            "schema_version": "1.0",
            "case_meta": {"case_id": "case-001", "scenario_id": "unit-case"},
            "coordinate_system": {"plane": "panel_xy"},
            "panel_domain": {"width": 1.0, "height": 0.8},
            "panel_material_ref": "panel_substrate",
            "materials": {
                "panel_substrate": {"conductivity": 5.0, "emissivity": 0.78},
                "electronics_housing": {"conductivity": 20.0, "emissivity": 0.82},
            },
            "components": [
                {
                    "component_id": "c01-001",
                    "role": "logic_board_01",
                    "shape": "rect",
                    "pose": {"x": 0.45, "y": 0.35, "rotation_deg": 0.0},
                    "geometry": {"width": 0.2, "height": 0.1},
                    "material_ref": "electronics_housing",
                }
            ],
            "boundary_features": [],
            "loads": [
                {
                    "load_id": "load-c01-001",
                    "target_component_id": "c01-001",
                    "total_power": 12.0,
                    "source_area_ratio": ratio,
                }
            ],
            "physics": {"kind": "steady_heat_radiation"},
            "mesh_profile": {"nx": 16, "ny": 12},
            "solver_profile": {"nonlinear_solver": "snes"},
            "provenance": {"source_template_id": "unit-case", "generation_seed": 0},
        }
    )


def test_interpret_case_builds_localized_source_region_from_load_ratio() -> None:
    interpreted = interpret_case(_case_with_source_ratio(0.25))
    component = interpreted["components"][0]

    assert component["source_area"] < component["area"]
    assert component["source_area"] == pytest.approx(component["area"] * 0.25, rel=1.0e-6)
    assert component["source_polygon"].centroid.distance(component["polygon"].centroid) == pytest.approx(0.0)


def test_interpret_case_surfaces_background_boundary_cooling() -> None:
    payload = _case_with_source_ratio(0.25).to_dict()
    payload["physics"] = {
        "kind": "steady_heat_radiation",
        "ambient_temperature": 292.0,
        "background_boundary_cooling": {
            "transfer_coefficient": 1.2,
            "emissivity": 0.72,
        },
    }

    interpreted = interpret_case(ThermalCase.from_dict(payload))

    assert interpreted["ambient_temperature"] == pytest.approx(292.0)
    assert interpreted["background_boundary_cooling"]["transfer_coefficient"] == pytest.approx(1.2)
    assert interpreted["background_boundary_cooling"]["emissivity"] == pytest.approx(0.72)
