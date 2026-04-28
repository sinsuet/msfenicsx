"""Structured compare bundle builders for external and suite-owned comparisons."""

from __future__ import annotations

import csv
import json
import shutil
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from optimizers.algorithm_identity import algorithm_label
from optimizers.analytics.loaders import iter_jsonl
from optimizers.analytics.pareto import pareto_front_indices
from optimizers.analytics.rollups import rollup_per_generation
from optimizers.render_assets import (
    REFERENCE_POINT,
    _grid_coordinates,
    _load_npz_grid,
    _load_representative_layout,
    normalize_evaluation_rows,
)
from optimizers.run_telemetry import build_progress_timeline
from optimizers.traces.llm_trace_io import iter_mode_seed_roots, resolve_llm_model_label
from visualization.figures.comparison_panels import (
    render_gradient_field_comparison,
    render_layout_comparison,
    render_pde_budget_accounting,
    render_progress_dashboard,
    render_seed_outcome_dashboard,
    render_summary_overview,
    render_temperature_field_comparison,
)
from visualization.figures.trace_series import (
    render_metric_band_comparison,
)

MODE_ORDER = ("raw", "union", "llm")


def build_comparison_bundle(
    *,
    runs: Sequence[Path],
    output: Path,
    comparison_kind: str = "external",
    suite_root: Path | None = None,
    benchmark_seed: int | None = None,
    hires: bool = False,
) -> dict[str, Any]:
    resolved_runs = [resolve_single_run_root(Path(run)) for run in runs]
    output = Path(output)
    _validate_external_output(resolved_runs, output)
    if output.exists():
        shutil.rmtree(output)
    analytics_root = output / "analytics"
    figures_root = output / "figures"
    tables_root = output / "tables"
    analytics_root.mkdir(parents=True, exist_ok=True)
    figures_root.mkdir(parents=True, exist_ok=True)
    tables_root.mkdir(parents=True, exist_ok=True)

    payloads = [_collect_run_payload(run_root) for run_root in resolved_runs]
    payloads.sort(key=lambda item: _series_sort_key(str(item["series_label"]), mode=str(item["mode"])))

    hypervolume_series = {
        str(payload["series_label"]): list(payload["hypervolume_series"])
        for payload in payloads
        if payload["hypervolume_series"]
    }
    progress_series = {
        str(payload["series_label"]): list(payload["progress_rows"])
        for payload in payloads
        if payload["progress_rows"]
    }
    summary_rows = [dict(payload["summary_row"]) for payload in payloads]
    timeline_rollups = [dict(payload["timeline_rollup"]) for payload in payloads]
    pairwise_rows = _pairwise_deltas(summary_rows)
    pde_budget_rows = _pde_budget_accounting_rows(progress_series)
    common_pde_cutoff_rows = _common_pde_cutoff_rows(progress_series)
    common_pde_cutoff = _common_pde_cutoff(progress_series)
    representative_panels = [
        dict(payload["representative_panel"])
        for payload in payloads
        if payload.get("representative_panel") is not None
    ]

    render_summary_overview(
        rows=summary_rows,
        output=figures_root / "summary_overview.png",
        title=_comparison_overview_title(benchmark_seed=benchmark_seed, comparison_kind=comparison_kind),
        hires=hires,
    )
    if representative_panels:
        render_layout_comparison(
            frames=[
                {**dict(panel["layout_frame"]), "title": _comparison_tile_title(panel)}
                for panel in representative_panels
            ],
            output=figures_root / "final_layout_comparison.png",
            title="Final Layout Comparison",
            hires=hires,
        )
        render_temperature_field_comparison(
            panels=[
                {
                    "grid": panel["temperature_grid"],
                    "xs": panel["xs"],
                    "ys": panel["ys"],
                    "layout": panel["layout"],
                    "hotspot": panel.get("temperature_hotspot"),
                    "title": _comparison_tile_title(panel),
                }
                for panel in representative_panels
                if panel.get("temperature_grid") is not None
            ],
            output=figures_root / "temperature_field_comparison.png",
            title="Temperature Field Comparison",
            hires=hires,
        )
        render_gradient_field_comparison(
            panels=[
                {
                    "grid": panel["gradient_grid"],
                    "xs": panel["xs"],
                    "ys": panel["ys"],
                    "layout": panel["layout"],
                    "title": _comparison_tile_title(panel),
                }
                for panel in representative_panels
                if panel.get("gradient_grid") is not None
            ],
            output=figures_root / "gradient_field_comparison.png",
            title="Gradient Field Comparison",
            hires=hires,
        )
    if progress_series or hypervolume_series:
        render_progress_dashboard(
            progress_series=progress_series,
            hypervolume_series=hypervolume_series,
            output=figures_root / "progress_dashboard.png",
            title=_progress_dashboard_title(benchmark_seed=benchmark_seed),
            hires=hires,
        )
        render_pde_budget_accounting(
            progress_series=progress_series,
            output=figures_root / "pde_budget_accounting.png",
            title=_pde_budget_accounting_title(benchmark_seed=benchmark_seed),
            common_pde_cutoff=common_pde_cutoff,
            hires=hires,
        )

    _write_json(analytics_root / "summary_rows.json", {"rows": summary_rows})
    _write_json(analytics_root / "timeline_rollups.json", {"rows": timeline_rollups})
    _write_json(analytics_root / "pde_budget_accounting.json", {"rows": pde_budget_rows})
    _write_json(analytics_root / "common_pde_cutoff.json", {"rows": common_pde_cutoff_rows})
    _write_table_files(tables_root / "summary_table", _summary_table_rows(summary_rows))
    _write_table_files(tables_root / "mode_metrics", summary_rows)
    _write_table_files(tables_root / "pairwise_deltas", pairwise_rows)
    _write_table_files(tables_root / "pde_budget_accounting", pde_budget_rows)
    _write_table_files(tables_root / "common_pde_cutoff", common_pde_cutoff_rows)

    manifest = {
        "comparison_kind": comparison_kind,
        "suite_root": None if suite_root is None else str(Path(suite_root)),
        "benchmark_seed": benchmark_seed,
        "mode_ids": [str(payload["mode"]) for payload in payloads],
        "series_labels": [str(payload["series_label"]) for payload in payloads],
        "run_roots": [str(payload["run_root"]) for payload in payloads],
        "created_at": datetime.now().isoformat(),
    }
    _write_json(output / "manifest.json", manifest)
    return {
        "manifest": manifest,
        "summary_rows": summary_rows,
        "timeline_rollups": timeline_rollups,
    }


def build_suite_comparisons(suite_root: str | Path, *, hires: bool = False) -> dict[str, Any]:
    suite_root = Path(suite_root)
    comparisons_root = suite_root / "comparisons"
    if comparisons_root.exists():
        shutil.rmtree(comparisons_root)

    seed_runs = _suite_seed_run_roots(suite_root)
    mode_ids = sorted(
        {mode for runs_by_mode in seed_runs.values() for mode in runs_by_mode},
        key=_mode_sort_key,
    )
    eligible_seed_runs = {
        seed: runs_by_mode
        for seed, runs_by_mode in seed_runs.items()
        if len(runs_by_mode) >= 2
    }
    if len(mode_ids) < 2 or not eligible_seed_runs:
        return {}

    benchmark_seeds = sorted(eligible_seed_runs)
    if len(benchmark_seeds) == 1:
        seed = benchmark_seeds[0]
        build_comparison_bundle(
            runs=_ordered_runs(eligible_seed_runs[seed]),
            output=comparisons_root,
            comparison_kind="single_seed",
            suite_root=suite_root,
            benchmark_seed=seed,
            hires=hires,
        )
        manifest = {
            "suite_root": str(suite_root),
            "mode_ids": mode_ids,
            "benchmark_seeds": benchmark_seeds,
            "comparison_kind": "single_seed",
            "by_seed_paths": {f"seed-{seed}": "."},
            "aggregate_path": None,
            "created_at": datetime.now().isoformat(),
        }
        _write_json(comparisons_root / "manifest.json", manifest)
        return manifest

    by_seed_paths: dict[str, str] = {}
    aggregate_payloads: list[dict[str, Any]] = []
    for seed in benchmark_seeds:
        seed_output = comparisons_root / "by_seed" / f"seed-{seed}"
        bundle = build_comparison_bundle(
            runs=_ordered_runs(eligible_seed_runs[seed]),
            output=seed_output,
            comparison_kind="by_seed",
            suite_root=suite_root,
            benchmark_seed=seed,
            hires=hires,
        )
        by_seed_paths[f"seed-{seed}"] = str(seed_output.relative_to(comparisons_root).as_posix())
        aggregate_payloads.extend(_collect_run_payload(run_root) for run_root in _ordered_runs(eligible_seed_runs[seed]))

    _build_aggregate_suite_bundle(
        payloads=aggregate_payloads,
        output=comparisons_root / "aggregate",
        hires=hires,
    )
    manifest = {
        "suite_root": str(suite_root),
        "mode_ids": mode_ids,
        "benchmark_seeds": benchmark_seeds,
        "comparison_kind": "multi_seed",
        "by_seed_paths": by_seed_paths,
        "aggregate_path": "aggregate",
        "created_at": datetime.now().isoformat(),
    }
    comparisons_root.mkdir(parents=True, exist_ok=True)
    _write_json(comparisons_root / "manifest.json", manifest)
    return manifest


def resolve_single_run_root(path: Path) -> Path:
    run_root = Path(path)
    if run_root.is_dir() and (run_root / "traces" / "evaluation_events.jsonl").exists():
        return run_root
    raise ValueError(
        "compare-runs expects each --run to be a concrete single-mode run root with traces/evaluation_events.jsonl."
    )


def _collect_run_payload(run_root: Path) -> dict[str, Any]:
    events = normalize_evaluation_rows(list(iter_jsonl(run_root / "traces" / "evaluation_events.jsonl")))
    front = _extract_final_front(events)
    hypervolume_rows = rollup_per_generation(events, reference_point=REFERENCE_POINT)
    hypervolume_series = [
        (int(row["generation"]), float(row["hypervolume"]))
        for row in hypervolume_rows
    ]
    progress_rows = _progress_rows(run_root)
    mode = _mode_of(run_root)
    benchmark_seed = _benchmark_seed_of(run_root)
    algorithm_seed = _algorithm_seed_of(run_root)
    algorithm = _algorithm_label_of(run_root)
    representative_panel = _load_compare_representative_panel(run_root, mode=mode, algorithm=algorithm)
    summary_row = {
        "mode": mode,
        "algorithm": algorithm,
        "model": _llm_model_of(run_root),
        "run": str(run_root),
        "benchmark_seed": benchmark_seed,
        "algorithm_seed": algorithm_seed,
        "front_size": len(front),
        "pde_evaluations": _final_progress_int(progress_rows, "pde_evaluations_so_far"),
        "solver_skipped_evaluations": _final_progress_int(progress_rows, "solver_skipped_evaluations_so_far"),
        "t_max_min": min((point[0] for point in front), default=None),
        "grad_rms_min": min((point[1] for point in front), default=None),
        "final_hypervolume": hypervolume_rows[-1]["hypervolume"] if hypervolume_rows else None,
        "first_feasible_pde_eval": _first_feasible_pde_eval(progress_rows),
        "feasible_rate": _final_progress_metric(progress_rows, "feasible_rate_so_far"),
        "best_temperature_max": _final_progress_metric(progress_rows, "best_temperature_max_so_far"),
        "best_gradient_rms": _final_progress_metric(progress_rows, "best_gradient_rms_so_far"),
        "final_constraint_violation": _final_progress_metric(progress_rows, "best_total_constraint_violation_so_far"),
    }
    summary_row["series_label"] = _series_label(summary_row)
    if representative_panel is not None:
        summary_row["representative_id"] = representative_panel["representative_id"]
    timeline_rollup = {
        "mode": mode,
        "series_label": summary_row["series_label"],
        "benchmark_seed": benchmark_seed,
        "progress_point_count": len(progress_rows),
        "hypervolume_point_count": len(hypervolume_rows),
        "first_feasible_pde_eval": summary_row["first_feasible_pde_eval"],
        "final_hypervolume": summary_row["final_hypervolume"],
    }
    return {
        "run_root": run_root,
        "mode": mode,
        "series_label": summary_row["series_label"],
        "front": front,
        "hypervolume_rows": hypervolume_rows,
        "hypervolume_series": hypervolume_series,
        "progress_rows": progress_rows,
        "summary_row": summary_row,
        "timeline_rollup": timeline_rollup,
        "representative_panel": representative_panel,
    }


def _build_aggregate_suite_bundle(
    *,
    payloads: Sequence[Mapping[str, Any]],
    output: Path,
    hires: bool,
) -> None:
    analytics_root = output / "analytics"
    figures_root = output / "figures"
    tables_root = output / "tables"
    analytics_root.mkdir(parents=True, exist_ok=True)
    figures_root.mkdir(parents=True, exist_ok=True)
    tables_root.mkdir(parents=True, exist_ok=True)

    rows = [dict(payload["summary_row"]) for payload in payloads]
    grouped_by_mode = _group_rows_by_mode(rows)
    grouped_payloads = _group_payloads_by_mode(payloads)
    temperature_bands = _progress_metric_bands(grouped_payloads, key="current_temperature_max")
    gradient_bands = _progress_metric_bands(grouped_payloads, key="current_gradient_rms")
    hypervolume_bands = _hypervolume_metric_bands(grouped_payloads)
    benchmark_seeds = sorted({int(row["benchmark_seed"]) for row in rows if row.get("benchmark_seed") is not None})

    if temperature_bands["xs"] and temperature_bands["bands"]:
        render_metric_band_comparison(
            xs=temperature_bands["xs"],
            bands=temperature_bands["bands"],
            ylabel="Current temperature (K)",
            output=figures_root / "temperature_trace_median_band.png",
            hires=hires,
        )
    if gradient_bands["xs"] and gradient_bands["bands"]:
        render_metric_band_comparison(
            xs=gradient_bands["xs"],
            bands=gradient_bands["bands"],
            ylabel="Current gradient RMS (K/m)",
            output=figures_root / "gradient_trace_median_band.png",
            hires=hires,
        )
    if hypervolume_bands["xs"] and hypervolume_bands["bands"]:
        render_metric_band_comparison(
            xs=hypervolume_bands["xs"],
            bands=hypervolume_bands["bands"],
            ylabel="Hypervolume",
            xlabel="Generation",
            output=figures_root / "hypervolume_iqr_comparison.png",
            hires=hires,
        )

    aggregate_rows = _aggregate_mode_summary(rows)
    win_rate_rows = _pairwise_win_rates(rows)
    render_summary_overview(
        rows=aggregate_rows,
        output=figures_root / "summary_overview.png",
        title=f"Across {len(benchmark_seeds)} Seeds",
        hires=hires,
    )
    render_seed_outcome_dashboard(
        rows=rows,
        output=figures_root / "seed_outcome_dashboard.png",
        title=f"Across {len(benchmark_seeds)} Seeds",
        hires=hires,
    )
    _write_json(analytics_root / "aggregate_mode_summary.json", {"rows": aggregate_rows})
    _write_json(analytics_root / "pairwise_win_rate.json", {"rows": win_rate_rows})
    _write_json(analytics_root / "seed_metric_rows.json", {"rows": rows})
    _write_table_files(tables_root / "per_seed_metrics", rows)
    _write_table_files(tables_root / "aggregate_mode_summary", aggregate_rows)
    _write_table_files(tables_root / "pairwise_win_rate", win_rate_rows)
    _write_json(
        output / "manifest.json",
        {
            "comparison_kind": "aggregate",
            "mode_ids": sorted(grouped_by_mode, key=_mode_sort_key),
            "benchmark_seeds": benchmark_seeds,
            "created_at": datetime.now().isoformat(),
        },
    )


def _suite_seed_run_roots(suite_root: Path) -> dict[int, dict[str, Path]]:
    rows: dict[int, dict[str, Path]] = defaultdict(dict)
    for mode in MODE_ORDER:
        mode_root = suite_root / mode
        if not (mode_root / "seeds").is_dir():
            continue
        for seed_root in iter_mode_seed_roots(mode_root):
            benchmark_seed = _benchmark_seed_of(seed_root)
            if benchmark_seed is None:
                continue
            rows[int(benchmark_seed)][mode] = seed_root
    return dict(rows)


def _ordered_runs(runs_by_mode: Mapping[str, Path]) -> list[Path]:
    return [runs_by_mode[mode] for mode in MODE_ORDER if mode in runs_by_mode]


def _validate_external_output(runs: Sequence[Path], output: Path) -> None:
    output_resolved = Path(output).resolve()
    for run_root in runs:
        run_resolved = Path(run_root).resolve()
        if output_resolved == run_resolved or output_resolved.is_relative_to(run_resolved):
            raise ValueError("compare-runs requires an external output path outside all source run roots.")


def _extract_final_front(events: Sequence[Mapping[str, Any]]) -> list[tuple[float, float]]:
    points = [
        (float(row["objectives"]["temperature_max"]), float(row["objectives"]["temperature_gradient_rms"]))
        for row in events
        if row.get("status") == "ok" and row.get("objectives")
    ]
    if not points:
        return []
    indices = pareto_front_indices(points)
    return [points[index] for index in indices]


def _progress_rows(run_root: Path) -> list[dict[str, Any]]:
    optimization_result_path = run_root / "optimization_result.json"
    if not optimization_result_path.exists():
        return []
    payload = json.loads(optimization_result_path.read_text(encoding="utf-8"))
    return build_progress_timeline(list(payload.get("history", [])))


def _mode_of(run_root: Path) -> str:
    run_yaml = _load_optional_yaml(run_root / "run.yaml")
    if run_yaml.get("mode"):
        return str(run_yaml["mode"])
    parent_name = run_root.parent.name
    if parent_name in MODE_ORDER:
        return parent_name
    if parent_name == "seeds" and run_root.parent.parent.name in MODE_ORDER:
        return run_root.parent.parent.name
    name = run_root.name
    return name.split("__", 1)[-1] if "__" in name else name


def _benchmark_seed_of(run_root: Path) -> int | None:
    run_yaml = _load_optional_yaml(run_root / "run.yaml")
    benchmark_seed = run_yaml.get("seeds", {}).get("benchmark")
    if benchmark_seed is not None:
        return int(benchmark_seed)
    optimization_result = _load_optional_json(run_root / "optimization_result.json")
    benchmark_seed = (
        optimization_result.get("run_meta", {}).get("benchmark_seed")
        or optimization_result.get("provenance", {}).get("benchmark_source", {}).get("seed")
    )
    return None if benchmark_seed is None else int(benchmark_seed)


def _algorithm_seed_of(run_root: Path) -> int | None:
    run_yaml = _load_optional_yaml(run_root / "run.yaml")
    algorithm_seed = run_yaml.get("seeds", {}).get("algorithm")
    if algorithm_seed is not None:
        return int(algorithm_seed)
    optimization_result = _load_optional_json(run_root / "optimization_result.json")
    algorithm_seed = optimization_result.get("run_meta", {}).get("algorithm_seed")
    return None if algorithm_seed is None else int(algorithm_seed)


def _algorithm_label_of(run_root: Path) -> str:
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


def _series_label(summary_row: Mapping[str, Any]) -> str:
    mode = str(summary_row.get("mode", "")).strip()
    algorithm = str(summary_row.get("algorithm", "")).strip()
    if not algorithm or algorithm == "NSGA-II":
        return mode
    return f"{algorithm} {mode}".strip()


def _row_series_label(row: Mapping[str, Any]) -> str:
    explicit = str(row.get("series_label", "")).strip()
    return explicit or _series_label(row)


def _first_feasible_pde_eval(rows: Sequence[Mapping[str, Any]]) -> int | None:
    for row in rows:
        if row.get("first_feasible_pde_eval_so_far") is not None:
            return int(row["first_feasible_pde_eval_so_far"])
    return None


def _final_progress_metric(rows: Sequence[Mapping[str, Any]], key: str) -> float | None:
    for row in reversed(rows):
        if row.get(key) is not None:
            return float(row[key])
    return None


def _final_progress_int(rows: Sequence[Mapping[str, Any]], key: str) -> int | None:
    value = _final_progress_metric(rows, key)
    return None if value is None else int(value)


def _summary_table_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "mode": row.get("mode"),
            "series_label": row.get("series_label"),
            "algorithm": row.get("algorithm"),
            "model": row.get("model"),
            "representative_id": row.get("representative_id"),
            "benchmark_seed": row.get("benchmark_seed"),
            "front_size": row.get("front_size"),
            "pde_evaluations": row.get("pde_evaluations"),
            "solver_skipped_evaluations": row.get("solver_skipped_evaluations"),
            "first_feasible_pde_eval": row.get("first_feasible_pde_eval"),
            "best_temperature_max": row.get("best_temperature_max"),
            "best_gradient_rms": row.get("best_gradient_rms"),
            "feasible_rate": row.get("feasible_rate"),
            "final_hypervolume": row.get("final_hypervolume"),
        }
        for row in rows
    ]


def _pde_budget_accounting_rows(
    progress_series: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for mode, series in _ordered_progress_series(progress_series):
        final_row = _last_progress_row(series)
        if final_row is None:
            continue
        optimizer_proposals = _progress_count(final_row, "optimizer_evaluations_so_far")
        pde_evaluations = _progress_count(final_row, "pde_evaluations_so_far")
        cheap_skipped = _progress_count(final_row, "solver_skipped_evaluations_so_far")
        rows.append(
            {
                "mode": mode,
                "optimizer_proposals": optimizer_proposals,
                "pde_evaluations": pde_evaluations,
                "cheap_screen_skipped": cheap_skipped,
                "proposal_accounting_total": None
                if pde_evaluations is None or cheap_skipped is None
                else pde_evaluations + cheap_skipped,
                "pde_attempt_rate": _safe_ratio(pde_evaluations, optimizer_proposals),
                "cheap_skip_rate": _safe_ratio(cheap_skipped, optimizer_proposals),
            }
        )
    return rows


def _common_pde_cutoff_rows(
    progress_series: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    cutoff = _common_pde_cutoff(progress_series)
    if cutoff is None:
        return []
    rows: list[dict[str, Any]] = []
    for mode, series in _ordered_progress_series(progress_series):
        cutoff_row = _row_at_pde_cutoff(series, cutoff)
        if cutoff_row is None:
            continue
        rows.append(
            {
                "mode": mode,
                "common_pde_cutoff": cutoff,
                "optimizer_proposals_at_cutoff": _progress_count(cutoff_row, "optimizer_evaluations_so_far"),
                "pde_evaluations_at_cutoff": _progress_count(cutoff_row, "pde_evaluations_so_far"),
                "cheap_screen_skipped_at_cutoff": _progress_count(
                    cutoff_row,
                    "solver_skipped_evaluations_so_far",
                ),
                "best_temperature_max_at_cutoff": cutoff_row.get("best_temperature_max_so_far"),
                "best_gradient_rms_at_cutoff": cutoff_row.get("best_gradient_rms_so_far"),
                "feasible_rate_at_cutoff": cutoff_row.get("feasible_rate_so_far"),
                "best_constraint_violation_at_cutoff": cutoff_row.get("best_total_constraint_violation_so_far"),
            }
        )
    return rows


def _common_pde_cutoff(progress_series: Mapping[str, Sequence[Mapping[str, Any]]]) -> int | None:
    final_counts: list[int] = []
    for _mode, series in _ordered_progress_series(progress_series):
        final_row = _last_progress_row(series)
        if final_row is None:
            continue
        pde_evaluations = _progress_count(final_row, "pde_evaluations_so_far")
        if pde_evaluations is not None:
            final_counts.append(pde_evaluations)
    return min(final_counts) if final_counts else None


def _ordered_progress_series(
    progress_series: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[tuple[str, Sequence[Mapping[str, Any]]]]:
    return sorted(
        ((str(mode), rows) for mode, rows in progress_series.items()),
        key=lambda item: _series_sort_key(item[0]),
    )


def _last_progress_row(rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    for row in reversed(rows):
        if row.get("optimizer_evaluations_so_far") is not None:
            return row
    return rows[-1] if rows else None


def _row_at_pde_cutoff(rows: Sequence[Mapping[str, Any]], cutoff: int) -> Mapping[str, Any] | None:
    candidate: Mapping[str, Any] | None = None
    for row in rows:
        pde_count = _progress_count(row, "pde_evaluations_so_far")
        if pde_count is None:
            continue
        candidate = row
        if pde_count >= cutoff:
            return row
    return candidate


def _progress_count(row: Mapping[str, Any], key: str) -> int | None:
    value = row.get(key)
    return None if value is None else int(value)


def _safe_ratio(numerator: int | None, denominator: int | None) -> float | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return float(numerator / denominator)


def _pairwise_deltas(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    ordered_rows = sorted(rows, key=lambda row: _series_sort_key(_row_series_label(row), mode=str(row.get("mode", ""))))
    pairs: list[dict[str, Any]] = []
    for left, right in combinations(ordered_rows, 2):
        pairs.append(
            {
                "left_label": _row_series_label(left),
                "right_label": _row_series_label(right),
                "left_mode": left.get("mode"),
                "right_mode": right.get("mode"),
                "delta_first_feasible_pde_eval": _delta(
                    left.get("first_feasible_pde_eval"),
                    right.get("first_feasible_pde_eval"),
                ),
                "delta_best_temperature_max": _delta(
                    left.get("best_temperature_max"),
                    right.get("best_temperature_max"),
                ),
                "delta_best_gradient_rms": _delta(
                    left.get("best_gradient_rms"),
                    right.get("best_gradient_rms"),
                ),
                "delta_final_hypervolume": _delta(
                    left.get("final_hypervolume"),
                    right.get("final_hypervolume"),
                ),
            }
        )
    return pairs


def _aggregate_mode_summary(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped = _group_rows_by_mode(rows)
    summary_rows: list[dict[str, Any]] = []
    for mode, mode_rows in sorted(grouped.items(), key=lambda item: _mode_sort_key(item[0])):
        summary_rows.append(
            {
                "mode": mode,
                "algorithm": next((row.get("algorithm") for row in mode_rows if row.get("algorithm")), None),
                "model": next((row.get("model") for row in mode_rows if row.get("model")), None),
                "seed_count": len(mode_rows),
                "pde_evaluations_mean": _mean(_numeric_values(mode_rows, "pde_evaluations")),
                "solver_skipped_evaluations_mean": _mean(_numeric_values(mode_rows, "solver_skipped_evaluations")),
                "first_feasible_pde_eval_mean": _mean(_numeric_values(mode_rows, "first_feasible_pde_eval")),
                "feasible_rate_mean": _mean(_numeric_values(mode_rows, "feasible_rate")),
                "best_temperature_max_mean": _mean(_numeric_values(mode_rows, "best_temperature_max")),
                "best_gradient_rms_mean": _mean(_numeric_values(mode_rows, "best_gradient_rms")),
                "final_hypervolume_mean": _mean(_numeric_values(mode_rows, "final_hypervolume")),
            }
        )
    return summary_rows


def _pairwise_win_rates(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        seed = row.get("benchmark_seed")
        mode = row.get("mode")
        if seed is None or mode is None:
            continue
        grouped[str(mode)][int(seed)] = dict(row)

    results: list[dict[str, Any]] = []
    modes = sorted(grouped, key=_mode_sort_key)
    for left_mode, right_mode in combinations(modes, 2):
        shared_seeds = sorted(set(grouped[left_mode]) & set(grouped[right_mode]))
        if not shared_seeds:
            continue
        results.append(
            {
                "left_mode": left_mode,
                "right_mode": right_mode,
                "shared_seed_count": len(shared_seeds),
                "first_feasible_pde_win_rate": _win_rate(
                    [grouped[left_mode][seed].get("first_feasible_pde_eval") for seed in shared_seeds],
                    [grouped[right_mode][seed].get("first_feasible_pde_eval") for seed in shared_seeds],
                    lower_is_better=True,
                ),
                "temperature_win_rate": _win_rate(
                    [grouped[left_mode][seed].get("best_temperature_max") for seed in shared_seeds],
                    [grouped[right_mode][seed].get("best_temperature_max") for seed in shared_seeds],
                    lower_is_better=True,
                ),
                "gradient_win_rate": _win_rate(
                    [grouped[left_mode][seed].get("best_gradient_rms") for seed in shared_seeds],
                    [grouped[right_mode][seed].get("best_gradient_rms") for seed in shared_seeds],
                    lower_is_better=True,
                ),
                "feasible_rate_win_rate": _win_rate(
                    [grouped[left_mode][seed].get("feasible_rate") for seed in shared_seeds],
                    [grouped[right_mode][seed].get("feasible_rate") for seed in shared_seeds],
                    lower_is_better=False,
                ),
                "hypervolume_win_rate": _win_rate(
                    [grouped[left_mode][seed].get("final_hypervolume") for seed in shared_seeds],
                    [grouped[right_mode][seed].get("final_hypervolume") for seed in shared_seeds],
                    lower_is_better=False,
                ),
            }
        )
    return results


def _group_rows_by_mode(rows: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        mode = row.get("mode")
        if mode is None:
            continue
        grouped[str(mode)].append(dict(row))
    return dict(grouped)


def _progress_metric_bands(
    grouped_payloads: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    key: str,
) -> dict[str, Any]:
    xs = sorted(
        {
            int(row["pde_evaluation_index"])
            for payloads in grouped_payloads.values()
            for payload in payloads
            for row in payload.get("progress_rows", [])
            if row.get(key) is not None and row.get("pde_evaluation_index") is not None
        }
    )
    bands = {
        mode: _sequence_band(
            xs=xs,
            rows_by_seed=[payload.get("progress_rows", []) for payload in payloads],
            x_key="pde_evaluation_index",
            value_key=key,
            forward_fill=True,
        )
        for mode, payloads in grouped_payloads.items()
    }
    return {
        "xs": xs,
        "bands": {mode: band for mode, band in bands.items() if band is not None},
    }


def _hypervolume_metric_bands(grouped_payloads: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, Any]:
    xs = sorted(
        {
            int(row["generation"])
            for payloads in grouped_payloads.values()
            for payload in payloads
            for row in payload.get("hypervolume_rows", [])
            if row.get("generation") is not None and row.get("hypervolume") is not None
        }
    )
    bands = {
        mode: _sequence_band(
            xs=xs,
            rows_by_seed=[payload.get("hypervolume_rows", []) for payload in payloads],
            x_key="generation",
            value_key="hypervolume",
            forward_fill=True,
        )
        for mode, payloads in grouped_payloads.items()
    }
    return {
        "xs": xs,
        "bands": {mode: band for mode, band in bands.items() if band is not None},
    }


def _sequence_band(
    *,
    xs: Sequence[int],
    rows_by_seed: Sequence[Sequence[Mapping[str, Any]]],
    x_key: str,
    value_key: str,
    forward_fill: bool,
) -> dict[str, list[float]] | None:
    median_values: list[float] = []
    p25_values: list[float] = []
    p75_values: list[float] = []
    for x_value in xs:
        values = [
            value
            for rows in rows_by_seed
            for value in [_row_value(rows, x_key=x_key, x_value=x_value, value_key=value_key, forward_fill=forward_fill)]
            if value is not None
        ]
        if not values:
            return None
        median_values.append(float(np.median(values)))
        p25_values.append(float(np.percentile(values, 25)))
        p75_values.append(float(np.percentile(values, 75)))
    return {
        "median": median_values,
        "p25": p25_values,
        "p75": p75_values,
    }


def _row_value(
    rows: Sequence[Mapping[str, Any]],
    *,
    x_key: str,
    x_value: int,
    value_key: str,
    forward_fill: bool,
) -> float | None:
    candidate: float | None = None
    for row in rows:
        row_x = row.get(x_key)
        if row_x is None:
            continue
        row_value = row.get(value_key)
        if row_value is None:
            continue
        row_x_int = int(row_x)
        if row_x_int == x_value:
            return float(row_value)
        if forward_fill and row_x_int < x_value:
            candidate = float(row_value)
        if row_x_int > x_value:
            break
    return candidate


def _group_payloads_by_mode(payloads: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for payload in payloads:
        mode = payload.get("mode")
        if mode is None:
            continue
        grouped[str(mode)].append(dict(payload))
    return dict(grouped)


def _write_table_files(base_path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    _write_rows_csv(base_path.with_suffix(".csv"), rows)
    base_path.with_suffix(".tex").write_text(_rows_to_booktabs(rows), encoding="utf-8")


def _write_rows_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    fieldnames = _fieldnames(rows)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: _csv_value(row.get(name)) for name in fieldnames})


def _rows_to_booktabs(rows: Sequence[Mapping[str, Any]]) -> str:
    fieldnames = _fieldnames(rows)
    lines = [
        "\\begin{tabular}{" + "l" * max(1, len(fieldnames)) + "}",
        "\\toprule",
        " & ".join(fieldnames) + " \\\\",
        "\\midrule",
    ]
    for row in rows:
        lines.append(" & ".join(_latex_escape(_csv_value(row.get(name))) for name in fieldnames) + " \\\\")
    lines.extend(["\\bottomrule", "\\end{tabular}", ""])
    return "\n".join(lines)


def _fieldnames(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    if not rows:
        return ["empty"]
    seen: list[str] = []
    for row in rows:
        for key in row.keys():
            key_text = str(key)
            if key_text not in seen:
                seen.append(key_text)
    return seen


def _delta(left: Any, right: Any) -> float | None:
    if left is None or right is None:
        return None
    return float(left) - float(right)


def _numeric_values(rows: Sequence[Mapping[str, Any]], key: str) -> list[float]:
    return [float(row[key]) for row in rows if row.get(key) is not None]


def _mean(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return float(sum(values) / float(len(values)))


def _win_rate(left_values: Sequence[Any], right_values: Sequence[Any], *, lower_is_better: bool) -> float | None:
    scores: list[float] = []
    for left, right in zip(left_values, right_values, strict=True):
        if left is None or right is None:
            continue
        left_value = float(left)
        right_value = float(right)
        if np.isclose(left_value, right_value):
            scores.append(0.5)
        elif lower_is_better:
            scores.append(1.0 if left_value < right_value else 0.0)
        else:
            scores.append(1.0 if left_value > right_value else 0.0)
    if not scores:
        return None
    return float(sum(scores) / float(len(scores)))


def _mode_sort_key(mode: str) -> int:
    return MODE_ORDER.index(mode) if mode in MODE_ORDER else len(MODE_ORDER)


def _series_sort_key(series_label: str, *, mode: str | None = None) -> tuple[int, int, str]:
    mode_text = str(mode or "").strip()
    label_text = str(series_label).strip()
    raw_priority = 0 if label_text == "raw" else 1
    if mode_text:
        return (_mode_sort_key(mode_text), raw_priority, label_text)
    for candidate in MODE_ORDER:
        if label_text == candidate or label_text.endswith(f" {candidate}"):
            return (_mode_sort_key(candidate), raw_priority, label_text)
    return (len(MODE_ORDER), raw_priority, label_text)


def _comparison_overview_title(*, benchmark_seed: int | None, comparison_kind: str) -> str:
    if benchmark_seed is not None:
        return f"Mode Summary | Seed {benchmark_seed}"
    if comparison_kind == "aggregate":
        return "Across Seeds"
    return "Mode Summary"


def _progress_dashboard_title(*, benchmark_seed: int | None) -> str:
    return f"Progress Dashboard | Seed {benchmark_seed}" if benchmark_seed is not None else "Progress Dashboard"


def _pde_budget_accounting_title(*, benchmark_seed: int | None) -> str:
    return f"PDE Budget Accounting | Seed {benchmark_seed}" if benchmark_seed is not None else "PDE Budget Accounting"


def _comparison_tile_title(panel: Mapping[str, Any]) -> str:
    mode = str(panel.get("series_label") or panel.get("mode", "")).upper()
    model = panel.get("model")
    label = str(panel.get("display_label") or panel.get("representative_id") or "")
    if model:
        return f"{mode}\n{model}\n{label}"
    return f"{mode}\n{label}"


def _load_compare_representative_panel(run_root: Path, *, mode: str, algorithm: str) -> dict[str, Any] | None:
    representatives_root = run_root / "representatives"
    if not representatives_root.is_dir():
        return None
    repr_root = _select_compare_representative_root(representatives_root)
    if repr_root is None:
        return None
    panel_domain, layout = _load_representative_layout(repr_root)
    if not panel_domain or layout is None:
        return None
    temperature_grid = _load_npz_grid(repr_root / "fields" / "temperature_grid.npz")
    gradient_grid = _load_npz_grid(repr_root / "fields" / "gradient_magnitude_grid.npz")
    grid_shape = temperature_grid.shape if temperature_grid is not None else gradient_grid.shape if gradient_grid is not None else None
    if grid_shape is None:
        return None
    xs, ys = _grid_coordinates(grid_shape, panel_domain)
    return {
        "mode": mode,
        "algorithm": algorithm,
        "series_label": _series_label({"mode": mode, "algorithm": algorithm}),
        "model": _llm_model_of(run_root),
        "representative_id": repr_root.name,
        "display_label": _representative_display_label(repr_root.name),
        "layout": layout,
        "layout_frame": {
            "generation": 0,
            "title": "",
            "panel_width": float(panel_domain.get("width", 1.0)),
            "panel_height": float(panel_domain.get("height", 1.0)),
            "components": list(layout.get("components", [])),
            "line_sinks": list(layout.get("line_sinks", [])),
        },
        "temperature_grid": temperature_grid,
        "gradient_grid": gradient_grid,
        "temperature_hotspot": _grid_hotspot(temperature_grid, xs, ys),
        "xs": xs,
        "ys": ys,
    }


def _select_compare_representative_root(representatives_root: Path) -> Path | None:
    priority = (
        "knee-candidate",
        "knee",
        "min-peak-temperature",
        "min-temperature-max",
        "best-peak",
        "min-temperature-gradient-rms",
        "best-gradient",
        "first-feasible",
        "baseline",
    )
    for name in priority:
        candidate = representatives_root / name
        if candidate.is_dir():
            return candidate
    directories = sorted(path for path in representatives_root.iterdir() if path.is_dir())
    return directories[0] if directories else None


def _representative_display_label(representative_id: str) -> str:
    mapping = {
        "knee-candidate": "Knee",
        "knee": "Knee",
        "min-peak-temperature": "Min Tmax",
        "min-temperature-max": "Min Tmax",
        "best-peak": "Min Tmax",
        "min-temperature-gradient-rms": "Min Grad",
        "best-gradient": "Min Grad",
        "first-feasible": "First Feasible",
        "baseline": "Baseline",
    }
    return mapping.get(representative_id, representative_id)


def _grid_hotspot(grid: np.ndarray | None, xs: np.ndarray, ys: np.ndarray) -> dict[str, float] | None:
    if grid is None or grid.size == 0:
        return None
    row_index, col_index = np.unravel_index(np.nanargmax(grid), grid.shape)
    return {
        "x": float(xs[col_index]),
        "y": float(ys[row_index]),
        "value": float(grid[row_index, col_index]),
    }


def _llm_model_of(run_root: Path) -> str | None:
    if _mode_of(run_root) != "llm":
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


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _load_optional_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2) + "\n", encoding="utf-8")
