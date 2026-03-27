"""Driver for raw multi-backbone optimizer runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from pymoo.optimize import minimize

from core.schema.io import load_case
from evaluation.io import load_multicase_spec
from optimizers.io import generate_benchmark_cases, load_optimization_spec, resolve_evaluation_spec_path
from optimizers.models import OptimizationResult
from optimizers.problem import CandidateArtifacts, ThermalOptimizationProblem, objective_to_minimization
from optimizers.raw_backbones.registry import build_raw_algorithm


@dataclass(slots=True)
class OptimizationRun:
    result: OptimizationResult
    representative_artifacts: dict[str, CandidateArtifacts]


def run_raw_optimization(base_cases: dict[str, Any], optimization_spec: Any, evaluation_spec: Any) -> OptimizationRun:
    spec_payload = optimization_spec.to_dict() if hasattr(optimization_spec, "to_dict") else dict(optimization_spec)
    evaluation_payload = evaluation_spec.to_dict() if hasattr(evaluation_spec, "to_dict") else dict(evaluation_spec)
    algorithm_config = spec_payload["algorithm"]
    if algorithm_config["mode"] != "raw":
        raise ValueError(f"run_raw_optimization only supports algorithm.mode='raw', got {algorithm_config['mode']!r}.")

    loaded_cases = _load_base_cases(base_cases)
    problem = ThermalOptimizationProblem(loaded_cases, spec_payload, evaluation_payload)
    baseline_record = problem.evaluate_baseline()

    algorithm = build_raw_algorithm(problem, algorithm_config)
    minimize(
        problem,
        algorithm,
        termination=("n_gen", int(algorithm_config["num_generations"])),
        seed=int(algorithm_config["seed"]),
        verbose=False,
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
    return OptimizationRun(
        result=OptimizationResult.from_dict(result_payload),
        representative_artifacts=representative_artifacts,
    )


def run_raw_optimization_from_spec(spec_path: str | Path) -> OptimizationRun:
    optimization_spec = load_optimization_spec(spec_path)
    base_cases = generate_benchmark_cases(spec_path, optimization_spec)
    evaluation_spec = load_multicase_spec(resolve_evaluation_spec_path(spec_path, optimization_spec))
    return run_raw_optimization(base_cases, optimization_spec, evaluation_spec)


def _load_base_cases(base_cases: dict[str, Any]) -> dict[str, Any]:
    loaded_cases: dict[str, Any] = {}
    for operating_case_id, case in base_cases.items():
        if isinstance(case, (str, Path)):
            loaded_cases[operating_case_id] = load_case(case)
        else:
            loaded_cases[operating_case_id] = case
    return loaded_cases


def _build_result_payload(
    loaded_cases: dict[str, Any],
    spec_payload: dict[str, Any],
    evaluation_payload: dict[str, Any],
    baseline_record: dict[str, Any],
    pareto_front: list[dict[str, Any]],
    representative_candidates: dict[str, dict[str, Any]],
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    feasible_indices = [entry["evaluation_index"] for entry in history if entry["feasible"]]
    feasible_rate = sum(1 for entry in history if entry["feasible"]) / float(len(history))
    return {
        "schema_version": spec_payload["schema_version"],
        "run_meta": {
            "run_id": f"{spec_payload['spec_meta']['spec_id']}-run",
            "base_case_ids": {
                operating_case_id: case.to_dict()["case_meta"]["case_id"] if hasattr(case, "to_dict") else case["case_meta"]["case_id"]
                for operating_case_id, case in loaded_cases.items()
            },
            "optimization_spec_id": spec_payload["spec_meta"]["spec_id"],
            "evaluation_spec_id": evaluation_payload["spec_meta"]["spec_id"],
        },
        "baseline_candidates": [baseline_record],
        "pareto_front": pareto_front,
        "representative_candidates": representative_candidates,
        "aggregate_metrics": {
            "num_evaluations": len(history),
            "feasible_rate": feasible_rate,
            "first_feasible_eval": feasible_indices[0] if feasible_indices else None,
            "pareto_size": len(pareto_front),
        },
        "history": history,
        "provenance": {
            "benchmark_source": spec_payload.get("benchmark_source"),
            "source_case_ids": {
                operating_case_id: case.to_dict()["case_meta"]["case_id"] if hasattr(case, "to_dict") else case["case_meta"]["case_id"]
                for operating_case_id, case in loaded_cases.items()
            },
            "source_optimization_spec_id": spec_payload["spec_meta"]["spec_id"],
            "source_evaluation_spec_id": evaluation_payload["spec_meta"]["spec_id"],
        },
    }


def _extract_pareto_front(history: list[dict[str, Any]], objectives: list[dict[str, Any]]) -> list[dict[str, Any]]:
    feasible_records = [record for record in history if record["feasible"]]
    pareto_front: list[dict[str, Any]] = []
    for candidate in feasible_records:
        dominated = False
        for incumbent in feasible_records:
            if candidate is incumbent:
                continue
            if _dominates(incumbent, candidate, objectives):
                dominated = True
                break
        if not dominated:
            pareto_front.append(candidate)
    pareto_front.sort(key=lambda record: record["evaluation_index"])
    return pareto_front


def _dominates(candidate: dict[str, Any], incumbent: dict[str, Any], objectives: list[dict[str, Any]]) -> bool:
    candidate_tuple = tuple(
        objective_to_minimization(candidate["objective_values"][objective["objective_id"]], objective["sense"])
        for objective in objectives
    )
    incumbent_tuple = tuple(
        objective_to_minimization(incumbent["objective_values"][objective["objective_id"]], objective["sense"])
        for objective in objectives
    )
    return all(left <= right for left, right in zip(candidate_tuple, incumbent_tuple, strict=True)) and any(
        left < right for left, right in zip(candidate_tuple, incumbent_tuple, strict=True)
    )


def _build_representative_candidates(
    pareto_front: list[dict[str, Any]],
    objectives: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    if not pareto_front:
        return {}
    representatives = {}
    for objective in objectives:
        representatives[_representative_key(objective)] = min(
            pareto_front,
            key=lambda record: objective_to_minimization(
                record["objective_values"][objective["objective_id"]],
                objective["sense"],
            ),
        )
    if len(pareto_front) >= 2:
        representatives["knee_candidate"] = _select_knee_candidate(pareto_front, objectives)
    return representatives


def _select_knee_candidate(pareto_front: list[dict[str, Any]], objectives: list[dict[str, Any]]) -> dict[str, Any]:
    objective_matrix = np.asarray(
        [
            [
                objective_to_minimization(record["objective_values"][objective["objective_id"]], objective["sense"])
                for objective in objectives
            ]
            for record in pareto_front
        ],
        dtype=np.float64,
    )
    minima = objective_matrix.min(axis=0)
    maxima = objective_matrix.max(axis=0)
    span = np.where((maxima - minima) > 0.0, maxima - minima, 1.0)
    normalized = (objective_matrix - minima) / span
    scores = normalized.sum(axis=1)
    return pareto_front[int(np.argmin(scores))]


def _representative_key(objective: dict[str, Any]) -> str:
    objective_id = str(objective["objective_id"])
    if objective_id.startswith("minimize_"):
        return f"min_{objective_id.removeprefix('minimize_')}"
    if objective_id.startswith("maximize_"):
        return f"max_{objective_id.removeprefix('maximize_')}"
    return objective_id
