from core.contracts.case_contracts import assert_case_geometry_contracts
from core.generator.paired_pipeline import generate_operating_case_pair
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


def test_generate_operating_case_pair_is_deterministic_for_fixed_seed() -> None:
    cases_a = generate_operating_case_pair("scenarios/templates/panel_four_component_hot_cold_benchmark.yaml", seed=11)
    cases_b = generate_operating_case_pair("scenarios/templates/panel_four_component_hot_cold_benchmark.yaml", seed=11)

    assert {name: case.to_dict() for name, case in cases_a.items()} == {
        name: case.to_dict() for name, case in cases_b.items()
    }


def test_generate_operating_case_pair_returns_hot_and_cold_cases() -> None:
    cases = generate_operating_case_pair("scenarios/templates/panel_four_component_hot_cold_benchmark.yaml", seed=11)

    assert set(cases) == {"hot", "cold"}
    assert cases["hot"].to_dict()["components"] == cases["cold"].to_dict()["components"]
    assert cases["hot"].to_dict()["loads"] != cases["cold"].to_dict()["loads"]
    assert cases["hot"].to_dict()["physics"]["ambient_temperature"] != cases["cold"].to_dict()["physics"]["ambient_temperature"]
    for case in cases.values():
        assert_case_geometry_contracts(case)
