from pathlib import Path

import numpy as np

from evaluation.io import load_spec
from optimizers.codec import extract_decision_vector
from optimizers.io import generate_benchmark_case, load_optimization_spec
from optimizers.problem import ThermalOptimizationProblem


SPEC_PATH = Path("scenarios/optimization/s1_typical_raw.yaml")


def test_generate_benchmark_case_returns_single_case() -> None:
    optimization_spec = load_optimization_spec(SPEC_PATH)

    case = generate_benchmark_case(SPEC_PATH, optimization_spec)

    assert case.case_meta["scenario_id"] == "s1_typical"


def test_problem_evaluates_single_case_report_and_history() -> None:
    optimization_spec = load_optimization_spec(SPEC_PATH)
    evaluation_spec = load_spec("scenarios/evaluation/s1_typical_eval.yaml")
    base_case = generate_benchmark_case(SPEC_PATH, optimization_spec)
    problem = ThermalOptimizationProblem(base_case, optimization_spec, evaluation_spec)
    vector = extract_decision_vector(base_case, optimization_spec)

    record, objective_vector, constraint_vector = problem.evaluate_vector(vector, source="optimizer")

    assert "evaluation_report" in record
    assert "case_reports" not in record
    assert record["evaluation_report"]["evaluation_meta"]["case_id"] == base_case.case_meta["case_id"]
    assert objective_vector.shape == (len(evaluation_spec.objectives),)
    assert constraint_vector.shape == (len(evaluation_spec.constraints),)
    assert all(np.isfinite(objective_vector))
    assert all(np.isfinite(constraint_vector))
