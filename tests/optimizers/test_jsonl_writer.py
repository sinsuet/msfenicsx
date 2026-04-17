"""JSONL append writer used by all trace sinks."""

from __future__ import annotations

import json
from pathlib import Path


def test_append_jsonl_creates_file_and_appends(tmp_path: Path) -> None:
    from optimizers.traces.jsonl_writer import append_jsonl

    target = tmp_path / "trace.jsonl"
    append_jsonl(target, {"a": 1})
    append_jsonl(target, {"a": 2})

    lines = target.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"a": 1}
    assert json.loads(lines[1]) == {"a": 2}


def test_append_jsonl_enforces_single_line_per_record(tmp_path: Path) -> None:
    from optimizers.traces.jsonl_writer import append_jsonl

    target = tmp_path / "trace.jsonl"
    append_jsonl(target, {"nested": {"x": 1}, "list": [1, 2, 3]})

    content = target.read_text(encoding="utf-8")
    # Exactly one newline at the end, no internal newlines in the record.
    assert content.count("\n") == 1
    assert "\n" not in content.rstrip("\n")


def test_write_jsonl_batch_truncates(tmp_path: Path) -> None:
    from optimizers.traces.jsonl_writer import write_jsonl_batch

    target = tmp_path / "trace.jsonl"
    write_jsonl_batch(target, [{"a": 1}])
    write_jsonl_batch(target, [{"a": 2}, {"a": 3}])

    lines = target.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"a": 2}
    assert json.loads(lines[1]) == {"a": 3}
