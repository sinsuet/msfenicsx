"""Structured-output schema helpers for OpenAI-compatible controller calls."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def build_operator_decision_schema(candidate_operator_ids: Sequence[str]) -> dict[str, Any]:
    operator_ids = [str(operator_id) for operator_id in candidate_operator_ids]
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "selected_operator_id": {
                "type": "string",
                "enum": operator_ids,
            },
            "selected_intent": {
                "type": "string",
            },
            "selected_semantic_task": {
                "type": "string",
            },
            "phase": {
                "type": "string",
            },
            "rationale": {
                "type": "string",
            },
        },
        "required": ["selected_operator_id"],
    }
