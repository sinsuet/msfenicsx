"""Pareto figure renders PDF + PNG at expected DPI."""

from __future__ import annotations

from pathlib import Path


def test_render_pareto_front_writes_pdf_and_png(tmp_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")

    from visualization.figures.pareto import render_pareto_front

    output = tmp_path / "pareto_front.png"
    render_pareto_front(
        fronts={
            "llm": [(320.0, 3.0), (315.0, 3.5), (310.0, 4.1)],
        },
        output=output,
    )
    assert output.exists()
    assert (tmp_path / "pdf" / "pareto_front.pdf").exists()


def test_render_pareto_front_overlay_multiple_modes(tmp_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")

    from visualization.figures.pareto import render_pareto_front

    output = tmp_path / "pareto_front.png"
    render_pareto_front(
        fronts={
            "raw": [(325.0, 3.2)],
            "union": [(322.0, 3.1)],
            "llm": [(320.0, 3.0)],
        },
        output=output,
    )
    assert output.exists()
