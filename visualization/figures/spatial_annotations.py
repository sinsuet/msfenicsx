"""Shared helpers for spatial figures, labels, sink ribbons, and info panels."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import numpy as np
from matplotlib import patheffects
from matplotlib.axes import Axes
from matplotlib.patches import Rectangle

from visualization.style.baseline import (
    SPATIAL_BOARD_EDGE,
    SPATIAL_INFO_BG,
    SPATIAL_INFO_EDGE,
    SPATIAL_INFO_TEXT,
    SPATIAL_LABEL_LIGHT_FILL,
    SPATIAL_LABEL_LIGHT_TEXT,
    SPATIAL_LAYOUT_OUTLINE,
    SPATIAL_SINK_COLOR,
    SPATIAL_SINK_EDGE,
)


def component_label_token(component_id: str, *, index: int) -> str:
    match = re.search(r"c(\d+)", component_id.lower())
    if match:
        return f"C{int(match.group(1)):02d}"
    return f"C{index + 1:02d}"


def hide_spatial_axes(ax: Axes, *, width: float, height: float, title: str | None = None) -> None:
    ax.set_xlim(0.0, width)
    ax.set_ylim(0.0, height)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("")
    ax.set_ylabel("")
    if title:
        ax.set_title(title)
    ax.set_axis_off()
    ax.add_patch(
        Rectangle(
            (0.0, 0.0),
            width,
            height,
            fill=False,
            edgecolor=SPATIAL_BOARD_EDGE,
            linewidth=0.9,
            zorder=5,
        )
    )


def draw_component_labels(
    ax: Axes,
    components: Sequence[Mapping[str, Any]],
    *,
    mode: str,
    sample_rgba: Callable[[float, float], Any] | None = None,
) -> None:
    for index, component in enumerate(components):
        outline = np.asarray(component.get("outline", []), dtype=np.float64)
        if outline.ndim != 2 or outline.shape[1] != 2 or outline.size == 0:
            continue
        token = component_label_token(str(component.get("component_id", "")), index=index)
        center = outline.mean(axis=0)
        span_x = float(outline[:, 0].max() - outline[:, 0].min())
        span_y = float(outline[:, 1].max() - outline[:, 1].min())
        rotate_vertical = span_y > span_x * 1.35 and span_x < 0.11
        font_size = 6.3 if min(span_x, span_y) < 0.08 else 7.0

        facecolor = SPATIAL_LABEL_LIGHT_FILL
        text_color = SPATIAL_LABEL_LIGHT_TEXT
        edgecolor = SPATIAL_LAYOUT_OUTLINE

        bbox = {
            "boxstyle": "round,pad=0.18",
            "facecolor": facecolor,
            "edgecolor": edgecolor,
            "linewidth": 0.6,
            "alpha": 0.95,
        }
        path_effects = [patheffects.withStroke(linewidth=0.75, foreground=facecolor)]
        text = ax.text(
            float(center[0]),
            float(center[1]),
            token,
            fontsize=font_size,
            rotation=90 if rotate_vertical else 0,
            rotation_mode="anchor",
            color=text_color,
            ha="center",
            va="center",
            bbox=bbox,
            zorder=7,
        )
        text.set_path_effects(path_effects)


def draw_sink_ribbons(
    ax: Axes,
    line_sinks: Sequence[Mapping[str, Any]],
    *,
    width: float,
    height: float,
) -> None:
    ribbon = max(0.022, min(width, height) * 0.045)
    for sink in line_sinks:
        edge = str(sink.get("edge", ""))
        if edge == "top":
            start = float(sink.get("start_x", 0.0))
            extent = max(0.0, float(sink.get("end_x", start)) - start)
            rect = Rectangle(
                (start, height - ribbon),
                extent,
                ribbon,
                facecolor=SPATIAL_SINK_COLOR,
                edgecolor=SPATIAL_SINK_EDGE,
                linewidth=0.9,
                zorder=6,
            )
            ax.add_patch(rect)
            if extent >= 0.12:
                ax.text(
                    start + extent / 2.0,
                    height - ribbon / 2.0,
                    "SINK",
                    fontsize=6.2,
                    color=SPATIAL_SINK_EDGE,
                    fontweight="semibold",
                    ha="center",
                    va="center",
                    zorder=7,
                )
        elif edge == "bottom":
            start = float(sink.get("start_x", 0.0))
            extent = max(0.0, float(sink.get("end_x", start)) - start)
            rect = Rectangle(
                (start, 0.0),
                extent,
                ribbon,
                facecolor=SPATIAL_SINK_COLOR,
                edgecolor=SPATIAL_SINK_EDGE,
                linewidth=0.9,
                zorder=6,
            )
            ax.add_patch(rect)
        elif edge == "left":
            start = float(sink.get("start_y", 0.0))
            extent = max(0.0, float(sink.get("end_y", start)) - start)
            rect = Rectangle(
                (0.0, start),
                ribbon,
                extent,
                facecolor=SPATIAL_SINK_COLOR,
                edgecolor=SPATIAL_SINK_EDGE,
                linewidth=0.9,
                zorder=6,
            )
            ax.add_patch(rect)
        elif edge == "right":
            start = float(sink.get("start_y", 0.0))
            extent = max(0.0, float(sink.get("end_y", start)) - start)
            rect = Rectangle(
                (width - ribbon, start),
                ribbon,
                extent,
                facecolor=SPATIAL_SINK_COLOR,
                edgecolor=SPATIAL_SINK_EDGE,
                linewidth=0.9,
                zorder=6,
            )
            ax.add_patch(rect)


def draw_metadata_panel(ax: Axes, metadata: Mapping[str, Any]) -> None:
    ax.cla()
    ax.set_axis_off()
    ax.add_patch(
        Rectangle(
            (0.0, 0.0),
            1.0,
            1.0,
            transform=ax.transAxes,
            facecolor=SPATIAL_INFO_BG,
            edgecolor=SPATIAL_INFO_EDGE,
            linewidth=0.9,
            zorder=1,
        )
    )
    y_cursor = 0.92
    for key, value in metadata.items():
        if value in (None, "", []):
            continue
        ax.text(
            0.08,
            y_cursor,
            str(key),
            transform=ax.transAxes,
            fontsize=6.2,
            fontweight="semibold",
            color=SPATIAL_INFO_TEXT,
            ha="left",
            va="top",
            zorder=2,
        )
        ax.text(
            0.08,
            y_cursor - 0.055,
            str(value),
            transform=ax.transAxes,
            fontsize=7.0,
            color=SPATIAL_INFO_TEXT,
            ha="left",
            va="top",
            zorder=2,
        )
        y_cursor -= 0.145
