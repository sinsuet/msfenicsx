from __future__ import annotations

import numpy as np
import pytest

from optimizers.operator_pool.semantic_prior_sampler import (
    OperatorPriorInput,
    SemanticPriorSamplerConfig,
    SemanticTaskPriorInput,
    sample_operator_from_semantic_priors,
)
from optimizers.operator_pool.state import ControllerState


def _state(
    *,
    recent_decisions: list[dict[str, object]] | None = None,
    generation_operator_counts: dict[str, int] | None = None,
    target_offsprings: int = 20,
) -> ControllerState:
    operator_counts = {
        operator_id: {"accepted_count": count}
        for operator_id, count in (generation_operator_counts or {}).items()
    }
    accepted_count = sum(generation_operator_counts.values()) if generation_operator_counts else 0
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=6,
        evaluation_index=120,
        parent_count=2,
        vector_size=32,
        metadata={
            "recent_decisions": recent_decisions or [],
            "generation_local_memory": {
                "accepted_count": accepted_count,
                "target_offsprings": target_offsprings,
                "operator_counts": operator_counts,
            },
        },
    )


def test_sampler_blends_llm_prior_with_uniform_floor() -> None:
    result = sample_operator_from_semantic_priors(
        candidate_operator_ids=("sink_shift", "component_jitter_1", "component_relocate_1"),
        operator_priors=(
            OperatorPriorInput("sink_shift", prior=1.0, risk=0.0, confidence=0.9),
        ),
        semantic_task_priors=(),
        state=_state(),
        config=SemanticPriorSamplerConfig(uniform_mix=0.15, min_probability_floor=0.03),
        rng=np.random.default_rng(4),
    )

    probabilities = result.sampler_probabilities
    assert set(probabilities) == {"sink_shift", "component_jitter_1", "component_relocate_1"}
    assert probabilities["sink_shift"] > probabilities["component_jitter_1"]
    assert probabilities["component_jitter_1"] >= 0.03
    assert sum(probabilities.values()) == pytest.approx(1.0)
    assert result.selected_operator_id in probabilities


def test_sampler_applies_risk_penalty_before_sampling() -> None:
    result = sample_operator_from_semantic_priors(
        candidate_operator_ids=("sink_shift", "component_jitter_1"),
        operator_priors=(
            OperatorPriorInput("sink_shift", prior=0.8, risk=1.0, confidence=0.9),
            OperatorPriorInput("component_jitter_1", prior=0.2, risk=0.0, confidence=0.9),
        ),
        semantic_task_priors=(),
        state=_state(),
        config=SemanticPriorSamplerConfig(
            uniform_mix=0.0,
            min_probability_floor=0.0,
            risk_penalty_weight=0.75,
        ),
        rng=np.random.default_rng(2),
    )

    assert result.normalized_operator_priors["sink_shift"] == pytest.approx(0.8)
    assert result.adjusted_operator_weights["sink_shift"] == pytest.approx(0.2)
    assert result.sampler_probabilities["sink_shift"] == pytest.approx(0.5)
    assert result.sampler_probabilities["component_jitter_1"] == pytest.approx(0.5)


def test_sampler_suppresses_generation_cap_when_alternative_exists() -> None:
    result = sample_operator_from_semantic_priors(
        candidate_operator_ids=("component_subspace_sbx", "component_jitter_1", "sink_resize"),
        operator_priors=(
            OperatorPriorInput("component_subspace_sbx", prior=0.9, risk=0.0, confidence=0.9),
            OperatorPriorInput("component_jitter_1", prior=0.1, risk=0.0, confidence=0.5),
        ),
        semantic_task_priors=(),
        state=_state(
            generation_operator_counts={"component_subspace_sbx": 7},
            target_offsprings=20,
        ),
        config=SemanticPriorSamplerConfig(
            uniform_mix=0.0,
            min_probability_floor=0.03,
            generation_operator_cap_fraction=0.35,
        ),
        rng=np.random.default_rng(9),
    )

    assert "component_subspace_sbx" in result.suppressed_operator_ids
    assert result.sampler_probabilities["component_subspace_sbx"] == 0.0
    assert sum(result.sampler_probabilities.values()) == pytest.approx(1.0)


def test_sampler_suppresses_rolling_semantic_task_cap() -> None:
    recent_decisions = [
        {"selected_operator_id": "sink_shift", "llm_valid": True}
        for _ in range(10)
    ] + [
        {"selected_operator_id": "component_jitter_1", "llm_valid": True}
        for _ in range(6)
    ]
    result = sample_operator_from_semantic_priors(
        candidate_operator_ids=("sink_shift", "sink_resize", "component_jitter_1"),
        operator_priors=(
            OperatorPriorInput("sink_shift", prior=0.5, risk=0.0, confidence=0.9),
            OperatorPriorInput("sink_resize", prior=0.3, risk=0.0, confidence=0.8),
            OperatorPriorInput("component_jitter_1", prior=0.2, risk=0.0, confidence=0.7),
        ),
        semantic_task_priors=(),
        state=_state(recent_decisions=recent_decisions),
        config=SemanticPriorSamplerConfig(
            uniform_mix=0.0,
            min_probability_floor=0.0,
            rolling_window=16,
            rolling_semantic_task_cap_fraction=0.55,
        ),
        rng=np.random.default_rng(11),
    )

    assert "sink_shift" in result.suppressed_operator_ids
    assert result.sampler_probabilities["sink_shift"] == 0.0
    assert result.sampler_probabilities["component_jitter_1"] > 0.0


def test_sampler_expands_semantic_task_priors_when_operator_priors_are_empty() -> None:
    result = sample_operator_from_semantic_priors(
        candidate_operator_ids=("component_jitter_1", "anchored_component_jitter", "sink_shift"),
        operator_priors=(),
        semantic_task_priors=(
            SemanticTaskPriorInput("local_polish", prior=1.0, risk=0.1, confidence=0.8),
        ),
        state=_state(),
        config=SemanticPriorSamplerConfig(uniform_mix=0.0, min_probability_floor=0.0),
        rng=np.random.default_rng(5),
    )

    assert result.sampler_probabilities["component_jitter_1"] == pytest.approx(0.5)
    assert result.sampler_probabilities["anchored_component_jitter"] == pytest.approx(0.5)
    assert result.sampler_probabilities["sink_shift"] == pytest.approx(0.0)
