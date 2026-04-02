"""Build canonical thermal_solution objects from solver outputs."""

from __future__ import annotations

from typing import Any

from core.schema.models import ThermalSolution


def build_solution(case: Any, sampled_fields: dict[str, Any], diagnostics: dict[str, Any]) -> ThermalSolution:
    case_payload = case.to_dict() if hasattr(case, "to_dict") else dict(case)
    payload = {
        "schema_version": case_payload["schema_version"],
        "solution_meta": {
            "solution_id": f"{case_payload['case_meta']['case_id']}-solution",
            "case_id": case_payload["case_meta"]["case_id"],
        },
        "solver_diagnostics": diagnostics,
        "field_records": sampled_fields["field_records"],
        "summary_metrics": sampled_fields["summary_metrics"],
        "component_summaries": sampled_fields["component_summaries"],
        "provenance": {
            "source_case_id": case_payload["case_meta"]["case_id"],
            "solver": diagnostics["solver"],
        },
    }
    return ThermalSolution.from_dict(payload)


def build_solution_artifacts(case: Any, sampled_fields: dict[str, Any], diagnostics: dict[str, Any]) -> dict[str, Any]:
    return {
        "solution": build_solution(case, sampled_fields, diagnostics),
        "field_exports": sampled_fields.get("field_exports"),
    }
