from __future__ import annotations

from optimizers.matrix.models import MatrixConfig, ResourceCap, ScenarioBudget


def build_s5_s7_budgeted_matrix() -> MatrixConfig:
    return MatrixConfig(
        matrix_id="s5_s7_budgeted",
        scenarios=("s5_aggressive15", "s6_aggressive20", "s7_aggressive25"),
        replicate_seeds=(11, 17, 23, 29, 31),
        algorithm_seed_offset=1000,
        scenario_budgets={
            "s5_aggressive15": ScenarioBudget(population_size=40, num_generations=32),
            "s6_aggressive20": ScenarioBudget(population_size=56, num_generations=36),
            "s7_aggressive25": ScenarioBudget(population_size=64, num_generations=40),
        },
        llm_profiles=(
            "gpt_5_4",
            "qwen3_6_plus",
            "glm_5",
            "minimax_m2_5",
            "deepseek_v4_flash",
            "gemma4",
            "mimo_v2_5",
        ),
        resource_caps={
            "raw": ResourceCap(evaluation_workers=8, concurrent_runs=80),
            "union": ResourceCap(evaluation_workers=8, concurrent_runs=60),
            "external_llm": ResourceCap(evaluation_workers=3, concurrent_runs=20),
            "gemma4": ResourceCap(evaluation_workers=3, concurrent_runs=8),
        },
    )


def build_s5_s7_512eval_matrix() -> MatrixConfig:
    """Backward-compatible entry point for the active S5-S7 budgeted matrix."""
    return build_s5_s7_budgeted_matrix()
