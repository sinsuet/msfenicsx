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
    prior_feasible_found = False

    for index, record in enumerate(ordered_history):
        prefix = ordered_history[: index + 1]
        dominant = dominant_violation(record)
        pareto_members = {
            int(item.get("evaluation_index", -1))
            for item in _pareto_front(prefix, objective_definitions)
        }
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
            "entered_feasible_region": bool(record.get("feasible", False)) and not prior_feasible_found,
            "preserved_feasibility": bool(record.get("feasible", False)) and prior_feasible_found,
            "pareto_membership_after_eval": int(record.get("evaluation_index", 0)) in pareto_members,
            "failure_reason": record.get("failure_reason"),
            "feasibility_phase": "post_feasible" if prior_feasible_found else "prefeasible",
        }
        rows.append(row)
        if bool(record.get("feasible", False)):
            prior_feasible_found = True
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
