"""Mesh construction for canonical panel domains."""

from __future__ import annotations

from dolfinx import mesh
from mpi4py import MPI


def build_panel_mesh(panel_domain: dict[str, float], mesh_profile: dict[str, int]) -> mesh.Mesh:
    width = float(panel_domain["width"])
    height = float(panel_domain["height"])
    nx = int(mesh_profile.get("nx", 32))
    ny = int(mesh_profile.get("ny", 32))
    return mesh.create_rectangle(
        MPI.COMM_SELF,
        ((0.0, 0.0), (width, height)),
        (nx, ny),
        cell_type=mesh.CellType.triangle,
    )
