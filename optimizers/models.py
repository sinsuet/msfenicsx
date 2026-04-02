"""Canonical contracts for single-case optimizer-layer specs and results."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, fields
from typing import Any, Self

from optimizers.validation import validate_optimization_result_payload, validate_optimization_spec_payload


def _deepcopy_field_dict(instance: Any) -> dict[str, Any]:
    return {field.name: deepcopy(getattr(instance, field.name)) for field in fields(instance)}


@dataclass(slots=True)
class OptimizationSpec:
    schema_version: str
    spec_meta: dict[str, Any]
    benchmark_source: dict[str, Any]
    design_variables: list[dict[str, Any]]
    algorithm: dict[str, Any]
    evaluation_protocol: dict[str, Any]
    operator_control: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        copied = deepcopy(payload)
        validate_optimization_spec_payload(copied)
        return cls(**copied)

    def to_dict(self) -> dict[str, Any]:
        payload = _deepcopy_field_dict(self)
        if payload.get("operator_control") is None:
            payload.pop("operator_control", None)
        return payload


@dataclass(slots=True)
class OptimizationResult:
    schema_version: str
    run_meta: dict[str, Any]
    baseline_candidates: list[dict[str, Any]]
    pareto_front: list[dict[str, Any]]
    representative_candidates: dict[str, dict[str, Any]]
    aggregate_metrics: dict[str, Any]
    history: list[dict[str, Any]]
    provenance: dict[str, Any]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        copied = deepcopy(payload)
        validate_optimization_result_payload(copied)
        return cls(**copied)

    def to_dict(self) -> dict[str, Any]:
        return _deepcopy_field_dict(self)
