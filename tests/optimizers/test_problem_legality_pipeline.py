from __future__ import annotations

import numpy as np
import pytest

from evaluation.io import load_spec
from optimizers.cheap_constraints import evaluate_cheap_constraints, resolve_radiator_span_max
from optimizers.codec import extract_decision_vector
from optimizers.clean_initialization import CleanBaselineSampling
from optimizers.io import generate_benchmark_case, load_optimization_spec, resolve_evaluation_spec_path
from optimizers.repair import project_case_payload_from_vector
import optimizers.problem as problem_module
from optimizers.problem import ThermalOptimizationProblem


def test_problem_records_proposal_and_evaluated_vectors_separately() -> None:
    spec_path = "scenarios/optimization/s1_typical_raw.yaml"
    optimization_spec = load_optimization_spec(spec_path)
    evaluation_spec = load_spec(resolve_evaluation_spec_path(spec_path, optimization_spec))
    base_case = generate_benchmark_case(spec_path, optimization_spec)
    problem = ThermalOptimizationProblem(base_case, optimization_spec, evaluation_spec, evaluation_workers=1)

    vector = np.asarray(problem.xl, dtype=np.float64).copy()
    vector[-2] = 0.90
    vector[-1] = 0.05

    record, _, _ = problem.evaluate_vector(vector, source="optimizer")
    problem.close()

    assert record["legality_policy_id"] == "minimal_canonicalization"
    assert "proposal_decision_vector" in record
    assert "evaluated_decision_vector" in record
    assert record["proposal_decision_vector"]["sink_start"] == 0.90
    assert record["evaluated_decision_vector"]["sink_start"] <= record["evaluated_decision_vector"]["sink_end"]
    assert "vector_transform_codes" in record


def test_problem_metadata_does_not_overwrite_canonical_record_fields() -> None:
    spec_path = "scenarios/optimization/s1_typical_raw.yaml"
    optimization_spec = load_optimization_spec(spec_path)
    evaluation_spec = load_spec(resolve_evaluation_spec_path(spec_path, optimization_spec))
    base_case = generate_benchmark_case(spec_path, optimization_spec)
    problem = ThermalOptimizationProblem(base_case, optimization_spec, evaluation_spec, evaluation_workers=1)

    vector = extract_decision_vector(base_case, optimization_spec)

    try:
        record, _, _ = problem.evaluate_vector(
            vector,
            source="optimizer",
            metadata={
                "legality_policy_id": "metadata_must_not_win",
                "solver_skipped": True,
                "cheap_constraint_issues": ["metadata_must_not_win"],
                "objective_values": {"metadata_must_not_win": 1.0},
                "custom_note": "kept",
            },
        )
    finally:
        problem.close()

    assert record["legality_policy_id"] == "minimal_canonicalization"
    assert record["solver_skipped"] is False
    assert record["cheap_constraint_issues"] == []
    assert "metadata_must_not_win" not in record["objective_values"]
    assert record["custom_note"] == "kept"


def test_problem_preserves_evaluated_vector_when_cheap_constraint_evaluation_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec_path = "scenarios/optimization/s1_typical_raw.yaml"
    optimization_spec = load_optimization_spec(spec_path)
    evaluation_spec = load_spec(resolve_evaluation_spec_path(spec_path, optimization_spec))
    base_case = generate_benchmark_case(spec_path, optimization_spec)
    problem = ThermalOptimizationProblem(base_case, optimization_spec, evaluation_spec, evaluation_workers=1)

    vector = np.asarray(problem.xl, dtype=np.float64).copy()
    vector[-2] = 0.90
    vector[-1] = 0.05

    def _raise_after_legality(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("cheap evaluation failed")

    monkeypatch.setattr(problem_module, "evaluate_cheap_constraints", _raise_after_legality)

    try:
        record, _, _ = problem.evaluate_vector(vector, source="optimizer")
    finally:
        problem.close()

    assert record["failure_reason"] == "RuntimeError: cheap evaluation failed"
    assert record["proposal_decision_vector"]["sink_start"] == 0.90
    assert record["evaluated_decision_vector"]["sink_start"] <= record["evaluated_decision_vector"]["sink_end"]
    assert "sink_reorder" in record["vector_transform_codes"]


def test_cheap_geometry_failure_exposes_optimizer_visible_constraint_signal() -> None:
    spec_path = "scenarios/optimization/s2_staged_raw.yaml"
    optimization_spec = load_optimization_spec(spec_path)
    evaluation_spec = load_spec(resolve_evaluation_spec_path(spec_path, optimization_spec))
    base_case = generate_benchmark_case(spec_path, optimization_spec)
    problem = ThermalOptimizationProblem(base_case, optimization_spec, evaluation_spec, evaluation_workers=1)

    vector = np.asarray(problem.xl, dtype=np.float64).copy()
    vector[-2] = 0.90
    vector[-1] = 0.05

    try:
        record, _, constraints = problem.evaluate_vector(vector, source="optimizer")
    finally:
        problem.close()

    assert record["failure_reason"] == "cheap_constraint_violation"
    assert record["solver_skipped"] is True
    assert record["cheap_constraint_issues"]
    assert record["constraint_values"]["cheap_geometry_issue_count"] > 0.0
    assert constraints.size == problem.n_ieq_constr


def test_clean_baseline_sampling_balances_sink_and_component_exploration() -> None:
    spec_path = "scenarios/optimization/s2_staged_raw.yaml"
    optimization_spec = load_optimization_spec(spec_path)
    evaluation_spec = load_spec(resolve_evaluation_spec_path(spec_path, optimization_spec))
    base_case = generate_benchmark_case(spec_path, optimization_spec)
    problem = ThermalOptimizationProblem(base_case, optimization_spec, evaluation_spec, evaluation_workers=1)

    try:
        samples = CleanBaselineSampling()._do(
            problem,
            20,
            random_state=np.random.default_rng(123),
        )
    finally:
        problem.close()

    base_vector = extract_decision_vector(base_case, optimization_spec)
    component_delta = np.linalg.norm(samples[:, :-2] - base_vector[:-2], axis=1)
    sink_delta = np.linalg.norm(samples[:, -2:] - base_vector[-2:], axis=1)

    assert samples.shape == (20, problem.n_var)
    assert np.count_nonzero(component_delta > 0.03) >= 4
    assert np.count_nonzero(sink_delta > 0.03) >= 4
    assert np.count_nonzero((component_delta > 0.03) & (sink_delta > 0.20)) >= 3


def test_clean_baseline_sampling_returns_only_cheap_feasible_candidates() -> None:
    spec_path = "scenarios/optimization/s2_staged_raw.yaml"
    optimization_spec = load_optimization_spec(spec_path)
    evaluation_spec = load_spec(resolve_evaluation_spec_path(spec_path, optimization_spec))
    base_case = generate_benchmark_case(spec_path, optimization_spec)
    problem = ThermalOptimizationProblem(base_case, optimization_spec, evaluation_spec, evaluation_workers=1)

    try:
        samples = CleanBaselineSampling()._do(
            problem,
            20,
            random_state=np.random.default_rng(123),
        )
    finally:
        problem.close()

    radiator_span_max = resolve_radiator_span_max(evaluation_spec)
    feasibility = []
    for vector in samples:
        payload = project_case_payload_from_vector(
            base_case,
            optimization_spec,
            vector,
            radiator_span_max=radiator_span_max,
        )
        feasibility.append(evaluate_cheap_constraints(payload, evaluation_spec).feasible)

    assert all(feasibility)


def test_clean_baseline_sampling_preserves_requested_shape_when_cheap_filter_rejects_all(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec_path = "scenarios/optimization/s2_staged_raw.yaml"
    optimization_spec = load_optimization_spec(spec_path)
    evaluation_spec = load_spec(resolve_evaluation_spec_path(spec_path, optimization_spec))
    base_case = generate_benchmark_case(spec_path, optimization_spec)
    problem = ThermalOptimizationProblem(base_case, optimization_spec, evaluation_spec, evaluation_workers=1)

    def _reject_all(*args, **kwargs):
        del args, kwargs
        return False

    monkeypatch.setattr("optimizers.clean_initialization._is_cheap_feasible", _reject_all)

    try:
        samples = CleanBaselineSampling()._do(
            problem,
            20,
            random_state=np.random.default_rng(123),
        )
    finally:
        problem.close()

    assert samples.shape == (20, problem.n_var)


def test_clean_baseline_sampling_avoids_global_random_fallback_outliers() -> None:
    spec_path = "scenarios/optimization/s2_staged_raw.yaml"
    optimization_spec = load_optimization_spec(spec_path)
    evaluation_spec = load_spec(resolve_evaluation_spec_path(spec_path, optimization_spec))
    base_case = generate_benchmark_case(spec_path, optimization_spec)
    problem = ThermalOptimizationProblem(base_case, optimization_spec, evaluation_spec, evaluation_workers=1)

    try:
        samples = CleanBaselineSampling()._do(
            problem,
            20,
            random_state=np.random.default_rng(123),
        )
    finally:
        problem.close()

    base_vector = extract_decision_vector(base_case, optimization_spec)
    component_delta = np.linalg.norm(samples[:, :-2] - base_vector[:-2], axis=1)

    assert samples.shape == (20, problem.n_var)
    assert float(np.max(component_delta)) < 0.35
