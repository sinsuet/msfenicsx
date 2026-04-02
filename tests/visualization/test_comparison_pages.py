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
    assert (run_root / "comparison" / "figures" / "progress.svg").exists()
    assert (run_root / "comparison" / "figures" / "fields.svg").exists()
    assert "first feasible" in outputs["progress"].read_text(encoding="utf-8").lower()
    assert "figures/progress.svg" in outputs["progress"].read_text(encoding="utf-8").lower()


def test_progress_figure_renders_multi_metric_comparison_panels(tmp_path: Path) -> None:
    run_root = create_mixed_run_root(tmp_path, modes=("raw", "union", "llm"), seeds=(11,))
    build_comparison_summaries(run_root)

    render_comparison_pages(run_root)
    svg = (run_root / "comparison" / "figures" / "progress.svg").read_text(encoding="utf-8")

    assert "Best Peak vs Evaluation" in svg
    assert "Best Gradient vs Evaluation" in svg
    assert "Feasible Rate vs Evaluation" in svg
    assert "Pareto Size vs Evaluation" in svg


def test_fields_figure_renders_actual_field_comparison_panels(tmp_path: Path) -> None:
    run_root = create_mixed_run_root(tmp_path, modes=("raw", "union"), seeds=(11,))
    build_comparison_summaries(run_root)

    render_comparison_pages(run_root)
    svg = (run_root / "comparison" / "figures" / "fields.svg").read_text(encoding="utf-8")

    assert "Shared Color Scale" in svg
    assert "Hotspot X by Mode" not in svg
