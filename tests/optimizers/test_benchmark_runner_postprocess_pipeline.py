from pathlib import Path

from optimizers.benchmark_runner.postprocess import run_leaf_postprocess


def test_leaf_postprocess_renders_and_runs_llm_diagnostics(tmp_path: Path, monkeypatch) -> None:
    seed_root = tmp_path / "llm-gpt" / "seeds" / "seed-11"
    (seed_root / "traces").mkdir(parents=True)
    (seed_root / "traces" / "llm_request_trace.jsonl").write_text("", encoding="utf-8")
    (seed_root / "traces" / "llm_response_trace.jsonl").write_text("", encoding="utf-8")
    (seed_root / "traces" / "controller_trace.jsonl").write_text("", encoding="utf-8")

    calls: list[str] = []
    monkeypatch.setattr(
        "optimizers.render_assets.render_assets",
        lambda path, hires=False: calls.append(f"render:{Path(path).name}") or [Path(path)],
    )
    monkeypatch.setattr("llm.openai_compatible.replay.replay_request_trace_file", lambda *args, **kwargs: {"rows": 0})
    monkeypatch.setattr(
        "llm.openai_compatible.replay.save_replay_summary",
        lambda output, summary: calls.append(f"replay:{Path(output).name}"),
    )
    monkeypatch.setattr(
        "optimizers.operator_pool.diagnostics.analyze_controller_trace",
        lambda *args, **kwargs: {"decisions": 0},
    )
    monkeypatch.setattr(
        "optimizers.operator_pool.diagnostics.save_controller_trace_summary",
        lambda output, summary: calls.append(f"controller:{Path(output).name}"),
    )

    run_leaf_postprocess(
        seed_root,
        mode="llm",
        llm_profile="gpt",
        optimization_spec_path=Path("scenarios/optimization/s5_aggressive15_llm.yaml"),
    )

    assert calls == ["render:seed-11", "replay:llm_replay_summary.json", "controller:controller_trace_summary.json"]
