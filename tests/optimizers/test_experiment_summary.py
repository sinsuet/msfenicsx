from __future__ import annotations

from optimizers.experiment_summary import build_experiment_summaries
from tests.optimizers.experiment_fixtures import create_experiment_root


def test_build_experiment_summaries_writes_run_index_and_aggregate_summary(tmp_path) -> None:
    experiment_root = create_experiment_root(tmp_path, mode_id="nsga2_raw")

    written = build_experiment_summaries(experiment_root)

    assert (experiment_root / "summaries" / "run_index.json").exists()
    assert (experiment_root / "summaries" / "aggregate_summary.json").exists()
    assert (experiment_root / "summaries" / "constraint_summary.json").exists()
    assert (experiment_root / "summaries" / "generation_summary.json").exists()
    assert written["run_index"] == "summaries/run_index.json"
