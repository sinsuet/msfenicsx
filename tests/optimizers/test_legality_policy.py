from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from core.generator.pipeline import generate_case
from evaluation.io import load_spec
from optimizers.cheap_constraints import evaluate_cheap_constraints
from optimizers.codec import extract_decision_vector
from optimizers.io import load_optimization_spec
from optimizers.legality import apply_legality_policy_from_vector
from optimizers.models import OptimizationSpec
from optimizers.validation import OptimizationValidationError


RADIATOR_SPAN_MAX = 0.48


ACTIVE_SPECS = {
    "s1_raw": Path("scenarios/optimization/s1_typical_raw.yaml"),
    "s1_union": Path("scenarios/optimization/s1_typical_union.yaml"),
    "s1_llm": Path("scenarios/optimization/s1_typical_llm.yaml"),
    "s2_raw": Path("scenarios/optimization/s2_staged_raw.yaml"),
    "s2_union": Path("scenarios/optimization/s2_staged_union.yaml"),
    "s2_llm": Path("scenarios/optimization/s2_staged_llm.yaml"),
}


def test_active_specs_declare_legality_policy_ids() -> None:
    expected = {
        "s1_raw": "minimal_canonicalization",
        "s1_union": "minimal_canonicalization",
        "s1_llm": "projection_plus_local_restore",
        "s2_raw": "minimal_canonicalization",
        "s2_union": "minimal_canonicalization",
        "s2_llm": "projection_plus_local_restore",
    }
    for key, path in ACTIVE_SPECS.items():
        spec = load_optimization_spec(path).to_dict()
        assert spec["evaluation_protocol"]["legality_policy_id"] == expected[key]


def test_invalid_legality_policy_id_is_rejected() -> None:
    payload = load_optimization_spec(ACTIVE_SPECS["s1_raw"]).to_dict()
    payload["evaluation_protocol"]["legality_policy_id"] = "mystery_mode"

    with pytest.raises(OptimizationValidationError, match="legality_policy_id"):
        OptimizationSpec.from_dict(payload)


def test_missing_legality_policy_id_is_rejected() -> None:
    payload = load_optimization_spec(ACTIVE_SPECS["s1_raw"]).to_dict()
    del payload["evaluation_protocol"]["legality_policy_id"]

    with pytest.raises(OptimizationValidationError, match="legality_policy_id"):
        OptimizationSpec.from_dict(payload)


def _case():
    return generate_case("scenarios/templates/s1_typical.yaml", seed=11)


def _raw_spec():
    return load_optimization_spec("scenarios/optimization/s1_typical_raw.yaml")


def _evaluation_spec():
    return load_spec("scenarios/evaluation/s1_typical_eval.yaml")


def test_minimal_canonicalization_projects_sink_but_does_not_restore_overlap() -> None:
    case = _case()
    spec = _raw_spec()
    vector = extract_decision_vector(case, spec)
    vector[0] = 0.18
    vector[1] = 0.18
    vector[2] = 0.18
    vector[3] = 0.18
    vector[-2] = 0.90
    vector[-1] = 0.05

    evaluated = apply_legality_policy_from_vector(
        case,
        spec,
        np.asarray(vector, dtype=np.float64),
        legality_policy_id="minimal_canonicalization",
        radiator_span_max=RADIATOR_SPAN_MAX,
    )
    cheap_result = evaluate_cheap_constraints(evaluated.case_payload, _evaluation_spec())

    assert evaluated.legality_policy_id == "minimal_canonicalization"
    assert "sink_reorder" in evaluated.vector_transform_codes
    assert "sink_project" in evaluated.vector_transform_codes
    assert "local_restore" not in evaluated.vector_transform_codes
    assert evaluated.proposal_vector[0] == pytest.approx(0.18)
    assert evaluated.evaluated_vector[0] == pytest.approx(0.18)
    assert any("clearance_violation" in issue for issue in cheap_result.geometry_issues)


def test_projection_plus_local_restore_matches_existing_repair_contract() -> None:
    case = _case()
    spec = _raw_spec()
    vector = extract_decision_vector(case, spec)
    for component_index in range(4):
        vector[component_index * 2] = 0.18
        vector[component_index * 2 + 1] = 0.18
    vector[-2] = 0.05
    vector[-1] = 0.95

    evaluated = apply_legality_policy_from_vector(
        case,
        spec,
        np.asarray(vector, dtype=np.float64),
        legality_policy_id="projection_plus_local_restore",
        radiator_span_max=RADIATOR_SPAN_MAX,
    )

    assert evaluated.legality_policy_id == "projection_plus_local_restore"
    assert evaluated.evaluated_vector[-1] - evaluated.evaluated_vector[-2] <= 0.48 + 1.0e-6
    assert evaluated.evaluated_vector[0] != pytest.approx(0.18)
    assert "local_restore" in evaluated.vector_transform_codes
    assert "bound_clip" not in evaluated.vector_transform_codes
