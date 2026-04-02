"""Experiment-level multi-seed summaries for three-mode NSGA-II runs."""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from optimizers.experiment_index import refresh_experiment_index
from optimizers.llm_summary import (
    build_llm_decision_summary,
    build_llm_prompt_summary,
    build_llm_reflection_summary,
    build_llm_runtime_summary,
)
from optimizers.operator_pool.diagnostics import summarize_controller_rows
from optimizers.operator_pool.domain_state import (
    build_history_lookup,
    outcome_regime,
    total_violation,
    vector_key,
)
from optimizers.operator_pool.reflection import summarize_operator_history
from optimizers.operator_pool.trace import ControllerTraceRow, OperatorTraceRow
from optimizers.run_telemetry import load_jsonl_rows


def build_experiment_summaries(experiment_root: str | Path) -> dict[str, Any]:
    root = Path(experiment_root)
    experiment_manifest = _load_json(root / "manifest.json")
    summaries_root = root / "summaries"
    summaries_root.mkdir(parents=True, exist_ok=True)

    run_rows = build_run_index(root)
    aggregate_summary = build_aggregate_summary(run_rows)
    constraint_summary = build_constraint_summary(root)
    generation_summary = build_generation_summary(root)

    _write_json(summaries_root / "run_index.json", run_rows)
    _write_json(summaries_root / "aggregate_summary.json", aggregate_summary)
    _write_json(summaries_root / "constraint_summary.json", constraint_summary)
    _write_json(summaries_root / "generation_summary.json", generation_summary)

    written = {
        "run_index": "summaries/run_index.json",
        "aggregate_summary": "summaries/aggregate_summary.json",
        "constraint_summary": "summaries/constraint_summary.json",
        "generation_summary": "summaries/generation_summary.json",
    }
    mode_id = str(experiment_manifest.get("mode_id", ""))
    if mode_id in {"nsga2_union", "nsga2_llm"}:
        controller_summary, operator_summary, regime_summary = build_mechanism_summaries(root)
        _write_json(summaries_root / "controller_trace_summary.json", controller_summary)
        _write_json(summaries_root / "operator_summary.json", operator_summary)
        _write_json(summaries_root / "regime_operator_summary.json", regime_summary)
        written.update(
            {
                "controller_trace_summary": "summaries/controller_trace_summary.json",
                "operator_summary": "summaries/operator_summary.json",
                "regime_operator_summary": "summaries/regime_operator_summary.json",
            }
        )
    if mode_id == "nsga2_llm":
        llm_summaries = build_experiment_llm_summaries(root)
        for summary_name, payload in llm_summaries.items():
            if payload is None:
                continue
            _write_json(summaries_root / f"{summary_name}.json", payload)
            written[summary_name] = f"summaries/{summary_name}.json"
    refresh_experiment_index(root)
    return written


def build_run_index(experiment_root: str | Path) -> list[dict[str, Any]]:
    root = Path(experiment_root)
    experiment_manifest = _load_json(root / "manifest.json")
    rows: list[dict[str, Any]] = []
    for run_root in _iter_run_roots(root):
        result_payload = _load_json(run_root / "optimization_result.json")
        history = list(result_payload.get("history", []))
        objective_definitions = _objective_definitions_from_history(history)
        evaluation_rows = (
            load_jsonl_rows(run_root / "evaluation_events.jsonl")
            if (run_root / "evaluation_events.jsonl").exists()
            else []
        )
        seed = int(run_root.name.removeprefix("seed-"))
        rows.append(
            {
                "seed": seed,
                "run_dir": str(run_root.relative_to(root).as_posix()),
                "run_id": str(result_payload["run_meta"]["run_id"]),
                "mode_id": str(experiment_manifest.get("mode_id", "")),
                "num_evaluations": int(result_payload["aggregate_metrics"].get("num_evaluations", len(history))),
                "feasible_rate": float(result_payload["aggregate_metrics"].get("feasible_rate", 0.0)),
                "first_feasible_eval": result_payload["aggregate_metrics"].get("first_feasible_eval"),
                "pareto_size": int(result_payload["aggregate_metrics"].get("pareto_size", 0)),
                "best_total_cv_among_infeasible": _best_total_cv_among_infeasible(history),
                "controller_trace": (run_root / "controller_trace.json").exists(),
                "operator_trace": (run_root / "operator_trace.json").exists(),
                "llm_request_trace": (run_root / "llm_request_trace.jsonl").exists(),
                "llm_response_trace": (run_root / "llm_response_trace.jsonl").exists(),
                "failure_count": int(sum(1 for row in evaluation_rows if row.get("failure_reason"))),
            }
        )
        rows[-1].update(
            {
                f"best_{objective_id}": _best_objective_value(history, objective_id, sense)
                for objective_id, sense in objective_definitions
            }
        )
    rows.sort(key=lambda row: int(row["seed"]))
    return rows


def build_aggregate_summary(run_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    dynamic_best_keys = sorted(
        {
            str(key)
            for row in run_rows
            for key in row.keys()
            if str(key).startswith("best_") and str(key) != "best_total_cv_among_infeasible"
        }
    )
    numeric_keys = (
        "num_evaluations",
        "feasible_rate",
        "first_feasible_eval",
        "pareto_size",
        "best_total_cv_among_infeasible",
        *dynamic_best_keys,
    )
    return {
        "num_runs": int(len(run_rows)),
        "seeds": [int(row["seed"]) for row in run_rows],
        "failed_runs": [int(row["seed"]) for row in run_rows if int(row.get("failure_count", 0)) > 0],
        "no_feasible_solution_runs": [
            int(row["seed"])
            for row in run_rows
            if row.get("first_feasible_eval") is None
        ],
        "metrics": {
            key: _metric_stats(
                [
                    float(row[key])
                    for row in run_rows
                    if row.get(key) is not None
                ]
            )
            for key in numeric_keys
        },
    }


def build_constraint_summary(experiment_root: str | Path) -> dict[str, Any]:
    rows = _load_evaluation_rows(Path(experiment_root))
    per_constraint: dict[str, dict[str, Any]] = {}
    dominant_constraint_frequency: Counter[str] = Counter()
    dominant_constraint_family_distribution: Counter[str] = Counter()
    phase_split: dict[str, Counter[str]] = {
        "prefeasible": Counter(),
        "post_feasible": Counter(),
    }
    for row in rows:
        constraint_values = dict(row.get("constraint_values", {}))
        phase_key = "post_feasible" if row.get("feasibility_phase") == "post_feasible" else "prefeasible"
        for constraint_id, raw_value in constraint_values.items():
            value = float(raw_value)
            summary = per_constraint.setdefault(
                str(constraint_id),
                {
                    "activation_count": 0,
                    "sample_count": 0,
                    "violation_sum": 0.0,
                    "active_violation_sum": 0.0,
                },
            )
            summary["sample_count"] += 1
            summary["violation_sum"] += max(0.0, value)
            if value > 0.0:
                summary["activation_count"] += 1
                summary["active_violation_sum"] += value
                phase_split[phase_key][str(constraint_id)] += 1
        dominant_id = row.get("dominant_violation_constraint_id")
        if dominant_id:
            dominant_constraint_frequency[str(dominant_id)] += 1
        dominant_family = row.get("dominant_violation_constraint_family")
        if dominant_family:
            dominant_constraint_family_distribution[str(dominant_family)] += 1
    return {
        "num_rows": int(len(rows)),
        "per_constraint": {
            constraint_id: {
                "activation_frequency": (
                    0.0 if summary["sample_count"] <= 0 else summary["activation_count"] / float(summary["sample_count"])
                ),
                "mean_violation": (
                    0.0 if summary["sample_count"] <= 0 else summary["violation_sum"] / float(summary["sample_count"])
                ),
                "mean_active_violation": (
                    0.0
                    if summary["activation_count"] <= 0
                    else summary["active_violation_sum"] / float(summary["activation_count"])
                ),
            }
            for constraint_id, summary in sorted(per_constraint.items())
        },
        "dominant_constraint_frequency": dict(dominant_constraint_frequency),
        "dominant_constraint_family_distribution": dict(dominant_constraint_family_distribution),
        "phase_split": {
            phase: dict(counter)
            for phase, counter in phase_split.items()
        },
    }


def build_generation_summary(experiment_root: str | Path) -> dict[str, Any]:
    generation_rows: list[dict[str, Any]] = []
    for run_root in _iter_run_roots(Path(experiment_root)):
        path = run_root / "generation_summary.jsonl"
        if path.exists():
            generation_rows.extend(load_jsonl_rows(path))
    dynamic_best_keys = sorted(
        {
            str(key)
            for row in generation_rows
            for key in row.keys()
            if str(key).startswith("best_") and str(key) != "best_total_constraint_violation"
        }
    )
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in generation_rows:
        grouped[int(row["generation_index"])].append(row)
    return {
        "num_rows": int(len(generation_rows)),
        "generations": [
            {
                "generation_index": generation_index,
                "mean_feasible_fraction": _mean_of(group_rows, "feasible_fraction"),
                "mean_best_total_constraint_violation": _mean_of(group_rows, "best_total_constraint_violation"),
                **{
                    f"mean_{best_key}": _mean_of(group_rows, best_key)
                    for best_key in dynamic_best_keys
                },
                "mean_pareto_size": _mean_of(group_rows, "pareto_size"),
            }
            for generation_index, group_rows in sorted(grouped.items())
        ],
    }


def build_mechanism_summaries(experiment_root: str | Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    root = Path(experiment_root)
    design_variable_ids = _load_design_variable_ids(root)
    controller_rows: list[ControllerTraceRow] = []
    operator_summary_runs: list[dict[str, dict[str, Any]]] = []
    regime_rows: list[dict[str, Any]] = []

    for run_root in _iter_run_roots(root):
        controller_path = run_root / "controller_trace.json"
        operator_path = run_root / "operator_trace.json"
        if not controller_path.exists() or not operator_path.exists():
            continue
        run_controller_rows = [ControllerTraceRow.from_dict(row) for row in _load_json(controller_path)]
        run_operator_rows = [OperatorTraceRow.from_dict(row) for row in _load_json(operator_path)]
        history = list(_load_json(run_root / "optimization_result.json").get("history", []))
        controller_rows.extend(run_controller_rows)
        operator_summary_runs.append(
            summarize_operator_history(
                run_controller_rows,
                run_operator_rows,
                recent_window=32,
                history=history,
                design_variable_ids=design_variable_ids,
            )
        )
        regime_rows.extend(
            _build_regime_operator_rows(
                run_operator_rows,
                history=history,
                design_variable_ids=design_variable_ids,
            )
        )

    controller_summary = summarize_controller_rows(controller_rows)
    operator_summary = _aggregate_operator_summaries(operator_summary_runs)
    regime_summary = _aggregate_regime_rows(regime_rows)
    return controller_summary, operator_summary, regime_summary


def build_experiment_llm_summaries(experiment_root: str | Path) -> dict[str, dict[str, Any] | None]:
    root = Path(experiment_root)
    metrics_rows: list[dict[str, Any]] = []
    request_rows: list[dict[str, Any]] = []
    response_rows: list[dict[str, Any]] = []
    reflection_rows: list[dict[str, Any]] = []
    controller_rows: list[dict[str, Any]] = []

    for run_root in _iter_run_roots(root):
        if (run_root / "llm_metrics.json").exists():
            metrics_rows.append(_load_json(run_root / "llm_metrics.json"))
        if (run_root / "llm_request_trace.jsonl").exists():
            request_rows.extend(load_jsonl_rows(run_root / "llm_request_trace.jsonl"))
        if (run_root / "llm_response_trace.jsonl").exists():
            response_rows.extend(load_jsonl_rows(run_root / "llm_response_trace.jsonl"))
        if (run_root / "llm_reflection_trace.jsonl").exists():
            reflection_rows.extend(load_jsonl_rows(run_root / "llm_reflection_trace.jsonl"))
        if (run_root / "controller_trace.json").exists():
            controller_rows.extend(_load_json(run_root / "controller_trace.json"))

    return {
        "llm_runtime_summary": build_llm_runtime_summary(
            metrics_rows=metrics_rows,
            request_rows=request_rows,
            response_rows=response_rows,
            reflection_rows=reflection_rows,
        ),
        "llm_decision_summary": build_llm_decision_summary(
            controller_rows=controller_rows,
            response_rows=response_rows,
        ),
        "llm_prompt_summary": build_llm_prompt_summary(request_rows=request_rows),
        "llm_reflection_summary": (
            None if not reflection_rows else build_llm_reflection_summary(reflection_rows=reflection_rows)
        ),
    }


def _build_regime_operator_rows(
    operator_rows: Sequence[OperatorTraceRow],
    *,
    history: Sequence[Mapping[str, Any]],
    design_variable_ids: Sequence[str] | None,
) -> list[dict[str, Any]]:
    if design_variable_ids is None:
        return []
    history_lookup = build_history_lookup(history, design_variable_ids)
    history_by_eval = {
        int(row["evaluation_index"]): dict(row)
        for row in history
        if "evaluation_index" in row
    }
    pareto_ids = {
        int(row["evaluation_index"])
        for row in history
        if bool(row.get("feasible", False))
    }
    rows: list[dict[str, Any]] = []
    for row in operator_rows:
        child_record = history_by_eval.get(int(row.evaluation_index))
        if child_record is None:
            continue
        parent_records = [
            history_lookup.get(vector_key(parent_vector))
            for parent_vector in row.parent_vectors
        ]
        parent_records = [record for record in parent_records if record is not None]
        if not parent_records:
            continue
        regime = outcome_regime(parent_records=parent_records, child_record=child_record)
        parent_total_violation = float(np.mean([total_violation(record) for record in parent_records]))
        child_total_violation = total_violation(child_record)
        repair_distance = 0.0
        repaired_vector = row.metadata.get("repaired_vector")
        if isinstance(repaired_vector, Sequence) and not isinstance(repaired_vector, (str, bytes)):
            repair_distance = float(
                np.linalg.norm(np.asarray(repaired_vector, dtype=np.float64) - np.asarray(row.proposal_vector, dtype=np.float64))
            )
        parent_feasible_flags = [bool(record.get("feasible", False)) for record in parent_records]
        rows.append(
            {
                "phase": str(regime["phase"]),
                "dominant_constraint_family": str(regime["dominant_constraint_family"]),
                "operator_id": str(row.operator_id),
                "proposal_count": 1,
                "feasible_entry_count": int(bool(child_record.get("feasible", False)) and not any(parent_feasible_flags)),
                "feasible_preservation_count": int(
                    bool(child_record.get("feasible", False)) and all(parent_feasible_flags)
                ),
                "pareto_hit_count": int(int(child_record["evaluation_index"]) in pareto_ids),
                "total_violation_delta": float(child_total_violation - parent_total_violation),
                "repair_distance": repair_distance,
            }
        )
    return rows


def _aggregate_operator_summaries(
    operator_summary_runs: Sequence[Mapping[str, Mapping[str, Any]]],
) -> dict[str, Any]:
    aggregate: dict[str, dict[str, Any]] = {}
    for run_summary in operator_summary_runs:
        for operator_id, summary in run_summary.items():
            target = aggregate.setdefault(
                operator_id,
                {
                    "selection_count": 0,
                    "recent_selection_count": 0,
                    "fallback_selection_count": 0,
                    "llm_valid_selection_count": 0,
                    "proposal_count": 0,
                    "feasible_entry_count": 0,
                    "feasible_preservation_count": 0,
                    "operator_family": summary.get("operator_family"),
                    "operator_role": summary.get("operator_role"),
                    "exploration_class": summary.get("exploration_class"),
                    "_violation_weighted_total": 0.0,
                    "_violation_weight": 0.0,
                    "_objective_weighted_total": 0.0,
                    "_objective_weight": 0.0,
                    "recent_helpful_regimes": set(),
                    "recent_harmful_regimes": set(),
                },
            )
            for key in (
                "selection_count",
                "recent_selection_count",
                "fallback_selection_count",
                "llm_valid_selection_count",
                "proposal_count",
                "feasible_entry_count",
                "feasible_preservation_count",
            ):
                target[key] += int(summary.get(key, 0))
            proposal_count = max(0, int(summary.get("proposal_count", 0)))
            target["_violation_weighted_total"] += float(summary.get("avg_total_violation_delta", 0.0)) * proposal_count
            target["_violation_weight"] += proposal_count
            objective_weight = int(summary.get("feasible_entry_count", 0)) + int(summary.get("feasible_preservation_count", 0))
            target["_objective_weighted_total"] += float(summary.get("avg_feasible_objective_delta", 0.0)) * objective_weight
            target["_objective_weight"] += objective_weight
            target["recent_helpful_regimes"].update(summary.get("recent_helpful_regimes", []))
            target["recent_harmful_regimes"].update(summary.get("recent_harmful_regimes", []))
    return {
        operator_id: {
            key: value
            for key, value in {
                **summary,
                "avg_total_violation_delta": (
                    0.0
                    if summary["_violation_weight"] <= 0
                    else summary["_violation_weighted_total"] / float(summary["_violation_weight"])
                ),
                "avg_feasible_objective_delta": (
                    0.0
                    if summary["_objective_weight"] <= 0
                    else summary["_objective_weighted_total"] / float(summary["_objective_weight"])
                ),
                "recent_helpful_regimes": sorted(summary["recent_helpful_regimes"]),
                "recent_harmful_regimes": sorted(summary["recent_harmful_regimes"]),
            }.items()
            if not key.startswith("_")
        }
        for operator_id, summary in sorted(aggregate.items())
    }


def _aggregate_regime_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        key = (
            str(row["phase"]),
            str(row["dominant_constraint_family"]),
            str(row["operator_id"]),
        )
        target = grouped.setdefault(
            key,
            {
                "proposal_count": 0,
                "feasible_entry_count": 0,
                "feasible_preservation_count": 0,
                "pareto_hit_count": 0,
                "total_violation_delta_sum": 0.0,
                "repair_distance_sum": 0.0,
            },
        )
        target["proposal_count"] += 1
        target["feasible_entry_count"] += int(row.get("feasible_entry_count", 0))
        target["feasible_preservation_count"] += int(row.get("feasible_preservation_count", 0))
        target["pareto_hit_count"] += int(row.get("pareto_hit_count", 0))
        target["total_violation_delta_sum"] += float(row.get("total_violation_delta", 0.0))
        target["repair_distance_sum"] += float(row.get("repair_distance", 0.0))
    return {
        "rows": [
            {
                "phase": phase,
                "dominant_constraint_family": family,
                "operator_id": operator_id,
                "proposal_count": int(summary["proposal_count"]),
                "feasible_entry_count": int(summary["feasible_entry_count"]),
                "feasible_preservation_count": int(summary["feasible_preservation_count"]),
                "pareto_hit_count": int(summary["pareto_hit_count"]),
                "mean_total_violation_delta": (
                    0.0
                    if summary["proposal_count"] <= 0
                    else summary["total_violation_delta_sum"] / float(summary["proposal_count"])
                ),
                "mean_repair_distance": (
                    0.0
                    if summary["proposal_count"] <= 0
                    else summary["repair_distance_sum"] / float(summary["proposal_count"])
                ),
            }
            for (phase, family, operator_id), summary in sorted(grouped.items())
        ]
    }


def _load_design_variable_ids(experiment_root: Path) -> list[str] | None:
    spec_snapshot_path = experiment_root / "spec_snapshot" / "optimization_spec.yaml"
    if not spec_snapshot_path.exists():
        return None
    spec_payload = _load_yaml(spec_snapshot_path)
    return [
        str(item["variable_id"])
        for item in spec_payload.get("design_variables", [])
        if isinstance(item, Mapping) and item.get("variable_id")
    ]


def _best_objective_value(history: Sequence[Mapping[str, Any]], objective_id: str, sense: str) -> float | None:
    feasible_values = [
        float(row["objective_values"][objective_id])
        for row in history
        if bool(row.get("feasible", False))
        and objective_id in dict(row.get("objective_values", {}))
    ]
    if not feasible_values:
        return None
    return float(max(feasible_values) if sense == "maximize" else min(feasible_values))


def _objective_definitions_from_history(history: Sequence[Mapping[str, Any]]) -> list[tuple[str, str]]:
    for row in history:
        objective_values = row.get("objective_values", {})
        if not isinstance(objective_values, Mapping) or not objective_values:
            continue
        return [
            (str(objective_id), _objective_sense(str(objective_id)))
            for objective_id in objective_values.keys()
        ]
    return []


def _objective_sense(objective_id: str) -> str:
    return "maximize" if objective_id.startswith("maximize_") else "minimize"


def _best_total_cv_among_infeasible(history: Sequence[Mapping[str, Any]]) -> float | None:
    values = [total_violation(row) for row in history if not bool(row.get("feasible", False))]
    if not values:
        return None
    return float(min(values))


def _metric_stats(values: Sequence[float]) -> dict[str, float | None]:
    if not values:
        return {"mean": None, "median": None, "std": None, "min": None, "max": None}
    return {
        "mean": float(statistics.mean(values)),
        "median": float(statistics.median(values)),
        "std": float(statistics.pstdev(values)) if len(values) > 1 else 0.0,
        "min": float(min(values)),
        "max": float(max(values)),
    }


def _mean_of(rows: Sequence[Mapping[str, Any]], key: str) -> float | None:
    values = [float(row[key]) for row in rows if row.get(key) is not None]
    if not values:
        return None
    return float(sum(values) / float(len(values)))


def _load_evaluation_rows(experiment_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run_root in _iter_run_roots(experiment_root):
        path = run_root / "evaluation_events.jsonl"
        if path.exists():
            rows.extend(load_jsonl_rows(path))
    return rows


def _iter_run_roots(experiment_root: Path) -> list[Path]:
    runs_root = experiment_root / "runs"
    if not runs_root.exists():
        return []
    return sorted(
        [path for path in runs_root.iterdir() if path.is_dir() and path.name.startswith("seed-")],
        key=lambda path: int(path.name.removeprefix("seed-")),
    )


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict[str, Any]:
    import yaml

    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"Expected mapping payload in {path}.")
    return payload


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
