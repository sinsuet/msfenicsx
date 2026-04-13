from __future__ import annotations

import json
from pathlib import Path

from optimizers.comparison_summary import build_comparison_summaries
from tests.optimizers.experiment_fixtures import create_mixed_run_root


def test_build_comparison_summary_writes_seed_delta_and_progress_matrix(tmp_path: Path) -> None:
    run_root = create_mixed_run_root(tmp_path, modes=("raw", "union", "llm"), seeds=(11,))

    written = build_comparison_summaries(run_root)

    assert "seed_delta_table" in written
    assert (run_root / "comparison" / "summaries" / "seed_delta_table.json").exists()
    assert (run_root / "comparison" / "summaries" / "progress_matrix.json").exists()
    seed_delta = json.loads((run_root / "comparison" / "summaries" / "seed_delta_table.json").read_text(encoding="utf-8"))
    mode_scoreboard = json.loads(
        (run_root / "comparison" / "summaries" / "mode_scoreboard.json").read_text(encoding="utf-8")
    )

    assert seed_delta["rows"][0]["baseline_feasible"] is False
    assert seed_delta["rows"][0]["optimizer_feasible_rate"] == 2.0 / 3.0
    assert "optimizer_feasible_rate_stats" in mode_scoreboard["rows"][0]


def test_build_comparison_summary_aligns_real_run_representative_names(tmp_path: Path) -> None:
    run_root = create_mixed_run_root(tmp_path, modes=("raw", "union"), seeds=(11,))

    for mode in ("raw", "union"):
        representatives_root = run_root / mode / "seeds" / "seed-11" / "representatives"
        (representatives_root / "knee").rename(representatives_root / "knee-candidate")
        (representatives_root / "best-peak").rename(representatives_root / "min-peak-temperature")
        (representatives_root / "best-gradient").rename(representatives_root / "min-temperature-gradient-rms")

    build_comparison_summaries(run_root)

    field_alignment = json.loads(
        (run_root / "comparison" / "summaries" / "field_alignment.json").read_text(encoding="utf-8")
    )

    assert len(field_alignment["rows"]) == 2


def test_comparison_summary_exposes_representative_alignment_metadata(tmp_path: Path) -> None:
    run_root = create_mixed_run_root(tmp_path, modes=("raw", "union"), seeds=(11,))

    build_comparison_summaries(run_root)

    payload = json.loads((run_root / "comparison" / "summaries" / "field_alignment.json").read_text(encoding="utf-8"))
    row = payload["rows"][0]

    assert "representative_id" in row
    assert "temperature_grid_shape" in row
    assert "temperature_grid_path" in row
    assert "panel_domain" in row
