from pathlib import Path

import pytest
import yaml

from llm.openai_compatible.profile_loader import load_provider_profile_overlay


def _write_profiles(path: Path, payload: dict) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_load_provider_profile_resolves_runtime_overlay_from_dotenv(tmp_path: Path) -> None:
    profiles_path = tmp_path / "profiles.yaml"
    _write_profiles(
        profiles_path,
        {
            "schema_version": "1.0",
            "profiles": {
                "gpt": {
                    "source_api_key_env_var": "GPT_PROXY_API_KEY",
                    "source_base_url_env_var": "GPT_PROXY_BASE_URL",
                    "model": "gpt-5.4",
                }
            },
        },
    )
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "GPT_PROXY_API_KEY=test-gpt-key\nGPT_PROXY_BASE_URL=https://gpt.example/v1\n",
        encoding="utf-8",
    )

    overlay = load_provider_profile_overlay("gpt", profiles_path=profiles_path, dotenv_path=dotenv_path)

    assert overlay == {
        "LLM_API_KEY": "test-gpt-key",
        "LLM_BASE_URL": "https://gpt.example/v1",
        "LLM_MODEL": "gpt-5.4",
    }


def test_load_provider_profile_rejects_unknown_profile(tmp_path: Path) -> None:
    profiles_path = tmp_path / "profiles.yaml"
    _write_profiles(
        profiles_path,
        {
            "schema_version": "1.0",
            "profiles": {},
        },
    )

    with pytest.raises(ValueError, match="Unknown LLM profile"):
        load_provider_profile_overlay("claude2", profiles_path=profiles_path)


def test_load_provider_profile_requires_source_base_url(tmp_path: Path) -> None:
    profiles_path = tmp_path / "profiles.yaml"
    _write_profiles(
        profiles_path,
        {
            "schema_version": "1.0",
            "profiles": {
                "qwen": {
                    "source_api_key_env_var": "QWEN_PROXY_API_KEY",
                    "source_base_url_env_var": "QWEN_PROXY_BASE_URL",
                    "model": "qwen3.6-plus",
                }
            },
        },
    )
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("QWEN_PROXY_API_KEY=qwen-key\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Missing source base URL"):
        load_provider_profile_overlay("qwen", profiles_path=profiles_path, dotenv_path=dotenv_path)


def test_bundled_profiles_support_default_profile_via_gpt_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GPT_PROXY_API_KEY", "bundled-gpt-key")
    monkeypatch.setenv("GPT_PROXY_BASE_URL", "https://bundled-gpt.example/v1")

    overlay = load_provider_profile_overlay("default")

    assert overlay == {
        "LLM_API_KEY": "bundled-gpt-key",
        "LLM_BASE_URL": "https://bundled-gpt.example/v1",
        "LLM_MODEL": "gpt-5.4",
    }


@pytest.mark.parametrize(
    ("profile_id", "api_key_env_var", "base_url_env_var", "api_key", "base_url", "expected_model"),
    [
        (
            "gpt",
            "GPT_PROXY_API_KEY",
            "GPT_PROXY_BASE_URL",
            "bundled-gpt-key",
            "https://bundled-gpt.example/v1",
            "gpt-5.4",
        ),
        (
            "claude",
            "CLAUDE_PROXY_API_KEY",
            "CLAUDE_PROXY_BASE_URL",
            "bundled-claude-key",
            "https://bundled-claude.example/v1",
            "claude-sonnet-4-6",
        ),
        (
            "qwen",
            "QWEN_PROXY_API_KEY",
            "QWEN_PROXY_BASE_URL",
            "bundled-qwen-key",
            "https://bundled-qwen.example/v1",
            "qwen3.6-plus",
        ),
        (
            "deepseek",
            "DEEPSEEK_PROXY_API_KEY",
            "DEEPSEEK_RPOXY_BASE_URL",
            "bundled-deepseek-key",
            "https://bundled-deepseek.example/v1",
            "DeepSeek-V4-Flash",
        ),
    ],
)
def test_bundled_profiles_use_expected_default_models(
    monkeypatch: pytest.MonkeyPatch,
    profile_id: str,
    api_key_env_var: str,
    base_url_env_var: str,
    api_key: str,
    base_url: str,
    expected_model: str,
) -> None:
    monkeypatch.setenv(api_key_env_var, api_key)
    monkeypatch.setenv(base_url_env_var, base_url)

    overlay = load_provider_profile_overlay(profile_id)

    assert overlay == {
        "LLM_API_KEY": api_key,
        "LLM_BASE_URL": base_url,
        "LLM_MODEL": expected_model,
    }
