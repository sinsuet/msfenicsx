"""Raw RVEA backbone wrapper."""

from __future__ import annotations

from typing import Any

from pymoo.algorithms.moo.rvea import RVEA
from pymoo.util.ref_dirs import get_reference_directions


FAMILY = "genetic"
BACKBONE = "rvea"


def build_algorithm(problem: Any, algorithm_config: dict[str, Any]) -> RVEA:
    pop_size = int(algorithm_config["population_size"])
    ref_dirs = get_reference_directions("energy", problem.n_obj, n_points=pop_size)
    return RVEA(ref_dirs=ref_dirs, pop_size=pop_size)
