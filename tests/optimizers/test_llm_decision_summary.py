from __future__ import annotations

import json
from pathlib import Path

from optimizers.llm_decision_summary import build_llm_decision_summaries
from optimizers.run_telemetry import load_jsonl_rows
from tests.optimizers.experiment_fixtures import create_mode_root_with_seed_bundles


def test_build_llm_decision_log_preserves_prompt_response_and_outcome_refs(tmp_path: Path) -> None:
    llm_mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="llm", seeds=(11,))

    written = build_llm_decision_summaries(llm_mode_root)
    rows = load_jsonl_rows(llm_mode_root / "summaries" / "llm_decision_log.jsonl")

    assert "llm_decision_log" in written
    assert rows[0]["selected_operator_id"]
    assert rows[0]["prompt_ref"]
    assert rows[0]["response_ref"]
    assert rows[0]["controller_ref"].startswith("seeds/seed-11/traces/controller_trace.jsonl#decision_id=")
    assert rows[0]["operator_ref"].startswith("seeds/seed-11/traces/operator_trace.jsonl#decision_id=")


def test_key_decision_detection_flags_first_feasible_and_pareto_expansion(tmp_path: Path) -> None:
    llm_mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="llm", seeds=(11,))

    build_llm_decision_summaries(llm_mode_root)
    payload = json.loads((llm_mode_root / "summaries" / "llm_key_decisions.json").read_text(encoding="utf-8"))

    trigger_ids = {row["trigger_type"] for row in payload["rows"]}
    assert "first_feasible_trigger" in trigger_ids
    assert "pareto_expansion_trigger" in trigger_ids


def test_decision_log_carries_progress_annotations_from_mode_timeline(tmp_path: Path) -> None:
    llm_mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="llm", seeds=(11,))

    build_llm_decision_summaries(llm_mode_root)
    rows = load_jsonl_rows(llm_mode_root / "summaries" / "llm_decision_log.jsonl")
    first_feasible_row = next(row for row in rows if int(row["evaluation_index"]) == 3)

    assert first_feasible_row["first_feasible_eval_so_far"] == 3
    assert first_feasible_row["feasible_count_so_far"] == 1
    assert first_feasible_row["pareto_size_so_far"] == 1
    assert first_feasible_row["best_temperature_max_so_far"] == 301.0


def test_decision_log_materializes_prompt_and_response_text_from_prompt_store(tmp_path: Path) -> None:
    llm_mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="llm", seeds=(11,))
    seed_root = llm_mode_root / "seeds" / "seed-11"
    prompts_root = seed_root / "prompts"
    prompts_root.mkdir(parents=True, exist_ok=True)
    (prompts_root / "request-c.md").write_text(
        "# System\n\nsystem prompt\n\n# User\n\naccepted prompt\n",
        encoding="utf-8",
    )
    (prompts_root / "response-c.md").write_text(
        '{"selected_operator_id":"local_refine","rationale":"accepted response"}\n',
        encoding="utf-8",
    )

    request_rows = [
        {
            "decision_id": "g001-e0003-d00",
            "generation_index": 1,
            "evaluation_index": 3,
            "candidate_operator_ids": ["native_sbx_pm", "local_refine"],
            "prompt_ref": "prompts/request-c.md",
        },
    ]
    response_rows = [
        {
            "decision_id": "g001-e0003-d00",
            "generation_index": 1,
            "evaluation_index": 3,
            "selected_operator_id": "local_refine",
            "response_ref": "prompts/response-c.md",
            "tokens": {"total": 123},
            "finish_reason": "stop",
            "http_status": 200,
            "retries": 0,
            "latency_ms": 900.0,
        },
    ]

    (seed_root / "traces" / "llm_request_trace.jsonl").write_text(
        "\n".join(json.dumps(row) for row in request_rows) + "\n",
        encoding="utf-8",
    )
    (seed_root / "traces" / "llm_response_trace.jsonl").write_text(
        "\n".join(json.dumps(row) for row in response_rows) + "\n",
        encoding="utf-8",
    )

    build_llm_decision_summaries(llm_mode_root)
    rows = load_jsonl_rows(llm_mode_root / "summaries" / "llm_decision_log.jsonl")
    first_row = next(row for row in rows if int(row["evaluation_index"]) == 3)

    assert first_row["user_prompt"] == "accepted prompt"
    assert "accepted response" in first_row["response_text"]


def test_llm_decision_summary_reports_route_family_counts_and_entropy(tmp_path: Path) -> None:
    llm_mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="llm", seeds=(11,))

    build_llm_decision_summaries(llm_mode_root)
    payload = json.loads((llm_mode_root / "summaries" / "llm_decision_summary.json").read_text(encoding="utf-8"))

    assert payload["route_family_counts"] == {
        "stable_local": 1,
        "sink_retarget": 1,
    }
    assert payload["route_family_entropy"] == 1.0
