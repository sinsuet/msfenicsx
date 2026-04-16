"""Compact evaluation- and generation-level sidecars for optimizer runs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from optimizers.problem import objective_to_minimization


def build_evaluation_events(
    history: list[dict],
    *,
    objective_definitions: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict]:
    """§ 4.1 evaluation_events rows — one per optimizer evaluation.

    Accepts the flat per-evaluation records that live on ``problem.history``.
    Baseline evaluations (``source == "baseline"``) are skipped so downstream
    analytics bucket only true search iterations. When ``objective_definitions``
    is supplied, objective values are re-keyed from the spec's ``objective_id``
    onto the bare metric suffix (``summary.temperature_max`` →
    ``temperature_max``) so analytics can read a stable, spec-agnostic name.
    """
    objective_short_names = _objective_short_names(objective_definitions)
    rows: list[dict] = []
    eval_index = 0
    previous_generation: int | None = None
    intra_generation_index = 0
    for record in history:
        if str(record.get("source", "")).strip().lower() == "baseline":
            continue
        generation = int(record.get("generation", 0))
        if previous_generation is None or generation != previous_generation:
            intra_generation_index = 0
            previous_generation = generation
        individual_id = record.get("individual_id") or f"g{generation:03d}-i{intra_generation_index:02d}"
        rows.append(
            {
                "decision_id": record.get("decision_id"),
                "generation": generation,
                "eval_index": eval_index,
                "individual_id": str(individual_id),
                "objectives": _project_objectives(record.get("objective_values", {}), objective_short_names),
                "constraints": dict(record.get("constraint_values", {})),
                "status": _record_status(record),
                "timing": dict(record.get("timing", {})),
            }
        )
        eval_index += 1
        intra_generation_index += 1
    return rows


def _objective_short_names(
    objective_definitions: Sequence[Mapping[str, Any]] | None,
) -> dict[str, str]:
    if not objective_definitions:
        return {}
    mapping: dict[str, str] = {}
    for definition in objective_definitions:
        objective_id = str(definition.get("objective_id", "")).strip()
        metric = str(definition.get("metric", "")).strip()
        if not objective_id:
            continue
        short_name = metric.rsplit(".", 1)[-1] if metric else objective_id
        mapping[objective_id] = short_name
    return mapping


def _project_objectives(
    objective_values: Mapping[str, Any],
    objective_short_names: Mapping[str, str],
) -> dict[str, Any]:
    if not objective_short_names:
        return dict(objective_values)
    return {
        objective_short_names.get(str(key), str(key)): value
        for key, value in objective_values.items()
    }


def _record_status(record: dict) -> str:
    explicit_status = record.get("status")
    if explicit_status is not None:
        return str(explicit_status)
    failure_reason = record.get("failure_reason")
    if failure_reason:
        return "failed"
    return "ok" if bool(record.get("feasible", False)) else "infeasible"


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
