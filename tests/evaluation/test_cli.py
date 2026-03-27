from pathlib import Path

import yaml

from core.schema.io import save_case, save_solution
from core.schema.models import ThermalCase, ThermalSolution
from evaluation.cli import main


def _case() -> ThermalCase:
    return ThermalCase.from_dict(
        {
            "schema_version": "1.0",
            "case_meta": {"case_id": "case-001", "scenario_id": "panel-four-component-hot-cold-benchmark"},
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
                }
            ],
            "boundary_features": [],
            "loads": [
                {"load_id": "load-processor", "target_component_id": "processor-001", "total_power": 18.0},
                {"load_id": "load-rf", "target_component_id": "rf-power-amp-001", "total_power": 14.0},
                {"load_id": "load-obc", "target_component_id": "obc-001", "total_power": 8.0},
                {"load_id": "load-battery", "target_component_id": "battery-001", "total_power": 1.0},
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
                    "component_id": "processor-001",
                    "temperature_min": 296.0,
                    "temperature_mean": 309.1,
                    "temperature_max": 320.0,
                },
                {
                    "component_id": "rf-power-amp-001",
                    "temperature_min": 298.0,
                    "temperature_mean": 311.0,
                    "temperature_max": 322.0,
                },
                {
                    "component_id": "obc-001",
                    "temperature_min": 292.0,
                    "temperature_mean": 304.0,
                    "temperature_max": 315.0,
                },
                {
                    "component_id": "battery-001",
                    "temperature_min": 289.0,
                    "temperature_mean": 300.0,
                    "temperature_max": 309.0,
                },
            ],
            "provenance": {"solver": "fenicsx"},
        }
    )


def test_evaluation_cli_writes_report_and_bundle_snapshot(tmp_path: Path) -> None:
    case_path = tmp_path / "case.yaml"
    solution_path = tmp_path / "solution.yaml"
    spec_path = tmp_path / "evaluation_spec.yaml"
    report_path = tmp_path / "evaluation_report.yaml"
    bundle_root = tmp_path / "scenario_runs" / "panel-baseline" / "case-001"
    bundle_root.mkdir(parents=True)

    save_case(_case(), case_path)
    save_solution(_solution(), solution_path)
    spec_path.write_text(
        yaml.safe_dump(
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
                        "metric": "component.rf-power-amp-001.temperature_max",
                        "relation": "<=",
                        "limit": 325.0,
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "evaluate-case",
            "--case",
            str(case_path),
            "--solution",
            str(solution_path),
            "--spec",
            str(spec_path),
            "--output",
            str(report_path),
            "--bundle-root",
            str(bundle_root),
        ]
    )

    assert exit_code == 0
    assert report_path.exists()
    assert (bundle_root / "evaluation.yaml").exists()


def test_multicase_evaluation_cli_writes_report(tmp_path: Path) -> None:
    hot_case_path = tmp_path / "hot_case.yaml"
    cold_case_path = tmp_path / "cold_case.yaml"
    hot_solution_path = tmp_path / "hot_solution.yaml"
    cold_solution_path = tmp_path / "cold_solution.yaml"
    spec_path = tmp_path / "multicase_spec.yaml"
    report_path = tmp_path / "multicase_report.yaml"

    hot_case = _case()
    cold_case = ThermalCase.from_dict(
        hot_case.to_dict()
        | {
            "case_meta": {"case_id": "case-002", "scenario_id": "panel-baseline"},
            "loads": [
                {"load_id": "load-processor", "target_component_id": "processor-001", "total_power": 8.0},
                {"load_id": "load-rf", "target_component_id": "rf-power-amp-001", "total_power": 6.0},
                {"load_id": "load-obc", "target_component_id": "obc-001", "total_power": 4.0},
                {"load_id": "load-battery", "target_component_id": "battery-001", "total_power": 0.5},
            ],
            "boundary_features": [
                {
                    "feature_id": "radiator-top-001",
                    "kind": "line_sink",
                    "edge": "top",
                    "start": 0.25,
                    "end": 0.75,
                    "sink_temperature": 270.0,
                    "transfer_coefficient": 16.0,
                }
            ],
            "physics": {
                "kind": "steady_heat_radiation",
                "ambient_temperature": 275.0,
                "stefan_boltzmann": 5.670374419e-8,
            },
        }
    )
    hot_solution = _solution()
    cold_solution = ThermalSolution.from_dict(
        _solution().to_dict()
        | {
            "solution_meta": {"solution_id": "sol-002", "case_id": "case-002"},
            "summary_metrics": {
                "temperature_min": 266.0,
                "temperature_mean": 272.0,
                "temperature_max": 279.0,
            },
            "component_summaries": [
                {
                    "component_id": "processor-001",
                    "temperature_min": 271.0,
                    "temperature_mean": 276.0,
                    "temperature_max": 282.0,
                },
                {
                    "component_id": "rf-power-amp-001",
                    "temperature_min": 272.0,
                    "temperature_mean": 277.0,
                    "temperature_max": 283.0,
                },
                {
                    "component_id": "obc-001",
                    "temperature_min": 269.0,
                    "temperature_mean": 274.0,
                    "temperature_max": 280.0,
                },
                {
                    "component_id": "battery-001",
                    "temperature_min": 267.0,
                    "temperature_mean": 272.5,
                    "temperature_max": 278.0,
                },
            ],
        }
    )

    save_case(hot_case, hot_case_path)
    save_case(cold_case, cold_case_path)
    save_solution(hot_solution, hot_solution_path)
    save_solution(cold_solution, cold_solution_path)
    spec_path.write_text(
        yaml.safe_dump(
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
                ],
                "constraints": [
                    {
                        "constraint_id": "hot_pa_limit",
                        "operating_case": "hot",
                        "metric": "component.rf_power_amp.temperature_max",
                        "relation": "<=",
                        "limit": 355.0,
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "evaluate-operating-cases",
            "--case",
            f"hot={hot_case_path}",
            "--case",
            f"cold={cold_case_path}",
            "--solution",
            f"hot={hot_solution_path}",
            "--solution",
            f"cold={cold_solution_path}",
            "--spec",
            str(spec_path),
            "--output",
            str(report_path),
        ]
    )

    assert exit_code == 0
    report_payload = yaml.safe_load(report_path.read_text(encoding="utf-8"))
    assert set(report_payload["case_reports"]) == {"hot", "cold"}
    assert report_payload["worst_case_signals"]["highest_temperature_case_id"] == "hot"
