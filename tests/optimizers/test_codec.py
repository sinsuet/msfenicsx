import numpy as np
import pytest

from core.generator.paired_pipeline import generate_operating_case_pair
from optimizers.codec import DecisionVectorError, apply_decision_vector, extract_decision_vector
from optimizers.models import OptimizationSpec


def _case():
    return generate_operating_case_pair("scenarios/templates/panel_four_component_hot_cold_benchmark.yaml", seed=11)["hot"]


def _spec() -> OptimizationSpec:
    return OptimizationSpec.from_dict(
        {
            "schema_version": "1.0",
            "spec_meta": {"spec_id": "panel-four-component-hot-cold-nsga2-b0", "description": "B0 benchmark search."},
            "benchmark_source": {
                "template_path": "scenarios/templates/panel_four_component_hot_cold_benchmark.yaml",
                "seed": 11,
            },
            "design_variables": [
                {
                    "variable_id": "processor_x",
                    "path": "components[0].pose.x",
                    "lower_bound": 0.12,
                    "upper_bound": 0.88,
                },
                {
                    "variable_id": "processor_y",
                    "path": "components[0].pose.y",
                    "lower_bound": 0.12,
                    "upper_bound": 0.66,
                },
                {
                    "variable_id": "rf_power_amp_x",
                    "path": "components[1].pose.x",
                    "lower_bound": 0.12,
                    "upper_bound": 0.88,
                },
                {
                    "variable_id": "rf_power_amp_y",
                    "path": "components[1].pose.y",
                    "lower_bound": 0.12,
                    "upper_bound": 0.66,
                },
                {
                    "variable_id": "battery_pack_x",
                    "path": "components[3].pose.x",
                    "lower_bound": 0.12,
                    "upper_bound": 0.88,
                },
                {
                    "variable_id": "battery_pack_y",
                    "path": "components[3].pose.y",
                    "lower_bound": 0.12,
                    "upper_bound": 0.66,
                },
                {
                    "variable_id": "radiator_start",
                    "path": "boundary_features[0].start",
                    "lower_bound": 0.05,
                    "upper_bound": 0.7,
                },
                {
                    "variable_id": "radiator_end",
                    "path": "boundary_features[0].end",
                    "lower_bound": 0.2,
                    "upper_bound": 0.95,
                },
            ],
            "algorithm": {
                "family": "genetic",
                "backbone": "nsga2",
                "mode": "raw",
                "population_size": 4,
                "num_generations": 1,
                "seed": 7,
            },
            "evaluation_protocol": {"evaluation_spec_path": "unused.yaml"},
        }
    )


def test_extract_and_apply_decision_vector_round_trip_for_b0_layout_variables() -> None:
    case = _case()
    spec = _spec()

    vector = extract_decision_vector(case, spec)
    mutated = apply_decision_vector(case, spec, np.array([0.42, 0.6, 0.74, 0.58, 0.33, 0.22, 0.12, 0.88]))

    assert vector.tolist() == pytest.approx([0.465458, 0.418131, 0.823217, 0.365615, 0.598222, 0.54933, 0.25, 0.75])
    assert mutated.components[0]["pose"]["x"] == pytest.approx(0.42)
    assert mutated.components[0]["pose"]["y"] == pytest.approx(0.6)
    assert mutated.components[1]["pose"]["x"] == pytest.approx(0.74)
    assert mutated.components[3]["pose"]["y"] == pytest.approx(0.22)
    assert mutated.boundary_features[0]["start"] == pytest.approx(0.12)
    assert mutated.boundary_features[0]["end"] == pytest.approx(0.88)
    assert case.components[0]["pose"]["x"] == pytest.approx(0.465458)


def test_apply_decision_vector_rejects_out_of_bounds_values() -> None:
    with pytest.raises(DecisionVectorError):
        apply_decision_vector(_case(), _spec(), np.array([1.2, 0.6, 0.74, 0.58, 0.33, 0.22, 0.12, 0.88]))
