"""Helpers for building richer controller-facing state payloads."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from optimizers.operator_pool.domain_state import (
    build_archive_state,
    build_domain_regime,
    build_history_lookup,
    build_parent_state,
    build_prompt_parent_panel,
    build_prompt_regime_panel,
    build_prefeasible_reset_summary,
    build_progress_state,
    build_run_state,
)
from optimizers.operator_pool.models import ParentBundle
from optimizers.operator_pool.operators import get_operator_behavior_profile
from optimizers.operator_pool.reflection import summarize_operator_history
from optimizers.operator_pool.state import ControllerState
from optimizers.operator_pool.trace import ControllerTraceRow, OperatorTraceRow

_APPLICABILITY_LABELS = ("low", "medium", "high")
_FIT_SCORES = {
    "weak": 0,
    "supported": 1,
    "trusted": 2,
}
_OPERATOR_EFFECTS: dict[str, dict[str, str]] = {
    "native_sbx_pm": {
        "expected_peak_effect": "neutral",
        "expected_gradient_effect": "neutral",
    },
    "global_explore": {
        "expected_peak_effect": "neutral",
        "expected_gradient_effect": "neutral",
    },
    "local_refine": {
        "expected_peak_effect": "improve",
        "expected_gradient_effect": "neutral",
    },
    "move_hottest_cluster_toward_sink": {
        "expected_peak_effect": "improve",
        "expected_gradient_effect": "neutral",
    },
    "spread_hottest_cluster": {
        "expected_peak_effect": "neutral",
        "expected_gradient_effect": "improve",
    },
    "smooth_high_gradient_band": {
        "expected_peak_effect": "neutral",
        "expected_gradient_effect": "improve",
    },
    "reduce_local_congestion": {
        "expected_peak_effect": "neutral",
        "expected_gradient_effect": "improve",
    },
    "repair_sink_budget": {
        "expected_peak_effect": "improve",
        "expected_gradient_effect": "neutral",
    },
    "slide_sink": {
        "expected_peak_effect": "improve",
        "expected_gradient_effect": "neutral",
    },
    "rebalance_layout": {
        "expected_peak_effect": "neutral",
        "expected_gradient_effect": "improve",
    },
}


def _compact_recent_decision(
    row: ControllerTraceRow,
    *,
    generation_local: bool = False,
) -> dict[str, Any]:
    fallback_used = bool(row.metadata.get("fallback_used", False))
    return {
        "evaluation_index": int(row.evaluation_index),
        "selected_operator_id": row.selected_operator_id,
        "fallback_used": fallback_used,
        "llm_valid": row.controller_id == "llm" and not fallback_used,
        "generation_local": bool(generation_local),
    }


def _policy_recent_decision(row: ControllerTraceRow) -> dict[str, Any]:
    reason_codes = row.metadata.get("guardrail_reason_codes", [])
    if not isinstance(reason_codes, Sequence) or isinstance(reason_codes, (str, bytes)):
        reason_codes = [] if not reason_codes else [str(reason_codes)]
    return {
        "selected_operator_id": row.selected_operator_id,
        "policy_phase": str(row.metadata.get("policy_phase") or row.metadata.get("guardrail_policy_phase") or row.phase),
        "policy_reset_active": bool(row.metadata.get("guardrail_policy_reset_active", False)),
        "reason_codes": [str(code) for code in reason_codes],
    }


def _build_recent_operator_counts(operator_summary: dict[str, dict[str, Any]]) -> dict[str, dict[str, int]]:
    return {
        operator_id: {
            "recent_selection_count": int(summary.get("recent_selection_count", 0)),
            "recent_fallback_selection_count": int(summary.get("recent_fallback_selection_count", 0)),
            "recent_llm_valid_selection_count": int(summary.get("recent_llm_valid_selection_count", 0)),
        }
        for operator_id, summary in operator_summary.items()
        if int(summary.get("recent_selection_count", 0)) > 0
    }


def _build_recent_operator_counts_from_decisions(
    recent_decisions: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, int]]:
    selection_counter: Counter[str] = Counter()
    fallback_counter: Counter[str] = Counter()
    llm_valid_counter: Counter[str] = Counter()
    for row in recent_decisions:
        operator_id = str(row.get("selected_operator_id", "")).strip()
        if not operator_id:
            continue
        selection_counter[operator_id] += 1
        if bool(row.get("fallback_used", False)):
            fallback_counter[operator_id] += 1
        if bool(row.get("llm_valid", False)):
            llm_valid_counter[operator_id] += 1
    return {
        operator_id: {
            "recent_selection_count": int(selection_counter.get(operator_id, 0)),
            "recent_fallback_selection_count": int(fallback_counter.get(operator_id, 0)),
            "recent_llm_valid_selection_count": int(llm_valid_counter.get(operator_id, 0)),
        }
        for operator_id in selection_counter
    }


def _combined_recent_decisions(
    controller_rows: Sequence[ControllerTraceRow],
    generation_local_rows: Sequence[ControllerTraceRow],
    *,
    recent_window: int,
) -> list[dict[str, Any]]:
    if recent_window <= 0:
        return []
    historical_rows = list(controller_rows[-recent_window:])
    if not generation_local_rows:
        return [_compact_recent_decision(row) for row in historical_rows]
    historical_capacity = max(0, recent_window - len(generation_local_rows))
    effective_rows = list(historical_rows[-historical_capacity:]) + list(generation_local_rows)
    return [
        _compact_recent_decision(row, generation_local=index >= len(effective_rows) - len(generation_local_rows))
        for index, row in enumerate(effective_rows)
    ]


def _build_generation_local_memory(
    generation_local_rows: Sequence[ControllerTraceRow],
    *,
    target_offsprings: int | None,
) -> dict[str, Any]:
    operator_counter = Counter(row.selected_operator_id for row in generation_local_rows)
    llm_valid_counter = Counter(
        row.selected_operator_id
        for row in generation_local_rows
        if row.controller_id == "llm" and not bool(row.metadata.get("fallback_used", False))
    )
    fallback_counter = Counter(
        row.selected_operator_id for row in generation_local_rows if bool(row.metadata.get("fallback_used", False))
    )
    accepted_count = len(generation_local_rows)
    dominant_operator_id = ""
    dominant_operator_count = 0
    dominant_operator_share = 0.0
    if operator_counter:
        dominant_operator_id, dominant_operator_count = operator_counter.most_common(1)[0]
        dominant_operator_share = dominant_operator_count / float(max(1, accepted_count))
    dominant_streak = 0
    if generation_local_rows:
        last_operator_id = generation_local_rows[-1].selected_operator_id
        for row in reversed(generation_local_rows):
            if row.selected_operator_id != last_operator_id:
                break
            dominant_streak += 1
    return {
        "accepted_count": int(accepted_count),
        "target_offsprings": None if target_offsprings is None else int(target_offsprings),
        "accepted_share": (
            0.0
            if target_offsprings is None or int(target_offsprings) <= 0
            else float(accepted_count) / float(int(target_offsprings))
        ),
        "dominant_operator_id": dominant_operator_id,
        "dominant_operator_count": int(dominant_operator_count),
        "dominant_operator_share": float(dominant_operator_share),
        "dominant_operator_streak": int(dominant_streak),
        "operator_counts": {
            operator_id: {
                "accepted_count": int(operator_counter.get(operator_id, 0)),
                "accepted_share": (
                    0.0
                    if accepted_count <= 0
                    else float(operator_counter.get(operator_id, 0)) / float(accepted_count)
                ),
                "llm_valid_accepted_count": int(llm_valid_counter.get(operator_id, 0)),
                "fallback_accepted_count": int(fallback_counter.get(operator_id, 0)),
            }
            for operator_id in sorted(operator_counter)
        },
    }


def _build_prompt_generation_panel(
    generation_local_memory: Mapping[str, Any],
) -> dict[str, Any]:
    operator_counts = generation_local_memory.get("operator_counts")
    if not isinstance(operator_counts, Mapping):
        operator_counts = {}
    return {
        "accepted_count": int(generation_local_memory.get("accepted_count", 0)),
        "target_offsprings": generation_local_memory.get("target_offsprings"),
        "accepted_share": float(generation_local_memory.get("accepted_share", 0.0)),
        "dominant_operator_id": str(generation_local_memory.get("dominant_operator_id", "")),
        "dominant_operator_count": int(generation_local_memory.get("dominant_operator_count", 0)),
        "dominant_operator_share": float(generation_local_memory.get("dominant_operator_share", 0.0)),
        "dominant_operator_streak": int(generation_local_memory.get("dominant_operator_streak", 0)),
        "operator_counts": {
            str(operator_id): {
                "accepted_count": int(dict(summary).get("accepted_count", 0)),
                "accepted_share": float(dict(summary).get("accepted_share", 0.0)),
            }
            for operator_id, summary in operator_counts.items()
            if isinstance(summary, Mapping)
        },
    }


def _build_prompt_run_panel(
    *,
    run_state: Mapping[str, Any],
    archive_state: Mapping[str, Any],
) -> dict[str, Any]:
    run_panel = {
        key: run_state[key]
        for key in (
            "evaluations_used",
            "evaluations_remaining",
            "feasible_rate",
            "first_feasible_eval",
            "peak_temperature",
            "temperature_gradient_rms",
            "sink_span",
            "sink_budget_utilization",
        )
        if key in run_state
    }
    run_panel["pareto_size"] = int(archive_state.get("pareto_size", 0))
    return run_panel


def _build_prompt_operator_panel(
    *,
    operator_summary: Mapping[str, Any],
    candidate_operator_ids: Sequence[str],
    regime_panel: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    operator_panel: dict[str, dict[str, Any]] = {}
    objective_balance = regime_panel.get("objective_balance")
    if not isinstance(objective_balance, Mapping):
        objective_balance = None
    for operator_id in candidate_operator_ids:
        normalized_operator_id = str(operator_id)
        summary = operator_summary.get(normalized_operator_id, {})
        summary_row = dict(summary) if isinstance(summary, Mapping) else {}
        operator_panel[normalized_operator_id] = {
            key: summary_row[key]
            for key in (
                "entry_fit",
                "preserve_fit",
                "expand_fit",
                "recent_regression_risk",
                "frontier_evidence",
                "dominant_violation_relief",
            )
            if key in summary_row
        }
        operator_panel[normalized_operator_id].update(
            _build_operator_applicability_row(
                normalized_operator_id,
                summary_row=summary_row,
                regime_panel=regime_panel,
                objective_balance=objective_balance,
            )
        )
    return operator_panel


def _phase_fit_key(phase: str) -> str:
    if phase == "post_feasible_expand":
        return "expand_fit"
    if phase.startswith("post_feasible"):
        return "preserve_fit"
    return "entry_fit"


def _clamp_applicability_score(score: int) -> int:
    return max(0, min(len(_APPLICABILITY_LABELS) - 1, int(score)))


def _objective_balance_effect_matches(
    *,
    preferred_effect: str,
    effects: Mapping[str, str],
) -> bool:
    if preferred_effect == "peak_improve":
        return str(effects.get("expected_peak_effect", "")) == "improve"
    if preferred_effect == "gradient_improve":
        return str(effects.get("expected_gradient_effect", "")) == "improve"
    return False


def _cap_weak_speculative_custom_applicability(
    *,
    operator_id: str,
    summary_row: Mapping[str, Any],
    frontier_evidence: str,
    dominant_violation_relief: str,
    objective_balance: Mapping[str, Any] | None,
    effects: Mapping[str, str],
    applicability_score: int,
) -> int:
    if not isinstance(objective_balance, Mapping):
        return applicability_score

    pressure = str(objective_balance.get("balance_pressure", "low"))
    preferred_effect = str(objective_balance.get("preferred_effect") or "")
    if pressure not in {"high", "medium"} or not _objective_balance_effect_matches(
        preferred_effect=preferred_effect,
        effects=effects,
    ):
        return applicability_score

    operator_family = str(
        summary_row.get("operator_family") or get_operator_behavior_profile(operator_id).family
    )
    if operator_family != "speculative_custom":
        return applicability_score
    if str(summary_row.get("entry_fit", "weak")) != "weak":
        return applicability_score
    if frontier_evidence == "positive":
        return applicability_score
    if dominant_violation_relief != "none":
        return applicability_score

    return min(applicability_score, _FIT_SCORES["supported"])


def _build_operator_applicability_row(
    operator_id: str,
    *,
    summary_row: Mapping[str, Any],
    regime_panel: Mapping[str, Any],
    objective_balance: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    phase = str(regime_panel.get("phase", ""))
    fit_key = _phase_fit_key(phase)
    fit_value = str(summary_row.get(fit_key, "weak"))
    applicability_score = _FIT_SCORES.get(fit_value, 0)
    regression_risk = str(summary_row.get("recent_regression_risk", "medium"))
    frontier_evidence = str(summary_row.get("frontier_evidence", "none"))
    dominant_violation_relief = str(summary_row.get("dominant_violation_relief", "none"))

    if phase == "post_feasible_expand" and frontier_evidence == "positive":
        applicability_score += 1
    if phase.startswith("post_feasible") and regression_risk == "high":
        applicability_score -= 1
    if phase.startswith("prefeasible") and dominant_violation_relief == "supported":
        applicability_score += 1

    effects = dict(
        _OPERATOR_EFFECTS.get(
            operator_id,
            {
                "expected_peak_effect": "neutral",
                "expected_gradient_effect": "neutral",
            },
        )
    )
    if isinstance(objective_balance, Mapping):
        pressure = str(objective_balance.get("balance_pressure", "low"))
        preferred_effect = str(objective_balance.get("preferred_effect") or "")
        if pressure in {"high", "medium"}:
            if preferred_effect == "peak_improve" and effects["expected_peak_effect"] == "improve":
                applicability_score += 1
            elif preferred_effect == "gradient_improve" and effects["expected_gradient_effect"] == "improve":
                applicability_score += 1
            elif (
                preferred_effect == "balanced"
                and "improve" in {effects["expected_peak_effect"], effects["expected_gradient_effect"]}
            ):
                applicability_score += 1
        applicability_score = _cap_weak_speculative_custom_applicability(
            operator_id=operator_id,
            summary_row=summary_row,
            frontier_evidence=frontier_evidence,
            dominant_violation_relief=dominant_violation_relief,
            objective_balance=objective_balance,
            effects=effects,
            applicability_score=applicability_score,
        )

    applicability = _APPLICABILITY_LABELS[_clamp_applicability_score(applicability_score)]
    return {
        **effects,
        "expected_feasibility_risk": regression_risk,
        "applicability": applicability,
    }


def build_controller_state(
    parents: ParentBundle,
    *,
    family: str,
    backbone: str,
    generation_index: int,
    evaluation_index: int,
    candidate_operator_ids: Sequence[str],
    metadata: dict[str, Any] | None = None,
    controller_trace: list[ControllerTraceRow] | None = None,
    operator_trace: list[OperatorTraceRow] | None = None,
    local_controller_trace: list[ControllerTraceRow] | None = None,
    local_operator_trace: list[OperatorTraceRow] | None = None,
    history: Sequence[dict[str, Any]] | None = None,
    recent_window: int = 8,
) -> ControllerState:
    controller_rows = [] if controller_trace is None else list(controller_trace)
    operator_rows = [] if operator_trace is None else list(operator_trace)
    generation_local_controller_rows = [] if local_controller_trace is None else list(local_controller_trace)
    history_rows = [] if history is None else [dict(row) for row in history]
    state_metadata = {} if metadata is None else dict(metadata)
    design_variable_ids = state_metadata.get("design_variable_ids")
    if isinstance(design_variable_ids, Sequence) and not isinstance(design_variable_ids, (str, bytes)):
        design_variable_ids = [str(variable_id) for variable_id in design_variable_ids]
    else:
        design_variable_ids = None
    generation_target_offsprings = state_metadata.get("generation_target_offsprings")
    if generation_target_offsprings is None:
        normalized_generation_target_offsprings = None
    else:
        normalized_generation_target_offsprings = int(generation_target_offsprings)
    state_metadata["candidate_operator_ids"] = [str(operator_id) for operator_id in candidate_operator_ids]
    state_metadata["recent_decisions"] = _combined_recent_decisions(
        controller_rows,
        generation_local_controller_rows,
        recent_window=recent_window,
    )
    operator_summary = summarize_operator_history(
        controller_rows,
        operator_rows,
        recent_window=recent_window,
        history=history_rows,
        design_variable_ids=design_variable_ids,
    )
    state_metadata["operator_summary"] = operator_summary
    state_metadata["historical_recent_operator_counts"] = _build_recent_operator_counts(operator_summary)
    state_metadata["recent_operator_counts"] = _build_recent_operator_counts_from_decisions(
        state_metadata["recent_decisions"]
    )
    generation_local_memory = _build_generation_local_memory(
        generation_local_controller_rows,
        target_offsprings=normalized_generation_target_offsprings,
    )
    state_metadata["generation_local_memory"] = generation_local_memory
    if history_rows:
        sink_budget_limit = (
            None
            if state_metadata.get("radiator_span_max") is None
            else float(state_metadata["radiator_span_max"])
        )
        run_state = build_run_state(
            generation_index=generation_index,
            evaluation_index=evaluation_index,
            history=history_rows,
            decision_index=None if state_metadata.get("decision_index") is None else int(state_metadata["decision_index"]),
            total_evaluation_budget=(
                None
                if state_metadata.get("total_evaluation_budget") is None
                else int(state_metadata["total_evaluation_budget"])
            ),
            sink_budget_limit=sink_budget_limit,
        )
        history_lookup = build_history_lookup(history_rows, design_variable_ids)
        parent_state = build_parent_state(
            parent_vectors=[tuple(float(value) for value in vector.tolist()) for vector in parents.vectors],
            design_variable_ids=design_variable_ids,
            history_lookup=history_lookup,
            parent_indices=state_metadata.get("parent_indices"),
        )
        archive_state = build_archive_state(history_rows)
        domain_regime = build_domain_regime(
            parent_state=parent_state,
            archive_state=archive_state,
            sink_budget_limit=sink_budget_limit,
        )
        progress_state = build_progress_state(history=history_rows)
        progress_state.update(
            build_prefeasible_reset_summary(
                [
                    _policy_recent_decision(row)
                    for row in controller_rows[-recent_window:]
                ]
            )
        )
        regime_panel = build_prompt_regime_panel(
            run_state=run_state,
            progress_state=progress_state,
            archive_state=archive_state,
            domain_regime=domain_regime,
        )
        state_metadata["run_state"] = run_state
        state_metadata["parent_state"] = parent_state
        state_metadata["archive_state"] = archive_state
        state_metadata["domain_regime"] = domain_regime
        state_metadata["progress_state"] = progress_state
        state_metadata["search_phase"] = str(state_metadata.get("search_phase") or domain_regime["phase"])
        state_metadata["prompt_panels"] = {
            "run_panel": _build_prompt_run_panel(run_state=run_state, archive_state=archive_state),
            "regime_panel": regime_panel,
            "parent_panel": build_prompt_parent_panel(parent_state),
            "operator_panel": _build_prompt_operator_panel(
                operator_summary=operator_summary,
                candidate_operator_ids=candidate_operator_ids,
                regime_panel=regime_panel,
            ),
            "generation_panel": _build_prompt_generation_panel(generation_local_memory),
        }
    elif "search_phase" in state_metadata:
        state_metadata["search_phase"] = str(state_metadata["search_phase"])
    return ControllerState.from_parent_bundle(
        parents,
        family=family,
        backbone=backbone,
        generation_index=generation_index,
        evaluation_index=evaluation_index,
        metadata=state_metadata,
    )
