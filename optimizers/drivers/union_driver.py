"""Driver for controller-guided multi-backbone union optimizer runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pymoo.optimize import minimize

from evaluation.io import load_multicase_spec
from optimizers.adapters.decomposition_family import build_decomposition_union_algorithm
from optimizers.adapters.genetic_family import build_genetic_union_algorithm
from optimizers.adapters.swarm_family import build_swarm_union_algorithm
from optimizers.algorithm_config import resolve_algorithm_config
from optimizers.drivers.raw_driver import (
    _build_representative_candidates,
    _build_result_payload,
    _extract_pareto_front,
    _load_base_cases,
)
from optimizers.io import generate_benchmark_cases, load_optimization_spec, resolve_evaluation_spec_path
from optimizers.models import OptimizationResult
from optimizers.operator_pool.trace import ControllerTraceRow, OperatorTraceRow
from optimizers.problem import CandidateArtifacts, ThermalOptimizationProblem


@dataclass(slots=True)
class UnionOptimizationRun:
    result: OptimizationResult
    representative_artifacts: dict[str, CandidateArtifacts]
    controller_trace: list[ControllerTraceRow]
    operator_trace: list[OperatorTraceRow]
    llm_request_trace: list[dict[str, Any]] | None = None
    llm_response_trace: list[dict[str, Any]] | None = None
    llm_reflection_trace: list[dict[str, Any]] | None = None
    llm_metrics: dict[str, Any] | None = None


def run_union_optimization(
    base_cases: dict[str, Any],
    optimization_spec: Any,
    evaluation_spec: Any,
    *,
    spec_path: str | Path | None = None,
) -> UnionOptimizationRun:
    spec_payload = optimization_spec.to_dict() if hasattr(optimization_spec, "to_dict") else dict(optimization_spec)
    evaluation_payload = evaluation_spec.to_dict() if hasattr(evaluation_spec, "to_dict") else dict(evaluation_spec)
    algorithm_config = resolve_algorithm_config(spec_path, spec_payload)
    if algorithm_config["mode"] != "union":
        raise ValueError(f"run_union_optimization only supports algorithm.mode='union', got {algorithm_config['mode']!r}.")

    loaded_cases = _load_base_cases(base_cases)
    problem = ThermalOptimizationProblem(loaded_cases, spec_payload, evaluation_payload)
    baseline_record = problem.evaluate_baseline()

    family = str(algorithm_config["family"])
    if family == "genetic":
        adapter = build_genetic_union_algorithm(problem, spec_payload, algorithm_config)
    elif family == "decomposition":
        adapter = build_decomposition_union_algorithm(problem, spec_payload, algorithm_config)
    elif family == "swarm":
        adapter = build_swarm_union_algorithm(problem, spec_payload, algorithm_config)
    else:
        raise ValueError(f"Unsupported union-driver family {family!r}.")
    minimize(
        problem,
        adapter.algorithm,
        termination=("n_gen", int(algorithm_config["num_generations"])),
        seed=int(algorithm_config["seed"]),
        verbose=False,
        copy_algorithm=False,
    )

    pareto_front = _extract_pareto_front(problem.history, evaluation_payload["objectives"])
    representative_candidates = _build_representative_candidates(pareto_front, evaluation_payload["objectives"])
    result_payload = _build_result_payload(
        loaded_cases=loaded_cases,
        spec_payload=spec_payload,
        evaluation_payload=evaluation_payload,
        baseline_record=baseline_record,
        pareto_front=pareto_front,
        representative_candidates=representative_candidates,
        history=problem.history,
    )
    representative_artifacts = {
        name: problem.artifacts_by_index[candidate["evaluation_index"]]
        for name, candidate in representative_candidates.items()
        if candidate["evaluation_index"] in problem.artifacts_by_index
    }
    return UnionOptimizationRun(
        result=OptimizationResult.from_dict(result_payload),
        representative_artifacts=representative_artifacts,
        controller_trace=list(adapter.controller_trace),
        operator_trace=list(adapter.operator_trace),
        llm_request_trace=None if getattr(adapter, "llm_request_trace", None) is None else list(adapter.llm_request_trace),
        llm_response_trace=None if getattr(adapter, "llm_response_trace", None) is None else list(adapter.llm_response_trace),
        llm_reflection_trace=(
            None if getattr(adapter, "llm_reflection_trace", None) is None else list(adapter.llm_reflection_trace)
        ),
        llm_metrics=None if getattr(adapter, "llm_metrics", None) is None else dict(adapter.llm_metrics),
    )


def run_union_optimization_from_spec(spec_path: str | Path) -> UnionOptimizationRun:
    optimization_spec = load_optimization_spec(spec_path)
    base_cases = generate_benchmark_cases(spec_path, optimization_spec)
    evaluation_spec = load_multicase_spec(resolve_evaluation_spec_path(spec_path, optimization_spec))
    return run_union_optimization(base_cases, optimization_spec, evaluation_spec, spec_path=spec_path)
