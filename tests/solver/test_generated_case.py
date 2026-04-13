from core.generator.pipeline import generate_case
from core.solver.case_to_geometry import interpret_case
from core.solver.nonlinear_solver import solve_case


def test_generated_s1_typical_case_solves_and_reports_temperature_bounds() -> None:
    case = generate_case("scenarios/templates/s1_typical.yaml", seed=11)

    solution = solve_case(case)
    temperature_span = solution.summary_metrics["temperature_max"] - solution.summary_metrics["temperature_min"]

    assert solution.solver_diagnostics["converged"] is True
    assert solution.summary_metrics["temperature_max"] >= solution.summary_metrics["temperature_min"]
    assert temperature_span >= 10.0
    assert solution.solution_meta["case_id"] == case.case_meta["case_id"]
    assert case.case_meta["case_id"] == "s1_typical-seed-0011"


def test_generated_s1_typical_case_uses_legacy_aligned_conductivities_and_localized_sources() -> None:
    case = generate_case("scenarios/templates/s1_typical.yaml", seed=11)

    interpreted = interpret_case(case)

    assert interpreted["default_conductivity"] == 3.0
    assert {component["conductivity"] for component in interpreted["components"]} == {12.0}
    assert min(component["source_area"] / component["area"] for component in interpreted["components"]) <= 0.18


def test_generated_s1_typical_case_uses_explicit_localized_sources_and_ambient_background_cooling() -> None:
    case = generate_case("scenarios/templates/s1_typical.yaml", seed=11)
    interpreted = interpret_case(case)

    assert interpreted["ambient_temperature"] > 0.0
    assert interpreted["background_boundary_cooling"]["transfer_coefficient"] > 0.0
    assert len(interpreted["components"]) == 15
    assert all(component["total_power"] > 0.0 for component in interpreted["components"])
    assert all(component["source_area"] < component["area"] for component in interpreted["components"])
