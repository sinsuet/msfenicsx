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
            "spec_id": f"s1-typical-{backbone}-{mode}",
            "description": "Matrix contract validation fixture.",
        },
        "benchmark_source": {
            "template_path": "scenarios/templates/s1_typical.yaml",
            "seed": 11,
        },
        "design_variables": [
            {
                "variable_id": "c01_x",
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
            "evaluation_spec_path": "scenarios/evaluation/s1_typical_eval.yaml",
            "legality_policy_id": "minimal_canonicalization",
        },
    }


def test_backbone_registry_lists_the_first_matrix_batch() -> None:
    assert list_supported_backbones() == [
        "moead",
        "nsga2",
        "spea2",
    ]
    assert SUPPORTED_BACKBONES_BY_FAMILY == {
        "genetic": ("nsga2", "spea2"),
        "decomposition": ("moead",),
    }


def test_validation_rejects_mismatched_family_backbone_pair() -> None:
    with pytest.raises(OptimizationValidationError):
        OptimizationSpec.from_dict(_spec_payload(family="genetic", backbone="moead"))


def test_validation_rejects_unapproved_backbone_family_pair() -> None:
    with pytest.raises(OptimizationValidationError):
        OptimizationSpec.from_dict(_spec_payload(family="decomposition", backbone="nsga2"))


def test_validation_rejects_unknown_family() -> None:
    with pytest.raises(OptimizationValidationError):
        OptimizationSpec.from_dict(_spec_payload(family="legacy", backbone="nsga2"))


@pytest.mark.parametrize(
    ("family", "backbone"),
    [
        ("genetic", "spea2"),
        ("decomposition", "moead"),
    ],
)
def test_validation_rejects_comparison_backbones_in_union_mode(family: str, backbone: str) -> None:
    with pytest.raises(OptimizationValidationError):
        OptimizationSpec.from_dict(_spec_payload(family=family, backbone=backbone, mode="union"))
