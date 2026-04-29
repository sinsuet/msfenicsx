from pathlib import Path

import pytest

from optimizers.io import load_optimization_spec


@pytest.mark.parametrize(
    ("scenario_id", "dimension"),
    [
        ("s5_aggressive15", 32),
        ("s6_aggressive20", 42),
        ("s7_aggressive25", 52),
    ],
)
@pytest.mark.parametrize(
    ("backbone", "family"),
    [
        ("spea2", "genetic"),
        ("moead", "decomposition"),
    ],
)
def test_s5_s7_raw_backbone_specs_exist_and_match_contract(
    scenario_id: str,
    dimension: int,
    backbone: str,
    family: str,
) -> None:
    spec_path = Path(f"scenarios/optimization/{scenario_id}_{backbone}_raw.yaml")
    profile_path = Path(f"scenarios/optimization/profiles/{scenario_id}_{backbone}_raw.yaml")

    assert spec_path.exists()
    assert profile_path.exists()

    spec = load_optimization_spec(spec_path)
    payload = spec.to_dict()

    assert payload["spec_meta"]["spec_id"] == f"{scenario_id}_{backbone}_raw"
    assert payload["benchmark_source"]["template_path"] == f"scenarios/templates/{scenario_id}.yaml"
    assert payload["benchmark_source"]["seed"] == 11
    assert len(payload["design_variables"]) == dimension
    assert payload["algorithm"]["family"] == family
    assert payload["algorithm"]["backbone"] == backbone
    assert payload["algorithm"]["mode"] == "raw"
    assert payload["algorithm"]["seed"] == 7
    assert payload["algorithm"]["profile_path"] == f"scenarios/optimization/profiles/{scenario_id}_{backbone}_raw.yaml"
    assert payload["evaluation_protocol"]["evaluation_spec_path"] == f"scenarios/evaluation/{scenario_id}_eval.yaml"
    assert "operator_control" not in payload
