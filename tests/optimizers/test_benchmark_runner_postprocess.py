import json
from pathlib import Path

from optimizers.benchmark_runner.postprocess import (
    build_offline_llm_replay_summary,
    build_runtime_summary,
    write_runtime_summary,
)


def test_runtime_summary_counts_history_and_wall_time(tmp_path: Path) -> None:
    history = [
        {"solver_skipped": True, "feasible": False, "timing": {"solve_ms": 0}},
        {"solver_skipped": False, "feasible": True, "timing": {"solve_ms": 1200}},
        {"solver_skipped": False, "feasible": False, "timing": {"solve_ms": 800}},
    ]

    summary = build_runtime_summary(
        scenario_id="s5_aggressive15",
        method_id="nsga2_raw",
        mode="raw",
        seed=11,
        population_size=40,
        num_generations=32,
        run_wall_seconds=10.0,
        optimizer_wall_seconds=8.0,
        baseline_wall_seconds=1.0,
        postprocess_wall_seconds=1.0,
        render_wall_seconds=0.5,
        history=history,
    )

    assert summary["run_wall_seconds"] == 10.0
    assert summary["evaluation_count"] == 3
    assert summary["pde_attempt_count"] == 2
    assert summary["cheap_skip_count"] == 1
    assert summary["feasible_count"] == 1
    assert summary["pde_wall_seconds_total"] == 2.0


def test_write_runtime_summary_writes_summaries_dir_and_run_event(tmp_path: Path) -> None:
    seed_root = tmp_path / "seed-11"
    summary = {"scenario_id": "s5_aggressive15", "method_id": "nsga2_raw", "mode": "raw", "seed": 11}

    write_runtime_summary(seed_root, summary)

    assert (seed_root / "summaries" / "runtime_summary.json").exists()
    assert (seed_root / "traces" / "run_events.jsonl").exists()
    payload = json.loads((seed_root / "summaries" / "runtime_summary.json").read_text(encoding="utf-8"))
    assert payload["method_id"] == "nsga2_raw"


def test_build_offline_llm_replay_summary_marks_missing_responses_as_fallback_equivalent(tmp_path: Path) -> None:
    seed_root = tmp_path / "seed-11"
    traces = seed_root / "traces"
    traces.mkdir(parents=True)
    (traces / "llm_request_trace.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "decision_id": "d1",
                        "generation_index": 1,
                        "evaluation_index": 10,
                        "candidate_operator_ids": ["a", "b"],
                        "model": "deepseek-v4-flash",
                    }
                ),
                json.dumps(
                    {
                        "decision_id": "d2",
                        "generation_index": 1,
                        "evaluation_index": 11,
                        "candidate_operator_ids": ["a", "b"],
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (traces / "llm_response_trace.jsonl").write_text(
        json.dumps(
            {
                "decision_id": "d1",
                "selected_operator_id": "b",
                "attempt_count": 2,
                "elapsed_seconds": 3.0,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = build_offline_llm_replay_summary(
        seed_root,
        controller_parameters={
            "provider": "openai-compatible",
            "model": "ignored-env-model",
            "capability_profile": "chat_compatible_json",
            "performance_profile": "balanced",
        },
    )

    assert summary["aggregate"]["request_count"] == 2
    assert summary["aggregate"]["success_count"] == 1
    assert summary["aggregate"]["retry_row_count"] == 1
    assert summary["aggregate"]["fallback_equivalent_count"] == 1
    assert summary["aggregate"]["elapsed_seconds_total"] == 3.0
    assert summary["replay_meta"]["model"] == "deepseek-v4-flash"
    assert summary["replay_meta"]["live_provider_call_count"] == 0
    assert summary["rows"][1]["error"] == "missing recorded response"
