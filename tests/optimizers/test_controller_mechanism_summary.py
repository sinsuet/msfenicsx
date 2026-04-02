from __future__ import annotations

from optimizers.experiment_summary import build_experiment_summaries
from tests.optimizers.experiment_fixtures import create_experiment_root


def test_union_experiment_builds_operator_and_regime_summaries(tmp_path) -> None:
    experiment_root = create_experiment_root(tmp_path, mode_id="nsga2_union")

    build_experiment_summaries(experiment_root)

    assert (experiment_root / "summaries" / "controller_trace_summary.json").exists()
    assert (experiment_root / "summaries" / "operator_summary.json").exists()
    assert (experiment_root / "summaries" / "regime_operator_summary.json").exists()
