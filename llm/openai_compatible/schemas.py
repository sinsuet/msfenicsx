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


def build_operator_prior_advice_schema(candidate_operator_ids: Sequence[str]) -> dict[str, Any]:
    operator_ids = [str(operator_id) for operator_id in candidate_operator_ids]
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "phase": {"type": "string"},
            "rationale": {"type": "string"},
            "semantic_task_priors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "semantic_task": {"type": "string"},
                        "prior": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "risk": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    },
                    "required": ["semantic_task", "prior"],
                },
            },
            "operator_priors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "operator_id": {"type": "string", "enum": operator_ids},
                        "prior": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "risk": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "rationale": {"type": "string"},
                    },
                    "required": ["operator_id", "prior"],
                },
            },
        },
        "required": ["operator_priors"],
    }
