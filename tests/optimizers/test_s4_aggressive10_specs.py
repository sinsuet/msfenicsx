from __future__ import annotations

from pathlib import Path

from evaluation.io import load_spec
from optimizers.algorithm_config import resolve_algorithm_config
from optimizers.io import generate_benchmark_case, load_optimization_spec
from optimizers.operator_pool.operators import approved_operator_pool


RAW = Path("scenarios/optimization/s4_aggressive10_raw.yaml")
UNION = Path("scenarios/optimization/s4_aggressive10_union.yaml")
LLM = Path("scenarios/optimization/s4_aggressive10_llm.yaml")
EVAL = Path("scenarios/evaluation/s4_aggressive10_eval.yaml")
EXPECTED_VARIABLE_IDS = [item for index in range(1, 11) for item in (f"c{index:02d}_x", f"c{index:02d}_y")] + [
    "sink_start",
    "sink_end",
]
EXPECTED_BALANCED_WEAK_UNION_OPERATOR_WEIGHTS = {
    "vector_sbx_pm": 0.50,
    "component_jitter_1": 0.05,
    "anchored_component_jitter": 0.04,
    "sink_shift": 0.18,
    "sink_resize": 0.08,
    "component_relocate_1": 0.04,
    "component_swap_2": 0.04,
    "component_block_translate_2_4": 0.04,
    "component_subspace_sbx": 0.03,
}


def _variable_ids(spec_path: Path) -> list[str]:
    return [str(item["variable_id"]) for item in load_optimization_spec(spec_path).design_variables]


def test_s4_optimization_specs_load_with_same_22_variables_and_32x16_budget() -> None:
    raw = load_optimization_spec(RAW)
    union = load_optimization_spec(UNION)
    llm = load_optimization_spec(LLM)

    assert raw.benchmark_source["template_path"] == "scenarios/templates/s4_aggressive10.yaml"
    assert raw.evaluation_protocol["evaluation_spec_path"] == "scenarios/evaluation/s4_aggressive10_eval.yaml"
    assert len(raw.design_variables) == 22
    assert len(union.design_variables) == 22
    assert len(llm.design_variables) == 22
    assert _variable_ids(RAW) == EXPECTED_VARIABLE_IDS
    assert _variable_ids(UNION) == EXPECTED_VARIABLE_IDS
    assert _variable_ids(LLM) == EXPECTED_VARIABLE_IDS
    assert raw.algorithm["population_size"] == 32
    assert raw.algorithm["num_generations"] == 16
    assert union.algorithm["population_size"] == 32
    assert union.algorithm["num_generations"] == 16
    assert llm.algorithm["population_size"] == 32
    assert llm.algorithm["num_generations"] == 16


def test_s4_registry_split_uses_structured_primitives_for_union_and_deepseek_llm() -> None:
    raw = load_optimization_spec(RAW).to_dict()
    union = load_optimization_spec(UNION).to_dict()
    llm = load_optimization_spec(LLM).to_dict()

    assert raw["algorithm"]["mode"] == "raw"
    assert "operator_control" not in raw
    assert union["operator_control"]["controller"] == "random_uniform"
    assert union["operator_control"]["registry_profile"] == "primitive_structured"
    assert tuple(union["operator_control"]["operator_pool"]) == approved_operator_pool("primitive_structured")
    assert union["operator_control"]["controller_parameters"]["operator_weights"] == (
        EXPECTED_BALANCED_WEAK_UNION_OPERATOR_WEIGHTS
    )
    assert llm["operator_control"]["controller"] == "llm"
    assert llm["operator_control"]["registry_profile"] == "primitive_structured"
    assert tuple(llm["operator_control"]["operator_pool"]) == approved_operator_pool("primitive_structured")
    assert llm["operator_control"]["operator_pool"] == union["operator_control"]["operator_pool"]
    params = llm["operator_control"]["controller_parameters"]
    assert params["provider_profile"] == "deepseek_v4_flash"
    assert params["selection_strategy"] == "semantic_ranked_pick"
    assert params["max_output_tokens"] == 1024
    assert llm["evaluation_protocol"] == union["evaluation_protocol"]


def test_s4_profiles_resolve_algorithm_parameters() -> None:
    raw = load_optimization_spec(RAW)
    union = load_optimization_spec(UNION)
    llm = load_optimization_spec(LLM)

    raw_algorithm = resolve_algorithm_config(RAW, raw)
    union_algorithm = resolve_algorithm_config(UNION, union)
    llm_algorithm = resolve_algorithm_config(LLM, llm)

    assert raw_algorithm["parameters"]["crossover"]["eta"] == 10
    assert raw_algorithm["parameters"]["mutation"]["eta"] == 15
    assert union_algorithm["parameters"] == llm_algorithm["parameters"]


def test_s4_evaluation_spec_has_expected_objectives_and_constraints() -> None:
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
    }
    assert constraints["radiator_span_budget"]["limit"] == 0.32


def test_s4_spec_generates_ten_component_case() -> None:
    spec = load_optimization_spec(RAW)
    case = generate_benchmark_case(RAW, spec)

    assert case.case_meta["scenario_id"] == "s4_aggressive10"
    assert len(case.components) == 10
    assert len(case.boundary_features) == 1
    assert case.boundary_features[0]["edge"] == "top"
