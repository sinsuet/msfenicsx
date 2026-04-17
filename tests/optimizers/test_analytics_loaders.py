"""JSONL loaders stream trace rows into typed dicts."""

from __future__ import annotations

import json
from pathlib import Path


def _write_lines(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row))
            handle.write("\n")


def test_iter_jsonl_yields_each_record(tmp_path: Path) -> None:
    from optimizers.analytics.loaders import iter_jsonl

    target = tmp_path / "t.jsonl"
    _write_lines(target, [{"a": 1}, {"a": 2}, {"a": 3}])

    rows = list(iter_jsonl(target))
    assert rows == [{"a": 1}, {"a": 2}, {"a": 3}]


def test_iter_jsonl_ignores_blank_lines(tmp_path: Path) -> None:
    from optimizers.analytics.loaders import iter_jsonl

    target = tmp_path / "t.jsonl"
    target.write_text('{"a":1}\n\n{"a":2}\n', encoding="utf-8")

    rows = list(iter_jsonl(target))
    assert rows == [{"a": 1}, {"a": 2}]


def test_iter_jsonl_missing_file_yields_empty(tmp_path: Path) -> None:
    from optimizers.analytics.loaders import iter_jsonl

    rows = list(iter_jsonl(tmp_path / "missing.jsonl"))
    assert rows == []
