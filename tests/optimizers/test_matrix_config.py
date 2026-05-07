from optimizers.matrix.config import build_s5_s7_budgeted_matrix


def test_s5_s7_matrix_counts_and_blocks() -> None:
    matrix = build_s5_s7_budgeted_matrix()

    assert matrix.matrix_id == "s5_s7_budgeted"
    assert matrix.scenario_budgets["s5_aggressive15"].population_size == 40
    assert matrix.scenario_budgets["s5_aggressive15"].num_generations == 32
    assert matrix.scenario_budgets["s6_aggressive20"].population_size == 56
    assert matrix.scenario_budgets["s6_aggressive20"].num_generations == 36
    assert matrix.scenario_budgets["s7_aggressive25"].population_size == 64
    assert matrix.scenario_budgets["s7_aggressive25"].num_generations == 40
    assert matrix.replicate_seeds == (11, 17, 23, 29, 31)
    assert matrix.algorithm_seed_offset == 1000

    leaves = matrix.expand_leaves()
    assert len(leaves) == 165

    counts = {}
    for leaf in leaves:
        counts[leaf.block_id] = counts.get(leaf.block_id, 0) + 1

    assert counts == {
        "M1_raw_backbone_budgeted": 45,
        "M2_nsga2_union_budgeted": 15,
        "M3a_llm_gpt_5_4_budgeted": 15,
        "M3b_llm_qwen3_6_plus_budgeted": 15,
        "M3c_llm_glm_5_budgeted": 15,
        "M3d_llm_minimax_m2_5_budgeted": 15,
        "M3e_llm_deepseek_v4_flash_budgeted": 15,
        "M3f_llm_gemma4_budgeted": 15,
        "M3g_llm_mimo_v2_5_budgeted": 15,
    }


def test_s5_s7_matrix_resource_caps() -> None:
    matrix = build_s5_s7_budgeted_matrix()

    assert matrix.resource_caps["raw"].evaluation_workers == 8
    assert matrix.resource_caps["raw"].concurrent_runs == 80
    assert matrix.resource_caps["union"].evaluation_workers == 8
    assert matrix.resource_caps["union"].concurrent_runs == 60
    assert matrix.resource_caps["external_llm"].evaluation_workers == 3
    assert matrix.resource_caps["external_llm"].concurrent_runs == 20
    assert matrix.resource_caps["gemma4"].evaluation_workers == 3
    assert matrix.resource_caps["gemma4"].concurrent_runs == 8
