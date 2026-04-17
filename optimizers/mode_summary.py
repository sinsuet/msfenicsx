"""Derived per-mode summaries for the new s1_typical run tree."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from optimizers.run_telemetry import build_progress_milestones, build_progress_timeline, load_jsonl_rows


def build_mode_summaries(mode_root: str | Path) -> dict[str, str]:
    root = Path(mode_root)
    summaries_root = root / "summaries"
    summaries_root.mkdir(parents=True, exist_ok=True)
    seed_rows: list[dict[str, Any]] = []
    written: dict[str, str] = {}

    for benchmark_seed, algorithm_seed, opt_root in _iter_seed_roots(root):
        label = f"seed-{benchmark_seed}__opt-{algorithm_seed}"
        evaluation_rows = load_jsonl_rows(opt_root / "evaluation_events.jsonl")
        timeline = build_progress_timeline(evaluation_rows)
        milestones = build_progress_milestones(timeline)
        timeline_path = summaries_root / f"progress_timeline__{label}.jsonl"
        milestones_path = summaries_root / f"milestones__{label}.json"
        _write_jsonl(timeline_path, timeline)
        _write_json(milestones_path, milestones)
        written[f"progress_timeline__{label}"] = str(timeline_path.relative_to(root).as_posix())
        written[f"milestones__{label}"] = str(milestones_path.relative_to(root).as_posix())
        result_payload = _load_json(opt_root / "optimization_result.json")
        seed_rows.append(
            {
                "seed": benchmark_seed,
                "algorithm_seed": algorithm_seed,
                "run_id": str(result_payload["run_meta"]["run_id"]),
                "progress_timeline": str(timeline_path.relative_to(root).as_posix()),
                "milestones": str(milestones_path.relative_to(root).as_posix()),
                "baseline_feasible": bool(result_payload["aggregate_metrics"].get("baseline_feasible", False)),
                "first_feasible_eval": result_payload["aggregate_metrics"].get("first_feasible_eval"),
                "optimizer_feasible_rate": result_payload["aggregate_metrics"].get(
                    "optimizer_feasible_rate",
                    result_payload["aggregate_metrics"].get("feasible_rate"),
                ),
                "pareto_size": int(result_payload["aggregate_metrics"].get("pareto_size", 0)),
                "final_timeline": timeline[-1] if timeline else {},
                "representatives": _discover_representatives(opt_root),
            }
        )

    seed_rows.sort(key=lambda row: (int(row["seed"]), int(row["algorithm_seed"])))
    seed_summary_payload = {"rows": seed_rows}
    mode_summary_payload = {
        "mode_id": _resolve_mode_id(root),
        "seed_count": int(len(seed_rows)),
        "seed_pairs": [
            {"benchmark_seed": int(row["seed"]), "algorithm_seed": int(row["algorithm_seed"])}
            for row in seed_rows
        ],
        "seeds": sorted({int(row["seed"]) for row in seed_rows}),
        "baseline_feasible_count": int(sum(1 for row in seed_rows if row.get("baseline_feasible", False))),
        "first_feasible_eval_stats": _metric_stats(
            [float(row["first_feasible_eval"]) for row in seed_rows if row.get("first_feasible_eval") is not None]
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


def _iter_seed_roots(mode_root: Path) -> list[tuple[int, int, Path]]:
    seeds_root = mode_root / "seeds"
    if not seeds_root.exists():
        return []
    entries: list[tuple[int, int, Path]] = []
    for seed_dir in sorted(
        [path for path in seeds_root.iterdir() if path.is_dir() and path.name.startswith("seed-")],
        key=lambda path: int(path.name.removeprefix("seed-")),
    ):
        benchmark_seed = int(seed_dir.name.removeprefix("seed-"))
        opt_dirs = sorted(
            [path for path in seed_dir.iterdir() if path.is_dir() and path.name.startswith("opt-")],
            key=lambda path: int(path.name.removeprefix("opt-")),
        )
        for opt_dir in opt_dirs:
            algorithm_seed = int(opt_dir.name.removeprefix("opt-"))
            entries.append((benchmark_seed, algorithm_seed, opt_dir))
    return entries


def _resolve_mode_id(mode_root: Path) -> str:
    manifest_path = mode_root / "manifest.json"
    if manifest_path.exists():
        manifest = _load_json(manifest_path)
        if manifest.get("mode_id"):
            return str(manifest["mode_id"])
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


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(dict(payload), indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
