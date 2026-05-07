"""Deterministic constrained picker for LLM semantic operator rankings."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from optimizers.operator_pool.semantic_tasks import semantic_task_for_operator
from optimizers.operator_pool.state import ControllerState


@dataclass(frozen=True, slots=True)
class RankedOperatorInput:
    operator_id: str
    semantic_task: str
    score: float
    risk: float
    confidence: float
    rationale: str = ""


@dataclass(frozen=True, slots=True)
class SemanticRankedPickConfig:
    max_rank_scan: int = 9
    generation_operator_cap_fraction: float = 0.35
    rolling_operator_cap_fraction: float = 0.40
    rolling_semantic_task_cap_fraction: float = 0.55
    rolling_window: int = 16
    near_tie_score_margin: float = 0.03
    low_confidence_threshold: float = 0.35

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any] | None) -> "SemanticRankedPickConfig":
        data = {} if payload is None else dict(payload)
        defaults = cls()
        return cls(
            max_rank_scan=max(1, int(data.get("max_rank_scan", defaults.max_rank_scan))),
            generation_operator_cap_fraction=_clamp_unit(
                data.get("generation_operator_cap_fraction", defaults.generation_operator_cap_fraction)
            ),
            rolling_operator_cap_fraction=_clamp_unit(
                data.get("rolling_operator_cap_fraction", defaults.rolling_operator_cap_fraction)
            ),
            rolling_semantic_task_cap_fraction=_clamp_unit(
                data.get("rolling_semantic_task_cap_fraction", defaults.rolling_semantic_task_cap_fraction)
            ),
            rolling_window=max(1, int(data.get("rolling_window", defaults.rolling_window))),
            near_tie_score_margin=_clamp_unit(data.get("near_tie_score_margin", defaults.near_tie_score_margin)),
            low_confidence_threshold=_clamp_unit(
                data.get("low_confidence_threshold", defaults.low_confidence_threshold)
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_rank_scan": int(self.max_rank_scan),
            "generation_operator_cap_fraction": float(self.generation_operator_cap_fraction),
            "rolling_operator_cap_fraction": float(self.rolling_operator_cap_fraction),
            "rolling_semantic_task_cap_fraction": float(self.rolling_semantic_task_cap_fraction),
            "rolling_window": int(self.rolling_window),
            "near_tie_score_margin": float(self.near_tie_score_margin),
            "low_confidence_threshold": float(self.low_confidence_threshold),
        }


@dataclass(frozen=True, slots=True)
class SemanticRankedPickResult:
    selected_operator_id: str
    selected_rank: int
    ranked_operator_rows: tuple[dict[str, Any], ...]
    suppressed_operator_ids: tuple[str, ...]
    cap_reasons: dict[str, str]
    override_reason: str
    missing_operator_ids: tuple[str, ...]
    config: dict[str, Any]


def pick_operator_from_semantic_ranking(
    *,
    candidate_operator_ids: Sequence[str],
    ranked_operators: Sequence[RankedOperatorInput],
    state: ControllerState,
    config: SemanticRankedPickConfig,
) -> SemanticRankedPickResult:
    candidates = tuple(str(operator_id) for operator_id in candidate_operator_ids)
    if not candidates:
        raise ValueError("Semantic ranked picker requires at least one candidate operator.")
    ranked_rows, missing_operator_ids = _complete_ranking(candidates, ranked_operators)
    suppressed, cap_reasons = _suppressed_by_caps(candidates, state, config)
    scanned_rows = ranked_rows[: min(len(ranked_rows), int(config.max_rank_scan))]
    active_rows = [row for row in scanned_rows if row["operator_id"] not in suppressed]
    if not active_rows:
        selected_row = scanned_rows[0]
        override_reason = "all_candidates_suppressed_release"
    else:
        selected_row = _select_with_near_tie_policy(active_rows, config)
        if selected_row["rank"] == 1 and not _near_tie_triggered(active_rows, config):
            override_reason = ""
        elif selected_row["rank"] != active_rows[0]["rank"]:
            override_reason = "low_confidence_near_tie_lower_risk"
        elif scanned_rows[0]["operator_id"] in suppressed:
            override_reason = "rank_1_suppressed"
        else:
            override_reason = ""
    return SemanticRankedPickResult(
        selected_operator_id=str(selected_row["operator_id"]),
        selected_rank=int(selected_row["rank"]),
        ranked_operator_rows=tuple(dict(row) for row in ranked_rows),
        suppressed_operator_ids=tuple(operator_id for operator_id in candidates if operator_id in suppressed),
        cap_reasons={str(operator_id): str(reason) for operator_id, reason in cap_reasons.items()},
        override_reason=override_reason,
        missing_operator_ids=tuple(missing_operator_ids),
        config=config.to_dict(),
    )


def _complete_ranking(
    candidates: tuple[str, ...],
    ranked_operators: Sequence[RankedOperatorInput],
) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ranked in ranked_operators:
        operator_id = str(ranked.operator_id)
        if operator_id not in candidates or operator_id in seen:
            continue
        seen.add(operator_id)
        rows.append(
            {
                "rank": len(rows) + 1,
                "operator_id": operator_id,
                "semantic_task": str(ranked.semantic_task),
                "canonical_semantic_task": semantic_task_for_operator(operator_id),
                "score": _require_unit_number(ranked.score, field_name="score", operator_id=operator_id),
                "risk": _require_unit_number(ranked.risk, field_name="risk", operator_id=operator_id),
                "confidence": _require_unit_number(
                    ranked.confidence,
                    field_name="confidence",
                    operator_id=operator_id,
                ),
                "rationale": str(ranked.rationale),
                "rank_source": "llm",
            }
        )
    missing = tuple(operator_id for operator_id in candidates if operator_id not in seen)
    for operator_id in missing:
        rows.append(
            {
                "rank": len(rows) + 1,
                "operator_id": operator_id,
                "semantic_task": semantic_task_for_operator(operator_id),
                "canonical_semantic_task": semantic_task_for_operator(operator_id),
                "score": 0.0,
                "risk": 1.0,
                "confidence": 0.0,
                "rationale": "not ranked by model",
                "rank_source": "missing_tail",
            }
        )
    return rows, missing


def _select_with_near_tie_policy(
    active_rows: list[dict[str, Any]],
    config: SemanticRankedPickConfig,
) -> dict[str, Any]:
    top = active_rows[0]
    tie_rows = [top]
    for row in active_rows[1:]:
        if float(top["score"]) - float(row["score"]) <= float(config.near_tie_score_margin):
            tie_rows.append(row)
        else:
            break
    if len(tie_rows) <= 1 and float(top["confidence"]) >= float(config.low_confidence_threshold):
        return top
    if float(top["confidence"]) < float(config.low_confidence_threshold) and len(active_rows) > 1:
        tie_rows = active_rows[: min(len(active_rows), 2)]
    return sorted(tie_rows, key=lambda row: (float(row["risk"]), -float(row["confidence"]), int(row["rank"])))[0]


def _near_tie_triggered(active_rows: list[dict[str, Any]], config: SemanticRankedPickConfig) -> bool:
    if not active_rows:
        return False
    if float(active_rows[0]["confidence"]) < float(config.low_confidence_threshold):
        return True
    if len(active_rows) < 2:
        return False
    return float(active_rows[0]["score"]) - float(active_rows[1]["score"]) <= float(config.near_tie_score_margin)


def _suppressed_by_caps(
    candidates: tuple[str, ...],
    state: ControllerState,
    config: SemanticRankedPickConfig,
) -> tuple[set[str], dict[str, str]]:
    suppressed: set[str] = set()
    reasons: dict[str, str] = {}
    _apply_generation_cap(candidates, state, config, suppressed, reasons)
    _apply_rolling_semantic_task_cap(candidates, state, config, suppressed, reasons)
    _apply_rolling_operator_cap(candidates, state, config, suppressed, reasons)
    return suppressed, reasons


def _apply_generation_cap(
    candidates: tuple[str, ...],
    state: ControllerState,
    config: SemanticRankedPickConfig,
    suppressed: set[str],
    reasons: dict[str, str],
) -> None:
    memory = state.metadata.get("generation_local_memory")
    if not isinstance(memory, Mapping):
        return
    target = int(memory.get("target_offsprings") or 0)
    if target <= 0:
        return
    cap_count = max(1, int(math.ceil(float(target) * float(config.generation_operator_cap_fraction))))
    operator_counts = memory.get("operator_counts")
    if not isinstance(operator_counts, Mapping):
        return
    for operator_id in candidates:
        summary = operator_counts.get(operator_id)
        accepted_count = int(dict(summary).get("accepted_count", 0)) if isinstance(summary, Mapping) else 0
        if accepted_count >= cap_count:
            suppressed.add(operator_id)
            reasons[operator_id] = "generation_operator_cap"


def _apply_rolling_operator_cap(
    candidates: tuple[str, ...],
    state: ControllerState,
    config: SemanticRankedPickConfig,
    suppressed: set[str],
    reasons: dict[str, str],
) -> None:
    recent = _recent_operator_sequence(state, candidates, int(config.rolling_window))
    if not recent:
        return
    counter = Counter(recent)
    total = float(len(recent))
    for operator_id, count in counter.items():
        if float(count) / total >= float(config.rolling_operator_cap_fraction):
            suppressed.add(operator_id)
            reasons.setdefault(operator_id, "rolling_operator_cap")


def _apply_rolling_semantic_task_cap(
    candidates: tuple[str, ...],
    state: ControllerState,
    config: SemanticRankedPickConfig,
    suppressed: set[str],
    reasons: dict[str, str],
) -> None:
    recent = _recent_operator_sequence(state, candidates, int(config.rolling_window))
    if not recent:
        return
    task_counter = Counter(semantic_task_for_operator(operator_id) for operator_id in recent)
    total = float(len(recent))
    capped_tasks = {
        task_id
        for task_id, count in task_counter.items()
        if float(count) / total >= float(config.rolling_semantic_task_cap_fraction)
    }
    for operator_id in candidates:
        if semantic_task_for_operator(operator_id) in capped_tasks:
            suppressed.add(operator_id)
            reasons.setdefault(operator_id, "rolling_semantic_task_cap")


def _recent_operator_sequence(
    state: ControllerState,
    candidates: tuple[str, ...],
    rolling_window: int,
) -> tuple[str, ...]:
    recent_decisions = state.metadata.get("recent_decisions", [])
    sequence: list[str] = []
    for row in recent_decisions:
        if not isinstance(row, Mapping):
            continue
        operator_id = str(row.get("selected_operator_id", "")).strip()
        if operator_id not in candidates:
            continue
        if row.get("fallback_used") is True:
            continue
        sequence.append(operator_id)
    return tuple(sequence[-max(1, int(rolling_window)):])


def _clamp_unit(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0.0
    if numeric < 0.0:
        return 0.0
    if numeric > 1.0:
        return 1.0
    return float(numeric)


def _require_unit_number(value: Any, *, field_name: str, operator_id: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"ranked operator {operator_id!r} field {field_name!r} must be a number between "
            f"0.0 and 1.0; got {value!r}."
        )
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0.0 or numeric > 1.0:
        raise ValueError(
            f"ranked operator {operator_id!r} field {field_name!r} must be between 0.0 and 1.0; "
            f"got {value!r}."
        )
    return numeric
