import pytest

from core.generator.layout_metrics import build_layout_context, measure_case_layout_metrics
from core.schema.models import ThermalCase, ThermalSolution
from evaluation.engine import MetricResolutionError, evaluate_case_solution
from evaluation.models import EvaluationSpec


def _case() -> ThermalCase:
    return ThermalCase.from_dict(
        {
            "schema_version": "1.0",
            "case_meta": {"case_id": "case-001", "scenario_id": "panel-baseline"},
            "coordinate_system": {"plane": "panel_xy"},
            "panel_domain": {"width": 1.0, "height": 0.8},
            "panel_material_ref": "aluminum",
            "materials": {
                "aluminum": {"conductivity": 205.0, "emissivity": 0.78},
            },
            "components": [
                {
                    "component_id": "comp-001",
                    "role": "payload",
                    "shape": "rect",
                    "pose": {"x": 0.3, "y": 0.35, "rotation_deg": 0.0},
                    "geometry": {"width": 0.16, "height": 0.09},
                    "material_ref": "aluminum",
                },
                {
                    "component_id": "comp-002",
                    "role": "payload",
                    "shape": "rect",
                    "pose": {"x": 0.6, "y": 0.35, "rotation_deg": 0.0},
                    "geometry": {"width": 0.12, "height": 0.08},
                    "material_ref": "aluminum",
                },
            ],
            "boundary_features": [],
            "loads": [
                {"load_id": "load-001", "target_component_id": "comp-001", "total_power": 18.0},
                {"load_id": "load-002", "target_component_id": "comp-002", "total_power": 10.0},
            ],
            "physics": {"kind": "steady_heat_radiation"},
            "mesh_profile": {"nx": 32, "ny": 24},
            "solver_profile": {"nonlinear_solver": "snes"},
            "provenance": {"source": "unit-test"},
        }
    )


def _solution() -> ThermalSolution:
    return ThermalSolution.from_dict(
        {
            "schema_version": "1.0",
            "solution_meta": {"solution_id": "sol-001", "case_id": "case-001"},
            "solver_diagnostics": {"converged": True, "iterations": 8, "solver": "dolfinx_snes"},
            "field_records": {"temperature": {"kind": "cg1_dofs", "num_dofs": 1024}},
            "summary_metrics": {
                "temperature_min": 285.1,
                "temperature_mean": 301.2,
                "temperature_max": 322.4,
            },
            "component_summaries": [
                {
                    "component_id": "comp-001",
                    "temperature_min": 296.0,
                    "temperature_mean": 309.1,
                    "temperature_max": 320.0,
                },
                {
                    "component_id": "comp-002",
                    "temperature_min": 292.3,
                    "temperature_mean": 300.2,
                    "temperature_max": 315.4,
                },
            ],
            "provenance": {"solver": "fenicsx"},
        }
    )


def _solution_with_gradient_rms(gradient_rms: float) -> ThermalSolution:
    return ThermalSolution.from_dict(
        _solution().to_dict()
        | {
            "summary_metrics": _solution().summary_metrics | {"temperature_gradient_rms": gradient_rms},
        }
    )


def _spec(limit: float = 325.0, metric: str = "component.comp-001.temperature_max") -> EvaluationSpec:
    return EvaluationSpec.from_dict(
        {
            "schema_version": "1.0",
            "spec_meta": {
                "spec_id": "panel-single-objective",
                "description": "Single-objective thermal evaluation baseline.",
            },
            "objectives": [
                {
                    "objective_id": "minimize_peak_temperature",
                    "metric": "summary.temperature_max",
                    "sense": "minimize",
                }
            ],
            "constraints": [
                {
                    "constraint_id": "payload_peak_limit",
                    "metric": metric,
                    "relation": "<=",
                    "limit": limit,
                },
                {
                    "constraint_id": "solver_iteration_budget",
                    "metric": "solver.iterations",
                    "relation": "<=",
                    "limit": 20.0,
                },
            ],
        }
    )


def _case_with_layout_metrics() -> ThermalCase:
    payload = _case().to_dict()
    payload["provenance"] = {
        **payload["provenance"],
        "layout_metrics": {
            "active_deck_occupancy": 0.401,
            "bbox_fill_ratio": 0.392,
            "nearest_neighbor_gap_mean": 0.011,
        },
    }
    return ThermalCase.from_dict(payload)


def _case_with_stale_layout_metrics_and_context() -> ThermalCase:
    payload = _case().to_dict()
    payload["provenance"] = {
        **payload["provenance"],
        "layout_context": build_layout_context(
            placement_region={"x_min": 0.1, "x_max": 0.9, "y_min": 0.1, "y_max": 0.7},
            active_deck={"x_min": 0.15, "x_max": 0.85, "y_min": 0.12, "y_max": 0.62},
            dense_core={"x_min": 0.22, "x_max": 0.78, "y_min": 0.18, "y_max": 0.56},
        ),
        "layout_metrics": {
            "active_deck_occupancy": 0.999,
            "bbox_fill_ratio": 0.999,
            "nearest_neighbor_gap_mean": 0.999,
            "centroid_dispersion": 0.999,
        },
    }
    return ThermalCase.from_dict(payload)


def test_evaluate_case_solution_reports_feasible_summary() -> None:
    report = evaluate_case_solution(_case(), _solution(), _spec())

    assert report.feasible is True
    assert report.metric_values["summary.temperature_max"] == pytest.approx(322.4)
    assert report.metric_values["case.total_power"] == pytest.approx(28.0)
    assert report.derived_signals["hotspot_component_id"] == "comp-001"
    assert report.derived_signals["power_density"] == pytest.approx(35.0)
    assert report.violations == []


def test_evaluate_case_solution_reports_negative_margin_when_constraint_fails() -> None:
    report = evaluate_case_solution(_case(), _solution(), _spec(limit=319.0))

    assert report.feasible is False
    assert len(report.violations) == 1
    assert report.violations[0]["constraint_id"] == "payload_peak_limit"
    assert report.violations[0]["margin"] == pytest.approx(-1.0)


def test_evaluate_case_solution_rejects_unknown_metric_keys() -> None:
    with pytest.raises(MetricResolutionError):
        evaluate_case_solution(_case(), _solution(), _spec(metric="summary.temperature_median"))


def test_evaluate_case_solution_supports_summary_temperature_gradient_rms() -> None:
    report = evaluate_case_solution(
        _case(),
        _solution_with_gradient_rms(12.5),
        _spec(metric="summary.temperature_gradient_rms"),
    )

    assert report.metric_values["summary.temperature_gradient_rms"] == pytest.approx(12.5)


def test_evaluate_case_solution_surfaces_layout_realism_signals() -> None:
    report = evaluate_case_solution(_case_with_layout_metrics(), _solution(), _spec())

    assert report.derived_signals["layout_active_deck_occupancy"] == pytest.approx(0.401)
    assert report.derived_signals["layout_bbox_fill_ratio"] == pytest.approx(0.392)
    assert report.derived_signals["layout_nearest_neighbor_gap_mean"] == pytest.approx(0.011)


def test_evaluate_case_solution_recomputes_layout_signals_from_candidate_geometry_when_context_is_present() -> None:
    case = _case_with_stale_layout_metrics_and_context()
    case_payload = case.to_dict()
    expected_metrics = measure_case_layout_metrics(
        case_payload,
        layout_context=case_payload["provenance"]["layout_context"],
    )

    assert expected_metrics is not None

    report = evaluate_case_solution(case, _solution(), _spec())

    assert report.derived_signals["layout_active_deck_occupancy"] == pytest.approx(expected_metrics["active_deck_occupancy"])
    assert report.derived_signals["layout_bbox_fill_ratio"] == pytest.approx(expected_metrics["bbox_fill_ratio"])
    assert report.derived_signals["layout_nearest_neighbor_gap_mean"] == pytest.approx(
        expected_metrics["nearest_neighbor_gap_mean"]
    )
    assert report.derived_signals["layout_bbox_fill_ratio"] != pytest.approx(0.999)


def test_evaluate_case_solution_surfaces_ambient_and_heat_source_signals() -> None:
    payload = _case_with_layout_metrics().to_dict()
    payload["physics"] = {
        "kind": "steady_heat_radiation",
        "ambient_temperature": 292.0,
        "background_boundary_cooling": {
            "transfer_coefficient": 0.15,
            "emissivity": 0.08,
        },
    }
    payload["loads"] = [
        {"load_id": f"load-{index}", "target_component_id": f"comp-{index:03d}", "total_power": 4.0}
        for index in range(1, 3)
    ]
    report = evaluate_case_solution(ThermalCase.from_dict(payload), _solution(), _spec())

    assert report.derived_signals["ambient_temperature"] == pytest.approx(292.0)
    assert report.derived_signals["background_boundary_transfer_coefficient"] == pytest.approx(0.15)
    assert report.derived_signals["active_heat_source_count"] == pytest.approx(2.0)
