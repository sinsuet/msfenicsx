"""High-level scenario-template to thermal-case pipeline."""

from __future__ import annotations

from pathlib import Path

from core.contracts.case_contracts import assert_case_geometry_contracts
from core.generator.case_builder import build_thermal_case
from core.generator.feature_synthesizer import synthesize_boundary_features
from core.generator.layout_engine import place_components
from core.generator.parameter_sampler import sample_template_parameters
from core.generator.template_loader import load_template_model
from core.schema.models import ThermalCase


def generate_case(template_path: str | Path, seed: int) -> ThermalCase:
    template = load_template_model(template_path)
    if template.operating_case_profiles:
        raise ValueError(
            "Templates with non-empty operating_case_profiles are not supported on generate-case; "
            "the retired generate-operating-case-pair path is no longer available."
        )
    sampled_payload = sample_template_parameters(template, seed=seed)
    placed_components = place_components(template=template, sampled_components=sampled_payload["components"], seed=seed)
    boundary_features = synthesize_boundary_features(sampled_payload["boundary_features"])
    case = build_thermal_case(
        template=template,
        sampled_payload=sampled_payload,
        placed_components=placed_components,
        boundary_features=boundary_features,
        seed=seed,
    )
    assert_case_geometry_contracts(case)
    return case
