import csv
import json
from pathlib import Path

import pytest

from optimizers import comparison_artifacts


def test_progress_rows_prefers_precomputed_progress_timeline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_root = tmp_path / "run"
    analytics = run_root / "analytics"
    analytics.mkdir(parents=True)
    (run_root / "optimization_result.json").write_text(
        json.dumps(
            {
                "history": [
                    {
                        "evaluation_index": 0,
                        "generation_index": 0,
                        "feasible": True,
                        "objective_values": {
                            "summary.temperature_max": 320.0,
                            "summary.temperature_gradient_rms": 12.0,
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with (analytics / "progress_timeline.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "evaluation_index",
                "generation_index",
                "pde_evaluations_so_far",
                "best_temperature_max_so_far",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "evaluation_index": "7",
                "generation_index": "2",
                "pde_evaluations_so_far": "5",
                "best_temperature_max_so_far": "319.5",
            }
        )

    def fail_recompute(history):
        raise AssertionError("progress timeline should be loaded from analytics sidecar")

    monkeypatch.setattr(comparison_artifacts, "build_progress_timeline", fail_recompute)

    assert comparison_artifacts._progress_rows(run_root) == [
        {
            "evaluation_index": 7,
            "generation_index": 2,
            "pde_evaluations_so_far": 5,
            "best_temperature_max_so_far": 319.5,
        }
    ]


def test_aggregate_mode_summary_includes_igd_statistics() -> None:
    rows = [
        {"mode": "raw", "final_igd": 0.9, "normalized_final_igd": 0.9},
        {"mode": "raw", "final_igd": 0.3, "normalized_final_igd": 0.3},
        {"mode": "llm", "final_igd": 0.0, "normalized_final_igd": 0.0},
        {"mode": "llm", "final_igd": 0.2, "normalized_final_igd": 0.2},
    ]

    summary = {
        row["mode"]: row
        for row in comparison_artifacts._aggregate_mode_summary(rows)
    }

    assert summary["raw"]["final_igd_mean"] == pytest.approx(0.6)
    assert summary["raw"]["final_igd_median"] == pytest.approx(0.6)
    assert summary["raw"]["final_igd_iqr"] == pytest.approx(0.3)
    assert summary["raw"]["normalized_final_igd_mean"] == pytest.approx(0.6)
    assert summary["llm"]["final_igd_mean"] == pytest.approx(0.1)
    assert summary["llm"]["normalized_final_igd_median"] == pytest.approx(0.1)


def test_summary_table_row_displays_igd_metrics() -> None:
    from visualization.figures import comparison_panels

    row = comparison_panels._summary_table_row(
        {
            "mode": "llm",
            "final_hypervolume_mean": 1.5,
            "final_igd_mean": 0.12,
            "normalized_final_igd_mean": 0.08,
        }
    )

    assert row["igd"] == 0.12
    assert row["nigd"] == 0.08
