from pathlib import Path

import numpy as np
import pytest

import optimizers.problem as problem_module
from evaluation.io import load_spec
from optimizers.cheap_constraints import project_sink_interval
from optimizers.io import generate_benchmark_case, load_optimization_spec
from optimizers.models import OptimizationSpec
from optimizers.problem import PENALTY_VALUE, ThermalOptimizationProblem


SPEC_PATH = Path("scenarios/optimization/s1_typical_raw.yaml")
EVALUATION_SPEC_PATH = Path("scenarios/evaluation/s1_typical_eval.yaml")


def _base_case():
    optimization_spec = load_optimization_spec(SPEC_PATH)
    return generate_benchmark_case(SPEC_PATH, optimization_spec)


def _impossible_overlap_spec() -> OptimizationSpec:
    payload = load_optimization_spec(SPEC_PATH).to_dict()
    payload["spec_meta"] = {
        "spec_id": "s1_typical_impossible_overlap",
        "description": "Cheap-constraint regression fixture with impossible narrow overlap bounds.",
    }
    payload["design_variables"] = [
        {
            "variable_id": "c01_x",
            "path": "components[0].pose.x",
            "lower_bound": 0.15,
            "upper_bound": 0.17,
        },
        {
            "variable_id": "c01_y",
            "path": "components[0].pose.y",
            "lower_bound": 0.15,
            "upper_bound": 0.17,
        },
        {
            "variable_id": "c02_x",
            "path": "components[1].pose.x",
            "lower_bound": 0.15,
            "upper_bound": 0.17,
        },
        {
            "variable_id": "c02_y",
            "path": "components[1].pose.y",
            "lower_bound": 0.15,
            "upper_bound": 0.17,
        },
        {
            "variable_id": "sink_start",
            "path": "boundary_features[0].start",
            "lower_bound": 0.2,
            "upper_bound": 0.25,
        },
        {
            "variable_id": "sink_end",
            "path": "boundary_features[0].end",
            "lower_bound": 0.6,
            "upper_bound": 0.65,
        },
    ]
    return OptimizationSpec.from_dict(payload)


def _clearance_violation_spec() -> OptimizationSpec:
    payload = load_optimization_spec(SPEC_PATH).to_dict()
    payload["spec_meta"] = {
        "spec_id": "s1_typical_clearance_violation",
        "description": "Cheap-constraint regression fixture with near-contact but non-overlapping bounds.",
    }
    payload["design_variables"] = [
        {
            "variable_id": "c01_x",
            "path": "components[0].pose.x",
            "lower_bound": 0.20,
            "upper_bound": 0.2005,
        },
        {
            "variable_id": "c01_y",
            "path": "components[0].pose.y",
            "lower_bound": 0.20,
            "upper_bound": 0.2005,
        },
        {
            "variable_id": "c02_x",
            "path": "components[1].pose.x",
            "lower_bound": 0.345,
            "upper_bound": 0.3455,
        },
        {
            "variable_id": "c02_y",
            "path": "components[1].pose.y",
            "lower_bound": 0.20,
            "upper_bound": 0.2005,
        },
        {
            "variable_id": "sink_start",
            "path": "boundary_features[0].start",
            "lower_bound": 0.2,
            "upper_bound": 0.2005,
        },
        {
            "variable_id": "sink_end",
            "path": "boundary_features[0].end",
            "lower_bound": 0.65,
            "upper_bound": 0.6505,
        },
    ]
    return OptimizationSpec.from_dict(payload)


def test_sink_budget_projection_caps_span_without_breaking_order() -> None:
    projected = project_sink_interval(start=0.2, end=0.9, span_max=0.4)

    assert projected.start < projected.end
    assert projected.end - projected.start == pytest.approx(0.4)


def test_sink_budget_projection_respects_individual_start_and_end_bounds() -> None:
    projected = project_sink_interval(
        start=0.7,
        end=0.95,
        span_max=0.2,
        start_bounds=(0.05, 0.7),
        end_bounds=(0.2, 0.95),
    )

    assert 0.05 <= projected.start <= 0.7
    assert 0.2 <= projected.end <= 0.95
    assert projected.end - projected.start == pytest.approx(0.2)


def test_problem_skips_pde_when_cheap_constraints_remain_violated(monkeypatch: pytest.MonkeyPatch) -> None:
    base_case = _base_case()
    optimization_spec = _impossible_overlap_spec()
    evaluation_spec = load_spec(EVALUATION_SPEC_PATH)
    problem = ThermalOptimizationProblem(base_case, optimization_spec, evaluation_spec)
    vector = np.asarray([0.16, 0.16, 0.16, 0.16, 0.2, 0.65], dtype=np.float64)

    def _fail_if_called(_case):
        raise AssertionError("solve_case should be skipped when cheap constraints remain violated")

    monkeypatch.setattr(problem_module, "solve_case", _fail_if_called)

    record, objective_vector, constraint_vector = problem.evaluate_vector(vector, source="optimizer")

    assert record["failure_reason"] == "cheap_constraint_violation"
    assert record["solver_skipped"] is True
    assert record["feasible"] is False
    assert np.all(objective_vector == PENALTY_VALUE)
    assert np.all(constraint_vector >= 0.0)


def test_problem_skips_pde_when_components_violate_clearance(monkeypatch: pytest.MonkeyPatch) -> None:
    base_case = _base_case()
    optimization_spec = _clearance_violation_spec()
    evaluation_spec = load_spec(EVALUATION_SPEC_PATH)
    problem = ThermalOptimizationProblem(base_case, optimization_spec, evaluation_spec)
    vector = np.asarray([0.20, 0.20, 0.345, 0.20, 0.2, 0.65], dtype=np.float64)

    def _fail_if_called(_case):
        raise AssertionError("solve_case should be skipped when cheap constraints remain violated")

    monkeypatch.setattr(problem_module, "solve_case", _fail_if_called)

    record, objective_vector, constraint_vector = problem.evaluate_vector(vector, source="optimizer")

    assert record["failure_reason"] == "cheap_constraint_violation"
    assert record["solver_skipped"] is True
    assert record["feasible"] is False
    assert any("clearance_violation" in issue for issue in record["cheap_constraint_issues"])
    assert np.all(objective_vector == PENALTY_VALUE)
    assert np.all(constraint_vector >= 0.0)
