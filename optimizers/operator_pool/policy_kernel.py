"""Reusable policy-kernel helpers for pre-LLM candidate shaping."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from optimizers.operator_pool.operators import get_operator_behavior_profile
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
_PEAK_BALANCE_ESCAPE_OPERATORS = frozenset(
    {"slide_sink", "move_hottest_cluster_toward_sink", "repair_sink_budget"}
)


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
        if progress_phase.startswith("post_feasible") and not _has_real_feasible_entry(state):
            return "prefeasible_stagnation" if int(progress_state.get("recent_no_progress_count", 0)) > 0 else "prefeasible_progress"
        if progress_phase.startswith("post_feasible") and post_feasible_mode in {"expand", "preserve", "recover"}:
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
    support_count = max(
        int(summary_row.get("selection_count", 0)),
        int(summary_row.get("proposal_count", 0)),
        int(summary_row.get("recent_selection_count", 0)),
    )
    if feasible_entry_count > 0 or feasible_preservation_count > 0:
        evidence_level = "trusted"
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
    allowed_operator_ids = list(candidate_ids)
    suppressed_operator_ids: list[str] = []
    reason_codes: list[str] = []
    reset_active = False

    if phase == "cold_start":
        filtered = _filter_to_stable_families(candidate_ids, candidate_annotations)
        if filtered != candidate_ids:
            allowed_operator_ids = list(filtered)
            suppressed_operator_ids.extend(
                operator_id for operator_id in candidate_ids if operator_id not in allowed_operator_ids
            )
            reason_codes.append("cold_start_stable_bootstrap")

    if phase.startswith("prefeasible"):
        suppressed_family_members = _prefeasible_speculative_family_suppression(
            state,
            candidate_ids,
            candidate_annotations,
        )
        if suppressed_family_members:
            allowed_operator_ids = [
                operator_id for operator_id in allowed_operator_ids if operator_id not in suppressed_family_members
            ]
            suppressed_operator_ids.extend(
                operator_id
                for operator_id in suppressed_family_members
                if operator_id not in suppressed_operator_ids
            )
            reason_codes.append("prefeasible_speculative_family_collapse")

        if phase == "prefeasible_convert":
            filtered = _prefeasible_convert_candidates(
                tuple(allowed_operator_ids),
                candidate_annotations,
            )
            if filtered and filtered != tuple(allowed_operator_ids):
                allowed_operator_ids = list(filtered)
                suppressed_operator_ids.extend(
                    operator_id
                    for operator_id in candidate_ids
                    if operator_id not in allowed_operator_ids and operator_id not in suppressed_operator_ids
                )
                reason_codes.append("prefeasible_convert_entry_bias")

        if _prefeasible_reset_active(state):
            reset_active = True
            filtered = _prefeasible_reset_candidates(
                state,
                tuple(allowed_operator_ids),
                candidate_annotations,
            )
            if filtered:
                allowed_operator_ids = list(filtered)
            reason_codes.append("prefeasible_forced_reset")

    if phase.startswith("post_feasible"):
        current_allowed_operator_ids = tuple(allowed_operator_ids)
        filtered, post_feasible_reason_code = _post_feasible_candidate_filter(
            state,
            phase,
            current_allowed_operator_ids,
            candidate_annotations,
        )
        peak_balance_escape_active = bool(
            _peak_balance_escape_candidates(state, phase, current_allowed_operator_ids)
        )
        if filtered != current_allowed_operator_ids:
            allowed_operator_ids = list(filtered)
            suppressed_operator_ids.extend(
                operator_id for operator_id in candidate_ids if operator_id not in allowed_operator_ids
            )
        if post_feasible_reason_code and (
            filtered != current_allowed_operator_ids or peak_balance_escape_active
        ):
            reason_codes.append(post_feasible_reason_code)

    if not allowed_operator_ids:
        allowed_operator_ids = list(candidate_ids)
        suppressed_operator_ids = []
        reason_codes = []
        reset_active = False

    return PolicySnapshot(
        phase=phase,
        allowed_operator_ids=tuple(allowed_operator_ids),
        suppressed_operator_ids=tuple(suppressed_operator_ids),
        reset_active=reset_active,
        reason_codes=tuple(reason_codes),
        candidate_annotations=candidate_annotations,
    )


def _filter_to_stable_families(
    candidate_operator_ids: Sequence[str],
    candidate_annotations: dict[str, dict[str, Any]],
) -> tuple[str, ...]:
    filtered = tuple(
        operator_id
        for operator_id in candidate_operator_ids
        if str(candidate_annotations.get(operator_id, {}).get("operator_family", "")) in _STABLE_FAMILIES
    )
    return tuple(candidate_operator_ids) if not filtered else filtered


def _annotate_prefeasible_roles(
    candidate_annotations: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    annotated: dict[str, dict[str, Any]] = {}
    for operator_id, annotation in candidate_annotations.items():
        enriched = dict(annotation)
        operator_family = str(enriched.get("operator_family", ""))
        enriched["prefeasible_role"] = _PREFEASIBLE_ROLE_BY_FAMILY.get(operator_family, "speculative_custom")
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
    if not _prefeasible_repeated_reset_window(state):
        if _prefeasible_convert_active(state):
            return _prefeasible_convert_candidates(
                candidate_operator_ids,
                candidate_annotations,
                required_operator_ids=stable_candidates,
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
            required_operator_ids=sorted_stable_candidates,
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
    operator_family = str(annotation.get("operator_family", ""))
    evidence_level = str(annotation.get("evidence_level", ""))
    feasible_preservation_count = int(annotation.get("feasible_preservation_count", 0))
    feasible_regression_count = int(annotation.get("feasible_regression_count", 0))
    pareto_contribution_count = int(annotation.get("pareto_contribution_count", 0))
    if operator_family in _STABLE_FAMILIES or feasible_preservation_count > 0:
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
        filtered = tuple(
            operator_id
            for operator_id in candidate_operator_ids
            if str(candidate_annotations.get(operator_id, {}).get("post_feasible_role", "")) == "trusted_preserve"
        )
        filtered = _merge_required_candidates(
            filtered,
            candidate_operator_ids,
            required_operator_ids=_peak_balance_escape_candidates(state, phase, candidate_operator_ids),
        )
        if not filtered:
            filtered = _filter_to_stable_families(candidate_operator_ids, candidate_annotations)
        return (
            tuple(candidate_operator_ids) if not filtered else tuple(filtered),
            "post_feasible_recover_preserve_bias",
        )

    if phase in {"post_feasible_expand", "post_feasible_preserve"}:
        filtered = tuple(
            operator_id
            for operator_id in candidate_operator_ids
            if str(candidate_annotations.get(operator_id, {}).get("post_feasible_role", "")) != "risky_expand"
        )
        frontier_bias_active = filtered and len(filtered) < len(tuple(candidate_operator_ids))
        if phase == "post_feasible_expand":
            filtered = _merge_required_candidates(
                filtered,
                candidate_operator_ids,
                required_operator_ids=_peak_balance_escape_candidates(state, phase, candidate_operator_ids),
            )
        if frontier_bias_active:
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
    prompt_panels = state.metadata.get("prompt_panels")
    if not isinstance(prompt_panels, dict):
        return ()
    regime_panel = prompt_panels.get("regime_panel")
    if not isinstance(regime_panel, dict):
        return ()
    objective_balance = regime_panel.get("objective_balance")
    if not isinstance(objective_balance, dict):
        return ()
    if str(objective_balance.get("balance_pressure", "")).strip() != "high":
        return ()
    if str(objective_balance.get("preferred_effect", "")).strip() != "peak_improve":
        return ()
    return tuple(
        operator_id
        for operator_id in candidate_operator_ids
        if operator_id in _PEAK_BALANCE_ESCAPE_OPERATORS
    )


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
