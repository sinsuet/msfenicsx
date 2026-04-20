"""Replay helpers for diagnosing OpenAI-compatible controller trace stability."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from llm.openai_compatible.client import OpenAICompatibleClient
from llm.openai_compatible.config import OpenAICompatibleConfig
from optimizers.traces.llm_trace_io import load_prompt_markdown_body, split_request_prompt_sections


def load_request_trace(path: str | Path) -> list[dict[str, Any]]:
    trace_path = Path(path)
    rows: list[dict[str, Any]] = []
    seed_root = trace_path.parent.parent if trace_path.parent.name == "traces" else trace_path.parent
    for raw_line in trace_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        payload = dict(json.loads(line))
        if not payload.get("system_prompt") and not payload.get("user_prompt") and payload.get("prompt_ref"):
            body = load_prompt_markdown_body(seed_root, str(payload["prompt_ref"]))
            system_prompt, user_prompt = split_request_prompt_sections(body)
            payload["system_prompt"] = system_prompt
            payload["user_prompt"] = user_prompt
        rows.append(payload)
    return rows


def replay_request_trace_rows(
    request_rows: list[dict[str, Any]],
    controller_parameters: dict[str, Any],
    *,
    client: OpenAICompatibleClient | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    config = OpenAICompatibleConfig.from_dict(controller_parameters)
    replay_client = OpenAICompatibleClient(config) if client is None else client
    selected_rows = list(request_rows if limit is None else request_rows[: max(0, int(limit))])
    row_summaries: list[dict[str, Any]] = []
    elapsed_seconds_total = 0.0

    for row_index, request_row in enumerate(selected_rows):
        attempt_trace: list[dict[str, Any]] = []
        started_at = time.perf_counter()
        try:
            decision = replay_client.request_operator_decision(
                system_prompt=str(request_row["system_prompt"]),
                user_prompt=str(request_row["user_prompt"]),
                candidate_operator_ids=tuple(str(value) for value in request_row["candidate_operator_ids"]),
                attempt_trace=attempt_trace,
            )
            error_message = None
            selected_operator_id = decision.selected_operator_id
            valid = True
        except Exception as exc:
            error_message = str(exc)
            selected_operator_id = None
            valid = False
        elapsed_seconds = max(0.0, float(time.perf_counter() - started_at))
        elapsed_seconds_total += elapsed_seconds
        row_summaries.append(
            {
                "row_index": int(row_index),
                "generation_index": int(request_row.get("generation_index", 0)),
                "evaluation_index": int(request_row.get("evaluation_index", 0)),
                "candidate_operator_ids": [str(value) for value in request_row["candidate_operator_ids"]],
                "valid": valid,
                "retried": len(attempt_trace) > 1,
                "attempt_count": int(len(attempt_trace)),
                "selected_operator_id": selected_operator_id,
                "error": error_message,
                "elapsed_seconds": elapsed_seconds,
                "attempt_trace": list(attempt_trace),
            }
        )

    request_count = len(row_summaries)
    success_count = sum(1 for row in row_summaries if row["valid"])
    retry_row_count = sum(1 for row in row_summaries if row["retried"])
    fallback_equivalent_count = sum(1 for row in row_summaries if not row["valid"])
    return {
        "aggregate": {
            "request_count": int(request_count),
            "success_count": int(success_count),
            "retry_row_count": int(retry_row_count),
            "fallback_equivalent_count": int(fallback_equivalent_count),
            "success_rate": 0.0 if request_count <= 0 else success_count / float(request_count),
            "retry_rate": 0.0 if request_count <= 0 else retry_row_count / float(request_count),
            "fallback_equivalent_rate": (
                0.0 if request_count <= 0 else fallback_equivalent_count / float(request_count)
            ),
            "elapsed_seconds_total": float(elapsed_seconds_total),
            "elapsed_seconds_avg": 0.0 if request_count <= 0 else elapsed_seconds_total / float(request_count),
        },
        "rows": row_summaries,
    }


def replay_request_trace_file(
    request_trace_path: str | Path,
    controller_parameters: dict[str, Any],
    *,
    client: OpenAICompatibleClient | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    replay_summary = replay_request_trace_rows(
        load_request_trace(request_trace_path),
        controller_parameters,
        client=client,
        limit=limit,
    )
    replay_summary["replay_meta"] = {
        "request_trace_path": str(request_trace_path),
        "provider": str(controller_parameters["provider"]),
        "model": str(controller_parameters["model"]),
        "capability_profile": str(controller_parameters["capability_profile"]),
        "performance_profile": str(controller_parameters["performance_profile"]),
    }
    return replay_summary


def save_replay_summary(path: str | Path, payload: dict[str, Any]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output_path
