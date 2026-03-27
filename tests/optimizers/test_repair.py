import numpy as np
import pytest

from core.contracts.case_contracts import assert_case_geometry_contracts
from core.generator.paired_pipeline import generate_operating_case_pair
from optimizers.codec import extract_decision_vector
from optimizers.models import OptimizationSpec
from optimizers.repair import MIN_RADIATOR_SPAN, repair_case_from_vector


def _case():
    return generate_operating_case_pair("scenarios/templates/panel_four_component_hot_cold_benchmark.yaml", seed=11)["hot"]


def _spec() -> OptimizationSpec:
    return OptimizationSpec.from_dict(
        {
            "schema_version": "1.0",
            "spec_meta": {"spec_id": "panel-four-component-hot-cold-repair-test", "description": "Repair regression test."},
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
                "backbone": "ctaea",
                "mode": "raw",
                "population_size": 4,
                "num_generations": 1,
                "seed": 7,
            },
            "evaluation_protocol": {"evaluation_spec_path": "unused.yaml"},
        }
    )


def test_repair_case_from_vector_fixes_inverted_radiator_interval_before_case_validation() -> None:
    case = _case()
    spec = _spec()
    vector = extract_decision_vector(case, spec)
    vector[-2] = 0.44815074277746997
    vector[-1] = 0.23295650597103754

    repaired = repair_case_from_vector(case, spec, np.asarray(vector, dtype=np.float64))
    feature = repaired.boundary_features[0]

    assert 0.05 <= feature["start"] < feature["end"] <= 0.95
    assert feature["end"] - feature["start"] >= MIN_RADIATOR_SPAN - 1.0e-9


def test_repair_case_from_vector_resolves_overlap_when_primary_axis_is_clamped() -> None:
    case = _case()
    spec = _spec()
    vector = np.array(
        [
            0.14711701186793308,
            0.39803996294654,
            0.4743165792472197,
            0.6152705975241403,
            0.598211953413168,
            0.3976235291637375,
            0.37296773300577774,
            0.3856361915204981,
        ],
        dtype=np.float64,
    )

    repaired = repair_case_from_vector(case, spec, vector)
    assert_case_geometry_contracts(repaired)
