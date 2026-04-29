from pathlib import Path

from optimizers.matrix.figures import (
    render_distribution_figure,
    render_failure_stacked_bar,
    render_rank_heatmap,
)


def test_render_distribution_figure_writes_png_and_pdf(tmp_path: Path) -> None:
    rows = [
        {"scenario_id": "s5", "method_id": "raw", "best_temperature_max": "10"},
        {"scenario_id": "s5", "method_id": "raw", "best_temperature_max": "12"},
        {"scenario_id": "s5", "method_id": "union", "best_temperature_max": "9"},
        {"scenario_id": "s5", "method_id": "union", "best_temperature_max": "11"},
    ]

    outputs = render_distribution_figure(rows, metric="best_temperature_max", output_dir=tmp_path)

    assert outputs == [tmp_path / "best_temperature_max_distribution.png", tmp_path / "best_temperature_max_distribution.pdf"]
    assert outputs[0].exists()
    assert outputs[1].exists()


def test_render_rank_heatmap_writes_png_and_pdf(tmp_path: Path) -> None:
    rows = [
        {"scenario_id": "s5", "method_id": "raw", "rank": "2"},
        {"scenario_id": "s5", "method_id": "union", "rank": "1"},
        {"scenario_id": "s6", "method_id": "raw", "rank": "1"},
        {"scenario_id": "s6", "method_id": "union", "rank": "2"},
    ]

    outputs = render_rank_heatmap(rows, output_dir=tmp_path)

    assert outputs == [tmp_path / "rank_heatmap.png", tmp_path / "rank_heatmap.pdf"]
    assert all(path.exists() for path in outputs)


def test_render_failure_stacked_bar_writes_png_and_pdf(tmp_path: Path) -> None:
    rows = [
        {"method_id": "raw", "status": "completed"},
        {"method_id": "raw", "status": "failed"},
        {"method_id": "union", "status": "timeout"},
    ]

    outputs = render_failure_stacked_bar(rows, output_dir=tmp_path)

    assert outputs == [tmp_path / "failure_stacked_bar.png", tmp_path / "failure_stacked_bar.pdf"]
    assert all(path.exists() for path in outputs)
