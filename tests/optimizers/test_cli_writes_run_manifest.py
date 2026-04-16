"""optimize-benchmark must write run.yaml at the output-root."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml


def test_optimize_benchmark_writes_run_manifest(tmp_path: Path) -> None:
    from optimizers.cli import main

    output_root = tmp_path / "run"
    output_root.mkdir()

    mock_run = MagicMock()
    mock_run.result.run_meta = {
        "run_id": "test-run",
        "optimization_spec_id": "s1_typical_raw",
        "evaluation_spec_id": "s1_typical_eval",
    }
    mock_run.result.history = []
    mock_run.result.pareto_front = []
    mock_run.representative_artifacts = {}
    mock_run.generation_summary_rows = []

    spec_path = "scenarios/optimization/s1_typical_raw.yaml"

    with patch("optimizers.cli.load_optimization_spec") as mock_load_spec, \
         patch("optimizers.cli.generate_benchmark_case") as mock_gen, \
         patch("optimizers.cli.resolve_evaluation_spec_path") as mock_resolve, \
         patch("optimizers.cli.load_spec") as mock_load_eval, \
         patch("optimizers.cli.run_raw_optimization", return_value=mock_run), \
         patch("optimizers.cli.write_optimization_artifacts"), \
         patch("optimizers.render_assets.render_run_assets"):
        mock_spec = MagicMock()
        mock_spec.algorithm = {"mode": "raw", "seed": 7, "population_size": 10, "num_generations": 5}
        mock_spec.benchmark_source = {"seed": 11}
        mock_spec.operator_control = None
        mock_spec.to_dict.return_value = {
            "algorithm": {"mode": "raw", "seed": 7, "population_size": 10, "num_generations": 5},
            "benchmark_source": {"seed": 11},
            "operator_control": None,
        }
        mock_load_spec.return_value = mock_spec
        mock_gen.return_value = MagicMock()
        mock_resolve.return_value = Path("scenarios/evaluation/s1_typical_eval.yaml")
        mock_eval_spec = MagicMock()
        mock_eval_spec.to_dict.return_value = {"objectives": []}
        mock_load_eval.return_value = mock_eval_spec

        rc = main([
            "optimize-benchmark",
            "--optimization-spec", spec_path,
            "--output-root", str(output_root),
            "--skip-render",
        ])
        assert rc == 0

    manifest_path = output_root / "run.yaml"
    assert manifest_path.exists()
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "raw"
    assert payload["seeds"]["benchmark"] == 11
    assert payload["seeds"]["algorithm"] == 7
    assert payload["algorithm"]["population_size"] == 10
    assert payload["algorithm"]["num_generations"] == 5
    assert "wall_seconds" in payload["timing"]
