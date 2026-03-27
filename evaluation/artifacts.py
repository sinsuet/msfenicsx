"""Helpers for attaching evaluation reports to scenario run bundles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def write_evaluation_snapshot(bundle_root: str | Path, report: Any) -> Path:
    resolved_bundle_root = Path(bundle_root)
    resolved_bundle_root.mkdir(parents=True, exist_ok=True)
    report_path = resolved_bundle_root / "evaluation.yaml"
    payload = report.to_dict() if hasattr(report, "to_dict") else report
    with report_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)

    manifest_path = resolved_bundle_root / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {}
    manifest["evaluation_snapshot"] = "evaluation.yaml"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return report_path
