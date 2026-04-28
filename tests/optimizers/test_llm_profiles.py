import json
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
                "custom_model": {
                    "source_api_key_env_var": "CUSTOM_MODEL_API_KEY",
                    "source_base_url_env_var": "CUSTOM_MODEL_BASE_URL",
                    "model": "custom-model",
                }
            },
        },
    )
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "CUSTOM_MODEL_API_KEY=test-custom-key\nCUSTOM_MODEL_BASE_URL=https://custom.example/v1\n",
        encoding="utf-8",
    )

    overlay = load_provider_profile_overlay("custom_model", profiles_path=profiles_path, dotenv_path=dotenv_path)

    assert overlay == {
        "LLM_API_KEY": "test-custom-key",
        "LLM_BASE_URL": "https://custom.example/v1",
        "LLM_MODEL": "custom-model",
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
        load_provider_profile_overlay("unknown_model", profiles_path=profiles_path)


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


def test_load_provider_profile_exports_optional_extra_body_as_json(tmp_path: Path) -> None:
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
                    "extra_body": {"enable_thinking": False},
                }
            },
        },
    )
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "QWEN_PROXY_API_KEY=qwen-key\nQWEN_PROXY_BASE_URL=https://qwen.example/v1\n",
        encoding="utf-8",
    )

    overlay = load_provider_profile_overlay("qwen", profiles_path=profiles_path, dotenv_path=dotenv_path)

    assert overlay["LLM_API_KEY"] == "qwen-key"
    assert overlay["LLM_BASE_URL"] == "https://qwen.example/v1"
    assert overlay["LLM_MODEL"] == "qwen3.6-plus"
    assert json.loads(overlay["LLM_EXTRA_BODY"]) == {"enable_thinking": False}


def test_bundled_profiles_support_default_profile_via_qwen_coding_plan_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QWEN_PROXY_API_KEY", "bundled-coding-key")
    monkeypatch.setenv("QWEN_PROXY_BASE_URL", "https://coding.example/v1")

    overlay = load_provider_profile_overlay("default")

    assert overlay == {
        "LLM_API_KEY": "bundled-coding-key",
        "LLM_BASE_URL": "https://coding.example/v1",
        "LLM_MODEL": "qwen3.6-plus",
        "LLM_EXTRA_BODY": '{"enable_thinking":false}',
    }


@pytest.mark.parametrize(
    ("profile_id", "expected_model", "exports_enable_thinking_false"),
    [
        ("qwen3_6_plus", "qwen3.6-plus", True),
        ("glm_5", "glm-5", True),
        ("minimax_m2_5", "MiniMax-M2.5", False),
    ],
)
def test_bundled_coding_plan_profiles_share_qwen_proxy_route(
    monkeypatch: pytest.MonkeyPatch,
    profile_id: str,
    expected_model: str,
    exports_enable_thinking_false: bool,
) -> None:
    monkeypatch.setenv("QWEN_PROXY_API_KEY", "bundled-coding-key")
    monkeypatch.setenv("QWEN_PROXY_BASE_URL", "https://coding.example/v1")

    overlay = load_provider_profile_overlay(profile_id)

    assert overlay["LLM_API_KEY"] == "bundled-coding-key"
    assert overlay["LLM_BASE_URL"] == "https://coding.example/v1"
    assert overlay["LLM_MODEL"] == expected_model
    if exports_enable_thinking_false:
        assert json.loads(overlay["LLM_EXTRA_BODY"]) == {"enable_thinking": False}
    else:
        assert "LLM_EXTRA_BODY" not in overlay


def test_bundled_deepseek_v4_flash_profile_uses_model_named_env_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEPSEEK_PROXY_API_KEY", "bundled-deepseek-key")
    monkeypatch.setenv("DEEPSEEK_PROXY_BASE_URL", "https://llmapi.paratera.example/v1")

    overlay = load_provider_profile_overlay("deepseek_v4_flash")

    assert overlay == {
        "LLM_API_KEY": "bundled-deepseek-key",
        "LLM_BASE_URL": "https://llmapi.paratera.example/v1",
        "LLM_MODEL": "DeepSeek-V4-Flash",
    }


def test_bundled_gemma4_placeholder_uses_model_named_env_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMMA4_API_KEY", "bundled-gemma-key")
    monkeypatch.setenv("GEMMA4_BASE_URL", "https://gemma.example/v1")

    overlay = load_provider_profile_overlay("gemma4")

    assert overlay == {
        "LLM_API_KEY": "bundled-gemma-key",
        "LLM_BASE_URL": "https://gemma.example/v1",
        "LLM_MODEL": "gemma-4",
    }


@pytest.mark.parametrize("profile_id", ["gpt", "claude", "qwen"])
def test_bundled_profiles_reject_legacy_provider_style_profile_ids(profile_id: str) -> None:
    with pytest.raises(ValueError, match="Unknown LLM profile"):
        load_provider_profile_overlay(profile_id)


@pytest.mark.parametrize(
    "profile_id",
    [
        "qwen3_5_plus",
        "qwen3_coder_next",
        "qwen3_coder_plus",
        "qwen3_max_2026_01_23",
        "glm_4_7",
        "kimi_k2_5",
    ],
)
def test_bundled_profiles_reject_non_selected_coding_plan_models(profile_id: str) -> None:
    with pytest.raises(ValueError, match="Unknown LLM profile"):
        load_provider_profile_overlay(profile_id)


def test_env_example_documents_profile_runtime_routes() -> None:
    env_example = Path(".env.example")

    text = env_example.read_text(encoding="utf-8")

    for expected in [
        "QWEN_PROXY_API_KEY=",
        "QWEN_PROXY_BASE_URL=https://coding.dashscope.aliyuncs.com/v1",
        "DEEPSEEK_PROXY_API_KEY=",
        "DEEPSEEK_PROXY_BASE_URL=https://llmapi.paratera.com/v1",
        "GEMMA4_API_KEY=",
        "GEMMA4_BASE_URL=",
    ]:
        assert expected in text
    assert "GPT_PROXY_API_KEY" not in text
    assert "GPT_PROXY_BASE_URL" not in text
    assert "DEEPSEEK_V4_FLASH_API_KEY" not in text
    assert "DEEPSEEK_V4_FLASH_BASE_URL" not in text
