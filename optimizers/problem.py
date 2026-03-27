"""pymoo problem definition for multicase thermal optimization."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

import numpy as np
from pymoo.core.problem import ElementwiseProblem

from core.contracts.case_contracts import assert_case_geometry_contracts
from core.solver.nonlinear_solver import solve_case
from evaluation.multicase_engine import evaluate_operating_cases
from optimizers.codec import extract_decision_vector
from optimizers.repair import repair_case_from_vector


PENALTY_VALUE = 1.0e12


@dataclass(slots=True)
class CandidateArtifacts:
    cases: dict[str, Any]
    solutions: dict[str, Any]
    evaluation: Any | None


class ThermalOptimizationProblem(ElementwiseProblem):
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

    def evaluate_vector(
        self,
        vector: np.ndarray,
        source: str,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
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
                candidate_case = repair_case_from_vector(base_case, self.optimization_spec, vector)
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
        if metadata:
            record.update(metadata)
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
