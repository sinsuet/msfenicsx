from core.generator.paired_pipeline import generate_operating_case_pair
from core.solver.nonlinear_solver import solve_case


def test_deterministic_hot_and_cold_benchmark_reference_cases_solve() -> None:
    cases = generate_operating_case_pair("scenarios/templates/panel_four_component_hot_cold_benchmark.yaml", seed=11)
    solutions = {operating_case_id: solve_case(case) for operating_case_id, case in cases.items()}

    assert set(solutions) == {"hot", "cold"}
    for operating_case_id, solution in solutions.items():
        assert solution.solver_diagnostics["converged"] is True
        assert solution.summary_metrics["temperature_max"] >= solution.summary_metrics["temperature_min"]
        assert solution.component_summaries
        assert cases[operating_case_id].provenance["operating_case"] == operating_case_id
