# tests/optimizers/test_compare_runs.py
"""compare-runs builds structured external comparison bundles."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from tests.optimizers.experiment_fixtures import create_mode_root_with_seed_bundles


def _seed_run(run_root: Path, label: str) -> None:
    (run_root / "traces").mkdir(parents=True, exist_ok=True)
    (run_root / "representatives" / "knee-candidate" / "fields").mkdir(parents=True, exist_ok=True)
    (run_root / "traces" / "evaluation_events.jsonl").write_text(
        "\n".join(
            json.dumps(
                {
                    "decision_id": None,
                    "generation": g,
                    "eval_index": g,
                    "individual_id": f"{label}-g{g}",
                    "objectives": {
                        "temperature_max": 320.0 - g,
                        "temperature_gradient_rms": 3.0 - 0.1 * g,
                    },
                    "constraints": {"total_radiator_span": 0.5, "radiator_span_max": 0.8, "violation": 0.0},
                    "status": "ok",
                    "timing": {"cheap_ms": 1.0, "solve_ms": 800.0},
                }
            )
            for g in range(3)
        )
        + "\n",
        encoding="utf-8",
    )
    (run_root / "representatives" / "knee-candidate" / "case.yaml").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "case_meta": {"case_id": f"{label}-case", "scenario_id": "s1_typical"},
                "panel_domain": {"width": 1.0, "height": 0.8},
                "boundary_features": [
                    {"feature_id": "sink-top", "kind": "line_sink", "edge": "top", "start": 0.2, "end": 0.58}
                ],
                "components": [
                    {
                        "component_id": "c01-001",
                        "family_id": "chip",
                        "shape": "rect",
                        "geometry": {"width": 0.18, "height": 0.12},
                        "pose": {"x": 0.22, "y": 0.18, "rotation_deg": 0.0},
                    },
                    {
                        "component_id": "c02-001",
                        "family_id": "chip",
                        "shape": "capsule",
                        "geometry": {"length": 0.24, "radius": 0.035},
                        "pose": {"x": 0.68, "y": 0.46, "rotation_deg": 90.0},
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (run_root / "representatives" / "knee-candidate" / "evaluation.yaml").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "evaluation_meta": {"case_id": f"{label}-case"},
                "feasible": True,
                "metric_values": {
                    "summary.temperature_max": 318.0 if label == "raw" else 316.0,
                    "summary.temperature_gradient_rms": 2.8 if label == "raw" else 2.6,
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    np.savez_compressed(
        run_root / "representatives" / "knee-candidate" / "fields" / "temperature_grid.npz",
        values=np.arange(16, dtype=np.float64).reshape(4, 4),
    )
    np.savez_compressed(
        run_root / "representatives" / "knee-candidate" / "fields" / "gradient_magnitude_grid.npz",
        values=np.linspace(0.0, 3.0, 16, dtype=np.float64).reshape(4, 4),
    )
    (run_root / "optimization_result.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "run_meta": {
                    "run_id": f"{label}-run",
                    "base_case_id": "fixture-case",
                    "optimization_spec_id": f"{label}-spec",
                    "evaluation_spec_id": "fixture-eval",
                    "benchmark_seed": 11,
                    "algorithm_seed": 7,
                },
                "baseline_candidates": [],
                "pareto_front": [],
                "representative_candidates": {},
                "aggregate_metrics": {
                    "num_evaluations": 3,
                    "optimizer_num_evaluations": 3,
                    "feasible_rate": 1.0,
                    "first_feasible_eval": 0,
                    "pareto_size": 3,
                },
                "history": [
                    {
                        "evaluation_index": g,
                        "generation": g,
                        "source": "optimizer",
                        "feasible": True,
                        "decision_vector": {"x": 0.2 + 0.1 * g, "y": 0.3 + 0.1 * g},
                        "objective_values": {
                            "minimize_peak_temperature": 320.0 - g,
                            "minimize_temperature_gradient_rms": 3.0 - 0.1 * g,
                        },
                        "constraint_values": {"radiator_span_budget": 0.0},
                        "evaluation_report": {"evaluation_meta": {"case_id": "fixture-case"}, "feasible": True},
                    }
                    for g in range(3)
                ],
                "provenance": {
                    "benchmark_source": {"seed": 11},
                    "source_case_id": "fixture-case",
                    "source_optimization_spec_id": f"{label}-spec",
                    "source_evaluation_spec_id": "fixture-eval",
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if label == "llm":
        (run_root / "traces" / "llm_request_trace.jsonl").write_text(
            json.dumps(
                {
                    "decision_id": "g000-e0000-d00",
                    "generation_index": 0,
                    "evaluation_index": 0,
                    "model": None,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (run_root / "traces" / "llm_response_trace.jsonl").write_text(
            json.dumps(
                {
                    "decision_id": "g000-e0000-d00",
                    "generation_index": 0,
                    "evaluation_index": 0,
                    "model": "gpt-5.4",
                    "selected_operator_id": "local_refine",
                }
            )
            + "\n",
            encoding="utf-8",
        )


def test_compare_runs_writes_summary_first_visual_bundle(tmp_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")

    from optimizers.compare_runs import compare_runs

    run_a = tmp_path / "0416_2030__raw"
    run_b = tmp_path / "0416_2035__llm"
    _seed_run(run_a, "raw")
    _seed_run(run_b, "llm")

    output = tmp_path / "comparisons" / "0416_2100__raw_vs_llm"
    compare_runs(runs=[run_a, run_b], output=output)

    assert (output / "manifest.json").exists()
    assert (output / "analytics" / "summary_rows.json").exists()
    assert (output / "analytics" / "timeline_rollups.json").exists()
    assert (output / "figures" / "summary_overview.png").exists()
    assert (output / "figures" / "pdf" / "summary_overview.pdf").exists()
    assert (output / "figures" / "final_layout_comparison.png").exists()
    assert (output / "figures" / "temperature_field_comparison.png").exists()
    assert (output / "figures" / "gradient_field_comparison.png").exists()
    assert (output / "figures" / "progress_dashboard.png").exists()
    assert (output / "tables" / "summary_table.csv").exists()
    assert (output / "tables" / "summary_table.tex").exists()
    assert (output / "tables" / "mode_metrics.csv").exists()
    assert (output / "tables" / "pairwise_deltas.csv").exists()
    summary_payload = json.loads((output / "analytics" / "summary_rows.json").read_text(encoding="utf-8"))
    assert summary_payload["rows"][0]["pde_evaluations"] == 3
    assert summary_payload["rows"][0]["first_feasible_pde_eval"] == 1
    llm_row = next(row for row in summary_payload["rows"] if row["mode"] == "llm")
    assert llm_row["model"] == "gpt-5.4"
    assert not (run_a / "comparison").exists()
    assert not (run_b / "comparison").exists()


def test_compare_runs_rejects_non_concrete_mode_root_inputs(tmp_path: Path) -> None:
    from optimizers.compare_runs import compare_runs

    mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="raw", seeds=(11,))
    output_root = tmp_path / "comparisons" / "should-not-exist"

    with pytest.raises(ValueError, match="concrete single-mode run root"):
        compare_runs(
            runs=[mode_root],
            output=output_root,
        )
    assert not output_root.exists()


def test_compare_runs_rejects_output_inside_source_run_root(tmp_path: Path) -> None:
    from optimizers.compare_runs import compare_runs

    run_a = tmp_path / "0416_2030__raw"
    run_b = tmp_path / "0416_2035__llm"
    _seed_run(run_a, "raw")
    _seed_run(run_b, "llm")

    with pytest.raises(ValueError, match="external output"):
        compare_runs(
            runs=[run_a, run_b],
            output=run_a / "comparisons" / "illegal",
        )
