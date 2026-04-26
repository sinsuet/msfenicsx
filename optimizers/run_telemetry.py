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
        row = {
            "decision_id": record.get("decision_id"),
            "generation": generation,
            "eval_index": eval_index,
            "individual_id": str(individual_id),
            "objectives": _project_objectives(record.get("objective_values", {}), objective_short_names),
            "constraints": dict(record.get("constraint_values", {})),
            "status": _record_status(record),
            "solver_skipped": bool(record.get("solver_skipped", False)),
            "timing": dict(record.get("timing", {})),
        }
        failure_reason = record.get("failure_reason")
        if failure_reason:
            row["failure_reason"] = str(failure_reason)
        cheap_constraint_issues = record.get("cheap_constraint_issues", [])
        if isinstance(cheap_constraint_issues, Sequence) and not isinstance(
            cheap_constraint_issues,
            (str, bytes, bytearray),
        ):
            issue_examples = [str(issue) for issue in cheap_constraint_issues[:3]]
            row["cheap_constraint_issue_count"] = int(len(cheap_constraint_issues))
            row["cheap_constraint_issue_examples"] = issue_examples
        rows.append(row)
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
    ordered_rows = _normalized_progress_rows(rows)
    if not ordered_rows:
        return []
    objective_definitions = _objective_definitions_from_rows(ordered_rows)
    feasible_prefix: list[Mapping[str, Any]] = []
    optimizer_evaluation_count = 0
    pde_evaluation_count = 0
    solver_skipped_count = 0
    feasible_count = 0
    first_feasible_eval: int | None = None
    first_feasible_pde_eval: int | None = None
    best_temperature_max: float | None = None
    best_gradient_rms: float | None = None
    best_total_constraint_violation: float | None = None
    timeline: list[dict[str, Any]] = []

    for row in ordered_rows:
        status = str(row.get("status", "ok"))
        current_peak, current_gradient = _current_objective_metrics(row, status=status)
        current_violation = _current_total_constraint_violation(row, status=status)
        evaluation_index = int(row.get("evaluation_index", 0))
        solver_skipped = bool(row.get("solver_skipped", False))
        pde_attempted = not solver_skipped
        explicit_total_constraint = row.get("total_constraint_violation")
        total_constraint_violation = (
            _sanitize_progress_metric(explicit_total_constraint, status=status)
            if explicit_total_constraint is not None
            else current_violation
        )
        feasible = bool(row.get("feasible", False))
        optimizer_evaluation_count += 1
        if pde_attempted:
            pde_evaluation_count += 1
        else:
            solver_skipped_count += 1
        if total_constraint_violation is not None:
            if best_total_constraint_violation is None:
                best_total_constraint_violation = total_constraint_violation
            else:
                best_total_constraint_violation = min(best_total_constraint_violation, total_constraint_violation)
        if feasible:
            feasible_count += 1
            feasible_prefix.append(row)
            if first_feasible_eval is None:
                first_feasible_eval = evaluation_index
            if first_feasible_pde_eval is None and pde_attempted:
                first_feasible_pde_eval = pde_evaluation_count
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
                "status": status,
                "solver_skipped": solver_skipped,
                "pde_attempted": pde_attempted,
                "pde_evaluation_index": pde_evaluation_count,
                "current_temperature_max": current_peak,
                "current_gradient_rms": current_gradient,
                "current_total_constraint_violation": current_violation,
                "budget_fraction": float(optimizer_evaluation_count / float(max(1, len(ordered_rows)))),
                "feasible": feasible,
                "optimizer_evaluations_so_far": optimizer_evaluation_count,
                "pde_evaluations_so_far": pde_evaluation_count,
                "solver_skipped_evaluations_so_far": solver_skipped_count,
                "feasible_count_so_far": feasible_count,
                "feasible_rate_so_far": float(feasible_count / float(max(1, optimizer_evaluation_count))),
                "first_feasible_eval_so_far": first_feasible_eval,
                "first_feasible_pde_eval_so_far": first_feasible_pde_eval,
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
        "pde_evaluation_index": int(row.get("pde_evaluation_index", 0)),
        "generation_index": int(row.get("generation_index", 0)),
        "feasible_count_so_far": int(row.get("feasible_count_so_far", 0)),
        "pareto_size_so_far": int(row.get("pareto_size_so_far", 0)),
        "best_temperature_max_so_far": row.get("best_temperature_max_so_far"),
        "best_gradient_rms_so_far": row.get("best_gradient_rms_so_far"),
        "best_total_constraint_violation_so_far": row.get("best_total_constraint_violation_so_far"),
        "first_feasible_pde_eval_so_far": row.get("first_feasible_pde_eval_so_far"),
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


def _normalized_progress_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        normalized_row = _normalize_progress_row(row)
        if _counts_toward_optimizer_progress(normalized_row):
            normalized.append(normalized_row)
    return sorted(normalized, key=lambda row: int(row.get("evaluation_index", 0)))


def _normalize_progress_row(row: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(row)
    source = payload.get("source")
    if source is None and "status" in payload:
        source = "optimizer"
    objective_values = payload.get("objective_values")
    if objective_values is None:
        objective_values = payload.get("objectives", {})
    constraint_values = payload.get("constraint_values")
    if constraint_values is None:
        constraint_values = payload.get("constraints", {})
    feasible = payload.get("feasible")
    if feasible is None:
        feasible = str(payload.get("status", "")).strip().lower() == "ok"
    status = payload.get("status")
    if status is None:
        failure_reason = payload.get("failure_reason")
        if failure_reason:
            status = "failed"
        else:
            status = "ok" if bool(feasible) else "infeasible"
    total_constraint_violation = payload.get("total_constraint_violation")
    if total_constraint_violation is None:
        total_constraint_violation = _sum_positive_constraint_values(constraint_values)
    generation_index = payload.get("generation_index")
    if generation_index is None:
        generation_index = payload.get("generation", 0)
    evaluation_index = payload.get("evaluation_index")
    if evaluation_index is None:
        evaluation_index = payload.get("eval_index", 0)
    return {
        "evaluation_index": int(evaluation_index),
        "generation_index": int(generation_index),
        "source": str(source or ""),
        "status": str(status),
        "feasible": bool(feasible),
        "solver_skipped": bool(payload.get("solver_skipped", False)),
        "objective_values": dict(objective_values or {}),
        "constraint_values": dict(constraint_values or {}),
        "total_constraint_violation": float(total_constraint_violation),
    }


def _sum_positive_constraint_values(values: Mapping[str, Any] | None) -> float:
    if not values:
        return 0.0
    return float(sum(max(0.0, float(value)) for value in dict(values).values()))


def _sanitize_progress_metric(value: Any, *, status: str) -> float | None:
    if value is None:
        return None
    numeric = float(value)
    if str(status).strip().lower() == "failed" or abs(numeric) >= 1.0e11:
        return None
    return numeric


def _current_objective_metrics(
    row: Mapping[str, Any],
    *,
    status: str,
) -> tuple[float | None, float | None]:
    objective_values = dict(row.get("objective_values", row.get("objectives", {})))
    peak_value = _extract_objective_value(
        objective_values,
        preferred_keys=("summary.temperature_max", "minimize_peak_temperature"),
        fallback_tokens=("temperature_max", "peak_temperature"),
    )
    gradient_value = _extract_objective_value(
        objective_values,
        preferred_keys=("summary.temperature_gradient_rms", "minimize_temperature_gradient_rms"),
        fallback_tokens=("temperature_gradient_rms", "gradient_rms"),
    )
    return (
        _sanitize_progress_metric(peak_value, status=status),
        _sanitize_progress_metric(gradient_value, status=status),
    )


def _current_total_constraint_violation(
    row: Mapping[str, Any],
    *,
    status: str,
) -> float | None:
    value = row.get("total_constraint_violation")
    if value is None:
        value = _sum_positive_constraint_values(row.get("constraint_values", row.get("constraints", {})))
    return _sanitize_progress_metric(value, status=status)
