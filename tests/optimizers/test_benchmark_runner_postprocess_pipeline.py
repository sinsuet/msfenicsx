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
    monkeypatch.setattr(
        "llm.openai_compatible.profile_loader.load_provider_profile_overlay",
        lambda profile: {
            "LLM_API_KEY": "test-key",
            "LLM_BASE_URL": "https://gpt.example/v1",
            "LLM_MODEL": "gpt-5.4",
        },
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


def test_leaf_postprocess_applies_llm_profile_overlay_for_replay(
    tmp_path: Path,
    monkeypatch,
) -> None:
    seed_root = tmp_path / "llm-qwen" / "seeds" / "seed-11"
    (seed_root / "traces").mkdir(parents=True)
    (seed_root / "traces" / "llm_request_trace.jsonl").write_text("", encoding="utf-8")
    (seed_root / "traces" / "llm_response_trace.jsonl").write_text("", encoding="utf-8")
    (seed_root / "traces" / "controller_trace.jsonl").write_text("", encoding="utf-8")

    replay_models: list[str | None] = []
    monkeypatch.setattr("optimizers.render_assets.render_assets", lambda path, hires=False: [Path(path)])
    monkeypatch.setattr(
        "llm.openai_compatible.profile_loader.load_provider_profile_overlay",
        lambda profile: {
            "LLM_API_KEY": "test-key",
            "LLM_BASE_URL": "https://qwen.example/v1",
            "LLM_MODEL": "qwen3.6-plus",
        },
    )

    def _capture_replay(_path, _params, **_kwargs):
        import os

        replay_models.append(os.environ.get("LLM_MODEL"))
        return {"rows": 0}

    monkeypatch.setattr("llm.openai_compatible.replay.replay_request_trace_file", _capture_replay)
    monkeypatch.setattr("llm.openai_compatible.replay.save_replay_summary", lambda output, summary: None)
    monkeypatch.setattr("optimizers.operator_pool.diagnostics.analyze_controller_trace", lambda *args, **kwargs: {})
    monkeypatch.setattr("optimizers.operator_pool.diagnostics.save_controller_trace_summary", lambda output, summary: None)

    run_leaf_postprocess(
        seed_root,
        mode="llm",
        llm_profile="qwen3_6_plus",
        optimization_spec_path=Path("scenarios/optimization/s5_aggressive15_llm.yaml"),
    )

    assert replay_models == ["qwen3.6-plus"]
