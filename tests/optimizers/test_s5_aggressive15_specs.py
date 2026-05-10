from __future__ import annotations

from pathlib import Path

from evaluation.io import load_spec
from optimizers.algorithm_config import resolve_algorithm_config
from optimizers.io import generate_benchmark_case, load_optimization_spec
from optimizers.operator_pool.operators import approved_operator_pool


RAW = Path("scenarios/optimization/s5_aggressive15_raw.yaml")
UNION = Path("scenarios/optimization/s5_aggressive15_union.yaml")
LLM = Path("scenarios/optimization/s5_aggressive15_llm.yaml")
LLM_DIRECT = Path("scenarios/optimization/s5_aggressive15_llm_direct.yaml")
EVAL = Path("scenarios/evaluation/s5_aggressive15_eval.yaml")
EXPECTED_VARIABLE_IDS = [item for index in range(1, 16) for item in (f"c{index:02d}_x", f"c{index:02d}_y")] + [
    "sink_start",
    "sink_end",
]
EXPECTED_NEUTRAL_UNION_OPERATOR_WEIGHTS = {
    "vector_sbx_pm": 0.60,
    "component_jitter_1": 0.05,
    "anchored_component_jitter": 0.05,
    "sink_shift": 0.05,
    "sink_resize": 0.05,
    "component_relocate_1": 0.08,
    "component_swap_2": 0.04,
    "component_block_translate_2_4": 0.04,
    "component_subspace_sbx": 0.04,
}


def _variable_ids(spec_path: Path) -> list[str]:
    return [str(item["variable_id"]) for item in load_optimization_spec(spec_path).design_variables]


def test_s5_optimization_specs_load_with_same_32_variables() -> None:
    raw = load_optimization_spec(RAW)
    union = load_optimization_spec(UNION)
    llm = load_optimization_spec(LLM)

    assert raw.benchmark_source["template_path"] == "scenarios/templates/s5_aggressive15.yaml"
    assert raw.evaluation_protocol["evaluation_spec_path"] == "scenarios/evaluation/s5_aggressive15_eval.yaml"
    assert len(raw.design_variables) == 32
    assert len(union.design_variables) == 32
    assert len(llm.design_variables) == 32
    assert _variable_ids(RAW) == EXPECTED_VARIABLE_IDS
    assert _variable_ids(UNION) == EXPECTED_VARIABLE_IDS
    assert _variable_ids(LLM) == EXPECTED_VARIABLE_IDS


def test_s5_registry_split_uses_structured_primitives_for_union_and_llm() -> None:
    raw = load_optimization_spec(RAW).to_dict()
    union = load_optimization_spec(UNION).to_dict()
    llm = load_optimization_spec(LLM).to_dict()

    assert raw["algorithm"]["mode"] == "raw"
    assert "operator_control" not in raw
    assert union["operator_control"]["controller"] == "random_uniform"
    assert union["operator_control"]["registry_profile"] == "primitive_structured"
    assert tuple(union["operator_control"]["operator_pool"]) == approved_operator_pool("primitive_structured")
    assert union["operator_control"]["controller_parameters"]["operator_weights"] == (
        EXPECTED_NEUTRAL_UNION_OPERATOR_WEIGHTS
    )
    assert llm["operator_control"]["controller"] == "llm"
    assert llm["operator_control"]["registry_profile"] == "primitive_structured"
    assert tuple(llm["operator_control"]["operator_pool"]) == approved_operator_pool("primitive_structured")
    assert llm["operator_control"]["operator_pool"] == union["operator_control"]["operator_pool"]
    params = llm["operator_control"]["controller_parameters"]
    assert params["selection_strategy"] == "semantic_ranked_pick"
    assert params["max_output_tokens"] == 1024
    assert params["semantic_ranked_pick"] == {
        "max_rank_scan": 9,
        "generation_operator_cap_fraction": 0.35,
        "rolling_operator_cap_fraction": 0.40,
        "rolling_semantic_task_cap_fraction": 0.55,
        "rolling_window": 16,
        "near_tie_score_margin": 0.03,
        "low_confidence_threshold": 0.35,
    }
    assert "semantic_prior_sampler" not in params
    assert llm["evaluation_protocol"] == union["evaluation_protocol"]


def test_s5_llm_direct_spec_is_isolated_from_semantic_controller_mechanisms() -> None:
    union = load_optimization_spec(UNION).to_dict()
    llm = load_optimization_spec(LLM).to_dict()
    direct = load_optimization_spec(LLM_DIRECT).to_dict()

    assert direct["spec_meta"]["spec_id"] == "s5_aggressive15_nsga2_llm_direct"
    assert direct["benchmark_source"] == llm["benchmark_source"]
    assert direct["design_variables"] == llm["design_variables"]
    assert direct["algorithm"]["family"] == "genetic"
    assert direct["algorithm"]["backbone"] == "nsga2"
    assert direct["algorithm"]["mode"] == "union"
    assert direct["algorithm"]["profile_path"] == llm["algorithm"]["profile_path"]
    assert direct["algorithm"]["population_size"] == llm["algorithm"]["population_size"]
    assert direct["algorithm"]["num_generations"] == llm["algorithm"]["num_generations"]
    assert direct["evaluation_protocol"] == union["evaluation_protocol"]
    assert direct["operator_control"]["controller"] == "llm_direct"
    assert direct["operator_control"]["registry_profile"] == "primitive_structured"
    assert direct["operator_control"]["operator_pool"] == union["operator_control"]["operator_pool"]
    assert direct["operator_control"]["operator_pool"] == llm["operator_control"]["operator_pool"]

    params = direct["operator_control"]["controller_parameters"]
    assert params["provider_profile"] == "deepseek_v4_flash"
    assert params["provider"] == "openai-compatible"
    assert params["capability_profile"] == "chat_compatible_json"
    assert params["performance_profile"] == "balanced"
    assert params["model_env_var"] == "LLM_MODEL"
    assert params["api_key_env_var"] == "LLM_API_KEY"
    assert params["base_url_env_var"] == "LLM_BASE_URL"
    assert params["max_output_tokens"] == 1024
    assert params["temperature"] == 0.7
    assert params["retry"]["max_attempts"] == 2
    assert params["retry"]["timeout_seconds"] == 35
    assert "selection_strategy" not in params
    assert "semantic_ranked_pick" not in params
    assert "semantic_prior_sampler" not in params
    assert "memory" not in params
    assert "fallback_controller" not in params


def test_s5_profiles_resolve_algorithm_parameters() -> None:
    raw = load_optimization_spec(RAW)
    union = load_optimization_spec(UNION)
    llm = load_optimization_spec(LLM)

    raw_algorithm = resolve_algorithm_config(RAW, raw)
    union_algorithm = resolve_algorithm_config(UNION, union)
    llm_algorithm = resolve_algorithm_config(LLM, llm)

    assert raw_algorithm["parameters"]["crossover"]["eta"] == 10
    assert raw_algorithm["parameters"]["mutation"]["eta"] == 15
    assert union_algorithm["parameters"] == llm_algorithm["parameters"]


def test_s5_evaluation_spec_has_expected_objectives_and_constraints() -> None:
    spec = load_spec(EVAL).to_dict()
    constraints = {constraint["constraint_id"]: constraint for constraint in spec["constraints"]}

    assert [objective["metric"] for objective in spec["objectives"]] == [
        "summary.temperature_max",
        "summary.temperature_gradient_rms",
    ]
    assert set(constraints) == {
        "radiator_span_budget",
        "c01_peak_temperature_limit",
        "c02_peak_temperature_limit",
        "c04_peak_temperature_limit",
        "c06_peak_temperature_limit",
        "c12_peak_temperature_limit",
    }
    assert constraints["radiator_span_budget"]["limit"] == 0.35
    assert constraints["c01_peak_temperature_limit"]["limit"] == 333.5
    assert constraints["c02_peak_temperature_limit"]["limit"] == 333.0
    assert constraints["c04_peak_temperature_limit"]["limit"] == 332.5
    assert constraints["c06_peak_temperature_limit"]["limit"] == 333.0
    assert constraints["c12_peak_temperature_limit"]["limit"] == 332.5


def test_s5_spec_generates_fifteen_component_case() -> None:
    spec = load_optimization_spec(RAW)
    case = generate_benchmark_case(RAW, spec)

    assert case.case_meta["scenario_id"] == "s5_aggressive15"
    assert len(case.components) == 15
    assert len(case.boundary_features) == 1
    assert case.boundary_features[0]["edge"] == "top"
