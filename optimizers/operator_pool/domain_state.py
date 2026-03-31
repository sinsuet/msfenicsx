"""Compact domain-grounded controller-state summaries for the L1 controller."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np


def vector_key(values: Sequence[float], *, ndigits: int = 12) -> tuple[float, ...]:
    return tuple(round(float(value), ndigits) for value in values)


def decision_vector_from_values(
    values: Sequence[float],
    design_variable_ids: Sequence[str] | None,
) -> dict[str, float]:
    if design_variable_ids is None:
        return {f"x{index}": float(value) for index, value in enumerate(values)}
    return {
        str(variable_id): float(value)
        for variable_id, value in zip(design_variable_ids, values, strict=True)
    }


def build_history_lookup(
    history: Sequence[Mapping[str, Any]],
    design_variable_ids: Sequence[str] | None,
) -> dict[tuple[float, ...], dict[str, Any]]:
    if design_variable_ids is None:
        return {}
    lookup: dict[tuple[float, ...], dict[str, Any]] = {}
    for row in history:
        decision_vector = row.get("decision_vector")
        if not isinstance(decision_vector, Mapping):
            continue
        try:
            values = [float(decision_vector[variable_id]) for variable_id in design_variable_ids]
        except KeyError:
            continue
        lookup[vector_key(values)] = dict(row)
    return lookup


def total_violation(record: Mapping[str, Any] | None) -> float:
    if record is None:
        return 0.0
    constraint_values = record.get("constraint_values", {})
    if not isinstance(constraint_values, Mapping):
        return 0.0
    return float(sum(max(0.0, float(value)) for value in constraint_values.values()))


def dominant_violation(record: Mapping[str, Any] | None) -> dict[str, float] | None:
    if record is None:
        return None
    constraint_values = record.get("constraint_values", {})
    if not isinstance(constraint_values, Mapping):
        return None
    active = [
        (str(constraint_id), float(violation))
        for constraint_id, violation in constraint_values.items()
        if float(violation) > 0.0
    ]
    if not active:
        return None
    constraint_id, violation = max(active, key=lambda item: item[1])
    return {
        "constraint_id": constraint_id,
        "violation": float(violation),
    }


def classify_constraint_family(constraint_id: str | None) -> str:
    normalized = "" if constraint_id is None else str(constraint_id).lower()
    if any(token in normalized for token in ("spread", "overlap", "spacing", "radiator", "geometry")):
        return "geometry_dominant"
    if any(token in normalized for token in ("cold", "battery")):
        return "cold_dominant"
    if any(token in normalized for token in ("hot", "processor", "pa")):
        return "hot_dominant"
    return "mixed"


def objective_score(objective_values: Mapping[str, Any] | None) -> float:
    if not objective_values:
        return float("inf")
    score = 0.0
    for objective_id, value in objective_values.items():
        numeric = float(value)
        objective_name = str(objective_id).lower()
        score += -numeric if "maximize" in objective_name else numeric
    return float(score)


def summarize_record(record: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if record is None:
        return None
    summary = {
        "evaluation_index": int(record.get("evaluation_index", -1)),
        "feasible": bool(record.get("feasible", False)),
        "total_violation": total_violation(record),
        "dominant_violation": dominant_violation(record),
    }
    objective_values = record.get("objective_values", {})
    if summary["feasible"] and isinstance(objective_values, Mapping):
        summary["objective_summary"] = {
            str(objective_id): float(value)
            for objective_id, value in objective_values.items()
        }
    return summary


def build_run_state(
    *,
    generation_index: int,
    evaluation_index: int,
    history: Sequence[Mapping[str, Any]],
    decision_index: int | None,
    total_evaluation_budget: int | None,
) -> dict[str, Any]:
    feasible_evaluations = [row for row in history if bool(row.get("feasible", False))]
    evaluations_used = max(0, int(evaluation_index) - 1)
    return {
        "generation_index": int(generation_index),
        "decision_index": None if decision_index is None else int(decision_index),
        "evaluations_used": evaluations_used,
        "evaluations_remaining": (
            None
            if total_evaluation_budget is None
            else max(0, int(total_evaluation_budget) - evaluations_used)
        ),
        "feasible_rate": (0.0 if not history else len(feasible_evaluations) / float(len(history))),
        "first_feasible_eval": (
            None
            if not feasible_evaluations
            else int(min(int(row.get("evaluation_index", 0)) for row in feasible_evaluations))
        ),
    }


def build_progress_state(
    *,
    history: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not history:
        return {
            "phase": "cold_start",
            "first_feasible_found": False,
            "evaluations_since_first_feasible": None,
            "recent_no_progress_count": 0,
            "last_progress_eval": None,
            "recent_best_near_feasible_improvement": 0.0,
            "recent_best_feasible_improvement": 0.0,
        }

    ordered_history = sorted(history, key=lambda row: int(row.get("evaluation_index", 0)))
    latest_completed_eval = int(ordered_history[-1].get("evaluation_index", 0))
    first_feasible_eval: int | None = None
    last_progress_eval: int | None = None
    best_near_feasible_violation = float("inf")
    best_feasible_score = float("inf")
    recent_best_near_feasible_improvement = 0.0
    recent_best_feasible_improvement = 0.0

    for row in ordered_history:
        row_eval = int(row.get("evaluation_index", 0))
        if bool(row.get("feasible", False)):
            if first_feasible_eval is None:
                first_feasible_eval = row_eval
            score = objective_score(row.get("objective_values"))
            if score < best_feasible_score:
                if best_feasible_score < float("inf"):
                    recent_best_feasible_improvement = float(score - best_feasible_score)
                best_feasible_score = score
                last_progress_eval = row_eval
            continue

        violation = total_violation(row)
        if violation < best_near_feasible_violation:
            if best_near_feasible_violation < float("inf"):
                recent_best_near_feasible_improvement = float(violation - best_near_feasible_violation)
            best_near_feasible_violation = violation
            if first_feasible_eval is None:
                last_progress_eval = row_eval

    first_feasible_found = first_feasible_eval is not None
    if last_progress_eval is None:
        last_progress_eval = first_feasible_eval if first_feasible_eval is not None else latest_completed_eval
    recent_no_progress_count = max(0, latest_completed_eval - int(last_progress_eval))
    if first_feasible_found:
        phase = "post_feasible_progress" if recent_no_progress_count == 0 else "post_feasible_stagnation"
    else:
        phase = "prefeasible_progress" if recent_no_progress_count == 0 else "prefeasible_stagnation"
    return {
        "phase": phase,
        "first_feasible_found": first_feasible_found,
        "evaluations_since_first_feasible": (
            None if first_feasible_eval is None else max(0, latest_completed_eval - first_feasible_eval)
        ),
        "recent_no_progress_count": recent_no_progress_count,
        "last_progress_eval": int(last_progress_eval),
        "recent_best_near_feasible_improvement": float(recent_best_near_feasible_improvement),
        "recent_best_feasible_improvement": float(recent_best_feasible_improvement),
    }


def build_parent_state(
    *,
    parent_vectors: Sequence[Sequence[float]],
    design_variable_ids: Sequence[str] | None,
    history_lookup: Mapping[tuple[float, ...], Mapping[str, Any]],
    parent_indices: Sequence[int] | None,
) -> dict[str, Any]:
    parents: list[dict[str, Any]] = []
    for vector in parent_vectors:
        key = vector_key(vector)
        matched_record = history_lookup.get(key)
        parent_summary = {
            "decision_vector": decision_vector_from_values(vector, design_variable_ids),
            "feasible": None if matched_record is None else bool(matched_record.get("feasible", False)),
            "total_violation": None if matched_record is None else total_violation(matched_record),
            "dominant_violation": dominant_violation(matched_record),
            "evaluation_index": None if matched_record is None else int(matched_record.get("evaluation_index", -1)),
        }
        objective_values = None if matched_record is None else matched_record.get("objective_values")
        if matched_record is not None and bool(matched_record.get("feasible", False)) and isinstance(objective_values, Mapping):
            parent_summary["objective_summary"] = {
                str(objective_id): float(value)
                for objective_id, value in objective_values.items()
            }
        parents.append(parent_summary)
    return {
        "parent_indices": [] if parent_indices is None else [int(index) for index in parent_indices],
        "parents": parents,
    }


def build_archive_state(history: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    feasible_rows = [dict(row) for row in history if bool(row.get("feasible", False))]
    infeasible_rows = [dict(row) for row in history if not bool(row.get("feasible", False))]
    best_feasible = None
    if feasible_rows:
        best_feasible = summarize_record(min(feasible_rows, key=lambda row: objective_score(row.get("objective_values"))))
    best_near_feasible = None
    if infeasible_rows:
        best_near_feasible = summarize_record(min(infeasible_rows, key=total_violation))
    return {
        "best_feasible": best_feasible,
        "best_near_feasible": best_near_feasible,
        "feasible_count": len(feasible_rows),
        "infeasible_count": len(infeasible_rows),
    }


def build_domain_regime(
    *,
    parent_state: Mapping[str, Any],
    archive_state: Mapping[str, Any],
) -> dict[str, str]:
    parents = list(parent_state.get("parents", []))
    parent_feasible = [bool(parent.get("feasible", False)) for parent in parents if parent.get("feasible") is not None]
    parent_violations = [
        float(parent.get("total_violation", 0.0))
        for parent in parents
        if parent.get("total_violation") is not None
    ]
    if any(parent_feasible):
        phase = "feasible_refine"
    elif parent_violations and min(parent_violations) <= 1.0:
        phase = "near_feasible"
    else:
        best_near_feasible = archive_state.get("best_near_feasible")
        if isinstance(best_near_feasible, Mapping) and float(best_near_feasible.get("total_violation", float("inf"))) <= 1.0:
            phase = "near_feasible"
        else:
            phase = "far_infeasible"

    dominant_constraint_id = None
    for parent in parents:
        dominant = parent.get("dominant_violation")
        if isinstance(dominant, Mapping) and dominant.get("constraint_id"):
            dominant_constraint_id = str(dominant["constraint_id"])
            break
    if dominant_constraint_id is None:
        best_near_feasible = archive_state.get("best_near_feasible")
        if isinstance(best_near_feasible, Mapping):
            dominant = best_near_feasible.get("dominant_violation")
            if isinstance(dominant, Mapping) and dominant.get("constraint_id"):
                dominant_constraint_id = str(dominant["constraint_id"])
    return {
        "phase": phase,
        "dominant_constraint_family": classify_constraint_family(dominant_constraint_id),
    }


def outcome_regime(
    *,
    parent_records: Sequence[Mapping[str, Any]],
    child_record: Mapping[str, Any] | None,
) -> dict[str, str]:
    parent_state = {
        "parents": [
            {
                "feasible": bool(record.get("feasible", False)),
                "total_violation": total_violation(record),
                "dominant_violation": dominant_violation(record),
            }
            for record in parent_records
        ]
    }
    archive_state = {
        "best_near_feasible": summarize_record(child_record),
    }
    if child_record is not None and bool(child_record.get("feasible", False)):
        archive_state["best_feasible"] = summarize_record(child_record)
    return build_domain_regime(parent_state=parent_state, archive_state=archive_state)
