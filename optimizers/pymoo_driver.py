"""pymoo-backed multicase Pareto optimizer baseline for thermal-case search."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import ElementwiseProblem
from pymoo.optimize import minimize

from core.contracts.case_contracts import assert_case_geometry_contracts
from core.schema.io import load_case
from core.solver.nonlinear_solver import solve_case
from evaluation.multicase_engine import evaluate_operating_cases
from optimizers.codec import apply_decision_vector, extract_decision_vector
from optimizers.models import OptimizationResult


PENALTY_VALUE = 1.0e12


@dataclass(slots=True)
class CandidateArtifacts:
    cases: dict[str, Any]
    solutions: dict[str, Any]
    evaluation: Any | None


@dataclass(slots=True)
class OptimizationRun:
    result: OptimizationResult
    representative_artifacts: dict[str, CandidateArtifacts]


class _ThermalOptimizationProblem(ElementwiseProblem):
    def __init__(self, base_cases: dict[str, Any], optimization_spec: dict[str, Any], evaluation_spec: dict[str, Any]) -> None:
        design_variables = optimization_spec["design_variables"]
        super().__init__(
            n_var=len(design_variables),
            n_obj=len(evaluation_spec["objectives"]),
            n_ieq_constr=len(evaluation_spec["constraints"]),
            xl=np.asarray([float(item["lower_bound"]) for item in design_variables], dtype=np.float64),
            xu=np.asarray([float(item["upper_bound"]) for item in design_variables], dtype=np.float64),
        )
        self.base_cases = base_cases
        self.optimization_spec = optimization_spec
        self.evaluation_spec = evaluation_spec
        self.history: list[dict[str, Any]] = []
        self.artifacts_by_index: dict[int, CandidateArtifacts] = {}
        self._next_evaluation_index = 1

    def evaluate_baseline(self) -> dict[str, Any]:
        first_case = next(iter(self.base_cases.values()))
        baseline_vector = extract_decision_vector(first_case, self.optimization_spec)
        record, _, _ = self.evaluate_vector(baseline_vector, source="baseline")
        return record

    def evaluate_vector(self, vector: np.ndarray, source: str) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
        evaluation_index = self._next_evaluation_index
        self._next_evaluation_index += 1
        decision_vector = {
            variable["variable_id"]: float(value)
            for variable, value in zip(self.optimization_spec["design_variables"], vector.tolist(), strict=True)
        }
        candidate_cases: dict[str, Any] = {}
        solutions: dict[str, Any] = {}
        evaluation = None
        feasible = False
        failure_reason = None
        try:
            for operating_case_id, base_case in self.base_cases.items():
                candidate_case = apply_decision_vector(base_case, self.optimization_spec, vector)
                assert_case_geometry_contracts(candidate_case)
                candidate_cases[operating_case_id] = candidate_case
                solutions[operating_case_id] = solve_case(candidate_case)
            evaluation = evaluate_operating_cases(candidate_cases, solutions, self.evaluation_spec)
            evaluation_payload = evaluation.to_dict()
            objective_values = {
                item["objective_id"]: float(item["value"]) for item in evaluation_payload["objective_summary"]
            }
            constraint_values = {
                item["constraint_id"]: _constraint_violation(item) for item in evaluation_payload["constraint_reports"]
            }
            case_reports = evaluation_payload["case_reports"]
            feasible = bool(evaluation_payload["feasible"])
            self.artifacts_by_index[evaluation_index] = CandidateArtifacts(
                cases=deepcopy(candidate_cases),
                solutions=deepcopy(solutions),
                evaluation=evaluation,
            )
        except Exception as exc:
            failure_reason = f"{type(exc).__name__}: {exc}"
            objective_values = {
                objective["objective_id"]: PENALTY_VALUE for objective in self.evaluation_spec["objectives"]
            }
            constraint_values = {
                constraint["constraint_id"]: PENALTY_VALUE for constraint in self.evaluation_spec["constraints"]
            }
            case_reports = {}

        record = {
            "evaluation_index": evaluation_index,
            "source": source,
            "feasible": feasible,
            "decision_vector": decision_vector,
            "objective_values": objective_values,
            "constraint_values": constraint_values,
            "case_reports": case_reports,
        }
        if failure_reason is not None:
            record["failure_reason"] = failure_reason
        self.history.append(record)

        objective_vector = np.asarray(
            [
                _objective_to_minimization(objective_values[item["objective_id"]], item["sense"])
                for item in self.evaluation_spec["objectives"]
            ],
            dtype=np.float64,
        )
        constraint_vector = np.asarray(
            [constraint_values[item["constraint_id"]] for item in self.evaluation_spec["constraints"]],
            dtype=np.float64,
        )
        return record, objective_vector, constraint_vector

    def _evaluate(self, x: np.ndarray, out: dict[str, Any], *args: Any, **kwargs: Any) -> None:
        _, objective_vector, constraint_vector = self.evaluate_vector(np.asarray(x, dtype=np.float64), "optimizer")
        out["F"] = objective_vector
        if self.n_ieq_constr:
            out["G"] = constraint_vector


def run_multicase_optimization(base_cases: dict[str, Any], optimization_spec: Any, evaluation_spec: Any) -> OptimizationRun:
    spec_payload = optimization_spec.to_dict() if hasattr(optimization_spec, "to_dict") else dict(optimization_spec)
    evaluation_payload = evaluation_spec.to_dict() if hasattr(evaluation_spec, "to_dict") else dict(evaluation_spec)
    loaded_cases = _load_base_cases(base_cases)
    problem = _ThermalOptimizationProblem(loaded_cases, spec_payload, evaluation_payload)
    baseline_record = problem.evaluate_baseline()

    algorithm_config = spec_payload["algorithm"]
    algorithm = _build_algorithm(algorithm_config)
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


def _load_base_cases(base_cases: dict[str, Any]) -> dict[str, Any]:
    loaded_cases: dict[str, Any] = {}
    for operating_case_id, case in base_cases.items():
        if isinstance(case, (str, Path)):
            loaded_cases[operating_case_id] = load_case(case)
        else:
            loaded_cases[operating_case_id] = case
    return loaded_cases


def _build_algorithm(algorithm_config: dict[str, Any]) -> NSGA2:
    if algorithm_config["name"] != "pymoo_nsga2":
        raise ValueError(f"Unsupported optimizer algorithm '{algorithm_config['name']}'.")
    return NSGA2(pop_size=int(algorithm_config["population_size"]))


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
            "source_case_ids": {
                operating_case_id: case.to_dict()["case_meta"]["case_id"] if hasattr(case, "to_dict") else case["case_meta"]["case_id"]
                for operating_case_id, case in loaded_cases.items()
            },
            "source_optimization_spec_id": spec_payload["spec_meta"]["spec_id"],
            "source_evaluation_spec_id": evaluation_payload["spec_meta"]["spec_id"],
        },
    }


def _constraint_violation(report: dict[str, Any]) -> float:
    relation = report["relation"]
    actual = float(report["actual"])
    limit = float(report["limit"])
    if relation == "<=":
        return actual - limit
    if relation == ">=":
        return limit - actual
    raise ValueError(f"Unsupported constraint relation '{relation}'.")


def _objective_to_minimization(value: float, sense: str) -> float:
    if sense == "minimize":
        return float(value)
    if sense == "maximize":
        return -float(value)
    raise ValueError(f"Unsupported objective sense '{sense}'.")


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
        _objective_to_minimization(candidate["objective_values"][objective["objective_id"]], objective["sense"])
        for objective in objectives
    )
    incumbent_tuple = tuple(
        _objective_to_minimization(incumbent["objective_values"][objective["objective_id"]], objective["sense"])
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
    representatives = {
        "min_hot_peak": min(
            pareto_front,
            key=lambda record: _objective_to_minimization(
                record["objective_values"][objectives[0]["objective_id"]],
                objectives[0]["sense"],
            ),
        )
    }
    if len(objectives) >= 2:
        representatives["min_resource_proxy"] = min(
            pareto_front,
            key=lambda record: _objective_to_minimization(
                record["objective_values"][objectives[1]["objective_id"]],
                objectives[1]["sense"],
            ),
        )
    if len(pareto_front) >= 2:
        representatives["knee_candidate"] = _select_knee_candidate(pareto_front, objectives)
    return representatives


def _select_knee_candidate(pareto_front: list[dict[str, Any]], objectives: list[dict[str, Any]]) -> dict[str, Any]:
    objective_matrix = np.asarray(
        [
            [
                _objective_to_minimization(record["objective_values"][objective["objective_id"]], objective["sense"])
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
