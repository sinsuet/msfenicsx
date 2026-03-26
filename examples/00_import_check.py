from mpi4py import MPI

import basix
import dolfinx
import matplotlib
import numpy as np
import petsc4py
import ufl


def main() -> None:
    print("FEniCSx import check")
    print(f"dolfinx: {dolfinx.__version__}")
    print(f"basix: {basix.__version__}")
    print(f"ufl: {ufl.__version__}")
    print(f"petsc4py: {petsc4py.__version__}")
    print(f"numpy: {np.__version__}")
    print(f"matplotlib: {matplotlib.__version__}")
    print(f"MPI size: {MPI.COMM_WORLD.size}")
    print(f"MPI rank: {MPI.COMM_WORLD.rank}")


if __name__ == "__main__":
    main()
