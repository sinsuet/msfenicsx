from __future__ import annotations

from optimizers.matrix.models import MatrixConfig, ResourceCap


def build_s5_s7_512eval_matrix() -> MatrixConfig:
    return MatrixConfig(
        matrix_id="s5_s7_512eval",
        scenarios=("s5_aggressive15", "s6_aggressive20", "s7_aggressive25"),
        replicate_seeds=(11, 17, 23, 29, 31),
        algorithm_seed_offset=1000,
        population_size=32,
        num_generations=16,
        llm_profiles=(
            "gpt_5_4",
            "qwen3_6_plus",
            "glm_5",
            "minimax_m2_5",
            "deepseek_v4_flash",
            "gemma4",
        ),
        resource_caps={
            "raw": ResourceCap(evaluation_workers=8, concurrent_runs=80),
            "union": ResourceCap(evaluation_workers=8, concurrent_runs=60),
            "external_llm": ResourceCap(evaluation_workers=3, concurrent_runs=20),
            "gemma4": ResourceCap(evaluation_workers=3, concurrent_runs=8),
        },
    )
