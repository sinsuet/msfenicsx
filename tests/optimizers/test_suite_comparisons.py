from __future__ import annotations

from pathlib import Path

from tests.optimizers.experiment_fixtures import create_mixed_run_root


def test_aggregate_bands_align_on_progress_and_generation_axes(tmp_path: Path) -> None:
    from optimizers.comparison_artifacts import (
        _collect_run_payload,
        _hypervolume_metric_bands,
        _progress_metric_bands,
        _suite_seed_run_roots,
    )

    run_root = create_mixed_run_root(tmp_path, modes=("raw", "llm"), seeds=(11, 17))
    seed_runs = _suite_seed_run_roots(run_root)
    grouped_payloads = {
        mode: [_collect_run_payload(seed_runs[seed][mode]) for seed in sorted(seed_runs)]
        for mode in ("raw", "llm")
    }

    progress_bands = _progress_metric_bands(grouped_payloads, key="current_temperature_max")
    hypervolume_bands = _hypervolume_metric_bands(grouped_payloads)

    assert progress_bands["xs"] == [1, 2, 3]
    assert hypervolume_bands["xs"] == [0, 1, 2]


def test_build_suite_comparisons_single_seed_writes_suite_owned_bundle(tmp_path: Path) -> None:
    import json

    import matplotlib

    matplotlib.use("Agg")

    from optimizers.comparison_artifacts import build_suite_comparisons

    run_root = create_mixed_run_root(tmp_path, modes=("raw", "union", "llm"), seeds=(11,))

    manifest = build_suite_comparisons(run_root)
    comparisons_root = run_root / "comparisons"

    assert manifest["comparison_kind"] == "single_seed"
    assert (comparisons_root / "manifest.json").exists()
    comparison_manifest = json.loads((comparisons_root / "manifest.json").read_text(encoding="utf-8"))
    assert "hypervolume_reference_point" in comparison_manifest
    assert (comparisons_root / "analytics" / "summary_rows.json").exists()
    assert (comparisons_root / "figures" / "summary_overview.png").exists()
    assert (comparisons_root / "figures" / "final_layout_comparison.png").exists()
    assert (comparisons_root / "figures" / "temperature_field_comparison.png").exists()
    assert (comparisons_root / "figures" / "gradient_field_comparison.png").exists()
    assert (comparisons_root / "figures" / "progress_dashboard.png").exists()
    assert (comparisons_root / "tables" / "summary_table.csv").exists()
    assert not (run_root / "comparison").exists()
    for mode in ("raw", "union", "llm"):
        assert not (run_root / mode / "seeds" / "seed-11" / "comparisons").exists()


def test_build_suite_comparisons_multi_seed_writes_by_seed_and_aggregate(tmp_path: Path) -> None:
    import json

    import matplotlib

    matplotlib.use("Agg")

    from optimizers.comparison_artifacts import build_suite_comparisons

    run_root = create_mixed_run_root(tmp_path, modes=("raw", "llm"), seeds=(11, 17))

    manifest = build_suite_comparisons(run_root)
    comparisons_root = run_root / "comparisons"

    assert manifest["comparison_kind"] == "multi_seed"
    assert (comparisons_root / "manifest.json").exists()
    assert (comparisons_root / "by_seed" / "seed-11" / "figures" / "summary_overview.png").exists()
    assert (comparisons_root / "by_seed" / "seed-11" / "figures" / "progress_dashboard.png").exists()
    assert (comparisons_root / "by_seed" / "seed-17" / "tables" / "summary_table.csv").exists()
    assert (comparisons_root / "aggregate" / "figures" / "summary_overview.png").exists()
    assert (comparisons_root / "aggregate" / "figures" / "seed_outcome_dashboard.png").exists()
    assert (comparisons_root / "aggregate" / "figures" / "temperature_trace_median_band.png").exists()
    assert (comparisons_root / "aggregate" / "figures" / "gradient_trace_median_band.png").exists()
    assert (comparisons_root / "aggregate" / "figures" / "hypervolume_iqr_comparison.png").exists()
    assert (comparisons_root / "aggregate" / "tables" / "aggregate_mode_summary.csv").exists()
    assert (comparisons_root / "aggregate" / "tables" / "pairwise_win_rate.csv").exists()
    assert (comparisons_root / "aggregate" / "analytics" / "aggregate_mode_summary.json").exists()
    assert (comparisons_root / "aggregate" / "analytics" / "pairwise_win_rate.json").exists()
    aggregate_manifest = json.loads((comparisons_root / "aggregate" / "manifest.json").read_text(encoding="utf-8"))
    assert "hypervolume_reference_point" in aggregate_manifest
