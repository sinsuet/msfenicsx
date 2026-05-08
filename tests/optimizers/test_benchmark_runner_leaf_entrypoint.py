from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import yaml

from optimizers.benchmark_runner import leaf_entrypoint


def test_leaf_entrypoint_writes_run_manifest_before_postprocess(tmp_path: Path, monkeypatch) -> None:
    output_root = tmp_path / "raw" / "seeds" / "seed-11"
    calls: list[str] = []

    class FakeSpec:
        benchmark_source = {"seed": 0}
        algorithm = {"family": "genetic", "backbone": "nsga2", "mode": "raw"}
        evaluation_protocol = {
            "legality_policy_id": "projection_plus_local_restore",
            "evaluation_spec_path": "scenarios/evaluation/s5_aggressive15_eval.yaml",
        }
        operator_control = None

    class FakeCase:
        def to_dict(self):
            return {"case_meta": {"scenario_id": "s5_aggressive15"}}

    class FakeResult:
        run_meta = {
            "run_id": "fake-run",
            "optimization_spec_id": "fake-spec",
            "evaluation_spec_id": "fake-eval",
        }
        history = []
        pareto_front = []

    fake_run = SimpleNamespace(result=FakeResult(), representative_artifacts={})

    monkeypatch.setattr(leaf_entrypoint, "load_optimization_spec", lambda _path: FakeSpec())
    monkeypatch.setattr(leaf_entrypoint, "generate_benchmark_case", lambda *_args, **_kwargs: FakeCase())
    monkeypatch.setattr(leaf_entrypoint, "resolve_evaluation_spec_path", lambda *_args, **_kwargs: Path("eval.yaml"))
    monkeypatch.setattr(leaf_entrypoint, "load_spec", lambda _path: SimpleNamespace(to_dict=lambda: {"objectives": []}))
    monkeypatch.setattr(leaf_entrypoint, "run_raw_optimization", lambda *_args, **_kwargs: fake_run)
    monkeypatch.setattr(leaf_entrypoint, "write_optimization_artifacts", lambda *_args, **_kwargs: output_root)
    monkeypatch.setattr(leaf_entrypoint, "write_runtime_summary", lambda *_args, **_kwargs: None)

    def fake_postprocess(seed_root, **_kwargs):
        calls.append("postprocess")
        assert (Path(seed_root) / "run.yaml").exists()

    monkeypatch.setattr(leaf_entrypoint, "run_leaf_postprocess", fake_postprocess)

    exit_code = leaf_entrypoint.main(
        [
            "--optimization-spec",
            "scenarios/optimization/s5_aggressive15_raw.yaml",
            "--mode",
            "raw",
            "--benchmark-seed",
            "11",
            "--algorithm-seed",
            "1011",
            "--population-size",
            "2",
            "--num-generations",
            "1",
            "--evaluation-workers",
            "1",
            "--output-root",
            str(output_root),
            "--method-id",
            "nsga2_raw",
        ]
    )

    assert exit_code == 0
    assert calls == ["postprocess"]
    payload = yaml.safe_load((output_root / "run.yaml").read_text(encoding="utf-8"))
    assert payload["method_id"] == "nsga2_raw"
    assert payload["status"] == "completed"
