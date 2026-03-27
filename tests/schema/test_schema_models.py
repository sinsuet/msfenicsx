from core.schema.models import ScenarioTemplate, ThermalCase, ThermalSolution


def test_thermal_case_requires_case_meta_and_components() -> None:
    payload = {
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

    case = ThermalCase.from_dict(payload)

    assert case.case_meta["case_id"] == "case-001"
    assert case.panel_material_ref == "aluminum"
    assert case.components == []
    assert case.to_dict() == payload


def test_scenario_template_round_trips_to_dict() -> None:
    payload = {
        "schema_version": "1.0",
        "template_meta": {
            "template_id": "panel-radiation-baseline",
            "description": "Baseline 2D satellite panel scenario template.",
        },
        "coordinate_system": {"plane": "panel_xy"},
        "panel_domain": {"width": 1.0, "height": 0.8},
        "placement_regions": [],
        "keep_out_regions": [],
        "component_families": [],
        "boundary_feature_families": [],
        "load_rules": [],
        "material_rules": [],
        "operating_case_profiles": [
            {
                "operating_case_id": "hot",
                "ambient_temperature": 300.0,
                "component_power_overrides": {"processor": 24.0},
                "boundary_feature_overrides": {"radiator-top": {"sink_temperature": 292.0}},
            }
        ],
        "mesh_profile": {"nx": 32, "ny": 24},
        "solver_profile": {"nonlinear_solver": "snes"},
        "generation_rules": {"seed_policy": "external"},
    }

    template = ScenarioTemplate.from_dict(payload)

    assert template.template_meta["template_id"] == "panel-radiation-baseline"
    assert template.operating_case_profiles[0]["operating_case_id"] == "hot"
    assert template.to_dict() == payload


def test_thermal_solution_round_trips_to_dict() -> None:
    payload = {
        "schema_version": "1.0",
        "solution_meta": {"solution_id": "sol-001", "case_id": "case-001"},
        "solver_diagnostics": {"converged": True, "iterations": 6},
        "field_records": {"temperature": {"path": "fields/temperature.npy"}},
        "summary_metrics": {"temperature_min": 285.1, "temperature_max": 322.4},
        "component_summaries": [],
        "provenance": {"solver": "fenicsx"},
    }

    solution = ThermalSolution.from_dict(payload)

    assert solution.solution_meta["case_id"] == "case-001"
    assert solution.to_dict() == payload
