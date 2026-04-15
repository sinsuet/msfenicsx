"""Shared environment and dotenv helpers for OpenAI-compatible runtime config."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping


def load_dotenv_payload(dotenv_path: str | Path | None = None) -> dict[str, str]:
    candidate_path = Path(".env") if dotenv_path is None else Path(dotenv_path)
    if not candidate_path.exists():
        return {}
    payload: dict[str, str] = {}
    for raw_line in candidate_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        payload[key.strip()] = value.strip()
    return payload


def resolve_optional_env_value(
    env_var_name: str | None,
    environ: Mapping[str, str] | None = None,
    *,
    dotenv_path: str | Path | None = None,
) -> str | None:
    if env_var_name is None or not str(env_var_name).strip():
        return None
    environment = os.environ if environ is None else environ
    value = str(environment.get(str(env_var_name), "")).strip()
    if not value:
        dotenv_payload = load_dotenv_payload(dotenv_path)
        value = str(dotenv_payload.get(str(env_var_name), "")).strip()
    return value or None
