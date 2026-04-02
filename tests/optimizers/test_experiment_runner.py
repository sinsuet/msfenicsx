from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import yaml

import optimizers.experiment_runner as experiment_runner_module
from optimizers.experiment_runner import run_mode_experiment
from optimizers.models import OptimizationResult, OptimizationSpec


def _write_spec_bundle(tmp_path: Path) -> Path:
    template_path = tmp_path / "template.yaml"
    evaluation_path = tmp_path / "evaluation.yaml"
    optimization_path = tmp_path / "optimization.yaml"
    template_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0",
                "template_meta": {"template_id": "s1_typical"},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    evaluation_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0",
                "spec_meta": {"spec_id": "s1_typical_eval"},
                "objectives": [
                    {"objective_id": "minimize_peak_temperature", "sense": "minimize"},
                    {"objective_id": "minimize_temperature_gradient_rms", "sense": "minimize"},
                ],
                "constraints": [
                    {"constraint_id": "radiator_span_budget"},
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    optimization_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0",
                "spec_meta": {"spec_id": "s1-typical-nsga2-raw"},
                "benchmark_source": {"template_path": str(template_path), "seed": 11},
                "design_variables": [
                    {
                        "variable_id": "c01_x",
                        "path": "components[0].pose.x",
                        "lower_bound": 0.1,
                        "upper_bound": 0.9,
                    }
                ],
                "algorithm": {
                    "family": "genetic",
                    "backbone": "nsga2",
                    "mode": "raw",
                    "population_size": 4,
                    "num_generations": 1,
                    "seed": 7,
                },
                "evaluation_protocol": {"evaluation_spec_path": str(evaluation_path)},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return optimization_path


def _fake_result(spec: OptimizationSpec, benchmark_seed: int) -> OptimizationResult:
    case_id = f"s1_typical-case-{benchmark_seed:03d}"
    return OptimizationResult.from_dict(
        {
            "schema_version": spec.schema_version,
            "run_meta": {
                "run_id": f"{spec.spec_meta['spec_id']}-seed-{benchmark_seed}-run",
                "optimization_spec_id": spec.spec_meta["spec_id"],
                "evaluation_spec_id": "s1_typical_eval",
                "base_case_id": case_id,
            },
            "baseline_candidates": [
                {
                    "evaluation_index": 1,
                    "source": "baseline",
                    "feasible": False,
                    "decision_vector": {"c01_x": 0.2},
                    "objective_values": {
                        "minimize_peak_temperature": 302.0,
                        "minimize_temperature_gradient_rms": 11.2,
                    },
                    "constraint_values": {
                        "radiator_span_budget": 0.05,
                    },
                    "evaluation_report": {
                        "evaluation_meta": {"case_id": case_id},
                        "feasible": False,
                    },
                }
            ],
            "pareto_front": [
                {
                    "evaluation_index": 2,
                    "source": "optimizer",
                    "feasible": True,
                    "decision_vector": {"c01_x": 0.4},
                    "objective_values": {
                        "minimize_peak_temperature": 299.0,
                        "minimize_temperature_gradient_rms": 8.4,
                    },
                    "constraint_values": {
                        "radiator_span_budget": 0.0,
                    },
                    "evaluation_report": {
                        "evaluation_meta": {"case_id": case_id},
                        "feasible": True,
                    },
                }
            ],
            "representative_candidates": {},
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
                    "decision_vector": {"c01_x": 0.2},
                    "objective_values": {
                        "minimize_peak_temperature": 302.0,
                        "minimize_temperature_gradient_rms": 11.2,
                    },
                    "constraint_values": {
                        "radiator_span_budget": 0.05,
                    },
                    "evaluation_report": {
                        "evaluation_meta": {"case_id": case_id},
                        "feasible": False,
                    },
                },
                {
                    "evaluation_index": 2,
                    "source": "optimizer",
                    "feasible": True,
                    "decision_vector": {"c01_x": 0.4},
                    "objective_values": {
                        "minimize_peak_temperature": 299.0,
                        "minimize_temperature_gradient_rms": 8.4,
                    },
                    "constraint_values": {
                        "radiator_span_budget": 0.0,
                    },
                    "evaluation_report": {
                        "evaluation_meta": {"case_id": case_id},
                        "feasible": True,
                    },
                },
            ],
            "provenance": {
                "benchmark_source": {"template_path": "template.yaml", "seed": benchmark_seed},
                "source_case_id": case_id,
                "source_optimization_spec_id": spec.spec_meta["spec_id"],
                "source_evaluation_spec_id": "s1_typical_eval",
            },
        }
    )


def test_run_mode_experiment_writes_seed_runs_and_spec_snapshots(tmp_path, monkeypatch) -> None:
    optimization_spec_path = _write_spec_bundle(tmp_path)

    def _fake_generate_benchmark_case(*args, **kwargs):
        del args, kwargs
        return object()

    def _fake_load_spec(path):
        del path
        return {
            "spec_meta": {"spec_id": "s1_typical_eval"},
            "objectives": [
                {"objective_id": "minimize_peak_temperature", "sense": "minimize"},
                {"objective_id": "minimize_temperature_gradient_rms", "sense": "minimize"},
            ],
            "constraints": [
                {"constraint_id": "radiator_span_budget"},
            ],
        }

    def _fake_run_raw_optimization(base_case, optimization_spec, evaluation_spec, *, spec_path=None):
        del base_case, evaluation_spec, spec_path
        benchmark_seed = int(optimization_spec.benchmark_source["seed"])
        return SimpleNamespace(
            result=_fake_result(optimization_spec, benchmark_seed),
            representative_artifacts={},
            generation_summary_rows=[
                {
                    "generation_index": 1,
                    "num_evaluations_so_far": 2,
                    "feasible_fraction": 0.5,
                    "best_total_constraint_violation": 0.0,
                    "best_minimize_peak_temperature": 299.0,
                    "best_minimize_temperature_gradient_rms": 8.4,
                    "pareto_size": 1,
                    "new_feasible_entries": 1,
                    "new_pareto_entries": 1,
                }
            ],
        )

    monkeypatch.setattr(experiment_runner_module, "generate_benchmark_case", _fake_generate_benchmark_case)
    monkeypatch.setattr(experiment_runner_module, "load_spec", _fake_load_spec)
    monkeypatch.setattr(experiment_runner_module, "run_raw_optimization", _fake_run_raw_optimization)

    experiment_root = run_mode_experiment(
        optimization_spec_path=optimization_spec_path,
        benchmark_seeds=[11, 17],
        scenario_runs_root=tmp_path / "scenario_runs",
    )

    assert (experiment_root / "spec_snapshot" / "optimization_spec.yaml").exists()
    assert (experiment_root / "spec_snapshot" / "scenario_template.yaml").exists()
    assert (experiment_root / "spec_snapshot" / "evaluation_spec.yaml").exists()
    assert (experiment_root / "runs" / "seed-11" / "optimization_result.json").exists()
    assert (experiment_root / "runs" / "seed-11" / "evaluation_events.jsonl").exists()
    assert (experiment_root / "runs" / "seed-17" / "optimization_result.json").exists()
    assert (experiment_root / "summaries" / "run_index.json").exists()
    assert (experiment_root / "figures" / "overview.svg").exists()
    assert (experiment_root / "figures" / "overview.json").exists()
    assert (experiment_root / "logs" / "experiment_index.json").exists()

    manifest = json.loads((experiment_root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["mode_id"] == "nsga2_raw"
    assert manifest["scenario_template_id"] == "s1_typical"
