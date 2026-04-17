# tests/optimizers/test_cli_pop_gen_overrides.py
"""CLI --population-size / --num-generations overrides."""

from __future__ import annotations


def test_build_parser_accepts_pop_gen_overrides() -> None:
    from optimizers.cli import build_parser

    parser = build_parser()
    args = parser.parse_args(
        [
            "optimize-benchmark",
            "--optimization-spec",
            "scenarios/optimization/s1_typical_llm.yaml",
            "--output-root",
            "./scenario_runs/smoke",
            "--population-size",
            "10",
            "--num-generations",
            "5",
        ]
    )
    assert args.population_size == 10
    assert args.num_generations == 5


def test_apply_algorithm_overrides_mutates_algorithm_dict() -> None:
    from optimizers.cli import apply_algorithm_overrides

    algorithm_dict = {"population_size": 32, "num_generations": 16}
    apply_algorithm_overrides(algorithm_dict, population_size=10, num_generations=5)
    assert algorithm_dict["population_size"] == 10
    assert algorithm_dict["num_generations"] == 5


def test_apply_algorithm_overrides_noop_when_absent() -> None:
    from optimizers.cli import apply_algorithm_overrides

    algorithm_dict = {"population_size": 32, "num_generations": 16}
    apply_algorithm_overrides(algorithm_dict, population_size=None, num_generations=None)
    assert algorithm_dict["population_size"] == 32
    assert algorithm_dict["num_generations"] == 16
