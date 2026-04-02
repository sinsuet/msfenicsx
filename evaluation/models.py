"""Canonical models for evaluation-layer inputs and outputs."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, fields
from typing import Any, Self

from evaluation.validation import (
    validate_report_payload,
    validate_spec_payload,
)


def _deepcopy_field_dict(instance: Any) -> dict[str, Any]:
    return {field.name: deepcopy(getattr(instance, field.name)) for field in fields(instance)}


@dataclass(slots=True)
class EvaluationSpec:
    schema_version: str
    spec_meta: dict[str, Any]
    objectives: list[dict[str, Any]]
    constraints: list[dict[str, Any]]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        copied = deepcopy(payload)
        validate_spec_payload(copied)
        return cls(**copied)

    def to_dict(self) -> dict[str, Any]:
        return _deepcopy_field_dict(self)


@dataclass(slots=True)
class EvaluationReport:
    schema_version: str
    evaluation_meta: dict[str, Any]
    feasible: bool
    metric_values: dict[str, float]
    objective_summary: list[dict[str, Any]]
    constraint_reports: list[dict[str, Any]]
    violations: list[dict[str, Any]]
    derived_signals: dict[str, Any]
    provenance: dict[str, Any]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        copied = deepcopy(payload)
        validate_report_payload(copied)
        return cls(**copied)

    def to_dict(self) -> dict[str, Any]:
        return _deepcopy_field_dict(self)
