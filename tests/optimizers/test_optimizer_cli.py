import json
from pathlib import Path

from optimizers.cli import main
from optimizers.io import save_optimization_spec


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
