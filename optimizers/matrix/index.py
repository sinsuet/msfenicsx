from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from optimizers.matrix.models import MatrixLeaf

INDEX_COLUMNS = [
    "matrix_id",
    "block_id",
    "scenario_id",
    "method_id",
    "algorithm_family",
    "algorithm_backbone",
    "mode",
    "llm_profile",
    "replicate_seed",
    "benchmark_seed",
    "algorithm_seed",
    "population_size",
    "num_generations",
    "nominal_budget",
    "optimization_spec_snapshot",
    "evaluation_spec_path",
    "template_path",
    "run_root",
    "attempt",
    "previous_attempt",
    "status",
    "failure_reason",
    "started_at",
    "finished_at",
    "wall_seconds",
    "actual_evaluations",
    "feasible_count",
    "render_status",
    "trace_status",
    "git_commit",
    "git_dirty",
    "spec_hash",
    "template_hash",
    "evaluation_spec_hash",
    "environment_summary_hash",
]

FAILED_STATUSES = {"failed", "timeout", "missing_artifacts", "render_failed"}


def build_initial_index_rows(leaves: Iterable[MatrixLeaf], *, matrix_root: str | Path) -> list[dict[str, str]]:
    root = Path(matrix_root)
    rows: list[dict[str, str]] = []
    for leaf in leaves:
        run_root = root / leaf.block_id / leaf.scenario_id / leaf.method_id / f"r{leaf.replicate_seed}" / "attempt-1"
        rows.append(_row_for_leaf(leaf, run_root=run_root, attempt=1, previous_attempt=""))
    return rows


def failed_retry_rows(rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    retries: list[dict[str, str]] = []
    for row in rows:
        if str(row.get("status", "")).strip() not in FAILED_STATUSES:
            continue
        if str(row.get("attempt", "1")) != "1":
            continue
        retry = dict(row)
        retry["attempt"] = "2"
        retry["previous_attempt"] = "1"
        retry["status"] = "pending"
        retry["failure_reason"] = ""
        retry["started_at"] = ""
        retry["finished_at"] = ""
        retry["wall_seconds"] = ""
        retry["actual_evaluations"] = ""
        retry["feasible_count"] = ""
        retry["render_status"] = ""
        retry["trace_status"] = ""
        retry["run_root"] = str(Path(row["run_root"]).parent / "attempt-2")
        retries.append(retry)
    return retries


def write_run_index(path: str | Path, rows: Iterable[dict[str, str]]) -> Path:
    index_path = Path(path)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=INDEX_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: str(row.get(column, "")) for column in INDEX_COLUMNS})
    return index_path


def read_run_index(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _row_for_leaf(leaf: MatrixLeaf, *, run_root: Path, attempt: int, previous_attempt: str) -> dict[str, str]:
    return {
        "matrix_id": leaf.matrix_id,
        "block_id": leaf.block_id,
        "scenario_id": leaf.scenario_id,
        "method_id": leaf.method_id,
        "algorithm_family": leaf.algorithm_family,
        "algorithm_backbone": leaf.algorithm_backbone,
        "mode": leaf.mode,
        "llm_profile": "" if leaf.llm_profile is None else leaf.llm_profile,
        "replicate_seed": str(leaf.replicate_seed),
        "benchmark_seed": str(leaf.benchmark_seed),
        "algorithm_seed": str(leaf.algorithm_seed),
        "population_size": str(leaf.population_size),
        "num_generations": str(leaf.num_generations),
        "nominal_budget": str(leaf.nominal_budget),
        "optimization_spec_snapshot": "",
        "evaluation_spec_path": "",
        "template_path": "",
        "run_root": str(run_root),
        "attempt": str(attempt),
        "previous_attempt": previous_attempt,
        "status": "pending",
        "failure_reason": "",
        "started_at": "",
        "finished_at": "",
        "wall_seconds": "",
        "actual_evaluations": "",
        "feasible_count": "",
        "render_status": "",
        "trace_status": "",
        "git_commit": "",
        "git_dirty": "",
        "spec_hash": "",
        "template_hash": "",
        "evaluation_spec_hash": "",
        "environment_summary_hash": "",
    }
