"""Lightweight constrained sampler for LLM semantic/operator priors."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from optimizers.operator_pool.semantic_tasks import semantic_task_for_operator
from optimizers.operator_pool.state import ControllerState


@dataclass(frozen=True, slots=True)
class OperatorPriorInput:
    operator_id: str
    prior: float
    risk: float = 0.5
    confidence: float = 0.5
    rationale: str = ""


@dataclass(frozen=True, slots=True)
class SemanticTaskPriorInput:
    semantic_task: str
    prior: float
    risk: float = 0.5
    confidence: float = 0.5


@dataclass(frozen=True, slots=True)
class SemanticPriorSamplerConfig:
    uniform_mix: float = 0.15
    min_probability_floor: float = 0.03
    generation_operator_cap_fraction: float = 0.35
    rolling_operator_cap_fraction: float = 0.40
    rolling_semantic_task_cap_fraction: float = 0.55
    rolling_window: int = 16
    risk_penalty_weight: float = 0.50

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any] | None) -> "SemanticPriorSamplerConfig":
        data = {} if payload is None else dict(payload)
        defaults = cls()
        return cls(
            uniform_mix=_clamp_unit(data.get("uniform_mix", defaults.uniform_mix)),
            min_probability_floor=_clamp_unit(data.get("min_probability_floor", defaults.min_probability_floor)),
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
            risk_penalty_weight=_clamp_unit(data.get("risk_penalty_weight", defaults.risk_penalty_weight)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "uniform_mix": float(self.uniform_mix),
            "min_probability_floor": float(self.min_probability_floor),
            "generation_operator_cap_fraction": float(self.generation_operator_cap_fraction),
            "rolling_operator_cap_fraction": float(self.rolling_operator_cap_fraction),
            "rolling_semantic_task_cap_fraction": float(self.rolling_semantic_task_cap_fraction),
            "rolling_window": int(self.rolling_window),
            "risk_penalty_weight": float(self.risk_penalty_weight),
        }


@dataclass(frozen=True, slots=True)
class SemanticPriorSamplerResult:
    selected_operator_id: str
    selected_probability: float
    sampler_probabilities: dict[str, float]
    normalized_operator_priors: dict[str, float]
    adjusted_operator_weights: dict[str, float]
    suppressed_operator_ids: tuple[str, ...]
    cap_reasons: dict[str, str]
    config: dict[str, Any]


def sample_operator_from_semantic_priors(
    *,
    candidate_operator_ids: Sequence[str],
    operator_priors: Sequence[OperatorPriorInput],
    semantic_task_priors: Sequence[SemanticTaskPriorInput],
    state: ControllerState,
    config: SemanticPriorSamplerConfig,
    rng: np.random.Generator,
) -> SemanticPriorSamplerResult:
    candidates = tuple(str(operator_id) for operator_id in candidate_operator_ids)
    if not candidates:
        raise ValueError("Semantic prior sampler requires at least one candidate operator.")
    normalized_priors = _operator_prior_distribution(candidates, operator_priors)
    if not any(value > 0.0 for value in normalized_priors.values()):
        normalized_priors = _semantic_task_prior_distribution(candidates, semantic_task_priors)
    if not any(value > 0.0 for value in normalized_priors.values()):
        normalized_priors = {operator_id: 1.0 / float(len(candidates)) for operator_id in candidates}

    risk_by_operator = {
        str(prior.operator_id): _clamp_unit(prior.risk)
        for prior in operator_priors
        if str(prior.operator_id) in candidates
    }
    adjusted_weights = {
        operator_id: float(prior)
        * max(0.0, 1.0 - float(config.risk_penalty_weight) * float(risk_by_operator.get(operator_id, 0.5)))
        for operator_id, prior in normalized_priors.items()
    }
    adjusted_probabilities = _normalize_distribution(adjusted_weights, candidates)
    uniform_probability = 1.0 / float(len(candidates))
    mixed_probabilities = {
        operator_id: (1.0 - float(config.uniform_mix)) * adjusted_probabilities[operator_id]
        + float(config.uniform_mix) * uniform_probability
        for operator_id in candidates
    }

    suppressed, cap_reasons = _suppressed_by_caps(candidates, state, config)
    active_candidates = [operator_id for operator_id in candidates if operator_id not in suppressed]
    if not active_candidates:
        suppressed = set()
        cap_reasons = {}
        active_candidates = list(candidates)

    capped_probabilities = {
        operator_id: (0.0 if operator_id in suppressed else mixed_probabilities[operator_id])
        for operator_id in candidates
    }
    floored_probabilities = _apply_probability_floor(
        capped_probabilities,
        active_candidates,
        floor=float(config.min_probability_floor),
    )
    probabilities = _normalize_distribution(floored_probabilities, candidates)
    selected_operator_id = str(rng.choice(list(candidates), p=[probabilities[operator_id] for operator_id in candidates]))
    return SemanticPriorSamplerResult(
        selected_operator_id=selected_operator_id,
        selected_probability=float(probabilities[selected_operator_id]),
        sampler_probabilities={operator_id: float(probabilities[operator_id]) for operator_id in candidates},
        normalized_operator_priors={
            operator_id: float(normalized_priors.get(operator_id, 0.0)) for operator_id in candidates
        },
        adjusted_operator_weights={
            operator_id: float(adjusted_weights.get(operator_id, 0.0)) for operator_id in candidates
        },
        suppressed_operator_ids=tuple(operator_id for operator_id in candidates if operator_id in suppressed),
        cap_reasons={str(operator_id): str(reason) for operator_id, reason in cap_reasons.items()},
        config=config.to_dict(),
    )


def _operator_prior_distribution(
    candidates: tuple[str, ...],
    operator_priors: Sequence[OperatorPriorInput],
) -> dict[str, float]:
    weights = {operator_id: 0.0 for operator_id in candidates}
    for prior in operator_priors:
        operator_id = str(prior.operator_id)
        if operator_id in weights:
            weights[operator_id] = max(weights[operator_id], _clamp_unit(prior.prior))
    if not any(value > 0.0 for value in weights.values()):
        return weights
    return _normalize_distribution(weights, candidates)


def _semantic_task_prior_distribution(
    candidates: tuple[str, ...],
    semantic_task_priors: Sequence[SemanticTaskPriorInput],
) -> dict[str, float]:
    task_weights: dict[str, float] = {}
    for prior in semantic_task_priors:
        task_id = str(prior.semantic_task).strip()
        if task_id:
            task_weights[task_id] = max(task_weights.get(task_id, 0.0), _clamp_unit(prior.prior))
    operator_weights = {operator_id: 0.0 for operator_id in candidates}
    for task_id, task_weight in task_weights.items():
        task_candidates = [operator_id for operator_id in candidates if semantic_task_for_operator(operator_id) == task_id]
        if not task_candidates:
            continue
        share = float(task_weight) / float(len(task_candidates))
        for operator_id in task_candidates:
            operator_weights[operator_id] += share
    if not any(value > 0.0 for value in operator_weights.values()):
        return operator_weights
    return _normalize_distribution(operator_weights, candidates)


def _suppressed_by_caps(
    candidates: tuple[str, ...],
    state: ControllerState,
    config: SemanticPriorSamplerConfig,
) -> tuple[set[str], dict[str, str]]:
    suppressed: set[str] = set()
    reasons: dict[str, str] = {}
    _apply_generation_cap(candidates, state, config, suppressed, reasons)
    _apply_rolling_operator_cap(candidates, state, config, suppressed, reasons)
    _apply_rolling_semantic_task_cap(candidates, state, config, suppressed, reasons)
    return suppressed, reasons


def _apply_generation_cap(
    candidates: tuple[str, ...],
    state: ControllerState,
    config: SemanticPriorSamplerConfig,
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
    config: SemanticPriorSamplerConfig,
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
            reasons[operator_id] = "rolling_operator_cap"


def _apply_rolling_semantic_task_cap(
    candidates: tuple[str, ...],
    state: ControllerState,
    config: SemanticPriorSamplerConfig,
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


def _apply_probability_floor(
    probabilities: Mapping[str, float],
    active_candidates: Sequence[str],
    *,
    floor: float,
) -> dict[str, float]:
    active = tuple(str(operator_id) for operator_id in active_candidates)
    if not active:
        return {str(operator_id): float(value) for operator_id, value in probabilities.items()}
    floor_value = min(max(float(floor), 0.0), 1.0 / float(len(active)))
    floor_total = floor_value * float(len(active))
    remaining_mass = max(0.0, 1.0 - floor_total)
    active_sum = sum(max(float(probabilities.get(operator_id, 0.0)), 0.0) for operator_id in active)
    result = {str(operator_id): 0.0 for operator_id in probabilities}
    for operator_id in active:
        normalized = (
            1.0 / float(len(active))
            if active_sum <= 0.0
            else max(float(probabilities.get(operator_id, 0.0)), 0.0) / active_sum
        )
        result[operator_id] = floor_value + remaining_mass * normalized
    return result


def _normalize_distribution(weights: Mapping[str, float], candidates: tuple[str, ...]) -> dict[str, float]:
    cleaned = {operator_id: max(float(weights.get(operator_id, 0.0)), 0.0) for operator_id in candidates}
    total = sum(cleaned.values())
    if total <= 0.0:
        return {operator_id: 1.0 / float(len(candidates)) for operator_id in candidates}
    return {operator_id: float(value) / float(total) for operator_id, value in cleaned.items()}


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
