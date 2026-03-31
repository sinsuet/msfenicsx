"""Reusable policy-kernel helpers for pre-LLM candidate shaping."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from optimizers.operator_pool.operators import get_operator_behavior_profile
from optimizers.operator_pool.state import ControllerState

_STABLE_FAMILIES = frozenset({"native_baseline", "global_explore", "local_refine"})
_SPECULATIVE_FAMILY = "speculative_custom"
_PREFEASIBLE_SPECULATIVE_FAMILY_WINDOW = 6
_PREFEASIBLE_SPECULATIVE_FAMILY_COUNT = 4
_NO_PROGRESS_RESET_THRESHOLD = 5
_SUPPORTED_SELECTION_THRESHOLD = 3


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
        if progress_phase:
            return progress_phase
    run_state = state.metadata.get("run_state")
    if isinstance(run_state, dict) and run_state.get("first_feasible_eval") is None:
        operator_summary = state.metadata.get("operator_summary", {})
        if isinstance(operator_summary, dict) and not operator_summary:
            return "cold_start"
        return "prefeasible_progress"
    return "post_feasible"


def score_operator_evidence(state: ControllerState, operator_id: str) -> dict[str, Any]:
    summary = state.metadata.get("operator_summary", {})
    summary_row = dict(summary.get(operator_id, {})) if isinstance(summary, dict) else {}
    profile = get_operator_behavior_profile(operator_id)
    feasible_entry_count = int(summary_row.get("feasible_entry_count", 0))
    feasible_preservation_count = int(summary_row.get("feasible_preservation_count", 0))
    support_count = max(
        int(summary_row.get("selection_count", 0)),
        int(summary_row.get("proposal_count", 0)),
        int(summary_row.get("recent_selection_count", 0)),
    )
    if feasible_entry_count > 0 or feasible_preservation_count > 0:
        evidence_level = "trusted"
    elif support_count >= _SUPPORTED_SELECTION_THRESHOLD:
        evidence_level = "supported"
    else:
        evidence_level = "speculative"
    return {
        "operator_family": profile.family,
        "role": profile.role,
        "exploration_class": profile.exploration_class,
        "evidence_level": evidence_level,
        "feasible_entry_count": feasible_entry_count,
        "feasible_preservation_count": feasible_preservation_count,
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

        if _prefeasible_reset_active(state):
            reset_active = True
            filtered = _filter_to_stable_families(tuple(allowed_operator_ids), candidate_annotations)
            if filtered:
                allowed_operator_ids = list(filtered)
            reason_codes.append("prefeasible_forced_reset")

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
