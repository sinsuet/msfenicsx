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
                "temperature_gradient_rms": 12.5,
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
                    },
                    {
                        "constraint_id": "gradient_rms_limit",
                        "metric": "summary.temperature_gradient_rms",
                        "relation": "<=",
                        "limit": 20.0,
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
    report_payload = yaml.safe_load(report_path.read_text(encoding="utf-8"))
    assert report_payload["metric_values"]["summary.temperature_gradient_rms"] == 12.5
    assert (bundle_root / "evaluation.yaml").exists()
