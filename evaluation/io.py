"""YAML and JSON helpers for evaluation-layer contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from evaluation.models import EvaluationReport, EvaluationSpec, MultiCaseEvaluationReport, MultiCaseEvaluationSpec


def load_spec(path: str | Path) -> EvaluationSpec:
    return EvaluationSpec.from_dict(_load_payload(path))


def load_report(path: str | Path) -> EvaluationReport:
    return EvaluationReport.from_dict(_load_payload(path))


def load_multicase_spec(path: str | Path) -> MultiCaseEvaluationSpec:
    return MultiCaseEvaluationSpec.from_dict(_load_payload(path))


def load_multicase_report(path: str | Path) -> MultiCaseEvaluationReport:
    return MultiCaseEvaluationReport.from_dict(_load_payload(path))


def save_spec(spec: EvaluationSpec | dict[str, Any], path: str | Path) -> Path:
    return _save_payload(_coerce_payload(spec), path)


def save_report(report: EvaluationReport | dict[str, Any], path: str | Path) -> Path:
    return _save_payload(_coerce_payload(report), path)


def save_multicase_spec(spec: MultiCaseEvaluationSpec | dict[str, Any], path: str | Path) -> Path:
    return _save_payload(_coerce_payload(spec), path)


def save_multicase_report(report: MultiCaseEvaluationReport | dict[str, Any], path: str | Path) -> Path:
    return _save_payload(_coerce_payload(report), path)


def _coerce_payload(
    value: EvaluationSpec | EvaluationReport | MultiCaseEvaluationSpec | MultiCaseEvaluationReport | dict[str, Any]
) -> dict[str, Any]:
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
        raise ValueError(f"Unsupported evaluation file extension: {resolved_path.suffix}")
    if not isinstance(payload, dict):
        raise TypeError(f"Evaluation file {resolved_path} must deserialize to a mapping.")
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
        raise ValueError(f"Unsupported evaluation file extension: {resolved_path.suffix}")
    return resolved_path
