from pathlib import Path

from core.schema.io import load_case, load_template, load_solution, save_case, save_template, save_solution
from core.schema.models import ScenarioTemplate, ThermalCase, ThermalSolution


def _template_payload() -> dict:
    return {
        "schema_version": "1.0",
        "template_meta": {
            "template_id": "s1_typical",
            "description": "Single-case s1_typical template.",
        },
        "coordinate_system": {"plane": "panel_xy"},
        "panel_domain": {"width": 1.0, "height": 0.8},
        "placement_regions": [],
        "keep_out_regions": [],
        "component_families": [],
        "boundary_feature_families": [],
        "load_rules": [],
        "material_rules": [],
        "mesh_profile": {"nx": 32, "ny": 24},
        "solver_profile": {"nonlinear_solver": "snes"},
        "generation_rules": {"seed_policy": "external"},
    }


def _case_payload() -> dict:
    return {
        "schema_version": "1.0",
        "case_meta": {"case_id": "case-001", "scenario_id": "panel-baseline"},
        "coordinate_system": {"plane": "panel_xy"},
        "panel_domain": {"width": 1.0, "height": 0.8},
        "panel_material_ref": "aluminum",
        "materials": {
            "aluminum": {"conductivity": 205.0, "emissivity": 0.78},
        },
        "components": [],
        "boundary_features": [],
        "loads": [],
        "physics": {"kind": "steady_heat_radiation"},
        "mesh_profile": {"nx": 32, "ny": 24},
        "solver_profile": {"nonlinear_solver": "snes"},
        "provenance": {"source": "unit-test"},
    }


def _solution_payload() -> dict:
    return {
        "schema_version": "1.0",
        "solution_meta": {"solution_id": "sol-001", "case_id": "case-001"},
        "solver_diagnostics": {"converged": True, "iterations": 6},
        "field_records": {"temperature": {"path": "fields/temperature.npy"}},
        "summary_metrics": {"temperature_min": 285.1, "temperature_max": 322.4},
        "component_summaries": [],
        "provenance": {"solver": "fenicsx"},
    }


def test_save_and_load_yaml_round_trip(tmp_path: Path) -> None:
    template_path = tmp_path / "template.yaml"
    case_path = tmp_path / "case.yaml"
    solution_path = tmp_path / "solution.yaml"

    save_template(ScenarioTemplate.from_dict(_template_payload()), template_path)
    save_case(ThermalCase.from_dict(_case_payload()), case_path)
    save_solution(ThermalSolution.from_dict(_solution_payload()), solution_path)

    assert load_template(template_path).to_dict() == _template_payload()
    assert load_case(case_path).to_dict() == _case_payload()
    assert load_solution(solution_path).to_dict() == _solution_payload()


def test_save_and_load_json_round_trip(tmp_path: Path) -> None:
    case_path = tmp_path / "case.json"

    save_case(ThermalCase.from_dict(_case_payload()), case_path)

    assert load_case(case_path).to_dict() == _case_payload()
