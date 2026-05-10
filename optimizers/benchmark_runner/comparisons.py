"""Campaign-local comparison planning."""

from __future__ import annotations

import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

from optimizers.comparison_artifacts import _collect_run_payload


def plan_campaign_comparisons(run_root: str | Path, *, compare_with: list[Path] | tuple[Path, ...] = ()) -> dict[str, Any]:
    root = Path(run_root)
    all_roots = [root, *[Path(path) for path in compare_with]]
    seed_runs = _collect_seed_runs(all_roots)
    comparisons_root = root / "comparisons"
    by_seed_paths: dict[str, str] = {}
    for seed, runs_by_method in sorted(seed_runs.items()):
        if len(runs_by_method) < 2:
            continue
        method_ids = _ordered_methods(runs_by_method)
        output = comparisons_root / "by_seed" / f"seed-{seed}" / _comparison_slug(method_ids)
        from optimizers.comparison_artifacts import build_comparison_bundle

        build_comparison_bundle(
            runs=[runs_by_method[method] for method in method_ids],
            output=output,
            comparison_kind="by_seed",
            suite_root=root,
            benchmark_seed=seed,
        )
        by_seed_paths[f"seed-{seed}:{_comparison_slug(method_ids)}"] = str(output.relative_to(root).as_posix())

    active_methods = _collect_root_methods(root)
    aggregate_path = _maybe_build_aggregate(root, seed_runs, required_methods=active_methods)
    manifest = {
        "run_root": str(root),
        "compare_with": [str(path) for path in compare_with],
        "by_seed_paths": by_seed_paths,
        "aggregate_path": aggregate_path,
    }
    comparisons_root.mkdir(parents=True, exist_ok=True)
    (comparisons_root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def _collect_seed_runs(roots: list[Path]) -> dict[int, dict[str, Path]]:
    rows: dict[int, dict[str, Path]] = defaultdict(dict)
    for root in roots:
        for method_root in sorted(path for path in root.iterdir() if path.is_dir()):
            seeds_root = method_root / "seeds"
            if not seeds_root.is_dir():
                continue
            for seed_root in sorted(seeds_root.glob("seed-*")):
                seed = int(seed_root.name.split("-", 1)[1])
                rows[seed][_method_id(seed_root)] = seed_root
    return dict(rows)


def _collect_root_methods(root: Path) -> set[str]:
    methods: set[str] = set()
    for method_root in sorted(path for path in root.iterdir() if path.is_dir()):
        seeds_root = method_root / "seeds"
        if not seeds_root.is_dir():
            continue
        seed_roots = sorted(seeds_root.glob("seed-*"))
        if seed_roots:
            methods.add(_method_id(seed_roots[0]))
    return methods


def _method_id(seed_root: Path) -> str:
    import yaml

    run_yaml = seed_root / "run.yaml"
    if run_yaml.exists():
        payload = yaml.safe_load(run_yaml.read_text(encoding="utf-8")) or {}
        explicit = payload.get("method_id")
        if explicit:
            return _canonical_method_id(str(explicit))
        mode = payload.get("mode")
        if mode:
            return _canonical_method_id(str(mode))
    return _canonical_method_id(seed_root.parent.parent.name)


def _canonical_method_id(method_id: str) -> str:
    method = str(method_id).strip()
    if method.startswith("nsga2_llm:"):
        return f"llm-{method.split(':', 1)[1]}"
    if method.startswith("nsga2-llm-"):
        return f"llm-{method.split('nsga2-llm-', 1)[1]}"
    return method.replace(":", "-")


def _ordered_methods(runs_by_method: dict[str, Path]) -> list[str]:
    return sorted(runs_by_method, key=_method_sort_key)


def _method_sort_key(method: str) -> tuple[int, str]:
    if method in {"raw", "nsga2_raw", "nsga2-raw"}:
        return (0, method)
    if method in {"union", "nsga2_union", "nsga2-union"}:
        return (1, method)
    if method.startswith("llm"):
        return (2, method)
    return (3, method)


def _comparison_slug(method_ids: list[str]) -> str:
    normalized = [
        "raw" if method in {"nsga2_raw", "nsga2-raw"} else "union" if method in {"nsga2_union", "nsga2-union"} else method
        for method in method_ids
    ]
    return "_vs_".join(normalized)


def _maybe_build_aggregate(
    root: Path,
    seed_runs: dict[int, dict[str, Path]],
    *,
    required_methods: set[str],
) -> str | None:
    if not seed_runs:
        return None
    all_methods = sorted({method for runs in seed_runs.values() for method in runs}, key=_method_sort_key)
    best_methods: list[str] = []
    best_shared_seeds: list[int] = []
    for width in range(len(all_methods), 1, -1):
        for methods in combinations(all_methods, width):
            if not required_methods.issubset(set(methods)):
                continue
            shared_seeds = [
                seed
                for seed, runs in sorted(seed_runs.items())
                if all(method in runs for method in methods)
            ]
            if len(shared_seeds) >= 2:
                best_methods = list(methods)
                best_shared_seeds = shared_seeds
                break
        if best_methods:
            break
    if not best_methods:
        return None
    output = root / "comparisons" / "aggregate" / _comparison_slug(best_methods)
    payloads = [
        _collect_run_payload(seed_runs[seed][method])
        for seed in best_shared_seeds
        for method in best_methods
    ]
    build_campaign_aggregate_bundle(
        payloads=payloads,
        output=output,
        method_ids=best_methods,
        benchmark_seeds=best_shared_seeds,
    )
    return str(output.relative_to(root).as_posix())


def build_campaign_aggregate_bundle(
    *,
    payloads: list[dict[str, Any]],
    output: Path,
    method_ids: list[str],
    benchmark_seeds: list[int],
) -> dict[str, Any]:
    from optimizers.comparison_artifacts import (
        _apply_shared_hypervolume_reference,
        _build_aggregate_suite_bundle,
    )

    reference_point = _apply_shared_hypervolume_reference(payloads)
    _build_aggregate_suite_bundle(
        payloads=payloads,
        output=output,
        hypervolume_reference_point=reference_point,
        hires=False,
    )
    return {
        "method_ids": list(method_ids),
        "benchmark_seeds": list(benchmark_seeds),
        "output": str(output),
    }
