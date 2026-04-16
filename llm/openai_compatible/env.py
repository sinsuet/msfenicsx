"""Shared environment and dotenv helpers for OpenAI-compatible runtime config."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping


def load_dotenv_payload(dotenv_path: str | Path | None = None) -> dict[str, str]:
    for candidate_path in _candidate_dotenv_paths(dotenv_path):
        if not candidate_path.exists():
            continue
        payload: dict[str, str] = {}
        for raw_line in candidate_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            payload[key.strip()] = value.strip()
        if payload:
            return payload
    return {}


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


def _candidate_dotenv_paths(dotenv_path: str | Path | None) -> tuple[Path, ...]:
    if dotenv_path is not None:
        return (Path(dotenv_path),)
    current_dotenv = Path(".env")
    common_root_dotenv = _git_common_root_dotenv_path(Path.cwd())
    if common_root_dotenv is None or common_root_dotenv == current_dotenv:
        return (current_dotenv,)
    return (current_dotenv, common_root_dotenv)


def _git_common_root_dotenv_path(cwd: Path) -> Path | None:
    git_path = cwd / ".git"
    if not git_path.is_file():
        return None
    raw_head = git_path.read_text(encoding="utf-8").splitlines()
    if not raw_head:
        return None
    first_line = raw_head[0].strip()
    if not first_line.startswith("gitdir:"):
        return None
    git_dir = Path(first_line.split(":", 1)[1].strip())
    if not git_dir.is_absolute():
        git_dir = (cwd / git_dir).resolve()
    if git_dir.parent.name != "worktrees":
        return None
    common_git_dir = git_dir.parent.parent
    if common_git_dir.name != ".git":
        return None
    return common_git_dir.parent / ".env"
