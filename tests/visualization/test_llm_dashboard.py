from __future__ import annotations

from optimizers.experiment_summary import build_experiment_summaries
from tests.optimizers.experiment_fixtures import create_experiment_root
from visualization.llm_dashboard import render_llm_dashboard


def test_render_llm_dashboard_writes_llm_html_for_llm_mode(tmp_path) -> None:
    experiment_root = create_experiment_root(tmp_path, mode_id="nsga2_llm")
    build_experiment_summaries(experiment_root)

    output_path = render_llm_dashboard(experiment_root)

    assert output_path.exists()
    assert "llm.html" in output_path.name
    assert (experiment_root / "figures" / "llm.svg").exists()
    assert (experiment_root / "figures" / "llm.json").exists()
    assert (experiment_root / "logs" / "experiment_index.json").exists()
