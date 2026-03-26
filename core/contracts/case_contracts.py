"""Shared case legality checks for generator and solver boundaries."""

from __future__ import annotations

from collections.abc import Mapping
from itertools import combinations
from typing import Any

from core.geometry.layout_rules import component_within_domain, components_overlap, validate_line_sink_edge_segment
from core.schema.validation import validate_thermal_case_payload


class CaseContractError(ValueError):
    """Raised when a validated case violates runtime layout contracts."""


def assert_case_geometry_contracts(case: Any) -> None:
    payload = _coerce_case_payload(case)
    validate_thermal_case_payload(payload)
    panel_domain = payload["panel_domain"]
    materials = payload["materials"]
    component_ids: set[str] = set()
    for component in payload["components"]:
        component_id = component["component_id"]
        if component_id in component_ids:
            raise CaseContractError(f"Duplicate component_id detected: {component_id}.")
        component_ids.add(component_id)
        if component["material_ref"] not in materials:
            raise CaseContractError(f"Component {component_id} references unknown material {component['material_ref']}.")
        if not component_within_domain(component, panel_domain):
            raise CaseContractError(f"Component {component_id} lies outside panel_domain.")
    for component_a, component_b in combinations(payload["components"], 2):
        if components_overlap(component_a, component_b):
            raise CaseContractError(
                f"Components {component_a['component_id']} and {component_b['component_id']} overlap."
            )
    for feature in payload["boundary_features"]:
        if not validate_line_sink_edge_segment(feature):
            raise CaseContractError(f"line_sink feature {feature['feature_id']} is not a valid edge segment.")
    for load in payload["loads"]:
        target_component_id = load.get("target_component_id")
        if target_component_id is not None and target_component_id not in component_ids:
            raise CaseContractError(f"Load targets unknown component {target_component_id}.")


def _coerce_case_payload(case: Any) -> dict[str, Any]:
    if hasattr(case, "to_dict"):
        return case.to_dict()
    if isinstance(case, Mapping):
        return dict(case)
    raise TypeError(f"Unsupported case payload type: {type(case)!r}")
