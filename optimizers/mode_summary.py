"""Derived per-mode summaries for the new s1_typical run tree."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from optimizers.run_telemetry import build_progress_milestones, build_progress_timeline, load_jsonl_rows
from optimizers.traces.llm_trace_io import iter_mode_seed_roots, resolve_seed_trace_path


def build_mode_summaries(mode_root: str | Path) -> dict[str, str]:
    root = Path(mode_root)
    summaries_root = root / "summaries"
    summaries_root.mkdir(parents=True, exist_ok=True)
    _cleanup_generated_mode_summaries(summaries_root)
    seed_rows: list[dict[str, Any]] = []
    written: dict[str, str] = {}

    for bundle_root in iter_mode_seed_roots(root):
        bundle_identity = _resolve_bundle_identity(bundle_root)
        seed_label = str(bundle_identity["label"])
        progress_rows = _load_progress_source_rows(bundle_root)
        timeline = build_progress_timeline(progress_rows)
        milestones = build_progress_milestones(timeline)
        timeline_path = summaries_root / f"progress_timeline__{seed_label}.jsonl"
        milestones_path = summaries_root / f"milestones__{seed_label}.json"
        _write_jsonl(timeline_path, timeline)
        _write_json(milestones_path, milestones)
        written[f"progress_timeline__{seed_label}"] = str(timeline_path.relative_to(root).as_posix())
        written[f"milestones__{seed_label}"] = str(milestones_path.relative_to(root).as_posix())
        result_payload = _load_optional_json(bundle_root / "optimization_result.json")
        aggregate_metrics = dict(result_payload.get("aggregate_metrics", {}))
        run_meta = dict(result_payload.get("run_meta", {}))
        final_timeline = timeline[-1] if timeline else {}
        seed_rows.append(
            {
                "seed": int(bundle_identity["benchmark_seed"]) if bundle_identity["benchmark_seed"] is not None else None,
                "algorithm_seed": (
                    int(bundle_identity["algorithm_seed"]) if bundle_identity["algorithm_seed"] is not None else None
                ),
                "label": seed_label,
                "bundle_root": _bundle_relative_path(root, bundle_root),
                "run_id": str(run_meta.get("run_id", bundle_root.name)),
                "progress_timeline": str(timeline_path.relative_to(root).as_posix()),
                "milestones": str(milestones_path.relative_to(root).as_posix()),
                "baseline_feasible": bool(aggregate_metrics.get("baseline_feasible", False)),
                "first_feasible_eval": aggregate_metrics.get("first_feasible_eval"),
                "first_feasible_pde_eval": final_timeline.get("first_feasible_pde_eval_so_far"),
                "pde_evaluations": final_timeline.get("pde_evaluations_so_far"),
                "solver_skipped_evaluations": final_timeline.get("solver_skipped_evaluations_so_far"),
                "optimizer_feasible_rate": aggregate_metrics.get(
                    "optimizer_feasible_rate",
                    aggregate_metrics.get("feasible_rate"),
                ),
                "pareto_size": int(aggregate_metrics.get("pareto_size", 0)),
                "final_timeline": final_timeline,
                "representatives": _discover_representatives(bundle_root),
            }
        )

    seed_rows.sort(
        key=lambda row: (
            int(row["seed"]) if row.get("seed") is not None else -1,
            int(row["algorithm_seed"]) if row.get("algorithm_seed") is not None else -1,
            str(row.get("bundle_root", "")),
        )
    )
    seed_summary_payload = {"rows": seed_rows}
    mode_summary_payload = {
        "mode_id": _resolve_mode_id(root),
        "seed_count": int(len(seed_rows)),
        "seeds": [int(row["seed"]) for row in seed_rows if row.get("seed") is not None],
        "baseline_feasible_count": int(sum(1 for row in seed_rows if row.get("baseline_feasible", False))),
        "first_feasible_eval_stats": _metric_stats(
            [float(row["first_feasible_eval"]) for row in seed_rows if row.get("first_feasible_eval") is not None]
        ),
        "first_feasible_pde_eval_stats": _metric_stats(
            [float(row["first_feasible_pde_eval"]) for row in seed_rows if row.get("first_feasible_pde_eval") is not None]
        ),
        "optimizer_feasible_rate_stats": _metric_stats(
            [float(row["optimizer_feasible_rate"]) for row in seed_rows if row.get("optimizer_feasible_rate") is not None]
        ),
        "pareto_size_stats": _metric_stats([float(row["pareto_size"]) for row in seed_rows]),
        "best_peak_stats": _metric_stats(
            [
                float(row["final_timeline"]["best_temperature_max_so_far"])
                for row in seed_rows
                if row.get("final_timeline", {}).get("best_temperature_max_so_far") is not None
            ]
        ),
        "best_gradient_stats": _metric_stats(
            [
                float(row["final_timeline"]["best_gradient_rms_so_far"])
                for row in seed_rows
                if row.get("final_timeline", {}).get("best_gradient_rms_so_far") is not None
            ]
        ),
    }
    seed_summary_path = summaries_root / "seed_summary.json"
    mode_summary_path = summaries_root / "mode_summary.json"
    _write_json(seed_summary_path, seed_summary_payload)
    _write_json(mode_summary_path, mode_summary_payload)
    written["seed_summary"] = str(seed_summary_path.relative_to(root).as_posix())
    written["mode_summary"] = str(mode_summary_path.relative_to(root).as_posix())
    return written


def _resolve_mode_id(mode_root: Path) -> str:
    manifest_path = mode_root / "manifest.json"
    if manifest_path.exists():
        manifest = _load_json(manifest_path)
        if manifest.get("mode_id"):
            return str(manifest["mode_id"])
    run_yaml_path = mode_root / "run.yaml"
    if run_yaml_path.exists():
        run_yaml = _load_optional_yaml(run_yaml_path)
        if run_yaml.get("mode"):
            return str(run_yaml["mode"])
    return mode_root.name


def _discover_representatives(seed_root: Path) -> list[str]:
    representatives_root = seed_root / "representatives"
    if not representatives_root.exists():
        return []
    return sorted(path.name for path in representatives_root.iterdir() if path.is_dir())


def _metric_stats(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "mean": None, "max": None}
    return {
        "min": float(min(values)),
        "mean": float(sum(values) / float(len(values))),
        "max": float(max(values)),
    }


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _load_optional_yaml(path: Path) -> dict[str, Any]:
    import yaml

    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _resolve_bundle_identity(bundle_root: Path) -> dict[str, Any]:
    benchmark_seed = _resolve_benchmark_seed(bundle_root)
    algorithm_seed = _resolve_algorithm_seed(bundle_root)
    label = f"seed-{benchmark_seed}" if benchmark_seed is not None else bundle_root.name
    return {
        "benchmark_seed": benchmark_seed,
        "algorithm_seed": algorithm_seed,
        "label": label,
    }


def _resolve_benchmark_seed(bundle_root: Path) -> int | None:
    run_yaml = _load_optional_yaml(bundle_root / "run.yaml")
    benchmark_seed = run_yaml.get("seeds", {}).get("benchmark")
    if benchmark_seed is not None:
        return int(benchmark_seed)
    optimization_result = _load_optional_json(bundle_root / "optimization_result.json")
    benchmark_seed = (
        optimization_result.get("run_meta", {}).get("benchmark_seed")
        or optimization_result.get("provenance", {}).get("benchmark_source", {}).get("seed")
    )
    if benchmark_seed is not None:
        return int(benchmark_seed)
    if bundle_root.name.startswith("seed-"):
        return int(bundle_root.name.removeprefix("seed-"))
    if bundle_root.parent.name.startswith("seed-"):
        return int(bundle_root.parent.name.removeprefix("seed-"))
    return None


def _resolve_algorithm_seed(bundle_root: Path) -> int | None:
    run_yaml = _load_optional_yaml(bundle_root / "run.yaml")
    algorithm_seed = run_yaml.get("seeds", {}).get("algorithm")
    if algorithm_seed is not None:
        return int(algorithm_seed)
    optimization_result = _load_optional_json(bundle_root / "optimization_result.json")
    algorithm_seed = optimization_result.get("run_meta", {}).get("algorithm_seed")
    if algorithm_seed is not None:
        return int(algorithm_seed)
    return None


def _load_progress_source_rows(bundle_root: Path) -> list[dict[str, Any]]:
    optimization_result = _load_optional_json(bundle_root / "optimization_result.json")
    history_rows = optimization_result.get("history")
    if isinstance(history_rows, list) and history_rows:
        return [dict(row) for row in history_rows]
    trace_path = resolve_seed_trace_path(bundle_root, "evaluation_events.jsonl")
    if trace_path.exists():
        return load_jsonl_rows(trace_path)
    return []


def _bundle_relative_path(root: Path, bundle_root: Path) -> str:
    relative_path = bundle_root.relative_to(root)
    return "." if relative_path == Path(".") else relative_path.as_posix()


def _cleanup_generated_mode_summaries(summaries_root: Path) -> None:
    for pattern in ("progress_timeline__*.jsonl", "milestones__*.json", "seed_summary.json", "mode_summary.json"):
        for path in summaries_root.glob(pattern):
            if path.is_file():
                path.unlink()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(dict(payload), indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
