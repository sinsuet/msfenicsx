import json
from pathlib import Path

import yaml

from core.io.scenario_runs import write_run_bundle
from evaluation.artifacts import write_evaluation_snapshot
from evaluation.models import EvaluationReport


def _report() -> EvaluationReport:
    return EvaluationReport.from_dict(
        {
            "schema_version": "1.0",
            "evaluation_meta": {
                "report_id": "eval-001",
                "case_id": "case-001",
                "solution_id": "sol-001",
                "spec_id": "panel-single-objective",
            },
            "feasible": True,
            "metric_values": {"summary.temperature_max": 322.4},
            "objective_summary": [
                {
                    "objective_id": "minimize_peak_temperature",
                    "metric": "summary.temperature_max",
                    "sense": "minimize",
                    "value": 322.4,
                }
            ],
            "constraint_reports": [],
            "violations": [],
            "derived_signals": {"hotspot_component_id": "comp-001"},
            "provenance": {
                "source_case_id": "case-001",
                "source_solution_id": "sol-001",
                "source_spec_id": "panel-single-objective",
            },
        }
    )


def test_write_evaluation_snapshot_updates_bundle_manifest(tmp_path: Path) -> None:
    bundle_root = write_run_bundle(
        tmp_path,
        scenario_id="panel-baseline",
        case_id="case-001",
        case_payload={"case_meta": {"case_id": "case-001"}},
        solution_payload={"solution_meta": {"case_id": "case-001"}},
    )

    report_path = write_evaluation_snapshot(bundle_root, _report())

    assert report_path == bundle_root / "evaluation.yaml"
    manifest = json.loads((bundle_root / "manifest.json").read_text(encoding="utf-8"))
    report_payload = yaml.safe_load((bundle_root / "evaluation.yaml").read_text(encoding="utf-8"))

    assert manifest["evaluation_snapshot"] == "evaluation.yaml"
    assert report_payload["evaluation_meta"]["report_id"] == "eval-001"
