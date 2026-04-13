from pathlib import Path

import pytest

from optimizers.io import save_optimization_spec
from optimizers.models import OptimizationSpec
from optimizers.run_suite import run_benchmark_suite


def _write_small_raw_spec(tmp_path: Path) -> Path:
    spec = OptimizationSpec.from_dict(
        {
            "schema_version": "1.0",
            "spec_meta": {
                "spec_id": "s1-typical-run-suite-policy-test",
                "description": "Regression spec for s1_typical single benchmark seed policy.",
            },
            "benchmark_source": {
                "template_path": "scenarios/templates/s1_typical.yaml",
                "seed": 11,
            },
            "design_variables": [
                {
                    "variable_id": "c01_x",
                    "path": "components[0].pose.x",
                    "lower_bound": 0.1,
                    "upper_bound": 0.9,
                },
                {
                    "variable_id": "c01_y",
                    "path": "components[0].pose.y",
                    "lower_bound": 0.1,
                    "upper_bound": 0.68,
                },
            ],
            "algorithm": {
                "family": "genetic",
                "backbone": "nsga2",
                "mode": "raw",
                "population_size": 4,
                "num_generations": 1,
                "seed": 7,
            },
            "evaluation_protocol": {
                "evaluation_spec_path": "scenarios/evaluation/s1_typical_eval.yaml",
            },
        }
    )
    spec_path = tmp_path / "nsga2_raw.yaml"
    save_optimization_spec(spec.to_dict(), spec_path)
    return spec_path


def test_run_benchmark_suite_rejects_multiple_benchmark_seeds_for_s1_typical(tmp_path: Path) -> None:
    raw_spec_path = _write_small_raw_spec(tmp_path)

    with pytest.raises(ValueError, match="s1_typical.*single benchmark_seed"):
        run_benchmark_suite(
            optimization_spec_paths=[raw_spec_path],
            benchmark_seeds=[11, 17],
            scenario_runs_root=tmp_path / "scenario_runs",
            modes=["raw"],
        )
