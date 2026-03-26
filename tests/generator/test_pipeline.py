from core.contracts.case_contracts import assert_case_geometry_contracts
from core.generator.pipeline import generate_case


def test_generate_case_is_deterministic_for_fixed_seed() -> None:
    case_a = generate_case("scenarios/templates/panel_radiation_baseline.yaml", seed=7)
    case_b = generate_case("scenarios/templates/panel_radiation_baseline.yaml", seed=7)

    assert case_a.to_dict() == case_b.to_dict()


def test_generate_case_returns_valid_canonical_case() -> None:
    case = generate_case("scenarios/templates/panel_radiation_baseline.yaml", seed=3)

    assert case.case_meta["scenario_id"] == "panel-radiation-baseline"
    assert case.boundary_features
    assert case.loads
    assert_case_geometry_contracts(case)
