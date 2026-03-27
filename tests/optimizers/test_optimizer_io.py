from pathlib import Path

from optimizers.io import load_optimization_result, load_optimization_spec, save_optimization_result, save_optimization_spec
from optimizers.models import OptimizationResult, OptimizationSpec


def _spec_payload() -> dict:
    return {
        "schema_version": "1.0",
        "spec_meta": {
            "spec_id": "reference-hot-cold-nsga2",
            "description": "Multicase NSGA-II baseline over payload position.",
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
            "name": "pymoo_nsga2",
            "population_size": 4,
            "num_generations": 1,
            "seed": 7,
        },
        "evaluation_protocol": {
            "evaluation_spec_path": "scenarios/evaluation/panel_hot_cold_multiobjective_baseline.yaml",
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

    assert load_optimization_spec(spec_path).to_dict() == _spec_payload()
    assert load_optimization_result(result_path).to_dict() == _result_payload()
