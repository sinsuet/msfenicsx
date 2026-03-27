"""Raw C-TAEA backbone wrapper."""

from __future__ import annotations

from typing import Any

from pymoo.algorithms.moo.ctaea import CTAEA
from pymoo.util.ref_dirs import get_reference_directions


FAMILY = "genetic"
BACKBONE = "ctaea"


def build_algorithm(problem: Any, algorithm_config: dict[str, Any]) -> CTAEA:
    ref_dirs = get_reference_directions("energy", problem.n_obj, n_points=int(algorithm_config["population_size"]))
    return CTAEA(ref_dirs=ref_dirs)
