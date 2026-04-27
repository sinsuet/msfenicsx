from __future__ import annotations

from pathlib import Path

from evaluation.io import load_spec
from optimizers.algorithm_config import resolve_algorithm_config
from optimizers.io import generate_benchmark_case, load_optimization_spec
from optimizers.operator_pool.operators import approved_operator_pool


S3_RAW = Path("scenarios/optimization/s3_scale20_raw.yaml")
S3_UNION = Path("scenarios/optimization/s3_scale20_union.yaml")
S3_LLM = Path("scenarios/optimization/s3_scale20_llm.yaml")
S3_EVAL = Path("scenarios/evaluation/s3_scale20_eval.yaml")

S4_RAW = Path("scenarios/optimization/s4_dense25_raw.yaml")
S4_UNION = Path("scenarios/optimization/s4_dense25_union.yaml")
S4_LLM = Path("scenarios/optimization/s4_dense25_llm.yaml")
S4_EVAL = Path("scenarios/evaluation/s4_dense25_eval.yaml")


def _variable_ids(spec_path: Path) -> list[str]:
    return [str(item["variable_id"]) for item in load_optimization_spec(spec_path).design_variables]


def test_s3_optimization_specs_load_with_42_variables() -> None:
    raw = load_optimization_spec(S3_RAW)
    union = load_optimization_spec(S3_UNION)
    llm = load_optimization_spec(S3_LLM)

    assert raw.benchmark_source["template_path"] == "scenarios/templates/s3_scale20.yaml"
    assert raw.evaluation_protocol["evaluation_spec_path"] == "scenarios/evaluation/s3_scale20_eval.yaml"
    assert len(raw.design_variables) == 42
    assert len(union.design_variables) == 42
    assert len(llm.design_variables) == 42
    assert _variable_ids(S3_RAW)[-4:] == ["c20_x", "c20_y", "sink_start", "sink_end"]


def test_s3_registry_split_matches_active_ladder() -> None:
    raw = load_optimization_spec(S3_RAW).to_dict()
    union = load_optimization_spec(S3_UNION).to_dict()
    llm = load_optimization_spec(S3_LLM).to_dict()

    assert raw["algorithm"]["mode"] == "raw"
    assert "operator_control" not in raw
    assert union["operator_control"]["controller"] == "random_uniform"
    assert union["operator_control"]["registry_profile"] == "primitive_clean"
    assert tuple(union["operator_control"]["operator_pool"]) == approved_operator_pool("primitive_clean")
    assert llm["operator_control"]["controller"] == "llm"
    assert llm["operator_control"]["registry_profile"] == "primitive_plus_assisted"
    assert tuple(llm["operator_control"]["operator_pool"]) == approved_operator_pool("primitive_plus_assisted")
    assert llm["evaluation_protocol"]["legality_policy_id"] == "projection_plus_local_restore"


def test_s3_profiles_resolve_algorithm_parameters() -> None:
    raw = load_optimization_spec(S3_RAW)
    union = load_optimization_spec(S3_UNION)

    raw_algorithm = resolve_algorithm_config(S3_RAW, raw)
    union_algorithm = resolve_algorithm_config(S3_UNION, union)

    assert raw_algorithm["parameters"]["crossover"]["eta"] == 10
    assert raw_algorithm["parameters"]["mutation"]["eta"] == 15
    assert union_algorithm["parameters"]["crossover"]["eta"] == 10
    assert union_algorithm["parameters"]["mutation"]["eta"] == 15


def test_s3_evaluation_spec_has_expected_constraints() -> None:
    spec = load_spec(S3_EVAL).to_dict()
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
        "panel_temperature_spread_limit",
    } <= constraint_ids


def test_s3_spec_generates_twenty_component_case() -> None:
    spec = load_optimization_spec(S3_RAW)
    case = generate_benchmark_case(S3_RAW, spec)

    assert case.case_meta["scenario_id"] == "s3_scale20"
    assert len(case.components) == 20
