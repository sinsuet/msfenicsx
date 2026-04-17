"""Correlation IDs link controller decisions -> LLM bodies -> operator ops -> evaluations."""

from __future__ import annotations

import re

_DECISION_ID_RE = re.compile(r"^g(\d{3})-e(\d{4})-d(\d{2})$")


def format_decision_id(generation: int, eval_index: int, decision_index: int) -> str:
    """Build a canonical decision id `g{gen:03d}-e{eval:04d}-d{dec:02d}`."""
    if generation < 0 or eval_index < 0 or decision_index < 0:
        raise ValueError(
            f"decision id components must be non-negative; got gen={generation}, "
            f"eval={eval_index}, dec={decision_index}"
        )
    return f"g{generation:03d}-e{eval_index:04d}-d{decision_index:02d}"


def parse_decision_id(value: str) -> tuple[int, int, int]:
    """Parse a decision id back into `(generation, eval_index, decision_index)`."""
    match = _DECISION_ID_RE.match(value)
    if match is None:
        raise ValueError(f"malformed decision id: {value!r}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))
