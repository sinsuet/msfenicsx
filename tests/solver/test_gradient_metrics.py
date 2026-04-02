import numpy as np
import pytest
from dolfinx import fem
from mpi4py import MPI
from shapely.geometry import box

from core.generator.paired_pipeline import generate_operating_case_pair
from core.solver import solve_case
from core.solver.field_sampler import sample_solution_fields
from core.solver.gradient_metrics import compute_temperature_gradient_rms
from core.solver.mesh_builder import build_panel_mesh
from evaluation.engine import evaluate_case_solution
from evaluation.models import EvaluationSpec


def test_compute_temperature_gradient_rms_returns_zero_for_constant_field() -> None:
    domain = build_panel_mesh({"width": 1.0, "height": 1.0}, {"nx": 4, "ny": 4})
    function_space = fem.functionspace(domain, ("Lagrange", 1))
    temperature = fem.Function(function_space)
    temperature.interpolate(lambda x: np.full(x.shape[1], 300.0, dtype=np.float64))
    temperature.x.scatter_forward()

    value = compute_temperature_gradient_rms(temperature, panel_area=1.0)

    assert value == pytest.approx(0.0)


def test_sample_solution_fields_reports_temperature_gradient_rms_in_summary_metrics() -> None:
    domain = build_panel_mesh({"width": 1.0, "height": 1.0}, {"nx": 4, "ny": 4})
    function_space = fem.functionspace(domain, ("Lagrange", 1))
    temperature = fem.Function(function_space)
    temperature.interpolate(lambda x: x[0])
    temperature.x.scatter_forward()

    sampled_fields = sample_solution_fields(
        temperature,
        components=[
            {
                "component_id": "comp-001",
                "polygon": box(0.2, 0.2, 0.4, 0.4),
            }
        ],
        panel_area=1.0,
    )

    assert sampled_fields["summary_metrics"]["temperature_gradient_rms"] == pytest.approx(1.0)
    assert sampled_fields["component_summaries"]


def test_solve_case_surfaces_temperature_gradient_rms_for_evaluation() -> None:
    case = generate_operating_case_pair("scenarios/templates/panel_four_component_hot_cold_benchmark.yaml", seed=11)["hot"]

    solution = solve_case(case)

    assert "temperature_gradient_rms" in solution.summary_metrics

    spec = EvaluationSpec.from_dict(
        {
            "schema_version": "1.0",
            "spec_meta": {
                "spec_id": "gradient-rms-check",
                "description": "Verify gradient RMS is evaluable from solver output.",
            },
            "objectives": [
                {
                    "objective_id": "minimize_temperature_gradient_rms",
                    "metric": "summary.temperature_gradient_rms",
                    "sense": "minimize",
                }
            ],
            "constraints": [],
        }
    )

    report = evaluate_case_solution(case, solution, spec)

    assert report.metric_values["summary.temperature_gradient_rms"] == pytest.approx(
        solution.summary_metrics["temperature_gradient_rms"]
    )
