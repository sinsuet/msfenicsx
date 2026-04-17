# tests/optimizers/test_run_manifest.py
"""Run manifest (run.yaml) top-level fields."""

from __future__ import annotations

from pathlib import Path

import yaml


def test_write_run_manifest_round_trips(tmp_path: Path) -> None:
    from optimizers.run_manifest import write_run_manifest

    target = tmp_path / "run.yaml"
    write_run_manifest(
        target,
        mode="llm",
        benchmark_seed=11,
        algorithm_seed=7,
        optimization_spec_path="scenarios/optimization/s1_typical_llm.yaml",
        evaluation_spec_path="scenarios/evaluation/s1_typical_eval.yaml",
        population_size=10,
        num_generations=5,
        wall_seconds=42.0,
    )
    payload = yaml.safe_load(target.read_text(encoding="utf-8"))
    assert payload["mode"] == "llm"
    assert payload["seeds"]["benchmark"] == 11
    assert payload["seeds"]["algorithm"] == 7
    assert payload["algorithm"]["population_size"] == 10
    assert payload["algorithm"]["num_generations"] == 5
    assert payload["timing"]["wall_seconds"] == 42.0
