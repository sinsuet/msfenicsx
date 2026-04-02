from __future__ import annotations

from tests.optimizers.experiment_fixtures import create_experiment_root
from visualization.optimizer_overview import render_optimizer_overview


def test_render_optimizer_overview_harness_uses_production_renderer(tmp_path) -> None:
    experiment_root = create_experiment_root(tmp_path, mode_id="nsga2_raw")

    output_path = render_optimizer_overview(experiment_root)

    assert output_path.exists()
    assert output_path.stat().st_size > 0
    assert "<h1>Overview" in output_path.read_text(encoding="utf-8")
