import pytest

from core.contracts.case_contracts import assert_case_geometry_contracts
from core.generator.pipeline import generate_case


def test_generate_case_is_deterministic_for_fixed_seed() -> None:
    case_a = generate_case("scenarios/templates/s1_typical.yaml", seed=11)
    case_b = generate_case("scenarios/templates/s1_typical.yaml", seed=11)

    assert case_a.to_dict() == case_b.to_dict()


def test_generate_case_returns_single_case_for_mainline_template() -> None:
    case = generate_case("scenarios/templates/s1_typical.yaml", seed=11)

    assert case.case_meta["scenario_id"] == "s1_typical"
    assert case.case_meta["case_id"] == "s1_typical-seed-0011"
    assert len(case.components) == 15
    assert len(case.loads) == 15
    assert case.physics["kind"] == "steady_heat_radiation"
    assert_case_geometry_contracts(case)


def test_generate_case_rejects_templates_with_operating_case_profiles() -> None:
    with pytest.raises(ValueError, match="generate-operating-case-pair"):
        generate_case("scenarios/templates/panel_four_component_hot_cold_benchmark.yaml", seed=11)
