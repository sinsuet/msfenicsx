from __future__ import annotations

from pathlib import Path


def test_render_objective_progress_writes_pdf_to_subdir_and_labels_both_panels(tmp_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from visualization.figures.progress import render_objective_progress

    original_close = plt.close
    output = tmp_path / "objective_progress.png"
    try:
        plt.close = lambda *args, **kwargs: None
        render_objective_progress(
            series={
                "raw": [
                    {
                        "evaluation_index": 3,
                        "pde_evaluation_index": 1,
                        "best_temperature_max_so_far": 325.0,
                        "best_gradient_rms_so_far": 18.0,
                        "first_feasible_pde_eval_so_far": 1,
                    },
                    {
                        "evaluation_index": 4,
                        "pde_evaluation_index": 2,
                        "best_temperature_max_so_far": 324.0,
                        "best_gradient_rms_so_far": 17.5,
                        "first_feasible_pde_eval_so_far": 1,
                    },
                ],
                "llm": [
                    {
                        "evaluation_index": 5,
                        "pde_evaluation_index": 1,
                        "best_temperature_max_so_far": 326.0,
                        "best_gradient_rms_so_far": 19.0,
                        "first_feasible_pde_eval_so_far": 1,
                    },
                    {
                        "evaluation_index": 6,
                        "pde_evaluation_index": 2,
                        "best_temperature_max_so_far": 323.0,
                        "best_gradient_rms_so_far": 16.0,
                        "first_feasible_pde_eval_so_far": 1,
                    },
                ],
            },
            output=output,
        )
        assert output.exists()
        assert (tmp_path / "pdf" / "objective_progress.pdf").exists()
        figure = plt.gcf()
        axes = figure.axes
        assert len(axes) == 2
        for axis in axes:
            legend = axis.get_legend()
            assert legend is not None
            labels = [text.get_text() for text in legend.get_texts()]
            assert labels == ["raw", "llm"]
        raw_peak_line = next(line for line in axes[0].lines if line.get_label() == "raw")
        assert list(raw_peak_line.get_xdata()) == [1, 2]
    finally:
        plt.close = original_close
        plt.close("all")
