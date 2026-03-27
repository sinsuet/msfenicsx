"""Raw NSGA-III backbone wrapper."""

from __future__ import annotations

from typing import Any

from pymoo.algorithms.moo.nsga3 import NSGA3
from pymoo.util.ref_dirs import get_reference_directions


FAMILY = "genetic"
BACKBONE = "nsga3"


def build_algorithm(problem: Any, algorithm_config: dict[str, Any]) -> NSGA3:
    pop_size = int(algorithm_config["population_size"])
    ref_dirs = get_reference_directions("energy", problem.n_obj, n_points=pop_size)
    return NSGA3(ref_dirs=ref_dirs, pop_size=pop_size)
