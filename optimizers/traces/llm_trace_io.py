"""Helpers for locating and materializing LLM trace sidecars."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from optimizers.run_telemetry import load_jsonl_rows


def resolve_seed_trace_path(seed_root: Path, filename: str) -> Path:
    """Return the canonical spec path `seed_root/traces/<filename>`."""
    return Path(seed_root) / "traces" / filename


def is_concrete_optimizer_run_root(path: Path) -> bool:
    return (Path(path) / "traces" / "evaluation_events.jsonl").exists()


def iter_mode_seed_roots(mode_root: Path) -> list[Path]:
    root = Path(mode_root)
    if is_concrete_optimizer_run_root(root):
        return [root]
    seeds_root = root / "seeds"
    if not seeds_root.exists():
        return []

    seed_roots = sorted(
        [entry for entry in seeds_root.iterdir() if entry.is_dir() and entry.name.startswith("seed-")],
        key=lambda item: int(item.name.removeprefix("seed-")),
    )
    concrete_roots: list[Path] = []
    for seed_root in seed_roots:
        if not is_concrete_optimizer_run_root(seed_root):
            raise ValueError(
                f"Legacy nested seed bundle layout is unsupported under {seed_root}. "
                "Expected traces directly under seeds/seed-<n>/."
            )
        concrete_roots.append(seed_root)
    return concrete_roots


def materialize_request_trace_rows(
    seed_root: Path,
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    materialized: list[dict[str, Any]] = []
    for row in rows:
        payload = dict(row)
        prompt_ref = payload.get("prompt_ref")
        system_prompt = ""
        user_prompt = ""
        if prompt_ref:
            body = load_prompt_markdown_body(Path(seed_root), str(prompt_ref))
            system_prompt, user_prompt = split_request_prompt_sections(body)
        payload["system_prompt"] = system_prompt
        payload["user_prompt"] = user_prompt
        materialized.append(payload)
    return materialized


def materialize_response_trace_rows(
    seed_root: Path,
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    materialized: list[dict[str, Any]] = []
    for row in rows:
        payload = dict(row)
        response_ref = payload.get("response_ref")
        payload["response_text"] = ""
        if response_ref:
            payload["response_text"] = load_prompt_markdown_body(Path(seed_root), str(response_ref))
        materialized.append(payload)
    return materialized


def load_prompt_markdown_body(seed_root: Path, prompt_ref: str) -> str:
    path = Path(seed_root) / str(prompt_ref)
    if not path.exists():
        return ""
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        return content
    closing_marker = content.find("\n---\n", 4)
    if closing_marker == -1:
        return content
    return content[closing_marker + len("\n---\n") :]


def split_request_prompt_sections(body: str) -> tuple[str, str]:
    text = str(body)
    system_marker = "# System"
    user_marker = "# User"
    if system_marker in text and user_marker in text:
        system_start = text.index(system_marker) + len(system_marker)
        user_start = text.index(user_marker)
        system_prompt = text[system_start:user_start].strip()
        user_prompt = text[user_start + len(user_marker) :].strip()
        return system_prompt, user_prompt
    return "", text.strip()


def resolve_llm_model_label(seed_root: Path) -> str | None:
    response_path = resolve_seed_trace_path(seed_root, "llm_response_trace.jsonl")
    if response_path.exists():
        model = _first_nonempty_model(load_jsonl_rows(response_path))
        if model:
            return model
    summary_path = Path(seed_root) / "summaries" / "llm_runtime_summary.json"
    if summary_path.exists():
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        if isinstance(payload, Mapping):
            model = _normalize_model_value(payload.get("model"))
            if model:
                return model
    request_path = resolve_seed_trace_path(seed_root, "llm_request_trace.jsonl")
    if request_path.exists():
        model = _first_nonempty_model(load_jsonl_rows(request_path))
        if model:
            return model
    return None


def _first_nonempty_model(rows: Sequence[Mapping[str, Any]]) -> str | None:
    for row in rows:
        model = _normalize_model_value(row.get("model"))
        if model:
            return model
    return None


def _normalize_model_value(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        labels = [str(item).strip() for item in value if str(item).strip()]
        if labels:
            return ", ".join(labels)
    return None
