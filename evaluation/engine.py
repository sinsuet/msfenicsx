"""Evaluation engine for thermal cases and solver outputs."""

from __future__ import annotations

from typing import Any

from evaluation.metrics import MetricResolutionError, build_derived_signals, build_metric_values
from evaluation.models import EvaluationReport, EvaluationSpec


def evaluate_case_solution(case: Any, solution: Any, spec: Any) -> EvaluationReport:
    case_payload = case.to_dict() if hasattr(case, "to_dict") else dict(case)
    solution_payload = solution.to_dict() if hasattr(solution, "to_dict") else dict(solution)
    spec_payload = spec.to_dict() if hasattr(spec, "to_dict") else dict(spec)

    required_metric_keys = {
        objective["metric"] for objective in spec_payload["objectives"]
    } | {
        constraint["metric"] for constraint in spec_payload["constraints"]
    }
    metric_values = build_metric_values(case_payload, solution_payload, required_metric_keys)
    objective_summary = _build_objective_summary(spec_payload, metric_values)
    constraint_reports = _build_constraint_reports(spec_payload, metric_values)
    violations = [report for report in constraint_reports if not report["satisfied"]]
    derived_signals = build_derived_signals(case_payload, solution_payload)

    payload = {
        "schema_version": spec_payload["schema_version"],
        "evaluation_meta": {
            "report_id": f"{case_payload['case_meta']['case_id']}-{spec_payload['spec_meta']['spec_id']}-evaluation",
            "case_id": case_payload["case_meta"]["case_id"],
            "solution_id": solution_payload["solution_meta"]["solution_id"],
            "spec_id": spec_payload["spec_meta"]["spec_id"],
        },
        "feasible": len(violations) == 0,
        "metric_values": metric_values,
        "objective_summary": objective_summary,
        "constraint_reports": constraint_reports,
        "violations": violations,
        "derived_signals": derived_signals,
        "provenance": {
            "source_case_id": case_payload["case_meta"]["case_id"],
            "source_solution_id": solution_payload["solution_meta"]["solution_id"],
            "source_spec_id": spec_payload["spec_meta"]["spec_id"],
        },
    }
    return EvaluationReport.from_dict(payload)


def _build_objective_summary(spec_payload: dict[str, Any], metric_values: dict[str, float]) -> list[dict[str, Any]]:
    objective_summary = []
    for objective in spec_payload["objectives"]:
        objective_summary.append(
            {
                "objective_id": objective["objective_id"],
                "metric": objective["metric"],
                "sense": objective["sense"],
                "value": metric_values[objective["metric"]],
            }
        )
    return objective_summary


def _build_constraint_reports(spec_payload: dict[str, Any], metric_values: dict[str, float]) -> list[dict[str, Any]]:
    constraint_reports = []
    for constraint in spec_payload["constraints"]:
        actual = metric_values[constraint["metric"]]
        limit = float(constraint["limit"])
        relation = constraint["relation"]
        if relation == "<=":
            margin = limit - actual
            satisfied = actual <= limit
        elif relation == ">=":
            margin = actual - limit
            satisfied = actual >= limit
        else:
            raise MetricResolutionError(f"Unsupported constraint relation '{relation}'.")
        constraint_reports.append(
            {
                "constraint_id": constraint["constraint_id"],
                "metric": constraint["metric"],
                "relation": relation,
                "limit": limit,
                "actual": actual,
                "margin": margin,
                "satisfied": satisfied,
            }
        )
    return constraint_reports


__all__ = ["MetricResolutionError", "EvaluationSpec", "evaluate_case_solution"]
