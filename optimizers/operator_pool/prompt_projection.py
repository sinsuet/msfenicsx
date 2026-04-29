"""Phase-scoped prompt projections for LLM operator selection."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from optimizers.operator_pool.policy_kernel import PolicySnapshot
from optimizers.operator_pool.state import ControllerState

_PREFEASIBLE_MIN_SUPPORTED_SELECTIONS = 3
_POST_FEASIBLE_ARCHIVE_KEYS = frozenset(
    {
        "pareto_size",
        "recent_frontier_add_count",
        "evaluations_since_frontier_add",
        "recent_feasible_regression_count",
        "recent_feasible_preservation_count",
        "recent_frontier_stagnation_count",
        "frontier_add_evaluation_indices",
        "feasible_regression_evaluation_indices",
        "feasible_preservation_evaluation_indices",
    }
)
_POST_FEASIBLE_PROGRESS_KEYS = frozenset(
    {
        "recent_frontier_stagnation_count",
        "post_feasible_mode",
    }
)
_POST_FEASIBLE_OPERATOR_KEYS = frozenset(
    {
        "pareto_contribution_count",
        "frontier_novelty_count",
        "post_feasible_avg_objective_delta",
        "post_feasible_avg_violation_delta",
        "avg_feasible_objective_delta",
    }
)
_RUN_PANEL_PROMPT_KEYS = frozenset(
    {
        "evaluations_used",
        "evaluations_remaining",
        "feasible_rate",
        "first_feasible_eval",
        "peak_temperature",
        "temperature_gradient_rms",
        "sink_span",
        "sink_budget_utilization",
        "pareto_size",
    }
)
_GENERATION_PANEL_PROMPT_KEYS = frozenset(
    {
        "accepted_count",
        "target_offsprings",
        "accepted_share",
        "dominant_operator_id",
        "dominant_operator_count",
        "dominant_operator_share",
        "dominant_operator_streak",
        "route_family_counts",
    }
)
_SPATIAL_PANEL_PROMPT_KEYS = frozenset(
    {
        "hotspot_to_sink_offset",
        "hotspot_inside_sink_window",
        "hottest_cluster_compactness",
        "nearest_neighbor_gap_min",
        "sink_budget_bucket",
    }
)
_PREFEASIBLE_OPERATOR_PANEL_PROMPT_KEYS = frozenset(
    {
        "applicability",
        "dominant_violation_relief",
        "entry_fit",
        "expand_fit",
        "expected_feasibility_risk",
        "expected_gradient_effect",
        "expected_peak_effect",
        "preserve_fit",
        "recent_regression_risk",
    }
)
_POST_FEASIBLE_OPERATOR_PANEL_PROMPT_KEYS = frozenset(
    {
        "applicability",
        "entry_fit",
        "preserve_fit",
        "expand_fit",
        "frontier_evidence",
        "expected_peak_effect",
        "expected_gradient_effect",
        "expected_feasibility_risk",
        "recent_regression_risk",
        "role",
        "post_feasible_role",
        "expand_budget_status",
        "exposure_priority",
        "exposure_status",
    }
)
_CANDIDATE_ANNOTATION_PROMPT_KEYS = frozenset(
    {
        "operator_family",
        "role",
        "evidence_level",
        "prefeasible_role",
        "post_feasible_role",
        "entry_evidence_level",
        "feasible_entry_count",
        "feasible_preservation_count",
        "feasible_regression_count",
        "pareto_contribution_count",
        "dominant_violation_relief_count",
    }
)
_PARENT_PROMPT_KEYS = frozenset(
    {
        "evaluation_index",
        "feasible",
        "total_violation",
        "dominant_violation",
        "objective_values",
        "sink_span",
        "sink_budget_utilization",
    }
)
_MATCH_EVIDENCE_PROMPT_KEYS = frozenset(
    {
        "frontier_add_count",
        "feasible_regression_count",
        "feasible_preservation_count",
        "penalty_event_count",
    }
)
_MAX_POSITIVE_MATCHES = 2
_MAX_NEGATIVE_MATCHES = 1


def build_prompt_projection(
    state: ControllerState,
    *,
    candidate_operator_ids: Sequence[str],
    original_candidate_operator_ids: Sequence[str],
    policy_snapshot: PolicySnapshot,
    guardrail: Mapping[str, Any] | None,
) -> dict[str, Any]:
    candidate_ids = tuple(str(operator_id) for operator_id in candidate_operator_ids)
    metadata: dict[str, Any] = {
        "candidate_operator_ids": list(candidate_ids),
    }
    prompt_phase = _resolve_prompt_phase(state, policy_snapshot)
    post_feasible_active = prompt_phase.startswith("post_feasible")

    if "search_phase" in state.metadata:
        metadata["search_phase"] = state.metadata["search_phase"]
    if "prompt_panels" in state.metadata and isinstance(state.metadata["prompt_panels"], Mapping):
        metadata["prompt_panels"] = _project_prompt_panels(
            dict(state.metadata["prompt_panels"]),
            candidate_operator_ids=candidate_ids,
            prompt_phase=prompt_phase,
            post_feasible_active=post_feasible_active,
            policy_snapshot=policy_snapshot,
        )
    metadata["phase_policy"] = {
        "phase": prompt_phase,
        "reset_active": policy_snapshot.reset_active,
        "reason_codes": list(policy_snapshot.reason_codes),
        "candidate_annotations": {},
    }
    if tuple(str(operator_id) for operator_id in original_candidate_operator_ids) != candidate_ids:
        metadata["original_candidate_operator_ids"] = [str(operator_id) for operator_id in original_candidate_operator_ids]
    if guardrail is not None:
        metadata["decision_guardrail"] = dict(guardrail)
    return metadata


def _project_prompt_panels(
    prompt_panels: dict[str, Any],
    *,
    candidate_operator_ids: Sequence[str],
    prompt_phase: str,
    post_feasible_active: bool,
    policy_snapshot: PolicySnapshot,
) -> dict[str, Any]:
    projected: dict[str, Any] = {}
    run_panel = prompt_panels.get("run_panel")
    if isinstance(run_panel, Mapping):
        projected["run_panel"] = _project_keyed_panel(run_panel, _RUN_PANEL_PROMPT_KEYS)
    regime_panel = prompt_panels.get("regime_panel")
    if isinstance(regime_panel, Mapping):
        projected_regime_panel = dict(regime_panel)
        projected_regime_panel["phase"] = prompt_phase
        projected["regime_panel"] = projected_regime_panel
    parent_panel = prompt_panels.get("parent_panel")
    if isinstance(parent_panel, Mapping):
        projected["parent_panel"] = _project_parent_panel(parent_panel)
    generation_panel = prompt_panels.get("generation_panel")
    if isinstance(generation_panel, Mapping):
        projected["generation_panel"] = _project_keyed_panel(generation_panel, _GENERATION_PANEL_PROMPT_KEYS)
    spatial_panel = prompt_panels.get("spatial_panel")
    if isinstance(spatial_panel, Mapping):
        projected["spatial_panel"] = _project_keyed_panel(spatial_panel, _SPATIAL_PANEL_PROMPT_KEYS)
    retrieval_panel = prompt_panels.get("retrieval_panel")
    if isinstance(retrieval_panel, Mapping):
        projected_retrieval_panel = _project_retrieval_panel(retrieval_panel)
        query_regime = projected_retrieval_panel.get("query_regime")
        if isinstance(query_regime, Mapping):
            projected_query_regime = dict(query_regime)
            original_phase = str(projected_query_regime.get("phase", "")).strip()
            existing_fallbacks = _string_list(projected_query_regime.get("phase_fallbacks", []))
            if prompt_phase:
                projected_query_regime["phase"] = prompt_phase
                if original_phase and original_phase != prompt_phase:
                    projected_query_regime["phase_fallbacks"] = _merge_phase_fallbacks(
                        original_phase,
                        existing_fallbacks,
                    )
                elif existing_fallbacks:
                    projected_query_regime["phase_fallbacks"] = existing_fallbacks
            projected_retrieval_panel["query_regime"] = projected_query_regime
        projected["retrieval_panel"] = projected_retrieval_panel
    operator_panel = prompt_panels.get("operator_panel")
    if isinstance(operator_panel, Mapping):
        projected_operator_panel: dict[str, dict[str, Any]] = {}
        for operator_id, summary in operator_panel.items():
            normalized_operator_id = str(operator_id)
            if normalized_operator_id not in candidate_operator_ids or not isinstance(summary, Mapping):
                continue
            projected_summary = _project_operator_panel_row(
                summary,
                post_feasible_active=post_feasible_active,
            )
            annotation = policy_snapshot.candidate_annotations.get(normalized_operator_id)
            if isinstance(annotation, Mapping):
                projected_summary.update(
                    _project_candidate_annotation(
                        annotation,
                        post_feasible_active=post_feasible_active,
                    )
                )
            if not post_feasible_active:
                projected_summary.pop("frontier_evidence", None)
            projected_operator_panel[normalized_operator_id] = projected_summary
        projected["operator_panel"] = projected_operator_panel
    return projected


def _project_keyed_panel(panel: Mapping[str, Any], keys: frozenset[str]) -> dict[str, Any]:
    return {
        key: panel[key]
        for key in keys
        if key in panel
    }


def _project_parent_panel(parent_panel: Mapping[str, Any]) -> dict[str, Any]:
    projected: dict[str, Any] = {}
    for key in ("closest_to_feasible_parent", "strongest_feasible_parent"):
        value = parent_panel.get(key)
        if isinstance(value, Mapping):
            projected[key] = _project_parent_summary(value)
        else:
            projected[key] = value
    return projected


def _project_parent_summary(parent_summary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: parent_summary[key]
        for key in _PARENT_PROMPT_KEYS
        if key in parent_summary
    }


def _project_retrieval_panel(retrieval_panel: Mapping[str, Any]) -> dict[str, Any]:
    projected: dict[str, Any] = {}
    for key in (
        "query_regime",
        "positive_match_families",
        "negative_match_families",
        "visibility_floor_families",
        "stable_local_handoff_active",
        "route_family_credit",
    ):
        if key in retrieval_panel:
            value = retrieval_panel[key]
            projected[key] = dict(value) if isinstance(value, Mapping) else value
    projected["positive_matches"] = _project_retrieval_matches(
        retrieval_panel.get("positive_matches", []),
        limit=_MAX_POSITIVE_MATCHES,
    )
    projected["negative_matches"] = _project_retrieval_matches(
        retrieval_panel.get("negative_matches", []),
        limit=_MAX_NEGATIVE_MATCHES,
    )
    return projected


def _project_retrieval_matches(value: Any, *, limit: int) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    projected_matches: list[dict[str, Any]] = []
    for match in value:
        if len(projected_matches) >= limit:
            break
        if not isinstance(match, Mapping):
            continue
        projected_match: dict[str, Any] = {}
        for key in ("operator_id", "route_family", "similarity_score"):
            if key in match:
                projected_match[key] = match[key]
        evidence = match.get("evidence")
        if isinstance(evidence, Mapping):
            projected_match["evidence"] = {
                key: evidence[key]
                for key in _MATCH_EVIDENCE_PROMPT_KEYS
                if key in evidence
            }
        projected_matches.append(projected_match)
    return projected_matches


def _project_operator_panel_row(
    summary: Mapping[str, Any],
    *,
    post_feasible_active: bool,
) -> dict[str, Any]:
    keys = (
        _POST_FEASIBLE_OPERATOR_PANEL_PROMPT_KEYS
        if post_feasible_active
        else _PREFEASIBLE_OPERATOR_PANEL_PROMPT_KEYS
    )
    return {
        key: summary[key]
        for key in keys
        if key in summary
    }


def _resolve_prompt_phase(state: ControllerState, policy_snapshot: PolicySnapshot) -> str:
    phase = str(policy_snapshot.phase)
    if not phase.startswith("post_feasible"):
        return phase
    run_state = state.metadata.get("run_state")
    progress_state = state.metadata.get("progress_state")
    first_feasible_eval = run_state.get("first_feasible_eval") if isinstance(run_state, Mapping) else None
    first_feasible_found = progress_state.get("first_feasible_found") if isinstance(progress_state, Mapping) else None
    if first_feasible_eval is None:
        return "prefeasible_progress"
    if first_feasible_found is None:
        return phase
    if first_feasible_found is not True:
        return "prefeasible_progress"
    return phase


def _project_archive_state(
    archive_state: dict[str, Any],
    *,
    post_feasible_active: bool,
) -> dict[str, Any]:
    if post_feasible_active:
        return archive_state
    return {
        key: value
        for key, value in archive_state.items()
        if key not in _POST_FEASIBLE_ARCHIVE_KEYS
    }


def _project_progress_state(
    progress_state: dict[str, Any],
    *,
    post_feasible_active: bool,
) -> dict[str, Any]:
    if post_feasible_active:
        return progress_state
    return {
        key: value
        for key, value in progress_state.items()
        if key not in _POST_FEASIBLE_PROGRESS_KEYS
    }


def _build_prompt_operator_summary(
    state: ControllerState,
    candidate_operator_ids: Sequence[str],
    *,
    post_feasible_active: bool,
) -> dict[str, dict[str, Any]]:
    raw_operator_summary = state.metadata.get("operator_summary", {})
    if not isinstance(raw_operator_summary, Mapping):
        return {}
    prompt_operator_summary: dict[str, dict[str, Any]] = {}
    for operator_id, raw_summary in raw_operator_summary.items():
        normalized_operator_id = str(operator_id)
        if normalized_operator_id not in candidate_operator_ids or not isinstance(raw_summary, Mapping):
            continue
        summary = dict(raw_summary)
        if not post_feasible_active:
            summary = _calibrate_prefeasible_operator_summary(summary)
            for key in _POST_FEASIBLE_OPERATOR_KEYS:
                summary.pop(key, None)
        prompt_operator_summary[normalized_operator_id] = summary
    return prompt_operator_summary


def _calibrate_prefeasible_operator_summary(summary: dict[str, Any]) -> dict[str, Any]:
    calibrated_summary = dict(summary)
    selection_count = int(calibrated_summary.get("selection_count", 0))
    proposal_count = int(calibrated_summary.get("proposal_count", 0))
    recent_selection_count = int(calibrated_summary.get("recent_selection_count", 0))
    feasible_entry_count = int(calibrated_summary.get("feasible_entry_count", 0))
    feasible_preservation_count = int(calibrated_summary.get("feasible_preservation_count", 0))
    has_feasible_credit = feasible_entry_count > 0 or feasible_preservation_count > 0
    support_count = max(selection_count, proposal_count, recent_selection_count)
    evidence_level = (
        "feasible_credit"
        if has_feasible_credit
        else "supported"
        if support_count >= _PREFEASIBLE_MIN_SUPPORTED_SELECTIONS
        else "limited"
    )
    calibrated_summary["evidence_level"] = evidence_level
    if evidence_level == "limited":
        calibrated_summary.pop("avg_total_violation_delta", None)
        calibrated_summary.pop("avg_near_feasible_violation_delta", None)
        calibrated_summary.pop("recent_helpful_regimes", None)
        calibrated_summary.pop("recent_harmful_regimes", None)
        calibrated_summary.pop("recent_entry_helpful_regimes", None)
    return calibrated_summary


def _project_candidate_annotation(
    annotation: Mapping[str, Any],
    *,
    post_feasible_active: bool,
) -> dict[str, Any]:
    projected = {
        key: annotation[key]
        for key in _CANDIDATE_ANNOTATION_PROMPT_KEYS
        if key in annotation
    }
    route_budget_state = annotation.get("route_budget_state")
    if isinstance(route_budget_state, Mapping) and "cooldown_active" in route_budget_state:
        projected["route_cooldown_active"] = bool(route_budget_state["cooldown_active"])
    expand_budget_state = annotation.get("expand_budget_state")
    if isinstance(expand_budget_state, Mapping):
        for key in (
            "expand_budget_status",
            "recent_expand_frontier_add_count",
            "recent_expand_feasible_preservation_count",
            "recent_expand_feasible_regression_count",
        ):
            if key in expand_budget_state:
                projected[key] = expand_budget_state[key]
    if post_feasible_active:
        projected.pop("prefeasible_role", None)
        for key in (
            "operator_family",
            "evidence_level",
            "entry_evidence_level",
            "feasible_entry_count",
            "feasible_preservation_count",
            "feasible_regression_count",
            "pareto_contribution_count",
            "dominant_violation_relief_count",
            "recent_expand_frontier_add_count",
            "recent_expand_feasible_preservation_count",
            "recent_expand_feasible_regression_count",
        ):
            projected.pop(key, None)
        if projected.get("route_cooldown_active") is False:
            projected.pop("route_cooldown_active", None)
        for key in ("exposure_priority", "exposure_status"):
            if annotation.get(key):
                projected[key] = annotation[key]
        return projected
    projected.pop("post_feasible_role", None)
    return projected


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _merge_phase_fallbacks(original_phase: str, existing_fallbacks: Sequence[str]) -> list[str]:
    merged: list[str] = []
    for phase in (original_phase, *existing_fallbacks):
        normalized_phase = str(phase).strip()
        if normalized_phase and normalized_phase not in merged:
            merged.append(normalized_phase)
    return merged
