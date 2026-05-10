from __future__ import annotations

from pathlib import Path

import yaml

from optimizers.io import load_optimization_spec


LLM_SPECS = (
    Path("scenarios/optimization/s4_aggressive10_llm.yaml"),
    Path("scenarios/optimization/s5_aggressive15_llm.yaml"),
    Path("scenarios/optimization/s6_aggressive20_llm.yaml"),
)


def test_s4_s5_s6_llm_specs_default_to_deepseek_v4_flash() -> None:
    registry = yaml.safe_load(Path("llm/openai_compatible/profiles.yaml").read_text(encoding="utf-8"))
    deepseek_profile = registry["profiles"]["deepseek_v4_flash"]

    assert registry["profiles"]["default"] == deepseek_profile
    assert "gemma4" not in registry["profiles"]
    assert deepseek_profile["model"] == "deepseek-v4-flash"
    assert deepseek_profile["max_output_tokens"] == 1024

    for spec_path in LLM_SPECS:
        spec = load_optimization_spec(spec_path)
        assert spec.operator_control is not None
        params = spec.operator_control["controller_parameters"]
        assert params["provider_profile"] == "deepseek_v4_flash"
        assert params["model_env_var"] == "LLM_MODEL"
        assert params["api_key_env_var"] == "LLM_API_KEY"
        assert params["base_url_env_var"] == "LLM_BASE_URL"
        assert params["max_output_tokens"] == deepseek_profile["max_output_tokens"]
