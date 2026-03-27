"""Generate paired operating-case thermal cases from one sampled layout."""

from __future__ import annotations

from pathlib import Path

from core.contracts.case_contracts import assert_case_geometry_contracts
from core.generator.feature_synthesizer import synthesize_boundary_features
from core.generator.layout_engine import place_components
from core.generator.operating_case_builder import build_operating_case
from core.generator.parameter_sampler import sample_template_parameters
from core.generator.template_loader import load_template_model
from core.schema.models import ThermalCase


def generate_operating_case_pair(template_path: str | Path, seed: int) -> dict[str, ThermalCase]:
    template = load_template_model(template_path)
    sampled_payload = sample_template_parameters(template, seed=seed)
    placed_components = place_components(template=template, sampled_components=sampled_payload["components"], seed=seed)
    boundary_features = synthesize_boundary_features(sampled_payload["boundary_features"])
    cases = {
        operating_case_profile["operating_case_id"]: build_operating_case(
            template=template,
            sampled_payload=sampled_payload,
            placed_components=placed_components,
            boundary_features=boundary_features,
            operating_case_profile=operating_case_profile,
            seed=seed,
        )
        for operating_case_profile in template.operating_case_profiles
    }
    for case in cases.values():
        assert_case_geometry_contracts(case)
    return cases
