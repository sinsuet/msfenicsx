"""Finite-element gradient-derived solution metrics."""

from __future__ import annotations

import math
from numbers import Real
from typing import Any

from dolfinx import fem
from mpi4py import MPI
import ufl


def compute_temperature_gradient_rms(temperature_function: Any, panel_area: Real) -> float:
    """Compute sqrt((1 / |Omega|) * integral_Omega |grad(T_h)|^2 dx)."""

    if float(panel_area) <= 0.0:
        raise ValueError("panel_area must be positive.")

    domain = temperature_function.function_space.mesh
    energy_density = ufl.inner(ufl.grad(temperature_function), ufl.grad(temperature_function)) * ufl.dx(domain=domain)
    local_integral = fem.assemble_scalar(fem.form(energy_density))
    integral = domain.comm.allreduce(local_integral, op=MPI.SUM)
    return math.sqrt(max(integral, 0.0) / float(panel_area))
