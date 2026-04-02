from pathlib import Path

from evaluation.io import (
    load_report,
    load_spec,
    save_report,
    save_spec,
)
from evaluation.models import EvaluationReport, EvaluationSpec


def _spec_payload() -> dict:
    return {
        "schema_version": "1.0",
        "spec_meta": {
            "spec_id": "panel-single-objective",
            "description": "Single-objective thermal evaluation baseline.",
        },
        "objectives": [
            {
                "objective_id": "minimize_peak_temperature",
                "metric": "summary.temperature_max",
                "sense": "minimize",
            }
        ],
        "constraints": [
            {
                "constraint_id": "payload_peak_limit",
                "metric": "component.comp-001.temperature_max",
                "relation": "<=",
                "limit": 325.0,
            }
        ],
    }


def _report_payload() -> dict:
    return {
        "schema_version": "1.0",
        "evaluation_meta": {
            "report_id": "eval-001",
            "case_id": "case-001",
            "solution_id": "sol-001",
            "spec_id": "panel-single-objective",
        },
        "feasible": True,
        "metric_values": {
            "summary.temperature_max": 322.4,
            "component.comp-001.temperature_max": 320.0,
        },
        "objective_summary": [
            {
                "objective_id": "minimize_peak_temperature",
                "metric": "summary.temperature_max",
                "sense": "minimize",
                "value": 322.4,
            }
        ],
        "constraint_reports": [
            {
                "constraint_id": "payload_peak_limit",
                "metric": "component.comp-001.temperature_max",
                "relation": "<=",
                "limit": 325.0,
                "actual": 320.0,
                "margin": 5.0,
                "satisfied": True,
            }
        ],
        "violations": [],
        "derived_signals": {
            "hotspot_component_id": "comp-001",
            "hotspot_temperature_max": 320.0,
            "panel_area": 0.8,
            "total_power": 28.0,
            "power_density": 35.0,
        },
        "provenance": {
            "source_case_id": "case-001",
            "source_solution_id": "sol-001",
            "source_spec_id": "panel-single-objective",
        },
    }


def test_save_and_load_yaml_round_trip(tmp_path: Path) -> None:
    spec_path = tmp_path / "evaluation_spec.yaml"
    report_path = tmp_path / "evaluation_report.yaml"

    save_spec(EvaluationSpec.from_dict(_spec_payload()), spec_path)
    save_report(EvaluationReport.from_dict(_report_payload()), report_path)

    assert load_spec(spec_path).to_dict() == _spec_payload()
    assert load_report(report_path).to_dict() == _report_payload()
