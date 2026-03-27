"""Raw C-TAEA backbone wrapper."""

from __future__ import annotations

from typing import Any

from pymoo.algorithms.moo.ctaea import CTAEA

from optimizers.raw_backbones.common import build_pm, build_reference_directions, build_sbx


FAMILY = "genetic"
BACKBONE = "ctaea"


def build_algorithm(problem: Any, algorithm_config: dict[str, Any]) -> CTAEA:
    pop_size = int(algorithm_config["population_size"])
    parameters = algorithm_config["parameters"]
    ref_dirs = build_reference_directions(problem.n_obj, pop_size, parameters["reference_directions"])
    return CTAEA(
        ref_dirs=ref_dirs,
        crossover=build_sbx(parameters["crossover"]),
        mutation=build_pm(parameters["mutation"]),
    )
