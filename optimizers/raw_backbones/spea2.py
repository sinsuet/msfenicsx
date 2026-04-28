"""Raw SPEA2 backbone wrapper."""

from __future__ import annotations

from typing import Any

from pymoo.algorithms.moo.spea2 import SPEA2

from optimizers.clean_initialization import CleanBaselineSampling
from optimizers.raw_backbones.common import build_pm, build_sbx


FAMILY = "genetic"
BACKBONE = "spea2"


def build_algorithm(problem: Any, algorithm_config: dict[str, Any]) -> SPEA2:
    del problem
    parameters = algorithm_config["parameters"]
    return SPEA2(
        pop_size=int(algorithm_config["population_size"]),
        sampling=CleanBaselineSampling(),
        crossover=build_sbx(parameters["crossover"]),
        mutation=build_pm(parameters["mutation"]),
    )
