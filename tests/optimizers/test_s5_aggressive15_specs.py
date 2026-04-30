from __future__ import annotations

from pathlib import Path

from evaluation.io import load_spec
from optimizers.algorithm_config import resolve_algorithm_config
from optimizers.io import generate_benchmark_case, load_optimization_spec
from optimizers.operator_pool.operators import approved_operator_pool


RAW = Path("scenarios/optimization/s5_aggressive15_raw.yaml")
UNION = Path("scenarios/optimization/s5_aggressive15_union.yaml")
LLM = Path("scenarios/optimization/s5_aggressive15_llm.yaml")
EVAL = Path("scenarios/evaluation/s5_aggressive15_eval.yaml")
EXPECTED_VARIABLE_IDS = [item for index in range(1, 16) for item in (f"c{index:02d}_x", f"c{index:02d}_y")] + [
    "sink_start",
    "sink_end",
]


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
    assert llm["operator_control"]["controller"] == "llm"
    assert llm["operator_control"]["registry_profile"] == "primitive_structured"
    assert tuple(llm["operator_control"]["operator_pool"]) == approved_operator_pool("primitive_structured")
    assert llm["operator_control"]["operator_pool"] == union["operator_control"]["operator_pool"]
    params = llm["operator_control"]["controller_parameters"]
    assert params["selection_strategy"] == "semantic_prior_sampler"
    assert params["max_output_tokens"] == 512
    assert params["semantic_prior_sampler"] == {
        "uniform_mix": 0.15,
        "min_probability_floor": 0.03,
        "generation_operator_cap_fraction": 0.35,
        "rolling_operator_cap_fraction": 0.40,
        "rolling_semantic_task_cap_fraction": 0.55,
        "rolling_window": 16,
        "risk_penalty_weight": 0.50,
    }
    assert llm["evaluation_protocol"] == union["evaluation_protocol"]


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
