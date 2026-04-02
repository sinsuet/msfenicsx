"""Write reproducible scenario run bundles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import yaml


def write_run_bundle(
    output_root: str | Path,
    scenario_id: str,
    case_id: str,
    case_payload: Any,
    solution_payload: Any,
    *,
    field_exports: dict[str, Any] | None = None,
) -> Path:
    bundle_root = Path(output_root) / scenario_id / case_id
    for directory_name in _bundle_directories().values():
        (bundle_root / directory_name).mkdir(parents=True, exist_ok=True)
    _write_yaml(bundle_root / "case.yaml", _coerce_payload(case_payload))
    _write_yaml(bundle_root / "solution.yaml", _coerce_payload(solution_payload))
    exported_fields = write_field_export_artifacts(bundle_root, field_exports) if field_exports is not None else None
    manifest = {
        "scenario_id": scenario_id,
        "case_id": case_id,
        "case_snapshot": "case.yaml",
        "solution_snapshot": "solution.yaml",
        "directories": _bundle_directories(),
    }
    if exported_fields is not None:
        manifest["field_exports"] = exported_fields
    (bundle_root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return bundle_root


def write_case_solution_bundle(
    output_root: str | Path,
    case: Any,
    solution: Any,
    *,
    field_exports: dict[str, Any] | None = None,
) -> Path:
    case_payload = _coerce_payload(case)
    solution_payload = _coerce_payload(solution)
    scenario_id = case_payload["case_meta"]["scenario_id"]
    case_id = case_payload["case_meta"]["case_id"]
    return write_run_bundle(
        output_root,
        scenario_id,
        case_id,
        case_payload,
        solution_payload,
        field_exports=field_exports,
    )


def write_field_export_artifacts(bundle_root: str | Path, field_exports: dict[str, Any]) -> dict[str, str]:
    resolved_bundle_root = Path(bundle_root)
    (resolved_bundle_root / "fields").mkdir(parents=True, exist_ok=True)
    (resolved_bundle_root / "summaries").mkdir(parents=True, exist_ok=True)
    arrays = field_exports.get("arrays") or {}
    exported_fields: dict[str, str] = {}
    for field_name, filename in (
        ("temperature", "temperature_grid.npz"),
        ("gradient_magnitude", "gradient_magnitude_grid.npz"),
    ):
        if field_name not in arrays:
            continue
        relative_path = Path("fields") / filename
        np.savez_compressed(
            resolved_bundle_root / relative_path,
            values=np.asarray(arrays[field_name], dtype=np.float64),
        )
        exported_fields[f"{field_name}_grid"] = relative_path.as_posix()

    field_view_path = resolved_bundle_root / "summaries" / "field_view.json"
    field_view_path.write_text(json.dumps(field_exports["field_view"], indent=2) + "\n", encoding="utf-8")
    exported_fields["field_view"] = Path("summaries").joinpath("field_view.json").as_posix()
    return exported_fields


def _coerce_payload(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return value


def _bundle_directories() -> dict[str, str]:
    return {
        "logs": "logs",
        "fields": "fields",
        "summaries": "summaries",
        "figures": "figures",
        "pages": "pages",
    }


def _write_yaml(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)
