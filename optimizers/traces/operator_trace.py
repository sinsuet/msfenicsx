"""Emit operator_trace.jsonl rows — spec § 4.3 schema, used by all drivers."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from optimizers.traces.jsonl_writer import append_jsonl


def emit_operator_trace(
    path: Path,
    *,
    generation: int,
    operator_name: str,
    parents: Sequence[str],
    offspring: Sequence[str],
    params: Mapping[str, Any],
    wall_ms: float,
    decision_id: str | None,
) -> None:
    """Append one § 4.3 operator_trace record."""
    params_serialized = json.dumps(dict(params), sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha1(params_serialized.encode("utf-8")).hexdigest()
    append_jsonl(
        path,
        {
            "decision_id": decision_id,
            "generation": int(generation),
            "operator_name": str(operator_name),
            "parents": list(parents),
            "offspring": list(offspring),
            "params_digest": digest,
            "wall_ms": float(wall_ms),
        },
    )
