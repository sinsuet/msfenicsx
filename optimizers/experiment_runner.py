"""Single-mode multi-seed experiment runner for the NSGA-II paper ladder."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from evaluation.io import load_spec
from optimizers.artifacts import write_optimization_artifacts
from optimizers.experiment_layout import (
    allocate_experiment_root,
    build_experiment_manifest,
    initialize_experiment_directories,
    resolve_experiment_mode_id,
    resolve_scenario_template_id,
    save_experiment_manifest,
    snapshot_experiment_inputs,
)
from optimizers.experiment_summary import build_experiment_summaries
from optimizers.io import (
    generate_benchmark_case,
    load_optimization_spec,
    resolve_benchmark_template_path,
    resolve_evaluation_spec_path,
)
from optimizers.models import OptimizationSpec
from optimizers.drivers.raw_driver import run_raw_optimization
from optimizers.drivers.union_driver import run_union_optimization


def run_mode_experiment(
    *,
    optimization_spec_path: Path,
    benchmark_seeds: list[int],
    scenario_runs_root: Path,
    started_at: datetime | None = None,
) -> Path:
    optimization_spec = load_optimization_spec(optimization_spec_path)
    mode_id = resolve_experiment_mode_id(optimization_spec, strict_nsga2=True)
    template_path = resolve_benchmark_template_path(optimization_spec_path, optimization_spec)
    scenario_template_id = resolve_scenario_template_id(template_path)
    effective_seeds = (
        [int(seed) for seed in benchmark_seeds]
        if benchmark_seeds
        else [int(optimization_spec.benchmark_source["seed"])]
    )

    experiment_root = allocate_experiment_root(
        scenario_runs_root=scenario_runs_root,
        scenario_template_id=scenario_template_id,
        mode_id=mode_id,
        started_at=started_at,
    )
    initialize_experiment_directories(experiment_root)
    snapshot_paths = snapshot_experiment_inputs(
        experiment_root=experiment_root,
        optimization_spec_path=optimization_spec_path,
        optimization_spec=optimization_spec,
    )
    manifest = build_experiment_manifest(
        scenario_template_id=scenario_template_id,
        mode_id=mode_id,
        benchmark_seeds=effective_seeds,
        optimization_spec_path=optimization_spec_path,
        started_at=started_at,
    )
    manifest["snapshots"] = snapshot_paths
    save_experiment_manifest(experiment_root / "manifest.json", manifest)

    for seed in effective_seeds:
        seeded_spec = _with_benchmark_seed(optimization_spec, seed)
        base_case = generate_benchmark_case(optimization_spec_path, seeded_spec)
        evaluation_spec = load_spec(resolve_evaluation_spec_path(optimization_spec_path, seeded_spec))
        run = _dispatch_run(base_case, seeded_spec, evaluation_spec, optimization_spec_path)
        evaluation_payload = evaluation_spec.to_dict() if hasattr(evaluation_spec, "to_dict") else dict(evaluation_spec)
        write_optimization_artifacts(
            experiment_root / "runs" / f"seed-{seed}",
            run,
            mode_id=mode_id,
            seed=seed,
            objective_definitions=list(evaluation_payload["objectives"]),
        )

    build_experiment_summaries(experiment_root)
    _render_experiment_dashboards(experiment_root, mode_id)
    return experiment_root


def _dispatch_run(
    base_case: Any,
    optimization_spec: OptimizationSpec,
    evaluation_spec: Any,
    optimization_spec_path: Path,
) -> Any:
    if optimization_spec.algorithm["mode"] == "raw":
        return run_raw_optimization(
            base_case,
            optimization_spec,
            evaluation_spec,
            spec_path=optimization_spec_path,
        )
    return run_union_optimization(
        base_case,
        optimization_spec,
        evaluation_spec,
        spec_path=optimization_spec_path,
    )


def _with_benchmark_seed(spec: OptimizationSpec, benchmark_seed: int) -> OptimizationSpec:
    payload = deepcopy(spec.to_dict())
    payload["benchmark_source"]["seed"] = int(benchmark_seed)
    return OptimizationSpec.from_dict(payload)


def _render_experiment_dashboards(experiment_root: Path, mode_id: str) -> None:
    from visualization.controller_mechanism import render_controller_mechanism
    from visualization.llm_dashboard import render_llm_dashboard
    from visualization.optimizer_overview import render_optimizer_overview

    render_optimizer_overview(experiment_root)
    if mode_id in {"nsga2_union", "nsga2_llm"}:
        render_controller_mechanism(experiment_root)
    if mode_id == "nsga2_llm":
        render_llm_dashboard(experiment_root)
