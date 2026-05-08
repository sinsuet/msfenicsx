from optimizers.benchmark_runner.specs import load_campaigns_from_batch_spec


def test_s5_raw_union_budgeted_batch_spec() -> None:
    campaign = load_campaigns_from_batch_spec("scenarios/batches/s5_raw_union_budgeted.yaml")[0]
    assert campaign.scenario_id == "s5_aggressive15"
    assert len(campaign.leaves) == 10
    assert {leaf.population_size for leaf in campaign.leaves} == {40}
    assert {leaf.num_generations for leaf in campaign.leaves} == {32}
    assert {leaf.evaluation_workers for leaf in campaign.leaves} == {16}


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
