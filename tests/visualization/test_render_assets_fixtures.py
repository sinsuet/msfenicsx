"""End-to-end: synthetic bundle -> render-assets -> assert full output set."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest
import yaml


def _seed_run_bundle(run_root: Path) -> None:
    from core.generator.pipeline import generate_case
    from optimizers.codec import extract_decision_vector
    from optimizers.io import load_optimization_spec
    from optimizers.artifacts import write_representative_bundle

    traces = run_root / "traces"
    traces.mkdir(parents=True, exist_ok=True)

    optimization_spec_path = "scenarios/optimization/s1_typical_llm.yaml"
    optimization_spec = load_optimization_spec(optimization_spec_path)
    case = generate_case("scenarios/templates/s1_typical.yaml", seed=11)
    baseline_vector = extract_decision_vector(case, optimization_spec)
    improved_vector = baseline_vector.copy()
    improved_vector[0] = min(float(improved_vector[0]) + 0.03, float(optimization_spec.design_variables[0]["upper_bound"]))
    improved_vector[1] = min(float(improved_vector[1]) + 0.02, float(optimization_spec.design_variables[1]["upper_bound"]))
    improved_vector[2] = max(float(improved_vector[2]) - 0.02, float(optimization_spec.design_variables[2]["lower_bound"]))
    improved_vector[3] = min(float(improved_vector[3]) + 0.01, float(optimization_spec.design_variables[3]["upper_bound"]))

    variable_ids = [str(item["variable_id"]) for item in optimization_spec.design_variables]

    (traces / "evaluation_events.jsonl").write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {
                    "decision_id": "g001-e0000-d00",
                    "generation": 1,
                    "eval_index": 0,
                    "individual_id": "g001-i00",
                    "objectives": {"temperature_max": 320.0, "temperature_gradient_rms": 13.0},
                    "constraints": {"radiator_span_budget": 0.2},
                    "status": "failed",
                    "solver_skipped": True,
                    "timing": {"cheap_ms": 1.0, "solve_ms": 800.0},
                },
                {
                    "decision_id": "g002-e0001-d00",
                    "generation": 2,
                    "eval_index": 1,
                    "individual_id": "g002-i00",
                    "objectives": {"temperature_max": 309.0, "temperature_gradient_rms": 9.1},
                    "constraints": {"radiator_span_budget": 0.0},
                    "status": "ok",
                    "solver_skipped": False,
                    "timing": {"cheap_ms": 1.0, "solve_ms": 810.0},
                },
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (traces / "operator_trace.jsonl").write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {
                    "decision_id": "g001-e0000-d00",
                    "generation": 1,
                    "operator_name": "local_refine",
                    "parents": ["baseline"],
                    "offspring": ["g001-i00"],
                    "params_digest": "a" * 40,
                    "wall_ms": 1.2,
                },
                {
                    "decision_id": "g002-e0001-d00",
                    "generation": 2,
                    "operator_name": "slide_sink",
                    "parents": ["g001-i00"],
                    "offspring": ["g002-i00"],
                    "params_digest": "b" * 40,
                    "wall_ms": 1.5,
                },
                {
                    "decision_id": None,
                    "generation": 0,
                    "operator_name": "orphaned_native",
                    "parents": ["baseline"],
                    "offspring": ["orphaned"],
                    "params_digest": "c" * 40,
                    "wall_ms": 0.7,
                },
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (traces / "controller_trace.jsonl").write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {
                    "decision_id": "g001-e0000-d00",
                    "phase": "prefeasible_progress",
                    "operator_selected": "local_refine",
                },
                {
                    "decision_id": "g002-e0001-d00",
                    "phase": "post_feasible_expand",
                    "operator_selected": "slide_sink",
                },
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (traces / "llm_request_trace.jsonl").write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {
                    "decision_id": "g001-e0000-d00",
                    "generation_index": 1,
                    "evaluation_index": 0,
                    "model": None,
                    "candidate_operator_ids": ["native_sbx_pm", "local_refine"],
                },
                {
                    "decision_id": "g002-e0001-d00",
                    "generation_index": 2,
                    "evaluation_index": 1,
                    "model": None,
                    "candidate_operator_ids": ["slide_sink", "local_refine"],
                },
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (traces / "llm_response_trace.jsonl").write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {
                    "decision_id": "g001-e0000-d00",
                    "generation_index": 1,
                    "evaluation_index": 0,
                    "model": "gpt-5.4",
                    "selected_operator_id": "local_refine",
                    "tokens": {"total": 300},
                    "latency_ms": 800.0,
                },
                {
                    "decision_id": "g002-e0001-d00",
                    "generation_index": 2,
                    "evaluation_index": 1,
                    "model": "gpt-5.4",
                    "selected_operator_id": "slide_sink",
                    "tokens": {"total": 280},
                    "latency_ms": 760.0,
                },
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    optimization_result = {
        "schema_version": "1.0",
        "run_meta": {
            "run_id": "fixture-llm-run",
            "base_case_id": case.case_meta["case_id"],
            "optimization_spec_id": "s1_typical_nsga2_llm",
            "evaluation_spec_id": "s1_typical_eval",
            "benchmark_seed": 11,
            "algorithm_seed": 7,
        },
        "baseline_candidates": [],
        "pareto_front": [
            {
                "evaluation_index": 2,
                "generation": 2,
                "source": "optimizer",
                "feasible": True,
                "decision_vector": {key: float(value) for key, value in zip(variable_ids, improved_vector.tolist(), strict=True)},
                "objective_values": {
                    "minimize_peak_temperature": 309.0,
                    "minimize_temperature_gradient_rms": 9.1,
                },
                "constraint_values": {"radiator_span_budget": 0.0},
                "evaluation_report": {"evaluation_meta": {"case_id": case.case_meta["case_id"]}, "feasible": True},
            }
        ],
        "representative_candidates": {},
                "aggregate_metrics": {
            "num_evaluations": 4,
            "optimizer_num_evaluations": 3,
            "feasible_rate": 1.0 / 3.0,
            "first_feasible_eval": 3,
            "pareto_size": 1,
        },
        "history": [
            {
                "evaluation_index": 0,
                "generation": 0,
                "source": "baseline",
                "feasible": False,
                "decision_vector": {key: float(value) for key, value in zip(variable_ids, baseline_vector.tolist(), strict=True)},
                "objective_values": {
                    "minimize_peak_temperature": 326.0,
                    "minimize_temperature_gradient_rms": 13.4,
                },
                "constraint_values": {"radiator_span_budget": 0.3},
                "evaluation_report": {"evaluation_meta": {"case_id": case.case_meta["case_id"]}, "feasible": False},
            },
            {
                "evaluation_index": 1,
                "generation": 1,
                "source": "optimizer",
                "feasible": False,
                "solver_skipped": True,
                "decision_vector": {key: float(value) for key, value in zip(variable_ids, baseline_vector.tolist(), strict=True)},
                "objective_values": {
                    "minimize_peak_temperature": 1.0e12,
                    "minimize_temperature_gradient_rms": 1.0e12,
                },
                "constraint_values": {"radiator_span_budget": 0.2},
                "failure_reason": "cheap_constraint_violation",
                "evaluation_report": {"evaluation_meta": {"case_id": case.case_meta["case_id"]}, "feasible": False},
            },
            {
                "evaluation_index": 2,
                "generation": 2,
                "source": "optimizer",
                "solver_skipped": False,
                "feasible": False,
                "decision_vector": {key: float(value) for key, value in zip(variable_ids, baseline_vector.tolist(), strict=True)},
                "objective_values": {
                    "minimize_peak_temperature": 320.0,
                    "minimize_temperature_gradient_rms": 13.0,
                },
                "constraint_values": {"radiator_span_budget": 0.2},
                "evaluation_report": {"evaluation_meta": {"case_id": case.case_meta["case_id"]}, "feasible": False},
            },
            {
                "evaluation_index": 3,
                "generation": 2,
                "source": "optimizer",
                "feasible": True,
                "solver_skipped": False,
                "decision_vector": {key: float(value) for key, value in zip(variable_ids, improved_vector.tolist(), strict=True)},
                "objective_values": {
                    "minimize_peak_temperature": 309.0,
                    "minimize_temperature_gradient_rms": 9.1,
                },
                "constraint_values": {"radiator_span_budget": 0.0},
                "evaluation_report": {"evaluation_meta": {"case_id": case.case_meta["case_id"]}, "feasible": True},
            },
        ],
        "provenance": {
            "benchmark_source": {"seed": 11},
            "source_case_id": case.case_meta["case_id"],
            "source_optimization_spec_id": "s1_typical_nsga2_llm",
            "source_evaluation_spec_id": "s1_typical_eval",
        },
    }
    (run_root / "optimization_result.json").write_text(
        json.dumps(optimization_result, indent=2) + "\n",
        encoding="utf-8",
    )
    (run_root / "run.yaml").write_text(
        yaml.safe_dump(
            {
                "mode": "llm",
                "seeds": {"benchmark": 11, "algorithm": 7},
                "specs": {
                    "optimization": optimization_spec_path,
                    "evaluation": "scenarios/evaluation/s1_typical_eval.yaml",
                },
                "algorithm": {"population_size": 10, "num_generations": 5},
                "timing": {"wall_seconds": 1.0},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    write_representative_bundle(
        run_root / "representatives" / "knee",
        case_yaml=yaml.safe_dump(case.to_dict(), sort_keys=False),
        solution_yaml="{}",
        evaluation_yaml=yaml.safe_dump(
            {
                "metric_values": {
                    "component.c01-001.temperature_max": 305.0,
                    "summary.temperature_max": 309.0,
                    "summary.temperature_gradient_rms": 9.1,
                }
            },
            sort_keys=False,
        ),
        temperature_grid=np.arange(16, dtype=np.float64).reshape(4, 4) + 300.0,
        gradient_grid=np.linspace(0.0, 3.0, 16, dtype=np.float64).reshape(4, 4),
    )


def test_render_assets_produces_full_mainline_outputs(tmp_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")

    from optimizers.render_assets import _layout_panel_metadata, render_run_assets

    run_root = tmp_path / "0416_2030__llm"
    _seed_run_bundle(run_root)

    render_run_assets(run_root, hires=False)

    required = [
        "analytics/hypervolume.csv",
        "analytics/operator_phase_heatmap.csv",
        "analytics/decision_outcomes.csv",
        "analytics/progress_timeline.csv",
        "analytics/pareto_front.csv",
        "figures/pareto_front.png",
        "figures/pdf/pareto_front.pdf",
        "figures/hypervolume_progress.png",
        "figures/pdf/hypervolume_progress.pdf",
        "figures/operator_phase_heatmap.png",
        "figures/objective_progress.png",
        "figures/temperature_trace.png",
        "figures/pdf/temperature_trace.pdf",
        "figures/gradient_trace.png",
        "figures/pdf/gradient_trace.pdf",
        "figures/constraint_violation_progress.png",
        "figures/pdf/constraint_violation_progress.pdf",
        "figures/temperature_field_knee.png",
        "figures/gradient_field_knee.png",
        "figures/layout_initial.png",
        "figures/layout_final.png",
        "figures/layout_evolution.gif",
        "figures/layout_evolution_frames/step_000.png",
        "summaries/mode_summary.json",
        "summaries/seed_summary.json",
        "summaries/llm_decision_log.jsonl",
        "tables/summary_statistics.csv",
        "tables/summary_statistics.tex",
        "tables/representative_points.csv",
        "tables/representative_points.tex",
    ]
    for relative_path in required:
        assert (run_root / relative_path).exists(), relative_path
    summary_rows = list(csv.DictReader((run_root / "tables" / "summary_statistics.csv").open()))
    assert summary_rows[0]["mode"] == "llm"
    assert summary_rows[0]["pde_evaluations"] == "2"
    assert summary_rows[0]["solver_skipped_evaluations"] == "1"
    assert summary_rows[0]["first_feasible_pde_eval"] == "2"
    representative_rows = list(csv.DictReader((run_root / "tables" / "representative_points.csv").open()))
    assert representative_rows[0]["temperature_max"] == "309.0"
    assert representative_rows[0]["temperature_gradient_rms"] == "9.1"
    assert representative_rows[0]["temperature_figure"] == "figures/temperature_field_knee.png"
    assert representative_rows[0]["gradient_figure"] == "figures/gradient_field_knee.png"
    assert not (run_root / "representatives" / "knee" / "pages").exists()
    assert not (run_root / "representatives" / "knee" / "summaries").exists()
    assert _layout_panel_metadata(run_root)["Model"] == "gpt-5.4"
    decision_rows = [
        json.loads(line)
        for line in (run_root / "summaries" / "llm_decision_log.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert {row["decision_id"] for row in decision_rows} == {"g001-e0000-d00", "g002-e0001-d00"}


def test_build_layout_frames_prefers_best_so_far_spatial_milestones(monkeypatch, tmp_path: Path) -> None:
    from optimizers.render_assets import _build_layout_frames

    run_root = tmp_path / "0416_2030__union"
    optimization_result = {
        "history": [
            {"evaluation_index": 1, "generation": 0, "source": "baseline", "feasible": False},
            {
                "evaluation_index": 2,
                "generation": 0,
                "source": "optimizer",
                "feasible": True,
                "constraint_values": {"radiator_span_budget": 0.0},
                "objective_values": {"minimize_peak_temperature": 330.0, "minimize_temperature_gradient_rms": 18.0},
            },
            {
                "evaluation_index": 3,
                "generation": 1,
                "source": "optimizer",
                "feasible": True,
                "constraint_values": {"radiator_span_budget": 0.0},
                "objective_values": {"minimize_peak_temperature": 325.0, "minimize_temperature_gradient_rms": 16.0},
            },
            {
                "evaluation_index": 4,
                "generation": 2,
                "source": "optimizer",
                "feasible": True,
                "constraint_values": {"radiator_span_budget": 0.0},
                "objective_values": {"minimize_peak_temperature": 324.0, "minimize_temperature_gradient_rms": 15.9},
            },
            {
                "evaluation_index": 5,
                "generation": 3,
                "source": "optimizer",
                "feasible": True,
                "constraint_values": {"radiator_span_budget": 0.0},
                "objective_values": {"minimize_peak_temperature": 323.0, "minimize_temperature_gradient_rms": 15.8},
            },
        ]
    }

    def _component_outline(x0: float, y0: float) -> list[list[float]]:
        return [[x0, y0], [x0 + 0.1, y0], [x0 + 0.1, y0 + 0.1], [x0, y0 + 0.1]]

    frame_payloads = {
        1: {
            "components": [{"component_id": "c01-001", "outline": _component_outline(0.10, 0.10)}],
            "line_sinks": [{"edge": "top", "start_x": 0.20, "end_x": 0.50}],
        },
        2: {
            "components": [{"component_id": "c01-001", "outline": _component_outline(0.12, 0.12)}],
            "line_sinks": [{"edge": "top", "start_x": 0.22, "end_x": 0.52}],
        },
        3: {
            "components": [{"component_id": "c01-001", "outline": _component_outline(0.42, 0.42)}],
            "line_sinks": [{"edge": "top", "start_x": 0.22, "end_x": 0.52}],
        },
        4: {
            "components": [{"component_id": "c01-001", "outline": _component_outline(0.42, 0.42)}],
            "line_sinks": [{"edge": "top", "start_x": 0.30, "end_x": 0.60}],
        },
        5: {
            "components": [{"component_id": "c01-001", "outline": _component_outline(0.42, 0.42)}],
            "line_sinks": [{"edge": "top", "start_x": 0.31, "end_x": 0.61}],
        },
    }

    monkeypatch.setattr("optimizers.render_assets._load_seed_base_case", lambda _: object())
    monkeypatch.setattr("optimizers.render_assets._load_seed_optimization_spec", lambda _: object())
    monkeypatch.setattr("optimizers.render_assets._layout_panel_metadata", lambda _: {"Scenario": "fixture"})

    def _fake_layout_frame(_base_case, _spec, record, *, generation, title, default_legality_policy_id=""):
        evaluation_index = int(record.get("evaluation_index", 1))
        payload = dict(frame_payloads[evaluation_index])
        payload.update(
            {
                "generation": generation,
                "title": title,
                "panel_width": 1.0,
                "panel_height": 0.8,
                "record_evaluation_index": evaluation_index,
            }
        )
        return payload

    monkeypatch.setattr("optimizers.render_assets._layout_frame_from_record", _fake_layout_frame)

    frames = _build_layout_frames(run_root, optimization_result)

    assert [frame["record_evaluation_index"] for frame in frames] == [1, 2, 3, 5]
    assert [frame["frame_index"] for frame in frames] == [0, 1, 2, 3]
    assert "first feasible" in frames[1]["title"].lower()
    assert frames[-1]["title"] == "final layout"


def test_layout_frames_use_repaired_geometry_for_optimizer_records(monkeypatch) -> None:
    from core.generator.pipeline import generate_case
    from optimizers.codec import extract_decision_vector
    from optimizers.io import load_optimization_spec
    from optimizers.render_assets import _layout_frame_from_record

    optimization_spec = load_optimization_spec("scenarios/optimization/s1_typical_llm.yaml")
    base_case = generate_case("scenarios/templates/s1_typical.yaml", seed=11)
    decision_vector = extract_decision_vector(base_case, optimization_spec)
    record = {
        "source": "optimizer",
        "decision_vector": {
            variable["variable_id"]: float(value)
            for variable, value in zip(optimization_spec.design_variables, decision_vector.tolist(), strict=True)
        },
    }
    repair_calls = {"count": 0}

    def _fake_repair(*args, **kwargs):
        repair_calls["count"] += 1
        return base_case.to_dict()

    monkeypatch.setattr("optimizers.render_assets.repair_case_payload_from_vector", _fake_repair)
    monkeypatch.setattr(
        "optimizers.render_assets.apply_decision_vector",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("fallback should not run when repair succeeds")),
    )

    frame = _layout_frame_from_record(base_case, optimization_spec, record, generation=1, title="generation 1")

    assert frame is not None
    assert repair_calls["count"] == 1


def test_layout_frames_prefer_evaluated_geometry_for_optimizer_records(monkeypatch) -> None:
    from core.generator.pipeline import generate_case
    from optimizers.codec import extract_decision_vector
    from optimizers.io import load_optimization_spec
    from optimizers.render_assets import _layout_frame_from_record

    optimization_spec = load_optimization_spec("scenarios/optimization/s1_typical_raw.yaml")
    base_case = generate_case("scenarios/templates/s1_typical.yaml", seed=11)
    decision_vector = extract_decision_vector(base_case, optimization_spec)
    record = {
        "source": "optimizer",
        "proposal_decision_vector": {
            variable["variable_id"]: float(value)
            for variable, value in zip(optimization_spec.design_variables, decision_vector.tolist(), strict=True)
        },
        "evaluated_decision_vector": {
            variable["variable_id"]: float(value)
            for variable, value in zip(optimization_spec.design_variables, decision_vector.tolist(), strict=True)
        },
        "legality_policy_id": "minimal_canonicalization",
    }

    frame = _layout_frame_from_record(
        base_case,
        optimization_spec,
        record,
        generation=1,
        title="gen 1",
        default_legality_policy_id="minimal_canonicalization",
    )

    assert frame is not None


def test_layout_frames_use_minimal_policy_for_baseline_evaluated_vectors(monkeypatch) -> None:
    from core.generator.pipeline import generate_case
    from optimizers.codec import extract_decision_vector
    from optimizers.io import load_optimization_spec
    from optimizers.render_assets import _layout_frame_from_record

    optimization_spec = load_optimization_spec("scenarios/optimization/s1_typical_raw.yaml")
    base_case = generate_case("scenarios/templates/s1_typical.yaml", seed=11)
    decision_vector = extract_decision_vector(base_case, optimization_spec)
    record = {
        "source": "baseline",
        "evaluated_decision_vector": {
            variable["variable_id"]: float(value)
            for variable, value in zip(optimization_spec.design_variables, decision_vector.tolist(), strict=True)
        },
        "legality_policy_id": "minimal_canonicalization",
    }
    project_calls = {"count": 0}

    def _fake_project(*args, **kwargs):
        project_calls["count"] += 1
        return base_case.to_dict()

    monkeypatch.setattr("optimizers.render_assets.project_case_payload_from_vector", _fake_project)
    monkeypatch.setattr(
        "optimizers.render_assets.repair_case_payload_from_vector",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("minimal replay should not full-repair")),
    )

    frame = _layout_frame_from_record(
        base_case,
        optimization_spec,
        record,
        generation=0,
        title="initial layout",
        default_legality_policy_id="minimal_canonicalization",
    )

    assert frame is not None
    assert project_calls["count"] == 1


def test_layout_frames_prefer_legacy_vector_before_proposal_for_partial_records(monkeypatch) -> None:
    from core.generator.pipeline import generate_case
    from optimizers.codec import extract_decision_vector
    from optimizers.io import load_optimization_spec
    from optimizers.render_assets import _layout_frame_from_record

    optimization_spec = load_optimization_spec("scenarios/optimization/s1_typical_raw.yaml")
    base_case = generate_case("scenarios/templates/s1_typical.yaml", seed=11)
    decision_vector = extract_decision_vector(base_case, optimization_spec)
    variable_ids = [str(variable["variable_id"]) for variable in optimization_spec.design_variables]
    legacy_mapping = {
        variable_id: float(value)
        for variable_id, value in zip(variable_ids, decision_vector.tolist(), strict=True)
    }
    proposal_mapping = dict(legacy_mapping)
    proposal_mapping[variable_ids[0]] = proposal_mapping[variable_ids[0]] + 0.01
    selected_values: list[float] = []
    record = {
        "source": "optimizer",
        "proposal_decision_vector": proposal_mapping,
        "decision_vector": legacy_mapping,
        "legality_policy_id": "minimal_canonicalization",
    }

    def _fake_project(_base_case, _optimization_spec, values, **kwargs):
        selected_values.extend(float(value) for value in values)
        return base_case.to_dict()

    monkeypatch.setattr("optimizers.render_assets.project_case_payload_from_vector", _fake_project)

    frame = _layout_frame_from_record(
        base_case,
        optimization_spec,
        record,
        generation=1,
        title="gen 1",
        default_legality_policy_id="minimal_canonicalization",
    )

    assert frame is not None
    assert selected_values[0] == legacy_mapping[variable_ids[0]]


def test_render_assets_suite_root_refreshes_mode_outputs_without_creating_comparison(tmp_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")

    from optimizers.render_assets import render_assets
    from tests.optimizers.experiment_fixtures import create_mixed_run_root

    run_root = create_mixed_run_root(tmp_path, modes=("raw", "union", "llm"), seeds=(11,))

    render_assets(run_root, hires=False)

    assert (run_root / "raw" / "summaries" / "mode_summary.json").exists()
    assert (run_root / "union" / "summaries" / "mode_summary.json").exists()
    assert (run_root / "llm" / "summaries" / "llm_decision_summary.json").exists()
    assert not (run_root / "comparison").exists()


def test_render_assets_rejects_nested_seed_bundle_layout(tmp_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")

    from optimizers.render_assets import render_assets

    mode_root = tmp_path / "0416_2100__raw" / "raw"
    nested_root = mode_root / "seeds" / "seed-11" / "opt-7"
    (nested_root / "traces").mkdir(parents=True, exist_ok=True)
    (nested_root / "optimization_result.json").write_text("{}", encoding="utf-8")
    (nested_root / "traces" / "evaluation_events.jsonl").write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="nested seed bundle layout"):
        render_assets(mode_root, hires=False)
