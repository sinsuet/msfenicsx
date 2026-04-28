from __future__ import annotations

from pathlib import Path

from evaluation.io import load_spec
from optimizers.algorithm_config import resolve_algorithm_config
from optimizers.io import generate_benchmark_case, load_optimization_spec
from optimizers.operator_pool.operators import approved_operator_pool


S7_RAW = Path("scenarios/optimization/s7_aggressive25_raw.yaml")
S7_UNION = Path("scenarios/optimization/s7_aggressive25_union.yaml")
S7_LLM = Path("scenarios/optimization/s7_aggressive25_llm.yaml")
S7_EVAL = Path("scenarios/evaluation/s7_aggressive25_eval.yaml")
EXPECTED_VARIABLE_IDS = [
    variable_id
    for index in range(1, 26)
    for variable_id in (f"c{index:02d}_x", f"c{index:02d}_y")
] + ["sink_start", "sink_end"]


def _variable_ids(spec_path: Path) -> list[str]:
    return [str(item["variable_id"]) for item in load_optimization_spec(spec_path).design_variables]


def test_s7_optimization_specs_load_with_matched_52_variables() -> None:
    raw = load_optimization_spec(S7_RAW)
    union = load_optimization_spec(S7_UNION)
    llm = load_optimization_spec(S7_LLM)

    assert raw.benchmark_source["template_path"] == "scenarios/templates/s7_aggressive25.yaml"
    assert raw.evaluation_protocol["evaluation_spec_path"] == "scenarios/evaluation/s7_aggressive25_eval.yaml"
    assert _variable_ids(S7_RAW) == EXPECTED_VARIABLE_IDS
    assert _variable_ids(S7_UNION) == EXPECTED_VARIABLE_IDS
    assert _variable_ids(S7_LLM) == EXPECTED_VARIABLE_IDS
    assert len(raw.design_variables) == 52
    assert len(union.design_variables) == 52
    assert len(llm.design_variables) == 52


def test_s7_registry_split_uses_structured_pool_for_union_and_llm_only() -> None:
    raw = load_optimization_spec(S7_RAW).to_dict()
    union = load_optimization_spec(S7_UNION).to_dict()
    llm = load_optimization_spec(S7_LLM).to_dict()

    assert raw["algorithm"]["mode"] == "raw"
    assert "operator_control" not in raw
    assert union["operator_control"]["controller"] == "random_uniform"
    assert union["operator_control"]["registry_profile"] == "primitive_structured"
    assert tuple(union["operator_control"]["operator_pool"]) == approved_operator_pool("primitive_structured")
    assert llm["operator_control"]["controller"] == "llm"
    assert llm["operator_control"]["registry_profile"] == "primitive_structured"
    assert tuple(llm["operator_control"]["operator_pool"]) == approved_operator_pool("primitive_structured")
    assert llm["operator_control"]["operator_pool"] == union["operator_control"]["operator_pool"]


def test_s7_profiles_resolve_algorithm_parameters() -> None:
    raw = load_optimization_spec(S7_RAW)
    union = load_optimization_spec(S7_UNION)

    raw_algorithm = resolve_algorithm_config(S7_RAW, raw)
    union_algorithm = resolve_algorithm_config(S7_UNION, union)

    assert raw_algorithm["parameters"]["crossover"]["eta"] == 10
    assert raw_algorithm["parameters"]["mutation"]["eta"] == 15
    assert union_algorithm["parameters"]["crossover"]["eta"] == 10
    assert union_algorithm["parameters"]["mutation"]["eta"] == 15


def test_s7_evaluation_spec_has_expected_constraints() -> None:
    spec = load_spec(S7_EVAL).to_dict()
    constraint_ids = {constraint["constraint_id"] for constraint in spec["constraints"]}

    assert [objective["metric"] for objective in spec["objectives"]] == [
        "summary.temperature_max",
        "summary.temperature_gradient_rms",
    ]
    assert {
        "radiator_span_budget",
        "c02_peak_temperature_limit",
        "c04_peak_temperature_limit",
        "c06_peak_temperature_limit",
        "c12_peak_temperature_limit",
        "c17_peak_temperature_limit",
    } <= constraint_ids
    radiator_budget = next(
        constraint for constraint in spec["constraints"] if constraint["constraint_id"] == "radiator_span_budget"
    )
    assert 0.37 <= float(radiator_budget["limit"]) <= 0.38


def test_s7_spec_generates_twenty_five_component_case() -> None:
    spec = load_optimization_spec(S7_RAW)
    case = generate_benchmark_case(S7_RAW, spec)

    assert case.case_meta["scenario_id"] == "s7_aggressive25"
    assert len(case.components) == 25
