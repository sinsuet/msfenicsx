# tests/optimizers/test_operator_trace.py
"""operator_trace.jsonl emitter — all modes, § 4.3 schema."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def test_emit_operator_trace_row_shape(tmp_path: Path) -> None:
    from optimizers.traces.operator_trace import emit_operator_trace

    target = tmp_path / "operator_trace.jsonl"
    emit_operator_trace(
        target,
        generation=3,
        operator_name="global_explore",
        parents=["g003-i00"],
        offspring=["g003-i10"],
        params={"sigma": 0.1},
        wall_ms=42.1,
        decision_id="g003-e0030-d00",
    )
    row = json.loads(target.read_text(encoding="utf-8").splitlines()[0])
    assert row["operator_name"] == "global_explore"
    assert row["generation"] == 3
    assert row["parents"] == ["g003-i00"]
    assert row["offspring"] == ["g003-i10"]
    assert row["decision_id"] == "g003-e0030-d00"
    assert row["wall_ms"] == 42.1
    expected_digest = hashlib.sha1(b'{"sigma":0.1}').hexdigest()
    assert row["params_digest"] == expected_digest


def test_emit_operator_trace_null_decision_for_raw_union(tmp_path: Path) -> None:
    from optimizers.traces.operator_trace import emit_operator_trace

    target = tmp_path / "operator_trace.jsonl"
    emit_operator_trace(
        target,
        generation=0,
        operator_name="native_sbx_pm",
        parents=["g000-i00", "g000-i01"],
        offspring=["g000-i10"],
        params={},
        wall_ms=1.1,
        decision_id=None,
    )
    row = json.loads(target.read_text(encoding="utf-8").splitlines()[0])
    assert row["decision_id"] is None
