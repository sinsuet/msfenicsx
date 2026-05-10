from pathlib import Path

import yaml

from optimizers.benchmark_runner.comparisons import plan_campaign_comparisons
from tests.optimizers.experiment_fixtures import create_mixed_run_root


def test_raw_union_five_seeds_gets_by_seed_and_aggregate(tmp_path: Path, monkeypatch) -> None:
    run_root = create_mixed_run_root(tmp_path, modes=("raw", "union"), seeds=(11, 17, 23, 29, 31))
    calls: list[tuple[tuple[str, ...], str]] = []
    monkeypatch.setattr(
        "optimizers.comparison_artifacts.build_comparison_bundle",
        lambda runs, output, **kwargs: calls.append(
            (tuple(Path(run).parent.parent.name for run in runs), str(output.relative_to(run_root)))
        )
        or {"manifest": {}},
    )
    monkeypatch.setattr(
        "optimizers.benchmark_runner.comparisons.build_campaign_aggregate_bundle",
        lambda payloads, output, method_ids, benchmark_seeds: calls.append(
            (tuple(method_ids), str(output.relative_to(run_root)))
        )
        or {},
    )

    manifest = plan_campaign_comparisons(run_root)

    assert len(manifest["by_seed_paths"]) == 5
    assert manifest["aggregate_path"] == "comparisons/aggregate/raw_vs_union"
    assert any(path == "comparisons/by_seed/seed-11/raw_vs_union" for _, path in calls)
    assert any(path == "comparisons/aggregate/raw_vs_union" for _, path in calls)


def test_single_llm_seed_only_refreshes_three_mode_by_seed(tmp_path: Path, monkeypatch) -> None:
    raw_union_root = create_mixed_run_root(tmp_path, modes=("raw", "union"), seeds=(11, 17, 23, 29, 31))
    llm_root = create_mixed_run_root(tmp_path, modes=("llm-gpt",), seeds=(11,))
    calls: list[str] = []
    monkeypatch.setattr(
        "optimizers.comparison_artifacts.build_comparison_bundle",
        lambda runs, output, **kwargs: calls.append(str(output)) or {"manifest": {}},
    )

    manifest = plan_campaign_comparisons(llm_root, compare_with=[raw_union_root])

    assert any("seed-11/raw_vs_union_vs_llm-gpt" in path for path in calls)
    assert not any("aggregate/raw_vs_union_vs_llm-gpt" in path for path in calls)
    assert manifest["aggregate_path"] is None


def test_nsga2_llm_and_llm_method_ids_share_comparison_identity(tmp_path: Path, monkeypatch) -> None:
    run_root = create_mixed_run_root(tmp_path, modes=("raw", "union", "llm"), seeds=(11, 13))
    seed_11_run_yaml = run_root / "llm" / "seeds" / "seed-11" / "run.yaml"
    seed_13_run_yaml = run_root / "llm" / "seeds" / "seed-13" / "run.yaml"
    for path, method_id in (
        (seed_11_run_yaml, "llm:deepseek_v4_flash"),
        (seed_13_run_yaml, "nsga2_llm:deepseek_v4_flash"),
    ):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
        payload["method_id"] = method_id
        payload["mode"] = "llm"
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    calls: list[tuple[tuple[str, ...], str]] = []
    monkeypatch.setattr(
        "optimizers.comparison_artifacts.build_comparison_bundle",
        lambda runs, output, **kwargs: calls.append(
            (tuple(Path(run).parent.parent.name for run in runs), str(output.relative_to(run_root)))
        )
        or {"manifest": {}},
    )
    monkeypatch.setattr(
        "optimizers.benchmark_runner.comparisons.build_campaign_aggregate_bundle",
        lambda payloads, output, method_ids, benchmark_seeds: calls.append(
            (tuple(method_ids), str(output.relative_to(run_root)))
        )
        or {},
    )

    manifest = plan_campaign_comparisons(run_root)

    assert len(manifest["by_seed_paths"]) == 2
    assert manifest["aggregate_path"] == "comparisons/aggregate/raw_vs_union_vs_llm-deepseek_v4_flash"
    assert any(path == "comparisons/by_seed/seed-11/raw_vs_union_vs_llm-deepseek_v4_flash" for _, path in calls)
    assert any(path == "comparisons/by_seed/seed-13/raw_vs_union_vs_llm-deepseek_v4_flash" for _, path in calls)
    assert any(
        method_ids == ("raw", "union", "llm-deepseek_v4_flash")
        and path == "comparisons/aggregate/raw_vs_union_vs_llm-deepseek_v4_flash"
        for method_ids, path in calls
    )
