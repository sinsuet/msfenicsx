"""YAML and JSON helpers for canonical schema objects."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from core.schema.models import ScenarioTemplate, ThermalCase, ThermalSolution


def load_template(path: str | Path) -> ScenarioTemplate:
    return ScenarioTemplate.from_dict(_load_payload(path))


def load_case(path: str | Path) -> ThermalCase:
    return ThermalCase.from_dict(_load_payload(path))


def load_solution(path: str | Path) -> ThermalSolution:
    return ThermalSolution.from_dict(_load_payload(path))


def save_template(template: ScenarioTemplate | dict[str, Any], path: str | Path) -> Path:
    return _save_payload(_coerce_payload(template), path)


def save_case(case: ThermalCase | dict[str, Any], path: str | Path) -> Path:
    return _save_payload(_coerce_payload(case), path)


def save_solution(solution: ThermalSolution | dict[str, Any], path: str | Path) -> Path:
    return _save_payload(_coerce_payload(solution), path)


def _coerce_payload(value: ScenarioTemplate | ThermalCase | ThermalSolution | dict[str, Any]) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return value
    raise TypeError(f"Unsupported payload type: {type(value)!r}")


def _load_payload(path: str | Path) -> dict[str, Any]:
    resolved_path = Path(path)
    suffix = resolved_path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        with resolved_path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle)
    elif suffix == ".json":
        with resolved_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    else:
        raise ValueError(f"Unsupported schema file extension: {resolved_path.suffix}")
    if not isinstance(payload, dict):
        raise TypeError(f"Schema file {resolved_path} must deserialize to a mapping.")
    return payload


def _save_payload(payload: dict[str, Any], path: str | Path) -> Path:
    resolved_path = Path(path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = resolved_path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        with resolved_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(payload, handle, sort_keys=False)
    elif suffix == ".json":
        with resolved_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
    else:
        raise ValueError(f"Unsupported schema file extension: {resolved_path.suffix}")
    return resolved_path
