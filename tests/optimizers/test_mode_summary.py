from __future__ import annotations

import json
from pathlib import Path

from optimizers.mode_summary import build_mode_summaries
from optimizers.run_telemetry import build_progress_timeline, load_jsonl_rows
from tests.optimizers.experiment_fixtures import create_mode_root_with_seed_bundles


def test_build_mode_summary_writes_progress_timeline_and_milestones(tmp_path: Path) -> None:
    mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="raw", seeds=(11,))

    written = build_mode_summaries(mode_root)

    assert "mode_summary" in written
    assert (mode_root / "summaries" / "mode_summary.json").exists()
    assert (mode_root / "summaries" / "seed_summary.json").exists()
    assert (mode_root / "summaries" / "progress_timeline__seed-11.jsonl").exists()
    assert (mode_root / "summaries" / "milestones__seed-11.json").exists()


def test_progress_timeline_tracks_first_feasible_and_pareto_growth(tmp_path: Path) -> None:
    mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="raw", seeds=(11,))
    evaluation_rows = load_jsonl_rows(mode_root / "seeds" / "seed-11" / "evaluation_events.jsonl")

    rows = build_progress_timeline(evaluation_rows)

    assert rows[-1]["feasible_count_so_far"] >= 1
    assert rows[-1]["pareto_size_so_far"] >= 1
    assert rows[-1]["first_feasible_eval_so_far"] == 3
    assert rows[-1]["budget_fraction"] == 1.0
    milestones = json.loads((mode_root / "seeds" / "seed-11" / "optimization_result.json").read_text(encoding="utf-8"))
    assert milestones["aggregate_metrics"]["first_feasible_eval"] == 3
