"""High-level scenario-template to thermal-case pipeline."""

from __future__ import annotations

from pathlib import Path

from core.contracts.case_contracts import assert_case_geometry_contracts
from core.generator.case_builder import build_thermal_case
from core.generator.feature_synthesizer import synthesize_boundary_features
from core.generator.layout_engine import place_components
from core.generator.layout_metrics import build_layout_context, measure_case_layout_metrics
from core.generator.parameter_sampler import sample_template_parameters
from core.generator.template_loader import load_template_model
from core.schema.models import ThermalCase


def generate_case(template_path: str | Path, seed: int) -> ThermalCase:
    template = load_template_model(template_path)
    sampled_payload = sample_template_parameters(template, seed=seed)
    placed_components = place_components(template=template, sampled_components=sampled_payload["components"], seed=seed)
    primary_region = (
        template.placement_regions[0]
        if template.placement_regions
        else {"x_min": 0.0, "x_max": float(template.panel_domain["width"]), "y_min": 0.0, "y_max": float(template.panel_domain["height"])}
    )
    layout_strategy = template.generation_rules.get("layout_strategy", {})
    active_deck = None
    dense_core = None
    if isinstance(layout_strategy, dict):
        zones = layout_strategy.get("zones", {})
        if isinstance(zones, dict):
            active_deck = zones.get("active_deck")
            dense_core = zones.get("dense_core")
    layout_context = build_layout_context(
        placement_region=primary_region,
        active_deck=active_deck,
        dense_core=dense_core,
    )
    layout_metrics = measure_case_layout_metrics(
        {"components": placed_components},
        layout_context=layout_context,
    ) or {}
    boundary_features = synthesize_boundary_features(sampled_payload["boundary_features"])
    case = build_thermal_case(
        template=template,
        sampled_payload=sampled_payload,
        placed_components=placed_components,
        boundary_features=boundary_features,
        seed=seed,
        layout_metrics=layout_metrics,
    )
    case_payload = case.to_dict()
    case_payload.setdefault("provenance", {})["layout_context"] = layout_context
    case = ThermalCase.from_dict(case_payload)
    assert_case_geometry_contracts(case)
    return case
