"""Streaming JSONL writers - append for live traces, batch for rewrites."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


def append_jsonl(path: Path, record: Mapping[str, Any]) -> None:
    """Append a single JSON record as one line (UTF-8, no BOM, LF newline)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(dict(record), ensure_ascii=False, separators=(",", ":"))
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(serialized)
        handle.write("\n")


def write_jsonl_batch(path: Path, records: Iterable[Mapping[str, Any]]) -> None:
    """Write (truncating) a JSONL file from an iterable of records."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(dict(record), ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")
