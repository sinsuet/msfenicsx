from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import numpy as np
import ufl
from mpi4py import MPI
from petsc4py import PETSc

from dolfinx import fem, io, mesh
from dolfinx.fem.petsc import LinearProblem


def exact_temperature(x: np.ndarray, length: float) -> np.ndarray:
    return 1.0 - x[0] / length


def main() -> None:
    root_dir = Path(__file__).resolve().parents[1]
    output_dir = root_dir / "outputs"
    figure_dir = output_dir / "figures"
    data_dir = output_dir / "data"
    figure_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    length = 1.0
    height = 0.4
    nx = 40
    ny = 16

    domain = mesh.create_rectangle(
        comm=MPI.COMM_WORLD,
        points=((0.0, 0.0), (length, height)),
        n=(nx, ny),
        cell_type=mesh.CellType.triangle,
    )

    V = fem.functionspace(domain, ("Lagrange", 1))

    u_D = fem.Function(V)
    u_D.interpolate(lambda x: exact_temperature(x, length))

    boundary_dofs = fem.locate_dofs_geometrical(
        V,
        lambda x: np.logical_or.reduce(
            (
                np.isclose(x[0], 0.0),
                np.isclose(x[0], length),
                np.isclose(x[1], 0.0),
                np.isclose(x[1], height),
            )
        ),
    )
    bc = fem.dirichletbc(u_D, boundary_dofs)

    u = ufl.TrialFunction(V)
    v = ufl.TestFunction(V)
    a = ufl.inner(ufl.grad(u), ufl.grad(v)) * ufl.dx
    L = fem.Constant(domain, PETSc.ScalarType(0.0)) * v * ufl.dx

    problem = LinearProblem(
        a,
        L,
        petsc_options_prefix="steady_heat_",
        bcs=[bc],
        petsc_options={"ksp_type": "preonly", "pc_type": "lu"},
    )
    uh = problem.solve()
    uh.name = "temperature"

    exact = fem.Function(V)
    exact.interpolate(lambda x: exact_temperature(x, length))
    error = np.abs(uh.x.array - exact.x.array)

    topology_dim = domain.topology.dim
    num_cells = domain.topology.index_map(topology_dim).size_local
    num_dofs_per_cell = V.dofmap.dof_layout.num_dofs
    cells = np.asarray(V.dofmap.list, dtype=np.int32).reshape(num_cells, num_dofs_per_cell)
    dof_coords = V.tabulate_dof_coordinates()[:, :2]

    triangulation = mtri.Triangulation(
        dof_coords[:, 0],
        dof_coords[:, 1],
        cells,
    )

    if domain.comm.rank == 0:
        fig, ax = plt.subplots(figsize=(8, 3))
        contour = ax.tricontourf(triangulation, uh.x.array, levels=30, cmap="inferno")
        ax.set_title("2D Steady Heat Conduction")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_aspect("equal")
        fig.colorbar(contour, ax=ax, label="Temperature")
        fig.tight_layout()
        fig.savefig(figure_dir / "01_steady_heat_rectangle.png", dpi=180)
        plt.close(fig)

        np.savetxt(
            data_dir / "01_steady_heat_rectangle_summary.txt",
            np.array(
                [
                    [uh.x.array.min(), uh.x.array.max(), error.max()],
                ]
            ),
            header="u_min u_max max_abs_error",
        )

    with io.XDMFFile(domain.comm, str(data_dir / "01_steady_heat_rectangle.xdmf"), "w") as xdmf:
        xdmf.write_mesh(domain)
        xdmf.write_function(uh)

    if domain.comm.rank == 0:
        print("Example finished.")
        print(f"Mesh: {nx} x {ny} triangles on a {length} x {height} rectangle")
        print(f"Temperature min: {uh.x.array.min():.6f}")
        print(f"Temperature max: {uh.x.array.max():.6f}")
        print(f"Max abs error vs exact solution: {error.max():.6e}")
        print(f"Figure saved to: {figure_dir / '01_steady_heat_rectangle.png'}")
        print(f"Data saved to: {data_dir / '01_steady_heat_rectangle.xdmf'}")


if __name__ == "__main__":
    main()
