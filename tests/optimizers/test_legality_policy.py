from __future__ import annotations

from pathlib import Path

import pytest

from optimizers.io import load_optimization_spec
from optimizers.models import OptimizationSpec
from optimizers.validation import OptimizationValidationError


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
