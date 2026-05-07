from __future__ import annotations

from collections import Counter

import numpy as np

from optimizers.operator_pool.controllers import build_controller
from optimizers.operator_pool.random_controller import RandomUniformController
from optimizers.operator_pool.state import ControllerState


def _state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=0,
        evaluation_index=0,
        parent_count=2,
        vector_size=2,
    )


def test_random_uniform_controller_accepts_operator_weights() -> None:
    controller = build_controller(
        "random_uniform",
        {
            "operator_weights": {
                "weak": 9.0,
                "strong": 1.0,
            }
        },
    )
    rng = np.random.default_rng(7)

    counts = Counter(controller.select_operator(_state(), ["weak", "strong"], rng) for _ in range(2000))

    assert counts["weak"] > counts["strong"] * 6


def test_random_uniform_controller_defaults_to_equal_sampling_without_weights() -> None:
    controller = RandomUniformController()
    rng = np.random.default_rng(7)

    counts = Counter(controller.select_operator(_state(), ["a", "b"], rng) for _ in range(2000))

    assert abs(counts["a"] - counts["b"]) < 150
