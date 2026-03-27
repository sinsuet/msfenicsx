from core.schema.io import load_case


def test_reference_hot_and_cold_cases_share_geometry_but_differ_in_environment() -> None:
    hot = load_case("scenarios/manual/reference_case_hot.yaml")
    cold = load_case("scenarios/manual/reference_case_cold.yaml")

    assert hot.components == cold.components
    assert hot.loads != cold.loads or hot.boundary_features != cold.boundary_features or hot.physics != cold.physics
