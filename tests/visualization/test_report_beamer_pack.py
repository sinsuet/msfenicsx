from __future__ import annotations

import json

from optimizers.experiment_summary import build_experiment_summaries
from tests.optimizers.experiment_fixtures import create_experiment_root


def test_experiment_summary_run_index_uses_generic_objective_ids(tmp_path) -> None:
    experiment_root = create_experiment_root(tmp_path, mode_id="nsga2_raw")

    build_experiment_summaries(experiment_root)

    run_index = json.loads((experiment_root / "summaries" / "run_index.json").read_text(encoding="utf-8"))
    generation_summary = json.loads(
        (experiment_root / "summaries" / "generation_summary.json").read_text(encoding="utf-8")
    )

    assert "best_minimize_peak_temperature" in run_index[0]
    assert "best_minimize_temperature_gradient_rms" in run_index[0]
    assert "best_hot_pa_peak" not in run_index[0]
    assert "mean_best_minimize_peak_temperature" in generation_summary["generations"][0]
    assert "mean_best_minimize_temperature_gradient_rms" in generation_summary["generations"][0]
