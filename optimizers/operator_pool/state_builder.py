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
    decision_vector_from_values,
    build_spatial_motif_panel,
    build_prompt_parent_panel,
    build_prompt_regime_panel,
    build_prefeasible_reset_summary,
    build_progress_state,
    build_run_state,
)
from optimizers.operator_pool.models import ParentBundle
from optimizers.operator_pool.operators import get_operator_behavior_profile
from optimizers.operator_pool.reflection import summarize_operator_history, summarize_route_family_credit
from optimizers.operator_pool.route_families import expand_budget_family_metrics, operator_route_family
from optimizers.operator_pool.semantic_tasks import (
    operators_by_semantic_task,
    semantic_task_description,
    semantic_task_for_operator,
    semantic_task_target,
)
from optimizers.operator_pool.state import ControllerState
from optimizers.operator_pool.trace import ControllerTraceRow, OperatorTraceRow

_APPLICABILITY_LABELS = ("low", "medium", "high")
_FIT_SCORES = {
    "weak": 0,
    "supported": 1,
    "trusted": 2,
}
_FIT_LABEL_BY_SCORE = {score: label for label, score in _FIT_SCORES.items()}
_OPERATOR_EFFECTS: dict[str, dict[str, str]] = {
    "vector_sbx_pm": {
        "expected_peak_effect": "diversify",
        "expected_gradient_effect": "diversify",
    },
    "component_jitter_1": {
        "expected_peak_effect": "improve",
        "expected_gradient_effect": "neutral",
    },
    "anchored_component_jitter": {
        "expected_peak_effect": "neutral",
        "expected_gradient_effect": "improve",
    },
    "component_relocate_1": {
        "expected_peak_effect": "improve",
        "expected_gradient_effect": "neutral",
    },
    "component_swap_2": {
        "expected_peak_effect": "neutral",
        "expected_gradient_effect": "improve",
    },
    "sink_shift": {
        "expected_peak_effect": "improve",
        "expected_gradient_effect": "neutral",
    },
    "sink_resize": {
        "expected_peak_effect": "neutral",
        "expected_gradient_effect": "neutral",
    },
    "component_block_translate_2_4": {
        "expected_peak_effect": "improve",
        "expected_gradient_effect": "neutral",
    },
    "component_subspace_sbx": {
        "expected_peak_effect": "diversify",
        "expected_gradient_effect": "diversify",
    },
    "hotspot_pull_toward_sink": {
        "expected_peak_effect": "improve",
        "expected_gradient_effect": "neutral",
    },
    "hotspot_spread": {
        "expected_peak_effect": "neutral",
        "expected_gradient_effect": "improve",
    },
    "gradient_band_smooth": {
        "expected_peak_effect": "neutral",
        "expected_gradient_effect": "improve",
    },
    "congestion_relief": {
        "expected_peak_effect": "neutral",
        "expected_gradient_effect": "improve",
    },
    "sink_retarget": {
        "expected_peak_effect": "improve",
        "expected_gradient_effect": "neutral",
    },
    "layout_rebalance": {
        "expected_peak_effect": "neutral",
        "expected_gradient_effect": "improve",
    },
    # Legacy trace aliases kept so older LLM diagnostics still carry the same
    # prompt-surface semantics after the operator-registry split.
    "native_sbx_pm": {
        "expected_peak_effect": "diversify",
        "expected_gradient_effect": "diversify",
    },
    "global_explore": {
        "expected_peak_effect": "neutral",
        "expected_gradient_effect": "neutral",
    },
    "local_refine": {
        "expected_peak_effect": "neutral",
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
    route_family_counter = Counter(
        operator_route_family(row.selected_operator_id)
        for row in generation_local_rows
        if str(row.selected_operator_id).strip()
    )
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
        "route_family_counts": {
            route_family: {
                "accepted_count": int(route_family_counter.get(route_family, 0)),
                "accepted_share": (
                    0.0
                    if accepted_count <= 0
                    else float(route_family_counter.get(route_family, 0)) / float(accepted_count)
                ),
            }
            for route_family in sorted(route_family_counter)
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
        "route_family_counts": {
            str(route_family): {
                "accepted_count": int(dict(summary).get("accepted_count", 0)),
                "accepted_share": float(dict(summary).get("accepted_share", 0.0)),
            }
            for route_family, summary in dict(generation_local_memory.get("route_family_counts", {})).items()
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
            "objective_extremes",
        )
        if key in run_state
    }
    run_panel["pareto_size"] = int(archive_state.get("pareto_size", 0))
    return run_panel


def _build_prompt_operator_panel(
    *,
    operator_summary: Mapping[str, Any],
    candidate_operator_ids: Sequence[str],
    spatial_panel: Mapping[str, Any] | None = None,
    regime_panel: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    operator_panel: dict[str, dict[str, Any]] = {}
    expand_budget_metrics = expand_budget_family_metrics(
        candidate_operator_ids,
        summary_by_operator={
            str(operator_id): dict(summary)
            for operator_id, summary in operator_summary.items()
            if isinstance(summary, Mapping)
        },
    )
    for operator_id in candidate_operator_ids:
        normalized_operator_id = str(operator_id)
        summary = operator_summary.get(normalized_operator_id, {})
        if not isinstance(summary, Mapping):
            summary = {}
        expand_budget_state = expand_budget_metrics.get(operator_route_family(normalized_operator_id), {})
        operator_panel[normalized_operator_id] = {
            key: summary[key]
            for key in (
                "entry_fit",
                "preserve_fit",
                "expand_fit",
                "recent_regression_risk",
                "frontier_evidence",
                "dominant_violation_relief",
                "post_feasible_selection_count",
                "post_feasible_success_count",
                "post_feasible_success_rate",
                "post_feasible_thermal_infeasible_count",
            )
            if key in summary
        }
        operator_panel[normalized_operator_id].update(
            {
                "recent_expand_preserve_credit": int(
                    expand_budget_state.get("recent_expand_feasible_preservation_count", 0)
                ),
                "recent_expand_regression_credit": int(
                    expand_budget_state.get("recent_expand_feasible_regression_count", 0)
                ),
                "recent_expand_frontier_credit": int(
                    expand_budget_state.get("recent_expand_frontier_add_count", 0)
                ),
                "expand_budget_status": str(expand_budget_state.get("expand_budget_status", "neutral")),
            }
        )
        operator_panel[normalized_operator_id].update(
            _build_operator_applicability_row(
                normalized_operator_id,
                summary_row=summary,
                spatial_panel=spatial_panel,
                regime_panel=regime_panel,
            )
        )
    return operator_panel


def _phase_fit_value(summary: Mapping[str, Any], phase: str, regime_panel: Mapping[str, Any]) -> str:
    if phase == "post_feasible_expand":
        return str(summary.get("expand_fit", "weak"))
    if phase == "post_feasible_recover":
        preserve_score = _FIT_SCORES.get(str(summary.get("preserve_fit", "weak")), 0)
        expand_score = _FIT_SCORES.get(str(summary.get("expand_fit", "weak")), 0)
        return _FIT_LABEL_BY_SCORE[max(preserve_score, expand_score)]
    if phase == "post_feasible_preserve":
        frontier_pressure = str(regime_panel.get("frontier_pressure") or "low")
        if frontier_pressure in {"medium", "high"}:
            preserve_score = _FIT_SCORES.get(str(summary.get("preserve_fit", "weak")), 0)
            expand_score = _FIT_SCORES.get(str(summary.get("expand_fit", "weak")), 0)
            return _FIT_LABEL_BY_SCORE[max(preserve_score, expand_score)]
        return str(summary.get("preserve_fit", "weak"))
    if phase.startswith("post_feasible"):
        return str(summary.get("preserve_fit", "weak"))
    return str(summary.get("entry_fit", "weak"))


def _clamp_applicability_score(score: int) -> int:
    return max(0, min(len(_APPLICABILITY_LABELS) - 1, int(score)))


def _qualitative_rank(score: int) -> int:
    if score >= 3:
        return 2
    if score >= 1:
        return 1
    return 0


def _qualitative_level(score: int) -> str:
    return _APPLICABILITY_LABELS[_qualitative_rank(score)]


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

    operator_family = str(summary_row.get("operator_family") or get_operator_behavior_profile(operator_id).family)
    if operator_family != "speculative_custom":
        return applicability_score
    if str(summary_row.get("entry_fit", "weak")) != "weak":
        return applicability_score
    if frontier_evidence == "positive":
        return applicability_score
    if dominant_violation_relief != "none":
        return applicability_score

    return min(applicability_score, _FIT_SCORES["supported"])


def _merge_feasibility_risk(primary: str, secondary: str | None) -> str:
    risk_rank = {"low": 0, "medium": 1, "high": 2}
    primary_label = str(primary or "low")
    secondary_label = str(secondary or primary_label)
    if risk_rank.get(secondary_label, -1) > risk_rank.get(primary_label, -1):
        return secondary_label
    return primary_label


def _offset_reason(offset: float, *, inside_sink_window: bool) -> str:
    if inside_sink_window:
        return "hotspot centroid already sits inside the current sink corridor."
    if offset > 0.0:
        return "hotspot centroid sits to the right of the current sink corridor."
    return "hotspot centroid sits to the left of the current sink corridor."


def _build_spatial_operator_support_row(
    operator_id: str,
    *,
    spatial_panel: Mapping[str, Any] | None,
    regime_panel: Mapping[str, Any],
) -> tuple[int, dict[str, str]]:
    if not isinstance(spatial_panel, Mapping) or not spatial_panel:
        return 0, {
            "expected_feasibility_risk": "low",
            "spatial_match_reason": "state provides only generic support for this operator.",
        }

    hotspot_offset = float(spatial_panel.get("hotspot_to_sink_offset", 0.0))
    inside_sink_window = bool(spatial_panel.get("hotspot_inside_sink_window", False))
    cluster_compactness = float(spatial_panel.get("hottest_cluster_compactness", 0.0))
    nearest_neighbor_gap_min = float(spatial_panel.get("nearest_neighbor_gap_min", 1.0))
    sink_budget_bucket = str(spatial_panel.get("sink_budget_bucket") or "available")
    phase = str(regime_panel.get("phase") or "")
    frontier_pressure = str(regime_panel.get("frontier_pressure") or "low")
    preservation_pressure = str(regime_panel.get("preservation_pressure") or "low")
    absolute_offset = abs(hotspot_offset)
    low_gap = nearest_neighbor_gap_min < 0.11
    compact_cluster = cluster_compactness < 0.13
    sink_aligned_expand = phase == "post_feasible_expand" and inside_sink_window and compact_cluster

    applicability_score = 0
    expected_feasibility_risk = "low"
    spatial_match_reason = "state provides only generic support for this operator."

    if operator_id == "sink_retarget":
        applicability_score = (2 if not inside_sink_window else 0) + (1 if absolute_offset >= 0.10 else 0)
        expected_feasibility_risk = "medium" if sink_budget_bucket == "full_sink" else "low"
        spatial_match_reason = _offset_reason(hotspot_offset, inside_sink_window=inside_sink_window)
    elif operator_id == "hotspot_pull_toward_sink":
        applicability_score = (2 if not inside_sink_window else 0) + (1 if absolute_offset >= 0.08 else 0)
        expected_feasibility_risk = "medium"
        spatial_match_reason = (
            "hot cluster already sits inside the sink corridor, so further sink retargeting has limited leverage."
            if inside_sink_window
            else "hot cluster is misaligned with the sink corridor and can be translated toward it."
        )
    elif operator_id == "hotspot_spread":
        applicability_score = (2 if compact_cluster else 0) + (1 if low_gap else 0) + (1 if sink_aligned_expand else 0)
        expected_feasibility_risk = "low" if sink_aligned_expand and preservation_pressure != "low" else "medium"
        spatial_match_reason = (
            "hot cluster already sits inside the sink corridor, so a bounded spread is the direct way "
            "to open local space without retargeting the sink."
            if sink_aligned_expand
            else "hot cluster is compact enough that spreading can relieve local peak pressure."
        )
    elif operator_id == "gradient_band_smooth":
        applicability_score = (2 if frontier_pressure == "high" else 0) + (1 if compact_cluster else 0)
        expected_feasibility_risk = "low"
        spatial_match_reason = "post-feasible refinement is still gradient-limited in the current regime."
    elif operator_id == "congestion_relief":
        applicability_score = (2 if low_gap else 0) + (1 if compact_cluster else 0)
        expected_feasibility_risk = "low"
        spatial_match_reason = "closest packed components indicate a local congestion bottleneck."
    elif operator_id == "layout_rebalance":
        applicability_score = (1 if absolute_offset >= 0.10 else 0) + (2 if low_gap else 0)
        expected_feasibility_risk = "medium"
        spatial_match_reason = "layout shows both sink misalignment and crowding pressure."
    elif operator_id in {"component_jitter_1", "anchored_component_jitter"}:
        applicability_score = (2 if preservation_pressure == "high" else 0) + (1 if low_gap else 0)
        expected_feasibility_risk = "low"
        spatial_match_reason = "current regime favors low-risk local cleanup around the incumbent basin."
    elif operator_id in {"component_relocate_1", "component_swap_2"}:
        applicability_score = 2 if phase.startswith("prefeasible") or frontier_pressure == "high" else 1
        expected_feasibility_risk = "medium"
        spatial_match_reason = "broader exploration remains useful when the controller still needs diversification."
    elif operator_id in {"vector_sbx_pm", "sink_shift", "sink_resize"}:
        applicability_score = 1
        expected_feasibility_risk = "low"
        spatial_match_reason = "primitive baseline variation remains a safe fallback anchor."
    elif operator_id in {"component_block_translate_2_4", "component_subspace_sbx"}:
        applicability_score = 2 if frontier_pressure == "high" else 1
        expected_feasibility_risk = "low"
        spatial_match_reason = "structured primitive variation can test compact component neighborhoods using only layout state."

    return _qualitative_rank(applicability_score), {
        "expected_feasibility_risk": expected_feasibility_risk,
        "spatial_match_reason": spatial_match_reason,
    }


def _build_operator_applicability_row(
    operator_id: str,
    *,
    summary_row: Mapping[str, Any] | None = None,
    spatial_panel: Mapping[str, Any] | None = None,
    regime_panel: Mapping[str, Any],
    objective_balance: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    summary = dict(summary_row) if isinstance(summary_row, Mapping) else {}
    phase = str(regime_panel.get("phase", ""))
    fit_value = _phase_fit_value(summary, phase, regime_panel)
    applicability_score = _FIT_SCORES.get(fit_value, 0)
    regression_risk = str(summary.get("recent_regression_risk", "medium"))
    frontier_evidence = str(summary.get("frontier_evidence", "none"))
    dominant_violation_relief = str(summary.get("dominant_violation_relief", "none"))

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
    if objective_balance is None:
        panel_objective_balance = regime_panel.get("objective_balance")
        objective_balance = panel_objective_balance if isinstance(panel_objective_balance, Mapping) else None
    if isinstance(objective_balance, Mapping):
        pressure = str(objective_balance.get("balance_pressure", "low"))
        preferred_effect = str(objective_balance.get("preferred_effect") or "")
        if pressure in {"high", "medium"}:
            if preferred_effect == "peak_improve" and effects["expected_peak_effect"] == "improve":
                applicability_score += 1
            elif preferred_effect == "gradient_improve" and effects["expected_gradient_effect"] == "improve":
                applicability_score += 1
            elif preferred_effect == "balanced" and (
                "improve" in {
                    effects["expected_peak_effect"],
                    effects["expected_gradient_effect"],
                }
                or "diversify" in {
                    effects["expected_peak_effect"],
                    effects["expected_gradient_effect"],
                }
            ):
                applicability_score += 1
        applicability_score = _cap_weak_speculative_custom_applicability(
            operator_id=operator_id,
            summary_row=summary,
            frontier_evidence=frontier_evidence,
            dominant_violation_relief=dominant_violation_relief,
            objective_balance=objective_balance,
            effects=effects,
            applicability_score=applicability_score,
        )

    summary_rank = _clamp_applicability_score(applicability_score)
    spatial_rank, spatial_row = _build_spatial_operator_support_row(
        operator_id,
        spatial_panel=spatial_panel,
        regime_panel=regime_panel,
    )
    return {
        "applicability": _APPLICABILITY_LABELS[max(summary_rank, spatial_rank)],
        "expected_peak_effect": str(effects["expected_peak_effect"]),
        "expected_gradient_effect": str(effects["expected_gradient_effect"]),
        "expected_feasibility_risk": _merge_feasibility_risk(
            regression_risk,
            spatial_row.get("expected_feasibility_risk"),
        ),
        "spatial_match_reason": str(
            spatial_row.get("spatial_match_reason", "state provides only generic support for this operator.")
        ),
    }

def _build_prompt_semantic_task_panel(
    *,
    candidate_operator_ids: Sequence[str],
    regime_panel: Mapping[str, Any],
    spatial_panel: Mapping[str, Any],
    recent_decisions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    grouped_candidates = operators_by_semantic_task(candidate_operator_ids)
    recent_task_counts = Counter(
        semantic_task_for_operator(str(row.get("selected_operator_id", "")))
        for row in recent_decisions
        if str(row.get("selected_operator_id", "")).strip()
    )
    recent_total = sum(recent_task_counts.values())
    active_bottleneck = _semantic_active_bottleneck(
        regime_panel=regime_panel,
        spatial_panel=spatial_panel,
    )
    stage_focus = _semantic_stage_focus(regime_panel)
    base_order = _semantic_base_task_order(
        active_bottleneck=active_bottleneck,
        regime_panel=regime_panel,
        spatial_panel=spatial_panel,
        stage_focus=stage_focus,
    )
    candidate_tasks = [task_id for task_id in base_order if task_id in grouped_candidates]
    for task_id in grouped_candidates:
        if task_id not in candidate_tasks:
            candidate_tasks.append(task_id)

    task_order_index = {task_id: index for index, task_id in enumerate(candidate_tasks)}

    sink_budget_gate_active = _semantic_sink_budget_gate_active(regime_panel)

    def task_rank(task_id: str) -> tuple[int, float, int, str]:
        target_low, _target_high = semantic_task_target(task_id)
        count = int(recent_task_counts.get(task_id, 0))
        share = 0.0 if recent_total <= 0 else float(count) / float(recent_total)
        if task_id == "baseline_reset" and stage_focus == "post_feasible_expand" and active_bottleneck in {
            "frontier_stagnation",
            "local_congestion",
        }:
            debt_rank = 2
        elif task_id == "sink_budget_shape" and stage_focus == "post_feasible_expand" and not sink_budget_gate_active:
            debt_rank = 0 if share < 0.50 else 1
        elif task_id == "sink_budget_shape" and sink_budget_gate_active:
            debt_rank = 2
        elif share < target_low:
            debt_rank = 0
        else:
            debt_rank = 1
        return (debt_rank, share, task_order_index.get(task_id, len(task_order_index)), task_id)

    recommended_task_order = sorted(candidate_tasks, key=task_rank)
    task_rationales = {
        task_id: _semantic_task_rationale(
            task_id,
            active_bottleneck=active_bottleneck,
            regime_panel=regime_panel,
            spatial_panel=spatial_panel,
            recent_count=int(recent_task_counts.get(task_id, 0)),
            recent_total=int(recent_total),
        )
        for task_id in recommended_task_order
    }
    return {
        "active_bottleneck": active_bottleneck,
        "stage_focus": stage_focus,
        "recommended_task_order": recommended_task_order,
        "task_operator_candidates": {
            task_id: list(grouped_candidates.get(task_id, []))
            for task_id in recommended_task_order
        },
        "task_rationales": task_rationales,
    }


def _semantic_stage_focus(regime_panel: Mapping[str, Any]) -> str:
    phase = str(regime_panel.get("phase") or "")
    if phase.startswith("prefeasible") or phase == "cold_start":
        return "prefeasible_feasibility"
    if phase == "post_feasible_expand":
        return "post_feasible_expand"
    if phase == "post_feasible_recover":
        return "post_feasible_recover"
    if phase == "post_feasible_preserve":
        return "post_feasible_preserve"
    return "balanced_portfolio"


def _semantic_sink_budget_gate_active(regime_panel: Mapping[str, Any]) -> bool:
    phase = str(regime_panel.get("phase") or "")
    if phase not in {"post_feasible_expand", "post_feasible_preserve"}:
        return False
    if str(regime_panel.get("dominant_violation_family") or "") == "sink_budget":
        return False
    feasible_rate = float(regime_panel.get("run_feasible_rate", 0.0) or 0.0)
    if feasible_rate < 0.50:
        return False
    frontier_stagnation = int(regime_panel.get("recent_frontier_stagnation_count", 0) or 0)
    return frontier_stagnation >= 6


def _semantic_active_bottleneck(
    *,
    regime_panel: Mapping[str, Any],
    spatial_panel: Mapping[str, Any],
) -> str:
    sink_budget_bucket = str(spatial_panel.get("sink_budget_bucket") or "")
    phase = str(regime_panel.get("phase") or "")
    dominant_violation_family = str(regime_panel.get("dominant_violation_family") or "")
    if sink_budget_bucket in {"full_sink", "near_full_sink"} and (
        dominant_violation_family == "sink_budget" or phase.startswith("prefeasible")
    ):
        return "sink_budget_pressure"
    if not bool(spatial_panel.get("hotspot_inside_sink_window", True)):
        return "sink_misaligned_hotspot"
    if float(spatial_panel.get("nearest_neighbor_gap_min", 1.0)) < 0.11:
        return "local_congestion"
    if str(regime_panel.get("frontier_pressure") or "") == "high":
        return "frontier_stagnation"
    return "balanced_portfolio"


def _semantic_base_task_order(
    *,
    active_bottleneck: str,
    regime_panel: Mapping[str, Any],
    spatial_panel: Mapping[str, Any],
    stage_focus: str,
) -> list[str]:
    if stage_focus == "prefeasible_feasibility":
        if active_bottleneck == "sink_budget_pressure":
            return ["sink_budget_shape", "baseline_reset", "global_layout_expand", "semantic_block_move"]
        if active_bottleneck == "sink_misaligned_hotspot":
            return ["sink_alignment", "baseline_reset", "global_layout_expand", "sink_budget_shape"]
        return ["baseline_reset", "global_layout_expand", "sink_budget_shape", "semantic_block_move"]
    if stage_focus == "post_feasible_preserve":
        if active_bottleneck == "sink_budget_pressure":
            return ["sink_budget_shape", "baseline_reset", "local_polish", "sink_alignment", "semantic_block_move"]
        return ["local_polish", "baseline_reset", "sink_budget_shape", "sink_alignment", "semantic_block_move"]
    if stage_focus == "post_feasible_recover":
        if active_bottleneck == "sink_budget_pressure":
            return ["sink_budget_shape", "baseline_reset", "sink_alignment", "local_polish", "semantic_block_move"]
        return ["sink_alignment", "sink_budget_shape", "baseline_reset", "local_polish", "semantic_block_move"]
    if active_bottleneck == "sink_budget_pressure":
        return ["sink_budget_shape", "baseline_reset", "semantic_block_move", "global_layout_expand", "local_polish"]
    if active_bottleneck == "sink_misaligned_hotspot":
        return ["sink_alignment", "semantic_block_move", "sink_budget_shape", "baseline_reset", "local_polish"]
    if active_bottleneck == "local_congestion":
        return ["semantic_block_move", "local_polish", "global_layout_expand", "baseline_reset"]
    if str(regime_panel.get("phase") or "").startswith("post_feasible_expand"):
        return ["global_layout_expand", "semantic_block_move", "baseline_reset", "sink_budget_shape", "local_polish"]
    return ["baseline_reset", "global_layout_expand", "local_polish", "sink_alignment", "sink_budget_shape"]


def _semantic_task_rationale(
    task_id: str,
    *,
    active_bottleneck: str,
    regime_panel: Mapping[str, Any],
    spatial_panel: Mapping[str, Any],
    recent_count: int,
    recent_total: int,
) -> str:
    if task_id == "sink_budget_shape" and active_bottleneck == "sink_budget_pressure":
        return "sink budget pressure is active; reshape coverage before repeating alignment moves."
    if task_id == "sink_alignment" and active_bottleneck == "sink_misaligned_hotspot":
        return "hotspot offset remains outside the current sink corridor."
    if task_id == "semantic_block_move" and active_bottleneck in {"local_congestion", "sink_misaligned_hotspot"}:
        return "component cluster geometry is the active layout bottleneck."
    if task_id == "baseline_reset" and recent_total > 0 and recent_count == 0:
        return "baseline reset is underused in the recent semantic portfolio."
    if task_id == "local_polish" and str(regime_panel.get("preservation_pressure") or "") == "high":
        return "preservation pressure favors low-risk local refinement."
    description = semantic_task_description(task_id)
    if recent_total > 0:
        return f"{description} recent portfolio count {recent_count}/{recent_total}."
    return description


def _build_retrieval_panel(
    *,
    operator_summary: Mapping[str, Any],
    candidate_operator_ids: Sequence[str],
    regime_panel: Mapping[str, Any],
    spatial_panel: Mapping[str, Any],
) -> dict[str, Any]:
    query_phase = str(regime_panel.get("phase") or "")
    phase_fallbacks = _retrieval_phase_fallbacks(query_phase)
    query_regime = {
        "phase": query_phase,
        "dominant_violation_family": str(regime_panel.get("dominant_violation_family") or ""),
        "sink_budget_bucket": str(spatial_panel.get("sink_budget_bucket") or "unknown"),
    }
    if phase_fallbacks:
        query_regime["phase_fallbacks"] = phase_fallbacks
    candidate_set = {str(operator_id) for operator_id in candidate_operator_ids}
    matched_episodes: list[dict[str, Any]] = []
    positive_matches: list[dict[str, Any]] = []
    negative_matches: list[dict[str, Any]] = []
    for operator_id, summary in operator_summary.items():
        normalized_operator_id = str(operator_id)
        if normalized_operator_id not in candidate_set or not isinstance(summary, Mapping):
            continue
        credit_by_regime = summary.get("credit_by_regime", {})
        if not isinstance(credit_by_regime, Mapping):
            continue
        for regime_key, evidence in credit_by_regime.items():
            if not isinstance(regime_key, tuple) or len(regime_key) != 3 or not isinstance(evidence, Mapping):
                continue
            phase, dominant_violation_family, sink_budget_bucket = (str(value) for value in regime_key)
            similarity_score = 0
            if phase == query_regime["phase"]:
                similarity_score += 3
            elif phase in phase_fallbacks:
                similarity_score += 2
            if dominant_violation_family == query_regime["dominant_violation_family"]:
                similarity_score += 2
            if sink_budget_bucket == query_regime["sink_budget_bucket"]:
                similarity_score += 1
            if similarity_score <= 0:
                continue
            matched_episodes.append(
                episode := {
                    "operator_id": normalized_operator_id,
                    "route_family": operator_route_family(normalized_operator_id),
                    "similarity_score": similarity_score,
                    "regime": {
                        "phase": phase,
                        "dominant_violation_family": dominant_violation_family,
                        "sink_budget_bucket": sink_budget_bucket,
                    },
                    "evidence": {
                        "frontier_add_count": int(evidence.get("frontier_add_count", 0)),
                        "feasible_preservation_count": int(evidence.get("feasible_preservation_count", 0)),
                        "feasible_regression_count": int(evidence.get("feasible_regression_count", 0)),
                        "penalty_event_count": int(evidence.get("penalty_event_count", 0)),
                        "avg_objective_delta": float(evidence.get("avg_objective_delta", 0.0)),
                        "avg_total_violation_delta": float(evidence.get("avg_total_violation_delta", 0.0)),
                    },
                }
            )
            evidence_row = episode["evidence"]
            if int(evidence_row["penalty_event_count"]) <= 0 and (
                int(evidence_row["frontier_add_count"]) > 0
                or int(evidence_row["feasible_preservation_count"]) > 0
                or float(evidence_row["avg_objective_delta"]) < 0.0
                or float(evidence_row["avg_total_violation_delta"]) < 0.0
            ):
                positive_matches.append(dict(episode))
            if (
                int(evidence_row["feasible_regression_count"]) > 0
                or int(evidence_row["penalty_event_count"]) > 0
                or float(evidence_row["avg_objective_delta"]) > 0.0
                or float(evidence_row["avg_total_violation_delta"]) > 0.0
            ):
                negative_matches.append(dict(episode))
    matched_episodes.sort(
        key=lambda row: (
            -int(row["similarity_score"]),
            -int(row["evidence"]["frontier_add_count"]),
            -int(row["evidence"]["feasible_preservation_count"]),
            float(row["evidence"]["avg_objective_delta"]),
        )
    )
    positive_matches.sort(
        key=lambda row: (
            -int(row["similarity_score"]),
            -int(row["evidence"]["frontier_add_count"]),
            -int(row["evidence"]["feasible_preservation_count"]),
            float(row["evidence"]["avg_objective_delta"]),
        )
    )
    negative_matches.sort(
        key=lambda row: (
            -int(row["similarity_score"]),
            -int(row["evidence"]["feasible_regression_count"]),
            -int(row["evidence"]["penalty_event_count"]),
            -float(row["evidence"]["avg_total_violation_delta"]),
            -float(row["evidence"]["avg_objective_delta"]),
        )
    )
    route_family_credit = summarize_route_family_credit(
        operator_summary,
        query_regime=query_regime,
    )
    handoff_families = {
        str(route_family).strip()
        for route_family in route_family_credit.get("handoff_families", [])
        if str(route_family).strip()
    }
    handoff_families.update(
        _stable_local_handoff_families(
            query_phase=query_phase,
            phase_fallbacks=phase_fallbacks,
            positive_matches=positive_matches,
        )
    )
    positive_match_families = sorted(
        {
            str(match.get("route_family", "")).strip()
            for match in positive_matches
            if isinstance(match, Mapping) and str(match.get("route_family", "")).strip()
        }
    )
    negative_match_families = sorted(
        {
            str(match.get("route_family", "")).strip()
            for match in negative_matches
            if isinstance(match, Mapping) and str(match.get("route_family", "")).strip()
        }
    )
    route_family_credit = {
        "positive_families": list(route_family_credit.get("positive_families", [])),
        "negative_families": list(route_family_credit.get("negative_families", [])),
        "handoff_families": sorted(handoff_families),
    }
    return {
        "query_regime": query_regime,
        "matched_episodes": matched_episodes[:3],
        "positive_matches": positive_matches[:2],
        "positive_match_families": positive_match_families,
        "negative_matches": negative_matches[:1],
        "negative_match_families": negative_match_families,
        "visibility_floor_families": sorted({*positive_match_families, *handoff_families}),
        "route_family_credit": route_family_credit,
        "stable_local_handoff_active": "stable_local" in handoff_families,
    }


def _retrieval_phase_fallbacks(phase: str) -> list[str]:
    normalized_phase = str(phase).strip()
    if normalized_phase == "post_feasible_recover":
        return ["post_feasible_preserve"]
    if normalized_phase in {"post_feasible_expand", "prefeasible_convert", "prefeasible_stagnation"}:
        return ["post_feasible_preserve"] if normalized_phase == "post_feasible_expand" else ["prefeasible_search"]
    return []


def _stable_local_handoff_families(
    *,
    query_phase: str,
    phase_fallbacks: Sequence[str],
    positive_matches: Sequence[Mapping[str, Any]],
) -> set[str]:
    if str(query_phase).strip() != "post_feasible_recover":
        return set()
    allowed_phases = {str(query_phase).strip(), *(str(phase).strip() for phase in phase_fallbacks)}
    for match in positive_matches:
        if not isinstance(match, Mapping):
            continue
        if str(match.get("route_family", "")).strip() != "stable_local":
            continue
        regime = match.get("regime", {})
        match_phase = str(regime.get("phase", "")).strip() if isinstance(regime, Mapping) else ""
        if match_phase in allowed_phases:
            return {"stable_local"}
    return set()


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
    sink_budget_limit = (
        None
        if state_metadata.get("radiator_span_max") is None
        else float(state_metadata["radiator_span_max"])
    )
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
        sink_budget_limit=sink_budget_limit,
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
        focus_vector = (
            decision_vector_from_values(parents.primary.tolist(), design_variable_ids)
            if design_variable_ids is not None
            else None
        )
        spatial_panel = build_spatial_motif_panel(
            decision_vector=focus_vector,
            sink_budget_limit=sink_budget_limit,
            run_state=run_state,
        )
        retrieval_panel = _build_retrieval_panel(
            operator_summary=operator_summary,
            candidate_operator_ids=candidate_operator_ids,
            regime_panel=regime_panel,
            spatial_panel=spatial_panel,
        )
        state_metadata["prompt_panels"] = {
            "run_panel": _build_prompt_run_panel(run_state=run_state, archive_state=archive_state),
            "regime_panel": regime_panel,
            "parent_panel": build_prompt_parent_panel(parent_state),
            "spatial_panel": spatial_panel,
            "retrieval_panel": retrieval_panel,
            "operator_panel": _build_prompt_operator_panel(
                operator_summary=operator_summary,
                candidate_operator_ids=candidate_operator_ids,
                spatial_panel=spatial_panel,
                regime_panel=regime_panel,
            ),
            "semantic_task_panel": _build_prompt_semantic_task_panel(
                candidate_operator_ids=candidate_operator_ids,
                regime_panel=regime_panel,
                spatial_panel=spatial_panel,
                recent_decisions=state_metadata["recent_decisions"],
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
