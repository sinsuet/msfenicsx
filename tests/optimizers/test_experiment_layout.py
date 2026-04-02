from __future__ import annotations

from datetime import datetime

from optimizers.experiment_layout import (
    allocate_experiment_root,
    build_experiment_manifest,
    initialize_experiment_directories,
)


def test_allocate_experiment_root_uses_template_first_mode_timestamp_layout(tmp_path) -> None:
    root = allocate_experiment_root(
        scenario_runs_root=tmp_path,
        scenario_template_id="s1_typical",
        mode_id="nsga2_union",
        started_at=datetime(2026, 4, 1, 14, 30),
    )

    assert root == (
        tmp_path
        / "s1_typical"
        / "experiments"
        / "nsga2_union__0401_1430"
    )


def test_allocate_experiment_root_appends_sequence_when_same_minute_exists(tmp_path) -> None:
    first = (
        tmp_path
        / "s1_typical"
        / "experiments"
        / "nsga2_union__0401_1430"
    )
    first.mkdir(parents=True)

    second = allocate_experiment_root(
        scenario_runs_root=tmp_path,
        scenario_template_id="s1_typical",
        mode_id="nsga2_union",
        started_at=datetime(2026, 4, 1, 14, 30),
    )

    assert second.name == "nsga2_union__0401_1430__01"


def test_initialize_experiment_directories_creates_expected_single_mode_structure(tmp_path) -> None:
    experiment_root = tmp_path / "s1_typical" / "experiments" / "nsga2_raw__0401_1430"

    initialize_experiment_directories(experiment_root)

    for directory_name in (
        "spec_snapshot",
        "runs",
        "summaries",
        "figures",
        "dashboards",
        "logs",
        "representatives",
    ):
        assert (experiment_root / directory_name).is_dir()


def test_build_experiment_manifest_includes_mode_template_and_seed_index() -> None:
    manifest = build_experiment_manifest(
        scenario_template_id="s1_typical",
        mode_id="nsga2_llm",
        benchmark_seeds=[11, 17],
        optimization_spec_path="scenarios/optimization/s1_typical_llm.yaml",
    )

    assert manifest["scenario_template_id"] == "s1_typical"
    assert manifest["mode_id"] == "nsga2_llm"
    assert manifest["benchmark_seeds"] == [11, 17]
    assert manifest["directories"]["runs"] == "runs"
