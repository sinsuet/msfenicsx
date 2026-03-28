"""Raw CMOPSO backbone wrapper."""

from __future__ import annotations

from typing import Any

from pymoo.algorithms.moo.cmopso import CMOPSO

from optimizers.raw_backbones.common import resolve_population_fraction_size


FAMILY = "swarm"
BACKBONE = "cmopso"


def build_algorithm_kwargs(problem: Any, algorithm_config: dict[str, Any]) -> dict[str, Any]:
    del problem
    pop_size = int(algorithm_config["population_size"])
    parameters = algorithm_config["parameters"]
    elite_size = resolve_population_fraction_size(pop_size, parameters["elite_archive"])
    return {
        "pop_size": pop_size,
        "elite_size": elite_size,
    }


def build_algorithm(problem: Any, algorithm_config: dict[str, Any]) -> CMOPSO:
    kwargs = build_algorithm_kwargs(problem, algorithm_config)
    return CMOPSO(pop_size=kwargs["pop_size"], elite_size=kwargs["elite_size"])
