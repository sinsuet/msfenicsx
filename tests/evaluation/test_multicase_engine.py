import pytest

from core.schema.models import ThermalCase, ThermalSolution
from evaluation.models import MultiCaseEvaluationSpec
from evaluation.multicase_engine import evaluate_operating_cases


def _case(case_id: str, sink_temperature: float, transfer_coefficient: float, total_power: float, ambient: float) -> ThermalCase:
    return ThermalCase.from_dict(
        {
            "schema_version": "1.0",
            "case_meta": {"case_id": case_id, "scenario_id": "panel-baseline"},
            "coordinate_system": {"plane": "panel_xy"},
            "panel_domain": {"width": 1.0, "height": 0.8},
            "materials": {"aluminum": {"conductivity": 205.0, "emissivity": 0.78}},
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
            "boundary_features": [
                {
                    "feature_id": "sink-top",
                    "kind": "line_sink",
                    "edge": "top",
                    "start": 0.2,
                    "end": 0.8,
                    "sink_temperature": sink_temperature,
                    "transfer_coefficient": transfer_coefficient,
                }
            ],
            "loads": [
                {"load_id": "load-001", "target_component_id": "comp-001", "total_power": total_power},
            ],
            "physics": {
                "kind": "steady_heat_radiation",
                "ambient_temperature": ambient,
                "stefan_boltzmann": 5.670374419e-8,
            },
            "mesh_profile": {"nx": 32, "ny": 24},
            "solver_profile": {"nonlinear_solver": "snes"},
            "provenance": {"source": "unit-test"},
        }
    )


def _solution(case_id: str, temperature_min: float, temperature_mean: float, temperature_max: float) -> ThermalSolution:
    return ThermalSolution.from_dict(
        {
            "schema_version": "1.0",
            "solution_meta": {"solution_id": f"{case_id}-solution", "case_id": case_id},
            "solver_diagnostics": {"converged": True, "iterations": 8, "solver": "dolfinx_snes"},
            "field_records": {"temperature": {"kind": "cg1_dofs", "num_dofs": 1024}},
            "summary_metrics": {
                "temperature_min": temperature_min,
                "temperature_mean": temperature_mean,
                "temperature_max": temperature_max,
            },
            "component_summaries": [
                {
                    "component_id": "comp-001",
                    "temperature_min": temperature_mean - 5.0,
                    "temperature_mean": temperature_mean + 2.0,
                    "temperature_max": temperature_max - 1.0,
                },
                {
                    "component_id": "comp-002",
                    "temperature_min": temperature_mean - 8.0,
                    "temperature_mean": temperature_mean - 4.0,
                    "temperature_max": temperature_max - 4.0,
                },
            ],
            "provenance": {"solver": "fenicsx"},
        }
    )


def _spec() -> MultiCaseEvaluationSpec:
    return MultiCaseEvaluationSpec.from_dict(
        {
            "schema_version": "1.0",
            "spec_meta": {
                "spec_id": "panel-hot-cold-multiobjective",
                "description": "Hot/cold multicase evaluation baseline.",
            },
            "operating_cases": [
                {"operating_case_id": "hot", "description": "Hot operating case"},
                {"operating_case_id": "cold", "description": "Cold operating case"},
            ],
            "objectives": [
                {
                    "objective_id": "minimize_hot_peak_temperature",
                    "operating_case": "hot",
                    "metric": "summary.temperature_max",
                    "sense": "minimize",
                },
                {
                    "objective_id": "minimize_cold_radiator_span",
                    "operating_case": "cold",
                    "metric": "case.total_radiator_span",
                    "sense": "minimize",
                },
                {
                    "objective_id": "minimize_hot_component_spread",
                    "operating_case": "hot",
                    "metric": "components.max_temperature_spread",
                    "sense": "minimize",
                },
            ],
            "constraints": [
                {
                    "constraint_id": "hot_peak_limit",
                    "operating_case": "hot",
                    "metric": "summary.temperature_max",
                    "relation": "<=",
                    "limit": 350.0,
                },
                {
                    "constraint_id": "cold_minimum_temperature",
                    "operating_case": "cold",
                    "metric": "summary.temperature_min",
                    "relation": ">=",
                    "limit": 260.0,
                },
            ],
        }
    )


def test_multicase_evaluation_reports_all_operating_cases() -> None:
    report = evaluate_operating_cases(
        cases={
            "hot": _case("case-hot", sink_temperature=295.0, transfer_coefficient=8.0, total_power=22.0, ambient=300.0),
            "cold": _case("case-cold", sink_temperature=270.0, transfer_coefficient=16.0, total_power=8.0, ambient=275.0),
        },
        solutions={
            "hot": _solution("case-hot", temperature_min=294.0, temperature_mean=309.0, temperature_max=327.0),
            "cold": _solution("case-cold", temperature_min=266.0, temperature_mean=272.0, temperature_max=279.0),
        },
        spec=_spec(),
    )

    assert report.feasible is True
    assert set(report.case_reports) == {"hot", "cold"}
    assert len(report.objective_summary) == 3
    assert report.worst_case_signals["highest_temperature_case_id"] == "hot"
    assert report.case_reports["hot"]["metric_values"]["summary.temperature_span"] == pytest.approx(33.0)
    assert report.case_reports["cold"]["metric_values"]["case.total_radiator_span"] == pytest.approx(0.6)

