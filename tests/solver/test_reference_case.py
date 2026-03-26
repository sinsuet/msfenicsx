from core.schema.io import load_case
from core.solver.nonlinear_solver import solve_case


def test_reference_case_solves_and_reports_temperature_bounds() -> None:
    case = load_case("scenarios/manual/reference_case.yaml")

    solution = solve_case(case)

    assert solution.solver_diagnostics["converged"] is True
    assert solution.summary_metrics["temperature_max"] >= solution.summary_metrics["temperature_min"]
    assert solution.component_summaries
