from pathlib import Path

from evaluation.io import (
    load_multicase_report,
    load_multicase_spec,
    load_report,
    load_spec,
    save_multicase_report,
    save_multicase_spec,
    save_report,
    save_spec,
)
from evaluation.models import EvaluationReport, EvaluationSpec, MultiCaseEvaluationReport, MultiCaseEvaluationSpec


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


def _multicase_spec_payload() -> dict:
    return {
        "schema_version": "1.0",
        "spec_meta": {
            "spec_id": "panel-four-component-hot-cold-baseline",
            "description": "Paper-grade hot/cold multicase evaluation baseline.",
        },
        "operating_cases": [
            {"operating_case_id": "hot", "description": "Hot operating case"},
            {"operating_case_id": "cold", "description": "Cold operating case"},
        ],
        "objectives": [
            {
                "objective_id": "minimize_hot_pa_peak",
                "operating_case": "hot",
                "metric": "component.rf_power_amp.temperature_max",
                "sense": "minimize",
            },
            {
                "objective_id": "maximize_cold_battery_min",
                "operating_case": "cold",
                "metric": "component.battery_pack.temperature_min",
                "sense": "maximize",
            }
        ],
        "constraints": [
            {
                "constraint_id": "hot_pa_limit",
                "operating_case": "hot",
                "metric": "component.rf_power_amp.temperature_max",
                "relation": "<=",
                "limit": 355.0,
            }
        ],
    }


def _multicase_report_payload() -> dict:
    return {
        "schema_version": "1.0",
        "evaluation_meta": {
            "report_id": "panel-four-component-hot-cold-baseline-eval-001",
            "spec_id": "panel-four-component-hot-cold-baseline",
        },
        "feasible": True,
        "case_reports": {
            "hot": _report_payload(),
            "cold": _report_payload() | {
                "evaluation_meta": {
                    "report_id": "eval-002",
                    "case_id": "case-002",
                    "solution_id": "sol-002",
                    "spec_id": "panel-four-component-hot-cold-baseline",
                }
            },
        },
        "objective_summary": [
            {
                "objective_id": "minimize_hot_pa_peak",
                "operating_case": "hot",
                "metric": "component.rf_power_amp.temperature_max",
                "sense": "minimize",
                "value": 322.4,
            }
        ],
        "constraint_reports": [],
        "violations": [],
        "derived_signals": {"operating_case_ids": ["hot", "cold"]},
        "worst_case_signals": {"highest_temperature_case_id": "hot", "highest_temperature_value": 322.4},
        "provenance": {
            "source_case_ids": {"hot": "case-001", "cold": "case-002"},
            "source_solution_ids": {"hot": "sol-001", "cold": "sol-002"},
            "source_spec_id": "panel-four-component-hot-cold-baseline",
        },
    }


def test_save_and_load_multicase_yaml_round_trip(tmp_path: Path) -> None:
    spec_path = tmp_path / "multicase_spec.yaml"
    report_path = tmp_path / "multicase_report.yaml"

    save_multicase_spec(MultiCaseEvaluationSpec.from_dict(_multicase_spec_payload()), spec_path)
    save_multicase_report(MultiCaseEvaluationReport.from_dict(_multicase_report_payload()), report_path)

    assert load_multicase_spec(spec_path).to_dict() == _multicase_spec_payload()
    assert load_multicase_report(report_path).to_dict() == _multicase_report_payload()
