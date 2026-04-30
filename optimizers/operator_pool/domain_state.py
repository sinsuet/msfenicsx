"""Compact domain-grounded controller-state summaries for the L1 controller."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from optimizers.operator_pool.operators import get_operator_behavior_profile

_RECENT_FRONTIER_WINDOW = 4
_OBJECTIVE_STAGNATION_THRESHOLD = 6
_OBJECTIVE_BALANCE_STALENESS_GAP_THRESHOLD = 24
_ENDPOINT_SINK_HEADROOM_UTILIZATION_THRESHOLD = 0.985
_EXPAND_SATURATION_THRESHOLD = 24
_PRESERVE_DWELL_MIN = 3


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


def _pde_attempt_history(history: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [row for row in _optimizer_progress_history(history) if not bool(row.get("solver_skipped", False))]


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


def _component_point_rows(
    decision_vector: Mapping[str, Any] | None,
) -> list[tuple[str, float, float]]:
    if not isinstance(decision_vector, Mapping):
        return []
    x_values: dict[str, float] = {}
    y_values: dict[str, float] = {}
    for key, value in decision_vector.items():
        normalized_key = str(key)
        if normalized_key.endswith("_x"):
            x_values[normalized_key[:-2]] = float(value)
        elif normalized_key.endswith("_y"):
            y_values[normalized_key[:-2]] = float(value)
    component_ids = sorted(set(x_values) & set(y_values))
    return [
        (component_id, float(x_values[component_id]), float(y_values[component_id]))
        for component_id in component_ids
    ]


def _normalize_metric(values: np.ndarray) -> np.ndarray:
    if values.size <= 0:
        return values
    span = float(np.max(values) - np.min(values))
    if span <= 1.0e-12:
        return np.zeros_like(values)
    return (values - float(np.min(values))) / span


def _nearest_neighbor_distances(points: np.ndarray) -> np.ndarray:
    count = int(points.shape[0])
    if count <= 1:
        return np.ones(count, dtype=np.float64)
    distances = np.full(count, np.inf, dtype=np.float64)
    for index in range(count):
        delta = points - points[index]
        norms = np.linalg.norm(delta, axis=1)
        norms[index] = np.inf
        distances[index] = float(np.min(norms))
    distances[~np.isfinite(distances)] = 1.0
    return distances


def _closest_pair_indices(points: np.ndarray) -> tuple[int, int] | None:
    if int(points.shape[0]) < 2:
        return None
    best_pair: tuple[int, int] | None = None
    best_distance = float("inf")
    for left_index in range(points.shape[0]):
        for right_index in range(left_index + 1, points.shape[0]):
            distance = float(np.linalg.norm(points[right_index] - points[left_index]))
            if distance < best_distance:
                best_distance = distance
                best_pair = (left_index, right_index)
    return best_pair


def _sink_interval_from_decision_vector(
    decision_vector: Mapping[str, Any] | None,
) -> tuple[float, float] | None:
    if not isinstance(decision_vector, Mapping):
        return None
    if "sink_start" in decision_vector and "sink_end" in decision_vector:
        return float(decision_vector["sink_start"]), float(decision_vector["sink_end"])
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
    return float(decision_vector[start_key]), float(decision_vector[end_key])


def sink_budget_bucket(utilization: float | None) -> str | None:
    if utilization is None:
        return None
    if float(utilization) >= 0.95:
        return "full_sink"
    if float(utilization) >= 0.75:
        return "tight"
    return "available"


def build_spatial_motif_panel(
    *,
    decision_vector: Mapping[str, Any] | None,
    sink_budget_limit: float | None,
    run_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    component_rows = _component_point_rows(decision_vector)
    if not component_rows:
        return {}
    component_ids = [component_id for component_id, _, _ in component_rows]
    points = np.asarray([[x_value, y_value] for _, x_value, y_value in component_rows], dtype=np.float64)
    sink_interval = _sink_interval_from_decision_vector(decision_vector)
    sink_start = 0.0 if sink_interval is None else float(sink_interval[0])
    sink_end = 1.0 if sink_interval is None else float(sink_interval[1])
    sink_center = 0.5 * (sink_start + sink_end)
    nearest_neighbor_distances = _nearest_neighbor_distances(points)
    crowding = 1.0 / np.maximum(nearest_neighbor_distances, 1.0e-6)
    y_distance_from_sink = float(np.max(points[:, 1])) - points[:, 1]
    x_alignment = np.abs(points[:, 0] - sink_center)
    scores = (
        0.5 * _normalize_metric(crowding)
        + 0.35 * _normalize_metric(y_distance_from_sink)
        + 0.15 * _normalize_metric(x_alignment)
    )
    cluster_size = min(max(2, len(component_rows) // 5 + 1), len(component_rows))
    cluster_indices = np.argsort(scores)[::-1][:cluster_size]
    cluster_points = points[np.asarray(cluster_indices, dtype=np.int64)]
    cluster_centroid = np.mean(cluster_points, axis=0)
    cluster_compactness = float(np.mean(np.linalg.norm(cluster_points - cluster_centroid, axis=1)))
    sink_span = max(0.0, sink_end - sink_start)
    sink_utilization = (
        None
        if sink_budget_limit is None or float(sink_budget_limit) <= 0.0
        else float(sink_span) / float(sink_budget_limit)
    )
    closest_pair = _closest_pair_indices(points)
    nearest_neighbor_gap_min = float(np.min(nearest_neighbor_distances)) if nearest_neighbor_distances.size > 0 else None
    layout_x_span = float(np.max(points[:, 0]) - np.min(points[:, 0]))
    layout_y_span = float(np.max(points[:, 1]) - np.min(points[:, 1]))
    layout_bbox_fill_ratio = float(
        min(1.0, (layout_x_span * layout_y_span) / max(1.0e-6, 0.7 * 0.7))
    )

    if run_state is None:
        frontier_tradeoff_direction = "balanced"
    else:
        peak_temperature = run_state.get("peak_temperature")
        gradient_rms = run_state.get("temperature_gradient_rms")
        if peak_temperature is None or gradient_rms is None:
            frontier_tradeoff_direction = "balanced"
        elif float(peak_temperature) >= 345.0 and float(gradient_rms) <= 9.5:
            frontier_tradeoff_direction = "peak_pressure"
        elif float(gradient_rms) >= 10.5 and float(peak_temperature) <= 345.0:
            frontier_tradeoff_direction = "gradient_pressure"
        else:
            frontier_tradeoff_direction = "balanced"

    spatial_panel: dict[str, Any] = {
        "hotspot_to_sink_offset": float(cluster_centroid[0] - sink_center),
        "hotspot_inside_sink_window": bool(sink_start <= float(cluster_centroid[0]) <= sink_end),
        "hottest_cluster_centroid": {
            "x": float(cluster_centroid[0]),
            "y": float(cluster_centroid[1]),
        },
        "hottest_cluster_compactness": cluster_compactness,
        "nearest_neighbor_gap_min": nearest_neighbor_gap_min,
        "sink_budget_bucket": sink_budget_bucket(sink_utilization),
        "sink_center": float(sink_center),
        "sink_span": float(sink_span),
        "layout_bbox_fill_ratio": layout_bbox_fill_ratio,
        "frontier_tradeoff_direction": frontier_tradeoff_direction,
    }
    if closest_pair is not None and nearest_neighbor_gap_min is not None:
        left_index, right_index = closest_pair
        spatial_panel["local_congestion_pair"] = {
            "component_ids": [component_ids[left_index], component_ids[right_index]],
            "gap": nearest_neighbor_gap_min,
        }
    return spatial_panel


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


def _objective_extreme_records(history: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    reference_history = _optimizer_progress_history(history)
    if not reference_history:
        reference_history = list(history)
    feasible_rows = [row for row in reference_history if bool(row.get("feasible", False))]
    if not feasible_rows:
        return {}
    objective_metrics = {
        "min_peak_temperature": "summary.temperature_max",
        "min_temperature_gradient_rms": "summary.temperature_gradient_rms",
    }
    extremes: dict[str, dict[str, Any]] = {}
    for extreme_id, metric_key in objective_metrics.items():
        candidates = [
            (metric_value, row)
            for row in feasible_rows
            if (metric_value := _metric_from_record(row, metric_key)) is not None
        ]
        if not candidates:
            continue
        metric_value, record = min(candidates, key=lambda item: item[0])
        summary = summarize_record(record)
        if summary is None:
            continue
        summary["metric_key"] = metric_key
        summary["metric_value"] = float(metric_value)
        extremes[extreme_id] = summary
    return extremes


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
    pde_history = _pde_attempt_history(history)
    feasible_evaluations = [row for row in progress_history if bool(row.get("feasible", False))]
    pde_feasible_evaluations = [row for row in pde_history if bool(row.get("feasible", False))]
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
            0.0 if not pde_history else len(pde_feasible_evaluations) / float(len(pde_history))
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
    objective_extremes = _objective_extreme_records(history)
    if objective_extremes:
        run_state["objective_extremes"] = objective_extremes
    return run_state


def _build_objective_stagnation(
    ordered_history: list[Mapping[str, Any]],
    first_feasible_eval: int | None,
    latest_completed_eval: int,
) -> dict[str, dict[str, Any]]:
    """Track per-objective stagnation across feasible evaluations."""
    objective_keys = {
        "temperature_max": "summary.temperature_max",
        "gradient_rms": "summary.temperature_gradient_rms",
    }
    result: dict[str, dict[str, Any]] = {}
    for short_key, metric_key in objective_keys.items():
        best_value: float | None = None
        last_improvement_eval: int | None = None
        for row in ordered_history:
            if not bool(row.get("feasible", False)):
                continue
            if str(row.get("source", "")).strip().lower() == "baseline":
                continue
            eval_index = int(row.get("evaluation_index", 0))
            value = _metric_from_record(row, metric_key)
            if value is None:
                continue
            if best_value is None or value < best_value:
                best_value = value
                last_improvement_eval = eval_index
        if best_value is None or last_improvement_eval is None:
            result[short_key] = {
                "best_value": None,
                "evaluations_since_improvement": None,
                "stagnant": False,
            }
        else:
            evals_since = max(0, latest_completed_eval - last_improvement_eval)
            result[short_key] = {
                "best_value": float(best_value),
                "evaluations_since_improvement": int(evals_since),
                "stagnant": evals_since >= _OBJECTIVE_STAGNATION_THRESHOLD,
            }
    return result


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
            "recent_violation_family_switch_count": 0,
            "stable_preservation_streak": 0,
            "new_dominant_violation_family": False,
            "recent_frontier_stagnation_count": 0,
            "post_feasible_mode": None,
            "recover_pressure_level": "low",
            "recover_exit_ready": False,
            "recover_release_ready": False,
            "preserve_dwell_count": 0,
            "preserve_dwell_remaining": 0,
            "recover_reentry_pressure": "low",
            "diversity_deficit_level": "low",
            "objective_stagnation": _empty_objective_stagnation(),
            "expand_saturation_count": 0,
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
    previous_dominant_violation_family: str | None = None
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
            previous_dominant_violation_family = family
            break
        recent_dominant_violation_persistence_count += 1
    new_dominant_violation_family = previous_dominant_violation_family is not None
    recent_violation_family_switch_count = 0
    recover_pressure_level = "low"
    recover_exit_ready = False
    recover_release_ready = False
    preserve_dwell_count = 0
    preserve_dwell_remaining = 0
    recover_reentry_pressure = "low"
    diversity_deficit_level = "low"

    stable_preservation_evaluation_indices = {
        int(evaluation_index)
        for evaluation_index in frontier_summary["feasible_preservation_evaluation_indices"]
    }
    stable_preservation_streak = 0
    for row in reversed(ordered_history):
        evaluation_index = int(row.get("evaluation_index", 0))
        if evaluation_index not in stable_preservation_evaluation_indices:
            break
        stable_preservation_streak += 1
    trailing_feasible_streak = 0
    for row in reversed(ordered_history):
        evaluation_index = int(row.get("evaluation_index", 0))
        if first_feasible_eval is not None and evaluation_index < int(first_feasible_eval):
            break
        if not bool(row.get("feasible", False)):
            break
        trailing_feasible_streak += 1
    stable_preservation_streak = max(stable_preservation_streak, trailing_feasible_streak)

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
        recent_feasible_regression_count = int(frontier_summary["recent_feasible_regression_count"])
        recent_feasible_preservation_count = int(frontier_summary["recent_feasible_preservation_count"])
        recent_violation_family_switch_count = _recent_violation_family_switch_count(
            ordered_history,
            first_feasible_eval=first_feasible_eval,
        )
        recover_pressure_level = _recover_pressure_level(
            recent_feasible_regression_count=recent_feasible_regression_count,
            recent_feasible_preservation_count=recent_feasible_preservation_count,
            recent_dominant_violation_persistence_count=recent_dominant_violation_persistence_count,
            recent_violation_family_switch_count=recent_violation_family_switch_count,
        )
        recover_reentry_pressure = recover_pressure_level
        regression_surplus = max(0, recent_feasible_regression_count - recent_feasible_preservation_count)
        if int(frontier_summary["pareto_size"]) <= 1:
            diversity_deficit_level = "high"
        elif (
            int(frontier_summary["pareto_size"]) == 2
            and int(frontier_summary["recent_frontier_stagnation_count"]) >= 2
        ):
            diversity_deficit_level = "medium"
        else:
            diversity_deficit_level = "low"
        preserve_dwell_signal = max(
            int(stable_preservation_streak),
            int(recent_feasible_preservation_count),
        )
        recover_release_ready = preserve_dwell_signal > 0 and regression_surplus <= 1
        recover_exit_ready = recover_release_ready
        expand_pressure_active = (
            int(frontier_summary["recent_frontier_stagnation_count"]) >= 2
            and diversity_deficit_level in {"high", "medium"}
            and regression_surplus <= 1
        )
        preserve_dwell_active = (
            preserve_dwell_signal > 0
            and recover_pressure_level != "high"
        )
        if preserve_dwell_active:
            post_feasible_mode = "preserve"
        elif recover_pressure_level != "low" and not expand_pressure_active:
            post_feasible_mode = "recover"
        elif int(frontier_summary["recent_frontier_stagnation_count"]) >= 2:
            post_feasible_mode = "expand"
        else:
            post_feasible_mode = "preserve"
        if post_feasible_mode == "preserve":
            preserve_dwell_count = int(preserve_dwell_signal)
            preserve_dwell_remaining = max(0, _PRESERVE_DWELL_MIN - preserve_dwell_count)
            if (
                preserve_dwell_remaining <= 0
                and int(frontier_summary["recent_frontier_stagnation_count"]) >= 2
                and diversity_deficit_level in {"high", "medium"}
                and regression_surplus <= 1
            ):
                post_feasible_mode = "expand"
    else:
        phase = "prefeasible_progress" if recent_no_progress_count == 0 else "prefeasible_stagnation"
        post_feasible_mode = None
    objective_stagnation = _build_objective_stagnation(
        ordered_history,
        first_feasible_eval=first_feasible_eval,
        latest_completed_eval=latest_completed_eval,
    )

    expand_saturation_count = 0
    if first_feasible_found and post_feasible_mode == "expand":
        last_frontier_add_eval = (
            None
            if not frontier_summary["frontier_add_evaluation_indices"]
            else frontier_summary["frontier_add_evaluation_indices"][-1]
        )
        if last_frontier_add_eval is not None:
            expand_saturation_count = max(0, latest_completed_eval - int(last_frontier_add_eval))
        elif first_feasible_eval is not None:
            expand_saturation_count = max(0, latest_completed_eval - first_feasible_eval)

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
        "recent_violation_family_switch_count": int(recent_violation_family_switch_count),
        "stable_preservation_streak": int(stable_preservation_streak),
        "new_dominant_violation_family": bool(new_dominant_violation_family),
        "recent_frontier_stagnation_count": int(frontier_summary["recent_frontier_stagnation_count"]),
        "post_feasible_mode": post_feasible_mode,
        "recover_pressure_level": str(recover_pressure_level),
        "recover_exit_ready": bool(recover_exit_ready),
        "recover_release_ready": bool(recover_release_ready),
        "preserve_dwell_count": int(preserve_dwell_count),
        "preserve_dwell_remaining": int(preserve_dwell_remaining),
        "recover_reentry_pressure": str(recover_reentry_pressure),
        "diversity_deficit_level": str(diversity_deficit_level),
        "expand_saturation_count": int(expand_saturation_count),
        "objective_stagnation": objective_stagnation,
    }


def _recent_violation_family_switch_count(
    ordered_history: Sequence[Mapping[str, Any]],
    *,
    first_feasible_eval: int | None,
    recent_window: int = _RECENT_FRONTIER_WINDOW,
) -> int:
    if first_feasible_eval is None:
        return 0
    recent_post_feasible_rows = [
        row
        for row in ordered_history
        if int(row.get("evaluation_index", 0)) >= int(first_feasible_eval)
    ][-max(1, int(recent_window)) :]
    recent_infeasible_families = [
        family
        for row in recent_post_feasible_rows
        if not bool(row.get("feasible", False))
        for family in [dominant_violation_family(row)]
        if family is not None
    ]
    if len(recent_infeasible_families) <= 1:
        return 0
    switches = 0
    previous_family = recent_infeasible_families[0]
    for family in recent_infeasible_families[1:]:
        if family != previous_family:
            switches += 1
        previous_family = family
    return int(switches)


def _recover_pressure_level(
    *,
    recent_feasible_regression_count: int,
    recent_feasible_preservation_count: int,
    recent_dominant_violation_persistence_count: int,
    recent_violation_family_switch_count: int,
) -> str:
    pressure_score = 0
    regression_surplus = max(0, int(recent_feasible_regression_count) - int(recent_feasible_preservation_count))
    if regression_surplus >= 2:
        pressure_score += 2
    elif regression_surplus >= 1:
        pressure_score += 1
    if int(recent_dominant_violation_persistence_count) >= 4:
        pressure_score += 2
    elif int(recent_dominant_violation_persistence_count) >= 2:
        pressure_score += 1
    if int(recent_violation_family_switch_count) >= 2:
        pressure_score += 2
    elif int(recent_violation_family_switch_count) >= 1:
        pressure_score += 1
    return _pressure_level(pressure_score)


def _empty_objective_stagnation() -> dict[str, dict[str, Any]]:
    return {
        "temperature_max": {
            "best_value": None,
            "evaluations_since_improvement": None,
            "stagnant": False,
        },
        "gradient_rms": {
            "best_value": None,
            "evaluations_since_improvement": None,
            "stagnant": False,
        },
    }


def _build_objective_stagnation(
    ordered_history: Sequence[Mapping[str, Any]],
    *,
    first_feasible_eval: int | None,
    latest_completed_eval: int,
) -> dict[str, dict[str, Any]]:
    """Track per-objective stagnation across feasible optimizer evaluations."""
    del first_feasible_eval
    objective_keys = {
        "temperature_max": "summary.temperature_max",
        "gradient_rms": "summary.temperature_gradient_rms",
    }
    result = _empty_objective_stagnation()
    for short_key, metric_key in objective_keys.items():
        best_value: float | None = None
        last_improvement_eval: int | None = None
        for row in ordered_history:
            if not bool(row.get("feasible", False)):
                continue
            if str(row.get("source", "")).strip().lower() == "baseline":
                continue
            eval_index = int(row.get("evaluation_index", 0))
            value = _metric_from_record(row, metric_key)
            if value is None:
                continue
            if best_value is None or value < best_value:
                best_value = float(value)
                last_improvement_eval = eval_index
        if best_value is None or last_improvement_eval is None:
            continue
        evals_since = max(0, latest_completed_eval - last_improvement_eval)
        result[short_key] = {
            "best_value": float(best_value),
            "evaluations_since_improvement": int(evals_since),
            "stagnant": evals_since >= _OBJECTIVE_STAGNATION_THRESHOLD,
        }
    return result


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


def _pressure_level(score: int) -> str:
    if score >= 3:
        return "high"
    if score >= 1:
        return "medium"
    return "low"


def build_prompt_phase(
    *,
    run_state: Mapping[str, Any],
    progress_state: Mapping[str, Any],
    domain_regime: Mapping[str, Any],
) -> str:
    first_feasible_eval = run_state.get("first_feasible_eval")
    if first_feasible_eval is None:
        prefeasible_mode = str(progress_state.get("prefeasible_mode", "")).strip()
        dominant_violation_family = str(progress_state.get("recent_dominant_violation_family", "")).strip()
        domain_phase = str(domain_regime.get("phase", "")).strip()
        if prefeasible_mode == "convert" and (domain_phase == "near_feasible" or dominant_violation_family):
            return "prefeasible_convert"
        return "prefeasible_search"
    post_feasible_mode = str(progress_state.get("post_feasible_mode", "")).strip()
    if post_feasible_mode == "recover":
        return "post_feasible_recover"
    if post_feasible_mode == "expand":
        return "post_feasible_expand"
    return "post_feasible_preserve"


def build_prompt_parent_panel(parent_state: Mapping[str, Any]) -> dict[str, Any]:
    parents = [dict(parent) for parent in parent_state.get("parents", []) if isinstance(parent, Mapping)]
    infeasible_parents = [parent for parent in parents if parent.get("feasible") is False]
    feasible_parents = [parent for parent in parents if parent.get("feasible") is True]

    closest_to_feasible_parent = None
    if infeasible_parents:
        closest_to_feasible_parent = min(
            infeasible_parents,
            key=lambda parent: (
                float(parent.get("total_violation", float("inf"))),
                int(parent.get("evaluation_index", 10**9)),
            ),
        )

    strongest_feasible_parent = None
    if feasible_parents:
        strongest_feasible_parent = min(
            feasible_parents,
            key=lambda parent: (
                objective_score(parent.get("objective_summary")),
                int(parent.get("evaluation_index", 10**9)),
            ),
        )

    return {
        "closest_to_feasible_parent": closest_to_feasible_parent,
        "strongest_feasible_parent": strongest_feasible_parent,
    }


def build_prompt_regime_panel(
    *,
    run_state: Mapping[str, Any],
    progress_state: Mapping[str, Any],
    archive_state: Mapping[str, Any],
    domain_regime: Mapping[str, Any],
) -> dict[str, Any]:
    phase = build_prompt_phase(
        run_state=run_state,
        progress_state=progress_state,
        domain_regime=domain_regime,
    )
    dominant_violation_family = str(
        progress_state.get("recent_dominant_violation_family")
        or domain_regime.get("dominant_constraint_family")
        or ""
    ).strip()
    persistence_count = int(progress_state.get("recent_dominant_violation_persistence_count", 0))
    first_feasible_eval = run_state.get("first_feasible_eval")
    recent_feasible_regression_count = int(archive_state.get("recent_feasible_regression_count", 0))
    recent_frontier_stagnation_count = int(progress_state.get("recent_frontier_stagnation_count", 0))
    stable_preservation_streak = int(progress_state.get("stable_preservation_streak", 0))
    new_dominant_violation_family = bool(progress_state.get("new_dominant_violation_family", False))
    recover_exit_ready = progress_state.get("recover_exit_ready")
    recover_release_ready = progress_state.get("recover_release_ready")
    resolved_recover_release_ready = (
        recover_release_ready
        if recover_release_ready is not None
        else recover_exit_ready
    )

    entry_pressure_score = 0
    if first_feasible_eval is None:
        entry_pressure_score = 3 if phase == "prefeasible_convert" else 1
        if persistence_count >= 2:
            entry_pressure_score = max(entry_pressure_score, 3)

    preservation_pressure_score = 0
    if first_feasible_eval is not None:
        preservation_pressure_score = 3 if recent_feasible_regression_count > 0 else 2
        if phase == "post_feasible_expand":
            preservation_pressure_score = max(1, preservation_pressure_score - 1)

    frontier_pressure_score = 0
    if first_feasible_eval is not None:
        frontier_pressure_score = 3 if phase == "post_feasible_expand" else 0
        if recent_frontier_stagnation_count > 0:
            frontier_pressure_score = max(frontier_pressure_score, 1)

    regime_panel = {
        "phase": phase,
        "dominant_violation_family": dominant_violation_family,
        "dominant_violation_persistence_count": persistence_count,
        "near_feasible_window": bool(first_feasible_eval is None and phase == "prefeasible_convert"),
        "entry_pressure": _pressure_level(entry_pressure_score),
        "preservation_pressure": _pressure_level(preservation_pressure_score),
        "frontier_pressure": _pressure_level(frontier_pressure_score),
        "run_feasible_rate": float(run_state.get("feasible_rate", 0.0) or 0.0),
        "recent_frontier_stagnation_count": recent_frontier_stagnation_count,
        "recover_release_ready": bool(
            resolved_recover_release_ready
            if resolved_recover_release_ready is not None
            else (
                first_feasible_eval is not None
                and stable_preservation_streak >= 3
                and recent_feasible_regression_count <= 0
                and not new_dominant_violation_family
            )
        ),
        "recover_exit_ready": bool(
            resolved_recover_release_ready
            if resolved_recover_release_ready is not None
            else (
                first_feasible_eval is not None
                and stable_preservation_streak >= 3
                and recent_feasible_regression_count <= 0
                and not new_dominant_violation_family
            )
        ),
    }
    if progress_state.get("preserve_dwell_remaining") is not None:
        regime_panel["preserve_dwell_remaining"] = int(progress_state.get("preserve_dwell_remaining", 0))
    if progress_state.get("recover_reentry_pressure") is not None:
        regime_panel["recover_reentry_pressure"] = str(progress_state.get("recover_reentry_pressure", "low"))
    if progress_state.get("diversity_deficit_level") is not None:
        regime_panel["diversity_deficit_level"] = str(progress_state.get("diversity_deficit_level", "low"))
    objective_stagnation = progress_state.get("objective_stagnation", {})
    if isinstance(objective_stagnation, Mapping):
        objective_balance = _build_objective_balance(objective_stagnation)
        regime_panel["objective_balance"] = _adjust_objective_balance_for_endpoint_deficit(
            objective_balance,
            run_state=run_state,
            progress_state=progress_state,
            archive_state=archive_state,
            domain_regime=domain_regime,
        )
    if domain_regime.get("sink_budget_utilization") is not None:
        regime_panel["sink_budget_utilization"] = float(domain_regime["sink_budget_utilization"])

    expand_saturation_count = int(progress_state.get("expand_saturation_count", 0))
    if expand_saturation_count > 0:
        regime_panel["expand_saturation_pressure"] = min(
            1.0, float(expand_saturation_count) / float(_EXPAND_SATURATION_THRESHOLD)
        )
    return regime_panel


def _build_objective_balance(
    objective_stagnation: Mapping[str, Any],
) -> dict[str, Any]:
    """Derive prompt-layer objective balance pressure from per-objective stagnation.

    In generation-batched controllers, both objectives can look stale at the start of a
    generation even when one just improved near the end of the previous generation.
    A large staleness gap restores directional pressure in those cases.
    """
    tmax_state = objective_stagnation.get("temperature_max")
    grad_state = objective_stagnation.get("gradient_rms")
    tmax_stagnant = bool(isinstance(tmax_state, Mapping) and tmax_state.get("stagnant", False))
    grad_stagnant = bool(isinstance(grad_state, Mapping) and grad_state.get("stagnant", False))
    tmax_since = (
        None
        if not isinstance(tmax_state, Mapping) or tmax_state.get("evaluations_since_improvement") is None
        else int(tmax_state["evaluations_since_improvement"])
    )
    grad_since = (
        None
        if not isinstance(grad_state, Mapping) or grad_state.get("evaluations_since_improvement") is None
        else int(grad_state["evaluations_since_improvement"])
    )

    if tmax_stagnant and not grad_stagnant:
        balance_pressure = "high"
        preferred_effect = "peak_improve"
        stagnant_objectives = ["temperature_max"]
        improving_objectives = ["gradient_rms"]
    elif grad_stagnant and not tmax_stagnant:
        balance_pressure = "high"
        preferred_effect = "gradient_improve"
        stagnant_objectives = ["gradient_rms"]
        improving_objectives = ["temperature_max"]
    elif tmax_stagnant and grad_stagnant:
        staleness_gap = None if tmax_since is None or grad_since is None else tmax_since - grad_since
        if staleness_gap is not None and staleness_gap >= _OBJECTIVE_BALANCE_STALENESS_GAP_THRESHOLD:
            balance_pressure = "high"
            preferred_effect = "peak_improve"
            stagnant_objectives = ["temperature_max"]
            improving_objectives = ["gradient_rms"]
        elif staleness_gap is not None and staleness_gap <= -_OBJECTIVE_BALANCE_STALENESS_GAP_THRESHOLD:
            balance_pressure = "high"
            preferred_effect = "gradient_improve"
            stagnant_objectives = ["gradient_rms"]
            improving_objectives = ["temperature_max"]
        else:
            balance_pressure = "medium"
            preferred_effect = "balanced"
            stagnant_objectives = ["temperature_max", "gradient_rms"]
            improving_objectives = []
    else:
        balance_pressure = "low"
        preferred_effect = None
        stagnant_objectives = []
        improving_objectives = ["temperature_max", "gradient_rms"]

    return {
        "stagnant_objectives": stagnant_objectives,
        "improving_objectives": improving_objectives,
        "balance_pressure": balance_pressure,
        "preferred_effect": preferred_effect,
    }


def _adjust_objective_balance_for_endpoint_deficit(
    objective_balance: Mapping[str, Any],
    *,
    run_state: Mapping[str, Any],
    progress_state: Mapping[str, Any],
    archive_state: Mapping[str, Any],
    domain_regime: Mapping[str, Any],
) -> dict[str, Any]:
    adjusted = dict(objective_balance)
    if not _frontier_endpoint_deficit_active(run_state, progress_state, archive_state):
        return adjusted
    preferred_effect = str(adjusted.get("preferred_effect") or "").strip()
    if preferred_effect not in {"", "balanced"}:
        return adjusted

    sink_budget_utilization = _endpoint_sink_budget_utilization(run_state, domain_regime)
    if (
        sink_budget_utilization is not None
        and sink_budget_utilization < _ENDPOINT_SINK_HEADROOM_UTILIZATION_THRESHOLD
    ):
        adjusted.update(
            {
                "balance_pressure": "high",
                "preferred_effect": "peak_improve",
                "stagnant_objectives": ["temperature_max"],
                "improving_objectives": ["gradient_rms"],
                "balance_reason": "frontier_endpoint_peak_budget_fill",
            }
        )
        return adjusted

    return adjusted


def _frontier_endpoint_deficit_active(
    run_state: Mapping[str, Any],
    progress_state: Mapping[str, Any],
    archive_state: Mapping[str, Any],
) -> bool:
    if run_state.get("first_feasible_eval") is None:
        return False
    pareto_size = int(archive_state.get("pareto_size", 0))
    diversity_deficit_level = str(progress_state.get("diversity_deficit_level", "")).strip()
    recent_frontier_stagnation_count = int(progress_state.get("recent_frontier_stagnation_count", 0))
    if pareto_size > 1 and diversity_deficit_level != "high":
        return False
    if recent_frontier_stagnation_count < 2 and diversity_deficit_level not in {"high", "medium"}:
        return False
    return _objective_extremes_share_endpoint(run_state)


def _objective_extremes_share_endpoint(run_state: Mapping[str, Any]) -> bool:
    objective_extremes = run_state.get("objective_extremes")
    if not isinstance(objective_extremes, Mapping):
        return False
    min_peak = objective_extremes.get("min_peak_temperature")
    min_gradient = objective_extremes.get("min_temperature_gradient_rms")
    if not isinstance(min_peak, Mapping) or not isinstance(min_gradient, Mapping):
        return False
    if min_peak.get("evaluation_index") is not None and min_peak.get("evaluation_index") == min_gradient.get(
        "evaluation_index"
    ):
        return True
    peak_summary = min_peak.get("objective_summary")
    gradient_summary = min_gradient.get("objective_summary")
    if not isinstance(peak_summary, Mapping) or not isinstance(gradient_summary, Mapping):
        return False
    keys = ("minimize_peak_temperature", "minimize_temperature_gradient_rms")
    for key in keys:
        if peak_summary.get(key) is None or gradient_summary.get(key) is None:
            return False
        if abs(float(peak_summary[key]) - float(gradient_summary[key])) > 1.0e-9:
            return False
    return True


def _endpoint_sink_budget_utilization(
    run_state: Mapping[str, Any],
    domain_regime: Mapping[str, Any],
) -> float | None:
    if run_state.get("sink_budget_utilization") is not None:
        return float(run_state["sink_budget_utilization"])
    if domain_regime.get("sink_budget_utilization") is not None:
        return float(domain_regime["sink_budget_utilization"])
    return None


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
