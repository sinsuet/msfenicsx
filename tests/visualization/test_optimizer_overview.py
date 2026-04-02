from __future__ import annotations

from tests.optimizers.experiment_fixtures import create_experiment_root
from visualization.optimizer_overview import render_optimizer_overview


def test_render_optimizer_overview_writes_overview_html(tmp_path) -> None:
    experiment_root = create_experiment_root(tmp_path, mode_id="nsga2_raw")

    output_path = render_optimizer_overview(experiment_root)

    assert output_path.exists()
    assert "overview.html" in output_path.name
    assert "nsga2_raw" in output_path.read_text(encoding="utf-8")
    assert (experiment_root / "figures" / "overview.svg").exists()
    assert (experiment_root / "figures" / "overview.json").exists()
    assert (experiment_root / "logs" / "experiment_index.json").exists()
