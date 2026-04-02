from __future__ import annotations

from optimizers.experiment_summary import build_experiment_summaries
from optimizers.llm_summary import build_llm_runtime_summary
from tests.optimizers.experiment_fixtures import create_experiment_root


def test_build_llm_runtime_summary_extracts_provider_model_and_latency() -> None:
    summary = build_llm_runtime_summary(
        metrics_rows=[
            {
                "provider": "openai-compatible",
                "model": "GPT-5.4",
                "capability_profile": "responses_native",
                "performance_profile": "balanced",
                "request_count": 1,
                "response_count": 1,
                "fallback_count": 0,
                "retry_count": 1,
                "invalid_response_count": 1,
                "schema_invalid_count": 1,
                "semantic_invalid_count": 0,
                "elapsed_seconds_total": 1.25,
                "elapsed_seconds_avg": 1.25,
                "elapsed_seconds_max": 1.25,
            }
        ],
        request_rows=[],
        response_rows=[],
    )

    assert summary["provider"] == "openai-compatible"
    assert summary["model"] == "GPT-5.4"
    assert summary["retry_count"] == 1
    assert summary["invalid_response_count"] == 1


def test_llm_experiment_builds_runtime_decision_and_prompt_summaries(tmp_path) -> None:
    experiment_root = create_experiment_root(tmp_path, mode_id="nsga2_llm")

    build_experiment_summaries(experiment_root)

    assert (experiment_root / "summaries" / "llm_runtime_summary.json").exists()
    assert (experiment_root / "summaries" / "llm_decision_summary.json").exists()
    assert (experiment_root / "summaries" / "llm_prompt_summary.json").exists()
