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


def test_leaf_postprocess_runs_live_llm_replay_when_explicitly_enabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    seed_root = tmp_path / "llm-gpt" / "seeds" / "seed-11"
    (seed_root / "traces").mkdir(parents=True)
    (seed_root / "traces" / "llm_request_trace.jsonl").write_text("", encoding="utf-8")
    (seed_root / "traces" / "llm_response_trace.jsonl").write_text("", encoding="utf-8")
    (seed_root / "traces" / "controller_trace.jsonl").write_text("", encoding="utf-8")

    replay_limits: list[int | None] = []
    monkeypatch.setenv("MSFENICSX_LLM_POSTPROCESS_REPLAY", "live")
    monkeypatch.setattr("optimizers.render_assets.render_assets", lambda path, hires=False: [Path(path)])
    monkeypatch.setattr(
        "llm.openai_compatible.profile_loader.load_provider_profile_overlay",
        lambda profile: {
            "LLM_API_KEY": "test-key",
            "LLM_BASE_URL": "https://gpt.example/v1",
            "LLM_MODEL": "gpt-5.4",
        },
    )

    def _capture_replay(_path, _params, **kwargs):
        replay_limits.append(kwargs.get("limit"))
        return {"rows": [], "aggregate": {"request_count": 0}}

    monkeypatch.setattr("llm.openai_compatible.replay.replay_request_trace_file", _capture_replay)
    monkeypatch.setattr("llm.openai_compatible.replay.save_replay_summary", lambda output, summary: None)
    monkeypatch.setattr("optimizers.operator_pool.diagnostics.analyze_controller_trace", lambda *args, **kwargs: {})
    monkeypatch.setattr("optimizers.operator_pool.diagnostics.save_controller_trace_summary", lambda output, summary: None)

    run_leaf_postprocess(
        seed_root,
        mode="llm",
        llm_profile="gpt",
        optimization_spec_path=Path("scenarios/optimization/s5_aggressive15_llm.yaml"),
    )

    assert replay_limits == [None]


def test_leaf_postprocess_defaults_to_offline_llm_replay_summary(tmp_path: Path, monkeypatch) -> None:
    seed_root = tmp_path / "llm-deepseek" / "seeds" / "seed-11"
    (seed_root / "traces").mkdir(parents=True)
    (seed_root / "traces" / "llm_request_trace.jsonl").write_text(
        '{"generation_index": 2, "evaluation_index": 34, "candidate_operator_ids": ["sink_shift"]}\n',
        encoding="utf-8",
    )
    (seed_root / "traces" / "llm_response_trace.jsonl").write_text(
        '{"generation_index": 2, "evaluation_index": 34, "selected_operator_id": "sink_shift", '
        '"attempt_count": 1, "retry_count": 0, "elapsed_seconds": 1.5}\n',
        encoding="utf-8",
    )
    (seed_root / "traces" / "controller_trace.jsonl").write_text("", encoding="utf-8")

    monkeypatch.setattr("optimizers.render_assets.render_assets", lambda path, hires=False: [Path(path)])
    monkeypatch.setattr(
        "llm.openai_compatible.replay.replay_request_trace_file",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("live replay should not run by default")),
    )
    monkeypatch.setattr("optimizers.operator_pool.diagnostics.analyze_controller_trace", lambda *args, **kwargs: {})
    monkeypatch.setattr("optimizers.operator_pool.diagnostics.save_controller_trace_summary", lambda output, summary: None)

    run_leaf_postprocess(
        seed_root,
        mode="llm",
        llm_profile="deepseek_v4_flash",
        optimization_spec_path=Path("scenarios/optimization/s4_aggressive10_llm.yaml"),
    )

    replay_summary = seed_root / "summaries" / "llm_replay_summary.json"
    assert replay_summary.exists()
    payload = __import__("json").loads(replay_summary.read_text(encoding="utf-8"))
    assert payload["aggregate"]["request_count"] == 1
    assert payload["aggregate"]["success_count"] == 1
    assert payload["aggregate"]["elapsed_seconds_total"] == 1.5
    assert payload["replay_meta"]["replay_mode"] == "offline_existing_trace"
    assert payload["replay_meta"]["live_provider_call_count"] == 0
    assert payload["rows"] == [
        {
            "row_index": 0,
            "generation_index": 2,
            "evaluation_index": 34,
            "candidate_operator_ids": ["sink_shift"],
            "valid": True,
            "retried": False,
            "attempt_count": 1,
            "selected_operator_id": "sink_shift",
            "error": None,
            "elapsed_seconds": 1.5,
            "attempt_trace": [],
        }
    ]


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

    def _capture_overlay(_path, _params, **_kwargs):
        import os

        replay_models.append(os.environ.get("LLM_MODEL"))
        return {"rows": 0}

    monkeypatch.setattr("llm.openai_compatible.replay.replay_request_trace_file", _capture_overlay)
    monkeypatch.setattr("llm.openai_compatible.replay.save_replay_summary", lambda output, summary: None)
    monkeypatch.setattr("optimizers.operator_pool.diagnostics.analyze_controller_trace", lambda *args, **kwargs: {})
    monkeypatch.setattr("optimizers.operator_pool.diagnostics.save_controller_trace_summary", lambda output, summary: None)

    run_leaf_postprocess(
        seed_root,
        mode="llm",
        llm_profile="qwen3_6_plus",
        optimization_spec_path=Path("scenarios/optimization/s5_aggressive15_llm.yaml"),
        replay_mode="live",
    )

    assert replay_models == ["qwen3.6-plus"]
