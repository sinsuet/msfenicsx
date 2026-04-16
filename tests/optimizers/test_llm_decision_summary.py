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


def test_llm_decision_summary_reports_route_family_counts_and_entropy(tmp_path: Path) -> None:
    llm_mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="llm", seeds=(11,))

    build_llm_decision_summaries(llm_mode_root)
    payload = json.loads((llm_mode_root / "summaries" / "llm_decision_summary.json").read_text(encoding="utf-8"))

    assert payload["route_family_counts"] == {
        "stable_local": 1,
        "sink_retarget": 1,
    }
    assert payload["route_family_entropy"] == 1.0
