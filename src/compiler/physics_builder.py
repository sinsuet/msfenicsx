from __future__ import annotations

import ufl

from dolfinx import fem
from dolfinx.fem.petsc import LinearProblem

from .mesh_builder import LEFT_TAG, RIGHT_TAG


def _dirichlet_value_by_location(boundary_conditions) -> dict[str, float]:
    values: dict[str, float] = {}
    for item in boundary_conditions:
        if item.type == "dirichlet":
            values[item.location] = float(item.value)
    return values


def build_problem(
    domain,
    cell_tags,
    facet_tags,
    layout,
    boundary_conditions,
    linear_solver: str = "lu",
):
    V = fem.functionspace(domain, ("Lagrange", 1))
    DG0 = fem.functionspace(domain, ("DG", 0))

    conductivity = fem.Function(DG0)
    heat_source = fem.Function(DG0)
    conductivity.x.array[:] = 0.0
    heat_source.x.array[:] = 0.0

    for component in layout:
        component_cells = cell_tags.find(component.label)
        conductivity.x.array[component_cells] = component.conductivity
        heat_source.x.array[component_cells] = component.heat_source

    fdim = domain.topology.dim - 1
    left_dofs = fem.locate_dofs_topological(V, fdim, facet_tags.find(LEFT_TAG))
    right_dofs = fem.locate_dofs_topological(V, fdim, facet_tags.find(RIGHT_TAG))
    dirichlet_values = _dirichlet_value_by_location(boundary_conditions)
    left_value = fem.Function(V)
    left_value.x.array[:] = dirichlet_values.get("left", 0.0)
    right_value = fem.Function(V)
    right_value.x.array[:] = dirichlet_values.get("right", 0.0)
    bc_left = fem.dirichletbc(left_value, left_dofs)
    bc_right = fem.dirichletbc(right_value, right_dofs)

    u = ufl.TrialFunction(V)
    v = ufl.TestFunction(V)
    a = conductivity * ufl.inner(ufl.grad(u), ufl.grad(v)) * ufl.dx
    L = heat_source * v * ufl.dx

    petsc_options = {"ksp_type": "preonly", "pc_type": linear_solver}
    problem = LinearProblem(
        a,
        L,
        petsc_options_prefix="multicomponent_heat_",
        bcs=[bc_left, bc_right],
        petsc_options=petsc_options,
    )
    return problem, V
