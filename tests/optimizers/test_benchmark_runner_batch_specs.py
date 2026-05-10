from optimizers.benchmark_runner.specs import load_campaigns_from_batch_spec


def test_s5_raw_union_budgeted_batch_spec() -> None:
    campaign = load_campaigns_from_batch_spec("scenarios/batches/s5_raw_union_budgeted.yaml")[0]
    assert campaign.scenario_id == "s5_aggressive15"
    assert len(campaign.leaves) == 10
    assert {leaf.population_size for leaf in campaign.leaves} == {40}
    assert {leaf.num_generations for leaf in campaign.leaves} == {32}
    assert {leaf.evaluation_workers for leaf in campaign.leaves} == {32}


def test_s6_raw_union_budgeted_batch_spec() -> None:
    campaign = load_campaigns_from_batch_spec("scenarios/batches/s6_raw_union_budgeted.yaml")[0]
    assert campaign.scenario_id == "s6_aggressive20"
    assert len(campaign.leaves) == 10
    assert {leaf.population_size for leaf in campaign.leaves} == {56}
    assert {leaf.num_generations for leaf in campaign.leaves} == {36}


def test_s5_s6_combined_batch_spec() -> None:
    campaigns = load_campaigns_from_batch_spec("scenarios/batches/s5_s6_raw_union_budgeted.yaml")
    assert [campaign.scenario_id for campaign in campaigns] == ["s5_aggressive15", "s6_aggressive20"]
    assert [len(campaign.leaves) for campaign in campaigns] == [10, 10]


def test_final_main_raw_vs_deepseek_llm_batch_specs() -> None:
    cases = [
        ("scenarios/batches/s4_main_raw_llm_deepseek_budgeted.yaml", "s4_aggressive10", 10, 32, 16),
        ("scenarios/batches/s5_main_raw_llm_deepseek_budgeted.yaml", "s5_aggressive15", 10, 40, 32),
        ("scenarios/batches/s6_main_raw_llm_deepseek_budgeted.yaml", "s6_aggressive20", 10, 56, 36),
    ]

    for path, scenario_id, leaf_count, population_size, num_generations in cases:
        campaign = load_campaigns_from_batch_spec(path)[0]
        assert campaign.scenario_id == scenario_id
        assert len(campaign.leaves) == leaf_count
        assert {leaf.population_size for leaf in campaign.leaves} == {population_size}
        assert {leaf.num_generations for leaf in campaign.leaves} == {num_generations}
        assert {leaf.llm_profile for leaf in campaign.leaves if leaf.mode == "llm"} == {"deepseek_v4_flash"}


def test_final_ablation_and_baseline_batch_specs() -> None:
    semantic = load_campaigns_from_batch_spec("scenarios/batches/s4_semantic_ablation_budgeted.yaml")[0]
    mechanism = load_campaigns_from_batch_spec("scenarios/batches/s5_mechanism_llm_direct_vs_ours_budgeted.yaml")[0]
    sensitivity = load_campaigns_from_batch_spec("scenarios/batches/s5_model_sensitivity_seed11.yaml")[0]
    algorithm = load_campaigns_from_batch_spec("scenarios/batches/s5_algorithm_baseline_raw_budgeted.yaml")[0]

    assert semantic.scenario_id == "s4_aggressive10"
    assert {leaf.method_id for leaf in semantic.leaves} == {
        "nsga2_raw",
        "nsga2_union",
        "nsga2_llm:deepseek_v4_flash",
    }
    assert len(semantic.leaves) == 15

    assert mechanism.scenario_id == "s5_aggressive15"
    assert {leaf.method_id for leaf in mechanism.leaves} == {
        "llm_direct:deepseek_v4_flash",
        "nsga2_llm:deepseek_v4_flash",
    }
    assert len(mechanism.leaves) == 10

    assert sensitivity.scenario_id == "s5_aggressive15"
    assert [leaf.benchmark_seed for leaf in sensitivity.leaves] == [11, 11, 11, 11, 11]
    assert {leaf.llm_profile for leaf in sensitivity.leaves} == {
        "deepseek_v4_flash",
        "qwen3_6_plus",
        "kimi_k2_5",
        "gpt",
        "mimo_v2_5",
    }

    assert algorithm.scenario_id == "s5_aggressive15"
    assert {leaf.method_id for leaf in algorithm.leaves} == {"nsga2_raw", "spea2_raw", "moead_raw"}
    assert len(algorithm.leaves) == 15
