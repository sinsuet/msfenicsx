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
    _write_field_figures(resolved_bundle_root, field_exports)
    return exported_fields


def _write_field_figures(bundle_root: Path, field_exports: dict[str, Any]) -> None:
    field_view = field_exports.get("field_view") or {}
    panel_domain = dict(field_view.get("panel_domain", {}))
    arrays = field_exports.get("arrays") or {}
    temperature = arrays.get("temperature")
    gradient = arrays.get("gradient_magnitude")
    if not panel_domain or temperature is None or gradient is None:
        return

    temperature_grid = np.asarray(temperature, dtype=np.float64)
    gradient_grid = np.asarray(gradient, dtype=np.float64)
    xs = np.linspace(0.0, float(panel_domain["width"]), temperature_grid.shape[1], dtype=np.float64)
    ys = np.linspace(0.0, float(panel_domain["height"]), temperature_grid.shape[0], dtype=np.float64)
    layout = dict(field_view.get("layout", {}))
    figures_root = bundle_root / "figures"
    figures_root.mkdir(parents=True, exist_ok=True)

    from visualization.figures.gradient_field import render_gradient_field
    from visualization.figures.layout_evolution import render_layout_snapshot
    from visualization.figures.temperature_field import render_temperature_field

    render_layout_snapshot(
        frame={
            "generation": 0,
            "title": "Layout",
            "panel_width": float(panel_domain["width"]),
            "panel_height": float(panel_domain["height"]),
            "components": list(layout.get("components", [])),
            "line_sinks": list(layout.get("line_sinks", [])),
        },
        output=figures_root / "layout.png",
    )
    render_temperature_field(
        grid=temperature_grid,
        xs=xs,
        ys=ys,
        layout=layout,
        hotspot=(field_view.get("temperature") or {}).get("hotspot"),
        output=figures_root / "temperature_field.png",
    )
    render_gradient_field(
        grid=gradient_grid,
        xs=xs,
        ys=ys,
        layout=layout,
        output=figures_root / "gradient_field.png",
    )


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
