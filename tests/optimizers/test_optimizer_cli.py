import os
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from llm.openai_compatible.client import OpenAICompatibleDecision
from optimizers.cli import build_parser, main
from optimizers.io import save_optimization_spec
from optimizers.models import OptimizationResult
from optimizers.operator_pool.operators import approved_union_operator_ids_for_backbone
from optimizers.operator_pool.trace import ControllerTraceRow, OperatorTraceRow


def _optimization_spec_payload() -> dict:
    return {
        "schema_version": "1.0",
        "spec_meta": {
            "spec_id": "s1-typical-nsga2-benchmark-source",
            "description": "Benchmark-sourced single-case NSGA-II baseline over the first payload position.",
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


def _write_small_union_spec(tmp_path: Path, *, controller: str = "random_uniform") -> Path:
    payload = yaml.safe_load(Path("scenarios/optimization/s1_typical_raw.yaml").read_text(encoding="utf-8"))
    payload["spec_meta"] = {
        "spec_id": f"s1-typical-nsga2-{controller}",
        "description": f"Single-case NSGA-II {controller} test spec.",
    }
    payload["algorithm"]["population_size"] = 4
    payload["algorithm"]["num_generations"] = 2
    payload["algorithm"]["mode"] = "union"
    payload["algorithm"]["profile_path"] = "scenarios/optimization/profiles/s1_typical_union.yaml"
    payload["operator_control"] = {
        "controller": controller,
        "operator_pool": list(approved_union_operator_ids_for_backbone("genetic", "nsga2")),
    }
    if controller == "llm":
        payload["operator_control"]["controller_parameters"] = {
            "provider": "openai",
            "capability_profile": "responses_native",
            "performance_profile": "balanced",
            "model": "gpt-5.4",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 1024,
        }
    spec_path = tmp_path / f"nsga2_union_{controller}.yaml"
    spec_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return spec_path


def _write_small_llm_spec(tmp_path: Path) -> Path:
    return _write_small_union_spec(tmp_path, controller="llm")


def _write_small_raw_spec(tmp_path: Path) -> Path:
    spec_path = tmp_path / "nsga2_raw.yaml"
    save_optimization_spec(_optimization_spec_payload(), spec_path)
    return spec_path


def _write_controller_trace(path: Path, rows: list[ControllerTraceRow]) -> None:
    path.write_text(
        json.dumps([row.to_dict() for row in rows], ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _write_operator_trace(path: Path, rows: list[OperatorTraceRow]) -> None:
    path.write_text(
        json.dumps([row.to_dict() for row in rows], ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=True, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def _write_enriched_diagnostics_artifacts(tmp_path: Path) -> dict[str, Path]:
    controller_trace_path = tmp_path / "controller_trace.json"
    operator_trace_path = tmp_path / "operator_trace.json"
    optimization_result_path = tmp_path / "optimization_result.json"
    request_trace_path = tmp_path / "llm_request_trace.jsonl"
    response_trace_path = tmp_path / "llm_response_trace.jsonl"

    _write_controller_trace(
        controller_trace_path,
        [
            ControllerTraceRow(
                generation_index=4,
                evaluation_index=57 + index,
                family="genetic",
                backbone="nsga2",
                controller_id="llm",
                candidate_operator_ids=(
                    "native_sbx_pm",
                    "local_refine",
                    "slide_sink",
                    "move_hottest_cluster_toward_sink",
                    "spread_hottest_cluster",
                ),
                selected_operator_id=operator_id,
                phase="",
                rationale="",
                metadata={
                    "fallback_used": False,
                    "policy_phase": phase,
                },
            )
            for index, (operator_id, phase) in enumerate(
                (
                    ("move_hottest_cluster_toward_sink", "prefeasible_progress"),
                    ("local_refine", "post_feasible_expand"),
                    ("slide_sink", "post_feasible_expand"),
                    ("move_hottest_cluster_toward_sink", "post_feasible_expand"),
                    ("native_sbx_pm", "post_feasible_preserve"),
                )
            )
        ],
    )
    _write_operator_trace(
        operator_trace_path,
        [
            OperatorTraceRow(
                generation_index=4,
                evaluation_index=57 + index,
                operator_id=operator_id,
                parent_count=2,
                parent_vectors=((0.2, 0.3), (0.4, 0.5)),
                proposal_vector=(0.25 + index * 0.01, 0.35 + index * 0.01),
                metadata={},
            )
            for index, operator_id in enumerate(
                (
                    "move_hottest_cluster_toward_sink",
                    "local_refine",
                    "slide_sink",
                    "move_hottest_cluster_toward_sink",
                    "native_sbx_pm",
                )
            )
        ],
    )
    optimization_result_path.write_text(
        json.dumps(
            {
                "aggregate_metrics": {
                    "num_evaluations": 61,
                    "feasible_rate": 0.5,
                    "first_feasible_eval": 58,
                    "pareto_size": 2,
                },
                "pareto_front": [
                    {
                        "evaluation_index": 58,
                        "feasible": True,
                        "objective_values": {
                            "minimize_peak_temperature": 10.0,
                            "minimize_temperature_gradient_rms": 5.0,
                        },
                        "constraint_values": {"c01_peak_temperature_limit": 0.0},
                    },
                    {
                        "evaluation_index": 59,
                        "feasible": True,
                        "objective_values": {
                            "minimize_peak_temperature": 9.5,
                            "minimize_temperature_gradient_rms": 5.2,
                        },
                        "constraint_values": {"c01_peak_temperature_limit": 0.0},
                    },
                ],
                "history": [
                    {
                        "evaluation_index": 57,
                        "feasible": False,
                        "objective_values": {
                            "minimize_peak_temperature": 10.8,
                            "minimize_temperature_gradient_rms": 4.7,
                        },
                        "constraint_values": {"c01_peak_temperature_limit": 0.4},
                    },
                    {
                        "evaluation_index": 58,
                        "feasible": True,
                        "objective_values": {
                            "minimize_peak_temperature": 10.0,
                            "minimize_temperature_gradient_rms": 5.0,
                        },
                        "constraint_values": {"c01_peak_temperature_limit": 0.0},
                    },
                    {
                        "evaluation_index": 59,
                        "feasible": True,
                        "objective_values": {
                            "minimize_peak_temperature": 9.5,
                            "minimize_temperature_gradient_rms": 5.2,
                        },
                        "constraint_values": {"c01_peak_temperature_limit": 0.0},
                    },
                    {
                        "evaluation_index": 60,
                        "feasible": False,
                        "objective_values": {
                            "minimize_peak_temperature": 9.4,
                            "minimize_temperature_gradient_rms": 4.8,
                        },
                        "constraint_values": {"c01_peak_temperature_limit": 0.3},
                    },
                    {
                        "evaluation_index": 61,
                        "feasible": True,
                        "objective_values": {
                            "minimize_peak_temperature": 9.7,
                            "minimize_temperature_gradient_rms": 5.1,
                        },
                        "constraint_values": {"c01_peak_temperature_limit": 0.0},
                    },
                ],
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_jsonl(
        request_trace_path,
        [
            {
                "evaluation_index": 58,
                "policy_phase": "post_feasible_expand",
                "candidate_operator_ids": ["local_refine", "slide_sink", "spread_hottest_cluster"],
                "user_prompt": json.dumps(
                    {
                        "metadata": {
                            "prompt_panels": {
                                "regime_panel": {"phase": "post_feasible_expand"},
                                "operator_panel": {
                                    "local_refine": {"expand_budget_status": "preferred"},
                                    "slide_sink": {"expand_budget_status": "neutral"},
                                    "spread_hottest_cluster": {"expand_budget_status": "throttled"},
                                },
                            }
                        }
                    },
                    ensure_ascii=True,
                    sort_keys=True,
                ),
            },
            {
                "evaluation_index": 59,
                "policy_phase": "post_feasible_expand",
                "candidate_operator_ids": ["slide_sink", "native_sbx_pm"],
                "user_prompt": json.dumps(
                    {
                        "metadata": {
                            "prompt_panels": {
                                "regime_panel": {"phase": "post_feasible_expand"},
                                "operator_panel": {
                                    "slide_sink": {"expand_budget_status": "preferred"},
                                    "native_sbx_pm": {"expand_budget_status": "preferred"},
                                },
                            }
                        }
                    },
                    ensure_ascii=True,
                    sort_keys=True,
                ),
            },
        ],
    )
    _write_jsonl(
        response_trace_path,
        [
            {"evaluation_index": 58, "selected_operator_id": "local_refine", "elapsed_seconds": 1.2},
            {"evaluation_index": 59, "selected_operator_id": "slide_sink", "elapsed_seconds": 1.4},
        ],
    )
    return {
        "controller_trace": controller_trace_path,
        "operator_trace": operator_trace_path,
        "optimization_result": optimization_result_path,
        "llm_request_trace": request_trace_path,
        "llm_response_trace": response_trace_path,
    }


def _fake_union_run(*, include_llm_sidecars: bool = False) -> SimpleNamespace:
    history = [
        {
            "evaluation_index": 1,
            "source": "baseline",
            "feasible": False,
            "decision_vector": {"c01_x": 0.2, "c01_y": 0.3},
            "objective_values": {
                "minimize_peak_temperature": 320.0,
                "minimize_temperature_gradient_rms": 12.0,
            },
            "constraint_values": {
                "radiator_span_budget": 0.05,
                "c01_peak_temperature_limit": 1.0,
                "c08_peak_temperature_limit": 0.0,
                "panel_temperature_spread_limit": 0.0,
            },
            "evaluation_report": {
                "evaluation_meta": {"case_id": "s1_typical-case-001"},
                "feasible": False,
            },
        },
        {
            "evaluation_index": 2,
            "source": "optimizer",
            "feasible": True,
            "decision_vector": {"c01_x": 0.25, "c01_y": 0.35},
            "objective_values": {
                "minimize_peak_temperature": 300.0,
                "minimize_temperature_gradient_rms": 8.5,
            },
            "constraint_values": {
                "radiator_span_budget": 0.0,
                "c01_peak_temperature_limit": 0.0,
                "c08_peak_temperature_limit": 0.0,
                "panel_temperature_spread_limit": 0.0,
            },
            "evaluation_report": {
                "evaluation_meta": {"case_id": "s1_typical-case-001"},
                "feasible": True,
            },
        },
    ]
    result_payload = {
            "schema_version": "1.0",
            "run_meta": {
                "run_id": "s1-typical-union-run",
                "base_case_id": "s1_typical-case-001",
                "optimization_spec_id": "s1-typical-nsga2-union",
                "evaluation_spec_id": "s1_typical_eval",
                "benchmark_seed": 11,
                "algorithm_seed": 7,
            },
            "baseline_candidates": [history[0]],
            "pareto_front": [history[1]],
            "representative_candidates": {},
            "aggregate_metrics": {
                "num_evaluations": len(history),
                "feasible_rate": 0.5,
                "first_feasible_eval": 2,
                "pareto_size": 1,
            },
            "history": history,
            "provenance": {
                "benchmark_source": {"seed": 11},
                "source_case_id": "s1_typical-case-001",
                "source_optimization_spec_id": "s1-typical-nsga2-union",
                "source_evaluation_spec_id": "s1_typical_eval",
            },
        }
    run = SimpleNamespace(
        result=OptimizationResult.from_dict(result_payload),
        representative_artifacts={},
        controller_trace=[
            ControllerTraceRow(
                generation_index=1,
                evaluation_index=2,
                family="genetic",
                backbone="nsga2",
                controller_id="llm" if include_llm_sidecars else "random_uniform",
                candidate_operator_ids=("native_sbx_pm", "local_refine"),
                selected_operator_id="local_refine",
                metadata={"fallback_used": False},
            )
        ],
        operator_trace=[
            OperatorTraceRow(
                generation_index=1,
                evaluation_index=2,
                operator_id="local_refine",
                parent_count=2,
                parent_vectors=((0.2, 0.3), (0.24, 0.34)),
                proposal_vector=(0.25, 0.35),
                metadata={},
            )
        ],
        generation_summary_rows=[
            {
                "generation_index": 1,
                "num_evaluations_so_far": 2,
                "feasible_fraction": 0.5,
                "best_total_constraint_violation": 0.0,
                "best_minimize_peak_temperature": 300.0,
                "best_minimize_temperature_gradient_rms": 8.5,
                "pareto_size": 1,
                "new_feasible_entries": 1,
                "new_pareto_entries": 1,
            }
        ],
        llm_request_trace=None,
        llm_response_trace=None,
        llm_reflection_trace=None,
        llm_metrics=None,
    )
    if include_llm_sidecars:
        run.llm_request_trace = [{"evaluation_index": 2, "candidate_operator_ids": ["native_sbx_pm", "local_refine"]}]
        run.llm_response_trace = [{"evaluation_index": 2, "selected_operator_id": "local_refine", "elapsed_seconds": 1.2}]
        run.llm_metrics = {"elapsed_seconds_total": 1.2, "elapsed_seconds_avg": 1.2}
    return run


def test_optimizer_cli_optimize_benchmark_writes_result_and_pareto_artifacts(tmp_path: Path) -> None:
    output_root = tmp_path / "optimizer_run"
    spec_path = tmp_path / "optimization_spec.yaml"
    save_optimization_spec(_optimization_spec_payload(), spec_path)

    exit_code = main(
        [
            "optimize-benchmark",
            "--optimization-spec",
            str(spec_path),
            "--output-root",
            str(output_root),
        ]
    )

    assert exit_code == 0
    assert (output_root / "optimization_result.json").exists()
    assert (output_root / "pareto_front.json").exists()
    assert (output_root / "traces" / "evaluation_events.jsonl").exists()
    assert (output_root / "traces" / "generation_summary.jsonl").exists()
    assert (output_root / "manifest.json").exists()
    for directory_name in ("logs", "summaries", "representatives", "traces"):
        assert (output_root / directory_name).is_dir()
    assert not (output_root / "tensors").exists()

    result_payload = json.loads((output_root / "optimization_result.json").read_text(encoding="utf-8"))
    generation_summary_rows = [
        json.loads(line)
        for line in (output_root / "traces" / "generation_summary.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert result_payload["run_meta"]["optimization_spec_id"] == _optimization_spec_payload()["spec_meta"]["spec_id"]
    assert result_payload["run_meta"]["base_case_id"].startswith("s1_typical")
    assert result_payload["provenance"]["source_case_id"] == result_payload["run_meta"]["base_case_id"]
    assert result_payload["history"]
    assert "operator_usage" not in result_payload["aggregate_metrics"]
    assert all("operator_id" not in entry for entry in result_payload["history"])
    assert all("evaluation_report" in entry for entry in result_payload["history"])
    assert all("case_reports" not in entry for entry in result_payload["history"])
    assert generation_summary_rows
    assert "best_minimize_peak_temperature" in generation_summary_rows[0]
    assert "best_minimize_temperature_gradient_rms" in generation_summary_rows[0]
    assert "best_hot_pa_peak" not in generation_summary_rows[0]


def test_optimizer_cli_optimize_benchmark_writes_manifest_backed_representative_bundles(tmp_path: Path) -> None:
    output_root = tmp_path / "optimizer_run"

    exit_code = main(
        [
            "optimize-benchmark",
            "--optimization-spec",
            "scenarios/optimization/s1_typical_raw.yaml",
            "--output-root",
            str(output_root),
        ]
    )

    assert exit_code == 0
    representative_roots = sorted(path for path in (output_root / "representatives").iterdir() if path.is_dir())
    assert representative_roots
    for representative_root in representative_roots:
        manifest_payload = json.loads((representative_root / "manifest.json").read_text(encoding="utf-8"))
        assert (representative_root / "evaluation.yaml").exists()
        assert manifest_payload["case_snapshot"] == "case.yaml"
        assert manifest_payload["solution_snapshot"] == "solution.yaml"
        assert manifest_payload["evaluation_snapshot"] == "evaluation.yaml"
        assert (representative_root / "case.yaml").exists()
        assert (representative_root / "solution.yaml").exists()
        assert (representative_root / "fields" / "temperature_grid.npz").exists()
        assert (representative_root / "fields" / "gradient_magnitude_grid.npz").exists()
        assert (representative_root / "summaries" / "field_view.json").exists()
        assert (representative_root / "pages").is_dir()
        assert not (representative_root / "tensors").exists()
    manifest_payload = json.loads(
        (output_root / "representatives" / "min-peak-temperature" / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest_payload["case_snapshot"] == "case.yaml"
    assert manifest_payload["evaluation_snapshot"] == "evaluation.yaml"
    assert manifest_payload["field_exports"]["field_view"] == "summaries/field_view.json"


def test_optimizer_cli_union_mode_writes_controller_and_operator_trace_sidecars(tmp_path: Path, monkeypatch) -> None:
    import optimizers.cli as cli_module

    output_root = tmp_path / "union_optimizer_run"
    spec_path = _write_small_union_spec(tmp_path)
    monkeypatch.setattr(cli_module, "run_union_optimization", lambda *args, **kwargs: _fake_union_run())

    exit_code = main(
        [
            "optimize-benchmark",
            "--optimization-spec",
            str(spec_path),
            "--output-root",
            str(output_root),
        ]
    )

    assert exit_code == 0
    assert (output_root / "optimization_result.json").exists()
    assert (output_root / "pareto_front.json").exists()
    assert (output_root / "traces" / "evaluation_events.jsonl").exists()
    assert (output_root / "traces" / "generation_summary.jsonl").exists()
    assert (output_root / "controller_trace.json").exists()
    assert (output_root / "operator_trace.json").exists()

    controller_trace = json.loads((output_root / "controller_trace.json").read_text(encoding="utf-8"))
    operator_trace = json.loads((output_root / "operator_trace.json").read_text(encoding="utf-8"))
    manifest_payload = json.loads((output_root / "manifest.json").read_text(encoding="utf-8"))

    assert controller_trace
    assert operator_trace
    assert manifest_payload["snapshots"]["controller_trace"] == "controller_trace.json"
    assert manifest_payload["snapshots"]["operator_trace"] == "operator_trace.json"


def test_optimizer_cli_union_mode_writes_single_case_history_records(tmp_path: Path, monkeypatch) -> None:
    import optimizers.cli as cli_module

    output_root = tmp_path / "single_case_union_optimizer_run"
    spec_path = _write_small_union_spec(tmp_path)
    monkeypatch.setattr(cli_module, "run_union_optimization", lambda *args, **kwargs: _fake_union_run())

    exit_code = main(
        [
            "optimize-benchmark",
            "--optimization-spec",
            str(spec_path),
            "--output-root",
            str(output_root),
        ]
    )

    assert exit_code == 0
    result_payload = json.loads((output_root / "optimization_result.json").read_text(encoding="utf-8"))
    assert result_payload["run_meta"]["base_case_id"].startswith("s1_typical")
    assert all("evaluation_report" in entry for entry in result_payload["history"])


def test_optimizer_cli_llm_union_mode_writes_llm_sidecars(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from llm.openai_compatible.client import OpenAICompatibleClient

    def _fake_request_operator_decision(self, *, system_prompt, user_prompt, candidate_operator_ids, attempt_trace=None):
        del self, system_prompt, user_prompt, attempt_trace
        return OpenAICompatibleDecision(
            selected_operator_id=candidate_operator_ids[1],
            phase="repair",
            rationale="bias toward local operator",
            provider="dashscope-compatible",
            model="glm-5",
            capability_profile="responses_native",
            performance_profile="balanced",
            raw_payload={"selected_operator_id": candidate_operator_ids[1]},
        )

    monkeypatch.setattr(OpenAICompatibleClient, "request_operator_decision", _fake_request_operator_decision)
    import optimizers.cli as cli_module

    spec_path = _write_small_llm_spec(tmp_path)
    output_root = tmp_path / "llm_union_optimizer_run"
    monkeypatch.setattr(cli_module, "run_union_optimization", lambda *args, **kwargs: _fake_union_run(include_llm_sidecars=True))

    exit_code = main(
        [
            "optimize-benchmark",
            "--optimization-spec",
            str(spec_path),
            "--output-root",
            str(output_root),
        ]
    )

    assert exit_code == 0
    assert (output_root / "controller_trace.json").exists()
    assert (output_root / "operator_trace.json").exists()
    assert (output_root / "traces" / "llm_request_trace.jsonl").exists()
    assert (output_root / "traces" / "llm_response_trace.jsonl").exists()
    assert (output_root / "llm_metrics.json").exists()
    assert (output_root / "traces" / "evaluation_events.jsonl").exists()
    assert (output_root / "traces" / "generation_summary.jsonl").exists()

    manifest_payload = json.loads((output_root / "manifest.json").read_text(encoding="utf-8"))
    llm_response_trace = [
        json.loads(line)
        for line in (output_root / "traces" / "llm_response_trace.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    llm_metrics = json.loads((output_root / "llm_metrics.json").read_text(encoding="utf-8"))

    assert manifest_payload["snapshots"]["llm_request_trace"] == "traces/llm_request_trace.jsonl"
    assert manifest_payload["snapshots"]["llm_response_trace"] == "traces/llm_response_trace.jsonl"
    assert manifest_payload["snapshots"]["llm_metrics"] == "llm_metrics.json"
    assert llm_response_trace
    assert "elapsed_seconds" in llm_response_trace[0]
    assert "elapsed_seconds_total" in llm_metrics
    assert "elapsed_seconds_avg" in llm_metrics


def test_optimizer_cli_run_llm_routes_profile_overlay_into_union_execution(tmp_path: Path, monkeypatch) -> None:
    import optimizers.cli as cli_module

    spec_path = _write_small_llm_spec(tmp_path)
    output_root = tmp_path / "run_llm_optimizer_run"
    captured: dict[str, str] = {}

    monkeypatch.setattr(
        cli_module,
        "load_provider_profile_overlay",
        lambda profile, **kwargs: {
            "LLM_API_KEY": "switch-key",
            "LLM_BASE_URL": "https://switch.example/v1",
            "LLM_MODEL": "claude-sonnet-4-6",
        },
        raising=False,
    )

    def _fake_run_union_optimization(*args, **kwargs):
        del args, kwargs
        captured["LLM_API_KEY"] = os.environ["LLM_API_KEY"]
        captured["LLM_BASE_URL"] = os.environ["LLM_BASE_URL"]
        captured["LLM_MODEL"] = os.environ["LLM_MODEL"]
        return _fake_union_run(include_llm_sidecars=True)

    monkeypatch.setattr(cli_module, "run_union_optimization", _fake_run_union_optimization)

    exit_code = main(
        [
            "run-llm",
            "claude",
            "--optimization-spec",
            str(spec_path),
            "--output-root",
            str(output_root),
        ]
    )

    assert exit_code == 0
    assert captured == {
        "LLM_API_KEY": "switch-key",
        "LLM_BASE_URL": "https://switch.example/v1",
        "LLM_MODEL": "claude-sonnet-4-6",
    }


def test_optimizer_cli_run_llm_uses_default_profile_when_omitted(tmp_path: Path, monkeypatch) -> None:
    import optimizers.cli as cli_module

    spec_path = _write_small_llm_spec(tmp_path)
    output_root = tmp_path / "run_llm_default_optimizer_run"
    captured: dict[str, str] = {}

    def _fake_load_provider_profile_overlay(profile, **kwargs):
        del kwargs
        captured["profile"] = profile
        return {
            "LLM_API_KEY": "default-key",
            "LLM_BASE_URL": "https://default.example/v1",
            "LLM_MODEL": "gpt-5.4",
        }

    monkeypatch.setattr(
        cli_module,
        "load_provider_profile_overlay",
        _fake_load_provider_profile_overlay,
        raising=False,
    )
    monkeypatch.setattr(cli_module, "run_union_optimization", lambda *args, **kwargs: _fake_union_run())

    exit_code = main(
        [
            "run-llm",
            "--optimization-spec",
            str(spec_path),
            "--output-root",
            str(output_root),
        ]
    )

    assert exit_code == 0
    assert captured["profile"] == "default"


def test_optimizer_cli_run_llm_rejects_non_llm_specs(tmp_path: Path) -> None:
    spec_path = _write_small_raw_spec(tmp_path)

    with pytest.raises(ValueError, match="operator_control.controller='llm'"):
        main(
            [
                "run-llm",
                "gpt",
                "--optimization-spec",
                str(spec_path),
                "--output-root",
                str(tmp_path / "run_llm_non_llm"),
            ]
        )


def test_optimizer_cli_replay_llm_trace_writes_summary_artifact(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from llm.openai_compatible.client import OpenAICompatibleClient

    def _fake_request_operator_decision(
        self,
        *,
        system_prompt,
        user_prompt,
        candidate_operator_ids,
        attempt_trace=None,
    ):
        del self, system_prompt, user_prompt
        if attempt_trace is not None:
            attempt_trace.append(
                {
                    "attempt_index": 1,
                    "valid": True,
                    "selected_operator_id": candidate_operator_ids[0],
                }
            )
        return OpenAICompatibleDecision(
            selected_operator_id=candidate_operator_ids[0],
            phase="repair",
            rationale="valid replay decision",
            provider="openai-compatible",
            model="Kimi-K2",
            capability_profile="chat_compatible_json",
            performance_profile="balanced",
            raw_payload={"selected_operator_id": candidate_operator_ids[0]},
        )

    monkeypatch.setattr(OpenAICompatibleClient, "request_operator_decision", _fake_request_operator_decision)
    spec_path = _write_small_llm_spec(tmp_path)
    request_trace_path = tmp_path / "llm_request_trace.jsonl"
    request_trace_path.write_text(
        json.dumps(
            {
                "generation_index": 2,
                "evaluation_index": 18,
                "provider": "openai-compatible",
                "model": "Kimi-K2",
                "capability_profile": "chat_compatible_json",
                "performance_profile": "balanced",
                "candidate_operator_ids": ["native_sbx_pm", "local_refine"],
                "system_prompt": "system prompt",
                "user_prompt": "user prompt",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    output_path = tmp_path / "llm_replay_summary.json"

    exit_code = main(
        [
            "replay-llm-trace",
            "--optimization-spec",
            str(spec_path),
            "--request-trace",
            str(request_trace_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    replay_summary = json.loads(output_path.read_text(encoding="utf-8"))
    assert replay_summary["aggregate"]["request_count"] == 1
    assert replay_summary["aggregate"]["success_count"] == 1
    assert replay_summary["aggregate"]["retry_row_count"] == 0
    assert replay_summary["aggregate"]["fallback_equivalent_count"] == 0
    assert replay_summary["rows"][0]["selected_operator_id"] == "native_sbx_pm"


def test_analyze_controller_trace_reports_speculative_family_collapse(tmp_path: Path) -> None:
    diagnostics = __import__("optimizers.operator_pool.diagnostics", fromlist=["analyze_controller_trace"])
    controller_trace_path = tmp_path / "controller_trace.json"
    _write_controller_trace(
        controller_trace_path,
        [
            ControllerTraceRow(
                generation_index=2,
                evaluation_index=18 + index,
                family="genetic",
                backbone="nsga2",
                controller_id="llm",
                candidate_operator_ids=(
                    "native_sbx_pm",
                    "local_refine",
                    "rebalance_layout",
                    "reduce_local_congestion",
                ),
                selected_operator_id=operator_id,
                metadata={
                    "fallback_used": False,
                    "guardrail_policy_phase": "prefeasible_progress",
                },
            )
            for index, operator_id in enumerate(
                (
                    "rebalance_layout",
                    "reduce_local_congestion",
                    "rebalance_layout",
                    "reduce_local_congestion",
                    "rebalance_layout",
                )
            )
        ]
        + [
            ControllerTraceRow(
                generation_index=3,
                evaluation_index=23,
                family="genetic",
                backbone="nsga2",
                controller_id="llm",
                candidate_operator_ids=("native_sbx_pm", "local_refine"),
                selected_operator_id="local_refine",
                metadata={
                    "fallback_used": False,
                    "guardrail_policy_phase": "prefeasible_stagnation",
                    "guardrail_reason_codes": [
                        "prefeasible_speculative_family_collapse",
                        "prefeasible_forced_reset",
                    ],
                    "guardrail_policy_reset_active": True,
                },
            )
        ],
    )

    summary = diagnostics.analyze_controller_trace(controller_trace_path)

    assert summary["prefeasible"]["max_speculative_family_streak"] >= 5
    assert summary["prefeasible"]["forced_reset_count"] == 1
    assert summary["aggregate"]["reason_code_counts"]["prefeasible_speculative_family_collapse"] == 1


def test_analyze_controller_trace_reports_prefeasible_stable_family_monopoly_metrics(tmp_path: Path) -> None:
    diagnostics = __import__("optimizers.operator_pool.diagnostics", fromlist=["analyze_controller_trace"])
    controller_trace_path = tmp_path / "controller_trace.json"
    _write_controller_trace(
        controller_trace_path,
        [
            ControllerTraceRow(
                generation_index=4,
                evaluation_index=41 + index,
                family="genetic",
                backbone="nsga2",
                controller_id="llm",
                candidate_operator_ids=("native_sbx_pm", "global_explore", "local_refine"),
                selected_operator_id=operator_id,
                metadata={
                    "fallback_used": False,
                    "policy_phase": "prefeasible_stagnation",
                    "guardrail_reason_codes": ["prefeasible_forced_reset"],
                    "guardrail_policy_reset_active": True,
                },
            )
            for index, operator_id in enumerate(
                (
                    "native_sbx_pm",
                    "native_sbx_pm",
                    "local_refine",
                    "native_sbx_pm",
                    "local_refine",
                    "local_refine",
                )
            )
        ],
    )

    summary = diagnostics.analyze_controller_trace(controller_trace_path)

    assert summary["prefeasible"]["max_stable_family_monopoly_streak"] >= 1
    assert summary["prefeasible"]["max_stable_role_monopoly_streak"] >= 1
    assert summary["prefeasible"]["reset_window_count"] == 6
    assert "global_explore_share_during_reset" in summary["prefeasible"]
    assert summary["prefeasible"]["native_baseline_share_during_reset"] > 0.0
    assert summary["prefeasible"]["local_refine_share_during_reset"] > 0.0


def test_analyze_controller_trace_reports_near_feasible_conversion_metrics(tmp_path: Path) -> None:
    diagnostics = __import__("optimizers.operator_pool.diagnostics", fromlist=["analyze_controller_trace"])
    controller_trace_path = tmp_path / "controller_trace.json"
    _write_controller_trace(
        controller_trace_path,
        [
            ControllerTraceRow(
                generation_index=4,
                evaluation_index=51 + index,
                family="genetic",
                backbone="nsga2",
                controller_id="llm",
                candidate_operator_ids=("native_sbx_pm", "global_explore", "local_refine"),
                selected_operator_id=operator_id,
                metadata={
                    "fallback_used": False,
                    "policy_phase": "prefeasible_convert",
                    "entry_convert_active": True,
                    "dominant_violation_family": "thermal_limit",
                    "near_feasible_relief": operator_id == "local_refine",
                },
            )
            for index, operator_id in enumerate(
                (
                    "native_sbx_pm",
                    "local_refine",
                    "native_sbx_pm",
                    "global_explore",
                )
            )
        ],
    )

    summary = diagnostics.analyze_controller_trace(controller_trace_path)

    assert "max_dominant_violation_persistence_streak" in summary["prefeasible"]
    assert "near_feasible_relief_count" in summary["prefeasible"]


def test_analyze_controller_trace_prefers_local_policy_phase_over_empty_provider_phase(tmp_path: Path) -> None:
    diagnostics = __import__("optimizers.operator_pool.diagnostics", fromlist=["analyze_controller_trace"])
    controller_trace_path = tmp_path / "controller_trace.json"
    _write_controller_trace(
        controller_trace_path,
        [
            ControllerTraceRow(
                generation_index=4,
                evaluation_index=57 + index,
                family="genetic",
                backbone="nsga2",
                controller_id="llm",
                candidate_operator_ids=("native_sbx_pm", "local_refine", "slide_sink"),
                selected_operator_id=operator_id,
                phase="",
                metadata={
                    "fallback_used": False,
                    "policy_phase": "post_feasible_progress",
                },
            )
            for index, operator_id in enumerate(
                (
                    "native_sbx_pm",
                    "local_refine",
                    "slide_sink",
                )
            )
        ],
    )

    summary = diagnostics.analyze_controller_trace(controller_trace_path)

    assert summary["post_feasible"]["decision_count"] == 3
    assert summary["unknown"]["decision_count"] == 0


def test_analyze_controller_trace_can_use_optimization_result_to_split_pre_and_post_feasible(tmp_path: Path) -> None:
    diagnostics = __import__("optimizers.operator_pool.diagnostics", fromlist=["analyze_controller_trace"])
    paths = _write_enriched_diagnostics_artifacts(tmp_path)

    summary = diagnostics.analyze_controller_trace(
        paths["controller_trace"],
        optimization_result_path=paths["optimization_result"],
    )

    assert summary["aggregate"]["first_feasible_eval"] == 58
    assert summary["aggregate"]["rows_before_first_feasible"] == 1
    assert summary["aggregate"]["rows_after_first_feasible"] == 4
    assert summary["post_feasible"]["decision_count"] == 4


def test_analyze_controller_trace_reports_frontier_and_regression_metrics(tmp_path: Path) -> None:
    diagnostics = __import__("optimizers.operator_pool.diagnostics", fromlist=["analyze_controller_trace"])
    paths = _write_enriched_diagnostics_artifacts(tmp_path)

    summary = diagnostics.analyze_controller_trace(
        paths["controller_trace"],
        optimization_result_path=paths["optimization_result"],
        operator_trace_path=paths["operator_trace"],
    )

    assert summary["post_feasible"]["frontier_add_count"] == 3
    assert summary["post_feasible"]["feasible_regression_count"] == 1
    assert summary["post_feasible"]["feasible_preservation_count"] == 0
    assert summary["post_feasible"]["family_mix"]["local_refine"] == 1


def test_controller_trace_summary_reports_semantic_visibility_rate(tmp_path: Path) -> None:
    diagnostics = __import__("optimizers.operator_pool.diagnostics", fromlist=["analyze_controller_trace"])
    paths = _write_enriched_diagnostics_artifacts(tmp_path)

    summary = diagnostics.analyze_controller_trace(
        paths["controller_trace"],
        optimization_result_path=paths["optimization_result"],
    )

    assert summary["semantic_visibility_rate"] > 0.0
    assert summary["semantic_candidate_count_avg"] >= 1.0
    assert "semantic_frontier_add_count" in summary


def test_controller_trace_summary_reports_stable_vs_semantic_pareto_ownership(tmp_path: Path) -> None:
    diagnostics = __import__("optimizers.operator_pool.diagnostics", fromlist=["analyze_controller_trace"])
    paths = _write_enriched_diagnostics_artifacts(tmp_path)

    summary = diagnostics.analyze_controller_trace(
        paths["controller_trace"],
        optimization_result_path=paths["optimization_result"],
    )

    assert summary["stable_vs_semantic_pareto_ownership"]["semantic"] >= 1


def test_analyze_controller_trace_reports_route_family_entropy_and_expand_mix(tmp_path: Path) -> None:
    diagnostics = __import__("optimizers.operator_pool.diagnostics", fromlist=["analyze_controller_trace"])
    controller_trace_path = tmp_path / "controller_trace.json"
    _write_controller_trace(
        controller_trace_path,
        [
            ControllerTraceRow(
                generation_index=4,
                evaluation_index=71 + index,
                family="genetic",
                backbone="nsga2",
                controller_id="llm",
                candidate_operator_ids=(
                    "spread_hottest_cluster",
                    "smooth_high_gradient_band",
                    "slide_sink",
                    "local_refine",
                ),
                selected_operator_id=operator_id,
                metadata={
                    "fallback_used": False,
                    "policy_phase": phase,
                },
            )
            for index, (operator_id, phase) in enumerate(
                (
                    ("spread_hottest_cluster", "post_feasible_expand"),
                    ("smooth_high_gradient_band", "post_feasible_expand"),
                    ("slide_sink", "post_feasible_expand"),
                    ("local_refine", "post_feasible_preserve"),
                )
            )
        ],
    )

    summary = diagnostics.analyze_controller_trace(controller_trace_path)

    assert summary["route_family_counts"]["stable_local"] == 1
    assert summary["route_family_counts"]["hotspot_spread"] == 1
    assert summary["route_family_counts"]["congestion_relief"] == 1
    assert summary["route_family_counts"]["sink_retarget"] == 1
    assert summary["route_family_entropy"] == pytest.approx(2.0)
    assert summary["expand_route_family_counts"] == {
        "hotspot_spread": 1,
        "congestion_relief": 1,
        "sink_retarget": 1,
    }
    assert summary["expand_route_family_entropy"] == pytest.approx(1.584962500721156)


def test_optimizer_cli_analyze_controller_trace_writes_summary_artifact(tmp_path: Path) -> None:
    controller_trace_path = tmp_path / "controller_trace.json"
    _write_controller_trace(
        controller_trace_path,
        [
            ControllerTraceRow(
                generation_index=4,
                evaluation_index=31,
                family="genetic",
                backbone="nsga2",
                controller_id="llm",
                candidate_operator_ids=("native_sbx_pm", "local_refine", "move_hottest_cluster_toward_sink"),
                selected_operator_id="move_hottest_cluster_toward_sink",
                metadata={
                    "fallback_used": False,
                    "guardrail_policy_phase": "prefeasible_progress",
                },
            ),
            ControllerTraceRow(
                generation_index=4,
                evaluation_index=32,
                family="genetic",
                backbone="nsga2",
                controller_id="llm",
                candidate_operator_ids=("native_sbx_pm", "local_refine"),
                selected_operator_id="native_sbx_pm",
                metadata={
                    "fallback_used": True,
                    "guardrail_policy_phase": "prefeasible_stagnation",
                    "guardrail_reason_codes": ["prefeasible_forced_reset"],
                    "guardrail_policy_reset_active": True,
                },
            ),
        ],
    )
    output_path = tmp_path / "controller_trace_summary.json"

    exit_code = main(
        [
            "analyze-controller-trace",
            "--controller-trace",
            str(controller_trace_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    summary = json.loads(output_path.read_text(encoding="utf-8"))
    assert summary["aggregate"]["decision_count"] == 2
    assert summary["aggregate"]["fallback_count"] == 1
    assert summary["prefeasible"]["forced_reset_count"] == 1


def test_optimizer_cli_run_benchmark_suite_single_mode_writes_run_root(tmp_path: Path) -> None:
    optimization_spec_path = _write_small_raw_spec(tmp_path)
    scenario_runs_root = tmp_path / "scenario_runs"

    exit_code = main(
        [
            "run-benchmark-suite",
            "--optimization-spec",
            str(optimization_spec_path),
            "--mode",
            "raw",
            "--benchmark-seed",
            "11",
            "--scenario-runs-root",
            str(scenario_runs_root),
        ]
    )

    assert exit_code == 0
    run_root = next((scenario_runs_root / "s1_typical").iterdir())
    assert run_root.name.endswith("__raw")
    assert (run_root / "shared").is_dir()
    assert (run_root / "raw").is_dir()
    assert (run_root / "raw" / "manifest.json").exists()
    assert not (run_root / "comparison").exists()


def test_optimizer_cli_run_benchmark_suite_mixed_mode_writes_comparison_root(tmp_path: Path) -> None:
    raw_spec_path = _write_small_raw_spec(tmp_path)
    union_spec_path = _write_small_union_spec(tmp_path, controller="random_uniform")
    scenario_runs_root = tmp_path / "scenario_runs"

    exit_code = main(
        [
            "run-benchmark-suite",
            "--optimization-spec",
            str(raw_spec_path),
            "--optimization-spec",
            str(union_spec_path),
            "--mode",
            "raw",
            "--mode",
            "union",
            "--benchmark-seed",
            "11",
            "--scenario-runs-root",
            str(scenario_runs_root),
        ]
    )

    assert exit_code == 0
    run_root = next((scenario_runs_root / "s1_typical").iterdir())
    assert run_root.name.endswith("__raw_union")
    assert (run_root / "shared").is_dir()
    assert (run_root / "raw").is_dir()
    assert (run_root / "union").is_dir()
    assert (run_root / "comparison").is_dir()


def test_optimizer_cli_run_benchmark_suite_rejects_multiple_benchmark_seeds_for_s1_typical(tmp_path: Path) -> None:
    raw_spec_path = _write_small_raw_spec(tmp_path)
    scenario_runs_root = tmp_path / "scenario_runs"

    with pytest.raises(ValueError, match="s1_typical.*single benchmark_seed"):
        main(
            [
                "run-benchmark-suite",
                "--optimization-spec",
                str(raw_spec_path),
                "--mode",
                "raw",
                "--benchmark-seed",
                "11",
                "--benchmark-seed",
                "17",
                "--scenario-runs-root",
                str(scenario_runs_root),
            ]
        )


def test_optimizer_cli_rejects_non_positive_evaluation_workers() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "run-benchmark-suite",
                "--optimization-spec",
                "spec.yaml",
                "--scenario-runs-root",
                "scenario_runs",
                "--evaluation-workers",
                "0",
            ]
        )


def test_optimizer_cli_optimize_benchmark_forwards_evaluation_workers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import optimizers.cli as cli_module

    output_root = tmp_path / "optimizer_run"
    spec_path = _write_small_raw_spec(tmp_path)
    forwarded: dict[str, object] = {}

    def _fake_run_raw(*args, **kwargs):
        del args
        forwarded.update(kwargs)
        return object()

    monkeypatch.setattr(cli_module, "run_raw_optimization", _fake_run_raw)
    monkeypatch.setattr(cli_module, "write_optimization_artifacts", lambda *args, **kwargs: None)

    exit_code = main(
        [
            "optimize-benchmark",
            "--optimization-spec",
            str(spec_path),
            "--output-root",
            str(output_root),
            "--evaluation-workers",
            "2",
        ]
    )

    assert exit_code == 0
    assert forwarded["evaluation_workers"] == 2


def test_optimizer_cli_run_benchmark_suite_forwards_evaluation_workers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import optimizers.cli as cli_module

    raw_spec_path = _write_small_raw_spec(tmp_path)
    scenario_runs_root = tmp_path / "scenario_runs"
    forwarded: dict[str, object] = {}

    def _fake_run_benchmark_suite(**kwargs):
        forwarded.update(kwargs)
        return scenario_runs_root / "s1_typical" / "fake-run"

    monkeypatch.setattr(cli_module, "run_benchmark_suite", _fake_run_benchmark_suite)

    exit_code = main(
        [
            "run-benchmark-suite",
            "--optimization-spec",
            str(raw_spec_path),
            "--mode",
            "raw",
            "--benchmark-seed",
            "11",
            "--scenario-runs-root",
            str(scenario_runs_root),
            "--evaluation-workers",
            "2",
        ]
    )

    assert exit_code == 0
    assert forwarded["evaluation_workers"] == 2


def test_optimizer_cli_run_benchmark_suite_llm_mode_writes_llm_pages_and_reports(tmp_path: Path, monkeypatch) -> None:
    import optimizers.run_suite as run_suite_module

    llm_spec_path = _write_small_llm_spec(tmp_path)
    scenario_runs_root = tmp_path / "scenario_runs"
    monkeypatch.setattr(
        run_suite_module,
        "run_union_optimization",
        lambda *args, **kwargs: _fake_union_run(include_llm_sidecars=True),
    )

    exit_code = main(
        [
            "run-benchmark-suite",
            "--optimization-spec",
            str(llm_spec_path),
            "--mode",
            "llm",
            "--benchmark-seed",
            "11",
            "--scenario-runs-root",
            str(scenario_runs_root),
        ]
    )

    assert exit_code == 0
    run_root = next((scenario_runs_root / "s1_typical").iterdir())
    assert (run_root / "llm").is_dir()
    assert (run_root / "llm" / "manifest.json").exists()
    assert (run_root / "llm" / "seeds" / "seed-11" / "traces" / "llm_request_trace.jsonl").exists()
    assert (run_root / "llm" / "seeds" / "seed-11" / "traces" / "llm_response_trace.jsonl").exists()


def test_optimizer_cli_does_not_expose_legacy_template_comparison_command() -> None:
    parser = build_parser()
    command_names = set(parser._subparsers._group_actions[0].choices)

    assert "render-template-comparison" not in command_names


def test_optimizer_cli_analyze_controller_trace_accepts_optional_operator_and_request_sidecars(
    tmp_path: Path,
) -> None:
    paths = _write_enriched_diagnostics_artifacts(tmp_path)
    output_path = tmp_path / "controller_trace_summary.json"

    exit_code = main(
        [
            "analyze-controller-trace",
            "--controller-trace",
            str(paths["controller_trace"]),
            "--optimization-result",
            str(paths["optimization_result"]),
            "--operator-trace",
            str(paths["operator_trace"]),
            "--llm-request-trace",
            str(paths["llm_request_trace"]),
            "--llm-response-trace",
            str(paths["llm_response_trace"]),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    summary = json.loads(output_path.read_text(encoding="utf-8"))
    assert summary["llm_trace"]["request_count"] == 2
    assert summary["llm_trace"]["response_count"] == 2
    assert summary["llm_trace"]["expand_budget_status_counts"]["throttled"] == 1


def test_analyze_controller_trace_reports_expand_family_outcomes_and_budget_throttling(tmp_path: Path) -> None:
    diagnostics = __import__("optimizers.operator_pool.diagnostics", fromlist=["analyze_controller_trace"])
    paths = _write_enriched_diagnostics_artifacts(tmp_path)

    summary = diagnostics.analyze_controller_trace(
        paths["controller_trace"],
        optimization_result_path=paths["optimization_result"],
        llm_request_trace_path=paths["llm_request_trace"],
        llm_response_trace_path=paths["llm_response_trace"],
    )

    assert summary["expand_family_outcomes"]["stable_local"]["frontier_add_count"] == 1
    assert summary["expand_family_outcomes"]["sink_retarget"]["frontier_add_count"] == 1
    assert summary["expand_family_outcomes"]["sink_retarget"]["feasible_regression_count"] == 1
    assert summary["llm_trace"]["expand_budget_throttled_route_family_counts"]["hotspot_spread"] == 1
