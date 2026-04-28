"""Configuration helpers for OpenAI-compatible controller clients."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from llm.openai_compatible.env import resolve_optional_env_value


@dataclass(frozen=True, slots=True)
class OpenAICompatibleConfig:
    provider: str
    model: str | None
    capability_profile: str
    performance_profile: str
    api_key_env_var: str
    max_output_tokens: int
    temperature: float | None = None
    reasoning: dict[str, Any] = field(default_factory=dict)
    retry: dict[str, Any] = field(default_factory=dict)
    memory: dict[str, Any] = field(default_factory=dict)
    extra_body: dict[str, Any] = field(default_factory=dict)
    base_url: str | None = None
    model_env_var: str | None = None
    base_url_env_var: str | None = None
    extra_body_env_var: str | None = "LLM_EXTRA_BODY"
    fallback_controller: str = "random_uniform"

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> OpenAICompatibleConfig:
        return cls(
            provider=str(payload["provider"]),
            model=None if payload.get("model") is None else str(payload["model"]),
            capability_profile=str(payload["capability_profile"]),
            performance_profile=str(payload["performance_profile"]),
            api_key_env_var=str(payload["api_key_env_var"]),
            max_output_tokens=int(payload["max_output_tokens"]),
            temperature=None if payload.get("temperature") is None else float(payload["temperature"]),
            reasoning=dict(payload.get("reasoning", {})),
            retry=dict(payload.get("retry", {})),
            memory=dict(payload.get("memory", {})),
            extra_body=dict(payload.get("extra_body", {})),
            base_url=None if payload.get("base_url") is None else str(payload["base_url"]),
            model_env_var=None if payload.get("model_env_var") is None else str(payload["model_env_var"]),
            base_url_env_var=None if payload.get("base_url_env_var") is None else str(payload["base_url_env_var"]),
            extra_body_env_var=(
                "LLM_EXTRA_BODY"
                if "extra_body_env_var" not in payload
                else None
                if payload.get("extra_body_env_var") is None
                else str(payload["extra_body_env_var"])
            ),
            fallback_controller=str(payload.get("fallback_controller", "random_uniform")),
        )

    def resolve_api_key(
        self,
        environ: Mapping[str, str] | None = None,
        *,
        dotenv_path: str | Path | None = None,
    ) -> str:
        environment = os.environ if environ is None else environ
        api_key = resolve_optional_env_value(
            self.api_key_env_var,
            environment,
            dotenv_path=dotenv_path,
        )
        if not api_key:
            raise RuntimeError(f"Missing API key in environment variable '{self.api_key_env_var}'.")
        return api_key

    def resolve_model(
        self,
        environ: Mapping[str, str] | None = None,
        *,
        dotenv_path: str | Path | None = None,
    ) -> str:
        model = resolve_optional_env_value(
            self.model_env_var,
            os.environ if environ is None else environ,
            dotenv_path=dotenv_path,
        )
        if model:
            return model
        literal_model = None if self.model is None else str(self.model).strip()
        if literal_model:
            return literal_model
        if self.model_env_var:
            raise RuntimeError(
                f"Missing model in configuration. Set literal 'model' or environment variable '{self.model_env_var}'."
            )
        raise RuntimeError("Missing model in configuration. Set literal 'model' or 'model_env_var'.")

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
        return resolve_optional_env_value(
            self.base_url_env_var,
            os.environ if environ is None else environ,
            dotenv_path=dotenv_path,
        )

    def resolve_extra_body(
        self,
        environ: Mapping[str, str] | None = None,
        *,
        dotenv_path: str | Path | None = None,
    ) -> dict[str, Any]:
        merged = dict(self.extra_body)
        raw_extra_body = resolve_optional_env_value(
            self.extra_body_env_var,
            os.environ if environ is None else environ,
            dotenv_path=dotenv_path,
        )
        if raw_extra_body:
            try:
                parsed = json.loads(raw_extra_body)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Environment variable '{self.extra_body_env_var}' must contain a JSON object."
                ) from exc
            if not isinstance(parsed, dict):
                raise ValueError(f"Environment variable '{self.extra_body_env_var}' must contain a JSON object.")
            merged.update(parsed)
        return merged

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
