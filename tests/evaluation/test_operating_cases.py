from core.generator.paired_pipeline import generate_operating_case_pair


def test_generated_hot_and_cold_cases_share_geometry_but_differ_in_environment() -> None:
    cases = generate_operating_case_pair("scenarios/templates/panel_four_component_hot_cold_benchmark.yaml", seed=11)
    hot = cases["hot"]
    cold = cases["cold"]

    assert hot.components == cold.components
    assert hot.loads != cold.loads or hot.boundary_features != cold.boundary_features or hot.physics != cold.physics
