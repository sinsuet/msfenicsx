import pytest

from core.schema.models import ThermalCase, ThermalSolution
from evaluation.models import MultiCaseEvaluationSpec
from evaluation.multicase_engine import evaluate_operating_cases


def _case(case_id: str, operating_case: str, sink_temperature: float, transfer_coefficient: float, power_by_role: dict[str, float], ambient: float) -> ThermalCase:
    return ThermalCase.from_dict(
        {
            "schema_version": "1.0",
            "case_meta": {"case_id": case_id, "scenario_id": "panel-four-component-hot-cold-benchmark"},
            "coordinate_system": {"plane": "panel_xy"},
            "panel_domain": {"width": 1.0, "height": 0.8},
            "panel_material_ref": "panel_substrate",
            "materials": {
                "panel_substrate": {"conductivity": 205.0, "emissivity": 0.78},
                "electronics_housing": {"conductivity": 160.0, "emissivity": 0.82},
                "battery_insulated_housing": {"conductivity": 45.0, "emissivity": 0.88},
            },
            "components": [
                {
                    "component_id": "processor-001",
                    "role": "processor",
                    "shape": "rect",
                    "pose": {"x": 0.18, "y": 0.2, "rotation_deg": 0.0},
                    "geometry": {"width": 0.16, "height": 0.1},
                    "material_ref": "electronics_housing",
                },
                {
                    "component_id": "rf-power-amp-001",
                    "role": "rf_power_amp",
                    "shape": "rect",
                    "pose": {"x": 0.55, "y": 0.24, "rotation_deg": 0.0},
                    "geometry": {"width": 0.14, "height": 0.1},
                    "material_ref": "electronics_housing",
                },
                {
                    "component_id": "obc-001",
                    "role": "obc",
                    "shape": "rect",
                    "pose": {"x": 0.3, "y": 0.5, "rotation_deg": 0.0},
                    "geometry": {"width": 0.12, "height": 0.08},
                    "material_ref": "electronics_housing",
                },
                {
                    "component_id": "battery-001",
                    "role": "battery_pack",
                    "shape": "rect",
                    "pose": {"x": 0.72, "y": 0.48, "rotation_deg": 0.0},
                    "geometry": {"width": 0.16, "height": 0.11},
                    "material_ref": "battery_insulated_housing",
                },
            ],
            "boundary_features": [
                {
                    "feature_id": "radiator-top-001",
                    "kind": "line_sink",
                    "edge": "top",
                    "start": 0.25,
                    "end": 0.75,
                    "sink_temperature": sink_temperature,
                    "transfer_coefficient": transfer_coefficient,
                }
            ],
            "loads": [
                {"load_id": "load-processor", "target_component_id": "processor-001", "total_power": power_by_role["processor"]},
                {"load_id": "load-rf", "target_component_id": "rf-power-amp-001", "total_power": power_by_role["rf_power_amp"]},
                {"load_id": "load-obc", "target_component_id": "obc-001", "total_power": power_by_role["obc"]},
                {"load_id": "load-battery", "target_component_id": "battery-001", "total_power": power_by_role["battery_pack"]},
            ],
            "physics": {
                "kind": "steady_heat_radiation",
                "ambient_temperature": ambient,
                "stefan_boltzmann": 5.670374419e-8,
            },
            "mesh_profile": {"nx": 32, "ny": 24},
            "solver_profile": {"nonlinear_solver": "snes"},
            "provenance": {"source": "unit-test", "operating_case": operating_case},
        }
    )


def _solution(case_id: str, summary: dict[str, float], component_summaries: list[dict[str, float | str]]) -> ThermalSolution:
    return ThermalSolution.from_dict(
        {
            "schema_version": "1.0",
            "solution_meta": {"solution_id": f"{case_id}-solution", "case_id": case_id},
            "solver_diagnostics": {"converged": True, "iterations": 8, "solver": "dolfinx_snes"},
            "field_records": {"temperature": {"kind": "cg1_dofs", "num_dofs": 1024}},
            "summary_metrics": summary,
            "component_summaries": component_summaries,
            "provenance": {"solver": "fenicsx"},
        }
    )


def _spec() -> MultiCaseEvaluationSpec:
    return MultiCaseEvaluationSpec.from_dict(
        {
            "schema_version": "1.0",
            "spec_meta": {
                "spec_id": "panel-four-component-hot-cold-baseline",
                "description": "Paper-grade hot/cold multicase evaluation baseline.",
            },
            "operating_cases": [
                {"operating_case_id": "hot", "description": "Hot operating case"},
                {"operating_case_id": "cold", "description": "Cold operating case"},
            ],
            "objectives": [
                {
                    "objective_id": "minimize_hot_pa_peak",
                    "operating_case": "hot",
                    "metric": "component.rf_power_amp.temperature_max",
                    "sense": "minimize",
                },
                {
                    "objective_id": "maximize_cold_battery_min",
                    "operating_case": "cold",
                    "metric": "component.battery_pack.temperature_min",
                    "sense": "maximize",
                },
                {
                    "objective_id": "minimize_radiator_resource",
                    "operating_case": "hot",
                    "metric": "case.total_radiator_span",
                    "sense": "minimize",
                },
            ],
            "constraints": [
                {
                    "constraint_id": "hot_pa_limit",
                    "operating_case": "hot",
                    "metric": "component.rf_power_amp.temperature_max",
                    "relation": "<=",
                    "limit": 355.0,
                },
                {
                    "constraint_id": "hot_processor_limit",
                    "operating_case": "hot",
                    "metric": "component.processor.temperature_max",
                    "relation": "<=",
                    "limit": 350.0,
                },
                {
                    "constraint_id": "cold_battery_floor",
                    "operating_case": "cold",
                    "metric": "component.battery_pack.temperature_min",
                    "relation": ">=",
                    "limit": 268.0,
                },
                {
                    "constraint_id": "hot_component_spread_limit",
                    "operating_case": "hot",
                    "metric": "components.max_temperature_spread",
                    "relation": "<=",
                    "limit": 20.0,
                },
            ],
        }
    )


def test_multicase_report_contains_component_specific_hot_and_cold_metrics() -> None:
    report = evaluate_operating_cases(
        cases={
            "hot": _case(
                "case-hot",
                operating_case="hot",
                sink_temperature=292.0,
                transfer_coefficient=8.0,
                power_by_role={"processor": 24.0, "rf_power_amp": 20.0, "obc": 10.0, "battery_pack": 2.0},
                ambient=300.0,
            ),
            "cold": _case(
                "case-cold",
                operating_case="cold",
                sink_temperature=270.0,
                transfer_coefficient=16.0,
                power_by_role={"processor": 8.0, "rf_power_amp": 6.0, "obc": 4.0, "battery_pack": 0.5},
                ambient=275.0,
            ),
        },
        solutions={
            "hot": _solution(
                "case-hot",
                summary={"temperature_min": 309.0, "temperature_mean": 330.0, "temperature_max": 349.0},
                component_summaries=[
                    {"component_id": "processor-001", "temperature_min": 330.0, "temperature_mean": 341.0, "temperature_max": 348.0},
                    {"component_id": "rf-power-amp-001", "temperature_min": 332.0, "temperature_mean": 344.0, "temperature_max": 349.0},
                    {"component_id": "obc-001", "temperature_min": 320.0, "temperature_mean": 329.0, "temperature_max": 336.0},
                    {"component_id": "battery-001", "temperature_min": 312.0, "temperature_mean": 324.0, "temperature_max": 331.0},
                ],
            ),
            "cold": _solution(
                "case-cold",
                summary={"temperature_min": 270.0, "temperature_mean": 279.0, "temperature_max": 289.0},
                component_summaries=[
                    {"component_id": "processor-001", "temperature_min": 276.0, "temperature_mean": 282.0, "temperature_max": 288.0},
                    {"component_id": "rf-power-amp-001", "temperature_min": 274.0, "temperature_mean": 280.0, "temperature_max": 286.0},
                    {"component_id": "obc-001", "temperature_min": 272.0, "temperature_mean": 278.0, "temperature_max": 284.0},
                    {"component_id": "battery-001", "temperature_min": 270.0, "temperature_mean": 274.0, "temperature_max": 279.0},
                ],
            ),
        },
        spec=_spec(),
    )

    assert report.feasible is True
    assert set(report.case_reports) == {"hot", "cold"}
    assert {item["objective_id"] for item in report.objective_summary} == {
        "minimize_hot_pa_peak",
        "maximize_cold_battery_min",
        "minimize_radiator_resource",
    }
    assert report.case_reports["hot"]["metric_values"]["component.rf_power_amp.temperature_max"] == pytest.approx(349.0)
    assert report.case_reports["cold"]["metric_values"]["component.battery_pack.temperature_min"] == pytest.approx(270.0)
    assert report.case_reports["hot"]["metric_values"]["case.total_radiator_span"] == pytest.approx(0.5)


def test_multicase_constraints_cover_hot_electronics_and_cold_battery() -> None:
    report = evaluate_operating_cases(
        cases={
            "hot": _case(
                "case-hot",
                operating_case="hot",
                sink_temperature=292.0,
                transfer_coefficient=8.0,
                power_by_role={"processor": 24.0, "rf_power_amp": 20.0, "obc": 10.0, "battery_pack": 2.0},
                ambient=300.0,
            ),
            "cold": _case(
                "case-cold",
                operating_case="cold",
                sink_temperature=270.0,
                transfer_coefficient=16.0,
                power_by_role={"processor": 8.0, "rf_power_amp": 6.0, "obc": 4.0, "battery_pack": 0.5},
                ambient=275.0,
            ),
        },
        solutions={
            "hot": _solution(
                "case-hot",
                summary={"temperature_min": 309.0, "temperature_mean": 330.0, "temperature_max": 349.0},
                component_summaries=[
                    {"component_id": "processor-001", "temperature_min": 330.0, "temperature_mean": 341.0, "temperature_max": 348.0},
                    {"component_id": "rf-power-amp-001", "temperature_min": 332.0, "temperature_mean": 344.0, "temperature_max": 349.0},
                    {"component_id": "obc-001", "temperature_min": 320.0, "temperature_mean": 329.0, "temperature_max": 336.0},
                    {"component_id": "battery-001", "temperature_min": 312.0, "temperature_mean": 324.0, "temperature_max": 331.0},
                ],
            ),
            "cold": _solution(
                "case-cold",
                summary={"temperature_min": 270.0, "temperature_mean": 279.0, "temperature_max": 289.0},
                component_summaries=[
                    {"component_id": "processor-001", "temperature_min": 276.0, "temperature_mean": 282.0, "temperature_max": 288.0},
                    {"component_id": "rf-power-amp-001", "temperature_min": 274.0, "temperature_mean": 280.0, "temperature_max": 286.0},
                    {"component_id": "obc-001", "temperature_min": 272.0, "temperature_mean": 278.0, "temperature_max": 284.0},
                    {"component_id": "battery-001", "temperature_min": 270.0, "temperature_mean": 274.0, "temperature_max": 279.0},
                ],
            ),
        },
        spec=_spec(),
    )

    assert {item["constraint_id"] for item in report.constraint_reports} == {
        "hot_pa_limit",
        "hot_processor_limit",
        "cold_battery_floor",
        "hot_component_spread_limit",
    }
    assert report.worst_case_signals["highest_temperature_case_id"] == "hot"
