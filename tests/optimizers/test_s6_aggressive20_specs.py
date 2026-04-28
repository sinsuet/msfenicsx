from __future__ import annotations

from pathlib import Path

from evaluation.io import load_spec
from optimizers.algorithm_config import resolve_algorithm_config
from optimizers.io import generate_benchmark_case, load_optimization_spec
from optimizers.operator_pool.operators import approved_operator_pool


RAW = Path("scenarios/optimization/s6_aggressive20_raw.yaml")
UNION = Path("scenarios/optimization/s6_aggressive20_union.yaml")
LLM = Path("scenarios/optimization/s6_aggressive20_llm.yaml")
EVAL = Path("scenarios/evaluation/s6_aggressive20_eval.yaml")
EXPECTED_VARIABLE_IDS = [item for index in range(1, 21) for item in (f"c{index:02d}_x", f"c{index:02d}_y")] + [
    "sink_start",
    "sink_end",
]


def _variable_ids(spec_path: Path) -> list[str]:
    return [str(item["variable_id"]) for item in load_optimization_spec(spec_path).design_variables]


def test_s6_optimization_specs_load_with_same_42_variables() -> None:
    raw = load_optimization_spec(RAW)
    union = load_optimization_spec(UNION)
    llm = load_optimization_spec(LLM)

    assert raw.benchmark_source["template_path"] == "scenarios/templates/s6_aggressive20.yaml"
    assert raw.evaluation_protocol["evaluation_spec_path"] == "scenarios/evaluation/s6_aggressive20_eval.yaml"
    assert len(raw.design_variables) == 42
    assert len(union.design_variables) == 42
    assert len(llm.design_variables) == 42
    assert _variable_ids(RAW) == EXPECTED_VARIABLE_IDS
    assert _variable_ids(UNION) == EXPECTED_VARIABLE_IDS
    assert _variable_ids(LLM) == EXPECTED_VARIABLE_IDS


def test_s6_registry_split_uses_structured_primitives_for_union_and_llm() -> None:
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
    assert llm["evaluation_protocol"] == union["evaluation_protocol"]


def test_s6_profiles_resolve_algorithm_parameters() -> None:
    raw = load_optimization_spec(RAW)
    union = load_optimization_spec(UNION)
    llm = load_optimization_spec(LLM)

    raw_algorithm = resolve_algorithm_config(RAW, raw)
    union_algorithm = resolve_algorithm_config(UNION, union)
    llm_algorithm = resolve_algorithm_config(LLM, llm)

    assert raw_algorithm["parameters"]["crossover"]["eta"] == 10
    assert raw_algorithm["parameters"]["mutation"]["eta"] == 15
    assert union_algorithm["parameters"] == llm_algorithm["parameters"]


def test_s6_evaluation_spec_has_expected_objectives_and_constraints() -> None:
    spec = load_spec(EVAL).to_dict()
    constraint_ids = {constraint["constraint_id"] for constraint in spec["constraints"]}

    assert [objective["metric"] for objective in spec["objectives"]] == [
        "summary.temperature_max",
        "summary.temperature_gradient_rms",
    ]
    assert {
        "radiator_span_budget",
        "c01_peak_temperature_limit",
        "c02_peak_temperature_limit",
        "c04_peak_temperature_limit",
        "c06_peak_temperature_limit",
        "c12_peak_temperature_limit",
        "c17_peak_temperature_limit",
    } == constraint_ids
    radiator = next(constraint for constraint in spec["constraints"] if constraint["constraint_id"] == "radiator_span_budget")
    assert radiator["limit"] == 0.36


def test_s6_spec_generates_twenty_component_case() -> None:
    spec = load_optimization_spec(RAW)
    case = generate_benchmark_case(RAW, spec)

    assert case.case_meta["scenario_id"] == "s6_aggressive20"
    assert len(case.components) == 20
    assert len(case.boundary_features) == 1
    assert case.boundary_features[0]["edge"] == "top"
