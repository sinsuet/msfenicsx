from __future__ import annotations

from optimizers.experiment_summary import build_experiment_summaries
from tests.optimizers.experiment_fixtures import create_experiment_root
from visualization.controller_mechanism import render_controller_mechanism


def test_render_controller_mechanism_writes_mechanism_html_for_union(tmp_path) -> None:
    experiment_root = create_experiment_root(tmp_path, mode_id="nsga2_union")
    build_experiment_summaries(experiment_root)

    output_path = render_controller_mechanism(experiment_root)

    assert output_path.exists()
    assert "mechanism.html" in output_path.name
    assert (experiment_root / "figures" / "mechanism.svg").exists()
    assert (experiment_root / "figures" / "mechanism.json").exists()
    assert (experiment_root / "logs" / "experiment_index.json").exists()
