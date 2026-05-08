import json
from pathlib import Path

from optimizers.benchmark_runner.postprocess import (
    build_runtime_summary,
    write_runtime_summary,
)


def test_runtime_summary_counts_history_and_wall_time(tmp_path: Path) -> None:
    history = [
        {"solver_skipped": True, "feasible": False, "timing": {"solve_ms": 0}},
        {"solver_skipped": False, "feasible": True, "timing": {"solve_ms": 1200}},
        {"solver_skipped": False, "feasible": False, "timing": {"solve_ms": 800}},
    ]

    summary = build_runtime_summary(
        scenario_id="s5_aggressive15",
        method_id="nsga2_raw",
        mode="raw",
        seed=11,
        population_size=40,
        num_generations=32,
        run_wall_seconds=10.0,
        optimizer_wall_seconds=8.0,
        baseline_wall_seconds=1.0,
        postprocess_wall_seconds=1.0,
        render_wall_seconds=0.5,
        history=history,
    )

    assert summary["run_wall_seconds"] == 10.0
    assert summary["evaluation_count"] == 3
    assert summary["pde_attempt_count"] == 2
    assert summary["cheap_skip_count"] == 1
    assert summary["feasible_count"] == 1
    assert summary["pde_wall_seconds_total"] == 2.0


def test_write_runtime_summary_writes_summaries_dir_and_run_event(tmp_path: Path) -> None:
    seed_root = tmp_path / "seed-11"
    summary = {"scenario_id": "s5_aggressive15", "method_id": "nsga2_raw", "mode": "raw", "seed": 11}

    write_runtime_summary(seed_root, summary)

    assert (seed_root / "summaries" / "runtime_summary.json").exists()
    assert (seed_root / "traces" / "run_events.jsonl").exists()
    payload = json.loads((seed_root / "summaries" / "runtime_summary.json").read_text(encoding="utf-8"))
    assert payload["method_id"] == "nsga2_raw"
