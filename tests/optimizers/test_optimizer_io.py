from pathlib import Path

import pytest
import yaml

from optimizers.algorithm_config import resolve_algorithm_config
from optimizers.io import load_optimization_result, load_optimization_spec, save_optimization_result, save_optimization_spec
from optimizers.models import OptimizationResult, OptimizationSpec
from optimizers.validation import OptimizationValidationError


def _spec_payload() -> dict:
    return {
        "schema_version": "1.0",
        "spec_meta": {
            "spec_id": "panel-four-component-hot-cold-nsga2-benchmark-source",
            "description": "Benchmark-sourced multicase NSGA-II baseline over payload position.",
        },
        "benchmark_source": {
            "template_path": "scenarios/templates/panel_four_component_hot_cold_benchmark.yaml",
            "seed": 11,
        },
        "design_variables": [
            {
                "variable_id": "payload_x",
                "path": "components[0].pose.x",
                "lower_bound": 0.08,
                "upper_bound": 0.92,
            },
            {
                "variable_id": "payload_y",
                "path": "components[0].pose.y",
                "lower_bound": 0.045,
                "upper_bound": 0.755,
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
            "evaluation_spec_path": "scenarios/evaluation/panel_four_component_hot_cold_baseline.yaml",
        },
    }


def _result_payload() -> dict:
    return {
        "schema_version": "1.0",
        "run_meta": {
            "run_id": "reference-hot-cold-nsga2-run",
            "base_case_ids": {"hot": "reference-case-hot-001", "cold": "reference-case-cold-001"},
            "optimization_spec_id": "reference-hot-cold-nsga2",
            "evaluation_spec_id": "panel-hot-cold-multiobjective-baseline",
        },
        "baseline_candidates": [
            {
                "evaluation_index": 1,
                "source": "baseline",
                "feasible": True,
                "decision_vector": {"payload_x": 0.3, "payload_y": 0.35},
                "objective_values": {
                    "minimize_hot_peak_temperature": 297.9,
                    "minimize_cold_radiator_span": 0.6,
                },
                "constraint_values": {
                    "hot_peak_limit": -52.1,
                    "cold_minimum_temperature": -10.6,
                },
                "case_reports": {"hot": {"feasible": True}, "cold": {"feasible": True}},
            }
        ],
        "pareto_front": [
            {
                "evaluation_index": 2,
                "source": "optimizer",
                "feasible": True,
                "decision_vector": {"payload_x": 0.3, "payload_y": 0.62},
                "objective_values": {
                    "minimize_hot_peak_temperature": 296.9,
                    "minimize_cold_radiator_span": 0.55,
                },
                "constraint_values": {
                    "hot_peak_limit": -53.1,
                    "cold_minimum_temperature": -10.2,
                },
                "case_reports": {"hot": {"feasible": True}, "cold": {"feasible": True}},
            }
        ],
        "representative_candidates": {
            "min_hot_peak": {
                "evaluation_index": 2,
                "source": "optimizer",
                "feasible": True,
                "decision_vector": {"payload_x": 0.3, "payload_y": 0.62},
                "objective_values": {
                    "minimize_hot_peak_temperature": 296.9,
                    "minimize_cold_radiator_span": 0.55,
                },
                "constraint_values": {
                    "hot_peak_limit": -53.1,
                    "cold_minimum_temperature": -10.2,
                },
                "case_reports": {"hot": {"feasible": True}, "cold": {"feasible": True}},
            }
        },
        "aggregate_metrics": {
            "num_evaluations": 5,
            "feasible_rate": 1.0,
            "first_feasible_eval": 1,
            "pareto_size": 1,
        },
        "history": [
            {
                "evaluation_index": 1,
                "source": "baseline",
                "feasible": True,
                "decision_vector": {"payload_x": 0.3, "payload_y": 0.35},
                "objective_values": {
                    "minimize_hot_peak_temperature": 297.9,
                    "minimize_cold_radiator_span": 0.6,
                },
                "constraint_values": {
                    "hot_peak_limit": -52.1,
                    "cold_minimum_temperature": -10.6,
                },
                "case_reports": {"hot": {"feasible": True}, "cold": {"feasible": True}},
            }
        ],
        "provenance": {
            "source_case_ids": {"hot": "reference-case-hot-001", "cold": "reference-case-cold-001"},
            "source_optimization_spec_id": "reference-hot-cold-nsga2",
            "source_evaluation_spec_id": "panel-hot-cold-multiobjective-baseline",
        },
    }


def test_save_and_load_yaml_round_trip(tmp_path: Path) -> None:
    spec_path = tmp_path / "optimization_spec.yaml"
    result_path = tmp_path / "optimization_result.yaml"

    save_optimization_spec(OptimizationSpec.from_dict(_spec_payload()), spec_path)
    save_optimization_result(OptimizationResult.from_dict(_result_payload()), result_path)

    loaded_spec = load_optimization_spec(spec_path)
    assert loaded_spec.to_dict() == _spec_payload()
    assert loaded_spec.benchmark_source["seed"] == 11
    assert loaded_spec.algorithm["family"] == "genetic"
    assert loaded_spec.algorithm["backbone"] == "nsga2"
    assert loaded_spec.algorithm["mode"] == "raw"
    assert load_optimization_result(result_path).to_dict() == _result_payload()


def test_matrix_spec_uses_family_backbone_mode_contract() -> None:
    spec = load_optimization_spec("scenarios/optimization/panel_four_component_hot_cold_nsga3_raw_b0.yaml")

    assert {key: spec.algorithm[key] for key in ("family", "backbone", "mode")} == {
        "family": "genetic",
        "backbone": "nsga3",
        "mode": "raw",
    }


def test_active_nsga_specs_resolve_benchmark_profiles() -> None:
    nsga2_spec = load_optimization_spec("scenarios/optimization/panel_four_component_hot_cold_nsga2_raw_b0.yaml")
    nsga3_spec = load_optimization_spec("scenarios/optimization/panel_four_component_hot_cold_nsga3_raw_b0.yaml")

    nsga2_algorithm = resolve_algorithm_config(
        "scenarios/optimization/panel_four_component_hot_cold_nsga2_raw_b0.yaml",
        nsga2_spec,
    )
    nsga3_algorithm = resolve_algorithm_config(
        "scenarios/optimization/panel_four_component_hot_cold_nsga3_raw_b0.yaml",
        nsga3_spec,
    )

    assert nsga2_algorithm["parameters"]["crossover"]["eta"] == 10
    assert nsga2_algorithm["parameters"]["mutation"]["eta"] == 15
    assert nsga3_algorithm["parameters"]["crossover"]["eta"] == 10
    assert nsga3_algorithm["parameters"]["mutation"]["eta"] == 15


def test_union_spec_requires_operator_control_block() -> None:
    with open("scenarios/optimization/panel_four_component_hot_cold_nsga2_union_uniform_p1.yaml", "r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)

    payload.pop("operator_control")

    with pytest.raises(OptimizationValidationError):
        OptimizationSpec.from_dict(payload)


def test_union_spec_uses_nsga2_union_mode_contract() -> None:
    spec = load_optimization_spec("scenarios/optimization/panel_four_component_hot_cold_nsga2_union_uniform_p1.yaml")

    assert {key: spec.algorithm[key] for key in ("family", "backbone", "mode")} == {
        "family": "genetic",
        "backbone": "nsga2",
        "mode": "union",
    }


@pytest.mark.parametrize(
    ("spec_name", "family", "backbone", "native_operator_id"),
    [
        ("panel_four_component_hot_cold_nsga2_union_uniform_p1.yaml", "genetic", "nsga2", "native_sbx_pm"),
        ("panel_four_component_hot_cold_nsga3_union_uniform_p1.yaml", "genetic", "nsga3", "native_sbx_pm"),
        ("panel_four_component_hot_cold_ctaea_union_uniform_p1.yaml", "genetic", "ctaea", "native_sbx_pm"),
        ("panel_four_component_hot_cold_rvea_union_uniform_p1.yaml", "genetic", "rvea", "native_sbx_pm"),
        ("panel_four_component_hot_cold_moead_union_uniform_p1.yaml", "decomposition", "moead", "native_moead"),
        ("panel_four_component_hot_cold_cmopso_union_uniform_p1.yaml", "swarm", "cmopso", "native_cmopso"),
    ],
)
def test_union_matrix_specs_load_with_backbone_native_action_contract(
    spec_name: str,
    family: str,
    backbone: str,
    native_operator_id: str,
) -> None:
    spec = load_optimization_spec(Path("scenarios/optimization") / spec_name)

    assert {key: spec.algorithm[key] for key in ("family", "backbone", "mode")} == {
        "family": family,
        "backbone": backbone,
        "mode": "union",
    }
    assert spec.operator_control is not None
    assert spec.operator_control["controller"] == "random_uniform"
    assert spec.operator_control["operator_pool"][0] == native_operator_id


def test_union_spec_requires_native_action_in_registry() -> None:
    payload = load_optimization_spec("scenarios/optimization/panel_four_component_hot_cold_nsga2_union_uniform_p1.yaml").to_dict()
    payload["operator_control"]["operator_pool"] = [
        operator_id
        for operator_id in payload["operator_control"]["operator_pool"]
        if operator_id != "native_sbx_pm"
    ]

    with pytest.raises(OptimizationValidationError):
        OptimizationSpec.from_dict(payload)


def test_union_specs_share_same_benchmark_source() -> None:
    uniform_spec = load_optimization_spec("scenarios/optimization/panel_four_component_hot_cold_nsga2_union_uniform_p1.yaml")
    llm_spec = load_optimization_spec("scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1.yaml")

    assert uniform_spec.benchmark_source == llm_spec.benchmark_source
    assert uniform_spec.operator_control is not None
    assert llm_spec.operator_control is not None
    assert uniform_spec.operator_control["operator_pool"] == llm_spec.operator_control["operator_pool"]
    assert uniform_spec.operator_control["controller"] == "random_uniform"
    assert llm_spec.operator_control["controller"] == "llm"


def test_moead_union_spec_requires_native_moead_action() -> None:
    payload = load_optimization_spec("scenarios/optimization/panel_four_component_hot_cold_moead_union_uniform_p1.yaml").to_dict()
    payload["operator_control"]["operator_pool"] = [
        operator_id
        for operator_id in payload["operator_control"]["operator_pool"]
        if operator_id != "native_moead"
    ]

    with pytest.raises(OptimizationValidationError):
        OptimizationSpec.from_dict(payload)


def test_resolve_algorithm_config_merges_global_defaults_profile_and_inline_overrides(tmp_path: Path) -> None:
    profile_path = tmp_path / "nsga2_profile.yaml"
    profile_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0",
                "profile_meta": {
                    "profile_id": "panel-four-component-hot-cold-nsga2-raw-profile",
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
    spec_payload = _spec_payload()
    spec_payload["algorithm"]["profile_path"] = str(profile_path)
    spec_payload["algorithm"]["parameters"] = {
        "mutation": {"eta": 13},
    }
    spec = OptimizationSpec.from_dict(spec_payload)

    resolved = resolve_algorithm_config(tmp_path / "optimization_spec.yaml", spec)

    assert resolved["family"] == "genetic"
    assert resolved["backbone"] == "nsga2"
    assert resolved["mode"] == "raw"
    assert resolved["parameters"]["crossover"] == {"operator": "sbx", "eta": 11, "prob": 0.9}
    assert resolved["parameters"]["mutation"] == {"operator": "pm", "eta": 13}


def test_resolve_algorithm_config_rejects_mismatched_profile_identity(tmp_path: Path) -> None:
    profile_path = tmp_path / "wrong_profile.yaml"
    profile_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0",
                "profile_meta": {
                    "profile_id": "panel-four-component-hot-cold-nsga3-raw-profile",
                    "description": "Mismatched profile fixture.",
                },
                "family": "genetic",
                "backbone": "nsga3",
                "mode": "raw",
                "parameters": {},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    spec_payload = _spec_payload()
    spec_payload["algorithm"]["profile_path"] = str(profile_path)
    spec = OptimizationSpec.from_dict(spec_payload)

    with pytest.raises(OptimizationValidationError):
        resolve_algorithm_config(tmp_path / "optimization_spec.yaml", spec)
