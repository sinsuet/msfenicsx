"""Directory-layout tests for multi-scenario-seed × multi-algorithm-seed suite runs."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from optimizers.run_suite import _validate_benchmark_seed_policy






from unittest.mock import MagicMock, patch
import json

from optimizers.run_suite import _with_algorithm_seed, run_benchmark_suite


def test_with_algorithm_seed_overrides_seed_without_mutating_source():
    spec = MagicMock()
    spec.to_dict.return_value = {
        "schema_version": "1.0",
        "spec_meta": {"spec_id": "dummy"},
        "benchmark_source": {"seed": 11},
        "algorithm": {"family": "genetic", "backbone": "nsga2", "mode": "raw", "seed": 7},
        "design_variables": [],
    }
    with patch("optimizers.run_suite.OptimizationSpec") as optimization_spec_cls:
        new_spec = MagicMock()
        optimization_spec_cls.from_dict.return_value = new_spec

        result = _with_algorithm_seed(spec, 29)

        assert result is new_spec
        forwarded = optimization_spec_cls.from_dict.call_args.args[0]
        assert forwarded["algorithm"]["seed"] == 29
        assert spec.to_dict()["algorithm"]["seed"] == 7


def test_run_benchmark_suite_writes_opt_sublayer_for_each_seed_combo(tmp_path):
    pytest.importorskip("pymoo")

    scenario_runs_root = tmp_path / "runs"
    run_root = run_benchmark_suite(
        optimization_spec_paths=[Path("scenarios/optimization/s1_typical_raw.yaml")],
        benchmark_seeds=[11, 42],
        algorithm_seeds=[7, 13],
        scenario_runs_root=scenario_runs_root,
        modes=["raw"],
        evaluation_workers=1,
        started_at=datetime(2026, 4, 16, 12, 0),
    )
    raw_seeds_root = run_root / "raw" / "seeds"
    for bseed in (11, 42):
        for aseed in (7, 13):
            opt_root = raw_seeds_root / f"seed-{bseed}" / f"opt-{aseed}"
            assert opt_root.is_dir(), f"missing {opt_root}"
            assert (opt_root / "optimization_result.json").is_file()
            assert (opt_root / "manifest.json").is_file()
    top_manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    assert top_manifest["benchmark_seeds"] == [11, 42]
    assert top_manifest["algorithm_seeds"] == [7, 13]


from optimizers.mode_summary import build_mode_summaries


def test_build_mode_summaries_reads_opt_sublayer(tmp_path):
    pytest.importorskip("pymoo")

    scenario_runs_root = tmp_path / "runs"
    run_root = run_benchmark_suite(
        optimization_spec_paths=[Path("scenarios/optimization/s1_typical_raw.yaml")],
        benchmark_seeds=[11],
        algorithm_seeds=[7, 13],
        scenario_runs_root=scenario_runs_root,
        modes=["raw"],
        evaluation_workers=1,
        started_at=datetime(2026, 4, 16, 12, 0),
    )
    written = build_mode_summaries(run_root / "raw")
    timeline_keys = [key for key in written if key.startswith("progress_timeline__")]
    assert {"progress_timeline__seed-11__opt-7", "progress_timeline__seed-11__opt-13"} <= set(timeline_keys)
