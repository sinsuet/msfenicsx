from core.generator.pipeline import generate_case
from core.solver.nonlinear_solver import solve_case


def test_generated_s1_typical_case_solves_and_reports_temperature_bounds() -> None:
    case = generate_case("scenarios/templates/s1_typical.yaml", seed=11)

    solution = solve_case(case)

    assert solution.solver_diagnostics["converged"] is True
    assert solution.summary_metrics["temperature_max"] >= solution.summary_metrics["temperature_min"]
    assert solution.solution_meta["case_id"] == case.case_meta["case_id"]
    assert case.case_meta["case_id"] == "s1_typical-seed-0011"
