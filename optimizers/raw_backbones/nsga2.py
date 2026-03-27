"""Raw NSGA-II backbone wrapper."""

from __future__ import annotations

from typing import Any

from pymoo.algorithms.moo.nsga2 import NSGA2


FAMILY = "genetic"
BACKBONE = "nsga2"


def build_algorithm(problem: Any, algorithm_config: dict[str, Any]) -> NSGA2:
    del problem
    return NSGA2(pop_size=int(algorithm_config["population_size"]))
