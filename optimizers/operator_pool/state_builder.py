"""Helpers for building richer controller-facing state payloads."""

from __future__ import annotations

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
from optimizers.operator_pool.reflection import summarize_operator_history
from optimizers.operator_pool.state import ControllerState
from optimizers.operator_pool.trace import ControllerTraceRow, OperatorTraceRow


def _compact_recent_decision(row: ControllerTraceRow) -> dict[str, Any]:
    fallback_used = bool(row.metadata.get("fallback_used", False))
    return {
        "evaluation_index": int(row.evaluation_index),
        "selected_operator_id": row.selected_operator_id,
        "fallback_used": fallback_used,
        "llm_valid": row.controller_id == "llm" and not fallback_used,
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
) -> dict[str, dict[str, Any]]:
    candidate_set = {str(operator_id) for operator_id in candidate_operator_ids}
    operator_panel: dict[str, dict[str, Any]] = {}
    for operator_id, summary in operator_summary.items():
        normalized_operator_id = str(operator_id)
        if normalized_operator_id not in candidate_set or not isinstance(summary, Mapping):
            continue
        operator_panel[normalized_operator_id] = {
            key: summary[key]
            for key in (
                "entry_fit",
                "preserve_fit",
                "expand_fit",
                "recent_regression_risk",
                "frontier_evidence",
                "dominant_violation_relief",
            )
            if key in summary
        }
    return operator_panel


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
    history: Sequence[dict[str, Any]] | None = None,
    recent_window: int = 8,
) -> ControllerState:
    controller_rows = [] if controller_trace is None else list(controller_trace)
    operator_rows = [] if operator_trace is None else list(operator_trace)
    history_rows = [] if history is None else [dict(row) for row in history]
    recent_rows = controller_rows[-recent_window:] if recent_window > 0 else []
    state_metadata = {} if metadata is None else dict(metadata)
    design_variable_ids = state_metadata.get("design_variable_ids")
    if isinstance(design_variable_ids, Sequence) and not isinstance(design_variable_ids, (str, bytes)):
        design_variable_ids = [str(variable_id) for variable_id in design_variable_ids]
    else:
        design_variable_ids = None
    state_metadata["candidate_operator_ids"] = [str(operator_id) for operator_id in candidate_operator_ids]
    state_metadata["recent_decisions"] = [_compact_recent_decision(row) for row in recent_rows]
    operator_summary = summarize_operator_history(
        controller_rows,
        operator_rows,
        recent_window=recent_window,
        history=history_rows,
        design_variable_ids=design_variable_ids,
    )
    state_metadata["operator_summary"] = operator_summary
    state_metadata["recent_operator_counts"] = _build_recent_operator_counts(operator_summary)
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
            build_prefeasible_reset_summary([_policy_recent_decision(row) for row in recent_rows])
        )
        state_metadata["run_state"] = run_state
        state_metadata["parent_state"] = parent_state
        state_metadata["archive_state"] = archive_state
        state_metadata["domain_regime"] = domain_regime
        state_metadata["progress_state"] = progress_state
        state_metadata["search_phase"] = str(state_metadata.get("search_phase") or domain_regime["phase"])
        state_metadata["prompt_panels"] = {
            "run_panel": _build_prompt_run_panel(run_state=run_state, archive_state=archive_state),
            "regime_panel": build_prompt_regime_panel(
                run_state=run_state,
                progress_state=progress_state,
                archive_state=archive_state,
                domain_regime=domain_regime,
            ),
            "parent_panel": build_prompt_parent_panel(parent_state),
            "operator_panel": _build_prompt_operator_panel(
                operator_summary=operator_summary,
                candidate_operator_ids=candidate_operator_ids,
            ),
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
