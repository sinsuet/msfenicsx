# tests/optimizers/test_controller_trace_new_schema.py
"""LLM controller writes § 4.4 controller_trace.jsonl records."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.skip(reason="requires harness wiring — see test_llm_controller.py")


def test_controller_trace_records_have_new_schema(tmp_path: Path) -> None:
    """A canned controller invocation emits a § 4.4 record referencing a prompt ref."""
    from optimizers.traces.prompt_store import PromptStore  # noqa: F401
    from optimizers.operator_pool.llm_controller import LLMOperatorController  # noqa: F401

    trace_path = tmp_path / "run" / "traces" / "controller_trace.jsonl"
    assert trace_path.exists()
    rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    row = rows[0]
    for key in (
        "decision_id",
        "phase",
        "operator_selected",
        "operator_pool_snapshot",
        "input_state_digest",
        "prompt_ref",
        "rationale",
        "fallback_used",
        "latency_ms",
    ):
        assert key in row
    assert row["prompt_ref"].startswith("prompts/")
    assert row["prompt_ref"].endswith(".md")
