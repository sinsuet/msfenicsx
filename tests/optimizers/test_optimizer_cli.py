import json
from pathlib import Path

import yaml

from llm.openai_compatible.client import OpenAICompatibleDecision
from optimizers.cli import main
from optimizers.io import save_optimization_spec
from optimizers.operator_pool.trace import ControllerTraceRow


def _optimization_spec_payload() -> dict:
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


def _union_optimization_spec_path() -> str:
    return "scenarios/optimization/panel_four_component_hot_cold_nsga2_union_uniform_p1.yaml"


def _matrix_union_optimization_spec_path(backbone: str) -> str:
    return f"scenarios/optimization/panel_four_component_hot_cold_{backbone}_union_uniform_p1.yaml"


def _write_small_llm_spec(tmp_path: Path) -> Path:
    payload = yaml.safe_load(
        Path("scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1.yaml").read_text(encoding="utf-8")
    )
    payload["algorithm"]["population_size"] = 4
    payload["algorithm"]["num_generations"] = 2
    payload["operator_control"]["controller_parameters"]["api_key_env_var"] = "TEST_OPENAI_API_KEY"
    spec_path = tmp_path / "nsga2_union_llm_l1.yaml"
    spec_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return spec_path


def _write_controller_trace(path: Path, rows: list[ControllerTraceRow]) -> None:
    path.write_text(
        json.dumps([row.to_dict() for row in rows], ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


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
    assert (output_root / "manifest.json").exists()
    for directory_name in ("logs", "fields", "tensors", "figures", "representatives"):
        assert (output_root / directory_name).is_dir()

    result_payload = json.loads((output_root / "optimization_result.json").read_text(encoding="utf-8"))
    assert result_payload["run_meta"]["optimization_spec_id"] == _optimization_spec_payload()["spec_meta"]["spec_id"]
    assert set(result_payload["run_meta"]["base_case_ids"]) == {"hot", "cold"}
    assert set(result_payload["provenance"]["source_case_ids"]) == {"hot", "cold"}
    assert result_payload["history"]
    assert "operator_usage" not in result_payload["aggregate_metrics"]
    assert all("operator_id" not in entry for entry in result_payload["history"])


def test_optimizer_cli_optimize_benchmark_writes_manifest_backed_representative_bundles(tmp_path: Path) -> None:
    output_root = tmp_path / "optimizer_run"

    exit_code = main(
        [
            "optimize-benchmark",
            "--optimization-spec",
            "scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml",
            "--output-root",
            str(output_root),
        ]
    )

    assert exit_code == 0
    representative_roots = sorted(path for path in (output_root / "representatives").iterdir() if path.is_dir())
    assert representative_roots
    for representative_root in representative_roots:
        assert (representative_root / "manifest.json").exists()
        assert (representative_root / "evaluation.yaml").exists()
        assert (representative_root / "cases" / "hot.yaml").exists()
        assert (representative_root / "cases" / "cold.yaml").exists()
        assert (representative_root / "solutions" / "hot.yaml").exists()
        assert (representative_root / "solutions" / "cold.yaml").exists()


def test_optimizer_cli_union_mode_writes_controller_and_operator_trace_sidecars(tmp_path: Path) -> None:
    output_root = tmp_path / "union_optimizer_run"

    exit_code = main(
        [
            "optimize-benchmark",
            "--optimization-spec",
            _union_optimization_spec_path(),
            "--output-root",
            str(output_root),
        ]
    )

    assert exit_code == 0
    assert (output_root / "optimization_result.json").exists()
    assert (output_root / "pareto_front.json").exists()
    assert (output_root / "controller_trace.json").exists()
    assert (output_root / "operator_trace.json").exists()

    controller_trace = json.loads((output_root / "controller_trace.json").read_text(encoding="utf-8"))
    operator_trace = json.loads((output_root / "operator_trace.json").read_text(encoding="utf-8"))
    manifest_payload = json.loads((output_root / "manifest.json").read_text(encoding="utf-8"))

    assert controller_trace
    assert operator_trace
    assert manifest_payload["snapshots"]["controller_trace"] == "controller_trace.json"
    assert manifest_payload["snapshots"]["operator_trace"] == "operator_trace.json"


def test_optimizer_cli_union_mode_dispatches_moead_and_cmopso_specs(tmp_path: Path) -> None:
    for backbone in ("moead", "cmopso"):
        output_root = tmp_path / f"{backbone}_union_optimizer_run"
        exit_code = main(
            [
                "optimize-benchmark",
                "--optimization-spec",
                _matrix_union_optimization_spec_path(backbone),
                "--output-root",
                str(output_root),
            ]
        )

        assert exit_code == 0
        assert (output_root / "controller_trace.json").exists()
        assert (output_root / "operator_trace.json").exists()


def test_optimizer_cli_llm_union_mode_writes_llm_sidecars(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from llm.openai_compatible.client import OpenAICompatibleClient

    def _fake_request_operator_decision(self, *, system_prompt, user_prompt, candidate_operator_ids):
        del self, system_prompt, user_prompt
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
    spec_path = _write_small_llm_spec(tmp_path)
    output_root = tmp_path / "llm_union_optimizer_run"

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
    assert (output_root / "llm_request_trace.jsonl").exists()
    assert (output_root / "llm_response_trace.jsonl").exists()
    assert (output_root / "llm_metrics.json").exists()

    manifest_payload = json.loads((output_root / "manifest.json").read_text(encoding="utf-8"))
    llm_response_trace = [
        json.loads(line)
        for line in (output_root / "llm_response_trace.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    llm_metrics = json.loads((output_root / "llm_metrics.json").read_text(encoding="utf-8"))

    assert manifest_payload["snapshots"]["llm_request_trace"] == "llm_request_trace.jsonl"
    assert manifest_payload["snapshots"]["llm_response_trace"] == "llm_response_trace.jsonl"
    assert manifest_payload["snapshots"]["llm_metrics"] == "llm_metrics.json"
    assert llm_response_trace
    assert "elapsed_seconds" in llm_response_trace[0]
    assert "elapsed_seconds_total" in llm_metrics
    assert "elapsed_seconds_avg" in llm_metrics


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
                    "battery_to_warm_zone",
                    "hot_pair_separate",
                ),
                selected_operator_id=operator_id,
                metadata={
                    "fallback_used": False,
                    "guardrail_policy_phase": "prefeasible_progress",
                },
            )
            for index, operator_id in enumerate(
                (
                    "battery_to_warm_zone",
                    "hot_pair_separate",
                    "battery_to_warm_zone",
                    "hot_pair_separate",
                    "battery_to_warm_zone",
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
                candidate_operator_ids=("native_sbx_pm", "local_refine", "radiator_expand"),
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
                    "radiator_expand",
                )
            )
        ],
    )

    summary = diagnostics.analyze_controller_trace(controller_trace_path)

    assert summary["post_feasible"]["decision_count"] == 3
    assert summary["unknown"]["decision_count"] == 0


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
                candidate_operator_ids=("native_sbx_pm", "local_refine", "hot_pair_to_sink"),
                selected_operator_id="hot_pair_to_sink",
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
