from core.generator.paired_pipeline import generate_operating_case_pair
from core.solver.nonlinear_solver import solve_case


def test_generated_hot_benchmark_case_solves_and_reports_temperature_bounds() -> None:
    case = generate_operating_case_pair("scenarios/templates/panel_four_component_hot_cold_benchmark.yaml", seed=11)["hot"]

    solution = solve_case(case)

    assert solution.solver_diagnostics["converged"] is True
    assert solution.summary_metrics["temperature_max"] >= solution.summary_metrics["temperature_min"]
    assert solution.solution_meta["case_id"] == case.case_meta["case_id"]
    assert case.case_meta["case_id"].endswith("-hot")
