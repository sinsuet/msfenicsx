"""Read traces, compute analytics, and render figures/tables."""

from __future__ import annotations

import csv
import json
import shutil
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from core.geometry.layout_rules import component_polygon
from optimizers.algorithm_identity import algorithm_label
from optimizers.analytics.decisions import decision_outcomes
from optimizers.analytics.heatmap import operator_phase_heatmap
from optimizers.analytics.loaders import iter_jsonl
from optimizers.analytics.pareto import pareto_front_indices
from optimizers.analytics.rollups import rollup_per_generation
from optimizers.codec import apply_decision_vector
from optimizers.io import generate_benchmark_case, load_optimization_spec
from optimizers.llm_decision_summary import build_llm_decision_summaries
from optimizers.mode_summary import build_mode_summaries
from optimizers.repair import project_case_payload_from_vector, repair_case_payload_from_vector
from optimizers.run_telemetry import build_progress_timeline
from optimizers.traces.llm_trace_io import (
    is_concrete_optimizer_run_root,
    iter_mode_seed_roots,
    resolve_llm_model_label,
    resolve_seed_trace_path,
)
from visualization.figures.gradient_field import render_gradient_field
from visualization.figures.hypervolume import render_hypervolume_progress
from visualization.figures.layout_evolution import render_layout_evolution, render_layout_snapshot
from visualization.figures.operator_heatmap import render_operator_heatmap
from visualization.figures.pareto import render_pareto_front
from visualization.figures.progress import render_objective_progress
from visualization.figures.trace_series import render_metric_trace
from visualization.figures.temperature_field import render_temperature_field

REFERENCE_POINT = (400.0, 20.0)
MODE_NAMES = ("raw", "union", "llm")
LAYOUT_COMPONENT_SHIFT_THRESHOLD = 0.02


def render_assets(target: str | Path, *, hires: bool = False) -> list[Path]:
    """Render one or more concrete bundles from a suite, mode, or bundle root."""
    target_path = Path(target)
    concrete_roots = resolve_render_targets(target_path)
    if not concrete_roots:
        raise ValueError(f"No renderable optimizer bundle found under {target_path}.")

    rendered: list[Path] = []
    for concrete_root in concrete_roots:
        render_run_assets(concrete_root, hires=hires)
        rendered.append(concrete_root)

    mode_roots = _resolve_mode_roots(target_path)
    for mode_root in mode_roots:
        _cleanup_mode_root_outputs(mode_root)
        if mode_root.name == "llm":
            build_llm_decision_summaries(mode_root)
        else:
            build_mode_summaries(mode_root)
    return rendered


def resolve_render_targets(target: str | Path) -> list[Path]:
    path = Path(target)
    if is_concrete_optimizer_run_root(path):
        return [path]
    if (path / "seeds").is_dir():
        return iter_mode_seed_roots(path)
    mode_roots = [path / mode for mode in MODE_NAMES if (path / mode).is_dir()]
    if mode_roots:
        concrete: list[Path] = []
        for mode_root in mode_roots:
            concrete.extend(iter_mode_seed_roots(mode_root))
        return concrete
    return []


def render_run_assets(run_root: str | Path, *, hires: bool = False) -> None:
    run_root = Path(run_root)
    _cleanup_render_outputs(run_root)
    traces = run_root / "traces"
    analytics = run_root / "analytics"
    figures = run_root / "figures"
    tables = run_root / "tables"
    analytics.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    events = normalize_evaluation_rows(list(iter_jsonl(resolve_seed_trace_path(run_root, "evaluation_events.jsonl"))))
    summaries = rollup_per_generation(events, reference_point=REFERENCE_POINT)
    _write_hypervolume_csv(analytics / "hypervolume.csv", summaries)
    if summaries:
        render_hypervolume_progress(
            series={_mode_label(run_root): [(row["generation"], row["hypervolume"]) for row in summaries]},
            output=figures / "hypervolume_progress.png",
            hires=hires,
        )

    pareto_points = _extract_feasible_front(events)
    _write_pareto_csv(analytics / "pareto_front.csv", pareto_points)
    if pareto_points:
        render_pareto_front(
            fronts={_mode_label(run_root): pareto_points},
            output=figures / "pareto_front.png",
            hires=hires,
        )

    operator_rows = _load_operator_rows(run_root)
    controller_rows = _load_controller_rows(run_root)
    heatmap_grid = operator_phase_heatmap(operator_rows, controller_rows)
    _write_operator_phase_heatmap_csv(analytics / "operator_phase_heatmap.csv", heatmap_grid)
    if heatmap_grid:
        render_operator_heatmap(
            grid=heatmap_grid,
            output=figures / "operator_phase_heatmap.png",
            hires=hires,
        )

    optimization_result = _load_optional_json(run_root / "optimization_result.json")
    progress_rows: list[dict[str, Any]] = []
    if optimization_result:
        progress_rows = build_progress_timeline(list(optimization_result.get("history", [])))
        _write_progress_timeline_csv(analytics / "progress_timeline.csv", progress_rows)
        if progress_rows:
            render_objective_progress(
                series={_mode_label(run_root): progress_rows},
                output=figures / "objective_progress.png",
                hires=hires,
            )
            render_metric_trace(
                series={_mode_label(run_root): progress_rows},
                current_key="current_temperature_max",
                best_key="best_temperature_max_so_far",
                ylabel="Temperature (K)",
                output=figures / "temperature_trace.png",
                hires=hires,
            )
            render_metric_trace(
                series={_mode_label(run_root): progress_rows},
                current_key="current_gradient_rms",
                best_key="best_gradient_rms_so_far",
                ylabel="Gradient RMS (K/m)",
                output=figures / "gradient_trace.png",
                hires=hires,
            )
            render_metric_trace(
                series={_mode_label(run_root): progress_rows},
                current_key="current_total_constraint_violation",
                best_key="best_total_constraint_violation_so_far",
                ylabel="Constraint violation",
                output=figures / "constraint_violation_progress.png",
                hires=hires,
            )

    llm_response_rows = _load_jsonl_rows(resolve_seed_trace_path(run_root, "llm_response_trace.jsonl"))
    if controller_rows:
        outcomes = decision_outcomes(
            controller_rows,
            llm_response_rows,
            operator_rows,
            evaluation_rows=events,
            reference_point=REFERENCE_POINT,
        )
        _write_dict_rows_csv(analytics / "decision_outcomes.csv", outcomes)

    representative_rows = _render_representative_fields(run_root, figures=figures, hires=hires)
    layout_frames = _build_layout_frames(run_root, optimization_result)
    if layout_frames:
        render_layout_snapshot(frame=layout_frames[0], output=figures / "layout_initial.png", hires=hires)
        render_layout_snapshot(frame=layout_frames[-1], output=figures / "layout_final.png", hires=hires)
        render_layout_evolution(
            frames=layout_frames,
            output_gif=figures / "layout_evolution.gif",
            frames_dir=figures / "layout_evolution_frames",
        )

    summary_rows = _build_summary_statistics(
        events=events,
        summaries=summaries,
        progress_rows=progress_rows,
        optimization_result=optimization_result,
        run_root=run_root,
    )
    _write_table_files(tables / "summary_statistics", summary_rows)
    _write_table_files(tables / "representative_points", representative_rows)
    if _mode_label(run_root) == "llm":
        build_llm_decision_summaries(run_root)
    else:
        build_mode_summaries(run_root)


def _resolve_mode_roots(target: Path) -> list[Path]:
    if target.name in MODE_NAMES and (target / "seeds").is_dir():
        return [target]
    return [target / mode for mode in MODE_NAMES if (target / mode).is_dir() and (target / mode / "seeds").is_dir()]


def _mode_label(run_root: Path) -> str:
    run_yaml_path = run_root / "run.yaml"
    if run_yaml_path.exists():
        payload = yaml.safe_load(run_yaml_path.read_text(encoding="utf-8")) or {}
        mode = payload.get("mode")
        if mode:
            return str(mode)
    parent_name = run_root.parent.name
    if parent_name in MODE_NAMES:
        return parent_name
    name = run_root.name
    return name.split("__", 1)[-1] if "__" in name else name


def _extract_feasible_front(events: Sequence[Mapping[str, Any]]) -> list[tuple[float, float]]:
    feasible_points = [
        (float(row["objectives"]["temperature_max"]), float(row["objectives"]["temperature_gradient_rms"]))
        for row in events
        if row.get("status") == "ok" and row.get("objectives")
    ]
    if not feasible_points:
        return []
    front_indices = pareto_front_indices(feasible_points)
    return [feasible_points[index] for index in front_indices]


def normalize_evaluation_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized_rows: list[dict[str, Any]] = []
    for raw_row in rows:
        payload = dict(raw_row)
        objectives = payload.get("objectives")
        if objectives is None:
            objective_values = dict(payload.get("objective_values", {}))
            objectives = {
                key: value
                for key, value in {
                    "temperature_max": _metric_lookup(objective_values, "temperature_max"),
                    "temperature_gradient_rms": _metric_lookup(objective_values, "temperature_gradient_rms"),
                }.items()
                if value is not None
            }
        status = payload.get("status")
        if status is None:
            status = "failed" if payload.get("failure_reason") else ("ok" if bool(payload.get("feasible", False)) else "infeasible")
        normalized_rows.append(
            {
                **payload,
                "generation": int(payload.get("generation", payload.get("generation_index", 0))),
                "eval_index": int(payload.get("eval_index", payload.get("evaluation_index", 0))),
                "objectives": dict(objectives or {}),
                "constraints": dict(payload.get("constraints", payload.get("constraint_values", {})) or {}),
                "status": str(status),
            }
        )
    return normalized_rows


def _load_operator_rows(run_root: Path) -> list[dict[str, Any]]:
    return _load_jsonl_rows(resolve_seed_trace_path(run_root, "operator_trace.jsonl"))


def _load_controller_rows(run_root: Path) -> list[dict[str, Any]]:
    jsonl_rows = _load_jsonl_rows(resolve_seed_trace_path(run_root, "controller_trace.jsonl"))
    return [_normalize_controller_row(row) for row in jsonl_rows]


def _normalize_controller_row(row: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(row)
    selected = payload.get("operator_selected", payload.get("selected_operator_id"))
    return {
        **payload,
        "decision_id": payload.get("decision_id"),
        "phase": payload.get("phase") or dict(payload.get("metadata", {})).get("policy_phase", ""),
        "operator_selected": selected,
        "selected_operator_id": selected,
    }


def _render_representative_fields(run_root: Path, *, figures: Path, hires: bool) -> list[dict[str, Any]]:
    representatives_root = run_root / "representatives"
    if not representatives_root.exists():
        return []

    rows: list[dict[str, Any]] = []
    for repr_root in sorted(path for path in representatives_root.iterdir() if path.is_dir()):
        panel_domain, layout = _load_representative_layout(repr_root)

        temperature_grid = _load_npz_grid(repr_root / "fields" / "temperature_grid.npz")
        gradient_grid = _load_npz_grid(repr_root / "fields" / "gradient_magnitude_grid.npz")
        temperature_figure_path = figures / f"temperature_field_{repr_root.name}.png"
        gradient_figure_path = figures / f"gradient_field_{repr_root.name}.png"
        if temperature_grid is not None:
            xs, ys = _grid_coordinates(temperature_grid.shape, panel_domain)
            render_temperature_field(
                grid=temperature_grid,
                xs=xs,
                ys=ys,
                output=temperature_figure_path,
                layout=layout,
                hotspot=_temperature_hotspot(temperature_grid, xs, ys),
                title=_representative_title(repr_root.name, "Temperature Field"),
                hires=hires,
            )
        if gradient_grid is not None:
            xs, ys = _grid_coordinates(gradient_grid.shape, panel_domain)
            render_gradient_field(
                grid=gradient_grid,
                xs=xs,
                ys=ys,
                output=gradient_figure_path,
                layout=layout,
                title=_representative_title(repr_root.name, "Gradient Field"),
                hires=hires,
            )

        evaluation_payload = _load_optional_yaml(repr_root / "evaluation.yaml")
        metric_values = dict(evaluation_payload.get("metric_values", {})) if evaluation_payload else {}
        rows.append(
            {
                "representative_id": repr_root.name,
                "temperature_max": _metric_lookup(metric_values, "temperature_max"),
                "temperature_gradient_rms": _metric_lookup(metric_values, "temperature_gradient_rms"),
                "temperature_figure": str(temperature_figure_path.relative_to(run_root).as_posix())
                if temperature_figure_path.exists()
                else None,
                "gradient_figure": str(gradient_figure_path.relative_to(run_root).as_posix())
                if gradient_figure_path.exists()
                else None,
            }
        )
    return rows


def _build_layout_frames(run_root: Path, optimization_result: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not optimization_result:
        return []
    seed_base = _load_seed_base_case(run_root)
    optimization_spec = _load_seed_optimization_spec(run_root)
    if seed_base is None or optimization_spec is None:
        return []

    history_rows = list(optimization_result.get("history", []))
    panel_meta = _layout_panel_metadata(run_root)
    default_legality_policy_id = _default_legality_policy_id(run_root)
    baseline_row: dict[str, Any] | None = None
    optimizer_rows: list[dict[str, Any]] = []
    for row in history_rows:
        if str(row.get("source", "")).strip().lower() == "baseline":
            baseline_row = dict(row)
            continue
        optimizer_rows.append(dict(row))

    frames: list[dict[str, Any]] = []
    if baseline_row is not None:
        baseline_frame = _layout_frame_from_record(
            seed_base,
            optimization_spec,
            baseline_row,
            generation=0,
            title="initial layout",
            default_legality_policy_id=default_legality_policy_id,
        )
        if baseline_frame is not None:
            baseline_frame["panel_meta"] = dict(panel_meta)
            frames.append(baseline_frame)

    milestone_frames = _build_best_so_far_layout_milestones(
        seed_base=seed_base,
        optimization_spec=optimization_spec,
        optimizer_rows=optimizer_rows,
        default_legality_policy_id=default_legality_policy_id,
    )
    for frame in milestone_frames:
        frame["panel_meta"] = dict(panel_meta)
        frames.append(frame)
    for frame_index, frame in enumerate(frames):
        frame["frame_index"] = frame_index
    if frames:
        frames[0]["title"] = "initial layout"
        frames[-1]["title"] = "final layout"
    return frames


def _select_generation_representative(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return dict(min(rows, key=_layout_record_rank))


def _build_best_so_far_layout_milestones(
    *,
    seed_base: Any,
    optimization_spec: Any,
    optimizer_rows: Sequence[Mapping[str, Any]],
    default_legality_policy_id: str = "",
) -> list[dict[str, Any]]:
    candidates = _best_so_far_layout_candidates(
        seed_base=seed_base,
        optimization_spec=optimization_spec,
        optimizer_rows=optimizer_rows,
        default_legality_policy_id=default_legality_policy_id,
    )
    if not candidates:
        return []

    first_feasible_index = next(
        (index for index, item in enumerate(candidates) if bool(item["record"].get("feasible", False))),
        None,
    )
    if first_feasible_index is None:
        milestone_candidates = candidates
    else:
        milestone_candidates = candidates[first_feasible_index:]
    if not milestone_candidates:
        return []

    kept: list[dict[str, Any]] = [dict(milestone_candidates[0]["frame"])]
    kept[-1]["title"] = _layout_milestone_title(dict(milestone_candidates[0]["record"]), kind="first")

    for candidate in milestone_candidates[1:-1]:
        candidate_frame = dict(candidate["frame"])
        if _component_layout_shift(kept[-1], candidate_frame) >= LAYOUT_COMPONENT_SHIFT_THRESHOLD:
            candidate_frame["title"] = _layout_milestone_title(dict(candidate["record"]), kind="shift")
            kept.append(candidate_frame)

    final_candidate = dict(milestone_candidates[-1]["frame"])
    final_eval = final_candidate.get("record_evaluation_index")
    if not kept or final_eval != kept[-1].get("record_evaluation_index"):
        final_candidate["title"] = _layout_milestone_title(dict(milestone_candidates[-1]["record"]), kind="final")
        kept.append(final_candidate)
    return kept


def _best_so_far_layout_candidates(
    *,
    seed_base: Any,
    optimization_spec: Any,
    optimizer_rows: Sequence[Mapping[str, Any]],
    default_legality_policy_id: str = "",
) -> list[dict[str, Any]]:
    best_row: dict[str, Any] | None = None
    candidates: list[dict[str, Any]] = []
    for row in optimizer_rows:
        row_payload = dict(row)
        if best_row is not None and _layout_record_rank(row_payload) >= _layout_record_rank(best_row):
            continue
        frame = _layout_frame_from_record(
            seed_base,
            optimization_spec,
            row_payload,
            generation=int(row_payload.get("generation", 0)),
            title="",
            default_legality_policy_id=default_legality_policy_id,
        )
        if frame is None:
            continue
        best_row = row_payload
        frame["record_evaluation_index"] = int(row_payload.get("evaluation_index", 0))
        candidates.append({"record": row_payload, "frame": frame})
    return candidates


def _layout_record_rank(row: Mapping[str, Any]) -> tuple[float, float, float, float, int]:
    return (
        0 if bool(row.get("feasible", False)) else 1,
        _constraint_violation(row),
        _objective_value(row, ("summary.temperature_max", "minimize_peak_temperature")),
        _objective_value(
            row,
            ("summary.temperature_gradient_rms", "minimize_temperature_gradient_rms"),
        ),
        int(row.get("evaluation_index", 0)),
    )


def _layout_milestone_title(record: Mapping[str, Any], *, kind: str) -> str:
    generation = int(record.get("generation", 0))
    evaluation_index = int(record.get("evaluation_index", 0))
    if kind == "first" and bool(record.get("feasible", False)):
        prefix = "first feasible"
    elif kind == "first":
        prefix = "best near-feasible"
    elif kind == "shift":
        prefix = "layout shift"
    else:
        prefix = "final best-so-far"
    return f"{prefix} · gen {generation} / eval {evaluation_index}"


def _component_layout_shift(previous_frame: Mapping[str, Any], candidate_frame: Mapping[str, Any]) -> float:
    previous_centers = _component_centers(previous_frame)
    candidate_centers = _component_centers(candidate_frame)
    if not previous_centers or len(previous_centers) != len(candidate_centers):
        return float("inf")
    panel_width = float(candidate_frame.get("panel_width", previous_frame.get("panel_width", 1.0)))
    panel_height = float(candidate_frame.get("panel_height", previous_frame.get("panel_height", 1.0)))
    diagonal = max((panel_width**2 + panel_height**2) ** 0.5, 1.0e-12)
    return max(
        (
            ((left[0] - right[0]) ** 2 + (left[1] - right[1]) ** 2) ** 0.5 / diagonal
            for left, right in zip(previous_centers, candidate_centers, strict=True)
        ),
        default=0.0,
    )


def _component_centers(frame: Mapping[str, Any]) -> list[tuple[float, float]]:
    centers: list[tuple[float, float]] = []
    for component in frame.get("components", []):
        outline = np.asarray(component.get("outline", []), dtype=np.float64)
        if outline.ndim != 2 or outline.shape[1] != 2 or outline.size == 0:
            continue
        center = outline.mean(axis=0)
        centers.append((float(center[0]), float(center[1])))
    return centers


def _layout_frame_from_record(
    base_case: Any,
    optimization_spec: Any,
    record: Mapping[str, Any],
    *,
    generation: int,
    title: str,
    default_legality_policy_id: str = "",
) -> dict[str, Any] | None:
    spec_payload = optimization_spec.to_dict() if hasattr(optimization_spec, "to_dict") else dict(optimization_spec)
    record_source = str(record.get("source", "")).strip().lower()
    try:
        vector_payload = _selected_layout_decision_vector(record)
        if vector_payload:
            values = _ordered_layout_vector_values(optimization_spec, vector_payload)
            legality_policy_id = str(record.get("legality_policy_id") or default_legality_policy_id or "")
            radiator_span_max = _layout_radiator_span_max(spec_payload)
            if legality_policy_id in {"", "projection_plus_local_restore"}:
                case_payload = repair_case_payload_from_vector(
                    base_case,
                    spec_payload,
                    values,
                    radiator_span_max=radiator_span_max,
                )
            else:
                case_payload = project_case_payload_from_vector(
                    base_case,
                    spec_payload,
                    np.asarray(values, dtype=np.float64),
                    radiator_span_max=radiator_span_max,
                )
        elif record_source == "baseline":
            case_payload = base_case.to_dict() if hasattr(base_case, "to_dict") else dict(base_case)
        else:
            return None
    except (KeyError, TypeError, ValueError):
        try:
            vector_payload = _selected_layout_decision_vector(record)
            values = _ordered_layout_vector_values(optimization_spec, vector_payload)
            case = apply_decision_vector(base_case, optimization_spec, values)
            case_payload = case.to_dict() if hasattr(case, "to_dict") else dict(case)
        except (KeyError, TypeError, ValueError):
            return None
    panel_domain = dict(case_payload["panel_domain"])
    components = []
    for component in case_payload["components"]:
        polygon = component_polygon(component)
        components.append(
            {
                "component_id": component["component_id"],
                "outline": [
                    [float(x_value), float(y_value)]
                    for x_value, y_value in list(polygon.exterior.coords)[:-1]
                ],
            }
        )
    return {
        "generation": int(generation),
        "title": title,
        "panel_width": float(panel_domain["width"]),
        "panel_height": float(panel_domain["height"]),
        "record_evaluation_index": int(record.get("evaluation_index", 0)),
        "components": components,
        "line_sinks": _serialize_line_sinks(case_payload["boundary_features"], panel_domain),
    }


def _selected_layout_decision_vector(record: Mapping[str, Any]) -> Mapping[str, Any]:
    for key in ("evaluated_decision_vector", "decision_vector", "proposal_decision_vector"):
        payload = record.get(key)
        if isinstance(payload, Mapping):
            return payload
    return {}


def _ordered_layout_vector_values(optimization_spec: Any, vector_payload: Mapping[str, Any]) -> list[float]:
    return [float(vector_payload[str(variable["variable_id"])]) for variable in optimization_spec.design_variables]


def _layout_radiator_span_max(spec_payload: Mapping[str, Any]) -> float | None:
    value = dict(spec_payload.get("algorithm", {})).get("parameters", {}).get("radiator_span_max")
    return None if value is None else float(value)


def _default_legality_policy_id(run_root: Path) -> str:
    run_yaml = _load_optional_yaml(run_root / "run.yaml")
    policies = run_yaml.get("policies") if isinstance(run_yaml, Mapping) else None
    if not isinstance(policies, Mapping):
        return ""
    return str(policies.get("legality") or "")


def _build_summary_statistics(
    *,
    events: Sequence[Mapping[str, Any]],
    summaries: Sequence[Mapping[str, Any]],
    progress_rows: Sequence[Mapping[str, Any]],
    optimization_result: Mapping[str, Any] | None,
    run_root: Path,
) -> list[dict[str, Any]]:
    aggregate_metrics = dict(optimization_result.get("aggregate_metrics", {})) if optimization_result else {}
    final_progress = dict(progress_rows[-1]) if progress_rows else {}
    pareto_points = _extract_feasible_front(events)
    return [
        {
            "mode": _mode_label(run_root),
            "optimizer_evaluations": aggregate_metrics.get("optimizer_num_evaluations", aggregate_metrics.get("num_evaluations")),
            "pde_evaluations": final_progress.get("pde_evaluations_so_far"),
            "solver_skipped_evaluations": final_progress.get("solver_skipped_evaluations_so_far"),
            "first_feasible_pde_eval": final_progress.get("first_feasible_pde_eval_so_far"),
            "pareto_size": len(pareto_points),
            "best_temperature_max": final_progress.get("best_temperature_max_so_far"),
            "best_gradient_rms": final_progress.get("best_gradient_rms_so_far"),
            "final_hypervolume": summaries[-1]["hypervolume"] if summaries else None,
        }
    ]


def _write_hypervolume_csv(path: Path, summaries: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["generation", "hypervolume"])
        for row in summaries:
            writer.writerow([row["generation"], row["hypervolume"]])


def _write_pareto_csv(path: Path, points: Sequence[tuple[float, float]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["temperature_max", "temperature_gradient_rms"])
        for temperature_max, gradient_rms in points:
            writer.writerow([temperature_max, gradient_rms])


def _write_operator_phase_heatmap_csv(path: Path, grid: Mapping[str, Mapping[str, int]]) -> None:
    phases: list[str] = []
    for counts in grid.values():
        for phase in counts:
            if phase not in phases:
                phases.append(phase)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["operator", *phases])
        for operator, counts in sorted(grid.items()):
            writer.writerow([operator, *(counts.get(phase, 0) for phase in phases)])


def _write_progress_timeline_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    _write_dict_rows_csv(path, rows)


def _write_dict_rows_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            key_text = str(key)
            if key_text not in fieldnames:
                fieldnames.append(key_text)
    with path.open("w", encoding="utf-8", newline="") as handle:
        if not fieldnames:
            handle.write("")
            return
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(value) for key, value in row.items()})


def _write_table_files(prefix: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    _write_dict_rows_csv(prefix.with_suffix(".csv"), rows)
    prefix.with_suffix(".tex").write_text(_rows_to_booktabs(rows), encoding="utf-8")


def _rows_to_booktabs(rows: Sequence[Mapping[str, Any]]) -> str:
    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            key_text = str(key)
            if key_text not in fieldnames:
                fieldnames.append(key_text)
    if not fieldnames:
        return "\\begin{tabular}{l}\n\\toprule\nNo data\\\\\n\\bottomrule\n\\end{tabular}\n"
    columns = "l" * len(fieldnames)
    lines = [
        f"\\begin{{tabular}}{{{columns}}}",
        "\\toprule",
        " & ".join(_latex_escape(name) for name in fieldnames) + " \\\\",
        "\\midrule",
    ]
    for row in rows:
        lines.append(
            " & ".join(_latex_escape(_csv_value(row.get(name))) for name in fieldnames) + " \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}", ""])
    return "\n".join(lines)


def _load_seed_base_case(run_root: Path) -> Any | None:
    optimization_spec_path, benchmark_seed = _seed_spec_and_seed(run_root)
    if optimization_spec_path is None or benchmark_seed is None:
        return None
    optimization_spec = load_optimization_spec(str(optimization_spec_path))
    payload = optimization_spec.to_dict()
    payload["benchmark_source"]["seed"] = int(benchmark_seed)
    return generate_benchmark_case(str(optimization_spec_path), optimization_spec.from_dict(payload))


def _load_seed_optimization_spec(run_root: Path):
    optimization_spec_path, benchmark_seed = _seed_spec_and_seed(run_root)
    if optimization_spec_path is None or benchmark_seed is None:
        return None
    optimization_spec = load_optimization_spec(str(optimization_spec_path))
    payload = optimization_spec.to_dict()
    payload["benchmark_source"]["seed"] = int(benchmark_seed)
    return optimization_spec.from_dict(payload)


def _seed_spec_and_seed(run_root: Path) -> tuple[str | None, int | None]:
    run_yaml = _load_optional_yaml(run_root / "run.yaml")
    if run_yaml:
        optimization_spec_path = run_yaml.get("specs", {}).get("optimization")
        benchmark_seed = run_yaml.get("seeds", {}).get("benchmark")
        if optimization_spec_path is not None and benchmark_seed is not None:
            resolved = _resolve_spec_path(run_root, str(optimization_spec_path))
            if resolved is not None:
                return str(resolved), int(benchmark_seed)

    mode_root = _nearest_mode_root(run_root)
    mode_manifest = _load_optional_json(mode_root / "manifest.json") if mode_root is not None else {}
    optimization_result = _load_optional_json(run_root / "optimization_result.json") or {}
    benchmark_seed = (
        optimization_result.get("run_meta", {}).get("benchmark_seed")
        or optimization_result.get("provenance", {}).get("benchmark_source", {}).get("seed")
    )
    optimization_spec_path = mode_manifest.get("optimization_spec_path")
    if optimization_spec_path is not None and benchmark_seed is not None:
        resolved = _resolve_spec_path(run_root, str(optimization_spec_path))
        if resolved is not None:
            return str(resolved), int(benchmark_seed)
    return None, None


def _nearest_mode_root(path: Path) -> Path | None:
    for candidate in [path, *path.parents]:
        if candidate.name in MODE_NAMES:
            return candidate
    return None


def _nearest_suite_root(path: Path) -> Path | None:
    for candidate in [path, *path.parents]:
        if (candidate / "shared" / "specs").is_dir():
            return candidate
    return None


def _resolve_spec_path(run_root: Path, raw_path: str) -> Path | None:
    candidate = Path(raw_path)
    if candidate.exists():
        return candidate
    mode_root = _nearest_mode_root(run_root)
    suite_root = _nearest_suite_root(run_root)
    if mode_root is not None and suite_root is not None:
        shared_snapshot = suite_root / "shared" / "specs" / f"{mode_root.name}.yaml"
        if shared_snapshot.exists():
            return shared_snapshot
    return None


def _load_npz_grid(path: Path) -> np.ndarray | None:
    if not path.exists():
        return None
    with np.load(path) as payload:
        if "values" in payload:
            return np.asarray(payload["values"], dtype=np.float64)
        if "grid" in payload:
            return np.asarray(payload["grid"], dtype=np.float64)
        first_key = next(iter(payload.files), None)
        if first_key is None:
            return None
        return np.asarray(payload[first_key], dtype=np.float64)


def _grid_coordinates(shape: tuple[int, int], panel_domain: Mapping[str, Any] | None) -> tuple[np.ndarray, np.ndarray]:
    height, width = shape
    panel_width = float((panel_domain or {}).get("width", 1.0))
    panel_height = float((panel_domain or {}).get("height", 1.0))
    xs = np.linspace(0.0, panel_width, width, dtype=np.float64)
    ys = np.linspace(0.0, panel_height, height, dtype=np.float64)
    return xs, ys


def _load_representative_layout(repr_root: Path) -> tuple[dict[str, Any], dict[str, Any] | None]:
    case_payload = _load_optional_yaml(repr_root / "case.yaml")
    panel_domain = dict(case_payload.get("panel_domain", {}))
    if not panel_domain:
        return {}, None

    components = []
    for component in case_payload.get("components", []):
        polygon = component_polygon(component)
        components.append(
            {
                "component_id": component["component_id"],
                "outline": [
                    [float(x_value), float(y_value)]
                    for x_value, y_value in list(polygon.exterior.coords)[:-1]
                ],
            }
        )
    layout = {
        "components": components,
        "line_sinks": _serialize_line_sinks(case_payload.get("boundary_features", []), panel_domain),
    }
    return panel_domain, layout


def _temperature_hotspot(grid: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> dict[str, float] | None:
    if grid.size == 0:
        return None
    row_index, col_index = np.unravel_index(np.nanargmax(grid), grid.shape)
    return {
        "x": float(xs[col_index]),
        "y": float(ys[row_index]),
        "value": float(grid[row_index, col_index]),
    }


def _load_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    return list(iter_jsonl(path))


def _load_optional_json(path: Path) -> dict[str, Any] | list[dict[str, Any]] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_optional_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _metric_lookup(metric_values: Mapping[str, Any], token: str) -> float | None:
    token_text = str(token)
    if token_text in metric_values:
        return float(metric_values[token_text])
    summary_key = token_text if token_text.startswith("summary.") else f"summary.{token_text}"
    if summary_key in metric_values:
        return float(metric_values[summary_key])
    for key, value in metric_values.items():
        if str(key) == token_text:
            return float(value)
    for key, value in metric_values.items():
        if token_text in str(key):
            return float(value)
    return None


def _constraint_violation(row: Mapping[str, Any]) -> float:
    constraint_values = dict(row.get("constraint_values", {}))
    if not constraint_values:
        return 0.0
    return float(sum(max(0.0, float(value)) for value in constraint_values.values()))


def _objective_value(row: Mapping[str, Any], keys: Sequence[str]) -> float:
    objective_values = dict(row.get("objective_values", {}))
    for key in keys:
        if key in objective_values:
            return float(objective_values[key])
    for key, value in objective_values.items():
        key_text = str(key)
        if any(token in key_text for token in keys):
            return float(value)
    return float("inf")


def _serialize_line_sinks(features: Sequence[Mapping[str, Any]], panel_domain: Mapping[str, Any]) -> list[dict[str, Any]]:
    panel_width = float(panel_domain["width"])
    panel_height = float(panel_domain["height"])
    rows: list[dict[str, Any]] = []
    for feature in features:
        if feature.get("kind") != "line_sink":
            continue
        edge = str(feature["edge"])
        start = float(feature["start"])
        end = float(feature["end"])
        if edge in {"top", "bottom"}:
            rows.append(
                {
                    "feature_id": str(feature["feature_id"]),
                    "edge": edge,
                    "start_x": start * panel_width,
                    "end_x": end * panel_width,
                }
            )
        else:
            rows.append(
                {
                    "feature_id": str(feature["feature_id"]),
                    "edge": edge,
                    "start_y": start * panel_height,
                    "end_y": end * panel_height,
                }
            )
    return rows


def _representative_title(representative_id: str, prefix: str) -> str:
    label_map = {
        "knee-candidate": "Knee",
        "min-peak-temperature": "Min Tmax",
        "min-temperature-gradient-rms": "Min Grad",
        "best-peak": "Min Tmax",
        "best-gradient": "Min Grad",
        "first-feasible": "First Feasible",
        "baseline": "Baseline",
    }
    return f"{prefix} | {label_map.get(representative_id, representative_id)}"


def _layout_panel_metadata(run_root: Path) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "Scenario": _scenario_label(run_root),
        "Algorithm": _algorithm_label(run_root),
        "Mode": _mode_label(run_root),
    }
    benchmark_seed = _benchmark_seed(run_root)
    if benchmark_seed is not None:
        metadata["Seed"] = benchmark_seed
    llm_model = _llm_model_label(run_root)
    if llm_model:
        metadata["Model"] = llm_model
    return metadata


def _algorithm_label(run_root: Path) -> str:
    run_yaml = _load_optional_yaml(run_root / "run.yaml")
    algorithm = run_yaml.get("algorithm", {})
    if isinstance(algorithm, Mapping):
        explicit_label = algorithm.get("label")
        if explicit_label:
            return str(explicit_label)
        backbone = algorithm.get("backbone")
        if backbone:
            return algorithm_label(str(backbone))
    return "NSGA-II"


def _scenario_label(run_root: Path) -> str:
    run_yaml = _load_optional_yaml(run_root / "run.yaml")
    optimization_spec_path = str(run_yaml.get("specs", {}).get("optimization", ""))
    if optimization_spec_path:
        stem = Path(optimization_spec_path).stem
        for suffix in ("_raw", "_union", "_llm"):
            if stem.endswith(suffix):
                return stem[: -len(suffix)]
        return stem
    parents = list(run_root.parents)
    if len(parents) >= 3:
        return parents[2].name
    return "unknown"


def _benchmark_seed(run_root: Path) -> int | None:
    run_yaml = _load_optional_yaml(run_root / "run.yaml")
    benchmark_seed = run_yaml.get("seeds", {}).get("benchmark")
    return None if benchmark_seed is None else int(benchmark_seed)


def _llm_model_label(run_root: Path) -> str | None:
    if _mode_label(run_root) != "llm":
        return None
    return resolve_llm_model_label(run_root)


def _csv_value(value: Any) -> Any:
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(value, ensure_ascii=True, sort_keys=True)
    return value


def _latex_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return (
        text.replace("\\", "\\textbackslash{}")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("_", "\\_")
        .replace("#", "\\#")
    )


def _cleanup_render_outputs(run_root: Path) -> None:
    figures_root = run_root / "figures"
    for pattern in (
        "pareto_front.*",
        "hypervolume_progress.*",
        "hypervolume_progress__*",
        "operator_phase_heatmap.*",
        "operator_phase_heatmap__*",
        "objective_progress.*",
        "temperature_trace.*",
        "gradient_trace.*",
        "constraint_violation_progress.*",
        "layout_initial.*",
        "layout_final.*",
        "layout_evolution.gif",
        "temperature_field_*.*",
        "gradient_field_*.*",
    ):
        for path in figures_root.glob(pattern):
            if path.is_file():
                path.unlink()
    layout_frames_root = figures_root / "layout_evolution_frames"
    if layout_frames_root.exists():
        shutil.rmtree(layout_frames_root)
    pdf_root = figures_root / "pdf"
    if pdf_root.exists():
        shutil.rmtree(pdf_root)
    for path in (
        run_root / "analytics" / "hypervolume.csv",
        run_root / "analytics" / "operator_phase_heatmap.csv",
        run_root / "analytics" / "decision_outcomes.csv",
        run_root / "analytics" / "progress_timeline.csv",
        run_root / "analytics" / "pareto_front.csv",
        run_root / "tables" / "summary_statistics.csv",
        run_root / "tables" / "summary_statistics.tex",
        run_root / "tables" / "representative_points.csv",
        run_root / "tables" / "representative_points.tex",
    ):
        if path.exists():
            path.unlink()


def _cleanup_mode_root_outputs(mode_root: Path) -> None:
    for directory_name in ("analytics", "figures", "tables"):
        directory = mode_root / directory_name
        if directory.exists():
            shutil.rmtree(directory)
