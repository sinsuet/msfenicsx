import numpy as np
import pytest

from core.schema.models import ThermalCase
from optimizers.codec import DecisionVectorError, apply_decision_vector, extract_decision_vector
from optimizers.models import OptimizationSpec


def _case() -> ThermalCase:
    return ThermalCase.from_dict(
        {
            "schema_version": "1.0",
            "case_meta": {"case_id": "case-001", "scenario_id": "panel-baseline"},
            "coordinate_system": {"plane": "panel_xy"},
            "panel_domain": {"width": 1.0, "height": 0.8},
            "materials": {"aluminum": {"conductivity": 205.0, "emissivity": 0.78}},
            "components": [
                {
                    "component_id": "comp-001",
                    "role": "payload",
                    "shape": "rect",
                    "pose": {"x": 0.3, "y": 0.35, "rotation_deg": 0.0},
                    "geometry": {"width": 0.16, "height": 0.09},
                    "material_ref": "aluminum",
                }
            ],
            "boundary_features": [],
            "loads": [{"load_id": "load-001", "target_component_id": "comp-001", "total_power": 18.0}],
            "physics": {"kind": "steady_heat_radiation"},
            "mesh_profile": {"nx": 12, "ny": 10},
            "solver_profile": {"nonlinear_solver": "snes"},
            "provenance": {"source": "unit-test"},
        }
    )


def _spec() -> OptimizationSpec:
    return OptimizationSpec.from_dict(
        {
            "schema_version": "1.0",
            "spec_meta": {"spec_id": "position-search", "description": "Payload position search."},
            "design_variables": [
                {
                    "variable_id": "payload_x",
                    "path": "components[0].pose.x",
                    "lower_bound": 0.08,
                    "upper_bound": 0.92,
                },
                {
                    "variable_id": "payload_y",
                    "path": "components[0].pose.y",
                    "lower_bound": 0.045,
                    "upper_bound": 0.755,
                },
            ],
            "algorithm": {"name": "pymoo_nsga2", "population_size": 4, "num_generations": 1, "seed": 7},
            "evaluation_protocol": {"evaluation_spec_path": "unused.yaml"},
        }
    )


def test_extract_and_apply_decision_vector_round_trip() -> None:
    case = _case()
    spec = _spec()

    vector = extract_decision_vector(case, spec)
    mutated = apply_decision_vector(case, spec, np.array([0.5, 0.6]))

    assert vector.tolist() == [0.3, 0.35]
    assert mutated.components[0]["pose"]["x"] == pytest.approx(0.5)
    assert mutated.components[0]["pose"]["y"] == pytest.approx(0.6)
    assert case.components[0]["pose"]["x"] == pytest.approx(0.3)


def test_apply_decision_vector_rejects_out_of_bounds_values() -> None:
    with pytest.raises(DecisionVectorError):
        apply_decision_vector(_case(), _spec(), np.array([1.2, 0.6]))
