"""Parallel leaf execution for run-benchmark-suite."""

from __future__ import annotations

import csv
import logging
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from multiprocessing import get_context
from pathlib import Path
from typing import Any, Sequence

from evaluation.io import load_spec
from optimizers.artifacts import write_optimization_artifacts
from optimizers.io import generate_benchmark_case
from optimizers.run_manifest import write_run_manifest
from optimizers.run_suite import _dispatch_run, _with_benchmark_seed

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SuiteLeaf:
    mode: str
    seed: int
    spec_path: Path
    optimization_spec: Any
    evaluation_spec_path: Path


@dataclass
class LeafResult:
    mode: str
    seed: int
    status: str
    started_at: str
    finished_at: str
    wall_seconds: float
    output_root: str
    failure_reason: str | None = None


def expand_leaves(
    spec_by_mode: dict[str, tuple[Path, Any]],
    selected_modes: Sequence[str],
    effective_seeds: Sequence[int],
) -> list[SuiteLeaf]:
    leaves: list[SuiteLeaf] = []
    for mode in selected_modes:
        spec_path, optimization_spec = spec_by_mode[mode]
        from optimizers.run_suite import resolve_suite_mode_id
        from optimizers.io import resolve_evaluation_spec_path

        for seed in effective_seeds:
            seeded_spec = _with_benchmark_seed(optimization_spec, seed)
            eval_spec_path = resolve_evaluation_spec_path(spec_path, seeded_spec)
            leaves.append(
                SuiteLeaf(
                    mode=mode,
                    seed=int(seed),
                    spec_path=Path(spec_path),
                    optimization_spec=seeded_spec,
                    evaluation_spec_path=eval_spec_path,
                )
            )
    return leaves


def run_leaf(
    leaf: SuiteLeaf,
    *,
    evaluation_workers: int | None,
    llm_env_overlay: dict[str, str],
    mode_root: Path,
) -> LeafResult:
    output_root = mode_root / "seeds" / f"seed-{leaf.seed}"
    started_at = datetime.now()
    started = time.monotonic()
    try:
        base_case = generate_benchmark_case(leaf.spec_path, leaf.optimization_spec)
        evaluation_spec = load_spec(leaf.evaluation_spec_path)

        if llm_env_overlay:
            import os
            previous = {k: os.environ.get(k) for k in llm_env_overlay}
            os.environ.update(llm_env_overlay)
            try:
                run = _dispatch_run(
                    base_case,
                    leaf.optimization_spec,
                    evaluation_spec,
                    leaf.spec_path,
                    evaluation_workers=evaluation_workers,
                    trace_output_root=output_root,
                )
            finally:
                for k, v in previous.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v
        else:
            run = _dispatch_run(
                base_case,
                leaf.optimization_spec,
                evaluation_spec,
                leaf.spec_path,
                evaluation_workers=evaluation_workers,
                trace_output_root=output_root,
            )

        wall_seconds = time.monotonic() - started
        evaluation_payload = evaluation_spec.to_dict() if hasattr(evaluation_spec, "to_dict") else dict(evaluation_spec)
        write_optimization_artifacts(
            output_root,
            run,
            mode_id=leaf.mode,
            seed=leaf.seed,
            objective_definitions=list(evaluation_payload["objectives"]),
        )
        write_run_manifest(
            output_root / "run.yaml",
            mode=leaf.mode,
            algorithm_family=str(leaf.optimization_spec.algorithm["family"]),
            algorithm_backbone=str(leaf.optimization_spec.algorithm["backbone"]),
            benchmark_seed=leaf.seed,
            algorithm_seed=int(leaf.optimization_spec.algorithm["seed"]),
            optimization_spec_path=str(leaf.spec_path),
            evaluation_spec_path=str(leaf.evaluation_spec_path),
            population_size=int(leaf.optimization_spec.algorithm["population_size"]),
            num_generations=int(leaf.optimization_spec.algorithm["num_generations"]),
            wall_seconds=wall_seconds,
            legality_policy_id=str(leaf.optimization_spec.evaluation_protocol["legality_policy_id"]),
        )
        return LeafResult(
            mode=leaf.mode,
            seed=leaf.seed,
            status="completed",
            started_at=started_at.isoformat(),
            finished_at=datetime.now().isoformat(),
            wall_seconds=wall_seconds,
            output_root=str(output_root),
        )
    except Exception as exc:
        logger.error("Leaf %s seed %d failed: %s", leaf.mode, leaf.seed, exc)
        return LeafResult(
            mode=leaf.mode,
            seed=leaf.seed,
            status="failed",
            started_at=started_at.isoformat(),
            finished_at=datetime.now().isoformat(),
            wall_seconds=time.monotonic() - started,
            output_root=str(output_root),
            failure_reason=str(exc),
        )


def run_leaves_parallel(
    leaves: list[SuiteLeaf],
    *,
    max_concurrent: int,
    evaluation_workers: int | None,
    llm_env_overlay: dict[str, str],
    mode_roots: dict[str, Path],
    run_index_path: Path,
    continue_on_failure: bool = True,
) -> list[LeafResult]:
    results: list[LeafResult] = []
    ctx = get_context("fork")
    with ProcessPoolExecutor(max_workers=max_concurrent, mp_context=ctx) as executor:
        futures = {}
        for leaf in leaves:
            future = executor.submit(
                run_leaf,
                leaf,
                evaluation_workers=evaluation_workers,
                llm_env_overlay=llm_env_overlay,
                mode_root=mode_roots[leaf.mode],
            )
            futures[future] = leaf

        for future in as_completed(futures):
            leaf = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                logger.error("Leaf %s seed %d raised: %s", leaf.mode, leaf.seed, exc)
                result = LeafResult(
                    mode=leaf.mode,
                    seed=leaf.seed,
                    status="failed",
                    started_at="",
                    finished_at=datetime.now().isoformat(),
                    wall_seconds=0.0,
                    output_root=str(mode_roots[leaf.mode] / "seeds" / f"seed-{leaf.seed}"),
                    failure_reason=str(exc),
                )
            results.append(result)
            _append_run_index_row(run_index_path, result)

            if result.status == "failed" and not continue_on_failure:
                logger.error("Leaf %s seed %d failed, aborting remaining leaves", leaf.mode, leaf.seed)
                break

    return results


def write_run_index_header(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "mode", "seed", "population_size", "num_generations",
            "status", "started_at", "finished_at", "wall_seconds",
            "output_root", "failure_reason",
        ])


def _append_run_index_row(path: Path, result: LeafResult) -> None:
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            result.mode, result.seed, "", "",
            result.status, result.started_at, result.finished_at,
            f"{result.wall_seconds:.2f}", result.output_root,
            result.failure_reason or "",
        ])
