from pathlib import Path

import pytest

import optimizers.parallel_evaluator as parallel_module
from evaluation.io import load_spec
from optimizers.io import generate_benchmark_case, load_optimization_spec


SPEC_PATH = Path("scenarios/optimization/s1_typical_raw.yaml")
EVALUATION_SPEC_PATH = Path("scenarios/evaluation/s1_typical_eval.yaml")


def _candidate_payload_and_spec() -> tuple[dict, dict]:
    optimization_spec = load_optimization_spec(SPEC_PATH)
    evaluation_spec = load_spec(EVALUATION_SPEC_PATH)
    base_case = generate_benchmark_case(SPEC_PATH, optimization_spec)
    return base_case.to_dict(), evaluation_spec.to_dict()


def test_evaluate_candidate_payload_returns_success_payload() -> None:
    candidate_payload, evaluation_spec = _candidate_payload_and_spec()

    result = parallel_module.evaluate_candidate_payload(candidate_payload, evaluation_spec)

    assert result["success"] is True
    assert result["case_payload"]["case_meta"]["case_id"] == candidate_payload["case_meta"]["case_id"]
    assert result["evaluation_payload"]["evaluation_meta"]["case_id"] == candidate_payload["case_meta"]["case_id"]
    assert result["objective_values"]
    assert result["constraint_values"]
    assert "field_exports" in result


def test_evaluate_candidate_payload_returns_structured_failure_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate_payload, evaluation_spec = _candidate_payload_and_spec()

    def _fail(_case):
        raise RuntimeError("solver exploded")

    monkeypatch.setattr(parallel_module, "solve_case_artifacts", _fail)

    result = parallel_module.evaluate_candidate_payload(candidate_payload, evaluation_spec)

    assert result["success"] is False
    assert "RuntimeError: solver exploded" in result["failure_reason"]

