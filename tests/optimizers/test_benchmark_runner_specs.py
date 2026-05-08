from pathlib import Path

import yaml

from optimizers.benchmark_runner.specs import (
    build_single_leaf_campaign,
    load_campaigns_from_batch_spec,
)


def test_single_leaf_llm_campaign_derives_method_and_paths(tmp_path: Path) -> None:
    campaign = build_single_leaf_campaign(
        optimization_spec=Path("scenarios/optimization/s5_aggressive15_llm.yaml"),
        mode="llm",
        llm_profile="gpt",
        benchmark_seed=11,
        algorithm_seed=1011,
        population_size=40,
        num_generations=32,
        evaluation_workers=16,
        scenario_runs_root=tmp_path / "scenario_runs",
        campaign_id="s5_budgeted_main",
        compare_with=[tmp_path / "scenario_runs/s5_aggressive15/0508_2300__raw_union"],
    )

    assert campaign.campaign_id == "s5_budgeted_main"
    assert campaign.scenario_runs_root == tmp_path / "scenario_runs"
    assert len(campaign.leaves) == 1
    leaf = campaign.leaves[0]
    assert leaf.method_id == "llm:gpt"
    assert leaf.method_slug == "llm-gpt"
    assert leaf.mode == "llm"
    assert leaf.llm_profile == "gpt"
    assert leaf.benchmark_seed == 11
    assert leaf.algorithm_seed == 1011
    assert leaf.population_size == 40
    assert leaf.num_generations == 32
    assert leaf.evaluation_workers == 16
    assert campaign.compare_with == (tmp_path / "scenario_runs/s5_aggressive15/0508_2300__raw_union",)


def test_batch_spec_expands_methods_by_replicate_seeds(tmp_path: Path) -> None:
    batch_path = tmp_path / "s5_raw_union.yaml"
    batch_path.write_text(
        yaml.safe_dump(
            {
                "campaign_id": "s5_budgeted_main",
                "scenario_runs_root": str(tmp_path / "scenario_runs"),
                "scenario_id": "s5_aggressive15",
                "methods": [
                    {
                        "method_id": "nsga2_raw",
                        "mode": "raw",
                        "optimization_spec": "scenarios/optimization/s5_aggressive15_raw.yaml",
                    },
                    {
                        "method_id": "nsga2_union",
                        "mode": "union",
                        "optimization_spec": "scenarios/optimization/s5_aggressive15_union.yaml",
                    },
                ],
                "replicate_seeds": [11, 17],
                "algorithm_seed_offset": 1000,
                "population_size": 40,
                "num_generations": 32,
                "resource_policy": {
                    "max_concurrent_leaves": 4,
                    "leaf_evaluation_workers": 16,
                },
                "comparison_policy": {"by_seed": True, "aggregate": True},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    campaigns = load_campaigns_from_batch_spec(batch_path)

    assert len(campaigns) == 1
    campaign = campaigns[0]
    assert campaign.scenario_id == "s5_aggressive15"
    assert campaign.resource_policy.max_concurrent_leaves == 4
    assert campaign.resource_policy.leaf_evaluation_workers == 16
    assert [(leaf.method_id, leaf.benchmark_seed, leaf.algorithm_seed) for leaf in campaign.leaves] == [
        ("nsga2_raw", 11, 1011),
        ("nsga2_raw", 17, 1017),
        ("nsga2_union", 11, 1011),
        ("nsga2_union", 17, 1017),
    ]


def test_multi_campaign_batch_wrapper(tmp_path: Path) -> None:
    batch_path = tmp_path / "s5_s6.yaml"
    batch_path.write_text(
        yaml.safe_dump(
            {
                "campaigns": [
                    {
                        "campaign_id": "s5_budgeted_main",
                        "scenario_runs_root": str(tmp_path / "scenario_runs"),
                        "scenario_id": "s5_aggressive15",
                        "methods": [
                            {
                                "method_id": "nsga2_raw",
                                "mode": "raw",
                                "optimization_spec": "scenarios/optimization/s5_aggressive15_raw.yaml",
                            }
                        ],
                        "replicate_seeds": [11],
                        "algorithm_seed_offset": 1000,
                        "population_size": 40,
                        "num_generations": 32,
                    },
                    {
                        "campaign_id": "s6_budgeted_main",
                        "scenario_runs_root": str(tmp_path / "scenario_runs"),
                        "scenario_id": "s6_aggressive20",
                        "methods": [
                            {
                                "method_id": "nsga2_union",
                                "mode": "union",
                                "optimization_spec": "scenarios/optimization/s6_aggressive20_union.yaml",
                            }
                        ],
                        "replicate_seeds": [17],
                        "algorithm_seed_offset": 1000,
                        "population_size": 56,
                        "num_generations": 36,
                    },
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    campaigns = load_campaigns_from_batch_spec(batch_path)

    assert [campaign.scenario_id for campaign in campaigns] == ["s5_aggressive15", "s6_aggressive20"]
    assert [campaign.leaves[0].algorithm_seed for campaign in campaigns] == [1011, 1017]
