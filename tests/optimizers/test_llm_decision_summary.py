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


def test_key_decision_detection_flags_first_feasible_and_pareto_expansion(tmp_path: Path) -> None:
    llm_mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="llm", seeds=(11,))

    build_llm_decision_summaries(llm_mode_root)
    payload = json.loads((llm_mode_root / "summaries" / "llm_key_decisions.json").read_text(encoding="utf-8"))

    trigger_ids = {row["trigger_type"] for row in payload["rows"]}
    assert "first_feasible_trigger" in trigger_ids
    assert "pareto_expansion_trigger" in trigger_ids


def test_decision_log_uses_accepted_evaluation_index_from_attempt_traces(tmp_path: Path) -> None:
    llm_mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="llm", seeds=(11,))
    seed_root = llm_mode_root / "seeds" / "seed-11"

    request_rows = [
        {
            "generation_index": 1,
            "evaluation_index": 3,
            "decision_index": 10,
            "candidate_operator_ids": ["native_sbx_pm", "local_refine"],
            "user_prompt": "rejected duplicate prompt",
            "accepted_for_evaluation": False,
            "accepted_evaluation_indices": [],
        },
        {
            "generation_index": 1,
            "evaluation_index": 2,
            "decision_index": 11,
            "candidate_operator_ids": ["native_sbx_pm", "local_refine"],
            "user_prompt": "accepted prompt",
            "accepted_for_evaluation": True,
            "accepted_evaluation_indices": [3],
            "accepted_evaluation_index": 3,
        },
    ]
    response_rows = [
        {
            "generation_index": 1,
            "evaluation_index": 3,
            "decision_index": 10,
            "selected_operator_id": "local_refine",
            "response_text": "rejected duplicate response",
            "accepted_for_evaluation": False,
            "accepted_evaluation_indices": [],
        },
        {
            "generation_index": 1,
            "evaluation_index": 2,
            "decision_index": 11,
            "selected_operator_id": "local_refine",
            "response_text": "accepted response",
            "accepted_for_evaluation": True,
            "accepted_evaluation_indices": [3],
            "accepted_evaluation_index": 3,
        },
    ]

    (seed_root / "llm_request_trace.jsonl").write_text(
        "\n".join(json.dumps(row) for row in request_rows) + "\n",
        encoding="utf-8",
    )
    (seed_root / "llm_response_trace.jsonl").write_text(
        "\n".join(json.dumps(row) for row in response_rows) + "\n",
        encoding="utf-8",
    )

    build_llm_decision_summaries(llm_mode_root)
    rows = load_jsonl_rows(llm_mode_root / "summaries" / "llm_decision_log.jsonl")
    first_row = next(row for row in rows if int(row["evaluation_index"]) == 3)

    assert first_row["user_prompt"] == "accepted prompt"
    assert first_row["response_text"] == "accepted response"


def test_llm_decision_summary_reports_route_family_counts_and_entropy(tmp_path: Path) -> None:
    llm_mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="llm", seeds=(11,))

    build_llm_decision_summaries(llm_mode_root)
    payload = json.loads((llm_mode_root / "summaries" / "llm_decision_summary.json").read_text(encoding="utf-8"))

    assert payload["route_family_counts"] == {
        "stable_local": 1,
        "sink_retarget": 1,
    }
    assert payload["route_family_entropy"] == 1.0
