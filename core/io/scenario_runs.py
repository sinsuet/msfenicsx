"""Write reproducible scenario run bundles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def write_run_bundle(
    output_root: str | Path,
    scenario_id: str,
    case_id: str,
    case_payload: Any,
    solution_payload: Any,
) -> Path:
    bundle_root = Path(output_root) / scenario_id / case_id
    for directory_name in ("logs", "fields", "tensors", "figures"):
        (bundle_root / directory_name).mkdir(parents=True, exist_ok=True)
    _write_yaml(bundle_root / "case.yaml", _coerce_payload(case_payload))
    _write_yaml(bundle_root / "solution.yaml", _coerce_payload(solution_payload))
    manifest = {
        "scenario_id": scenario_id,
        "case_id": case_id,
        "case_snapshot": "case.yaml",
        "solution_snapshot": "solution.yaml",
        "directories": {
            "logs": "logs",
            "fields": "fields",
            "tensors": "tensors",
            "figures": "figures",
        },
    }
    (bundle_root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return bundle_root


def write_case_solution_bundle(output_root: str | Path, case: Any, solution: Any) -> Path:
    case_payload = _coerce_payload(case)
    solution_payload = _coerce_payload(solution)
    scenario_id = case_payload["case_meta"]["scenario_id"]
    case_id = case_payload["case_meta"]["case_id"]
    return write_run_bundle(output_root, scenario_id, case_id, case_payload, solution_payload)


def _coerce_payload(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return value


def _write_yaml(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)
