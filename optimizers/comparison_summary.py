"""Cross-mode comparison summaries for the new s1_typical run tree."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from optimizers.mode_summary import build_mode_summaries
from optimizers.run_telemetry import load_jsonl_rows


def build_comparison_summaries(run_root: str | Path) -> dict[str, str]:
    root = Path(run_root)
    comparison_root = root / "comparison"
    summaries_root = comparison_root / "summaries"
    summaries_root.mkdir(parents=True, exist_ok=True)
    modes = [mode for mode in ("raw", "union", "llm") if (root / mode).is_dir()]

    mode_scoreboard_rows: list[dict[str, Any]] = []
    seed_delta_rows: list[dict[str, Any]] = []
    progress_rows: list[dict[str, Any]] = []
    pareto_rows: list[dict[str, Any]] = []
    field_rows: list[dict[str, Any]] = []
    controller_rows: list[dict[str, Any]] = []

    for mode in modes:
        mode_root = root / mode
        build_mode_summaries(mode_root)
        mode_summary = _load_json(mode_root / "summaries" / "mode_summary.json")
        seed_summary = _load_json(mode_root / "summaries" / "seed_summary.json")
        mode_scoreboard_rows.append(
            {
                "mode_id": mode,
                "seed_count": int(mode_summary.get("seed_count", 0)),
                "first_feasible_eval_stats": mode_summary.get("first_feasible_eval_stats", {}),
                "pareto_size_stats": mode_summary.get("pareto_size_stats", {}),
                "best_peak_stats": mode_summary.get("best_peak_stats", {}),
                "best_gradient_stats": mode_summary.get("best_gradient_stats", {}),
            }
        )
        for seed_row in seed_summary.get("rows", []):
            seed = int(seed_row["seed"])
            timeline = load_jsonl_rows(mode_root / seed_row["progress_timeline"])
            progress_rows.append({"mode_id": mode, "seed": seed, "timeline": timeline})
            final_timeline = dict(seed_row.get("final_timeline", {}))
            seed_delta_rows.append(
                {
                    "mode_id": mode,
                    "seed": seed,
                    "first_feasible_eval": seed_row.get("first_feasible_eval"),
                    "pareto_size": seed_row.get("pareto_size"),
                    "best_temperature_max": final_timeline.get("best_temperature_max_so_far"),
                    "best_gradient_rms": final_timeline.get("best_gradient_rms_so_far"),
                }
            )
            pareto_rows.append(
                {
                    "mode_id": mode,
                    "seed": seed,
                    "pareto_size": seed_row.get("pareto_size"),
                }
            )
            representative_root = _resolve_field_representative_root(
                mode_root / "seeds" / f"seed-{seed}" / "representatives"
            )
            if representative_root is not None and (representative_root / "summaries" / "field_view.json").exists():
                field_view = _load_json(representative_root / "summaries" / "field_view.json")
                field_rows.append(
                    {
                        "mode_id": mode,
                        "seed": seed,
                        "representative_id": representative_root.name,
                        "representative_root": str(representative_root.relative_to(root).as_posix()),
                        "field_view_path": str((representative_root / "summaries" / "field_view.json").relative_to(root).as_posix()),
                        "temperature_grid_path": str(
                            (representative_root / "fields" / "temperature_grid.npz").relative_to(root).as_posix()
                        ),
                        "gradient_grid_path": str(
                            (representative_root / "fields" / "gradient_magnitude_grid.npz").relative_to(root).as_posix()
                        ),
                        "panel_domain": field_view.get("panel_domain", {}),
                        "layout": field_view.get("layout", {}),
                        "temperature_grid_shape": field_view.get("temperature", {}).get("grid_shape"),
                        "gradient_grid_shape": field_view.get("gradient_magnitude", {}).get("grid_shape"),
                        "temperature_min": field_view.get("temperature", {}).get("min"),
                        "temperature_max": field_view.get("temperature", {}).get("max"),
                        "gradient_min": field_view.get("gradient_magnitude", {}).get("min"),
                        "gradient_max": field_view.get("gradient_magnitude", {}).get("max"),
                        "hotspot": field_view.get("temperature", {}).get("hotspot"),
                    }
                )
            controller_trace_path = mode_root / "seeds" / f"seed-{seed}" / "controller_trace.json"
            if controller_trace_path.exists():
                controller_rows.append(
                    {
                        "mode_id": mode,
                        "seed": seed,
                        "selected_operator_counts": dict(
                            Counter(
                                str(row.get("selected_operator_id", ""))
                                for row in _load_json(controller_trace_path)
                                if row.get("selected_operator_id")
                            )
                        ),
                    }
                )

    payloads = {
        "mode_scoreboard": {"rows": mode_scoreboard_rows},
        "seed_delta_table": {"rows": seed_delta_rows},
        "progress_matrix": {"rows": progress_rows},
        "pareto_comparison": {"rows": pareto_rows},
        "field_alignment": {"rows": field_rows},
    }
    if {"union", "llm"} <= set(modes):
        payloads["controller_comparison"] = {"rows": controller_rows}

    written: dict[str, str] = {}
    for summary_name, payload in payloads.items():
        output_path = summaries_root / f"{summary_name}.json"
        output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        written[summary_name] = str(output_path.relative_to(root).as_posix())
    return written


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_field_representative_root(representatives_root: Path) -> Path | None:
    if not representatives_root.exists():
        return None
    representatives = sorted(path for path in representatives_root.iterdir() if path.is_dir())
    if not representatives:
        return None
    search_orders = (
        ("knee", "candidate"),
        ("knee",),
        ("min", "peak"),
        ("best", "peak"),
        ("min", "gradient"),
        ("best", "gradient"),
        ("first", "feasible"),
        ("baseline",),
    )
    lowered = [(path, path.name.lower()) for path in representatives]
    for search_tokens in search_orders:
        for path, lowered_name in lowered:
            if all(token in lowered_name for token in search_tokens):
                return path
    return representatives[0]
