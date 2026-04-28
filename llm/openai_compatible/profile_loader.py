"""Provider profile loading for OpenAI-compatible runtime switching."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from llm.openai_compatible.env import resolve_optional_env_value


def load_provider_profile_overlay(
    profile_id: str,
    *,
    profiles_path: str | Path | None = None,
    dotenv_path: str | Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    resolved_profile_id = str(profile_id).strip()
    registry = _load_profiles_registry(profiles_path)
    profiles = registry.get("profiles")
    if not isinstance(profiles, Mapping):
        raise ValueError("LLM profiles registry must define a 'profiles' mapping.")
    raw_profile = profiles.get(resolved_profile_id)
    if not isinstance(raw_profile, Mapping):
        available_profiles = ", ".join(sorted(str(name) for name in profiles))
        raise ValueError(
            f"Unknown LLM profile '{resolved_profile_id}'. Available profiles: {available_profiles or '(none)'}."
        )

    source_api_key_env_var = _require_text(
        raw_profile.get("source_api_key_env_var"),
        f"profile '{resolved_profile_id}'.source_api_key_env_var",
    )
    source_base_url_env_var = _require_text(
        raw_profile.get("source_base_url_env_var"),
        f"profile '{resolved_profile_id}'.source_base_url_env_var",
    )
    model = _require_text(raw_profile.get("model"), f"profile '{resolved_profile_id}'.model")

    api_key = resolve_optional_env_value(source_api_key_env_var, environ, dotenv_path=dotenv_path)
    if not api_key:
        raise RuntimeError(
            f"Missing source API key env var '{source_api_key_env_var}' for profile '{resolved_profile_id}'."
        )
    base_url = resolve_optional_env_value(source_base_url_env_var, environ, dotenv_path=dotenv_path)
    if not base_url:
        raise RuntimeError(
            f"Missing source base URL env var '{source_base_url_env_var}' for profile '{resolved_profile_id}'."
        )

    overlay = {
        "LLM_API_KEY": api_key,
        "LLM_BASE_URL": base_url,
        "LLM_MODEL": model,
    }
    extra_body = raw_profile.get("extra_body")
    if extra_body is not None:
        if not isinstance(extra_body, Mapping):
            raise ValueError(
                f"LLM profiles registry field 'profile {resolved_profile_id}.extra_body' must be a mapping."
            )
        overlay["LLM_EXTRA_BODY"] = json.dumps(dict(extra_body), sort_keys=True, separators=(",", ":"))
    return overlay


def _load_profiles_registry(profiles_path: str | Path | None) -> dict[str, Any]:
    resolved_path = Path(profiles_path) if profiles_path is not None else Path(__file__).with_name("profiles.yaml")
    if not resolved_path.exists():
        raise RuntimeError(f"LLM profiles registry does not exist: {resolved_path}")
    payload = yaml.safe_load(resolved_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"LLM profiles registry must deserialize to a mapping: {resolved_path}")
    return payload


def _require_text(value: Any, label: str) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        raise ValueError(f"LLM profiles registry field '{label}' must be non-empty text.")
    return text
