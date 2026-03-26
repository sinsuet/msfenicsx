import json
from pathlib import Path

import yaml

from core.io.scenario_runs import write_run_bundle


def test_write_run_bundle_creates_expected_layout(tmp_path: Path) -> None:
    output = write_run_bundle(
        tmp_path,
        scenario_id="panel-baseline",
        case_id="case-001",
        case_payload={"case_meta": {"case_id": "case-001"}},
        solution_payload={"solution_meta": {"case_id": "case-001"}},
    )

    assert (output / "case.yaml").exists()
    assert (output / "solution.yaml").exists()
    assert (output / "manifest.json").exists()
    assert (output / "logs").is_dir()
    assert (output / "fields").is_dir()
    assert (output / "tensors").is_dir()
    assert (output / "figures").is_dir()

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    case_snapshot = yaml.safe_load((output / "case.yaml").read_text(encoding="utf-8"))
    solution_snapshot = yaml.safe_load((output / "solution.yaml").read_text(encoding="utf-8"))

    assert manifest["case_snapshot"] == "case.yaml"
    assert manifest["solution_snapshot"] == "solution.yaml"
    assert case_snapshot["case_meta"]["case_id"] == "case-001"
    assert solution_snapshot["solution_meta"]["case_id"] == "case-001"
