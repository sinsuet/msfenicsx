from __future__ import annotations

from pathlib import Path


def test_render_metric_trace_writes_pdf_and_ignores_failed_sentinels(tmp_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from visualization.figures.trace_series import render_metric_trace

    original_close = plt.close
    output = tmp_path / "temperature_trace.png"
    try:
        plt.close = lambda *args, **kwargs: None
        render_metric_trace(
            series={
                "raw": [
                    {
                        "evaluation_index": 1,
                        "status": "failed",
                        "current_temperature_max": None,
                        "best_temperature_max_so_far": None,
                    },
                    {
                        "evaluation_index": 2,
                        "status": "infeasible",
                        "current_temperature_max": 325.0,
                        "best_temperature_max_so_far": None,
                    },
                    {
                        "evaluation_index": 3,
                        "status": "ok",
                        "current_temperature_max": 320.0,
                        "best_temperature_max_so_far": 320.0,
                    },
                ]
            },
            current_key="current_temperature_max",
            best_key="best_temperature_max_so_far",
            ylabel="Temperature (K)",
            output=output,
        )
        assert output.exists()
        assert (tmp_path / "pdf" / "temperature_trace.pdf").exists()
        axis = plt.gcf().axes[0]
        ymin, ymax = axis.get_ylim()
        assert ymax < 400.0
    finally:
        plt.close = original_close
        plt.close("all")


def test_render_feasible_progress_writes_pdf(tmp_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from visualization.figures.trace_series import render_feasible_progress

    original_close = plt.close
    output = tmp_path / "feasible_progress.png"
    try:
        plt.close = lambda *args, **kwargs: None
        render_feasible_progress(
            series={
                "raw": [
                    {"evaluation_index": 3, "pde_evaluation_index": 1, "feasible_count_so_far": 0, "feasible_rate_so_far": 0.0},
                    {"evaluation_index": 4, "pde_evaluation_index": 2, "feasible_count_so_far": 1, "feasible_rate_so_far": 0.5},
                ],
                "llm": [
                    {"evaluation_index": 5, "pde_evaluation_index": 1, "feasible_count_so_far": 0, "feasible_rate_so_far": 0.0},
                    {"evaluation_index": 6, "pde_evaluation_index": 2, "feasible_count_so_far": 2, "feasible_rate_so_far": 1.0},
                ],
            },
            output=output,
        )

        assert output.exists()
        assert (tmp_path / "pdf" / "feasible_progress.pdf").exists()
        count_axis = plt.gcf().axes[0]
        raw_line = next(line for line in count_axis.lines if line.get_label() == "raw")
        assert list(raw_line.get_xdata()) == [1, 2]
    finally:
        plt.close = original_close
        plt.close("all")
