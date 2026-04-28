"""Run one or more paper-facing modes under a single s1_typical run root."""

from __future__ import annotations

import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from evaluation.io import load_spec
from optimizers.artifacts import write_optimization_artifacts
from optimizers.comparison_artifacts import build_suite_comparisons
from optimizers.drivers.raw_driver import run_raw_optimization
from optimizers.drivers.union_driver import run_union_optimization
from optimizers.io import (
    generate_benchmark_case,
    load_optimization_spec,
    resolve_benchmark_template_path,
    resolve_evaluation_spec_path,
)
from optimizers.models import OptimizationSpec
from optimizers.run_layout import (
    build_run_id,
    initialize_mode_root,
    initialize_run_root,
    write_manifest,
)
from optimizers.run_manifest import write_run_manifest


def run_benchmark_suite(
    *,
    optimization_spec_paths: Sequence[Path],
    benchmark_seeds: Sequence[int],
    scenario_runs_root: Path,
    modes: Sequence[str] | None = None,
    evaluation_workers: int | None = None,
    population_size: int | None = None,
    num_generations: int | None = None,
    skip_render: bool = False,
    started_at: datetime | None = None,
) -> Path:
    if not optimization_spec_paths:
        raise ValueError("run_benchmark_suite requires at least one optimization spec path.")

    loaded_specs = [
        (Path(spec_path), load_optimization_spec(spec_path))
        for spec_path in optimization_spec_paths
    ]
    from optimizers.cli import _temporary_env_overlay, _llm_env_overlay_for_spec, apply_algorithm_overrides
    for _, spec in loaded_specs:
        apply_algorithm_overrides(
            spec.algorithm,
            population_size=population_size,
            num_generations=num_generations,
        )
    selected_modes = _normalize_modes(modes or [resolve_suite_mode_id(spec) for _, spec in loaded_specs])
    spec_by_mode = {
        resolve_suite_mode_id(spec): (spec_path, spec)
        for spec_path, spec in loaded_specs
    }
    missing_modes = [mode for mode in selected_modes if mode not in spec_by_mode]
    if missing_modes:
        raise ValueError(f"Missing optimization specs for modes: {missing_modes}.")

    primary_spec_path, primary_spec = spec_by_mode[selected_modes[0]]
    template_path = resolve_benchmark_template_path(primary_spec_path, primary_spec)
    scenario_template_id = _resolve_template_id(template_path)
    effective_seeds = list(benchmark_seeds) if benchmark_seeds else [int(primary_spec.benchmark_source["seed"])]
    _validate_benchmark_seed_policy(
        scenario_template_id=scenario_template_id,
        benchmark_seeds=effective_seeds,
    )
    effective_started_at = datetime.now() if started_at is None else started_at
    run_id = build_run_id(effective_started_at, selected_modes)
    run_root = initialize_run_root(
        scenario_runs_root,
        scenario_template_id=scenario_template_id,
        run_id=run_id,
        modes=selected_modes,
    )

    _snapshot_shared_inputs(run_root, spec_by_mode, selected_modes)
    write_manifest(
        run_root / "manifest.json",
        {
            "scenario_template_id": scenario_template_id,
            "run_id": run_id,
            "mode_ids": list(selected_modes),
            "benchmark_seeds": list(effective_seeds),
            "created_at": effective_started_at.isoformat(),
            "directories": {
                "shared": "shared",
                **{mode: mode for mode in selected_modes},
            },
        },
    )

    for mode in selected_modes:
        spec_path, optimization_spec = spec_by_mode[mode]
        mode_root = initialize_mode_root(run_root, mode=mode)
        write_manifest(
            mode_root / "manifest.json",
            {
                "mode_id": mode,
                "optimization_spec_path": str(spec_path),
                "benchmark_seeds": list(effective_seeds),
                "directories": {
                    "summaries": "summaries",
                    "seeds": "seeds",
                },
            },
        )
        for seed in effective_seeds:
            seeded_spec = _with_benchmark_seed(optimization_spec, seed)
            base_case = generate_benchmark_case(spec_path, seeded_spec)
            evaluation_spec_path_for_seed = resolve_evaluation_spec_path(spec_path, seeded_spec)
            evaluation_spec = load_spec(evaluation_spec_path_for_seed)
            _wall_start = time.monotonic()
            with _temporary_env_overlay(_llm_env_overlay_for_spec(seeded_spec)):
                run = _dispatch_run(
                    base_case,
                    seeded_spec,
                    evaluation_spec,
                    spec_path,
                    evaluation_workers=evaluation_workers,
                    trace_output_root=mode_root / "seeds" / f"seed-{seed}",
                )
            _wall_seconds = time.monotonic() - _wall_start
            evaluation_payload = evaluation_spec.to_dict() if hasattr(evaluation_spec, "to_dict") else dict(evaluation_spec)
            write_optimization_artifacts(
                mode_root / "seeds" / f"seed-{seed}",
                run,
                mode_id=mode,
                seed=seed,
                objective_definitions=list(evaluation_payload["objectives"]),
            )
            write_run_manifest(
                mode_root / "seeds" / f"seed-{seed}" / "run.yaml",
                mode=mode,
                algorithm_family=str(seeded_spec.algorithm["family"]),
                algorithm_backbone=str(seeded_spec.algorithm["backbone"]),
                benchmark_seed=int(seed),
                algorithm_seed=int(seeded_spec.algorithm["seed"]),
                optimization_spec_path=str(spec_path),
                evaluation_spec_path=str(evaluation_spec_path_for_seed),
                population_size=int(seeded_spec.algorithm["population_size"]),
                num_generations=int(seeded_spec.algorithm["num_generations"]),
                wall_seconds=_wall_seconds,
                legality_policy_id=str(seeded_spec.evaluation_protocol["legality_policy_id"]),
            )
        if not skip_render:
            from optimizers.render_assets import render_assets
            render_assets(mode_root, hires=False)
    if not skip_render:
        build_suite_comparisons(run_root)
    return run_root


def resolve_suite_mode_id(optimization_spec: OptimizationSpec | dict[str, Any]) -> str:
    payload = optimization_spec.to_dict() if hasattr(optimization_spec, "to_dict") else dict(optimization_spec)
    if payload["algorithm"]["mode"] == "raw":
        return "raw"
    operator_control = payload.get("operator_control") or {}
    if operator_control.get("controller") == "llm":
        return "llm"
    return "union"


def _normalize_modes(modes: Sequence[str]) -> list[str]:
    requested = {str(mode) for mode in modes}
    ordered = [mode for mode in ("raw", "union", "llm") if mode in requested]
    if not ordered:
        raise ValueError("run_benchmark_suite requires at least one supported mode.")
    return ordered


def _resolve_template_id(template_path: Path) -> str:
    import yaml

    payload = yaml.safe_load(template_path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        template_meta = payload.get("template_meta")
        if isinstance(template_meta, dict) and template_meta.get("template_id"):
            return str(template_meta["template_id"])
    return template_path.stem


def _validate_benchmark_seed_policy(*, scenario_template_id: str, benchmark_seeds: Sequence[int]) -> None:
    unique_seeds = {int(seed) for seed in benchmark_seeds}
    if scenario_template_id == "s1_typical" and len(unique_seeds) > 1:
        raise ValueError("s1_typical is a fixed single benchmark_seed case; pass exactly one benchmark_seed.")


def _snapshot_shared_inputs(
    run_root: Path,
    spec_by_mode: dict[str, tuple[Path, OptimizationSpec]],
    selected_modes: Sequence[str],
) -> None:
    shared_root = run_root / "shared"
    (shared_root / "specs").mkdir(parents=True, exist_ok=True)
    snapshots: dict[str, str] = {}
    for mode in selected_modes:
        spec_path, optimization_spec = spec_by_mode[mode]
        destination = shared_root / "specs" / f"{mode}.yaml"
        destination.write_text(Path(spec_path).read_text(encoding="utf-8"), encoding="utf-8")
        snapshots[mode] = str(destination.relative_to(run_root).as_posix())
        template_path = resolve_benchmark_template_path(spec_path, optimization_spec)
        evaluation_path = resolve_evaluation_spec_path(spec_path, optimization_spec)
        template_destination = shared_root / "scenario_template.yaml"
        evaluation_destination = shared_root / "evaluation_spec.yaml"
        if not template_destination.exists():
            template_destination.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")
        if not evaluation_destination.exists():
            evaluation_destination.write_text(evaluation_path.read_text(encoding="utf-8"), encoding="utf-8")
    write_manifest(
        shared_root / "manifest.json",
        {
            "snapshots": snapshots,
            "scenario_template": "shared/scenario_template.yaml",
            "evaluation_spec": "shared/evaluation_spec.yaml",
        },
    )


def _dispatch_run(
    base_case: Any,
    optimization_spec: OptimizationSpec,
    evaluation_spec: Any,
    optimization_spec_path: Path,
    *,
    evaluation_workers: int | None = None,
    trace_output_root: Path | None = None,
) -> Any:
    if optimization_spec.algorithm["mode"] == "raw":
        return run_raw_optimization(
            base_case,
            optimization_spec,
            evaluation_spec,
            spec_path=optimization_spec_path,
            evaluation_workers=evaluation_workers,
        )
    return run_union_optimization(
        base_case,
        optimization_spec,
        evaluation_spec,
        spec_path=optimization_spec_path,
        evaluation_workers=evaluation_workers,
        trace_output_root=trace_output_root,
    )


def _with_benchmark_seed(spec: OptimizationSpec, benchmark_seed: int) -> OptimizationSpec:
    payload = deepcopy(spec.to_dict())
    payload["benchmark_source"]["seed"] = int(benchmark_seed)
    return OptimizationSpec.from_dict(payload)
