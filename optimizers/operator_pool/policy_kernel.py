"""Reusable policy-kernel helpers for pre-LLM candidate shaping."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from optimizers.operator_pool.operators import get_operator_behavior_profile
from optimizers.operator_pool.route_families import (
    ROUTE_FAMILY_BY_OPERATOR,
    STABLE_ROUTE_FAMILIES,
    expand_budget_family_metrics,
    operator_route_family,
)
from optimizers.operator_pool.state import ControllerState

_STABLE_FAMILIES = frozenset({"native_baseline", "global_explore", "local_refine"})
_PREFEASIBLE_ROLE_BY_FAMILY = {
    "native_baseline": "stable_baseline",
    "global_explore": "stable_global",
    "local_refine": "stable_local",
}
_STABLE_PREFEASIBLE_ROLES = frozenset(_PREFEASIBLE_ROLE_BY_FAMILY.values())
_SPECULATIVE_FAMILY = "speculative_custom"
_PREFEASIBLE_SPECULATIVE_FAMILY_WINDOW = 6
_PREFEASIBLE_SPECULATIVE_FAMILY_COUNT = 4
_NO_PROGRESS_RESET_THRESHOLD = 5
_SUPPORTED_SELECTION_THRESHOLD = 3
_PREFEASIBLE_CONVERT_STALL_THRESHOLD = 3
_PREFEASIBLE_CONVERT_PERSISTENCE_THRESHOLD = 2
_CUSTOM_MIN_OUTCOME_WINDOW = 4
_CUSTOM_MIN_POST_FEASIBLE_SUCCESS_RATE = 0.35
_STABLE_MIN_OUTCOME_WINDOW = 8
_STABLE_MIN_POST_FEASIBLE_SUCCESS_RATE = 0.35
_PEAK_BALANCE_ESCAPE_OPERATORS = frozenset(
    {
        "hotspot_pull_toward_sink",
        "sink_resize",
        "sink_retarget",
        "slide_sink",
        "move_hottest_cluster_toward_sink",
        "repair_sink_budget",
    }
)
_GRADIENT_BALANCE_ESCAPE_OPERATORS = frozenset(
    {
        "hotspot_spread",
        "gradient_band_smooth",
        "congestion_relief",
        "layout_rebalance",
        "smooth_high_gradient_band",
        "reduce_local_congestion",
        "rebalance_layout",
    }
)
_POST_FEASIBLE_RECOVER_SEMANTIC_VISIBLE = 1
_POST_FEASIBLE_EXPAND_SEMANTIC_VISIBLE = 2
_ROUTE_COOLDOWN_MIN_COUNT = 4
_ROUTE_COOLDOWN_MIN_SHARE = 0.75
_POST_FEASIBLE_ROUTE_FAMILY_DOMINANCE_WINDOW = 6
_POST_FEASIBLE_ROUTE_FAMILY_DOMINANCE_MIN_COUNT = 5
_POST_FEASIBLE_ROUTE_FAMILY_DOMINANCE_MIN_SHARE = 0.75
_OBJECTIVE_ROUTE_CAP_WINDOW = 6
_OBJECTIVE_ROUTE_CAP_MIN_COUNT = 4
_OBJECTIVE_ROUTE_CAP_MIN_SHARE = 0.50
_GENERATION_CUSTOM_OPERATOR_PROBE_LIMIT = 2
_GENERATION_CUSTOM_ROUTE_PROBE_LIMIT = 3
_GENERATION_CUSTOM_TOTAL_PROBE_LIMIT = 4
_GRADIENT_POLISH_HANDOFF_WINDOW = 6
_GRADIENT_POLISH_HANDOFF_MIN_COUNT = 4
_GRADIENT_POLISH_HANDOFF_MIN_SHARE = 0.50
_GRADIENT_POLISH_BROAD_ROLES = frozenset({"native_baseline", "component_swap", "global_explore"})
_GRADIENT_POLISH_ALTERNATIVE_ROLES = frozenset({"component_jitter", "component_relocate", "local_refine"})
_PRESERVE_PLATEAU_WINDOW = 8
_PRESERVE_PLATEAU_MIN_COUNT = 5
_PRESERVE_PLATEAU_MIN_SHARE = 0.50
_PRESERVE_PLATEAU_STABLE_SINK_FAMILY = "primitive_sink"
_PRESERVE_PLATEAU_ASSISTED_SINK_ROUTE_FAMILIES = frozenset({"sink_retarget"})
_PEAK_BUDGET_FILL_UTILIZATION_THRESHOLD = 0.985
_PEAK_BUDGET_FILL_OPERATORS = frozenset(
    {
        "hotspot_pull_toward_sink",
        "sink_resize",
        "sink_retarget",
        "slide_sink",
        "move_hottest_cluster_toward_sink",
        "repair_sink_budget",
    }
)
_EXPAND_SATURATION_THRESHOLD = 24


def _is_stable_annotation(annotation: dict[str, Any]) -> bool:
    return (
        str(annotation.get("exploration_class", "")) == "stable"
        or str(annotation.get("operator_family", "")) in _STABLE_FAMILIES
    )


def _is_custom_annotation(annotation: dict[str, Any]) -> bool:
    return str(annotation.get("exploration_class", "")) == "custom" and not _is_stable_annotation(annotation)


def _custom_has_outcome_credit(annotation: dict[str, Any]) -> bool:
    return (
        int(annotation.get("feasible_entry_count", 0)) > 0
        or int(annotation.get("feasible_preservation_count", 0)) > 0
        or int(annotation.get("pareto_contribution_count", 0)) > 0
        or int(annotation.get("dominant_violation_relief_count", 0)) > 0
        or int(annotation.get("near_feasible_improvement_count", 0)) > 0
        or int(annotation.get("recent_expand_feasible_preservation_count", 0)) > 0
        or int(annotation.get("recent_expand_frontier_add_count", 0)) > 0
    )


def _post_feasible_success_rate(annotation: dict[str, Any]) -> float | None:
    selection_count = int(annotation.get("post_feasible_selection_count", 0))
    if selection_count <= 0:
        return None
    success_count = int(annotation.get("post_feasible_success_count", 0))
    return float(success_count) / float(selection_count)


def _custom_low_post_feasible_success(annotation: dict[str, Any]) -> bool:
    selection_count = int(annotation.get("post_feasible_selection_count", 0))
    if selection_count < _CUSTOM_MIN_OUTCOME_WINDOW:
        return False
    success_rate = _post_feasible_success_rate(annotation)
    return success_rate is not None and success_rate < _CUSTOM_MIN_POST_FEASIBLE_SUCCESS_RATE


def _custom_low_success_without_frontier_credit(annotation: dict[str, Any]) -> bool:
    return (
        _is_custom_annotation(annotation)
        and _custom_low_post_feasible_success(annotation)
        and int(annotation.get("pareto_contribution_count", 0)) <= 0
        and int(annotation.get("recent_expand_frontier_add_count", 0)) <= 0
    )


def _stable_low_success_without_frontier_credit(annotation: dict[str, Any]) -> bool:
    if not _is_stable_annotation(annotation):
        return False
    if str(annotation.get("role", "")) == "native_baseline":
        return False
    selection_count = int(annotation.get("post_feasible_selection_count", 0))
    if selection_count < _STABLE_MIN_OUTCOME_WINDOW:
        return False
    success_rate = _post_feasible_success_rate(annotation)
    if success_rate is None or success_rate >= _STABLE_MIN_POST_FEASIBLE_SUCCESS_RATE:
        return False
    return (
        int(annotation.get("pareto_contribution_count", 0)) <= 0
        and int(annotation.get("frontier_novelty_count", 0)) <= 0
        and int(annotation.get("recent_expand_frontier_add_count", 0)) <= 0
    )


def _custom_without_generation_credit(operator_id: str, annotation: dict[str, Any] | None) -> bool:
    if annotation:
        return _is_custom_annotation(annotation) and not _custom_has_outcome_credit(annotation)
    try:
        profile = get_operator_behavior_profile(str(operator_id))
    except KeyError:
        return False
    return str(profile.exploration_class) == "custom"


@dataclass(frozen=True, slots=True)
class PolicySnapshot:
    phase: str
    allowed_operator_ids: tuple[str, ...]
    suppressed_operator_ids: tuple[str, ...]
    reset_active: bool
    reason_codes: tuple[str, ...]
    candidate_annotations: dict[str, dict[str, Any]]


def detect_search_phase(state: ControllerState) -> str:
    progress_state = state.metadata.get("progress_state")
    if isinstance(progress_state, dict):
        progress_phase = str(progress_state.get("phase", "")).strip()
        if _prefeasible_convert_active(state):
            return "prefeasible_convert"
        post_feasible_mode = str(progress_state.get("post_feasible_mode", "")).strip()
        if (
            progress_phase.startswith("post_feasible")
            and int(progress_state.get("preserve_dwell_remaining", 0)) > 0
            and post_feasible_mode in {"preserve", "recover"}
        ):
            return "post_feasible_preserve"
        if progress_phase.startswith("post_feasible") and _post_feasible_recover_direct_expand_active(state):
            if _expand_saturated(state):
                return "post_feasible_preserve"
            return "post_feasible_expand"
        if post_feasible_mode == "recover" and _post_feasible_recover_exit_ready(state):
            return "post_feasible_preserve"
        if progress_phase.startswith("post_feasible") and _post_feasible_expand_promotion_active(state):
            if _expand_saturated(state):
                return "post_feasible_preserve"
            return "post_feasible_expand"
        if progress_phase.startswith("post_feasible") and not _has_real_feasible_entry(state):
            return "prefeasible_stagnation" if int(progress_state.get("recent_no_progress_count", 0)) > 0 else "prefeasible_progress"
        if progress_phase.startswith("post_feasible") and post_feasible_mode == "expand":
            if _expand_saturated(state):
                return "post_feasible_preserve"
            return "post_feasible_expand"
        if progress_phase.startswith("post_feasible") and post_feasible_mode in {"preserve", "recover"}:
            return f"post_feasible_{post_feasible_mode}"
        if progress_phase:
            return progress_phase
    run_state = state.metadata.get("run_state")
    if isinstance(run_state, dict) and run_state.get("first_feasible_eval") is None:
        operator_summary = state.metadata.get("operator_summary", {})
        if isinstance(operator_summary, dict) and not operator_summary:
            return "cold_start"
        return "prefeasible_progress"
    return "post_feasible"


def _has_real_feasible_entry(state: ControllerState) -> bool:
    run_state = state.metadata.get("run_state")
    progress_state = state.metadata.get("progress_state")
    first_feasible_eval = run_state.get("first_feasible_eval") if isinstance(run_state, dict) else None
    first_feasible_found = progress_state.get("first_feasible_found") if isinstance(progress_state, dict) else None
    if first_feasible_eval is None:
        return False
    if first_feasible_found is None:
        return True
    return first_feasible_found is True


def _expand_saturated(state: ControllerState) -> bool:
    progress_state = state.metadata.get("progress_state")
    if not isinstance(progress_state, dict):
        return False
    expand_saturation_count = int(progress_state.get("expand_saturation_count", 0))
    if expand_saturation_count < _EXPAND_SATURATION_THRESHOLD:
        return False
    return _resolve_diversity_deficit_level(state) == "low"


def _expand_saturation_demotion_active(state: ControllerState, resolved_phase: str) -> bool:
    if resolved_phase != "post_feasible_preserve":
        return False
    progress_state = state.metadata.get("progress_state")
    if not isinstance(progress_state, dict):
        return False
    return (
        str(progress_state.get("post_feasible_mode", "")).strip() == "expand"
        and _expand_saturated(state)
    )


def _post_feasible_recover_exit_ready(state: ControllerState) -> bool:
    progress_state = state.metadata.get("progress_state")
    archive_state = state.metadata.get("archive_state")
    run_state = state.metadata.get("run_state")
    if not isinstance(progress_state, dict) or not isinstance(archive_state, dict) or not isinstance(run_state, dict):
        return False
    if run_state.get("first_feasible_eval") is None:
        return False
    if progress_state.get("recover_release_ready") is not None:
        return bool(progress_state.get("recover_release_ready"))
    if progress_state.get("recover_exit_ready") is not None:
        return bool(progress_state.get("recover_exit_ready"))
    recover_pressure_level = str(progress_state.get("recover_pressure_level", "")).strip()
    if recover_pressure_level:
        return recover_pressure_level == "low"
    stable_preservation_streak = int(progress_state.get("stable_preservation_streak", 0))
    recent_feasible_regression_count = int(archive_state.get("recent_feasible_regression_count", 0))
    new_dominant_violation_family = bool(progress_state.get("new_dominant_violation_family", False))
    return (
        stable_preservation_streak >= 3
        and recent_feasible_regression_count <= 0
        and not new_dominant_violation_family
    )


def _post_feasible_recover_direct_expand_active(state: ControllerState) -> bool:
    progress_state = state.metadata.get("progress_state")
    run_state = state.metadata.get("run_state")
    if not isinstance(progress_state, dict) or not isinstance(run_state, dict):
        return False
    if run_state.get("first_feasible_eval") is None:
        return False
    if str(progress_state.get("post_feasible_mode", "")).strip() != "recover":
        return False
    if not _recover_release_evidence_active(state):
        return False
    if int(progress_state.get("recent_frontier_stagnation_count", 0)) < 2:
        return False
    if _resolve_diversity_deficit_level(state) not in {"high", "medium"}:
        return False
    return True


def _recover_release_evidence_active(state: ControllerState) -> bool:
    progress_state = state.metadata.get("progress_state")
    if isinstance(progress_state, dict) and bool(progress_state.get("recover_release_ready", False)):
        return True
    prompt_panels = state.metadata.get("prompt_panels")
    if not isinstance(prompt_panels, dict):
        return False
    regime_panel = prompt_panels.get("regime_panel")
    if not isinstance(regime_panel, dict):
        regime_panel = {}
    if str(regime_panel.get("preservation_pressure", "low")).strip() != "high":
        return False
    retrieval_panel = _retrieval_panel_from_state(state)
    visibility_floor_families = {
        str(route_family).strip()
        for route_family in retrieval_panel.get("visibility_floor_families", [])
        if str(route_family).strip()
    }
    return bool(visibility_floor_families & STABLE_ROUTE_FAMILIES)


def _post_feasible_expand_promotion_active(state: ControllerState) -> bool:
    progress_state = state.metadata.get("progress_state")
    archive_state = state.metadata.get("archive_state")
    run_state = state.metadata.get("run_state")
    if not isinstance(progress_state, dict) or not isinstance(archive_state, dict) or not isinstance(run_state, dict):
        return False
    if run_state.get("first_feasible_eval") is None:
        return False
    if str(progress_state.get("post_feasible_mode", "")).strip() not in {"preserve", "expand"}:
        return False
    if int(progress_state.get("preserve_dwell_remaining", 0)) > 0:
        return False
    if int(progress_state.get("recent_frontier_stagnation_count", 0)) < 2:
        return False
    diversity_deficit_level = _resolve_diversity_deficit_level(state)
    if diversity_deficit_level not in {"high", "medium"}:
        return False
    regression_surplus = max(
        0,
        int(archive_state.get("recent_feasible_regression_count", 0))
        - int(archive_state.get("recent_feasible_preservation_count", 0)),
    )
    if regression_surplus > 0:
        return False
    return True


def _resolve_diversity_deficit_level(state: ControllerState) -> str:
    progress_state = state.metadata.get("progress_state")
    if isinstance(progress_state, dict):
        diversity_deficit_level = str(progress_state.get("diversity_deficit_level", "")).strip()
        if diversity_deficit_level:
            return diversity_deficit_level
        recent_frontier_stagnation_count = int(progress_state.get("recent_frontier_stagnation_count", 0))
    else:
        recent_frontier_stagnation_count = 0
    archive_state = state.metadata.get("archive_state")
    if not isinstance(archive_state, dict):
        return "low"
    pareto_size = int(archive_state.get("pareto_size", 0))
    if pareto_size <= 1:
        return "high"
    if pareto_size == 2 and recent_frontier_stagnation_count >= 2:
        return "medium"
    return "low"


def score_operator_evidence(state: ControllerState, operator_id: str) -> dict[str, Any]:
    summary = state.metadata.get("operator_summary", {})
    summary_row = dict(summary.get(operator_id, {})) if isinstance(summary, dict) else {}
    profile = get_operator_behavior_profile(operator_id)
    feasible_entry_count = int(summary_row.get("feasible_entry_count", 0))
    feasible_preservation_count = int(summary_row.get("feasible_preservation_count", 0))
    feasible_regression_count = int(summary_row.get("feasible_regression_count", 0))
    pareto_contribution_count = int(summary_row.get("pareto_contribution_count", 0))
    post_feasible_avg_objective_delta = float(summary_row.get("post_feasible_avg_objective_delta", 0.0))
    dominant_violation_relief_count = int(summary_row.get("dominant_violation_relief_count", 0))
    near_feasible_improvement_count = int(summary_row.get("near_feasible_improvement_count", 0))
    avg_near_feasible_violation_delta = float(summary_row.get("avg_near_feasible_violation_delta", 0.0))
    recent_expand_selection_count = int(summary_row.get("recent_expand_selection_count", 0))
    recent_expand_feasible_preservation_count = int(
        summary_row.get("recent_expand_feasible_preservation_count", 0)
    )
    recent_expand_feasible_regression_count = int(summary_row.get("recent_expand_feasible_regression_count", 0))
    recent_expand_frontier_add_count = int(summary_row.get("recent_expand_frontier_add_count", 0))
    post_feasible_selection_count = int(summary_row.get("post_feasible_selection_count", 0))
    post_feasible_success_count = int(summary_row.get("post_feasible_success_count", 0))
    post_feasible_thermal_infeasible_count = int(summary_row.get("post_feasible_thermal_infeasible_count", 0))
    support_count = max(
        int(summary_row.get("selection_count", 0)),
        int(summary_row.get("proposal_count", 0)),
        int(summary_row.get("recent_selection_count", 0)),
    )
    has_custom_outcome_credit = (
        feasible_entry_count > 0
        or feasible_preservation_count > 0
        or pareto_contribution_count > 0
        or dominant_violation_relief_count > 0
        or near_feasible_improvement_count > 0
        or recent_expand_feasible_preservation_count > 0
        or recent_expand_frontier_add_count > 0
    )
    if feasible_entry_count > 0 or feasible_preservation_count > 0:
        evidence_level = "trusted"
    elif profile.exploration_class == "custom":
        evidence_level = "supported" if has_custom_outcome_credit else "speculative"
    elif support_count >= _SUPPORTED_SELECTION_THRESHOLD and profile.family != _SPECULATIVE_FAMILY:
        evidence_level = "supported"
    else:
        evidence_level = "speculative"
    if feasible_entry_count > 0 or (
        dominant_violation_relief_count > 0 and near_feasible_improvement_count > 0
    ):
        entry_evidence_level = "trusted"
    elif dominant_violation_relief_count > 0 or near_feasible_improvement_count > 0:
        entry_evidence_level = "supported"
    else:
        entry_evidence_level = "speculative"
    return {
        "operator_family": profile.family,
        "role": profile.role,
        "exploration_class": profile.exploration_class,
        "evidence_level": evidence_level,
        "entry_evidence_level": entry_evidence_level,
        "feasible_entry_count": feasible_entry_count,
        "feasible_preservation_count": feasible_preservation_count,
        "feasible_regression_count": feasible_regression_count,
        "pareto_contribution_count": pareto_contribution_count,
        "dominant_violation_relief_count": dominant_violation_relief_count,
        "near_feasible_improvement_count": near_feasible_improvement_count,
        "avg_near_feasible_violation_delta": avg_near_feasible_violation_delta,
        "recent_expand_selection_count": recent_expand_selection_count,
        "recent_expand_feasible_preservation_count": recent_expand_feasible_preservation_count,
        "recent_expand_feasible_regression_count": recent_expand_feasible_regression_count,
        "recent_expand_frontier_add_count": recent_expand_frontier_add_count,
        "post_feasible_selection_count": post_feasible_selection_count,
        "post_feasible_success_count": post_feasible_success_count,
        "post_feasible_success_rate": (
            None
            if post_feasible_selection_count <= 0
            else float(post_feasible_success_count) / float(post_feasible_selection_count)
        ),
        "post_feasible_thermal_infeasible_count": post_feasible_thermal_infeasible_count,
        "recent_entry_helpful_regimes": list(summary_row.get("recent_entry_helpful_regimes", [])),
        "post_feasible_avg_objective_delta": post_feasible_avg_objective_delta,
        "recent_family_share": float(summary_row.get("recent_family_share", 0.0)),
        "recent_role_share": float(summary_row.get("recent_role_share", 0.0)),
    }


def build_policy_snapshot(
    state: ControllerState,
    candidate_operator_ids: Sequence[str],
) -> PolicySnapshot:
    candidate_ids = tuple(str(operator_id) for operator_id in candidate_operator_ids)
    phase = detect_search_phase(state)
    candidate_annotations = {
        operator_id: score_operator_evidence(state, operator_id)
        for operator_id in candidate_ids
    }
    if phase == "cold_start" or phase.startswith("prefeasible"):
        candidate_annotations = _annotate_prefeasible_roles(candidate_annotations)
    if phase.startswith("post_feasible"):
        candidate_annotations = _annotate_post_feasible_roles(candidate_annotations)
        candidate_annotations = _annotate_post_feasible_route_budget(
            state,
            candidate_ids,
            candidate_annotations,
        )
        candidate_annotations = _annotate_post_feasible_expand_budget(
            candidate_ids,
            candidate_annotations,
        )
        candidate_annotations = _annotate_post_feasible_generation_probe_budget(
            state,
            candidate_ids,
            candidate_annotations,
        )
        candidate_annotations = _annotate_post_feasible_gradient_polish(
            state,
            phase,
            candidate_ids,
            candidate_annotations,
        )
        candidate_annotations = _annotate_post_feasible_stable_success(
            candidate_ids,
            candidate_annotations,
        )
        candidate_annotations = _annotate_post_feasible_preserve_plateau(
            state,
            phase,
            candidate_ids,
            candidate_annotations,
        )
    reason_codes: list[str] = []
    reset_active = False

    if _expand_saturation_demotion_active(state, phase):
        reason_codes.append("post_feasible_expand_saturation_demotion")

    if phase == "cold_start":
        if any(
            str(annotation.get("prefeasible_role", "")) == "speculative_custom"
            for annotation in candidate_annotations.values()
        ):
            reason_codes.append("cold_start_stable_bootstrap")

    if phase.startswith("prefeasible"):
        suppressed_family_members = _prefeasible_speculative_family_suppression(
            state,
            candidate_ids,
            candidate_annotations,
        )
        if suppressed_family_members:
            reason_codes.append("prefeasible_speculative_family_collapse")

        if phase == "prefeasible_convert":
            required_operator_ids = _prefeasible_convert_required_operator_ids(
                state,
                candidate_ids,
            )
            filtered = _prefeasible_convert_candidates(
                candidate_ids,
                candidate_annotations,
                required_operator_ids=required_operator_ids,
            )
            if filtered and filtered != candidate_ids:
                reason_codes.append("prefeasible_convert_entry_bias")

        if _prefeasible_reset_active(state):
            reset_active = True
            filtered = _prefeasible_reset_candidates(
                state,
                candidate_ids,
                candidate_annotations,
            )
            if filtered:
                reason_codes.append("prefeasible_forced_reset")

        if phase == "prefeasible_convert":
            filtered, positive_credit_restored = _restore_positive_route_family_visibility(
                state,
                phase,
                candidate_ids,
                candidate_ids,
                candidate_annotations,
            )
            if positive_credit_restored or filtered != candidate_ids:
                reason_codes.append("prefeasible_convert_positive_credit_visibility")

    if phase.startswith("post_feasible"):
        positive_restore_candidate_ids = tuple(candidate_ids)
        stable_low_success_suppressed = _post_feasible_stable_low_success_suppression(
            candidate_ids,
            candidate_annotations,
        )
        if stable_low_success_suppressed:
            reason_codes.append("post_feasible_stable_low_success_cooldown")
        preserve_plateau_suppressed = _post_feasible_preserve_plateau_suppression(
            candidate_ids,
            candidate_annotations,
        )
        if preserve_plateau_suppressed:
            reason_codes.append(f"{phase}_plateau_cooldown")
        if phase == "post_feasible_expand":
            generation_probe_suppressed = _post_feasible_generation_probe_budget_suppression(
                state,
                candidate_ids,
                candidate_annotations,
            )
            if generation_probe_suppressed:
                reason_codes.append("post_feasible_expand_generation_probe_budget")
            gradient_polish_suppressed = _post_feasible_gradient_polish_suppression(
                candidate_ids,
                candidate_annotations,
            )
            if gradient_polish_suppressed:
                reason_codes.append("post_feasible_expand_gradient_polish_handoff")
            suppressed_route_family_members = _post_feasible_expand_route_family_dominance_suppression(
                state,
                candidate_ids,
                candidate_annotations,
            )
            if suppressed_route_family_members:
                reason_codes.append("post_feasible_expand_route_family_dominance_cap")
            objective_route_cap_members = _post_feasible_expand_objective_route_cap_suppression(
                state,
                candidate_ids,
                candidate_annotations,
            )
            if objective_route_cap_members:
                reason_codes.append("post_feasible_expand_objective_route_cap")
        filtered, post_feasible_reason_code = _post_feasible_candidate_filter(
            state,
            phase,
            candidate_ids,
            candidate_annotations,
        )
        if phase == "post_feasible_expand":
            filtered, _ = _restore_positive_route_family_visibility(
                state,
                phase,
                positive_restore_candidate_ids,
                tuple(filtered),
                candidate_annotations,
            )
        peak_balance_escape_active = bool(
            _peak_balance_escape_candidates(state, phase, candidate_ids)
        )
        gradient_balance_escape_active = bool(
            _gradient_balance_escape_candidates(state, phase, candidate_ids)
        )
        if post_feasible_reason_code and (
            filtered != candidate_ids
            or peak_balance_escape_active
            or gradient_balance_escape_active
        ):
            reason_codes.append(post_feasible_reason_code)
        gradient_escape_reason_code = _gradient_escape_reason_code(phase)
        if gradient_escape_reason_code and gradient_balance_escape_active:
            reason_codes.append(gradient_escape_reason_code)

    return PolicySnapshot(
        phase=phase,
        allowed_operator_ids=candidate_ids,
        suppressed_operator_ids=(),
        reset_active=reset_active,
        reason_codes=tuple(dict.fromkeys(reason_codes)),
        candidate_annotations=candidate_annotations,
    )


def _annotate_post_feasible_route_budget(
    state: ControllerState,
    candidate_operator_ids: Sequence[str],
    candidate_annotations: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    recent_decisions = state.metadata.get("recent_decisions", [])
    route_counter: Counter[str] = Counter()
    recent_total = 0
    candidate_set = {str(operator_id) for operator_id in candidate_operator_ids}
    for row in recent_decisions:
        operator_id = str(row.get("selected_operator_id", "")).strip()
        if operator_id not in candidate_set:
            continue
        route_family = ROUTE_FAMILY_BY_OPERATOR.get(operator_id)
        if route_family is None:
            continue
        route_counter[route_family] += 1
        recent_total += 1

    annotated: dict[str, dict[str, Any]] = {}
    for operator_id, annotation in candidate_annotations.items():
        enriched = dict(annotation)
        route_family = ROUTE_FAMILY_BY_OPERATOR.get(str(operator_id), "stable_local")
        route_count = int(route_counter.get(route_family, 0))
        route_share = 0.0 if recent_total <= 0 else float(route_count) / float(recent_total)
        cooldown_active = (
            route_count >= _ROUTE_COOLDOWN_MIN_COUNT
            and route_share >= _ROUTE_COOLDOWN_MIN_SHARE
            and int(enriched.get("feasible_regression_count", 0)) > int(enriched.get("pareto_contribution_count", 0))
        )
        enriched["route_budget_state"] = {
            "route_family": route_family,
            "recent_family_count": route_count,
            "recent_family_share": route_share,
            "cooldown_active": cooldown_active,
        }
        annotated[operator_id] = enriched
    return annotated


def _annotate_post_feasible_expand_budget(
    candidate_operator_ids: Sequence[str],
    candidate_annotations: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    family_metrics = expand_budget_family_metrics(
        candidate_operator_ids,
        summary_by_operator=candidate_annotations,
    )
    annotated: dict[str, dict[str, Any]] = {}
    for operator_id, annotation in candidate_annotations.items():
        enriched = dict(annotation)
        route_family = operator_route_family(str(operator_id))
        enriched["expand_budget_state"] = dict(
            family_metrics.get(
                route_family,
                {
                    "route_family": route_family,
                    "recent_expand_selection_count": 0,
                    "recent_expand_feasible_preservation_count": 0,
                    "recent_expand_feasible_regression_count": 0,
                    "recent_expand_frontier_add_count": 0,
                    "expand_budget_score": 0,
                    "expand_budget_status": "neutral",
                },
            )
        )
        low_success_cooldown_active = _custom_low_success_without_frontier_credit(enriched)
        enriched["expand_budget_state"]["low_success_cooldown_active"] = low_success_cooldown_active
        if low_success_cooldown_active:
            enriched["expand_budget_state"]["expand_budget_status"] = "throttled"
            enriched["expand_budget_state"]["budget_status"] = "throttled"
        annotated[operator_id] = enriched
    return annotated


def _annotate_post_feasible_generation_probe_budget(
    state: ControllerState,
    candidate_operator_ids: Sequence[str],
    candidate_annotations: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    operator_counter, route_counter, uncredited_custom_total = _generation_local_probe_counts(
        state,
        candidate_annotations,
    )
    peak_budget_fill_operator_ids = set(
        _peak_budget_fill_operator_ids(state, "post_feasible_expand", candidate_operator_ids)
    )
    annotated: dict[str, dict[str, Any]] = {}
    for operator_id, annotation in candidate_annotations.items():
        enriched = dict(annotation)
        route_family = operator_route_family(str(operator_id))
        operator_count = int(operator_counter.get(str(operator_id), 0))
        route_count = int(route_counter.get(route_family, 0))
        uncredited_custom = _custom_without_generation_credit(str(operator_id), enriched)
        credited_custom = _is_custom_annotation(enriched) and _custom_has_outcome_credit(enriched)
        budget_status = "stable"
        throttle_reasons: list[str] = []
        if credited_custom:
            budget_status = "credited"
        elif str(operator_id) in peak_budget_fill_operator_ids:
            budget_status = "peak_budget_fill"
        elif uncredited_custom:
            if operator_count >= _GENERATION_CUSTOM_OPERATOR_PROBE_LIMIT:
                throttle_reasons.append("operator_probe_limit")
            if route_count >= _GENERATION_CUSTOM_ROUTE_PROBE_LIMIT:
                throttle_reasons.append("route_probe_limit")
            if uncredited_custom_total >= _GENERATION_CUSTOM_TOTAL_PROBE_LIMIT:
                throttle_reasons.append("custom_total_probe_limit")
            budget_status = "throttled" if throttle_reasons else "open_probe"
        enriched["generation_probe_state"] = {
            "route_family": route_family,
            "operator_count": operator_count,
            "route_family_count": route_count,
            "custom_total_count": int(uncredited_custom_total),
            "budget_status": budget_status,
            "throttle_reasons": throttle_reasons,
        }
        annotated[operator_id] = enriched
    return annotated


def _generation_local_probe_counts(
    state: ControllerState,
    candidate_annotations: dict[str, dict[str, Any]],
) -> tuple[Counter[str], Counter[str], int]:
    operator_counter: Counter[str] = Counter()
    route_counter: Counter[str] = Counter()
    uncredited_custom_total = 0
    for row in state.metadata.get("recent_decisions", []):
        if not isinstance(row, dict) or not bool(row.get("generation_local", False)):
            continue
        operator_id = str(row.get("selected_operator_id", "")).strip()
        if not operator_id:
            continue
        operator_counter[operator_id] += 1
        route_family = operator_route_family(operator_id)
        route_counter[route_family] += 1
        if _custom_without_generation_credit(operator_id, candidate_annotations.get(operator_id)):
            uncredited_custom_total += 1
    return operator_counter, route_counter, uncredited_custom_total


def _post_feasible_generation_probe_budget_suppression(
    state: ControllerState,
    candidate_operator_ids: Sequence[str],
    candidate_annotations: dict[str, dict[str, Any]],
) -> tuple[str, ...]:
    stable_alternatives = tuple(
        operator_id
        for operator_id in candidate_operator_ids
        if _is_stable_annotation(dict(candidate_annotations.get(operator_id, {})))
    )
    if not stable_alternatives:
        return ()
    protected_operator_ids = set(
        _peak_budget_fill_operator_ids(state, "post_feasible_expand", candidate_operator_ids)
    )
    return tuple(
        operator_id
        for operator_id in candidate_operator_ids
        if operator_id not in protected_operator_ids
        if str(
            dict(candidate_annotations.get(operator_id, {}))
            .get("generation_probe_state", {})
            .get("budget_status", "")
        )
        == "throttled"
    )


def _annotate_post_feasible_stable_success(
    candidate_operator_ids: Sequence[str],
    candidate_annotations: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    candidate_set = {str(operator_id) for operator_id in candidate_operator_ids}
    annotated: dict[str, dict[str, Any]] = {}
    for operator_id, annotation in candidate_annotations.items():
        enriched = dict(annotation)
        low_success = str(operator_id) in candidate_set and _stable_low_success_without_frontier_credit(enriched)
        enriched["stable_success_state"] = {
            "selection_count": int(enriched.get("post_feasible_selection_count", 0)),
            "success_rate": _post_feasible_success_rate(enriched),
            "low_success_cooldown_active": bool(low_success),
            "budget_status": "throttled" if low_success else "neutral",
        }
        annotated[operator_id] = enriched
    return annotated


def _post_feasible_stable_low_success_suppression(
    candidate_operator_ids: Sequence[str],
    candidate_annotations: dict[str, dict[str, Any]],
) -> tuple[str, ...]:
    throttled = tuple(
        operator_id
        for operator_id in candidate_operator_ids
        if str(
            dict(candidate_annotations.get(operator_id, {}))
            .get("stable_success_state", {})
            .get("budget_status", "")
        )
        == "throttled"
    )
    if not throttled:
        return ()
    viable_alternatives = tuple(
        operator_id
        for operator_id in candidate_operator_ids
        if operator_id not in throttled
        and str(candidate_annotations.get(operator_id, {}).get("post_feasible_role", "")) != "risky_expand"
    )
    return throttled if viable_alternatives else ()


def _annotate_post_feasible_preserve_plateau(
    state: ControllerState,
    phase: str,
    candidate_operator_ids: Sequence[str],
    candidate_annotations: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    plateau_active, plateau_count, plateau_share = _preserve_plateau_state(
        state,
        phase,
        candidate_operator_ids,
        candidate_annotations,
    )
    plateau_operator_ids = {
        str(operator_id)
        for operator_id in candidate_operator_ids
        if _preserve_plateau_operator(str(operator_id), dict(candidate_annotations.get(operator_id, {})))
    }
    plateau_operator_ids.difference_update(
        _peak_budget_fill_operator_ids(state, phase, candidate_operator_ids)
    )
    alternative_available = any(
        str(operator_id) not in plateau_operator_ids
        and str(
            dict(candidate_annotations.get(str(operator_id), {}))
            .get("stable_success_state", {})
            .get("budget_status", "")
        )
        != "throttled"
        and str(candidate_annotations.get(str(operator_id), {}).get("post_feasible_role", "")) != "risky_expand"
        for operator_id in candidate_operator_ids
    )
    annotated: dict[str, dict[str, Any]] = {}
    for operator_id, annotation in candidate_annotations.items():
        enriched = dict(annotation)
        plateau_candidate = str(operator_id) in plateau_operator_ids
        suppress = bool(plateau_active and alternative_available and plateau_candidate)
        enriched["preserve_plateau_state"] = {
            "plateau_active": bool(plateau_active and alternative_available),
            "plateau_candidate": bool(plateau_candidate),
            "alternative_available": bool(alternative_available),
            "recent_plateau_count": int(plateau_count),
            "recent_plateau_share": float(plateau_share),
            "budget_status": "throttled" if suppress else "neutral",
        }
        annotated[operator_id] = enriched
    return annotated


def _post_feasible_preserve_plateau_suppression(
    candidate_operator_ids: Sequence[str],
    candidate_annotations: dict[str, dict[str, Any]],
) -> tuple[str, ...]:
    return tuple(
        operator_id
        for operator_id in candidate_operator_ids
        if str(
            dict(candidate_annotations.get(operator_id, {}))
            .get("preserve_plateau_state", {})
            .get("budget_status", "")
        )
        == "throttled"
    )


def _preserve_plateau_state(
    state: ControllerState,
    phase: str,
    candidate_operator_ids: Sequence[str],
    candidate_annotations: dict[str, dict[str, Any]],
) -> tuple[bool, int, float]:
    if phase not in {"post_feasible_preserve", "post_feasible_expand"}:
        return False, 0, 0.0
    if not _post_feasible_objective_plateau_pressure_active(state):
        return False, 0, 0.0
    candidate_set = {str(operator_id) for operator_id in candidate_operator_ids}
    recent_sequence: list[str] = []
    for row in state.metadata.get("recent_decisions", []):
        if not isinstance(row, dict):
            continue
        operator_id = str(row.get("selected_operator_id", "")).strip()
        if operator_id not in candidate_set:
            continue
        if bool(row.get("fallback_used", False)):
            continue
        if row.get("llm_valid") is False:
            continue
        recent_sequence.append(operator_id)
    recent_window = recent_sequence[-_PRESERVE_PLATEAU_WINDOW:]
    if not recent_window:
        return False, 0, 0.0
    plateau_count = sum(
        1
        for operator_id in recent_window
        if _preserve_plateau_operator(operator_id, dict(candidate_annotations.get(operator_id, {})))
    )
    plateau_share = float(plateau_count) / float(len(recent_window))
    plateau_active = (
        plateau_count >= _PRESERVE_PLATEAU_MIN_COUNT
        and plateau_share >= _PRESERVE_PLATEAU_MIN_SHARE
    )
    return bool(plateau_active), int(plateau_count), float(plateau_share)


def _post_feasible_objective_plateau_pressure_active(state: ControllerState) -> bool:
    progress_state = state.metadata.get("progress_state")
    recent_frontier_stagnation_count = (
        int(progress_state.get("recent_frontier_stagnation_count", 0))
        if isinstance(progress_state, dict)
        else 0
    )
    if recent_frontier_stagnation_count >= _PRESERVE_PLATEAU_WINDOW:
        return True
    prompt_panels = state.metadata.get("prompt_panels")
    if not isinstance(prompt_panels, dict):
        return False
    regime_panel = prompt_panels.get("regime_panel")
    if not isinstance(regime_panel, dict):
        return False
    objective_balance = regime_panel.get("objective_balance")
    if not isinstance(objective_balance, dict):
        return False
    return str(objective_balance.get("balance_pressure", "")).strip() in {"high", "medium"}


def _preserve_plateau_operator(operator_id: str, annotation: dict[str, Any]) -> bool:
    try:
        profile = get_operator_behavior_profile(str(operator_id))
    except KeyError:
        return False
    if _is_stable_annotation(annotation):
        return str(profile.family) == _PRESERVE_PLATEAU_STABLE_SINK_FAMILY
    route_family = operator_route_family(str(operator_id))
    if route_family not in _PRESERVE_PLATEAU_ASSISTED_SINK_ROUTE_FAMILIES:
        return False
    has_frontier_credit = (
        int(annotation.get("pareto_contribution_count", 0)) > 0
        or int(annotation.get("frontier_novelty_count", 0)) > 0
        or int(annotation.get("recent_expand_frontier_add_count", 0)) > 0
        or float(annotation.get("post_feasible_avg_objective_delta", 0.0)) < 0.0
    )
    return not has_frontier_credit


def _annotate_post_feasible_gradient_polish(
    state: ControllerState,
    phase: str,
    candidate_operator_ids: Sequence[str],
    candidate_annotations: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    handoff_active, recent_broad_count, recent_broad_share = _gradient_polish_handoff_state(
        state,
        phase,
        candidate_operator_ids,
    )
    polish_alternatives = set(
        _gradient_polish_alternative_operator_ids(candidate_operator_ids, candidate_annotations)
    )
    alternative_available = bool(polish_alternatives)
    annotated: dict[str, dict[str, Any]] = {}
    for operator_id, annotation in candidate_annotations.items():
        enriched = dict(annotation)
        broad_candidate = _gradient_polish_broad_operator(str(operator_id))
        escape_credit = _gradient_polish_escape_credit(enriched)
        suppress = handoff_active and alternative_available and broad_candidate and not escape_credit
        if suppress:
            budget_status = "throttled"
        elif broad_candidate and escape_credit:
            budget_status = "escape_credit"
        elif str(operator_id) in polish_alternatives:
            budget_status = "polish_alternative"
        else:
            budget_status = "neutral"
        enriched["gradient_polish_state"] = {
            "handoff_active": bool(handoff_active and alternative_available),
            "broad_candidate": bool(broad_candidate),
            "escape_credit": bool(escape_credit),
            "alternative_available": bool(alternative_available),
            "polish_alternative": str(operator_id) in polish_alternatives,
            "recent_broad_count": int(recent_broad_count),
            "recent_broad_share": float(recent_broad_share),
            "budget_status": budget_status,
        }
        annotated[operator_id] = enriched
    return annotated


def _post_feasible_gradient_polish_suppression(
    candidate_operator_ids: Sequence[str],
    candidate_annotations: dict[str, dict[str, Any]],
) -> tuple[str, ...]:
    if not _gradient_polish_alternative_operator_ids(candidate_operator_ids, candidate_annotations):
        return ()
    return tuple(
        operator_id
        for operator_id in candidate_operator_ids
        if str(
            dict(candidate_annotations.get(operator_id, {}))
            .get("gradient_polish_state", {})
            .get("budget_status", "")
        )
        == "throttled"
    )


def _gradient_polish_handoff_state(
    state: ControllerState,
    phase: str,
    candidate_operator_ids: Sequence[str],
) -> tuple[bool, int, float]:
    if phase != "post_feasible_expand":
        return False, 0, 0.0
    if not _gradient_polish_objective_pressure_active(state):
        return False, 0, 0.0
    candidate_set = {str(operator_id) for operator_id in candidate_operator_ids}
    recent_sequence: list[str] = []
    for row in state.metadata.get("recent_decisions", []):
        if not isinstance(row, dict):
            continue
        operator_id = str(row.get("selected_operator_id", "")).strip()
        if operator_id not in candidate_set:
            continue
        if bool(row.get("fallback_used", False)):
            continue
        if row.get("llm_valid") is False:
            continue
        recent_sequence.append(operator_id)
    recent_window = recent_sequence[-_GRADIENT_POLISH_HANDOFF_WINDOW:]
    if not recent_window:
        return False, 0, 0.0
    broad_count = sum(1 for operator_id in recent_window if _gradient_polish_broad_operator(operator_id))
    broad_share = float(broad_count) / float(len(recent_window))
    handoff_active = (
        broad_count >= _GRADIENT_POLISH_HANDOFF_MIN_COUNT
        and broad_share >= _GRADIENT_POLISH_HANDOFF_MIN_SHARE
    )
    return handoff_active, int(broad_count), float(broad_share)


def _gradient_polish_objective_pressure_active(state: ControllerState) -> bool:
    prompt_panels = state.metadata.get("prompt_panels")
    if not isinstance(prompt_panels, dict):
        return False
    regime_panel = prompt_panels.get("regime_panel")
    if not isinstance(regime_panel, dict):
        return False
    objective_balance = regime_panel.get("objective_balance")
    if not isinstance(objective_balance, dict):
        return False
    if str(objective_balance.get("preferred_effect", "")).strip() != "gradient_improve":
        return False
    if str(objective_balance.get("balance_pressure", "")).strip() not in {"high", "medium"}:
        return False
    stagnant_objectives = [str(value).lower() for value in objective_balance.get("stagnant_objectives", [])]
    improving_objectives = [str(value).lower() for value in objective_balance.get("improving_objectives", [])]
    gradient_stagnant = any("gradient" in value for value in stagnant_objectives)
    peak_improving = any("temperature_max" in value or "peak" in value for value in improving_objectives)
    return gradient_stagnant and peak_improving


def _gradient_polish_broad_operator(operator_id: str) -> bool:
    try:
        profile = get_operator_behavior_profile(str(operator_id))
    except KeyError:
        return False
    return str(profile.role) in _GRADIENT_POLISH_BROAD_ROLES


def _gradient_polish_escape_credit(annotation: dict[str, Any]) -> bool:
    return (
        int(annotation.get("pareto_contribution_count", 0)) > 0
        or int(annotation.get("frontier_novelty_count", 0)) > 0
        or int(annotation.get("recent_expand_frontier_add_count", 0)) > 0
        or float(annotation.get("post_feasible_avg_objective_delta", 0.0)) < 0.0
    )


def _gradient_polish_alternative_operator_ids(
    candidate_operator_ids: Sequence[str],
    candidate_annotations: dict[str, dict[str, Any]],
) -> tuple[str, ...]:
    alternatives: list[str] = []
    for operator_id in candidate_operator_ids:
        annotation = dict(candidate_annotations.get(operator_id, {}))
        if not _is_stable_annotation(annotation):
            continue
        try:
            profile = get_operator_behavior_profile(str(operator_id))
        except KeyError:
            continue
        if str(profile.role) not in _GRADIENT_POLISH_ALTERNATIVE_ROLES:
            continue
        if str(annotation.get("post_feasible_role", "")) == "risky_expand":
            continue
        alternatives.append(str(operator_id))
    return tuple(alternatives)


def _post_feasible_expand_route_family_dominance_suppression(
    state: ControllerState,
    candidate_operator_ids: Sequence[str],
    candidate_annotations: dict[str, dict[str, Any]],
) -> tuple[str, ...]:
    candidate_set = {str(operator_id) for operator_id in candidate_operator_ids}
    recent_decisions = state.metadata.get("recent_decisions", [])
    semantic_route_sequence: list[str] = []
    for row in recent_decisions:
        operator_id = str(row.get("selected_operator_id", "")).strip()
        if operator_id not in candidate_set:
            continue
        if bool(row.get("fallback_used", False)):
            continue
        if row.get("llm_valid") is False:
            continue
        route_family = str(
            dict(candidate_annotations.get(operator_id, {}))
            .get("route_budget_state", {})
            .get("route_family", "")
        )
        if not route_family or route_family in {"stable_local", "stable_global"}:
            continue
        semantic_route_sequence.append(route_family)
    if not semantic_route_sequence:
        return ()

    recent_window = semantic_route_sequence[-_POST_FEASIBLE_ROUTE_FAMILY_DOMINANCE_WINDOW:]
    family_counter = Counter(recent_window)
    dominant_family, dominant_count = family_counter.most_common(1)[0]
    dominant_share = float(dominant_count) / float(max(1, len(recent_window)))
    if (
        dominant_count < _POST_FEASIBLE_ROUTE_FAMILY_DOMINANCE_MIN_COUNT
        or dominant_share < _POST_FEASIBLE_ROUTE_FAMILY_DOMINANCE_MIN_SHARE
    ):
        return ()

    alternative_families = {
        str(
            dict(candidate_annotations.get(operator_id, {}))
            .get("route_budget_state", {})
            .get("route_family", "")
        )
        for operator_id in candidate_operator_ids
        if str(
            dict(candidate_annotations.get(operator_id, {}))
            .get("route_budget_state", {})
            .get("route_family", "")
        )
        not in {"", "stable_local", "stable_global", dominant_family}
    }
    if len(alternative_families) < 2:
        return ()

    return tuple(
        operator_id
        for operator_id in candidate_operator_ids
        if str(
            dict(candidate_annotations.get(operator_id, {}))
            .get("route_budget_state", {})
            .get("route_family", "")
        )
        == dominant_family
    )


def _post_feasible_expand_objective_route_cap_suppression(
    state: ControllerState,
    candidate_operator_ids: Sequence[str],
    candidate_annotations: dict[str, dict[str, Any]],
) -> tuple[str, ...]:
    prompt_panels = state.metadata.get("prompt_panels")
    if not isinstance(prompt_panels, dict):
        return ()
    regime_panel = prompt_panels.get("regime_panel")
    if not isinstance(regime_panel, dict):
        return ()
    objective_balance = regime_panel.get("objective_balance")
    if not isinstance(objective_balance, dict):
        return ()
    if str(objective_balance.get("preferred_effect", "")).strip() != "gradient_improve":
        return ()
    if str(objective_balance.get("balance_pressure", "")).strip() not in {"high", "medium"}:
        return ()

    candidate_set = {str(operator_id) for operator_id in candidate_operator_ids}
    recent_route_sequence: list[str] = []
    for row in state.metadata.get("recent_decisions", []):
        operator_id = str(row.get("selected_operator_id", "")).strip()
        if operator_id not in candidate_set:
            continue
        if bool(row.get("fallback_used", False)):
            continue
        if row.get("llm_valid") is False:
            continue
        route_family = operator_route_family(operator_id)
        if route_family:
            recent_route_sequence.append(route_family)
    recent_window = recent_route_sequence[-_OBJECTIVE_ROUTE_CAP_WINDOW:]
    if not recent_window:
        return ()
    sink_retarget_count = sum(1 for route_family in recent_window if route_family == "sink_retarget")
    sink_retarget_share = float(sink_retarget_count) / float(len(recent_window))
    if (
        sink_retarget_count < _OBJECTIVE_ROUTE_CAP_MIN_COUNT
        or sink_retarget_share < _OBJECTIVE_ROUTE_CAP_MIN_SHARE
    ):
        return ()

    gradient_or_stable_alternative_exists = any(
        operator_route_family(operator_id) in {"congestion_relief", "stable_local", "stable_global"}
        for operator_id in candidate_operator_ids
        if operator_route_family(operator_id) != "sink_retarget"
    )
    if not gradient_or_stable_alternative_exists:
        return ()

    suppressible: list[str] = []
    for operator_id in candidate_operator_ids:
        if operator_route_family(operator_id) != "sink_retarget":
            continue
        annotation = dict(candidate_annotations.get(operator_id, {}))
        if int(annotation.get("recent_expand_frontier_add_count", 0)) > 0:
            continue
        suppressible.append(str(operator_id))
    return tuple(suppressible)


def _filter_to_stable_families(
    candidate_operator_ids: Sequence[str],
    candidate_annotations: dict[str, dict[str, Any]],
) -> tuple[str, ...]:
    filtered = tuple(
        operator_id
        for operator_id in candidate_operator_ids
        if _is_stable_annotation(dict(candidate_annotations.get(operator_id, {})))
    )
    return tuple(candidate_operator_ids) if not filtered else filtered


def _annotate_prefeasible_roles(
    candidate_annotations: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    annotated: dict[str, dict[str, Any]] = {}
    for operator_id, annotation in candidate_annotations.items():
        enriched = dict(annotation)
        operator_family = str(enriched.get("operator_family", ""))
        prefeasible_role = _PREFEASIBLE_ROLE_BY_FAMILY.get(operator_family)
        if prefeasible_role is None and _is_stable_annotation(enriched):
            route_family = operator_route_family(str(operator_id))
            prefeasible_role = "stable_global" if route_family == "stable_global" else "stable_local"
        enriched["prefeasible_role"] = prefeasible_role or "speculative_custom"
        annotated[operator_id] = enriched
    return annotated


def _recent_llm_valid_sequence(state: ControllerState, candidate_operator_ids: Sequence[str]) -> tuple[str, ...]:
    candidate_set = {str(operator_id) for operator_id in candidate_operator_ids}
    recent_decisions = state.metadata.get("recent_decisions", [])
    selected_operator_ids: list[str] = []
    for row in recent_decisions:
        operator_id = str(row.get("selected_operator_id", "")).strip()
        if operator_id not in candidate_set:
            continue
        if bool(row.get("fallback_used", False)):
            continue
        if row.get("llm_valid") is False:
            continue
        selected_operator_ids.append(operator_id)
    return tuple(selected_operator_ids)


def _prefeasible_speculative_family_suppression(
    state: ControllerState,
    candidate_operator_ids: Sequence[str],
    candidate_annotations: dict[str, dict[str, Any]],
) -> tuple[str, ...]:
    recent_sequence = _recent_llm_valid_sequence(state, candidate_operator_ids)
    if not recent_sequence:
        return ()
    recent_window = recent_sequence[-_PREFEASIBLE_SPECULATIVE_FAMILY_WINDOW:]
    family_counter = Counter(
        str(candidate_annotations.get(operator_id, {}).get("operator_family", ""))
        for operator_id in recent_window
        if operator_id in candidate_annotations
    )
    if not family_counter:
        return ()
    dominant_family, dominant_count = family_counter.most_common(1)[0]
    if dominant_family != _SPECULATIVE_FAMILY or dominant_count < _PREFEASIBLE_SPECULATIVE_FAMILY_COUNT:
        return ()
    return tuple(
        operator_id
        for operator_id in candidate_operator_ids
        if str(candidate_annotations.get(operator_id, {}).get("operator_family", "")) == dominant_family
        and str(candidate_annotations.get(operator_id, {}).get("evidence_level", "")) == "supported"
    ) or tuple(
        operator_id
        for operator_id in candidate_operator_ids
        if str(candidate_annotations.get(operator_id, {}).get("operator_family", "")) == dominant_family
    )


def _prefeasible_reset_active(state: ControllerState) -> bool:
    progress_state = state.metadata.get("progress_state")
    if not isinstance(progress_state, dict):
        return False
    return int(progress_state.get("recent_no_progress_count", 0)) >= _NO_PROGRESS_RESET_THRESHOLD


def _prefeasible_reset_candidates(
    state: ControllerState,
    candidate_operator_ids: Sequence[str],
    candidate_annotations: dict[str, dict[str, Any]],
) -> tuple[str, ...]:
    stable_candidates = tuple(
        operator_id
        for operator_id in candidate_operator_ids
        if str(candidate_annotations.get(operator_id, {}).get("prefeasible_role", "")) in _STABLE_PREFEASIBLE_ROLES
    )
    if not stable_candidates:
        return _filter_to_stable_families(candidate_operator_ids, candidate_annotations)
    convert_required_operator_ids = (
        _prefeasible_convert_required_operator_ids(
            state,
            candidate_operator_ids,
        )
        if _prefeasible_convert_active(state)
        else ()
    )
    reset_required_operator_ids = (
        *stable_candidates,
        *convert_required_operator_ids,
    )
    if not _prefeasible_repeated_reset_window(state):
        if _prefeasible_convert_active(state):
            return _prefeasible_convert_candidates(
                candidate_operator_ids,
                candidate_annotations,
                required_operator_ids=reset_required_operator_ids,
            )
        return stable_candidates

    original_order = {operator_id: index for index, operator_id in enumerate(candidate_operator_ids)}

    def _sort_key(operator_id: str) -> tuple[float, float, float, int]:
        annotation = candidate_annotations.get(operator_id, {})
        return (
            float(annotation.get("recent_role_share", 0.0)),
            float(annotation.get("recent_family_share", 0.0)),
            float(annotation.get("feasible_entry_count", 0)),
            original_order[operator_id],
        )

    sorted_stable_candidates = tuple(sorted(stable_candidates, key=_sort_key))
    if _prefeasible_convert_active(state):
        return _prefeasible_convert_candidates(
            candidate_operator_ids,
            candidate_annotations,
            required_operator_ids=(
                *sorted_stable_candidates,
                *convert_required_operator_ids,
            ),
        )
    return sorted_stable_candidates


def _prefeasible_repeated_reset_window(state: ControllerState) -> bool:
    progress_state = state.metadata.get("progress_state")
    if not isinstance(progress_state, dict):
        return False
    return int(progress_state.get("prefeasible_reset_window_count", 0)) > 0


def _prefeasible_convert_active(state: ControllerState) -> bool:
    if _has_real_feasible_entry(state):
        return False
    progress_state = state.metadata.get("progress_state")
    if not isinstance(progress_state, dict):
        return False
    if str(progress_state.get("prefeasible_mode", "")).strip() != "convert":
        return False
    search_phase = str(state.metadata.get("search_phase", "")).strip()
    domain_regime = state.metadata.get("domain_regime")
    near_feasible_active = search_phase == "near_feasible"
    if not near_feasible_active and isinstance(domain_regime, dict):
        near_feasible_active = str(domain_regime.get("phase", "")).strip() == "near_feasible"
    if not near_feasible_active and progress_state.get("recent_dominant_violation_family"):
        near_feasible_active = True
    if not near_feasible_active:
        return False
    recent_no_progress_count = _int_or_zero(progress_state.get("recent_no_progress_count"))
    evaluations_since_near_feasible_improvement = _int_or_zero(
        progress_state.get("evaluations_since_near_feasible_improvement")
    )
    dominant_violation_persistence_count = _int_or_zero(
        progress_state.get("recent_dominant_violation_persistence_count")
    )
    return (
        max(recent_no_progress_count, evaluations_since_near_feasible_improvement)
        >= _PREFEASIBLE_CONVERT_STALL_THRESHOLD
        and dominant_violation_persistence_count >= _PREFEASIBLE_CONVERT_PERSISTENCE_THRESHOLD
    )


def _prefeasible_convert_candidates(
    candidate_operator_ids: Sequence[str],
    candidate_annotations: dict[str, dict[str, Any]],
    *,
    required_operator_ids: Sequence[str] = (),
) -> tuple[str, ...]:
    required_set = {str(operator_id) for operator_id in required_operator_ids}
    filtered = tuple(
        operator_id
        for operator_id in candidate_operator_ids
        if operator_id in required_set
        or str(candidate_annotations.get(operator_id, {}).get("prefeasible_role", "")) in _STABLE_PREFEASIBLE_ROLES
        or str(candidate_annotations.get(operator_id, {}).get("entry_evidence_level", ""))
        in {"supported", "trusted"}
    )
    return tuple(candidate_operator_ids) if not filtered else filtered


def _prefeasible_convert_required_operator_ids(
    state: ControllerState,
    candidate_operator_ids: Sequence[str],
) -> tuple[str, ...]:
    prompt_panels = state.metadata.get("prompt_panels")
    if not isinstance(prompt_panels, dict):
        prompt_panels = {}
    regime_panel = prompt_panels.get("regime_panel")
    if not isinstance(regime_panel, dict):
        regime_panel = {}
    spatial_panel = prompt_panels.get("spatial_panel")
    if not isinstance(spatial_panel, dict):
        spatial_panel = {}
    objective_balance = regime_panel.get("objective_balance")
    if not isinstance(objective_balance, dict):
        objective_balance = {}

    required_operator_ids: list[str] = []
    sink_budget_bucket = str(spatial_panel.get("sink_budget_bucket", "")).strip()
    if not sink_budget_bucket:
        domain_regime = state.metadata.get("domain_regime")
        if isinstance(domain_regime, dict) and domain_regime.get("sink_budget_utilization") is not None:
            sink_budget_utilization = float(domain_regime.get("sink_budget_utilization", 0.0))
            if sink_budget_utilization >= 0.95:
                sink_budget_bucket = "full_sink"
            elif sink_budget_utilization >= 0.75:
                sink_budget_bucket = "tight"
            else:
                sink_budget_bucket = "available"

    if sink_budget_bucket in {"tight", "full_sink"}:
        required_operator_ids.extend(
            operator_id
            for operator_id in ("sink_retarget", "repair_sink_budget")
            if operator_id in candidate_operator_ids
        )

    preferred_effect = str(objective_balance.get("preferred_effect", "")).strip()
    balance_pressure = str(objective_balance.get("balance_pressure", "")).strip()
    if preferred_effect == "peak_improve":
        required_operator_ids.extend(
            operator_id
            for operator_id in candidate_operator_ids
            if operator_id in _PEAK_BALANCE_ESCAPE_OPERATORS
        )
    if preferred_effect == "gradient_improve" and balance_pressure in {"high", "medium"}:
        required_operator_ids.extend(
            operator_id
            for operator_id in candidate_operator_ids
            if operator_id in _GRADIENT_BALANCE_ESCAPE_OPERATORS
        )

    hotspot_inside_sink_window = bool(spatial_panel.get("hotspot_inside_sink_window", False))
    if not hotspot_inside_sink_window:
        required_operator_ids.extend(
            operator_id
            for operator_id in (
                "hotspot_pull_toward_sink",
                "sink_retarget",
                "move_hottest_cluster_toward_sink",
            )
            if operator_id in candidate_operator_ids
        )
    if hotspot_inside_sink_window:
        required_operator_ids.extend(
            operator_id
            for operator_id in ("hotspot_spread", "spread_hottest_cluster")
            if operator_id in candidate_operator_ids
        )

    return tuple(
        operator_id
        for operator_id in candidate_operator_ids
        if operator_id in set(required_operator_ids)
    )


def _int_or_zero(value: Any) -> int:
    if value is None:
        return 0
    return int(value)


def _annotate_post_feasible_roles(
    candidate_annotations: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    annotated: dict[str, dict[str, Any]] = {}
    for operator_id, annotation in candidate_annotations.items():
        enriched = dict(annotation)
        enriched["post_feasible_role"] = _post_feasible_role(enriched)
        annotated[operator_id] = enriched
    return annotated


def _post_feasible_role(annotation: dict[str, Any]) -> str:
    evidence_level = str(annotation.get("evidence_level", ""))
    feasible_preservation_count = int(annotation.get("feasible_preservation_count", 0))
    feasible_regression_count = int(annotation.get("feasible_regression_count", 0))
    pareto_contribution_count = int(annotation.get("pareto_contribution_count", 0))
    if _is_custom_annotation(annotation) and (
        not _custom_has_outcome_credit(annotation)
        or _custom_low_post_feasible_success(annotation)
    ):
        return "risky_expand"
    if _is_stable_annotation(annotation) or feasible_preservation_count > 0:
        if feasible_regression_count <= 0:
            return "trusted_preserve"
        return "fragile_preserve"
    if pareto_contribution_count > 0 or (
        evidence_level in {"trusted", "supported"}
        and feasible_regression_count <= 0
        and float(annotation.get("post_feasible_avg_objective_delta", 0.0)) <= 0.0
    ):
        return "supported_expand"
    return "risky_expand"


def _post_feasible_candidate_filter(
    state: ControllerState,
    phase: str,
    candidate_operator_ids: Sequence[str],
    candidate_annotations: dict[str, dict[str, Any]],
) -> tuple[tuple[str, ...], str | None]:
    if phase == "post_feasible_recover":
        gradient_escape_candidates = _gradient_balance_escape_candidates(
            state,
            phase,
            candidate_operator_ids,
        )
        filtered = tuple(
            operator_id
            for operator_id in candidate_operator_ids
            if (
                str(candidate_annotations.get(operator_id, {}).get("post_feasible_role", "")) == "trusted_preserve"
                and _is_stable_annotation(dict(candidate_annotations.get(operator_id, {})))
            )
        )
        filtered = _merge_required_candidates(
            filtered,
            candidate_operator_ids,
            required_operator_ids=(
                *_peak_balance_escape_candidates(state, phase, candidate_operator_ids),
                *gradient_escape_candidates,
            ),
        )
        if not filtered:
            filtered = _filter_to_stable_families(candidate_operator_ids, candidate_annotations)
        filtered, _ = _restore_semantic_visibility(
            phase,
            tuple(candidate_operator_ids),
            tuple(filtered),
            candidate_annotations,
        )
        filtered, positive_credit_restored = _restore_positive_route_family_visibility(
            state,
            phase,
            tuple(candidate_operator_ids),
            tuple(filtered),
            candidate_annotations,
        )
        return (
            tuple(candidate_operator_ids) if not filtered else tuple(filtered),
            (
                "post_feasible_recover_positive_credit_visibility"
                if positive_credit_restored
                else "post_feasible_recover_preserve_bias"
            ),
        )

    if phase in {"post_feasible_expand", "post_feasible_preserve"}:
        candidate_pool = tuple(candidate_operator_ids)
        budget_filtered = False
        if phase == "post_feasible_expand":
            throttled_semantic = {
                operator_id
                for operator_id in candidate_pool
                if _semantic_expand_budget_throttled(operator_id, candidate_annotations)
            }
            if throttled_semantic:
                filtered_pool = tuple(
                    operator_id for operator_id in candidate_pool if operator_id not in throttled_semantic
                )
                if filtered_pool:
                    candidate_pool = filtered_pool
                    budget_filtered = True
        pre_visibility_filtered = tuple(
            operator_id
            for operator_id in candidate_pool
            if str(candidate_annotations.get(operator_id, {}).get("post_feasible_role", "")) != "risky_expand"
        )
        filtered = tuple(
            operator_id
            for operator_id in candidate_pool
            if str(candidate_annotations.get(operator_id, {}).get("post_feasible_role", "")) != "risky_expand"
        )
        if phase == "post_feasible_expand":
            filtered, route_rebalanced = _restore_semantic_visibility(
                phase,
                tuple(candidate_pool),
                tuple(filtered),
                candidate_annotations,
            )
        else:
            route_rebalanced = False
        if phase == "post_feasible_expand":
            filtered = _merge_required_candidates(
                filtered,
                candidate_operator_ids,
                required_operator_ids=(
                    *_peak_balance_escape_candidates(state, phase, candidate_pool),
                    *_gradient_balance_escape_candidates(state, phase, candidate_pool),
                ),
            )
        if phase == "post_feasible_preserve":
            filtered, positive_credit_restored = _restore_positive_route_family_visibility(
                state,
                phase,
                tuple(candidate_operator_ids),
                tuple(filtered),
                candidate_annotations,
            )
            filtered = _merge_required_candidates(
                filtered,
                candidate_operator_ids,
                required_operator_ids=_peak_budget_fill_operator_ids(
                    state,
                    phase,
                    candidate_operator_ids,
                ),
            )
        else:
            positive_credit_restored = False
        if filtered and (
            len(pre_visibility_filtered) < len(tuple(candidate_pool))
            or tuple(filtered) != tuple(candidate_pool)
            or budget_filtered
        ):
            if phase == "post_feasible_expand" and budget_filtered:
                reason_code = "post_feasible_expand_semantic_budget"
            elif phase == "post_feasible_expand" and route_rebalanced:
                reason_code = "post_feasible_expand_route_rebalance"
            elif phase == "post_feasible_preserve" and positive_credit_restored:
                reason_code = "post_feasible_preserve_positive_credit_visibility"
            else:
                reason_code = (
                    "post_feasible_expand_frontier_bias"
                    if phase == "post_feasible_expand"
                    else "post_feasible_preserve_low_regression_bias"
                )
            return tuple(filtered), reason_code

    return tuple(candidate_operator_ids), None


def _peak_balance_escape_candidates(
    state: ControllerState,
    phase: str,
    candidate_operator_ids: Sequence[str],
) -> tuple[str, ...]:
    if phase not in {"post_feasible_recover", "post_feasible_expand"}:
        return ()
    peak_budget_fill_operator_ids = _peak_budget_fill_operator_ids(
        state,
        phase,
        candidate_operator_ids,
    )
    prompt_panels = state.metadata.get("prompt_panels")
    if not isinstance(prompt_panels, dict):
        return peak_budget_fill_operator_ids
    regime_panel = prompt_panels.get("regime_panel")
    if not isinstance(regime_panel, dict):
        return peak_budget_fill_operator_ids
    objective_balance = regime_panel.get("objective_balance")
    if not isinstance(objective_balance, dict):
        return peak_budget_fill_operator_ids
    if str(objective_balance.get("balance_pressure", "")).strip() != "high":
        return peak_budget_fill_operator_ids
    if str(objective_balance.get("preferred_effect", "")).strip() != "peak_improve":
        return peak_budget_fill_operator_ids
    objective_escape_operator_ids = tuple(
        operator_id
        for operator_id in candidate_operator_ids
        if operator_id in _PEAK_BALANCE_ESCAPE_OPERATORS
    )
    return tuple(dict.fromkeys((*objective_escape_operator_ids, *peak_budget_fill_operator_ids)))


def _peak_budget_fill_operator_ids(
    state: ControllerState,
    phase: str,
    candidate_operator_ids: Sequence[str],
) -> tuple[str, ...]:
    if phase not in {"post_feasible_recover", "post_feasible_expand", "post_feasible_preserve"}:
        return ()
    if not _peak_budget_fill_pressure_active(state):
        return ()
    return tuple(
        operator_id
        for operator_id in candidate_operator_ids
        if operator_id in _PEAK_BUDGET_FILL_OPERATORS
    )


def _peak_budget_fill_pressure_active(state: ControllerState) -> bool:
    prompt_panels = state.metadata.get("prompt_panels")
    prompt_panels = prompt_panels if isinstance(prompt_panels, dict) else {}
    run_panel = prompt_panels.get("run_panel")
    run_panel = run_panel if isinstance(run_panel, dict) else {}
    regime_panel = prompt_panels.get("regime_panel")
    regime_panel = regime_panel if isinstance(regime_panel, dict) else {}
    objective_balance = regime_panel.get("objective_balance")
    objective_balance = objective_balance if isinstance(objective_balance, dict) else {}
    if str(objective_balance.get("balance_reason", "")).strip() == "frontier_endpoint_peak_budget_fill":
        return True
    if str(objective_balance.get("preferred_effect", "")).strip() != "peak_improve":
        return False

    sink_budget_utilization = _state_sink_budget_utilization(state, run_panel, regime_panel)
    if (
        sink_budget_utilization is None
        or sink_budget_utilization >= _PEAK_BUDGET_FILL_UTILIZATION_THRESHOLD
    ):
        return False
    pareto_size = int(run_panel.get("pareto_size", 0) or 0)
    if pareto_size > 1:
        return False
    return _state_objective_extremes_share_endpoint(state, run_panel)


def _state_sink_budget_utilization(
    state: ControllerState,
    run_panel: dict[str, Any],
    regime_panel: dict[str, Any],
) -> float | None:
    if run_panel.get("sink_budget_utilization") is not None:
        return float(run_panel["sink_budget_utilization"])
    run_state = state.metadata.get("run_state")
    if isinstance(run_state, dict) and run_state.get("sink_budget_utilization") is not None:
        return float(run_state["sink_budget_utilization"])
    if regime_panel.get("sink_budget_utilization") is not None:
        return float(regime_panel["sink_budget_utilization"])
    return None


def _state_objective_extremes_share_endpoint(
    state: ControllerState,
    run_panel: dict[str, Any],
) -> bool:
    objective_extremes = run_panel.get("objective_extremes")
    if not isinstance(objective_extremes, dict):
        run_state = state.metadata.get("run_state")
        if isinstance(run_state, dict):
            objective_extremes = run_state.get("objective_extremes")
    if not isinstance(objective_extremes, dict):
        return False
    min_peak = objective_extremes.get("min_peak_temperature")
    min_gradient = objective_extremes.get("min_temperature_gradient_rms")
    if not isinstance(min_peak, dict) or not isinstance(min_gradient, dict):
        return False
    if min_peak.get("evaluation_index") is not None and min_peak.get("evaluation_index") == min_gradient.get(
        "evaluation_index"
    ):
        return True
    peak_summary = min_peak.get("objective_summary")
    gradient_summary = min_gradient.get("objective_summary")
    if not isinstance(peak_summary, dict) or not isinstance(gradient_summary, dict):
        return False
    for objective_id in ("minimize_peak_temperature", "minimize_temperature_gradient_rms"):
        if peak_summary.get(objective_id) is None or gradient_summary.get(objective_id) is None:
            return False
        if abs(float(peak_summary[objective_id]) - float(gradient_summary[objective_id])) > 1.0e-9:
            return False
    return True


def _gradient_balance_escape_candidates(
    state: ControllerState,
    phase: str,
    candidate_operator_ids: Sequence[str],
) -> tuple[str, ...]:
    if phase not in {"post_feasible_recover", "post_feasible_expand"}:
        return ()
    prompt_panels = state.metadata.get("prompt_panels")
    if not isinstance(prompt_panels, dict):
        return ()
    regime_panel = prompt_panels.get("regime_panel")
    spatial_panel = prompt_panels.get("spatial_panel")
    if not isinstance(regime_panel, dict) or not isinstance(spatial_panel, dict):
        return ()
    objective_balance = regime_panel.get("objective_balance")
    if not isinstance(objective_balance, dict):
        return ()
    if str(objective_balance.get("preferred_effect", "")).strip() != "gradient_improve":
        return ()
    if str(objective_balance.get("balance_pressure", "")).strip() not in {"high", "medium"}:
        return ()

    nearest_neighbor_gap_min = float(spatial_panel.get("nearest_neighbor_gap_min", 1.0))
    hottest_cluster_compactness = float(spatial_panel.get("hottest_cluster_compactness", 1.0))
    hotspot_inside_sink_window = bool(spatial_panel.get("hotspot_inside_sink_window", False))
    if (
        nearest_neighbor_gap_min >= 0.11
        and hottest_cluster_compactness >= 0.13
        and hotspot_inside_sink_window
    ):
        return ()

    return tuple(
        operator_id
        for operator_id in candidate_operator_ids
        if operator_id in _GRADIENT_BALANCE_ESCAPE_OPERATORS
    )


def _gradient_escape_reason_code(phase: str) -> str | None:
    if phase == "post_feasible_recover":
        return "post_feasible_recover_gradient_escape_floor"
    if phase == "post_feasible_expand":
        return "post_feasible_expand_gradient_escape_floor"
    return None


def _merge_required_candidates(
    filtered_operator_ids: Sequence[str],
    candidate_operator_ids: Sequence[str],
    *,
    required_operator_ids: Sequence[str] = (),
) -> tuple[str, ...]:
    required_set = {str(operator_id) for operator_id in required_operator_ids}
    return tuple(
        operator_id
        for operator_id in candidate_operator_ids
        if operator_id in filtered_operator_ids or operator_id in required_set
    )


def _restore_positive_route_family_visibility(
    state: ControllerState,
    phase: str,
    candidate_operator_ids: Sequence[str],
    filtered_operator_ids: Sequence[str],
    candidate_annotations: dict[str, dict[str, Any]],
) -> tuple[tuple[str, ...], bool]:
    if phase not in {
        "prefeasible_convert",
        "post_feasible_recover",
        "post_feasible_preserve",
        "post_feasible_expand",
    }:
        return tuple(filtered_operator_ids), False
    retrieval_panel = _retrieval_panel_from_state(state)
    route_family_credit = retrieval_panel.get("route_family_credit", {})
    if not isinstance(route_family_credit, dict):
        return tuple(filtered_operator_ids), False
    visibility_floor_families = {
        str(route_family).strip()
        for route_family in retrieval_panel.get("visibility_floor_families", [])
        if str(route_family).strip()
    }
    positive_families = {
        str(route_family).strip()
        for route_family in route_family_credit.get("positive_families", [])
        if str(route_family).strip()
    }
    negative_families = {
        str(route_family).strip()
        for route_family in route_family_credit.get("negative_families", [])
        if str(route_family).strip()
    }
    handoff_families = {
        str(route_family).strip()
        for route_family in route_family_credit.get("handoff_families", [])
        if str(route_family).strip()
    }
    positive_visibility_families = visibility_floor_families | (positive_families - negative_families) | handoff_families
    if not positive_visibility_families:
        return tuple(filtered_operator_ids), False

    positive_match_operator_ids_by_family: dict[str, list[str]] = {}
    for match in retrieval_panel.get("positive_matches", []):
        if not isinstance(match, dict):
            continue
        operator_id = str(match.get("operator_id", "")).strip()
        route_family = str(match.get("route_family", "")).strip()
        if (
            not operator_id
            or not route_family
            or operator_id not in candidate_operator_ids
        ):
            continue
        family_matches = positive_match_operator_ids_by_family.setdefault(route_family, [])
        if operator_id not in family_matches:
            family_matches.append(operator_id)

    selected_operator_ids = {str(operator_id) for operator_id in filtered_operator_ids}
    restored = False
    for route_family in positive_visibility_families:
        positive_match_operator_ids = positive_match_operator_ids_by_family.get(route_family, [])
        if phase == "prefeasible_convert" and positive_match_operator_ids:
            exact_match_operator_id = next(
                (
                    operator_id
                    for operator_id in positive_match_operator_ids
                    if operator_id not in selected_operator_ids
                ),
                "",
            )
            if exact_match_operator_id:
                selected_operator_ids.add(exact_match_operator_id)
                restored = True
                continue
        if any(operator_route_family(operator_id) == route_family for operator_id in selected_operator_ids):
            continue
        family_candidates = _rank_route_family_candidates(
            phase,
            route_family,
            candidate_operator_ids,
            candidate_annotations,
        )
        if phase == "post_feasible_preserve":
            family_candidates = tuple(
                operator_id
                for operator_id in family_candidates
                if _is_stable_annotation(dict(candidate_annotations.get(operator_id, {})))
                or _custom_has_outcome_credit(dict(candidate_annotations.get(operator_id, {})))
            )
        if not family_candidates:
            continue
        if route_family in handoff_families:
            selected_operator_ids.update(family_candidates)
        elif positive_match_operator_ids:
            selected_operator_ids.add(positive_match_operator_ids[0])
        else:
            selected_operator_ids.add(family_candidates[0])
        restored = True
    if not restored:
        return tuple(filtered_operator_ids), False
    restored_candidates = tuple(
        operator_id
        for operator_id in candidate_operator_ids
        if operator_id in selected_operator_ids
    )
    return restored_candidates, True


def _retrieval_panel_from_state(state: ControllerState) -> dict[str, Any]:
    prompt_panels = state.metadata.get("prompt_panels")
    if not isinstance(prompt_panels, dict):
        return {}
    retrieval_panel = prompt_panels.get("retrieval_panel")
    return dict(retrieval_panel) if isinstance(retrieval_panel, dict) else {}


def _rank_route_family_candidates(
    phase: str,
    route_family: str,
    candidate_operator_ids: Sequence[str],
    candidate_annotations: dict[str, dict[str, Any]],
) -> tuple[str, ...]:
    family_operator_ids = tuple(
        operator_id
        for operator_id in candidate_operator_ids
        if operator_route_family(operator_id) == route_family
    )
    if not family_operator_ids:
        return ()
    original_order = {operator_id: index for index, operator_id in enumerate(candidate_operator_ids)}
    semantic_operator_ids = tuple(
        operator_id
        for operator_id in family_operator_ids
        if not _is_stable_annotation(dict(candidate_annotations.get(operator_id, {})))
    )
    if semantic_operator_ids:
        ranked_semantic = _rank_semantic_candidates(
            phase,
            semantic_operator_ids,
            candidate_annotations,
            original_order=original_order,
        )
        if ranked_semantic:
            return ranked_semantic
    return tuple(sorted(family_operator_ids, key=lambda operator_id: original_order.get(operator_id, 10**6)))


def _restore_semantic_visibility(
    phase: str,
    candidate_operator_ids: Sequence[str],
    filtered_operator_ids: Sequence[str],
    candidate_annotations: dict[str, dict[str, Any]],
) -> tuple[tuple[str, ...], bool]:
    semantic_target = (
        _POST_FEASIBLE_RECOVER_SEMANTIC_VISIBLE
        if phase == "post_feasible_recover"
        else _POST_FEASIBLE_EXPAND_SEMANTIC_VISIBLE
    )
    if semantic_target <= 0:
        return tuple(filtered_operator_ids), False

    original_order = {operator_id: index for index, operator_id in enumerate(candidate_operator_ids)}
    stable_operator_ids = tuple(
        operator_id
        for operator_id in candidate_operator_ids
        if _is_stable_annotation(dict(candidate_annotations.get(operator_id, {})))
    )
    semantic_operator_ids = tuple(
        operator_id
        for operator_id in candidate_operator_ids
        if operator_id not in stable_operator_ids
    )
    if not semantic_operator_ids:
        return tuple(filtered_operator_ids), False

    selected_operator_ids = {str(operator_id) for operator_id in filtered_operator_ids}
    if phase == "post_feasible_expand":
        rebalanced = _rebalance_expand_route_visibility(
            tuple(filtered_operator_ids),
            stable_operator_ids,
            semantic_operator_ids,
            candidate_annotations,
            original_order=original_order,
        )
        if rebalanced is not None:
            return rebalanced, tuple(rebalanced) != tuple(filtered_operator_ids)

    selected_semantic_count = sum(1 for operator_id in semantic_operator_ids if operator_id in selected_operator_ids)
    if selected_semantic_count >= semantic_target:
        return tuple(filtered_operator_ids), False

    for operator_id in _rank_semantic_candidates(
        phase,
        semantic_operator_ids,
        candidate_annotations,
        original_order=original_order,
    ):
        selected_operator_ids.add(operator_id)
        selected_semantic_count = sum(1 for candidate_id in semantic_operator_ids if candidate_id in selected_operator_ids)
        if selected_semantic_count >= semantic_target:
            break

    stable_selected = [operator_id for operator_id in stable_operator_ids if operator_id in selected_operator_ids]
    semantic_selected = [operator_id for operator_id in semantic_operator_ids if operator_id in selected_operator_ids]
    restored = tuple(stable_selected + semantic_selected)
    return restored, restored != tuple(filtered_operator_ids)


def _rebalance_expand_route_visibility(
    filtered_operator_ids: Sequence[str],
    stable_operator_ids: Sequence[str],
    semantic_operator_ids: Sequence[str],
    candidate_annotations: dict[str, dict[str, Any]],
    *,
    original_order: dict[str, int],
) -> tuple[str, ...] | None:
    ranked_semantic = _rank_semantic_candidates(
        "post_feasible_expand",
        semantic_operator_ids,
        candidate_annotations,
        original_order=original_order,
    )
    if not ranked_semantic:
        return None

    cooled_route_families = {
        str(
            dict(candidate_annotations.get(operator_id, {}))
            .get("route_budget_state", {})
            .get("route_family", "")
        )
        for operator_id in ranked_semantic
        if bool(
            dict(candidate_annotations.get(operator_id, {}))
            .get("route_budget_state", {})
            .get("cooldown_active", False)
        )
    }
    cooled_route_families.discard("")
    if not cooled_route_families:
        return None

    non_cooled_family_order: list[str] = []
    for operator_id in ranked_semantic:
        route_family = str(
            dict(candidate_annotations.get(operator_id, {}))
            .get("route_budget_state", {})
            .get("route_family", "")
        )
        if not route_family or route_family in cooled_route_families or route_family in non_cooled_family_order:
            continue
        non_cooled_family_order.append(route_family)
    if len(non_cooled_family_order) < 2:
        return None

    semantic_selected: list[str] = []
    for route_family in non_cooled_family_order[:2]:
        for operator_id in ranked_semantic:
            candidate_route_family = str(
                dict(candidate_annotations.get(operator_id, {}))
                .get("route_budget_state", {})
                .get("route_family", "")
            )
            if candidate_route_family == route_family and operator_id not in semantic_selected:
                semantic_selected.append(operator_id)
                break
    if len(semantic_selected) < 2:
        return None

    filtered_selected = {str(operator_id) for operator_id in filtered_operator_ids}
    stable_selected = [operator_id for operator_id in stable_operator_ids if operator_id in filtered_selected]
    return tuple(stable_selected + semantic_selected)


def _rank_semantic_candidates(
    phase: str,
    semantic_operator_ids: Sequence[str],
    candidate_annotations: dict[str, dict[str, Any]],
    *,
    original_order: dict[str, int],
) -> tuple[str, ...]:
    def _expand_budget_rank(annotation: dict[str, Any]) -> int:
        budget_status = str(dict(annotation.get("expand_budget_state", {})).get("expand_budget_status", "neutral"))
        priority = {
            "preferred": 0,
            "neutral": 1,
            "throttled": 2,
        }
        return priority.get(budget_status, 1)

    def _evidence_rank(annotation: dict[str, Any]) -> int:
        evidence_level = str(annotation.get("evidence_level", ""))
        if evidence_level == "trusted":
            return 0
        if evidence_level == "supported":
            return 1
        return 2

    def _role_rank(annotation: dict[str, Any]) -> int:
        role = str(annotation.get("post_feasible_role", ""))
        if phase == "post_feasible_recover":
            priority = {
                "trusted_preserve": 0,
                "fragile_preserve": 1,
                "supported_expand": 2,
                "risky_expand": 3,
            }
            return priority.get(role, 4)
        priority = {
            "supported_expand": 0,
            "fragile_preserve": 1,
            "trusted_preserve": 2,
            "risky_expand": 3,
        }
        return priority.get(role, 4)

    def _sort_key(operator_id: str) -> tuple[float, ...]:
        annotation = dict(candidate_annotations.get(operator_id, {}))
        return (
            float(_expand_budget_rank(annotation)) if phase == "post_feasible_expand" else 0.0,
            float(_role_rank(annotation)),
            float(_evidence_rank(annotation)),
            -float(annotation.get("pareto_contribution_count", 0)),
            -float(dict(annotation.get("expand_budget_state", {})).get("recent_expand_frontier_add_count", 0)),
            -float(dict(annotation.get("expand_budget_state", {})).get("recent_expand_feasible_preservation_count", 0)),
            float(dict(annotation.get("expand_budget_state", {})).get("recent_expand_feasible_regression_count", 0)),
            -float(annotation.get("feasible_preservation_count", 0)),
            float(annotation.get("feasible_regression_count", 0)),
            float(original_order.get(operator_id, 10**6)),
        )

    return tuple(sorted((str(operator_id) for operator_id in semantic_operator_ids), key=_sort_key))


def _semantic_expand_budget_throttled(
    operator_id: str,
    candidate_annotations: dict[str, dict[str, Any]],
) -> bool:
    annotation = dict(candidate_annotations.get(str(operator_id), {}))
    if _is_stable_annotation(annotation):
        return False
    expand_budget_state = dict(annotation.get("expand_budget_state", {}))
    return str(expand_budget_state.get("expand_budget_status", "neutral")) == "throttled"
