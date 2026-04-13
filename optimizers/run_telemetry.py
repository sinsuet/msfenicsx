"""Compact evaluation- and generation-level sidecars for optimizer runs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from optimizers.operator_pool.domain_state import classify_constraint_family, dominant_violation, total_violation
from optimizers.problem import objective_to_minimization


def build_evaluation_events(
    *,
    run_id: str,
    mode_id: str,
    seed: int,
    history: Sequence[Mapping[str, Any]],
    objectives: Sequence[Mapping[str, Any]],
    generation_rows: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    objective_definitions = [
        {
            "objective_id": str(item["objective_id"]),
            "sense": str(item.get("sense", "minimize")),
        }
        for item in objectives
    ]
    ordered_history = sorted(history, key=lambda row: int(row.get("evaluation_index", 0)))
    generation_lookup = _build_generation_lookup(ordered_history, generation_rows or [])
    rows: list[dict[str, Any]] = []
    prior_optimizer_feasible_found = False

    for index, record in enumerate(ordered_history):
        prefix = ordered_history[: index + 1]
        optimizer_prefix = [row for row in prefix if _counts_toward_optimizer_progress(row)]
        dominant = dominant_violation(record)
        pareto_members = {
            int(item.get("evaluation_index", -1))
            for item in _pareto_front(optimizer_prefix, objective_definitions)
        }
        counts_toward_progress = _counts_toward_optimizer_progress(record)
        row = {
            "run_id": str(run_id),
            "mode_id": str(mode_id),
            "seed": int(seed),
            "generation_index": int(generation_lookup.get(int(record.get("evaluation_index", 0)), 0)),
            "evaluation_index": int(record.get("evaluation_index", 0)),
            "source": str(record.get("source", "")),
            "decision_vector": {
                str(key): float(value)
                for key, value in dict(record.get("decision_vector", {})).items()
            },
            "objective_values": {
                str(key): float(value)
                for key, value in dict(record.get("objective_values", {})).items()
            },
            "constraint_values": {
                str(key): float(value)
                for key, value in dict(record.get("constraint_values", {})).items()
            },
            "feasible": bool(record.get("feasible", False)),
            "total_constraint_violation": float(total_violation(record)),
            "dominant_violation_constraint_id": None if dominant is None else str(dominant["constraint_id"]),
            "dominant_violation_constraint_family": (
                None
                if dominant is None
                else classify_constraint_family(str(dominant["constraint_id"]))
            ),
            "violation_count": int(
                sum(
                    1
                    for value in dict(record.get("constraint_values", {})).values()
                    if float(value) > 0.0
                )
            ),
            "entered_feasible_region": (
                counts_toward_progress
                and bool(record.get("feasible", False))
                and not prior_optimizer_feasible_found
            ),
            "preserved_feasibility": (
                counts_toward_progress
                and bool(record.get("feasible", False))
                and prior_optimizer_feasible_found
            ),
            "pareto_membership_after_eval": int(record.get("evaluation_index", 0)) in pareto_members,
            "failure_reason": record.get("failure_reason"),
            "feasibility_phase": "post_feasible" if prior_optimizer_feasible_found else "prefeasible",
        }
        rows.append(row)
        if counts_toward_progress and bool(record.get("feasible", False)):
            prior_optimizer_feasible_found = True
    return rows


def build_generation_summary_rows(
    *,
    run_id: str,
    mode_id: str,
    seed: int,
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    generation_rows: list[dict[str, Any]] = []
    for row in rows:
        payload = {
            "run_id": str(run_id),
            "mode_id": str(mode_id),
            "seed": int(seed),
        }
        payload.update({str(key): value for key, value in dict(row).items()})
        generation_rows.append(payload)
    return generation_rows


def build_progress_timeline(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    ordered_rows = sorted(rows, key=lambda row: int(row.get("evaluation_index", 0)))
    if not ordered_rows:
        return []
    total_budget = max(int(row.get("evaluation_index", 0)) for row in ordered_rows)
    objective_definitions = _objective_definitions_from_rows(ordered_rows)
    feasible_prefix: list[Mapping[str, Any]] = []
    optimizer_evaluation_count = 0
    feasible_count = 0
    first_feasible_eval: int | None = None
    best_temperature_max: float | None = None
    best_gradient_rms: float | None = None
    best_total_constraint_violation: float | None = None
    timeline: list[dict[str, Any]] = []

    for row in ordered_rows:
        evaluation_index = int(row.get("evaluation_index", 0))
        total_constraint_violation = float(row.get("total_constraint_violation", 0.0))
        feasible = bool(row.get("feasible", False))
        if _counts_toward_optimizer_progress(row):
            optimizer_evaluation_count += 1
            if best_total_constraint_violation is None:
                best_total_constraint_violation = total_constraint_violation
            else:
                best_total_constraint_violation = min(best_total_constraint_violation, total_constraint_violation)
            if feasible:
                feasible_count += 1
                feasible_prefix.append(row)
                if first_feasible_eval is None:
                    first_feasible_eval = evaluation_index
                peak_value = _extract_objective_value(
                    dict(row.get("objective_values", {})),
                    preferred_keys=("summary.temperature_max", "minimize_peak_temperature"),
                    fallback_tokens=("temperature_max", "peak_temperature"),
                )
                gradient_value = _extract_objective_value(
                    dict(row.get("objective_values", {})),
                    preferred_keys=("summary.temperature_gradient_rms", "minimize_temperature_gradient_rms"),
                    fallback_tokens=("temperature_gradient_rms", "gradient_rms"),
                )
                if peak_value is not None:
                    best_temperature_max = (
                        peak_value if best_temperature_max is None else min(best_temperature_max, peak_value)
                    )
                if gradient_value is not None:
                    best_gradient_rms = (
                        gradient_value if best_gradient_rms is None else min(best_gradient_rms, gradient_value)
                    )
        pareto_size = len(_pareto_front(feasible_prefix, objective_definitions)) if feasible_prefix else 0
        timeline.append(
            {
                "evaluation_index": evaluation_index,
                "generation_index": int(row.get("generation_index", 0)),
                "budget_fraction": float(evaluation_index / float(max(1, total_budget))),
                "feasible": feasible,
                "feasible_count_so_far": feasible_count,
                "feasible_rate_so_far": (
                    0.0
                    if optimizer_evaluation_count <= 0
                    else float(feasible_count / float(optimizer_evaluation_count))
                ),
                "first_feasible_eval_so_far": first_feasible_eval,
                "pareto_size_so_far": pareto_size,
                "best_temperature_max_so_far": best_temperature_max,
                "best_gradient_rms_so_far": best_gradient_rms,
                "best_total_constraint_violation_so_far": best_total_constraint_violation,
            }
        )
    return timeline


def build_progress_milestones(timeline: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not timeline:
        return {"rows": []}
    rows: list[dict[str, Any]] = []
    prior_pareto_size = 0
    prior_best_peak: float | None = None
    prior_best_gradient: float | None = None
    prior_best_constraint: float | None = None
    for row in timeline:
        evaluation_index = int(row["evaluation_index"])
        if row.get("first_feasible_eval_so_far") == evaluation_index:
            rows.append(_milestone_row("first_feasible", "first_feasible", row))
        pareto_size = int(row.get("pareto_size_so_far", 0))
        if pareto_size > prior_pareto_size:
            rows.append(_milestone_row("pareto_expansion", "pareto_expansion", row))
            prior_pareto_size = pareto_size
        best_peak = row.get("best_temperature_max_so_far")
        if best_peak is not None and (prior_best_peak is None or float(best_peak) < prior_best_peak):
            rows.append(_milestone_row("peak_drop", "peak_drop", row))
            prior_best_peak = float(best_peak)
        best_gradient = row.get("best_gradient_rms_so_far")
        if best_gradient is not None and (prior_best_gradient is None or float(best_gradient) < prior_best_gradient):
            rows.append(_milestone_row("gradient_drop", "gradient_drop", row))
            prior_best_gradient = float(best_gradient)
        best_constraint = row.get("best_total_constraint_violation_so_far")
        if best_constraint is not None and (prior_best_constraint is None or float(best_constraint) < prior_best_constraint):
            rows.append(_milestone_row("violation_drop", "violation_drop", row))
            prior_best_constraint = float(best_constraint)
    return {"rows": rows}


def load_jsonl_rows(path: str | Any) -> list[dict[str, Any]]:
    from json import loads
    from pathlib import Path

    rows: list[dict[str, Any]] = []
    for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        rows.append(dict(loads(line)))
    return rows


def _milestone_row(trigger_id: str, trigger_type: str, row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "trigger_id": trigger_id,
        "trigger_type": trigger_type,
        "evaluation_index": int(row.get("evaluation_index", 0)),
        "generation_index": int(row.get("generation_index", 0)),
        "feasible_count_so_far": int(row.get("feasible_count_so_far", 0)),
        "pareto_size_so_far": int(row.get("pareto_size_so_far", 0)),
        "best_temperature_max_so_far": row.get("best_temperature_max_so_far"),
        "best_gradient_rms_so_far": row.get("best_gradient_rms_so_far"),
        "best_total_constraint_violation_so_far": row.get("best_total_constraint_violation_so_far"),
    }


def _objective_definitions_from_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    objective_ids: list[str] = []
    for row in rows:
        for objective_id in dict(row.get("objective_values", {})).keys():
            objective_text = str(objective_id)
            if objective_text not in objective_ids:
                objective_ids.append(objective_text)
    return [{"objective_id": objective_id, "sense": "minimize"} for objective_id in objective_ids]


def _extract_objective_value(
    objective_values: Mapping[str, Any],
    *,
    preferred_keys: Sequence[str],
    fallback_tokens: Sequence[str],
) -> float | None:
    for key in preferred_keys:
        if key in objective_values:
            return float(objective_values[key])
    for key, value in objective_values.items():
        key_text = str(key)
        if any(token in key_text for token in fallback_tokens):
            return float(value)
    return None


def _build_generation_lookup(
    history: Sequence[Mapping[str, Any]],
    generation_rows: Sequence[Mapping[str, Any]],
) -> dict[int, int]:
    lookup: dict[int, int] = {}
    boundaries = sorted(
        (
            int(row.get("num_evaluations_so_far", 0)),
            int(row.get("generation_index", 0)),
        )
        for row in generation_rows
    )
    boundary_index = 0
    last_generation = 0
    for position, record in enumerate(history, start=1):
        evaluation_index = int(record.get("evaluation_index", 0))
        if str(record.get("source", "")) == "baseline":
            lookup[evaluation_index] = 0
            continue
        while boundary_index < len(boundaries) and position > boundaries[boundary_index][0]:
            last_generation = boundaries[boundary_index][1]
            boundary_index += 1
        if boundary_index < len(boundaries):
            lookup[evaluation_index] = boundaries[boundary_index][1]
            last_generation = boundaries[boundary_index][1]
        else:
            lookup[evaluation_index] = last_generation
    return lookup


def _pareto_front(
    history: Sequence[Mapping[str, Any]],
    objective_definitions: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    feasible_records = [record for record in history if bool(record.get("feasible", False))]
    pareto_front: list[Mapping[str, Any]] = []
    for candidate in feasible_records:
        dominated = False
        for incumbent in feasible_records:
            if candidate is incumbent:
                continue
            if _dominates(incumbent, candidate, objective_definitions):
                dominated = True
                break
        if not dominated:
            pareto_front.append(candidate)
    return pareto_front


def _dominates(
    candidate: Mapping[str, Any],
    incumbent: Mapping[str, Any],
    objective_definitions: Sequence[Mapping[str, Any]],
) -> bool:
    candidate_tuple = tuple(
        objective_to_minimization(
            float(candidate["objective_values"][definition["objective_id"]]),
            str(definition["sense"]),
        )
        for definition in objective_definitions
    )
    incumbent_tuple = tuple(
        objective_to_minimization(
            float(incumbent["objective_values"][definition["objective_id"]]),
            str(definition["sense"]),
        )
        for definition in objective_definitions
    )
    return all(left <= right for left, right in zip(candidate_tuple, incumbent_tuple, strict=True)) and any(
        left < right for left, right in zip(candidate_tuple, incumbent_tuple, strict=True)
    )


def _counts_toward_optimizer_progress(record: Mapping[str, Any]) -> bool:
    return str(record.get("source", "")).strip().lower() != "baseline"
