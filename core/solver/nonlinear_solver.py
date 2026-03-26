"""Solve canonical thermal cases with the Phase 1 FEniCSx baseline."""

from __future__ import annotations

from typing import Any

from dolfinx.fem.petsc import NonlinearProblem

from core.contracts.case_contracts import assert_case_geometry_contracts
from core.schema.models import ThermalSolution
from core.solver.case_to_geometry import interpret_case
from core.solver.field_sampler import sample_solution_fields
from core.solver.mesh_builder import build_panel_mesh
from core.solver.physics_builder import build_thermal_problem
from core.solver.solution_builder import build_solution


def solve_case(case: Any) -> ThermalSolution:
    assert_case_geometry_contracts(case)
    solver_inputs = interpret_case(case)
    domain = build_panel_mesh(solver_inputs["panel_domain"], solver_inputs["mesh_profile"])
    problem_data = build_thermal_problem(domain, solver_inputs)
    solver_profile = solver_inputs["solver_profile"]
    petsc_options = {
        "snes_type": "newtonls",
        "snes_atol": float(solver_profile.get("absolute_tolerance", 1.0e-8)),
        "snes_rtol": float(solver_profile.get("relative_tolerance", 1.0e-8)),
        "snes_max_it": int(solver_profile.get("max_iterations", 50)),
        "ksp_type": "preonly",
        "pc_type": "lu",
    }
    problem = NonlinearProblem(
        problem_data["residual"],
        problem_data["temperature"],
        petsc_options_prefix="thermal_",
        petsc_options=petsc_options,
    )
    problem.solve()
    problem_data["temperature"].x.scatter_forward()
    iterations = problem.solver.getIterationNumber()
    converged = problem.solver.getConvergedReason() > 0
    sampled_fields = sample_solution_fields(problem_data["temperature"], solver_inputs["components"])
    diagnostics = {
        "converged": bool(converged),
        "iterations": int(iterations),
        "solver": "dolfinx_snes",
    }
    return build_solution(case, sampled_fields, diagnostics)
