"""Subprocess supervisor for benchmark leaves."""

from __future__ import annotations

import csv
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml

from optimizers.benchmark_runner.specs import BenchmarkLeaf, CampaignSpec


LEAF_ENV_DEFAULTS = {
    "PYTHONUNBUFFERED": "1",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
    "MPLBACKEND": "Agg",
    "CUDA_VISIBLE_DEVICES": "",
}

RUN_INDEX_FIELDS = [
    "campaign_id",
    "scenario_id",
    "method_id",
    "method_slug",
    "mode",
    "llm_profile",
    "benchmark_seed",
    "algorithm_seed",
    "population_size",
    "num_generations",
    "evaluation_workers",
    "status",
    "started_at",
    "finished_at",
    "wall_seconds",
    "output_root",
    "failure_reason",
]


@dataclass(frozen=True)
class LeafExecution:
    leaf: BenchmarkLeaf
    output_root: Path
    process: subprocess.Popen
    started_at: datetime
    monotonic_start: float


def build_leaf_command(leaf: BenchmarkLeaf, *, output_root: Path) -> list[str]:
    cmd = [
        "python",
        "-m",
        "optimizers.benchmark_runner.leaf_entrypoint",
        "--optimization-spec",
        str(leaf.optimization_spec),
        "--mode",
        leaf.mode,
        "--benchmark-seed",
        str(leaf.benchmark_seed),
        "--algorithm-seed",
        str(leaf.algorithm_seed),
        "--population-size",
        str(leaf.population_size),
        "--num-generations",
        str(leaf.num_generations),
        "--evaluation-workers",
        str(leaf.evaluation_workers),
        "--output-root",
        str(output_root),
        "--method-id",
        leaf.method_id,
    ]
    if leaf.llm_profile:
        cmd.extend(["--llm-profile", leaf.llm_profile])
    return cmd


def run_campaign_supervisor(campaign: CampaignSpec, *, run_id: str | None = None) -> Path:
    effective_run_id = run_id or _build_run_id(campaign)
    run_root = campaign.scenario_runs_root / campaign.scenario_id / effective_run_id
    run_root.mkdir(parents=True, exist_ok=True)
    _write_campaign_manifest(campaign, run_root)
    run_index_path = run_root / "run_index.csv"
    _write_run_index_header(run_index_path)

    pending = list(campaign.leaves)
    active: list[LeafExecution] = []
    while pending or active:
        while pending and len(active) < campaign.resource_policy.max_concurrent_leaves:
            leaf = pending.pop(0)
            output_root = run_root / leaf.method_slug / "seeds" / f"seed-{leaf.benchmark_seed}"
            output_root.mkdir(parents=True, exist_ok=True)
            env = dict(os.environ)
            env.update(LEAF_ENV_DEFAULTS)
            process = subprocess.Popen(build_leaf_command(leaf, output_root=output_root), env=env, cwd=Path.cwd())
            active.append(
                LeafExecution(
                    leaf=leaf,
                    output_root=output_root,
                    process=process,
                    started_at=datetime.now(),
                    monotonic_start=time.monotonic(),
                )
            )
        still_active: list[LeafExecution] = []
        for execution in active:
            return_code = execution.process.poll()
            if return_code is None:
                still_active.append(execution)
                continue
            _append_run_index_row(
                run_index_path,
                campaign=campaign,
                execution=execution,
                status="completed" if return_code == 0 else "failed",
                failure_reason="" if return_code == 0 else f"exit_code={return_code}",
            )
        active = still_active
        if active:
            time.sleep(0.2)
    return run_root


def _build_run_id(campaign: CampaignSpec) -> str:
    slug = "_".join(_ordered_unique(_run_slug_for_leaf(leaf) for leaf in campaign.leaves))
    return f"{datetime.now():%m%d_%H%M}__{slug}"


def _run_slug_for_leaf(leaf: BenchmarkLeaf) -> str:
    if leaf.method_id == "nsga2_raw":
        return "raw"
    if leaf.method_id == "nsga2_union":
        return "union"
    if leaf.method_id.startswith("llm_direct:"):
        return leaf.method_slug
    if leaf.mode == "llm":
        return f"llm-{leaf.llm_profile or 'default'}"
    return leaf.method_slug


def _ordered_unique(values) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value)
        if text not in result:
            result.append(text)
    return result


def _write_campaign_manifest(campaign: CampaignSpec, run_root: Path) -> None:
    payload = {
        "campaign_id": campaign.campaign_id,
        "scenario_id": campaign.scenario_id,
        "resource_policy": {
            "max_concurrent_leaves": campaign.resource_policy.max_concurrent_leaves,
            "leaf_evaluation_workers": campaign.resource_policy.leaf_evaluation_workers,
        },
        "comparison_policy": {
            "by_seed": campaign.comparison_policy.by_seed,
            "aggregate": campaign.comparison_policy.aggregate,
        },
        "compare_with": [str(path) for path in campaign.compare_with],
        "leaf_count": len(campaign.leaves),
    }
    (run_root / "campaign.yaml").write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _write_run_index_header(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        csv.DictWriter(handle, fieldnames=RUN_INDEX_FIELDS).writeheader()


def _append_run_index_row(
    path: Path,
    *,
    campaign: CampaignSpec,
    execution: LeafExecution,
    status: str,
    failure_reason: str,
) -> None:
    wall_seconds = time.monotonic() - execution.monotonic_start
    leaf = execution.leaf
    row = {
        "campaign_id": campaign.campaign_id,
        "scenario_id": leaf.scenario_id,
        "method_id": leaf.method_id,
        "method_slug": leaf.method_slug,
        "mode": leaf.mode,
        "llm_profile": leaf.llm_profile or "",
        "benchmark_seed": leaf.benchmark_seed,
        "algorithm_seed": leaf.algorithm_seed,
        "population_size": leaf.population_size,
        "num_generations": leaf.num_generations,
        "evaluation_workers": leaf.evaluation_workers,
        "status": status,
        "started_at": execution.started_at.isoformat(),
        "finished_at": datetime.now().isoformat(),
        "wall_seconds": f"{wall_seconds:.3f}",
        "output_root": str(execution.output_root),
        "failure_reason": failure_reason,
    }
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RUN_INDEX_FIELDS)
        writer.writerow(row)
