"""Canonical schema object definitions for Phase 1."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, fields
from typing import Any, Self

from core.schema.validation import (
    validate_scenario_template_payload,
    validate_thermal_case_payload,
    validate_thermal_solution_payload,
)


def _deepcopy_field_dict(instance: Any) -> dict[str, Any]:
    return {field.name: deepcopy(getattr(instance, field.name)) for field in fields(instance)}


@dataclass(slots=True)
class ScenarioTemplate:
    schema_version: str
    template_meta: dict[str, Any]
    coordinate_system: dict[str, Any]
    panel_domain: dict[str, Any]
    placement_regions: list[dict[str, Any]]
    keep_out_regions: list[dict[str, Any]]
    component_families: list[dict[str, Any]]
    boundary_feature_families: list[dict[str, Any]]
    load_rules: list[dict[str, Any]]
    material_rules: list[dict[str, Any]]
    mesh_profile: dict[str, Any]
    solver_profile: dict[str, Any]
    generation_rules: dict[str, Any]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        copied = deepcopy(payload)
        validate_scenario_template_payload(copied)
        return cls(**copied)

    def to_dict(self) -> dict[str, Any]:
        return _deepcopy_field_dict(self)


@dataclass(slots=True)
class ThermalCase:
    schema_version: str
    case_meta: dict[str, Any]
    coordinate_system: dict[str, Any]
    panel_domain: dict[str, Any]
    materials: dict[str, Any]
    components: list[dict[str, Any]]
    boundary_features: list[dict[str, Any]]
    loads: list[dict[str, Any]]
    physics: dict[str, Any]
    mesh_profile: dict[str, Any]
    solver_profile: dict[str, Any]
    provenance: dict[str, Any]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        copied = deepcopy(payload)
        validate_thermal_case_payload(copied)
        return cls(**copied)

    def to_dict(self) -> dict[str, Any]:
        return _deepcopy_field_dict(self)


@dataclass(slots=True)
class ThermalSolution:
    schema_version: str
    solution_meta: dict[str, Any]
    solver_diagnostics: dict[str, Any]
    field_records: dict[str, Any]
    summary_metrics: dict[str, Any]
    component_summaries: list[dict[str, Any]]
    provenance: dict[str, Any]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        copied = deepcopy(payload)
        validate_thermal_solution_payload(copied)
        return cls(**copied)

    def to_dict(self) -> dict[str, Any]:
        return _deepcopy_field_dict(self)
