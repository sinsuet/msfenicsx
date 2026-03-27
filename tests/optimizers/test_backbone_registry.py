import pytest

from optimizers.models import OptimizationSpec
from optimizers.validation import (
    OptimizationValidationError,
    SUPPORTED_BACKBONES_BY_FAMILY,
    list_supported_backbones,
)


def _spec_payload(*, family: str = "genetic", backbone: str = "nsga2", mode: str = "raw") -> dict:
    return {
        "schema_version": "1.0",
        "spec_meta": {
            "spec_id": f"panel-four-component-hot-cold-{backbone}-{mode}",
            "description": "Matrix contract validation fixture.",
        },
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
            }
        ],
        "algorithm": {
            "family": family,
            "backbone": backbone,
            "mode": mode,
            "population_size": 4,
            "num_generations": 1,
            "seed": 7,
        },
        "evaluation_protocol": {
            "evaluation_spec_path": "scenarios/evaluation/panel_four_component_hot_cold_baseline.yaml",
        },
    }


def test_backbone_registry_lists_the_first_matrix_batch() -> None:
    assert list_supported_backbones() == [
        "cmopso",
        "ctaea",
        "moead",
        "nsga2",
        "nsga3",
        "rvea",
    ]
    assert SUPPORTED_BACKBONES_BY_FAMILY == {
        "genetic": ("nsga2", "nsga3", "ctaea", "rvea"),
        "decomposition": ("moead",),
        "swarm": ("cmopso",),
    }


def test_validation_rejects_mismatched_family_backbone_pair() -> None:
    with pytest.raises(OptimizationValidationError):
        OptimizationSpec.from_dict(_spec_payload(family="genetic", backbone="moead"))
