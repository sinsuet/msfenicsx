"""Compact domain-grounded controller-state summaries for the L1 controller."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from optimizers.operator_pool.operators import get_operator_behavior_profile

_RECENT_FRONTIER_WINDOW = 4


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


def _counts_toward_optimizer_progress(record: Mapping[str, Any]) -> bool:
    return str(record.get("source", "")).strip().lower() != "baseline"


def _optimizer_progress_history(history: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [row for row in history if _counts_toward_optimizer_progress(row)]


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


def _metric_from_record(record: Mapping[str, Any] | None, metric_key: str) -> float | None:
    if record is None:
        return None
    evaluation_report = record.get("evaluation_report", {})
    if isinstance(evaluation_report, Mapping):
        metric_values = evaluation_report.get("metric_values", {})
        if isinstance(metric_values, Mapping) and metric_key in metric_values:
            return float(metric_values[metric_key])
    objective_values = record.get("objective_values", {})
    if not isinstance(objective_values, Mapping):
        objective_values = {}
    metric_name = metric_key.lower()
    if metric_name == "summary.temperature_max":
        for objective_id, value in objective_values.items():
            normalized = str(objective_id).lower()
            if "peak_temperature" in normalized or "temperature_max" in normalized:
                return float(value)
    if metric_name == "summary.temperature_gradient_rms":
        for objective_id, value in objective_values.items():
            normalized = str(objective_id).lower()
            if "temperature_gradient_rms" in normalized or "gradient_rms" in normalized:
                return float(value)
    if metric_name == "case.total_radiator_span":
        return _sink_span_from_record(record)
    return None


def _sink_span_from_decision_vector(decision_vector: Mapping[str, Any] | None) -> float | None:
    if not isinstance(decision_vector, Mapping):
        return None
    if "sink_start" in decision_vector and "sink_end" in decision_vector:
        return float(decision_vector["sink_end"]) - float(decision_vector["sink_start"])
    start_key = None
    end_key = None
    for key in decision_vector:
        normalized = str(key).lower()
        if start_key is None and normalized.endswith("start"):
            start_key = str(key)
        if end_key is None and normalized.endswith("end"):
            end_key = str(key)
    if start_key is None or end_key is None:
        return None
    return float(decision_vector[end_key]) - float(decision_vector[start_key])


def _sink_span_from_record(record: Mapping[str, Any] | None) -> float | None:
    if record is None:
        return None
    return _sink_span_from_decision_vector(record.get("decision_vector"))


def _reference_record_for_run_state(history: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    reference_history = _optimizer_progress_history(history)
    if not reference_history:
        reference_history = list(history)
    feasible_rows = [row for row in reference_history if bool(row.get("feasible", False))]
    if feasible_rows:
        return min(feasible_rows, key=lambda row: objective_score(row.get("objective_values")))
    if reference_history:
        return min(reference_history, key=total_violation)
    return None


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


def dominant_violation_family(record: Mapping[str, Any] | None) -> str | None:
    dominant = dominant_violation(record)
    if dominant is None:
        return None
    constraint_id = dominant.get("constraint_id")
    if constraint_id is None:
        return None
    return classify_constraint_family(str(constraint_id))


def classify_constraint_family(constraint_id: str | None) -> str:
    normalized = "" if constraint_id is None else str(constraint_id).lower()
    if any(token in normalized for token in ("sink", "radiator", "span", "budget")):
        return "sink_budget"
    if any(token in normalized for token in ("temperature", "thermal", "peak", "gradient", "hotspot")):
        return "thermal_limit"
    if any(token in normalized for token in ("overlap", "spacing", "geometry", "layout")):
        return "layout_spacing"
    return "mixed"


def family_violation_total(
    record: Mapping[str, Any] | None,
    family: str | None,
) -> float:
    if record is None or not family:
        return 0.0
    constraint_values = record.get("constraint_values", {})
    if not isinstance(constraint_values, Mapping):
        return 0.0
    return float(
        sum(
            max(0.0, float(violation))
            for constraint_id, violation in constraint_values.items()
            if classify_constraint_family(str(constraint_id)) == str(family)
        )
    )


def objective_score(objective_values: Mapping[str, Any] | None) -> float:
    if not objective_values:
        return float("inf")
    score = 0.0
    for objective_id, value in objective_values.items():
        numeric = float(value)
        objective_name = str(objective_id).lower()
        score += -numeric if "maximize" in objective_name else numeric
    return float(score)


def objective_vector(record: Mapping[str, Any] | None) -> tuple[float, ...] | None:
    if record is None:
        return None
    objective_values = record.get("objective_values", {})
    if not isinstance(objective_values, Mapping) or not objective_values:
        return None
    normalized_items: list[tuple[str, float]] = []
    for objective_id, value in objective_values.items():
        objective_name = str(objective_id).lower()
        numeric_value = float(value)
        minimized_value = -numeric_value if "maximize" in objective_name else numeric_value
        normalized_items.append((str(objective_id), minimized_value))
    normalized_items.sort(key=lambda item: item[0])
    return tuple(value for _, value in normalized_items)


def dominates_objectives(left: Sequence[float], right: Sequence[float]) -> bool:
    return all(lv <= rv for lv, rv in zip(left, right, strict=True)) and any(
        lv < rv for lv, rv in zip(left, right, strict=True)
    )


def is_frontier_add_record(
    record: Mapping[str, Any] | None,
    prior_feasible_records: Sequence[Mapping[str, Any]],
) -> bool:
    candidate_vector = objective_vector(record)
    if candidate_vector is None:
        return False
    for prior_record in prior_feasible_records:
        prior_vector = objective_vector(prior_record)
        if prior_vector is None:
            continue
        if prior_vector == candidate_vector:
            return False
        if dominates_objectives(prior_vector, candidate_vector):
            return False
    return True


def build_frontier_summary(
    history: Sequence[Mapping[str, Any]],
    *,
    recent_window: int = _RECENT_FRONTIER_WINDOW,
) -> dict[str, Any]:
    progress_history = _optimizer_progress_history(history)
    if not progress_history:
        return {
            "pareto_size": 0,
            "recent_frontier_add_count": 0,
            "evaluations_since_frontier_add": None,
            "recent_feasible_regression_count": 0,
            "recent_feasible_preservation_count": 0,
            "recent_frontier_stagnation_count": 0,
            "frontier_add_evaluation_indices": [],
            "feasible_regression_evaluation_indices": [],
            "feasible_preservation_evaluation_indices": [],
        }

    ordered_history = sorted(progress_history, key=lambda row: int(row.get("evaluation_index", 0)))
    feasible_rows = [dict(row) for row in ordered_history if bool(row.get("feasible", False))]
    first_feasible_eval = (
        None
        if not feasible_rows
        else min(int(row.get("evaluation_index", 0)) for row in feasible_rows)
    )
    prior_feasible_records: list[Mapping[str, Any]] = []
    frontier_add_evaluation_indices: list[int] = []
    feasible_regression_evaluation_indices: list[int] = []
    feasible_preservation_evaluation_indices: list[int] = []
    for row in ordered_history:
        evaluation_index = int(row.get("evaluation_index", 0))
        feasible = bool(row.get("feasible", False))
        if first_feasible_eval is not None and evaluation_index >= first_feasible_eval:
            if feasible:
                if is_frontier_add_record(row, prior_feasible_records):
                    frontier_add_evaluation_indices.append(evaluation_index)
                else:
                    feasible_preservation_evaluation_indices.append(evaluation_index)
            else:
                feasible_regression_evaluation_indices.append(evaluation_index)
        if feasible:
            prior_feasible_records.append(dict(row))

    latest_completed_eval = int(ordered_history[-1].get("evaluation_index", 0))
    recent_rows = ordered_history[-max(1, int(recent_window)) :]
    recent_evaluation_indices = {int(row.get("evaluation_index", 0)) for row in recent_rows}
    last_frontier_add_eval = (
        None if not frontier_add_evaluation_indices else frontier_add_evaluation_indices[-1]
    )
    current_pareto_size = 0
    for candidate_row in feasible_rows:
        candidate_vector = objective_vector(candidate_row)
        if candidate_vector is None:
            continue
        dominated = False
        for incumbent_row in feasible_rows:
            if candidate_row is incumbent_row:
                continue
            incumbent_vector = objective_vector(incumbent_row)
            if incumbent_vector is None:
                continue
            if dominates_objectives(incumbent_vector, candidate_vector):
                dominated = True
                break
        if not dominated:
            current_pareto_size += 1
    return {
        "pareto_size": int(current_pareto_size),
        "recent_frontier_add_count": sum(
            1 for evaluation_index in frontier_add_evaluation_indices if evaluation_index in recent_evaluation_indices
        ),
        "evaluations_since_frontier_add": (
            None
            if last_frontier_add_eval is None
            else max(0, latest_completed_eval - int(last_frontier_add_eval))
        ),
        "recent_feasible_regression_count": sum(
            1
            for evaluation_index in feasible_regression_evaluation_indices
            if evaluation_index in recent_evaluation_indices
        ),
        "recent_feasible_preservation_count": sum(
            1
            for evaluation_index in feasible_preservation_evaluation_indices
            if evaluation_index in recent_evaluation_indices
        ),
        "recent_frontier_stagnation_count": (
            0
            if last_frontier_add_eval is None
            else max(0, latest_completed_eval - int(last_frontier_add_eval))
        ),
        "frontier_add_evaluation_indices": list(frontier_add_evaluation_indices),
        "feasible_regression_evaluation_indices": list(feasible_regression_evaluation_indices),
        "feasible_preservation_evaluation_indices": list(feasible_preservation_evaluation_indices),
    }


def summarize_record(record: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if record is None:
        return None
    summary = {
        "evaluation_index": int(record.get("evaluation_index", -1)),
        "feasible": bool(record.get("feasible", False)),
        "total_violation": total_violation(record),
        "dominant_violation": dominant_violation(record),
    }
    sink_span = _sink_span_from_record(record)
    if sink_span is not None:
        summary["sink_span"] = float(sink_span)
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
    sink_budget_limit: float | None = None,
) -> dict[str, Any]:
    progress_history = _optimizer_progress_history(history)
    feasible_evaluations = [row for row in progress_history if bool(row.get("feasible", False))]
    evaluations_used = max(0, int(evaluation_index) - 1)
    run_state = {
        "generation_index": int(generation_index),
        "decision_index": None if decision_index is None else int(decision_index),
        "evaluations_used": evaluations_used,
        "evaluations_remaining": (
            None
            if total_evaluation_budget is None
            else max(0, int(total_evaluation_budget) - evaluations_used)
        ),
        "feasible_rate": (
            0.0 if not progress_history else len(feasible_evaluations) / float(len(progress_history))
        ),
        "first_feasible_eval": (
            None
            if not feasible_evaluations
            else int(min(int(row.get("evaluation_index", 0)) for row in feasible_evaluations))
        ),
    }
    reference_record = _reference_record_for_run_state(history)
    peak_temperature = _metric_from_record(reference_record, "summary.temperature_max")
    if peak_temperature is not None:
        run_state["peak_temperature"] = float(peak_temperature)
    temperature_gradient_rms = _metric_from_record(reference_record, "summary.temperature_gradient_rms")
    if temperature_gradient_rms is not None:
        run_state["temperature_gradient_rms"] = float(temperature_gradient_rms)
    sink_span = _metric_from_record(reference_record, "case.total_radiator_span")
    if sink_span is not None:
        run_state["sink_span"] = float(sink_span)
        if sink_budget_limit is not None and float(sink_budget_limit) > 0.0:
            run_state["sink_budget_utilization"] = float(sink_span) / float(sink_budget_limit)
    return run_state


def build_progress_state(
    *,
    history: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    progress_history = _optimizer_progress_history(history)
    if not progress_history:
        return {
            "phase": "cold_start",
            "first_feasible_found": False,
            "evaluations_since_first_feasible": None,
            "recent_no_progress_count": 0,
            "last_progress_eval": None,
            "recent_best_near_feasible_improvement": 0.0,
            "recent_best_feasible_improvement": 0.0,
            "prefeasible_mode": "diversify",
            "evaluations_since_near_feasible_improvement": None,
            "recent_dominant_violation_family": None,
            "recent_dominant_violation_persistence_count": 0,
            "recent_frontier_stagnation_count": 0,
            "post_feasible_mode": None,
        }

    ordered_history = sorted(progress_history, key=lambda row: int(row.get("evaluation_index", 0)))
    frontier_summary = build_frontier_summary(ordered_history)
    latest_completed_eval = int(ordered_history[-1].get("evaluation_index", 0))
    first_feasible_eval: int | None = None
    last_progress_eval: int | None = None
    best_near_feasible_violation = float("inf")
    best_feasible_score = float("inf")
    recent_best_near_feasible_improvement = 0.0
    recent_best_feasible_improvement = 0.0
    last_near_feasible_improvement_eval: int | None = None

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
            last_near_feasible_improvement_eval = row_eval
            if first_feasible_eval is None:
                last_progress_eval = row_eval

    recent_dominant_violation_family: str | None = None
    recent_dominant_violation_persistence_count = 0
    for row in reversed(ordered_history):
        if bool(row.get("feasible", False)):
            continue
        family = dominant_violation_family(row)
        if family is None:
            continue
        if recent_dominant_violation_family is None:
            recent_dominant_violation_family = family
        if family != recent_dominant_violation_family:
            break
        recent_dominant_violation_persistence_count += 1

    first_feasible_found = first_feasible_eval is not None
    if last_progress_eval is None:
        last_progress_eval = first_feasible_eval if first_feasible_eval is not None else latest_completed_eval
    recent_no_progress_count = max(0, latest_completed_eval - int(last_progress_eval))
    evaluations_since_near_feasible_improvement = (
        None
        if last_near_feasible_improvement_eval is None
        else max(0, latest_completed_eval - int(last_near_feasible_improvement_eval))
    )
    prefeasible_mode = (
        "convert"
        if not first_feasible_found and best_near_feasible_violation <= 1.0
        else "diversify"
    )
    if first_feasible_found:
        phase = "post_feasible_progress" if recent_no_progress_count == 0 else "post_feasible_stagnation"
        if int(frontier_summary["recent_feasible_regression_count"]) > 0:
            post_feasible_mode = "recover"
        elif int(frontier_summary["recent_frontier_stagnation_count"]) >= 2:
            post_feasible_mode = "expand"
        else:
            post_feasible_mode = "preserve"
    else:
        phase = "prefeasible_progress" if recent_no_progress_count == 0 else "prefeasible_stagnation"
        post_feasible_mode = None
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
        "prefeasible_mode": prefeasible_mode,
        "evaluations_since_near_feasible_improvement": evaluations_since_near_feasible_improvement,
        "recent_dominant_violation_family": recent_dominant_violation_family,
        "recent_dominant_violation_persistence_count": int(recent_dominant_violation_persistence_count),
        "recent_frontier_stagnation_count": int(frontier_summary["recent_frontier_stagnation_count"]),
        "post_feasible_mode": post_feasible_mode,
    }


def build_prefeasible_reset_summary(
    recent_decisions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    stable_family_mix: Counter[str] = Counter()
    reset_row_count = 0
    for row in recent_decisions:
        policy_phase = str(row.get("policy_phase", "")).strip()
        if not policy_phase.startswith("prefeasible"):
            continue
        reason_codes = row.get("reason_codes", [])
        if not isinstance(reason_codes, Sequence) or isinstance(reason_codes, (str, bytes)):
            reason_codes = [] if not reason_codes else [str(reason_codes)]
        reset_active = bool(row.get("policy_reset_active", False)) or "prefeasible_forced_reset" in {
            str(code) for code in reason_codes
        }
        if not reset_active:
            continue
        operator_id = str(row.get("selected_operator_id", "")).strip()
        if not operator_id:
            continue
        try:
            profile = get_operator_behavior_profile(operator_id)
        except KeyError:
            continue
        if profile.exploration_class != "stable":
            continue
        reset_row_count += 1
        stable_family_mix[profile.family] += 1
    return {
        "prefeasible_reset_window_count": int(reset_row_count),
        "prefeasible_recent_stable_family_mix": dict(stable_family_mix),
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
    progress_history = _optimizer_progress_history(history)
    archive_history = progress_history or list(history)
    frontier_summary = build_frontier_summary(archive_history)
    feasible_rows = [dict(row) for row in archive_history if bool(row.get("feasible", False))]
    infeasible_rows = [dict(row) for row in archive_history if not bool(row.get("feasible", False))]
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
        "pareto_size": int(frontier_summary["pareto_size"]),
        "recent_frontier_add_count": int(frontier_summary["recent_frontier_add_count"]),
        "evaluations_since_frontier_add": frontier_summary["evaluations_since_frontier_add"],
        "recent_feasible_regression_count": int(frontier_summary["recent_feasible_regression_count"]),
        "recent_feasible_preservation_count": int(frontier_summary["recent_feasible_preservation_count"]),
    }


def build_domain_regime(
    *,
    parent_state: Mapping[str, Any],
    archive_state: Mapping[str, Any],
    sink_budget_limit: float | None = None,
) -> dict[str, Any]:
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
    sink_span = None
    for archive_key in ("best_feasible", "best_near_feasible"):
        candidate = archive_state.get(archive_key)
        if isinstance(candidate, Mapping) and candidate.get("sink_span") is not None:
            sink_span = float(candidate["sink_span"])
            break
    if sink_span is None:
        for parent in parents:
            sink_span = _sink_span_from_decision_vector(parent.get("decision_vector"))
            if sink_span is not None:
                break
    domain_regime = {
        "phase": phase,
        "dominant_constraint_family": classify_constraint_family(dominant_constraint_id),
    }
    if sink_span is not None and sink_budget_limit is not None and float(sink_budget_limit) > 0.0:
        domain_regime["sink_budget_utilization"] = float(sink_span) / float(sink_budget_limit)
    return domain_regime


def outcome_regime(
    *,
    parent_records: Sequence[Mapping[str, Any]],
    child_record: Mapping[str, Any] | None,
) -> dict[str, Any]:
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
