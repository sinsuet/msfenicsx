from __future__ import annotations

from pathlib import Path

import yaml


def test_write_run_manifest_records_unified_runner_fields(tmp_path: Path) -> None:
    from optimizers.run_manifest import write_run_manifest

    target = tmp_path / "run.yaml"
    write_run_manifest(
        target,
        mode="llm",
        method_id="llm:gpt",
        llm_profile="gpt",
        status="completed",
        algorithm_family="genetic",
        algorithm_backbone="nsga2",
        benchmark_seed=11,
        algorithm_seed=1011,
        optimization_spec_path="scenarios/optimization/s5_aggressive15_llm.yaml",
        evaluation_spec_path="scenarios/evaluation/s5_aggressive15_eval.yaml",
        population_size=40,
        num_generations=32,
        wall_seconds=12.5,
        postprocess_wall_seconds=2.0,
        legality_policy_id="projection_plus_local_restore",
    )

    payload = yaml.safe_load(target.read_text(encoding="utf-8"))
    assert payload["mode"] == "llm"
    assert payload["method_id"] == "llm:gpt"
    assert payload["llm_profile"] == "gpt"
    assert payload["status"] == "completed"
    assert payload["seeds"] == {"benchmark": 11, "algorithm": 1011}
    assert payload["timing"]["wall_seconds"] == 12.5
    assert payload["timing"]["postprocess_wall_seconds"] == 2.0
