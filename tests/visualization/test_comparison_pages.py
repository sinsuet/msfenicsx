from __future__ import annotations

from pathlib import Path

from optimizers.comparison_summary import build_comparison_summaries
from tests.optimizers.experiment_fixtures import create_mixed_run_root
from visualization.comparison_pages import render_comparison_pages


def test_render_comparison_pages_writes_progress_and_fields_html(tmp_path: Path) -> None:
    run_root = create_mixed_run_root(tmp_path, modes=("raw", "union", "llm"), seeds=(11,))
    build_comparison_summaries(run_root)

    outputs = render_comparison_pages(run_root)

    assert (run_root / "comparison" / "pages" / "progress.html").exists()
    assert (run_root / "comparison" / "pages" / "fields.html").exists()
    assert "first feasible" in outputs["progress"].read_text(encoding="utf-8").lower()
