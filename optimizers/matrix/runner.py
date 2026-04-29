from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Iterable

from optimizers.matrix.index import build_initial_index_rows, failed_retry_rows, read_run_index, write_run_index
from optimizers.matrix.leaf_executor import execute_leaf
from optimizers.matrix.models import MatrixConfig, MatrixLeaf
from optimizers.matrix.spec_snapshots import write_leaf_spec_snapshot


def run_matrix_block(
    matrix: MatrixConfig,
    *,
    matrix_root: str | Path,
    block_id: str,
    max_leaves: int | None = None,
) -> Path:
    root = Path(matrix_root)
    index_path = root / "run_index.csv"
    if block_id == "M4_rerun_failed_512eval":
        rows = failed_retry_rows(read_run_index(index_path))
        leaves = _leaves_for_retry_rows(matrix, rows)
    else:
        leaves = [leaf for leaf in matrix.expand_leaves() if leaf.block_id == block_id]
        if max_leaves is not None:
            leaves = leaves[: int(max_leaves)]
        rows = build_initial_index_rows(leaves, matrix_root=root)
    leaves_by_key = {_leaf_key(leaf): leaf for leaf in leaves}
    for row in rows:
        leaf = leaves_by_key[_row_key(row)]
        row["optimization_spec_snapshot"] = str(write_leaf_spec_snapshot(leaf, root))
    completed_rows = _run_rows_concurrently(
        rows,
        matrix=matrix,
        leaves_by_key=leaves_by_key,
        max_workers=_concurrent_runs_for_block(matrix, block_id),
    )
    if block_id == "M4_rerun_failed_512eval" and index_path.exists():
        all_rows = read_run_index(index_path) + completed_rows
    else:
        all_rows = completed_rows
    return write_run_index(index_path, all_rows)


def _run_rows_concurrently(
    rows: list[dict[str, str]],
    *,
    matrix: MatrixConfig,
    leaves_by_key: dict[tuple[str, str, str, str], MatrixLeaf],
    max_workers: int,
) -> list[dict[str, str]]:
    completed: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for row in rows:
            leaf = leaves_by_key[_row_key(row)]
            futures[executor.submit(_run_leaf_with_timing, row, matrix=matrix, leaf=leaf)] = row
        for future in as_completed(futures):
            completed.append(future.result())
    return completed


def _run_leaf_with_timing(row: dict[str, str], *, matrix: MatrixConfig, leaf: MatrixLeaf) -> dict[str, str]:
    updated = dict(row)
    updated["status"] = "running"
    updated["started_at"] = datetime.now().isoformat()
    started = time.monotonic()
    try:
        result = _run_leaf(updated, evaluation_workers=_evaluation_workers_for_leaf(matrix, leaf))
        updated.update(result)
        updated["status"] = result.get("status", "completed")
    except Exception as exc:
        updated["status"] = "failed"
        updated["failure_reason"] = str(exc)
    updated["finished_at"] = datetime.now().isoformat()
    updated["wall_seconds"] = f"{time.monotonic() - started:.6f}"
    return updated


def _run_leaf(row: dict[str, str], *, evaluation_workers: int) -> dict[str, str]:
    return execute_leaf(row, evaluation_workers=evaluation_workers)


def _evaluation_workers_for_leaf(matrix: MatrixConfig, leaf: MatrixLeaf) -> int:
    if leaf.mode == "raw":
        return matrix.resource_caps["raw"].evaluation_workers
    if leaf.mode == "union":
        return matrix.resource_caps["union"].evaluation_workers
    if leaf.llm_profile == "gemma4":
        return matrix.resource_caps["gemma4"].evaluation_workers
    return matrix.resource_caps["external_llm"].evaluation_workers


def _concurrent_runs_for_block(matrix: MatrixConfig, block_id: str) -> int:
    if block_id == "M1_raw_backbone_512eval":
        return matrix.resource_caps["raw"].concurrent_runs
    if block_id == "M2_nsga2_union_512eval":
        return matrix.resource_caps["union"].concurrent_runs
    if "gemma4" in block_id:
        return matrix.resource_caps["gemma4"].concurrent_runs
    if block_id.startswith("M3"):
        return matrix.resource_caps["external_llm"].concurrent_runs
    return 1


def _leaves_for_retry_rows(matrix: MatrixConfig, rows: Iterable[dict[str, str]]) -> list[MatrixLeaf]:
    leaves = {_leaf_key(leaf): leaf for leaf in matrix.expand_leaves()}
    return [leaves[_row_key(row)] for row in rows]


def _leaf_key(leaf: MatrixLeaf) -> tuple[str, str, str, str]:
    return (leaf.block_id, leaf.scenario_id, leaf.method_id, str(leaf.replicate_seed))


def _row_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    block_id = row["block_id"]
    if block_id == "M4_rerun_failed_512eval":
        block_id = _source_block_for_method(row["method_id"])
    return (block_id, row["scenario_id"], row["method_id"], row["replicate_seed"])


def _source_block_for_method(method_id: str) -> str:
    if method_id.endswith("_raw"):
        return "M1_raw_backbone_512eval"
    if method_id == "nsga2_union":
        return "M2_nsga2_union_512eval"
    if method_id.startswith("nsga2_llm_"):
        profile = method_id.removeprefix("nsga2_llm_")
        letters = {
            "gpt_5_4": "a",
            "qwen3_6_plus": "b",
            "glm_5": "c",
            "minimax_m2_5": "d",
            "deepseek_v4_flash": "e",
            "gemma4": "f",
        }
        return f"M3{letters[profile]}_llm_{profile}_512eval"
    raise ValueError(f"Unknown method_id: {method_id}")
