"""Raw RVEA backbone wrapper."""

from __future__ import annotations

from typing import Any

from pymoo.algorithms.moo.rvea import RVEA

from optimizers.raw_backbones.common import build_reference_directions


FAMILY = "genetic"
BACKBONE = "rvea"


def build_algorithm(problem: Any, algorithm_config: dict[str, Any]) -> RVEA:
    pop_size = int(algorithm_config["population_size"])
    parameters = algorithm_config["parameters"]
    ref_dirs = build_reference_directions(problem.n_obj, pop_size, parameters["reference_directions"])
    return RVEA(ref_dirs=ref_dirs, pop_size=pop_size)
