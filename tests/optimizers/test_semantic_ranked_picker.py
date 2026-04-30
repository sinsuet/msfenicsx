from __future__ import annotations

import pytest

from optimizers.operator_pool.semantic_ranked_picker import (
    RankedOperatorInput,
    SemanticRankedPickConfig,
    pick_operator_from_semantic_ranking,
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


def test_ranked_picker_selects_top_rank_without_caps() -> None:
    result = pick_operator_from_semantic_ranking(
        candidate_operator_ids=("sink_shift", "component_jitter_1"),
        ranked_operators=(
            RankedOperatorInput(
                "sink_shift",
                "sink_alignment",
                score=0.82,
                risk=0.22,
                confidence=0.74,
                rationale="align",
            ),
            RankedOperatorInput(
                "component_jitter_1",
                "local_polish",
                score=0.71,
                risk=0.18,
                confidence=0.61,
                rationale="local",
            ),
        ),
        state=_state(),
        config=SemanticRankedPickConfig(),
    )

    assert result.selected_operator_id == "sink_shift"
    assert result.selected_rank == 1
    assert result.override_reason == ""
    assert result.suppressed_operator_ids == ()


def test_ranked_picker_skips_generation_capped_top_rank() -> None:
    result = pick_operator_from_semantic_ranking(
        candidate_operator_ids=("sink_shift", "component_jitter_1"),
        ranked_operators=(
            RankedOperatorInput(
                "sink_shift",
                "sink_alignment",
                score=0.82,
                risk=0.22,
                confidence=0.74,
                rationale="align",
            ),
            RankedOperatorInput(
                "component_jitter_1",
                "local_polish",
                score=0.71,
                risk=0.18,
                confidence=0.61,
                rationale="local",
            ),
        ),
        state=_state(generation_operator_counts={"sink_shift": 7}, target_offsprings=20),
        config=SemanticRankedPickConfig(generation_operator_cap_fraction=0.35),
    )

    assert result.selected_operator_id == "component_jitter_1"
    assert result.selected_rank == 2
    assert result.suppressed_operator_ids == ("sink_shift",)
    assert result.cap_reasons["sink_shift"] == "generation_operator_cap"
    assert result.override_reason == "rank_1_suppressed"


def test_ranked_picker_applies_rolling_semantic_task_cap() -> None:
    recent_decisions = [
        {"selected_operator_id": "sink_shift", "fallback_used": False}
        for _ in range(10)
    ] + [
        {"selected_operator_id": "component_jitter_1", "fallback_used": False}
        for _ in range(6)
    ]
    result = pick_operator_from_semantic_ranking(
        candidate_operator_ids=("sink_shift", "hotspot_pull_toward_sink", "component_jitter_1"),
        ranked_operators=(
            RankedOperatorInput(
                "sink_shift",
                "sink_alignment",
                score=0.90,
                risk=0.20,
                confidence=0.80,
                rationale="align",
            ),
            RankedOperatorInput(
                "hotspot_pull_toward_sink",
                "sink_alignment",
                score=0.85,
                risk=0.25,
                confidence=0.70,
                rationale="pull",
            ),
            RankedOperatorInput(
                "component_jitter_1",
                "local_polish",
                score=0.70,
                risk=0.15,
                confidence=0.60,
                rationale="local",
            ),
        ),
        state=_state(recent_decisions=recent_decisions),
        config=SemanticRankedPickConfig(rolling_window=16, rolling_semantic_task_cap_fraction=0.55),
    )

    assert result.selected_operator_id == "component_jitter_1"
    assert "sink_shift" in result.suppressed_operator_ids
    assert "hotspot_pull_toward_sink" in result.suppressed_operator_ids
    assert result.cap_reasons["sink_shift"] == "rolling_semantic_task_cap"


def test_ranked_picker_uses_lower_risk_for_low_confidence_near_tie() -> None:
    result = pick_operator_from_semantic_ranking(
        candidate_operator_ids=("sink_shift", "component_jitter_1"),
        ranked_operators=(
            RankedOperatorInput(
                "sink_shift",
                "sink_alignment",
                score=0.80,
                risk=0.70,
                confidence=0.30,
                rationale="uncertain",
            ),
            RankedOperatorInput(
                "component_jitter_1",
                "local_polish",
                score=0.79,
                risk=0.10,
                confidence=0.58,
                rationale="safer",
            ),
        ),
        state=_state(),
        config=SemanticRankedPickConfig(near_tie_score_margin=0.03, low_confidence_threshold=0.35),
    )

    assert result.selected_operator_id == "component_jitter_1"
    assert result.selected_rank == 2
    assert result.override_reason == "low_confidence_near_tie_lower_risk"


def test_ranked_picker_records_missing_candidates_and_appends_them_to_tail() -> None:
    result = pick_operator_from_semantic_ranking(
        candidate_operator_ids=("sink_shift", "component_jitter_1", "component_swap_2"),
        ranked_operators=(
            RankedOperatorInput(
                "sink_shift",
                "sink_alignment",
                score=0.80,
                risk=0.20,
                confidence=0.70,
                rationale="align",
            ),
        ),
        state=_state(generation_operator_counts={"sink_shift": 7}, target_offsprings=20),
        config=SemanticRankedPickConfig(generation_operator_cap_fraction=0.35),
    )

    assert result.selected_operator_id == "component_jitter_1"
    assert result.selected_rank == 2
    assert result.missing_operator_ids == ("component_jitter_1", "component_swap_2")


def test_ranked_picker_releases_caps_when_every_candidate_is_suppressed() -> None:
    result = pick_operator_from_semantic_ranking(
        candidate_operator_ids=("sink_shift", "component_jitter_1"),
        ranked_operators=(
            RankedOperatorInput(
                "sink_shift",
                "sink_alignment",
                score=0.80,
                risk=0.20,
                confidence=0.70,
                rationale="align",
            ),
            RankedOperatorInput(
                "component_jitter_1",
                "local_polish",
                score=0.70,
                risk=0.20,
                confidence=0.70,
                rationale="local",
            ),
        ),
        state=_state(
            generation_operator_counts={"sink_shift": 7, "component_jitter_1": 7},
            target_offsprings=20,
        ),
        config=SemanticRankedPickConfig(generation_operator_cap_fraction=0.35),
    )

    assert result.selected_operator_id == "sink_shift"
    assert result.selected_rank == 1
    assert result.override_reason == "all_candidates_suppressed_release"
    assert set(result.suppressed_operator_ids) == {"sink_shift", "component_jitter_1"}


def test_ranked_picker_rejects_invalid_rank_numeric_values() -> None:
    with pytest.raises(ValueError, match="score.*0.0.*1.0"):
        pick_operator_from_semantic_ranking(
            candidate_operator_ids=("sink_shift", "component_jitter_1"),
            ranked_operators=(
                RankedOperatorInput(
                    "sink_shift",
                    "sink_alignment",
                    score=9.2,
                    risk=0.2,
                    confidence=0.7,
                    rationale="bad score scale",
                ),
            ),
            state=_state(),
            config=SemanticRankedPickConfig(),
        )
