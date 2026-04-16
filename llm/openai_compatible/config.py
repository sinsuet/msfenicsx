"""Configuration helpers for OpenAI-compatible controller clients."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class OpenAICompatibleConfig:
    provider: str
    model: str
    capability_profile: str
    performance_profile: str
    api_key_env_var: str
    max_output_tokens: int
    temperature: float | None = None
    reasoning: dict[str, Any] = field(default_factory=dict)
    retry: dict[str, Any] = field(default_factory=dict)
    memory: dict[str, Any] = field(default_factory=dict)
    base_url: str | None = None
    base_url_env_var: str | None = None
    fallback_controller: str = "random_uniform"

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> OpenAICompatibleConfig:
        return cls(
            provider=str(payload["provider"]),
            model=str(payload["model"]),
            capability_profile=str(payload["capability_profile"]),
            performance_profile=str(payload["performance_profile"]),
            api_key_env_var=str(payload["api_key_env_var"]),
            max_output_tokens=int(payload["max_output_tokens"]),
            temperature=None if payload.get("temperature") is None else float(payload["temperature"]),
            reasoning=dict(payload.get("reasoning", {})),
            retry=dict(payload.get("retry", {})),
            memory=dict(payload.get("memory", {})),
            base_url=None if payload.get("base_url") is None else str(payload["base_url"]),
            base_url_env_var=None if payload.get("base_url_env_var") is None else str(payload["base_url_env_var"]),
            fallback_controller=str(payload.get("fallback_controller", "random_uniform")),
        )

    def resolve_api_key(
        self,
        environ: Mapping[str, str] | None = None,
        *,
        dotenv_path: str | Path | None = None,
    ) -> str:
        environment = os.environ if environ is None else environ
        api_key = str(environment.get(self.api_key_env_var, "")).strip()
        if not api_key:
            dotenv_payload = _load_dotenv_payload(dotenv_path)
            api_key = str(dotenv_payload.get(self.api_key_env_var, "")).strip()
        if not api_key:
            raise RuntimeError(f"Missing API key in environment variable '{self.api_key_env_var}'.")
        return api_key

    def resolve_base_url(
        self,
        environ: Mapping[str, str] | None = None,
        *,
        dotenv_path: str | Path | None = None,
    ) -> str | None:
        if self.base_url:
            return self.base_url
        if not self.base_url_env_var:
            return None
        environment = os.environ if environ is None else environ
        value = str(environment.get(self.base_url_env_var, "")).strip()
        if not value:
            dotenv_payload = _load_dotenv_payload(dotenv_path)
            value = str(dotenv_payload.get(self.base_url_env_var, "")).strip()
        return value or None

    @property
    def timeout_seconds(self) -> float | None:
        timeout = self.retry.get("timeout_seconds")
        return None if timeout is None else float(timeout)

    @property
    def max_attempts(self) -> int:
        attempts = self.retry.get("max_attempts")
        if attempts is None:
            return 1
        return max(1, int(attempts))


def _load_dotenv_payload(dotenv_path: str | Path | None) -> dict[str, str]:
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
