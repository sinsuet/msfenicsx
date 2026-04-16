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
        )
    metadata["phase_policy"] = {
        "phase": prompt_phase,
        "reset_active": policy_snapshot.reset_active,
        "reason_codes": list(policy_snapshot.reason_codes),
        "candidate_annotations": {
            operator_id: _project_candidate_annotation(
                annotation,
                post_feasible_active=post_feasible_active,
            )
            for operator_id, annotation in policy_snapshot.candidate_annotations.items()
            if operator_id in candidate_ids
        },
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
) -> dict[str, Any]:
    projected: dict[str, Any] = {}
    run_panel = prompt_panels.get("run_panel")
    if isinstance(run_panel, Mapping):
        projected["run_panel"] = dict(run_panel)
    regime_panel = prompt_panels.get("regime_panel")
    if isinstance(regime_panel, Mapping):
        projected_regime_panel = dict(regime_panel)
        projected_regime_panel["phase"] = prompt_phase
        projected["regime_panel"] = projected_regime_panel
    parent_panel = prompt_panels.get("parent_panel")
    if isinstance(parent_panel, Mapping):
        projected["parent_panel"] = dict(parent_panel)
    spatial_panel = prompt_panels.get("spatial_panel")
    if isinstance(spatial_panel, Mapping):
        projected["spatial_panel"] = dict(spatial_panel)
    retrieval_panel = prompt_panels.get("retrieval_panel")
    if isinstance(retrieval_panel, Mapping):
        projected["retrieval_panel"] = dict(retrieval_panel)
    operator_panel = prompt_panels.get("operator_panel")
    if isinstance(operator_panel, Mapping):
        projected_operator_panel: dict[str, dict[str, Any]] = {}
        for operator_id, summary in operator_panel.items():
            normalized_operator_id = str(operator_id)
            if normalized_operator_id not in candidate_operator_ids or not isinstance(summary, Mapping):
                continue
            projected_summary = dict(summary)
            if not post_feasible_active:
                projected_summary.pop("frontier_evidence", None)
            projected_operator_panel[normalized_operator_id] = projected_summary
        projected["operator_panel"] = projected_operator_panel
    return projected


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
    projected = dict(annotation)
    if post_feasible_active:
        projected.pop("prefeasible_role", None)
        return projected
    projected.pop("post_feasible_role", None)
    return projected
