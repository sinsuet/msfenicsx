# tests/visualization/test_render_assets_fixtures.py
"""End-to-end: synthetic trace bundle → render-assets → asserts all outputs."""

from __future__ import annotations

import json
from pathlib import Path


def _seed_run_bundle(run_root: Path) -> None:
    """Create a tiny run bundle with the minimum traces needed for analytics."""
    traces = run_root / "traces"
    traces.mkdir(parents=True, exist_ok=True)

    (traces / "evaluation_events.jsonl").write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {
                    "decision_id": None,
                    "generation": 0,
                    "eval_index": 0,
                    "individual_id": "g000-i00",
                    "objectives": {"temperature_max": 320.0, "temperature_gradient_rms": 3.0},
                    "constraints": {"total_radiator_span": 0.6, "radiator_span_max": 0.8, "violation": 0.0},
                    "status": "ok",
                    "timing": {"cheap_ms": 1.0, "solve_ms": 800.0},
                },
                {
                    "decision_id": None,
                    "generation": 1,
                    "eval_index": 1,
                    "individual_id": "g001-i00",
                    "objectives": {"temperature_max": 310.0, "temperature_gradient_rms": 2.5},
                    "constraints": {"total_radiator_span": 0.55, "radiator_span_max": 0.8, "violation": 0.0},
                    "status": "ok",
                    "timing": {"cheap_ms": 1.0, "solve_ms": 800.0},
                },
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (traces / "operator_trace.jsonl").write_text(
        json.dumps(
            {
                "decision_id": None,
                "generation": 1,
                "operator_name": "native_sbx_pm",
                "parents": ["g000-i00"],
                "offspring": ["g001-i00"],
                "params_digest": "a" * 40,
                "wall_ms": 1.2,
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_render_assets_produces_required_outputs(tmp_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")

    from optimizers.render_assets import render_run_assets

    run_root = tmp_path / "0416_2030__raw"
    _seed_run_bundle(run_root)

    render_run_assets(run_root, hires=False)

    assert (run_root / "analytics" / "hypervolume.csv").exists()
    assert (run_root / "analytics" / "operator_phase_heatmap.csv").exists()
    assert (run_root / "figures" / "hypervolume_progress.png").exists()
    assert (run_root / "figures" / "hypervolume_progress.pdf").exists()
    assert (run_root / "figures" / "operator_phase_heatmap.png").exists()
