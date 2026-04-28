from __future__ import annotations

from core.generator.pipeline import generate_case
from core.solver.nonlinear_solver import solve_case


def test_generated_s3_scale20_case_solves_for_seed_11() -> None:
    case = generate_case("scenarios/templates/s3_scale20.yaml", seed=11)

    solution = solve_case(case)
    temperature_span = solution.summary_metrics["temperature_max"] - solution.summary_metrics["temperature_min"]

    assert solution.solver_diagnostics["converged"] is True
    assert solution.summary_metrics["temperature_max"] >= solution.summary_metrics["temperature_min"]
    assert temperature_span >= 10.0
    assert solution.solution_meta["case_id"] == "s3_scale20-seed-0011"


def test_generated_s4_dense25_case_solves_for_seed_11() -> None:
    case = generate_case("scenarios/templates/s4_dense25.yaml", seed=11)

    solution = solve_case(case)
    temperature_span = solution.summary_metrics["temperature_max"] - solution.summary_metrics["temperature_min"]

    assert solution.solver_diagnostics["converged"] is True
    assert solution.summary_metrics["temperature_max"] >= solution.summary_metrics["temperature_min"]
    assert temperature_span >= 10.0
    assert solution.solution_meta["case_id"] == "s4_dense25-seed-0011"
