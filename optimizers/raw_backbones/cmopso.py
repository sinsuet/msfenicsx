"""Raw CMOPSO backbone wrapper."""

from __future__ import annotations

from typing import Any

from pymoo.algorithms.moo.cmopso import CMOPSO


FAMILY = "swarm"
BACKBONE = "cmopso"


def build_algorithm(problem: Any, algorithm_config: dict[str, Any]) -> CMOPSO:
    del problem
    pop_size = int(algorithm_config["population_size"])
    elite_size = min(max(5, pop_size // 2), pop_size)
    return CMOPSO(pop_size=pop_size, elite_size=elite_size)
