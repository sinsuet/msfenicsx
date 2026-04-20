from __future__ import annotations

from pathlib import Path

import numpy as np


def test_render_layout_snapshot_uses_panel_form_and_keeps_capsule_label_inside(tmp_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from visualization.figures.layout_evolution import render_layout_snapshot

    original_close = plt.close
    output = tmp_path / "layout.png"
    frame = {
        "generation": 2,
        "title": "Final Layout",
        "panel_width": 1.0,
        "panel_height": 0.8,
        "panel_meta": {
            "Scenario": "s2_staged",
            "Algorithm": "NSGA-II",
            "Mode": "llm",
            "Model": "gpt-5.4",
            "Seed": "11",
            "Representative": "Knee",
        },
        "components": [
            {"component_id": "c01-001", "outline": [[0.1, 0.1], [0.3, 0.1], [0.3, 0.3], [0.1, 0.3]]},
            {"component_id": "c02-001", "outline": [[0.5, 0.2], [0.58, 0.2], [0.58, 0.6], [0.5, 0.6]]},
        ],
        "line_sinks": [{"edge": "top", "start_x": 0.2, "end_x": 0.55}],
    }
    try:
        plt.close = lambda *args, **kwargs: None
        render_layout_snapshot(frame=frame, output=output)
        board_ax, info_ax = plt.gcf().axes
        assert not board_ax.axison
        assert not info_ax.axison
        info_texts = [text.get_text() for text in info_ax.texts]
        assert any("NSGA-II" in text for text in info_texts)
        assert any("gpt-5.4" in text for text in info_texts)
        label_positions = {text.get_text(): text.get_position() for text in board_ax.texts}
        assert "SINK" in label_positions
        assert "C01" in label_positions
        assert "C02" in label_positions
        c02_x, c02_y = label_positions["C02"]
        assert 0.5 <= c02_x <= 0.58
        assert 0.2 <= c02_y <= 0.6
    finally:
        plt.close = original_close
        plt.close("all")


def test_temperature_field_uses_uniform_white_label_chips(tmp_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib.colors import to_hex

    from visualization.figures.temperature_field import render_temperature_field

    grid = np.array(
        [
            [314.0, 314.0, 314.0, 314.0],
            [314.0, 318.0, 321.5, 323.0],
            [314.0, 318.0, 321.5, 323.0],
            [314.0, 314.0, 314.0, 314.0],
        ]
    )
    xs = np.linspace(0.0, 1.0, grid.shape[1])
    ys = np.linspace(0.0, 0.8, grid.shape[0])
    layout = {
        "components": [
            {"component_id": "c01-001", "outline": [[0.05, 0.05], [0.25, 0.05], [0.25, 0.25], [0.05, 0.25]]},
            {"component_id": "c02-001", "outline": [[0.7, 0.5], [0.9, 0.5], [0.9, 0.7], [0.7, 0.7]]},
        ],
        "line_sinks": [],
    }

    fig, _, _ = render_temperature_field(
        grid=grid,
        xs=xs,
        ys=ys,
        layout=layout,
        output=tmp_path / "temperature.png",
        return_artifacts=True,
    )

    axis = fig.axes[0]
    label_facecolors = {
        text.get_text(): to_hex(text.get_bbox_patch().get_facecolor(), keep_alpha=False)
        for text in axis.texts
        if text.get_text().startswith("C")
    }
    label_edgecolors = {
        text.get_text(): to_hex(text.get_bbox_patch().get_edgecolor(), keep_alpha=False)
        for text in axis.texts
        if text.get_text().startswith("C")
    }
    assert label_facecolors["C01"] == "#fffdf8"
    assert label_facecolors["C01"] == label_facecolors["C02"]
    assert label_edgecolors["C01"] == label_edgecolors["C02"]


def test_temperature_field_defaults_title_draws_sink_and_keeps_capsule_label_inside(tmp_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")

    from visualization.figures.temperature_field import render_temperature_field

    grid = np.array(
        [
            [314.0, 314.0, 314.0, 314.0],
            [314.0, 318.0, 321.5, 323.0],
            [314.0, 318.0, 321.5, 323.0],
            [314.0, 314.0, 314.0, 314.0],
        ]
    )
    xs = np.linspace(0.0, 1.0, grid.shape[1])
    ys = np.linspace(0.0, 0.8, grid.shape[0])
    layout = {
        "components": [
            {"component_id": "c01-001", "outline": [[0.05, 0.05], [0.25, 0.05], [0.25, 0.25], [0.05, 0.25]]},
            {"component_id": "c02-001", "outline": [[0.7, 0.15], [0.78, 0.15], [0.78, 0.62], [0.7, 0.62]]},
        ],
        "line_sinks": [{"edge": "top", "start_x": 0.2, "end_x": 0.6}],
    }

    fig, _, _ = render_temperature_field(
        grid=grid,
        xs=xs,
        ys=ys,
        layout=layout,
        output=tmp_path / "temperature.png",
        return_artifacts=True,
    )

    axis = fig.axes[0]
    assert axis.get_title() == "Temperature Field"
    label_positions = {text.get_text(): text.get_position() for text in axis.texts}
    assert "SINK" in label_positions
    c02_x, c02_y = label_positions["C02"]
    assert 0.7 <= c02_x <= 0.78
    assert 0.15 <= c02_y <= 0.62
