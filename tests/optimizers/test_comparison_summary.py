from __future__ import annotations

from pathlib import Path

from optimizers.comparison_summary import build_comparison_summaries
from tests.optimizers.experiment_fixtures import create_mixed_run_root


def test_build_comparison_summary_writes_seed_delta_and_progress_matrix(tmp_path: Path) -> None:
    run_root = create_mixed_run_root(tmp_path, modes=("raw", "union", "llm"), seeds=(11,))

    written = build_comparison_summaries(run_root)

    assert "seed_delta_table" in written
    assert (run_root / "comparison" / "summaries" / "seed_delta_table.json").exists()
    assert (run_root / "comparison" / "summaries" / "progress_matrix.json").exists()
