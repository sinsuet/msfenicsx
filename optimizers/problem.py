"""pymoo problem definition for single-case thermal optimization."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from dataclasses import dataclass
from multiprocessing import get_context
from typing import Any

import numpy as np
from pymoo.core.problem import Problem

from core.contracts.case_contracts import assert_case_geometry_contracts
from core.schema.models import ThermalCase, ThermalSolution
from core.solver.nonlinear_solver import solve_case_artifacts
from evaluation.engine import evaluate_case_solution
from evaluation.models import EvaluationReport
from optimizers.codec import extract_decision_vector
from optimizers.cheap_constraints import evaluate_cheap_constraints, resolve_radiator_span_max
from optimizers.parallel_evaluator import evaluate_candidate_payload, resolve_evaluation_workers
from optimizers.repair import repair_case_payload_from_vector


PENALTY_VALUE = 1.0e12
solve_case = solve_case_artifacts


@dataclass(slots=True)
class CandidateArtifacts:
    case: Any
    solution: Any
    evaluation: Any | None
    field_exports: dict[str, Any] | None = None


@dataclass(slots=True)
class PreparedCandidate:
    evaluation_index: int
    source: str
    decision_vector: dict[str, float]
    metadata: dict[str, Any] | None
    candidate_payload: dict[str, Any] | None = None
    immediate_record: dict[str, Any] | None = None
    immediate_objective_vector: np.ndarray | None = None
    immediate_constraint_vector: np.ndarray | None = None


class ThermalOptimizationProblem(Problem):
    def __init__(
        self,
        base_case: Any,
        optimization_spec: Any,
        evaluation_spec: Any,
        *,
        evaluation_workers: int | None = None,
    ) -> None:
        optimization_payload = optimization_spec.to_dict() if hasattr(optimization_spec, "to_dict") else dict(optimization_spec)
        evaluation_payload = evaluation_spec.to_dict() if hasattr(evaluation_spec, "to_dict") else dict(evaluation_spec)
        design_variables = optimization_payload["design_variables"]
        super().__init__(
            n_var=len(design_variables),
            n_obj=len(evaluation_payload["objectives"]),
            n_ieq_constr=len(evaluation_payload["constraints"]),
            xl=np.asarray([float(item["lower_bound"]) for item in design_variables], dtype=np.float64),
            xu=np.asarray([float(item["upper_bound"]) for item in design_variables], dtype=np.float64),
        )
        self.base_case = base_case
        self.optimization_spec = optimization_payload
        self.evaluation_spec = evaluation_payload
        self.radiator_span_max = resolve_radiator_span_max(evaluation_payload)
        self.history: list[dict[str, Any]] = []
        self.artifacts_by_index: dict[int, CandidateArtifacts] = {}
        self._next_evaluation_index = 1
        self.current_generation: int = 0
        self.evaluation_workers = resolve_evaluation_workers(evaluation_workers)
        self._executor: ProcessPoolExecutor | None = None

    def evaluate_baseline(self) -> dict[str, Any]:
        baseline_vector = extract_decision_vector(self.base_case, self.optimization_spec)
        record, _, _ = self.evaluate_vector(baseline_vector, source="baseline")
        return record

    def evaluate_vector(
        self,
        vector: np.ndarray,
        source: str,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
        records, objective_matrix, constraint_matrix = self.evaluate_vectors(
            np.asarray([vector], dtype=np.float64),
            source=source,
            metadata_rows=[metadata],
        )
        return records[0], objective_matrix[0], constraint_matrix[0]

    def evaluate_vectors(
        self,
        vectors: np.ndarray,
        *,
        source: str,
        metadata_rows: list[dict[str, Any] | None] | None = None,
    ) -> tuple[list[dict[str, Any]], np.ndarray, np.ndarray]:
        vector_matrix = np.asarray(vectors, dtype=np.float64)
        if vector_matrix.ndim == 1:
            vector_matrix = vector_matrix.reshape(1, -1)
        if metadata_rows is None:
            metadata_rows = [None] * len(vector_matrix)
        if len(metadata_rows) != len(vector_matrix):
            raise ValueError("metadata_rows length must match the number of vectors.")

        prepared_candidates = [
            self._prepare_candidate(np.asarray(vector, dtype=np.float64), source=source, metadata=metadata)
            for vector, metadata in zip(vector_matrix, metadata_rows, strict=True)
        ]
        worker_results = self._collect_worker_results(prepared_candidates)

        records: list[dict[str, Any]] = []
        objective_vectors: list[np.ndarray] = []
        constraint_vectors: list[np.ndarray] = []
        for prepared in prepared_candidates:
            if prepared.immediate_record is not None:
                record = prepared.immediate_record
                objective_vector = prepared.immediate_objective_vector
                constraint_vector = prepared.immediate_constraint_vector
                self.history.append(record)
            else:
                record, objective_vector, constraint_vector = self._commit_worker_result(
                    prepared,
                    worker_results.get(prepared.evaluation_index),
                )
            records.append(record)
            objective_vectors.append(objective_vector)
            constraint_vectors.append(constraint_vector)
        return (
            records,
            np.asarray(objective_vectors, dtype=np.float64),
            np.asarray(constraint_vectors, dtype=np.float64),
        )

    def _evaluate(self, x: np.ndarray, out: dict[str, Any], *args: Any, **kwargs: Any) -> None:
        del args, kwargs
        vector_matrix = np.asarray(x, dtype=np.float64)
        is_single = vector_matrix.ndim == 1
        if is_single:
            vector_matrix = vector_matrix.reshape(1, -1)
        _, objective_matrix, constraint_matrix = self.evaluate_vectors(vector_matrix, source="optimizer")
        out["F"] = objective_matrix[0] if is_single else objective_matrix
        if self.n_ieq_constr:
            out["G"] = constraint_matrix[0] if is_single else constraint_matrix
        self.current_generation += 1

    def close(self) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=True, cancel_futures=False)
            self._executor = None

    def _prepare_candidate(
        self,
        vector: np.ndarray,
        *,
        source: str,
        metadata: dict[str, Any] | None,
    ) -> PreparedCandidate:
        evaluation_index = self._next_evaluation_index
        self._next_evaluation_index += 1
        decision_vector = {
            variable["variable_id"]: float(value)
            for variable, value in zip(self.optimization_spec["design_variables"], vector.tolist(), strict=True)
        }
        try:
            candidate_payload = repair_case_payload_from_vector(
                self.base_case,
                self.optimization_spec,
                vector,
                radiator_span_max=self.radiator_span_max,
            )
            cheap_result = evaluate_cheap_constraints(candidate_payload, self.evaluation_spec)
            if not cheap_result.feasible:
                return self._build_immediate_penalty(
                    evaluation_index=evaluation_index,
                    source=source,
                    decision_vector=decision_vector,
                    metadata=metadata,
                    failure_reason="cheap_constraint_violation",
                    constraint_values={
                        constraint["constraint_id"]: cheap_result.constraint_values.get(
                            constraint["constraint_id"],
                            PENALTY_VALUE,
                        )
                        for constraint in self.evaluation_spec["constraints"]
                    },
                    solver_skipped=True,
                    cheap_constraint_issues=list(cheap_result.geometry_issues),
                )
            return PreparedCandidate(
                evaluation_index=evaluation_index,
                source=source,
                decision_vector=decision_vector,
                metadata=metadata,
                candidate_payload=candidate_payload,
            )
        except Exception as exc:
            return self._build_immediate_penalty(
                evaluation_index=evaluation_index,
                source=source,
                decision_vector=decision_vector,
                metadata=metadata,
                failure_reason=f"{type(exc).__name__}: {exc}",
            )

    def _collect_worker_results(self, prepared_candidates: list[PreparedCandidate]) -> dict[int, dict[str, Any]]:
        executable = [prepared for prepared in prepared_candidates if prepared.candidate_payload is not None]
        if not executable:
            return {}
        if self.evaluation_workers <= 1 or len(executable) <= 1:
            return {
                prepared.evaluation_index: evaluate_candidate_payload(prepared.candidate_payload, self.evaluation_spec)
                for prepared in executable
            }

        executor = self._ensure_executor()
        futures = {
            executor.submit(evaluate_candidate_payload, prepared.candidate_payload, self.evaluation_spec): prepared.evaluation_index
            for prepared in executable
        }
        results: dict[int, dict[str, Any]] = {}
        for future in as_completed(futures):
            evaluation_index = futures[future]
            try:
                results[evaluation_index] = future.result()
            except Exception as exc:  # pragma: no cover - safety net for executor issues
                results[evaluation_index] = {
                    "success": False,
                    "failure_reason": f"{type(exc).__name__}: {exc}",
                }
        return results

    def _commit_worker_result(
        self,
        prepared: PreparedCandidate,
        worker_result: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
        if worker_result is None or not worker_result.get("success", False):
            record = self._build_record(
                evaluation_index=prepared.evaluation_index,
                source=prepared.source,
                decision_vector=prepared.decision_vector,
                objective_values=self._penalty_objective_values(),
                constraint_values=self._penalty_constraint_values(),
                evaluation_report={},
                feasible=False,
                metadata=prepared.metadata,
                failure_reason=None if worker_result is None else worker_result.get("failure_reason"),
            )
        else:
            evaluation_payload = dict(worker_result["evaluation_payload"])
            objective_values = {
                item["objective_id"]: float(item["value"]) for item in evaluation_payload["objective_summary"]
            }
            constraint_values = {
                item["constraint_id"]: _constraint_violation(item) for item in evaluation_payload["constraint_reports"]
            }
            candidate_case = ThermalCase.from_dict(worker_result["case_payload"])
            solution = ThermalSolution.from_dict(worker_result["solution_payload"])
            evaluation = EvaluationReport.from_dict(evaluation_payload)
            self.artifacts_by_index[prepared.evaluation_index] = CandidateArtifacts(
                case=deepcopy(candidate_case),
                solution=deepcopy(solution),
                evaluation=evaluation,
                field_exports=deepcopy(worker_result.get("field_exports")),
            )
            record = self._build_record(
                evaluation_index=prepared.evaluation_index,
                source=prepared.source,
                decision_vector=prepared.decision_vector,
                objective_values=objective_values,
                constraint_values=constraint_values,
                evaluation_report=evaluation_payload,
                feasible=bool(evaluation_payload["feasible"]),
                metadata=prepared.metadata,
            )
        self.history.append(record)
        return record, self._objective_vector(record["objective_values"]), self._constraint_vector(record["constraint_values"])

    def _build_immediate_penalty(
        self,
        *,
        evaluation_index: int,
        source: str,
        decision_vector: dict[str, float],
        metadata: dict[str, Any] | None,
        failure_reason: str,
        constraint_values: dict[str, float] | None = None,
        solver_skipped: bool = False,
        cheap_constraint_issues: list[str] | None = None,
    ) -> PreparedCandidate:
        effective_constraint_values = (
            self._penalty_constraint_values() if constraint_values is None else dict(constraint_values)
        )
        record = self._build_record(
            evaluation_index=evaluation_index,
            source=source,
            decision_vector=decision_vector,
            objective_values=self._penalty_objective_values(),
            constraint_values=effective_constraint_values,
            evaluation_report={},
            feasible=False,
            metadata=metadata,
            failure_reason=failure_reason,
            solver_skipped=solver_skipped,
            cheap_constraint_issues=cheap_constraint_issues,
        )
        return PreparedCandidate(
            evaluation_index=evaluation_index,
            source=source,
            decision_vector=decision_vector,
            metadata=metadata,
            immediate_record=record,
            immediate_objective_vector=self._objective_vector(record["objective_values"]),
            immediate_constraint_vector=self._constraint_vector(record["constraint_values"]),
        )

    def _build_record(
        self,
        *,
        evaluation_index: int,
        source: str,
        decision_vector: dict[str, float],
        objective_values: dict[str, float],
        constraint_values: dict[str, float],
        evaluation_report: dict[str, Any],
        feasible: bool,
        metadata: dict[str, Any] | None,
        failure_reason: str | None = None,
        solver_skipped: bool = False,
        cheap_constraint_issues: list[str] | None = None,
    ) -> dict[str, Any]:
        record = {
            "evaluation_index": evaluation_index,
            "generation": int(self.current_generation),
            "source": source,
            "feasible": feasible,
            "decision_vector": decision_vector,
            "objective_values": objective_values,
            "constraint_values": constraint_values,
            "evaluation_report": evaluation_report,
        }
        if metadata:
            record.update(metadata)
        if failure_reason is not None:
            record["failure_reason"] = failure_reason
        if solver_skipped:
            record["solver_skipped"] = True
        if cheap_constraint_issues:
            record["cheap_constraint_issues"] = list(cheap_constraint_issues)
        return record

    def _objective_vector(self, objective_values: dict[str, float]) -> np.ndarray:
        return np.asarray(
            [
                _objective_to_minimization(objective_values[item["objective_id"]], item["sense"])
                for item in self.evaluation_spec["objectives"]
            ],
            dtype=np.float64,
        )

    def _constraint_vector(self, constraint_values: dict[str, float]) -> np.ndarray:
        return np.asarray(
            [constraint_values[item["constraint_id"]] for item in self.evaluation_spec["constraints"]],
            dtype=np.float64,
        )

    def _penalty_objective_values(self) -> dict[str, float]:
        return {
            objective["objective_id"]: PENALTY_VALUE for objective in self.evaluation_spec["objectives"]
        }

    def _penalty_constraint_values(self) -> dict[str, float]:
        return {
            constraint["constraint_id"]: PENALTY_VALUE for constraint in self.evaluation_spec["constraints"]
        }

    def _ensure_executor(self) -> ProcessPoolExecutor:
        if self._executor is None:
            self._executor = ProcessPoolExecutor(
                max_workers=self.evaluation_workers,
                mp_context=get_context("spawn"),
            )
        return self._executor


def constraint_violation(report: dict[str, Any]) -> float:
    return _constraint_violation(report)


def objective_to_minimization(value: float, sense: str) -> float:
    return _objective_to_minimization(value, sense)


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
