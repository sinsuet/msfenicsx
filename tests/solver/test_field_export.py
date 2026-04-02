from __future__ import annotations

import numpy as np
from dolfinx import fem
from shapely.geometry import box

from core.generator.pipeline import generate_case
from core.solver.field_export import export_field_views
from core.solver.field_sampler import sample_solution_fields
from core.solver.mesh_builder import build_panel_mesh
from core.solver.nonlinear_solver import solve_case_artifacts


def test_export_field_views_writes_temperature_and_gradient_grids() -> None:
    domain = build_panel_mesh({"width": 1.0, "height": 0.8}, {"nx": 4, "ny": 4})
    function_space = fem.functionspace(domain, ("Lagrange", 1))
    temperature = fem.Function(function_space)
    temperature.interpolate(lambda x: x[0] + 2.0 * x[1])
    temperature.x.scatter_forward()

    payload = export_field_views(
        temperature,
        panel_domain={"width": 1.0, "height": 0.8},
        components=[
            {
                "component_id": "comp-001",
                "polygon": box(0.2, 0.2, 0.4, 0.4),
            }
        ],
        line_sinks=[
            {
                "feature_id": "sink-top-window",
                "edge": "top",
                "start": 0.25,
                "end": 0.55,
            }
        ],
    )

    assert payload["arrays"]["temperature"].shape == (81, 101)
    assert payload["arrays"]["gradient_magnitude"].shape == (81, 101)
    assert payload["field_view"]["temperature"]["grid_shape"] == [81, 101]
    assert payload["field_view"]["layout"]["components"][0]["component_id"] == "comp-001"
    assert payload["field_view"]["layout"]["line_sinks"][0]["feature_id"] == "sink-top-window"


def test_sample_solution_fields_includes_page_ready_field_exports() -> None:
    domain = build_panel_mesh({"width": 1.0, "height": 0.8}, {"nx": 4, "ny": 4})
    function_space = fem.functionspace(domain, ("Lagrange", 1))
    temperature = fem.Function(function_space)
    temperature.interpolate(lambda x: np.full(x.shape[1], 300.0, dtype=np.float64))
    temperature.x.scatter_forward()

    sampled = sample_solution_fields(
        temperature,
        components=[
            {
                "component_id": "comp-001",
                "polygon": box(0.2, 0.2, 0.4, 0.4),
            }
        ],
        panel_area=0.8,
        panel_domain={"width": 1.0, "height": 0.8},
        line_sinks=[
            {
                "feature_id": "sink-top-window",
                "edge": "top",
                "start": 0.25,
                "end": 0.55,
            }
        ],
    )

    assert sampled["field_records"]["temperature"]["kind"] == "cg1_dofs"
    assert "temperature_gradient_rms" in sampled["summary_metrics"]
    assert sampled["field_exports"]["field_view"]["temperature"]["grid_shape"] == [81, 101]


def test_solve_case_artifacts_returns_solution_and_field_exports() -> None:
    case = generate_case("scenarios/templates/s1_typical.yaml", seed=11)

    solved = solve_case_artifacts(case)

    assert solved["solution"].solution_meta["case_id"] == case.case_meta["case_id"]
    assert solved["field_exports"]["field_view"]["temperature"]["grid_shape"] == [81, 101]
