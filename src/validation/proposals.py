from __future__ import annotations

from dataclasses import asdict, is_dataclass
import tempfile
from pathlib import Path
from typing import Any

import yaml

from optimization.variable_registry import variable_registry_by_path
from thermal_state import load_state

from .bounds import (
    check_conductivity_bounds,
    check_mesh_bounds,
    check_positive_dimension,
    check_step_limit,
)
from .geometry import check_component_overlaps, check_components_inside_envelope, component_bounds


def _to_plain_data(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {key: _to_plain_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_plain_data(item) for item in value]
    return value


def _set_path(payload: Any, dotted_path: str, new_value: Any) -> None:
    parts = dotted_path.split(".")
    cursor = payload
    for part in parts[:-1]:
        if isinstance(cursor, list):
            cursor = cursor[int(part)]
        else:
            cursor = cursor[part]
    last = parts[-1]
    if isinstance(cursor, list):
        cursor[int(last)] = new_value
    else:
        cursor[last] = new_value


def _load_state_from_payload(payload: dict[str, Any]):
    with tempfile.TemporaryDirectory(prefix="msfenicsx_validate_") as tmp_dir:
        path = Path(tmp_dir) / "state.yaml"
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        return load_state(path)


def _check_change_allowed(path: str) -> str | None:
    if path in variable_registry_by_path():
        return None
    return f"change path is not allowed: {path}"


def validate_proposal_against_state(state, proposal: dict[str, Any]) -> dict[str, Any]:
    payload = _to_plain_data(state)
    registry = variable_registry_by_path()
    current_components = state.components
    design_domain = state.geometry.get("design_domain")
    if design_domain is None:
        min_x, min_y, max_x, max_y = component_bounds(current_components)
    else:
        min_x = float(design_domain["x0"])
        min_y = float(design_domain["y0"])
        max_x = min_x + float(design_domain["width"])
        max_y = min_y + float(design_domain["height"])
    envelope_width = max_x - min_x
    envelope_height = max_y - min_y

    reasons: list[str] = []
    checked_changes: list[dict[str, Any]] = []
    applyable_changes: list[dict[str, Any]] = []

    for change in proposal.get("changes", []):
        path = change["path"]
        old_value = change.get("old")
        new_value = change.get("new")
        checked_changes.append({"path": path, "old": old_value, "new": new_value})

        reason = _check_change_allowed(path)
        if reason is not None:
            reasons.append(reason)
            continue

        variable = registry[path]
        if isinstance(new_value, (int, float)) and not (variable.min_value <= float(new_value) <= variable.max_value):
            reasons.append(
                f"{path} must stay within [{variable.min_value}, {variable.max_value}], got {float(new_value):.6f}"
            )

        applyable_changes.append(change)
        step_reason = check_step_limit(
            path,
            old_value,
            new_value,
            envelope_width=envelope_width,
            envelope_height=envelope_height,
        )
        if step_reason is not None:
            reasons.append(step_reason)

        if path.endswith(".conductivity"):
            bound_reason = check_conductivity_bounds(float(new_value))
            if bound_reason is not None:
                reasons.append(bound_reason)
        elif path.endswith(".width") or path.endswith(".height"):
            dim_reason = check_positive_dimension(float(new_value), field_name=path)
            if dim_reason is not None:
                reasons.append(dim_reason)
        elif path.endswith("mesh.nx") or path.endswith("mesh.ny"):
            mesh_reason = check_mesh_bounds(int(new_value), field_name=path)
            if mesh_reason is not None:
                reasons.append(mesh_reason)
        elif path.endswith("heat_sources.0.value"):
            if float(new_value) <= 0.0:
                reasons.append(f"{path} must be > 0, got {float(new_value):.6f}")

    for change in applyable_changes:
        _set_path(payload, change["path"], change["new"])

    next_state = _load_state_from_payload(payload)
    next_components = next_state.components

    for component in next_components:
        dim_reason = check_positive_dimension(component.width, field_name=f"{component.name}.width")
        if dim_reason is not None:
            reasons.append(dim_reason)
        dim_reason = check_positive_dimension(component.height, field_name=f"{component.name}.height")
        if dim_reason is not None:
            reasons.append(dim_reason)

    reasons.extend(check_components_inside_envelope(next_components, (min_x, min_y, max_x, max_y)))
    reasons.extend(check_component_overlaps(next_components))

    for material_name, material in next_state.materials.items():
        bound_reason = check_conductivity_bounds(material.conductivity)
        if bound_reason is not None:
            reasons.append(f"{material_name}: {bound_reason}")

    reasons = list(dict.fromkeys(reasons))
    return {
        "valid": len(reasons) == 0,
        "reasons": reasons,
        "checked_changes": checked_changes,
    }
