from pathlib import Path

import pytest
import yaml

from optimizers.algorithm_config import resolve_algorithm_config
from optimizers.io import load_optimization_result, load_optimization_spec, save_optimization_result, save_optimization_spec
from optimizers.models import OptimizationResult, OptimizationSpec
from optimizers.operator_pool.operators import approved_union_operator_ids_for_backbone
from optimizers.validation import OptimizationValidationError


def _spec_payload() -> dict:
    return {
        "schema_version": "1.0",
        "spec_meta": {
            "spec_id": "s1_typical_nsga2_raw_fixture",
            "description": "Single-case s1_typical raw fixture.",
        },
        "benchmark_source": {
            "template_path": "scenarios/templates/s1_typical.yaml",
            "seed": 11,
        },
        "design_variables": [
            {
                "variable_id": "c01_x",
                "path": "components[0].pose.x",
                "lower_bound": 0.1,
                "upper_bound": 0.9,
            },
            {
                "variable_id": "c01_y",
                "path": "components[0].pose.y",
                "lower_bound": 0.1,
                "upper_bound": 0.68,
            },
            {
                "variable_id": "sink_start",
                "path": "boundary_features[0].start",
                "lower_bound": 0.05,
                "upper_bound": 0.7,
            },
            {
                "variable_id": "sink_end",
                "path": "boundary_features[0].end",
                "lower_bound": 0.2,
                "upper_bound": 0.95,
            },
        ],
        "algorithm": {
            "family": "genetic",
            "backbone": "nsga2",
            "mode": "raw",
            "population_size": 4,
            "num_generations": 1,
            "seed": 7,
        },
        "evaluation_protocol": {
            "evaluation_spec_path": "scenarios/evaluation/s1_typical_eval.yaml",
        },
    }


def _result_payload() -> dict:
    return {
        "schema_version": "1.0",
        "run_meta": {
            "run_id": "s1_typical_nsga2_raw_seed11",
            "base_case_id": "s1_typical-seed-0011",
            "optimization_spec_id": "s1_typical_nsga2_raw_fixture",
            "evaluation_spec_id": "s1_typical_eval",
        },
        "baseline_candidates": [
            {
                "evaluation_index": 1,
                "source": "baseline",
                "feasible": False,
                "decision_vector": {
                    "c01_x": 0.2,
                    "c01_y": 0.3,
                    "sink_start": 0.2,
                    "sink_end": 0.7,
                },
                "objective_values": {
                    "minimize_peak_temperature": 320.0,
                    "minimize_temperature_gradient_rms": 10.5,
                },
                "constraint_values": {
                    "radiator_span_budget": 0.05,
                    "c01_peak_temperature_limit": 1.2,
                },
                "evaluation_report": {
                    "evaluation_meta": {"case_id": "s1_typical-seed-0011"},
                    "metric_values": {"summary.temperature_max": 320.0},
                    "feasible": False,
                },
            }
        ],
        "pareto_front": [
            {
                "evaluation_index": 2,
                "source": "optimizer",
                "feasible": True,
                "decision_vector": {
                    "c01_x": 0.25,
                    "c01_y": 0.35,
                    "sink_start": 0.18,
                    "sink_end": 0.58,
                },
                "objective_values": {
                    "minimize_peak_temperature": 302.0,
                    "minimize_temperature_gradient_rms": 8.1,
                },
                "constraint_values": {
                    "radiator_span_budget": 0.0,
                    "c01_peak_temperature_limit": 0.0,
                },
                "evaluation_report": {
                    "evaluation_meta": {"case_id": "s1_typical-seed-0011"},
                    "metric_values": {"summary.temperature_max": 302.0},
                    "feasible": True,
                },
            }
        ],
        "representative_candidates": {
            "min-peak-temperature": {
                "evaluation_index": 2,
                "source": "optimizer",
                "feasible": True,
                "decision_vector": {
                    "c01_x": 0.25,
                    "c01_y": 0.35,
                    "sink_start": 0.18,
                    "sink_end": 0.58,
                },
                "objective_values": {
                    "minimize_peak_temperature": 302.0,
                    "minimize_temperature_gradient_rms": 8.1,
                },
                "constraint_values": {
                    "radiator_span_budget": 0.0,
                    "c01_peak_temperature_limit": 0.0,
                },
                "evaluation_report": {
                    "evaluation_meta": {"case_id": "s1_typical-seed-0011"},
                    "metric_values": {"summary.temperature_max": 302.0},
                    "feasible": True,
                },
            }
        },
        "aggregate_metrics": {
            "num_evaluations": 2,
            "feasible_rate": 0.5,
            "first_feasible_eval": 2,
            "pareto_size": 1,
        },
        "history": [
            {
                "evaluation_index": 1,
                "source": "baseline",
                "feasible": False,
                "decision_vector": {
                    "c01_x": 0.2,
                    "c01_y": 0.3,
                    "sink_start": 0.2,
                    "sink_end": 0.7,
                },
                "objective_values": {
                    "minimize_peak_temperature": 320.0,
                    "minimize_temperature_gradient_rms": 10.5,
                },
                "constraint_values": {
                    "radiator_span_budget": 0.05,
                    "c01_peak_temperature_limit": 1.2,
                },
                "evaluation_report": {
                    "evaluation_meta": {"case_id": "s1_typical-seed-0011"},
                    "metric_values": {"summary.temperature_max": 320.0},
                    "feasible": False,
                },
            },
            {
                "evaluation_index": 2,
                "source": "optimizer",
                "feasible": True,
                "decision_vector": {
                    "c01_x": 0.25,
                    "c01_y": 0.35,
                    "sink_start": 0.18,
                    "sink_end": 0.58,
                },
                "objective_values": {
                    "minimize_peak_temperature": 302.0,
                    "minimize_temperature_gradient_rms": 8.1,
                },
                "constraint_values": {
                    "radiator_span_budget": 0.0,
                    "c01_peak_temperature_limit": 0.0,
                },
                "evaluation_report": {
                    "evaluation_meta": {"case_id": "s1_typical-seed-0011"},
                    "metric_values": {"summary.temperature_max": 302.0},
                    "feasible": True,
                },
            },
        ],
        "provenance": {
            "benchmark_source": {"template_path": "scenarios/templates/s1_typical.yaml", "seed": 11},
            "source_case_id": "s1_typical-seed-0011",
            "source_optimization_spec_id": "s1_typical_nsga2_raw_fixture",
            "source_evaluation_spec_id": "s1_typical_eval",
        },
    }


def test_save_and_load_yaml_round_trip(tmp_path: Path) -> None:
    spec_path = tmp_path / "optimization_spec.yaml"
    result_path = tmp_path / "optimization_result.yaml"

    save_optimization_spec(OptimizationSpec.from_dict(_spec_payload()), spec_path)
    save_optimization_result(OptimizationResult.from_dict(_result_payload()), result_path)

    loaded_spec = load_optimization_spec(spec_path)
    assert loaded_spec.to_dict() == _spec_payload()
    assert loaded_spec.algorithm["family"] == "genetic"
    assert loaded_spec.algorithm["backbone"] == "nsga2"
    assert loaded_spec.algorithm["mode"] == "raw"

    loaded_result = load_optimization_result(result_path).to_dict()
    assert loaded_result == _result_payload()
    assert all("evaluation_report" in entry for entry in loaded_result["history"])
    assert all("case_reports" not in entry for entry in loaded_result["history"])


def test_active_raw_spec_resolves_s1_typical_profile_parameters() -> None:
    spec = load_optimization_spec("scenarios/optimization/s1_typical_raw.yaml")
    algorithm = resolve_algorithm_config("scenarios/optimization/s1_typical_raw.yaml", spec)

    assert {key: spec.algorithm[key] for key in ("family", "backbone", "mode")} == {
        "family": "genetic",
        "backbone": "nsga2",
        "mode": "raw",
    }
    assert len(spec.design_variables) == 32
    assert algorithm["parameters"]["crossover"]["eta"] == 10
    assert algorithm["parameters"]["mutation"]["eta"] == 15


def test_union_spec_requires_operator_control_block() -> None:
    with open("scenarios/optimization/s1_typical_union.yaml", "r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)

    payload.pop("operator_control")

    with pytest.raises(OptimizationValidationError):
        OptimizationSpec.from_dict(payload)


def test_union_spec_uses_exact_semantic_operator_pool() -> None:
    spec = load_optimization_spec("scenarios/optimization/s1_typical_union.yaml")

    assert {key: spec.algorithm[key] for key in ("family", "backbone", "mode")} == {
        "family": "genetic",
        "backbone": "nsga2",
        "mode": "union",
    }
    assert spec.operator_control is not None
    assert spec.operator_control["controller"] == "random_uniform"
    assert tuple(spec.operator_control["operator_pool"]) == approved_union_operator_ids_for_backbone("genetic", "nsga2")


def test_union_spec_rejects_modified_semantic_operator_pool() -> None:
    payload = load_optimization_spec("scenarios/optimization/s1_typical_union.yaml").to_dict()
    payload["operator_control"]["operator_pool"] = [
        operator_id
        for operator_id in payload["operator_control"]["operator_pool"]
        if operator_id != "slide_sink"
    ]

    with pytest.raises(OptimizationValidationError):
        OptimizationSpec.from_dict(payload)


def test_llm_spec_shares_benchmark_source_and_operator_pool_with_union_spec() -> None:
    union_spec = load_optimization_spec("scenarios/optimization/s1_typical_union.yaml")
    llm_spec = load_optimization_spec("scenarios/optimization/s1_typical_llm.yaml")

    assert union_spec.benchmark_source == llm_spec.benchmark_source
    assert union_spec.operator_control is not None
    assert llm_spec.operator_control is not None
    assert union_spec.operator_control["operator_pool"] == llm_spec.operator_control["operator_pool"]
    assert union_spec.operator_control["controller"] == "random_uniform"
    assert llm_spec.operator_control["controller"] == "llm"


def test_llm_spec_round_trips_openai_controller_profile() -> None:
    spec = load_optimization_spec("scenarios/optimization/s1_typical_llm.yaml")

    assert spec.operator_control is not None
    params = spec.operator_control["controller_parameters"]
    assert params["provider"] == "openai"
    assert params["capability_profile"] == "responses_native"
    assert params["performance_profile"] == "balanced"
    assert params["model"] == "gpt-5.4"
    assert params["api_key_env_var"] == "OPENAI_API_KEY"
    assert params["max_output_tokens"] == 1024
    assert params["reasoning"] == {"effort": "medium"}


def test_resolve_algorithm_config_merges_global_defaults_profile_and_inline_overrides(tmp_path: Path) -> None:
    profile_path = tmp_path / "nsga2_profile.yaml"
    profile_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0",
                "profile_meta": {
                    "profile_id": "s1_typical_nsga2_raw_profile_override",
                    "description": "Test profile for algorithm parameter resolution.",
                },
                "family": "genetic",
                "backbone": "nsga2",
                "mode": "raw",
                "parameters": {
                    "crossover": {"eta": 11},
                    "mutation": {"eta": 17},
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    payload = _spec_payload()
    payload["algorithm"]["profile_path"] = str(profile_path)
    payload["algorithm"]["parameters"] = {"mutation": {"eta": 23}}
    spec = OptimizationSpec.from_dict(payload)

    resolved = resolve_algorithm_config(None, spec)

    assert resolved["parameters"]["crossover"]["operator"] == "sbx"
    assert resolved["parameters"]["crossover"]["eta"] == 11
    assert resolved["parameters"]["crossover"]["prob"] == 0.9
    assert resolved["parameters"]["mutation"]["operator"] == "pm"
    assert resolved["parameters"]["mutation"]["eta"] == 23
