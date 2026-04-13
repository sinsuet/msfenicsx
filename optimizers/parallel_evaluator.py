"""Worker-safe helpers for bounded parallel candidate evaluation."""

from __future__ import annotations

from copy import deepcopy
import os
from typing import Any

from core.contracts.case_contracts import assert_case_geometry_contracts
from core.schema.models import ThermalCase
from core.solver.nonlinear_solver import solve_case_artifacts
from evaluation.engine import evaluate_case_solution


def resolve_evaluation_workers(requested: int | None) -> int:
    if requested is not None:
        value = int(requested)
        if value < 1:
            raise ValueError("evaluation_workers must be >= 1.")
        return value
    cpu_count = os.cpu_count() or 1
    return 1 if cpu_count <= 4 else 2


def evaluate_candidate_payload(candidate_payload: dict[str, Any], evaluation_spec: dict[str, Any]) -> dict[str, Any]:
    try:
        candidate_case = ThermalCase.from_dict(candidate_payload)
        assert_case_geometry_contracts(candidate_case)
        solve_outputs = solve_case_artifacts(candidate_case)
        solution = solve_outputs["solution"]
        evaluation = evaluate_case_solution(candidate_case, solution, evaluation_spec)
        evaluation_payload = evaluation.to_dict()
        return {
            "success": True,
            "case_payload": candidate_case.to_dict(),
            "solution_payload": solution.to_dict() if hasattr(solution, "to_dict") else dict(solution),
            "evaluation_payload": evaluation_payload,
            "objective_values": {
                item["objective_id"]: float(item["value"]) for item in evaluation_payload["objective_summary"]
            },
            "constraint_values": {
                item["constraint_id"]: _constraint_violation(item)
                for item in evaluation_payload["constraint_reports"]
            },
            "field_exports": deepcopy(solve_outputs.get("field_exports")),
        }
    except Exception as exc:  # pragma: no cover - exercised through caller-facing tests
        return {
            "success": False,
            "failure_reason": f"{type(exc).__name__}: {exc}",
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
