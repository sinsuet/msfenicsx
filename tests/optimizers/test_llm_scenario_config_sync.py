from __future__ import annotations

from pathlib import Path

import yaml

from optimizers.io import load_optimization_spec


LLM_SPECS = (
    Path("scenarios/optimization/s5_aggressive15_llm.yaml"),
    Path("scenarios/optimization/s6_aggressive20_llm.yaml"),
    Path("scenarios/optimization/s7_aggressive25_llm.yaml"),
)


def test_s5_s6_s7_gemma4_specs_share_profile_and_token_budget() -> None:
    registry = yaml.safe_load(Path("llm/openai_compatible/profiles.yaml").read_text(encoding="utf-8"))
    gemma4_profile = registry["profiles"]["gemma4"]

    assert gemma4_profile["model"] == "gemma4:31b-it-q8_0"
    assert gemma4_profile["max_output_tokens"] == 1024

    for spec_path in LLM_SPECS:
        spec = load_optimization_spec(spec_path)
        assert spec.operator_control is not None
        params = spec.operator_control["controller_parameters"]
        assert params["provider_profile"] == "gemma4"
        assert params["model_env_var"] == "LLM_MODEL"
        assert params["api_key_env_var"] == "LLM_API_KEY"
        assert params["base_url_env_var"] == "LLM_BASE_URL"
        assert params["max_output_tokens"] == gemma4_profile["max_output_tokens"]
