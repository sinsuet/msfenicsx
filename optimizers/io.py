"""YAML and JSON helpers for optimizer-layer contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from optimizers.models import OptimizationResult, OptimizationSpec


def load_optimization_spec(path: str | Path) -> OptimizationSpec:
    return OptimizationSpec.from_dict(_load_payload(path))


def load_optimization_result(path: str | Path) -> OptimizationResult:
    return OptimizationResult.from_dict(_load_payload(path))


def save_optimization_spec(spec: OptimizationSpec | dict[str, Any], path: str | Path) -> Path:
    return _save_payload(_coerce_payload(spec), path)


def save_optimization_result(result: OptimizationResult | dict[str, Any], path: str | Path) -> Path:
    return _save_payload(_coerce_payload(result), path)


def resolve_evaluation_spec_path(spec_path: str | Path, optimization_spec: OptimizationSpec | dict[str, Any]) -> Path:
    spec_payload = _coerce_payload(optimization_spec)
    raw_path = Path(spec_payload["evaluation_protocol"]["evaluation_spec_path"])
    if raw_path.is_absolute():
        return raw_path
    if raw_path.exists():
        return raw_path
    return Path(spec_path).resolve().parent / raw_path


def _coerce_payload(value: OptimizationSpec | OptimizationResult | dict[str, Any]) -> dict[str, Any]:
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
        raise ValueError(f"Unsupported optimizer file extension: {resolved_path.suffix}")
    if not isinstance(payload, dict):
        raise TypeError(f"Optimizer file {resolved_path} must deserialize to a mapping.")
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
        raise ValueError(f"Unsupported optimizer file extension: {resolved_path.suffix}")
    return resolved_path
