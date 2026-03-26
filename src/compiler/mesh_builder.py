from __future__ import annotations

import gmsh
import numpy as np
from mpi4py import MPI

from dolfinx.io.gmsh import model_to_mesh


LEFT_TAG = 101
RIGHT_TAG = 102


def _inside_component(x: float, y: float, component, tol: float = 1e-9) -> bool:
    return (
        component.x0 - tol <= x <= component.x1 + tol
        and component.y0 - tol <= y <= component.y1 + tol
    )


def _build_gmsh_model(layout, mesh_size: float) -> None:
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add("multicomponent_steady_heat")

    surfaces = []
    for component in layout:
        tag = gmsh.model.occ.addRectangle(
            component.x0,
            component.y0,
            0.0,
            component.width,
            component.height,
        )
        surfaces.append((2, tag))

    gmsh.model.occ.fragment([surfaces[0]], surfaces[1:])
    gmsh.model.occ.synchronize()

    all_surfaces = gmsh.model.getEntities(dim=2)
    for _, surface_tag in all_surfaces:
        cx, cy, _ = gmsh.model.occ.getCenterOfMass(2, surface_tag)
        matched = None
        for component in layout:
            if _inside_component(cx, cy, component):
                matched = component
                break
        if matched is None:
            raise RuntimeError(f"Could not map surface {surface_tag} to a component.")
        gmsh.model.addPhysicalGroup(2, [surface_tag], matched.label)
        gmsh.model.setPhysicalName(2, matched.label, matched.name)

    x_min = min(component.x0 for component in layout)
    x_max = max(component.x1 for component in layout)
    left_curves = []
    right_curves = []
    for _, curve_tag in gmsh.model.getEntities(dim=1):
        cx, _, _ = gmsh.model.occ.getCenterOfMass(1, curve_tag)
        if np.isclose(cx, x_min):
            left_curves.append(curve_tag)
        elif np.isclose(cx, x_max):
            right_curves.append(curve_tag)

    if not left_curves or not right_curves:
        raise RuntimeError("Failed to identify left/right boundary curves.")

    gmsh.model.addPhysicalGroup(1, left_curves, LEFT_TAG)
    gmsh.model.setPhysicalName(1, LEFT_TAG, "left_cold_boundary")
    gmsh.model.addPhysicalGroup(1, right_curves, RIGHT_TAG)
    gmsh.model.setPhysicalName(1, RIGHT_TAG, "right_cold_boundary")

    gmsh.model.mesh.setSize(gmsh.model.getEntities(0), mesh_size)
    gmsh.model.mesh.generate(2)


def build_mesh_from_layout(layout, nx: int, ny: int, comm: MPI.Comm = MPI.COMM_WORLD):
    total_width = max(component.x1 for component in layout) - min(component.x0 for component in layout)
    total_height = max(component.y1 for component in layout) - min(component.y0 for component in layout)
    mesh_size = min(total_width / nx, total_height / ny)

    gmsh.initialize()
    try:
        if comm.rank == 0:
            _build_gmsh_model(layout, mesh_size)
        mesh_data = model_to_mesh(gmsh.model, comm, 0, gdim=2)
    finally:
        gmsh.finalize()

    return mesh_data, mesh_size
