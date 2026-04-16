# tests/optimizers/test_compare_runs.py
"""compare-runs builds Pareto overlay + summary table across 2+ runs."""

from __future__ import annotations

import json
from pathlib import Path


def _seed_run(run_root: Path, label: str) -> None:
    (run_root / "traces").mkdir(parents=True, exist_ok=True)
    (run_root / "traces" / "evaluation_events.jsonl").write_text(
        "\n".join(
            json.dumps(
                {
                    "decision_id": None,
                    "generation": g,
                    "eval_index": g,
                    "individual_id": f"{label}-g{g}",
                    "objectives": {
                        "temperature_max": 320.0 - g,
                        "temperature_gradient_rms": 3.0 - 0.1 * g,
                    },
                    "constraints": {"total_radiator_span": 0.5, "radiator_span_max": 0.8, "violation": 0.0},
                    "status": "ok",
                    "timing": {"cheap_ms": 1.0, "solve_ms": 800.0},
                }
            )
            for g in range(3)
        )
        + "\n",
        encoding="utf-8",
    )


def test_compare_runs_writes_overlay_and_summary(tmp_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")

    from optimizers.compare_runs import compare_runs

    run_a = tmp_path / "0416_2030__raw"
    run_b = tmp_path / "0416_2035__llm"
    _seed_run(run_a, "raw")
    _seed_run(run_b, "llm")

    output = tmp_path / "comparisons" / "0416_2100__raw_vs_llm"
    compare_runs(runs=[run_a, run_b], output=output)

    assert (output / "pareto_overlay.png").exists()
    assert (output / "pareto_overlay.pdf").exists()
    assert (output / "summary_table.csv").exists()
    assert (output / "inputs.yaml").exists()
