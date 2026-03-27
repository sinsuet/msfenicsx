"""Raw NSGA-III backbone wrapper."""

from __future__ import annotations

from typing import Any

import numpy as np
from pymoo.algorithms.moo.nsga3 import NSGA3
from pymoo.operators.selection.tournament import TournamentSelection
from pymoo.util import default_random_state

from optimizers.raw_backbones.common import build_pm, build_reference_directions, build_sbx


FAMILY = "genetic"
BACKBONE = "nsga3"


@default_random_state
def _comp_by_cv_then_seeded_random(pop: Any, P: np.ndarray, random_state=None, **kwargs) -> np.ndarray:
    del kwargs
    winners = np.full(P.shape[0], np.nan)

    for index in range(P.shape[0]):
        left, right = P[index, 0], P[index, 1]
        left_cv = float(np.asarray(pop[left].CV).reshape(-1)[0])
        right_cv = float(np.asarray(pop[right].CV).reshape(-1)[0])

        if left_cv > 0.0 or right_cv > 0.0:
            if left_cv < right_cv:
                winners[index] = left
            elif left_cv > right_cv:
                winners[index] = right
            else:
                winners[index] = random_state.choice([left, right])
        else:
            winners[index] = random_state.choice([left, right])

    return winners[:, None].astype(int)


def build_algorithm(problem: Any, algorithm_config: dict[str, Any]) -> NSGA3:
    pop_size = int(algorithm_config["population_size"])
    parameters = algorithm_config["parameters"]
    ref_dirs = build_reference_directions(problem.n_obj, pop_size, parameters["reference_directions"])
    return NSGA3(
        ref_dirs=ref_dirs,
        pop_size=pop_size,
        selection=TournamentSelection(func_comp=_comp_by_cv_then_seeded_random),
        crossover=build_sbx(parameters["crossover"]),
        mutation=build_pm(parameters["mutation"]),
    )
