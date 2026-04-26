"""Raw NSGA-II backbone wrapper."""

from __future__ import annotations

from typing import Any

from pymoo.algorithms.moo.nsga2 import NSGA2

from optimizers.clean_initialization import CleanBaselineSampling
from optimizers.raw_backbones.common import build_pm, build_sbx


FAMILY = "genetic"
BACKBONE = "nsga2"


def build_algorithm(problem: Any, algorithm_config: dict[str, Any]) -> NSGA2:
    parameters = algorithm_config["parameters"]
    return NSGA2(
        pop_size=int(algorithm_config["population_size"]),
        sampling=CleanBaselineSampling(),
        crossover=build_sbx(parameters["crossover"]),
        mutation=build_pm(parameters["mutation"]),
    )
