"""Compact reflection summaries for controller-visible operator history."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from optimizers.operator_pool.domain_state import (
    build_history_lookup,
    classify_constraint_family,
    dominant_violation,
    family_violation_total,
    is_frontier_add_record,
    objective_score,
    outcome_regime,
    sink_budget_bucket,
    total_violation,
    vector_key,
)
from optimizers.operator_pool.operators import get_operator_behavior_profile
from optimizers.operator_pool.trace import ControllerTraceRow, OperatorTraceRow

_SUPPORTED_SELECTION_THRESHOLD = 3


def _is_fallback_selection(row: ControllerTraceRow) -> bool:
    return bool(row.metadata.get("fallback_used", False))


def _is_llm_valid_selection(row: ControllerTraceRow) -> bool:
    return row.controller_id == "llm" and not _is_fallback_selection(row)


def _evidence_level(summary_row: Mapping[str, Any]) -> str:
    feasible_entry_count = int(summary_row.get("feasible_entry_count", 0))
    feasible_preservation_count = int(summary_row.get("feasible_preservation_count", 0))
    pareto_contribution_count = int(summary_row.get("pareto_contribution_count", 0))
    support_count = max(
        int(summary_row.get("selection_count", 0)),
        int(summary_row.get("proposal_count", 0)),
        int(summary_row.get("recent_selection_count", 0)),
    )
    if feasible_entry_count > 0 or feasible_preservation_count > 0 or pareto_contribution_count > 0:
        return "trusted"
    if support_count >= _SUPPORTED_SELECTION_THRESHOLD:
        return "supported"
    return "speculative"


def _entry_fit(summary_row: Mapping[str, Any]) -> str:
    if int(summary_row.get("feasible_entry_count", 0)) > 0:
        return "trusted"
    if int(summary_row.get("dominant_violation_relief_count", 0)) > 0:
        return "supported"
    if int(summary_row.get("near_feasible_improvement_count", 0)) > 0:
        return "supported"
    return "weak"


def _preserve_fit(summary_row: Mapping[str, Any]) -> str:
    feasible_preservation_count = int(summary_row.get("feasible_preservation_count", 0))
    feasible_regression_count = int(summary_row.get("feasible_regression_count", 0))
    if feasible_preservation_count > 0 and feasible_regression_count <= 0:
        return "trusted"
    if feasible_preservation_count > 0:
        return "supported"
    if str(summary_row.get("evidence_level", "")) in {"trusted", "supported"}:
        return "supported"
    return "weak"


def _expand_fit(summary_row: Mapping[str, Any]) -> str:
    if (
        int(summary_row.get("pareto_contribution_count", 0)) > 0
        or int(summary_row.get("frontier_novelty_count", 0)) > 0
        or float(summary_row.get("post_feasible_avg_objective_delta", 0.0)) < 0.0
    ):
        return "trusted"
    if str(summary_row.get("evidence_level", "")) in {"trusted", "supported"}:
        return "supported"
    return "weak"


def _recent_regression_risk(summary_row: Mapping[str, Any]) -> str:
    if (
        int(summary_row.get("feasible_regression_count", 0)) > 0
        or float(summary_row.get("post_feasible_avg_violation_delta", 0.0)) > 0.0
    ):
        return "high"
    if (
        int(summary_row.get("feasible_preservation_count", 0)) <= 0
        and str(summary_row.get("evidence_level", "")) == "speculative"
    ):
        return "medium"
    return "low"


def _frontier_evidence(summary_row: Mapping[str, Any]) -> str:
    if (
        int(summary_row.get("pareto_contribution_count", 0)) > 0
        or int(summary_row.get("frontier_novelty_count", 0)) > 0
        or float(summary_row.get("post_feasible_avg_objective_delta", 0.0)) < 0.0
    ):
        return "positive"
    if max(
        int(summary_row.get("selection_count", 0)),
        int(summary_row.get("proposal_count", 0)),
        int(summary_row.get("recent_selection_count", 0)),
    ) > 0:
        return "limited"
    return "none"


def _dominant_violation_relief(summary_row: Mapping[str, Any]) -> str:
    if int(summary_row.get("dominant_violation_relief_count", 0)) > 0:
        return "supported"
    if int(summary_row.get("near_feasible_improvement_count", 0)) > 0:
        return "limited"
    return "none"


def summarize_operator_history(
    controller_trace: list[ControllerTraceRow],
    operator_trace: list[OperatorTraceRow],
    *,
    recent_window: int,
    history: Sequence[Mapping[str, Any]] | None = None,
    design_variable_ids: Sequence[str] | None = None,
    sink_budget_limit: float | None = None,
) -> dict[str, dict[str, Any]]:
    selected_operator_ids = [row.selected_operator_id for row in controller_trace]
    recent_controller_rows = controller_trace[-recent_window:] if recent_window > 0 else []
    recent_selected_operator_ids = [row.selected_operator_id for row in recent_controller_rows]
    fallback_selected_operator_ids = [row.selected_operator_id for row in controller_trace if _is_fallback_selection(row)]
    llm_valid_selected_operator_ids = [row.selected_operator_id for row in controller_trace if _is_llm_valid_selection(row)]
    recent_fallback_selected_operator_ids = [
        row.selected_operator_id for row in recent_controller_rows if _is_fallback_selection(row)
    ]
    recent_llm_valid_selected_operator_ids = [
        row.selected_operator_id for row in recent_controller_rows if _is_llm_valid_selection(row)
    ]
    recent_effective_rows = [row for row in recent_controller_rows if _is_llm_valid_selection(row)]
    if not recent_effective_rows:
        recent_effective_rows = [row for row in recent_controller_rows if not _is_fallback_selection(row)]
    if not recent_effective_rows:
        recent_effective_rows = list(recent_controller_rows)
    selection_counter = Counter(selected_operator_ids)
    recent_selection_counter = Counter(recent_selected_operator_ids)
    fallback_selection_counter = Counter(fallback_selected_operator_ids)
    llm_valid_selection_counter = Counter(llm_valid_selected_operator_ids)
    recent_fallback_selection_counter = Counter(recent_fallback_selected_operator_ids)
    recent_llm_valid_selection_counter = Counter(recent_llm_valid_selected_operator_ids)
    proposal_counter = Counter(row.operator_id for row in operator_trace)
    recent_family_counter = Counter(
        get_operator_behavior_profile(row.selected_operator_id).family
        for row in recent_effective_rows
    )
    recent_role_counter = Counter(
        get_operator_behavior_profile(row.selected_operator_id).role
        for row in recent_effective_rows
    )
    recent_effective_total = len(recent_effective_rows)
    controller_phase_by_evaluation_index = {
        int(row.evaluation_index): str(
            row.metadata.get("policy_phase") or row.metadata.get("guardrail_policy_phase") or row.phase
        )
        for row in controller_trace
    }
    recent_evaluation_indices = {
        int(row.evaluation_index)
        for row in recent_controller_rows
    }

    operator_ids = sorted(
        set(selection_counter)
        | set(recent_selection_counter)
        | set(fallback_selection_counter)
        | set(llm_valid_selection_counter)
        | set(recent_fallback_selection_counter)
        | set(recent_llm_valid_selection_counter)
        | set(proposal_counter)
    )
    outcome_summary = _summarize_operator_outcomes(
        operator_trace,
        history=history,
        design_variable_ids=design_variable_ids,
        sink_budget_limit=sink_budget_limit,
        controller_phase_by_evaluation_index=controller_phase_by_evaluation_index,
        recent_evaluation_indices=recent_evaluation_indices,
    )
    summary: dict[str, dict[str, Any]] = {}
    for operator_id in operator_ids:
        profile = get_operator_behavior_profile(operator_id)
        operator_summary = {
            "selection_count": int(selection_counter.get(operator_id, 0)),
            "recent_selection_count": int(recent_selection_counter.get(operator_id, 0)),
            "fallback_selection_count": int(fallback_selection_counter.get(operator_id, 0)),
            "llm_valid_selection_count": int(llm_valid_selection_counter.get(operator_id, 0)),
            "recent_fallback_selection_count": int(recent_fallback_selection_counter.get(operator_id, 0)),
            "recent_llm_valid_selection_count": int(recent_llm_valid_selection_counter.get(operator_id, 0)),
            "proposal_count": int(proposal_counter.get(operator_id, 0)),
            "recent_family_share": (
                0.0
                if recent_effective_total <= 0
                else float(recent_family_counter.get(profile.family, 0)) / float(recent_effective_total)
            ),
            "recent_role_share": (
                0.0
                if recent_effective_total <= 0
                else float(recent_role_counter.get(profile.role, 0)) / float(recent_effective_total)
            ),
            **outcome_summary.get(
                operator_id,
                {
                    "feasible_entry_count": 0,
                    "feasible_preservation_count": 0,
                    "feasible_regression_count": 0,
                    "pareto_contribution_count": 0,
                    "frontier_novelty_count": 0,
                    "avg_total_violation_delta": 0.0,
                    "avg_feasible_objective_delta": 0.0,
                    "post_feasible_avg_objective_delta": 0.0,
                    "post_feasible_avg_violation_delta": 0.0,
                    "dominant_violation_relief_count": 0,
                    "near_feasible_improvement_count": 0,
                    "avg_near_feasible_violation_delta": 0.0,
                    "recent_helpful_regimes": [],
                    "recent_harmful_regimes": [],
                    "recent_entry_helpful_regimes": [],
                    "recent_expand_selection_count": 0,
                    "recent_expand_feasible_preservation_count": 0,
                    "recent_expand_feasible_regression_count": 0,
                    "recent_expand_frontier_add_count": 0,
                    "credit_by_regime": {},
                    "regime_episodes": [],
                },
            ),
        }
        operator_summary["operator_family"] = profile.family
        operator_summary["operator_role"] = profile.role
        operator_summary["exploration_class"] = profile.exploration_class
        operator_summary["evidence_level"] = _evidence_level(operator_summary)
        operator_summary["entry_fit"] = _entry_fit(operator_summary)
        operator_summary["preserve_fit"] = _preserve_fit(operator_summary)
        operator_summary["expand_fit"] = _expand_fit(operator_summary)
        operator_summary["recent_regression_risk"] = _recent_regression_risk(operator_summary)
        operator_summary["frontier_evidence"] = _frontier_evidence(operator_summary)
        operator_summary["dominant_violation_relief"] = _dominant_violation_relief(operator_summary)
        summary[operator_id] = operator_summary
    return summary


def _summarize_operator_outcomes(
    operator_trace: Sequence[OperatorTraceRow],
    *,
    history: Sequence[Mapping[str, Any]] | None,
    design_variable_ids: Sequence[str] | None,
    sink_budget_limit: float | None,
    controller_phase_by_evaluation_index: Mapping[int, str],
    recent_evaluation_indices: set[int],
) -> dict[str, dict[str, Any]]:
    if not history or design_variable_ids is None:
        return {}

    history_lookup = build_history_lookup(history, design_variable_ids)
    history_by_evaluation_index = {
        int(row["evaluation_index"]): dict(row)
        for row in history
        if "evaluation_index" in row
    }
    per_operator: dict[str, dict[str, Any]] = {}

    for row in operator_trace:
        operator_summary = per_operator.setdefault(
            row.operator_id,
            {
                "feasible_entry_count": 0,
                "feasible_preservation_count": 0,
                "feasible_regression_count": 0,
                "pareto_contribution_count": 0,
                "frontier_novelty_count": 0,
                "dominant_violation_relief_count": 0,
                "near_feasible_improvement_count": 0,
                "total_violation_deltas": [],
                "feasible_objective_deltas": [],
                "post_feasible_violation_deltas": [],
                "near_feasible_violation_deltas": [],
                "recent_helpful_regimes": [],
                "recent_harmful_regimes": [],
                "recent_entry_helpful_regimes": [],
                "recent_expand_selection_count": 0,
                "recent_expand_feasible_preservation_count": 0,
                "recent_expand_feasible_regression_count": 0,
                "recent_expand_frontier_add_count": 0,
                "credit_by_regime": {},
                "regime_episodes": [],
            },
        )
        child_record = history_by_evaluation_index.get(int(row.evaluation_index))
        if child_record is None:
            continue
        parent_records = [
            history_lookup.get(vector_key(parent_vector))
            for parent_vector in row.parent_vectors
        ]
        parent_records = [record for record in parent_records if record is not None]
        if not parent_records:
            continue

        parent_total_violation = float(np.mean([total_violation(record) for record in parent_records]))
        child_total_violation = total_violation(child_record)
        violation_delta = float(child_total_violation - parent_total_violation)
        operator_summary["total_violation_deltas"].append(violation_delta)

        child_feasible = bool(child_record.get("feasible", False))
        parent_feasible_flags = [bool(record.get("feasible", False)) for record in parent_records]
        if child_feasible and not any(parent_feasible_flags):
            operator_summary["feasible_entry_count"] += 1
        if child_feasible and all(parent_feasible_flags):
            operator_summary["feasible_preservation_count"] += 1
        if not child_feasible and any(parent_feasible_flags):
            operator_summary["feasible_regression_count"] += 1

        prior_feasible_records = [
            dict(record)
            for evaluation_index, record in history_by_evaluation_index.items()
            if evaluation_index < int(row.evaluation_index) and bool(record.get("feasible", False))
        ]
        frontier_add = child_feasible and is_frontier_add_record(child_record, prior_feasible_records)
        if frontier_add:
            operator_summary["pareto_contribution_count"] += 1
            operator_summary["frontier_novelty_count"] += 1

        if child_feasible and any(parent_feasible_flags):
            parent_objective_scores = [
                objective_score(record.get("objective_values"))
                for record in parent_records
                if bool(record.get("feasible", False))
            ]
            if parent_objective_scores:
                operator_summary["feasible_objective_deltas"].append(
                    float(objective_score(child_record.get("objective_values")) - np.mean(parent_objective_scores))
                )
            operator_summary["post_feasible_violation_deltas"].append(violation_delta)
        elif any(parent_feasible_flags):
            operator_summary["post_feasible_violation_deltas"].append(violation_delta)

        controller_phase = str(controller_phase_by_evaluation_index.get(int(row.evaluation_index), "")).strip()
        if (
            int(row.evaluation_index) in recent_evaluation_indices
            and controller_phase == "post_feasible_expand"
        ):
            operator_summary["recent_expand_selection_count"] += 1
            if frontier_add:
                operator_summary["recent_expand_frontier_add_count"] += 1
            elif child_feasible and all(parent_feasible_flags):
                operator_summary["recent_expand_feasible_preservation_count"] += 1
            elif (not child_feasible) and any(parent_feasible_flags):
                operator_summary["recent_expand_feasible_regression_count"] += 1

        regime = outcome_regime(parent_records=parent_records, child_record=child_record)
        regime_tags = [str(regime.get("phase", "")), str(regime.get("dominant_constraint_family", ""))]
        target_key = "recent_helpful_regimes" if violation_delta < 0.0 else "recent_harmful_regimes"
        for regime_tag in regime_tags:
            if regime_tag and regime_tag not in operator_summary[target_key]:
                operator_summary[target_key].append(regime_tag)

        if (
            not any(parent_feasible_flags)
            and not child_feasible
            and regime.get("phase") == "near_feasible"
            and violation_delta < 0.0
        ):
            operator_summary["near_feasible_improvement_count"] += 1
            operator_summary["near_feasible_violation_deltas"].append(violation_delta)
            for regime_tag in regime_tags:
                if regime_tag and regime_tag not in operator_summary["recent_entry_helpful_regimes"]:
                    operator_summary["recent_entry_helpful_regimes"].append(regime_tag)

        parent_dominant_candidates = [
            (str(parent_dominant["constraint_id"]), float(parent_dominant["violation"]))
            for record in parent_records
            for parent_dominant in [dominant_violation(record)]
            if parent_dominant is not None and parent_dominant.get("constraint_id")
        ]
        if parent_dominant_candidates:
            dominant_constraint_id = max(parent_dominant_candidates, key=lambda item: item[1])[0]
            dominant_family = classify_constraint_family(dominant_constraint_id)
            parent_family_violation = float(
                np.mean(
                    [
                        family_violation_total(record, dominant_family)
                        for record in parent_records
                    ]
                )
            )
            child_family_violation = family_violation_total(child_record, dominant_family)
            if child_family_violation < parent_family_violation:
                operator_summary["dominant_violation_relief_count"] += 1
                if dominant_family and dominant_family not in operator_summary["recent_entry_helpful_regimes"]:
                    operator_summary["recent_entry_helpful_regimes"].append(dominant_family)

        credit_phase = _credit_phase(
            parent_feasible_flags=parent_feasible_flags,
            child_feasible=child_feasible,
            frontier_add=frontier_add,
            fallback_phase=str(regime.get("phase", "")),
        )
        credit_family = _credit_family(
            parent_records=parent_records,
            child_record=child_record,
            fallback_family=str(regime.get("dominant_constraint_family", "")),
        )
        credit_sink_bucket = _credit_sink_bucket(
            child_record=child_record,
            parent_records=parent_records,
            sink_budget_limit=sink_budget_limit,
        )
        credit_key = (credit_phase, credit_family, credit_sink_bucket)
        credit_row = operator_summary["credit_by_regime"].setdefault(
            credit_key,
            {
                "frontier_add_count": 0,
                "feasible_preservation_count": 0,
                "feasible_regression_count": 0,
                "objective_deltas": [],
                "violation_deltas": [],
            },
        )
        if frontier_add:
            credit_row["frontier_add_count"] += 1
        if child_feasible and all(parent_feasible_flags):
            credit_row["feasible_preservation_count"] += 1
        if not child_feasible and any(parent_feasible_flags):
            credit_row["feasible_regression_count"] += 1
        if child_feasible and any(parent_feasible_flags):
            parent_objective_scores = [
                objective_score(record.get("objective_values"))
                for record in parent_records
                if bool(record.get("feasible", False))
            ]
            if parent_objective_scores:
                credit_row["objective_deltas"].append(
                    float(objective_score(child_record.get("objective_values")) - np.mean(parent_objective_scores))
                )
        credit_row["violation_deltas"].append(violation_delta)
        operator_summary["regime_episodes"].append(
            {
                "phase": credit_phase,
                "dominant_violation_family": credit_family,
                "sink_budget_bucket": credit_sink_bucket,
                "frontier_add": bool(frontier_add),
                "feasible_preservation": bool(child_feasible and all(parent_feasible_flags)),
                "feasible_regression": bool((not child_feasible) and any(parent_feasible_flags)),
                "avg_total_violation_delta": float(violation_delta),
            }
        )

    return {
        operator_id: {
            "feasible_entry_count": int(summary["feasible_entry_count"]),
            "feasible_preservation_count": int(summary["feasible_preservation_count"]),
            "feasible_regression_count": int(summary["feasible_regression_count"]),
            "pareto_contribution_count": int(summary["pareto_contribution_count"]),
            "frontier_novelty_count": int(summary["frontier_novelty_count"]),
            "dominant_violation_relief_count": int(summary["dominant_violation_relief_count"]),
            "near_feasible_improvement_count": int(summary["near_feasible_improvement_count"]),
            "avg_total_violation_delta": (
                0.0
                if not summary["total_violation_deltas"]
                else float(np.mean(summary["total_violation_deltas"]))
            ),
            "avg_feasible_objective_delta": (
                0.0
                if not summary["feasible_objective_deltas"]
                else float(np.mean(summary["feasible_objective_deltas"]))
            ),
            "post_feasible_avg_objective_delta": (
                0.0
                if not summary["feasible_objective_deltas"]
                else float(np.mean(summary["feasible_objective_deltas"]))
            ),
            "post_feasible_avg_violation_delta": (
                0.0
                if not summary["post_feasible_violation_deltas"]
                else float(np.mean(summary["post_feasible_violation_deltas"]))
            ),
            "avg_near_feasible_violation_delta": (
                0.0
                if not summary["near_feasible_violation_deltas"]
                else float(np.mean(summary["near_feasible_violation_deltas"]))
            ),
            "recent_helpful_regimes": list(summary["recent_helpful_regimes"]),
            "recent_harmful_regimes": list(summary["recent_harmful_regimes"]),
            "recent_entry_helpful_regimes": list(summary["recent_entry_helpful_regimes"]),
            "recent_expand_selection_count": int(summary["recent_expand_selection_count"]),
            "recent_expand_feasible_preservation_count": int(
                summary["recent_expand_feasible_preservation_count"]
            ),
            "recent_expand_feasible_regression_count": int(summary["recent_expand_feasible_regression_count"]),
            "recent_expand_frontier_add_count": int(summary["recent_expand_frontier_add_count"]),
            "credit_by_regime": {
                regime_key: {
                    "frontier_add_count": int(regime_summary["frontier_add_count"]),
                    "feasible_preservation_count": int(regime_summary["feasible_preservation_count"]),
                    "feasible_regression_count": int(regime_summary["feasible_regression_count"]),
                    "avg_objective_delta": (
                        0.0
                        if not regime_summary["objective_deltas"]
                        else float(np.mean(regime_summary["objective_deltas"]))
                    ),
                    "avg_total_violation_delta": (
                        0.0
                        if not regime_summary["violation_deltas"]
                        else float(np.mean(regime_summary["violation_deltas"]))
                    ),
                }
                for regime_key, regime_summary in summary["credit_by_regime"].items()
            },
            "regime_episodes": list(summary["regime_episodes"]),
        }
        for operator_id, summary in per_operator.items()
    }


def _credit_phase(
    *,
    parent_feasible_flags: Sequence[bool],
    child_feasible: bool,
    frontier_add: bool,
    fallback_phase: str,
) -> str:
    if any(parent_feasible_flags):
        if child_feasible and frontier_add:
            return "post_feasible_expand"
        if child_feasible:
            return "post_feasible_preserve"
        return "post_feasible_recover"
    if fallback_phase == "near_feasible":
        return "prefeasible_convert"
    if fallback_phase:
        return str(fallback_phase)
    return "prefeasible_search"


def _credit_family(
    *,
    parent_records: Sequence[Mapping[str, Any]],
    child_record: Mapping[str, Any],
    fallback_family: str,
) -> str:
    parent_dominant_candidates = [
        (str(parent_dominant["constraint_id"]), float(parent_dominant["violation"]))
        for record in parent_records
        for parent_dominant in [dominant_violation(record)]
        if parent_dominant is not None and parent_dominant.get("constraint_id")
    ]
    if parent_dominant_candidates:
        dominant_constraint_id = max(parent_dominant_candidates, key=lambda item: item[1])[0]
        return classify_constraint_family(dominant_constraint_id)
    child_dominant = dominant_violation(child_record)
    if child_dominant is not None and child_dominant.get("constraint_id"):
        return classify_constraint_family(str(child_dominant["constraint_id"]))
    if bool(child_record.get("feasible", False)):
        return "thermal_limit"
    if fallback_family:
        return fallback_family
    return "mixed"


def _record_sink_span(record: Mapping[str, Any] | None) -> float | None:
    if record is None:
        return None
    decision_vector = record.get("decision_vector")
    if not isinstance(decision_vector, Mapping):
        return None
    if "sink_start" in decision_vector and "sink_end" in decision_vector:
        return float(decision_vector["sink_end"]) - float(decision_vector["sink_start"])
    return None


def _credit_sink_bucket(
    *,
    child_record: Mapping[str, Any],
    parent_records: Sequence[Mapping[str, Any]],
    sink_budget_limit: float | None,
) -> str:
    if sink_budget_limit is None or float(sink_budget_limit) <= 0.0:
        return "unknown"
    sink_span = _record_sink_span(child_record)
    if sink_span is None:
        parent_spans = [
            span
            for span in (_record_sink_span(record) for record in parent_records)
            if span is not None
        ]
        sink_span = None if not parent_spans else float(np.mean(parent_spans))
    if sink_span is None:
        return "unknown"
    bucket = sink_budget_bucket(float(sink_span) / float(sink_budget_limit))
    return "unknown" if bucket is None else str(bucket)
