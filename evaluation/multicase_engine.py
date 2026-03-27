"""Multicase evaluation aggregation for paired operating cases."""

from __future__ import annotations

from typing import Any

from evaluation.engine import evaluate_case_solution
from evaluation.models import MultiCaseEvaluationReport


def evaluate_operating_cases(cases: dict[str, Any], solutions: dict[str, Any], spec: Any) -> MultiCaseEvaluationReport:
    spec_payload = spec.to_dict() if hasattr(spec, "to_dict") else dict(spec)
    operating_case_ids = [item["operating_case_id"] for item in spec_payload["operating_cases"]]
    missing_cases = [operating_case_id for operating_case_id in operating_case_ids if operating_case_id not in cases]
    missing_solutions = [operating_case_id for operating_case_id in operating_case_ids if operating_case_id not in solutions]
    if missing_cases:
        raise ValueError(f"Missing cases for operating cases: {', '.join(missing_cases)}.")
    if missing_solutions:
        raise ValueError(f"Missing solutions for operating cases: {', '.join(missing_solutions)}.")

    case_reports: dict[str, dict[str, Any]] = {}
    objective_summary: list[dict[str, Any]] = []
    constraint_reports: list[dict[str, Any]] = []
    source_case_ids: dict[str, str] = {}
    source_solution_ids: dict[str, str] = {}

    for operating_case_id in operating_case_ids:
        single_case_spec = {
            "schema_version": spec_payload["schema_version"],
            "spec_meta": {
                "spec_id": f"{spec_payload['spec_meta']['spec_id']}-{operating_case_id}",
                "description": f"{spec_payload['spec_meta'].get('description', '').strip()} [{operating_case_id}]".strip(),
            },
            "objectives": [
                {
                    "objective_id": objective["objective_id"],
                    "metric": objective["metric"],
                    "sense": objective["sense"],
                }
                for objective in spec_payload["objectives"]
                if objective["operating_case"] == operating_case_id
            ],
            "constraints": [
                {
                    "constraint_id": constraint["constraint_id"],
                    "metric": constraint["metric"],
                    "relation": constraint["relation"],
                    "limit": constraint["limit"],
                }
                for constraint in spec_payload["constraints"]
                if constraint["operating_case"] == operating_case_id
            ],
        }
        report = evaluate_case_solution(cases[operating_case_id], solutions[operating_case_id], single_case_spec)
        report_payload = report.to_dict()
        case_reports[operating_case_id] = report_payload
        source_case_ids[operating_case_id] = report_payload["evaluation_meta"]["case_id"]
        source_solution_ids[operating_case_id] = report_payload["evaluation_meta"]["solution_id"]
        objective_summary.extend(
            {
                "objective_id": objective["objective_id"],
                "operating_case": operating_case_id,
                "metric": objective["metric"],
                "sense": objective["sense"],
                "value": objective["value"],
            }
            for objective in report_payload["objective_summary"]
        )
        constraint_reports.extend(
            {
                "constraint_id": constraint["constraint_id"],
                "operating_case": operating_case_id,
                "metric": constraint["metric"],
                "relation": constraint["relation"],
                "limit": constraint["limit"],
                "actual": constraint["actual"],
                "margin": constraint["margin"],
                "satisfied": constraint["satisfied"],
            }
            for constraint in report_payload["constraint_reports"]
        )

    violations = [constraint for constraint in constraint_reports if not constraint["satisfied"]]
    hottest_operating_case_id, hottest_report = max(
        case_reports.items(),
        key=lambda item: float(item[1]["metric_values"]["summary.temperature_max"]),
    )
    payload = {
        "schema_version": spec_payload["schema_version"],
        "evaluation_meta": {
            "report_id": f"{spec_payload['spec_meta']['spec_id']}-multicase-evaluation",
            "spec_id": spec_payload["spec_meta"]["spec_id"],
        },
        "feasible": len(violations) == 0,
        "case_reports": case_reports,
        "objective_summary": objective_summary,
        "constraint_reports": constraint_reports,
        "violations": violations,
        "derived_signals": {
            "operating_case_ids": operating_case_ids,
            "feasible_case_count": sum(1 for report in case_reports.values() if report["feasible"]),
        },
        "worst_case_signals": {
            "highest_temperature_case_id": hottest_operating_case_id,
            "highest_temperature_value": hottest_report["metric_values"]["summary.temperature_max"],
        },
        "provenance": {
            "source_case_ids": source_case_ids,
            "source_solution_ids": source_solution_ids,
            "source_spec_id": spec_payload["spec_meta"]["spec_id"],
        },
    }
    return MultiCaseEvaluationReport.from_dict(payload)
