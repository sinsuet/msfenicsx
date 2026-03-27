from pathlib import Path

import yaml

from core.schema.io import save_case, save_solution
from core.schema.models import ThermalCase, ThermalSolution
from evaluation.cli import main


def _case() -> ThermalCase:
    return ThermalCase.from_dict(
        {
            "schema_version": "1.0",
            "case_meta": {"case_id": "case-001", "scenario_id": "panel-baseline"},
            "coordinate_system": {"plane": "panel_xy"},
            "panel_domain": {"width": 1.0, "height": 0.8},
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
                }
            ],
            "boundary_features": [],
            "loads": [{"load_id": "load-001", "target_component_id": "comp-001", "total_power": 18.0}],
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
                }
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
                        "metric": "component.comp-001.temperature_max",
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
            "loads": [{"load_id": "load-001", "target_component_id": "comp-001", "total_power": 8.0}],
            "boundary_features": [
                {
                    "feature_id": "sink-top",
                    "kind": "line_sink",
                    "edge": "top",
                    "start": 0.2,
                    "end": 0.8,
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
                    "component_id": "comp-001",
                    "temperature_min": 267.0,
                    "temperature_mean": 272.5,
                    "temperature_max": 278.0,
                }
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
                ],
                "constraints": [
                    {
                        "constraint_id": "hot_peak_limit",
                        "operating_case": "hot",
                        "metric": "summary.temperature_max",
                        "relation": "<=",
                        "limit": 350.0,
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
