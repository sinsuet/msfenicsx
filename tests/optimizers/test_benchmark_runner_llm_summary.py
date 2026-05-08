import json
from pathlib import Path

from optimizers.llm_summary import build_seed_llm_runtime_summary


def test_seed_llm_runtime_summary_reports_latency_and_tokens(tmp_path: Path) -> None:
    traces = tmp_path / "traces"
    traces.mkdir()
    (traces / "llm_request_trace.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"decision_id": "d1", "provider": "openai_compatible", "model": "gpt-5.4"}),
                json.dumps({"decision_id": "d2", "provider": "openai_compatible", "model": "gpt-5.4"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (traces / "llm_response_trace.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "decision_id": "d1",
                        "provider": "openai_compatible",
                        "model": "gpt-5.4",
                        "latency_ms": 1000,
                        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                    }
                ),
                json.dumps(
                    {
                        "decision_id": "d2",
                        "provider": "openai_compatible",
                        "model": "gpt-5.4",
                        "latency_ms": 3000,
                        "usage": {"prompt_tokens": 20, "completion_tokens": 7, "total_tokens": 27},
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (traces / "controller_trace.jsonl").write_text(
        json.dumps({"decision_id": "d1", "fallback_used": True}) + "\n",
        encoding="utf-8",
    )

    summary = build_seed_llm_runtime_summary(
        tmp_path,
        scenario_id="s5_aggressive15",
        method_id="llm:gpt",
        mode="llm",
        llm_profile="gpt",
        run_wall_seconds=12.0,
        optimizer_wall_seconds=10.0,
    )

    assert summary["llm_request_count"] == 2
    assert summary["llm_response_count"] == 2
    assert summary["llm_fallback_count"] == 1
    assert summary["llm_latency_seconds_total"] == 4.0
    assert summary["llm_latency_seconds_mean"] == 2.0
    assert summary["llm_latency_seconds_median"] == 2.0
    assert summary["llm_latency_seconds_p95"] == 2.9
    assert summary["llm_latency_seconds_max"] == 3.0
    assert summary["tokens_prompt_total"] == 30
    assert summary["tokens_completion_total"] == 12
    assert summary["tokens_total"] == 42
