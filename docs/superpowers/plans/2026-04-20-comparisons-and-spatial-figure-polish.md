# Comparisons & Spatial Figure Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add automatic suite-owned `comparisons/` output, current-vs-best objective trace figures, panelized spatial figures, and a paper-facing compare bundle that leads with dense summary/mosaic artifacts instead of many low-signal singleton charts.

**Architecture:** Keep the pure new-chain optimizer bundle layout, but extend it in three focused layers: richer telemetry in `optimizers/run_telemetry.py`, panel-aware figure helpers under `visualization/figures/`, and a comparison-orchestration layer that lets `run-benchmark-suite` emit concise `comparisons/` bundles without reviving legacy `comparison/` or HTML pages. Spatial rendering is centralized through shared annotation and layout helpers so layout, temperature, and gradient figures all use the same `C01..C15` labels, explicit sink rendering, and stable composition.

**Tech Stack:** Python 3.11, matplotlib, numpy, PyYAML, pytest, existing optimizer analytics helpers in `optimizers/analytics/`.

**Spec:** [docs/superpowers/specs/2026-04-20-comparisons-and-spatial-figure-polish-design.md](../specs/2026-04-20-comparisons-and-spatial-figure-polish-design.md)

---

## 2026-04-20 Late-Review Amendment

The late review that followed the first draft changed the paper-facing contract in four ways. These bullets override any stale examples later in this plan:

- **Layout figures are publication panels, not bare board tiles.** They must keep labels inside the component body, render the sink as an explicit inset ribbon, and add a compact metadata strip on the right.
- **Field figures require fixed composition.** Titles are mandatory, sink rendering must remain explicit, and the board tile plus colorbar should use a locked layout rather than pure auto-placement.
- **Per-seed compare bundles now lead with five primary artifacts:** `summary_overview`, `final_layout_comparison`, `temperature_field_comparison`, `gradient_field_comparison`, and `progress_dashboard`.
- **`aggregate/` means across-seeds rollup, not “another by-seed folder”.** It exists for multi-seed suites with `N>=2`, stays descriptive for `N=2`, and may add stronger statistics only for `N>=3`.

Implementation should still reuse any lower-level helper charts that are useful internally, but the user-facing contract above is the one to preserve in code, tests, and docs.

- **`layout_evolution` is not per-generation anymore.** It replays best-so-far spatial milestones and preserves neutral `step_<NNN>.png` frame names rather than `gen_<NNN>.png`.
- **Field label chips are single-style.** Use the same white paper chip on all spatial fields; do not switch to dark chips on bright regions.
- **Paper-facing PDE counts mean solver attempts.** Axes, compare tables, and `first_feasible_*` summaries must use the cumulative count of non-baseline evaluations with `solver_skipped == false`, while raw `evaluation_index` remains available only for trace correlation.

### Task 1: Extend Progress Telemetry And Add Trace-Series Figure Helpers

**Files:**
- Modify: `optimizers/run_telemetry.py`
- Create: `visualization/figures/trace_series.py`
- Modify: `tests/optimizers/test_run_telemetry.py`
- Create: `tests/visualization/test_trace_series_figure.py`

- [ ] **Step 1: Write the failing telemetry and figure tests**

```python
# Append to tests/optimizers/test_run_telemetry.py
def test_build_progress_timeline_carries_current_values_and_status() -> None:
    timeline = build_progress_timeline(
        [
            {
                "generation": 1,
                "eval_index": 0,
                "objectives": {"temperature_max": 321.0, "temperature_gradient_rms": 11.5},
                "constraints": {"radiator_span_budget": 0.4},
                "status": "infeasible",
            },
            {
                "generation": 2,
                "eval_index": 1,
                "objectives": {"temperature_max": 309.0, "temperature_gradient_rms": 8.8},
                "constraints": {"radiator_span_budget": 0.0},
                "status": "ok",
            },
        ]
    )

    assert timeline[0]["status"] == "infeasible"
    assert timeline[0]["current_temperature_max"] == 321.0
    assert timeline[0]["current_gradient_rms"] == 11.5
    assert timeline[0]["current_total_constraint_violation"] == 0.4
    assert timeline[1]["status"] == "ok"
    assert timeline[1]["current_temperature_max"] == 309.0
    assert timeline[1]["best_temperature_max_so_far"] == 309.0


def test_build_progress_timeline_sanitizes_failed_sentinel_values() -> None:
    timeline = build_progress_timeline(
        [
            {
                "generation": 1,
                "eval_index": 0,
                "objectives": {"temperature_max": 1.0e12, "temperature_gradient_rms": 1.0e12},
                "constraints": {"radiator_span_budget": 1.0e12},
                "status": "failed",
            }
        ]
    )

    assert timeline[0]["status"] == "failed"
    assert timeline[0]["current_temperature_max"] is None
    assert timeline[0]["current_gradient_rms"] is None
    assert timeline[0]["current_total_constraint_violation"] is None
```

```python
# Create tests/visualization/test_trace_series_figure.py
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

    from visualization.figures.trace_series import render_feasible_progress

    output = tmp_path / "feasible_progress.png"
    render_feasible_progress(
        series={
            "raw": [
                {"evaluation_index": 1, "feasible_count_so_far": 0, "feasible_rate_so_far": 0.0},
                {"evaluation_index": 2, "feasible_count_so_far": 1, "feasible_rate_so_far": 0.5},
            ],
            "llm": [
                {"evaluation_index": 1, "feasible_count_so_far": 0, "feasible_rate_so_far": 0.0},
                {"evaluation_index": 2, "feasible_count_so_far": 2, "feasible_rate_so_far": 1.0},
            ],
        },
        output=output,
    )

    assert output.exists()
    assert (tmp_path / "pdf" / "feasible_progress.pdf").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_run_telemetry.py tests/visualization/test_trace_series_figure.py -v`

Expected:
- `test_run_telemetry.py` fails on missing `current_*` / `status` keys
- `tests/visualization/test_trace_series_figure.py` fails with `ModuleNotFoundError: No module named 'visualization.figures.trace_series'`

- [ ] **Step 3: Implement telemetry extensions and new figure module**

```python
# In optimizers/run_telemetry.py, add helpers near build_progress_timeline
def _sanitize_progress_metric(value: Any, *, status: str) -> float | None:
    if value is None:
        return None
    numeric = float(value)
    if status == "failed" or abs(numeric) >= 1.0e11:
        return None
    return numeric


def _current_objective_metrics(row: Mapping[str, Any], *, status: str) -> tuple[float | None, float | None]:
    objective_values = dict(row.get("objective_values", row.get("objectives", {})))
    peak_value = _extract_objective_value(
        objective_values,
        preferred_keys=("summary.temperature_max", "minimize_peak_temperature"),
        fallback_tokens=("temperature_max", "peak_temperature"),
    )
    gradient_value = _extract_objective_value(
        objective_values,
        preferred_keys=("summary.temperature_gradient_rms", "minimize_temperature_gradient_rms"),
        fallback_tokens=("temperature_gradient_rms", "gradient_rms"),
    )
    return (
        _sanitize_progress_metric(peak_value, status=status),
        _sanitize_progress_metric(gradient_value, status=status),
    )


def _current_total_constraint_violation(row: Mapping[str, Any], *, status: str) -> float | None:
    constraint_values = dict(row.get("constraint_values", row.get("constraints", {})))
    if "violation" in constraint_values:
        return _sanitize_progress_metric(constraint_values["violation"], status=status)
    if "radiator_span_budget" in constraint_values:
        return _sanitize_progress_metric(max(0.0, float(constraint_values["radiator_span_budget"])), status=status)
    numeric_values = [max(0.0, float(value)) for value in constraint_values.values()]
    return _sanitize_progress_metric(sum(numeric_values), status=status) if numeric_values else None
```

```python
# In optimizers/run_telemetry.py, update build_progress_timeline
    for row in ordered_rows:
        status = str(row.get("status", "ok"))
        current_peak, current_gradient = _current_objective_metrics(row, status=status)
        current_violation = _current_total_constraint_violation(row, status=status)
        evaluation_index = int(row.get("evaluation_index", 0))
        total_constraint_violation = float(row.get("total_constraint_violation", current_violation or 0.0))
        feasible = bool(row.get("feasible", False))
        optimizer_evaluation_count += 1
        if best_total_constraint_violation is None:
            best_total_constraint_violation = total_constraint_violation
        else:
            best_total_constraint_violation = min(best_total_constraint_violation, total_constraint_violation)
        if feasible:
            feasible_count += 1
            feasible_prefix.append(row)
            if first_feasible_eval is None:
                first_feasible_eval = evaluation_index
            if current_peak is not None:
                best_temperature_max = current_peak if best_temperature_max is None else min(best_temperature_max, current_peak)
            if current_gradient is not None:
                best_gradient_rms = current_gradient if best_gradient_rms is None else min(best_gradient_rms, current_gradient)
        pareto_size = len(_pareto_front(feasible_prefix, objective_definitions)) if feasible_prefix else 0
        timeline.append(
            {
                "evaluation_index": evaluation_index,
                "generation_index": int(row.get("generation_index", 0)),
                "status": status,
                "current_temperature_max": current_peak,
                "current_gradient_rms": current_gradient,
                "current_total_constraint_violation": current_violation,
                "budget_fraction": float(optimizer_evaluation_count / float(max(1, len(ordered_rows)))),
                "feasible": feasible,
                "feasible_count_so_far": feasible_count,
                "feasible_rate_so_far": float(feasible_count / float(max(1, optimizer_evaluation_count))),
                "first_feasible_eval_so_far": first_feasible_eval,
                "pareto_size_so_far": pareto_size,
                "best_temperature_max_so_far": best_temperature_max,
                "best_gradient_rms_so_far": best_gradient_rms,
                "best_total_constraint_violation_so_far": best_total_constraint_violation,
            }
        )
```

```python
# Create visualization/figures/trace_series.py
"""Current-vs-best trace figures and feasible-progress comparisons."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from visualization.figures._outputs import ensure_output_parent, paired_pdf_path
from visualization.style.baseline import DPI_DEFAULT, DPI_HIRES, PALETTE_CATEGORICAL, apply_baseline


def render_metric_trace(
    *,
    series: Mapping[str, Sequence[Mapping[str, Any]]],
    current_key: str,
    best_key: str,
    ylabel: str,
    output: Path,
    hires: bool = False,
) -> None:
    apply_baseline()
    fig, ax = plt.subplots(figsize=(3.6, 2.6))
    for idx, (label, rows) in enumerate(series.items()):
        color = PALETTE_CATEGORICAL[(idx + 1) % len(PALETTE_CATEGORICAL)]
        current_points = [
            (int(row["evaluation_index"]), float(row[current_key]))
            for row in rows
            if row.get(current_key) is not None
        ]
        best_points = [
            (int(row["evaluation_index"]), float(row[best_key]))
            for row in rows
            if row.get(best_key) is not None
        ]
        failed_xs = [int(row["evaluation_index"]) for row in rows if str(row.get("status", "")) == "failed"]
        if current_points:
            ax.plot(
                [item[0] for item in current_points],
                [item[1] for item in current_points],
                color=color,
                alpha=0.28,
                linewidth=0.8,
            )
            ax.scatter(
                [item[0] for item in current_points],
                [item[1] for item in current_points],
                color=color,
                alpha=0.35,
                s=8.0,
            )
        if best_points:
            ax.step(
                [item[0] for item in best_points],
                [item[1] for item in best_points],
                where="post",
                color=color,
                linewidth=1.25,
                label=label,
            )
        if failed_xs:
            ymin = ax.get_ylim()[0] if ax.lines else 0.0
            ax.scatter(failed_xs, [ymin] * len(failed_xs), marker="x", color=color, s=10.0, alpha=0.6)
    ax.set_xlabel("PDE evaluations")
    ax.set_ylabel(ylabel)
    if len(series) > 1:
        ax.legend()
    _save_trace_figure(fig, output, hires=hires)


def render_feasible_progress(
    *,
    series: Mapping[str, Sequence[Mapping[str, Any]]],
    output: Path,
    hires: bool = False,
) -> None:
    apply_baseline()
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.6))
    count_ax, rate_ax = axes
    for idx, (label, rows) in enumerate(series.items()):
        color = PALETTE_CATEGORICAL[(idx + 1) % len(PALETTE_CATEGORICAL)]
        xs = [int(row["evaluation_index"]) for row in rows]
        count_ax.step(xs, [int(row["feasible_count_so_far"]) for row in rows], where="post", color=color, label=label)
        rate_ax.step(xs, [float(row["feasible_rate_so_far"]) for row in rows], where="post", color=color, label=label)
    count_ax.set_xlabel("PDE evaluations")
    count_ax.set_ylabel("Feasible count")
    rate_ax.set_xlabel("PDE evaluations")
    rate_ax.set_ylabel("Feasible rate")
    if len(series) > 1:
        count_ax.legend()
        rate_ax.legend()
    _save_trace_figure(fig, output, hires=hires)


def render_metric_band_comparison(
    *,
    xs: Sequence[int],
    bands: Mapping[str, Mapping[str, Sequence[float]]],
    ylabel: str,
    output: Path,
    hires: bool = False,
) -> None:
    apply_baseline()
    fig, ax = plt.subplots(figsize=(3.6, 2.6))
    x_values = np.asarray(xs)
    for idx, (label, payload) in enumerate(bands.items()):
        color = PALETTE_CATEGORICAL[(idx + 1) % len(PALETTE_CATEGORICAL)]
        ax.fill_between(x_values, payload["p25"], payload["p75"], color=color, alpha=0.18, linewidth=0)
        ax.plot(x_values, payload["median"], color=color, linewidth=1.25, label=label)
    ax.set_xlabel("PDE evaluations")
    ax.set_ylabel(ylabel)
    if len(bands) > 1:
        ax.legend()
    _save_trace_figure(fig, output, hires=hires)


def render_metric_boxplot(
    *,
    values_by_mode: Mapping[str, Sequence[float]],
    ylabel: str,
    output: Path,
    hires: bool = False,
) -> None:
    apply_baseline()
    fig, ax = plt.subplots(figsize=(3.6, 2.8))
    labels = [label for label, values in values_by_mode.items() if values]
    datasets = [list(values_by_mode[label]) for label in labels]
    ax.boxplot(datasets, labels=labels, patch_artist=True)
    ax.set_ylabel(ylabel)
    _save_trace_figure(fig, output, hires=hires)


def render_dual_metric_boxplot(
    *,
    left_values_by_mode: Mapping[str, Sequence[float]],
    right_values_by_mode: Mapping[str, Sequence[float]],
    left_ylabel: str,
    right_ylabel: str,
    output: Path,
    hires: bool = False,
) -> None:
    apply_baseline()
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.8))
    left_labels = [label for label, values in left_values_by_mode.items() if values]
    right_labels = [label for label, values in right_values_by_mode.items() if values]
    axes[0].boxplot([list(left_values_by_mode[label]) for label in left_labels], labels=left_labels, patch_artist=True)
    axes[0].set_ylabel(left_ylabel)
    axes[1].boxplot([list(right_values_by_mode[label]) for label in right_labels], labels=right_labels, patch_artist=True)
    axes[1].set_ylabel(right_ylabel)
    _save_trace_figure(fig, output, hires=hires)


def _save_trace_figure(fig: Any, output: Path, *, hires: bool) -> None:
    output = ensure_output_parent(Path(output))
    fig.savefig(output, dpi=DPI_HIRES if hires else DPI_DEFAULT)
    if output.suffix.lower() == ".png":
        pdf_path = paired_pdf_path(output)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(pdf_path)
    plt.close(fig)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_run_telemetry.py tests/visualization/test_trace_series_figure.py -v`

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add optimizers/run_telemetry.py visualization/figures/trace_series.py tests/optimizers/test_run_telemetry.py tests/visualization/test_trace_series_figure.py
git commit -m "feat(viz): add current-vs-best trace telemetry"
```

### Task 2: Add Shared Spatial Annotation Helpers And Upgrade Layout/Field Figures To Panel Form

**Files:**
- Modify: `visualization/style/baseline.py`
- Create: `visualization/figures/spatial_annotations.py`
- Modify: `visualization/figures/layout_evolution.py`
- Modify: `visualization/figures/temperature_field.py`
- Modify: `visualization/figures/gradient_field.py`
- Create: `tests/visualization/test_spatial_figure_contract.py`

- [ ] **Step 1: Write the failing spatial-figure tests**

```python
# Create tests/visualization/test_spatial_figure_contract.py
from __future__ import annotations

from pathlib import Path

import numpy as np


def test_render_layout_snapshot_hides_axes_and_draws_component_labels(tmp_path: Path) -> None:
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
        "components": [
            {"component_id": "c01-001", "outline": [[0.1, 0.1], [0.3, 0.1], [0.3, 0.3], [0.1, 0.3]]},
            {"component_id": "c02-001", "outline": [[0.5, 0.2], [0.58, 0.2], [0.58, 0.6], [0.5, 0.6]]},
        ],
        "line_sinks": [],
    }
    try:
        plt.close = lambda *args, **kwargs: None
        render_layout_snapshot(frame=frame, output=output)
        axis = plt.gcf().axes[0]
        assert not axis.axison
        labels = [text.get_text() for text in axis.texts]
        assert "C01" in labels
        assert "C02" in labels
    finally:
        plt.close = original_close
        plt.close("all")


def test_temperature_field_uses_contrast_adaptive_label_chips(tmp_path: Path) -> None:
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
    label_styles = {text.get_text(): to_hex(text.get_bbox_patch().get_facecolor(), keep_alpha=False) for text in axis.texts}
    assert label_styles["C01"] != label_styles["C02"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n msfenicsx pytest tests/visualization/test_spatial_figure_contract.py -v`

Expected:
- `layout snapshot` test fails because the axis is still on and no `C01` labels exist
- `temperature field` test fails because no label chips are rendered

- [ ] **Step 3: Implement shared annotation helpers and update the spatial figure modules**

```python
# In visualization/style/baseline.py, add constants
SPATIAL_BOARD_EDGE: str = "#1A1A1A"
SPATIAL_LAYOUT_OUTLINE: str = "#2A2A2A"
SPATIAL_FIELD_OUTLINE: str = "#F7F7F4"
SPATIAL_SINK_COLOR: str = "#00A9B7"
SPATIAL_LABEL_LIGHT_FILL: str = "#FFFDF8"
SPATIAL_LABEL_LIGHT_TEXT: str = "#111111"
SPATIAL_LABEL_DARK_FILL: str = "#1B1B1B"
SPATIAL_LABEL_DARK_TEXT: str = "#FFFDF8"
```

```python
# Create visualization/figures/spatial_annotations.py
"""Shared helpers for component labels and clean spatial axes."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, Callable

import numpy as np
from matplotlib.axes import Axes
from matplotlib import patheffects

from visualization.style.baseline import (
    SPATIAL_BOARD_EDGE,
    SPATIAL_FIELD_OUTLINE,
    SPATIAL_LABEL_DARK_FILL,
    SPATIAL_LABEL_DARK_TEXT,
    SPATIAL_LABEL_LIGHT_FILL,
    SPATIAL_LABEL_LIGHT_TEXT,
    SPATIAL_LAYOUT_OUTLINE,
    SPATIAL_SINK_COLOR,
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
    ax.set_frame_on(True)
    ax.axison = False
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.9)
        spine.set_edgecolor(SPATIAL_BOARD_EDGE)
    if title:
        ax.set_title(title)


def draw_component_labels(
    ax: Axes,
    components: Sequence[Mapping[str, Any]],
    *,
    mode: str,
    sample_rgba: Callable[[float, float], Any] | None = None,
) -> None:
    for index, component in enumerate(components):
        outline = np.asarray(component.get("outline", []), dtype=np.float64)
        if outline.ndim != 2 or outline.shape[1] != 2:
            continue
        token = component_label_token(str(component.get("component_id", "")), index=index)
        center = outline.mean(axis=0)
        span_x = float(outline[:, 0].max() - outline[:, 0].min())
        span_y = float(outline[:, 1].max() - outline[:, 1].min())
        use_callout = min(span_x, span_y) < 0.07
        if mode == "field" and sample_rgba is not None:
            rgba = sample_rgba(float(center[0]), float(center[1]))
            luminance = 0.2126 * rgba[0] + 0.7152 * rgba[1] + 0.0722 * rgba[2]
            if luminance > 0.62:
                bbox = {"boxstyle": "round,pad=0.22", "facecolor": SPATIAL_LABEL_DARK_FILL, "edgecolor": SPATIAL_LABEL_DARK_TEXT, "linewidth": 0.6, "alpha": 0.92}
                text_color = SPATIAL_LABEL_DARK_TEXT
                halo = SPATIAL_LABEL_DARK_FILL
            else:
                bbox = {"boxstyle": "round,pad=0.22", "facecolor": SPATIAL_LABEL_LIGHT_FILL, "edgecolor": SPATIAL_LABEL_LIGHT_TEXT, "linewidth": 0.6, "alpha": 0.92}
                text_color = SPATIAL_LABEL_LIGHT_TEXT
                halo = SPATIAL_LABEL_LIGHT_FILL
        else:
            bbox = {"boxstyle": "round,pad=0.16", "facecolor": SPATIAL_LABEL_LIGHT_FILL, "edgecolor": SPATIAL_LABEL_LIGHT_TEXT, "linewidth": 0.5, "alpha": 0.9}
            text_color = SPATIAL_LABEL_LIGHT_TEXT
            halo = SPATIAL_LABEL_LIGHT_FILL
        if use_callout:
            target = (float(center[0] + 0.05), float(center[1] + 0.03))
            ax.annotate(token, xy=center, xytext=target, fontsize=7, color=text_color, ha="center", va="center", bbox=bbox, arrowprops={"arrowstyle": "-", "linewidth": 0.5, "color": text_color})
        else:
            text = ax.text(float(center[0]), float(center[1]), token, fontsize=7, color=text_color, ha="center", va="center", bbox=bbox)
            text.set_path_effects([patheffects.withStroke(linewidth=0.8, foreground=halo)])
```

```python
# In visualization/figures/layout_evolution.py, replace _draw_layout_frame with
from visualization.figures.spatial_annotations import draw_component_labels, hide_spatial_axes
from visualization.style.baseline import SPATIAL_LAYOUT_OUTLINE, SPATIAL_SINK_COLOR


def _draw_layout_frame(ax, frame: dict) -> None:
    ax.cla()
    width = float(frame.get("panel_width", 1.0))
    height = float(frame.get("panel_height", 1.0))
    title = str(frame.get("title") or f"Generation {int(frame['generation'])}")
    hide_spatial_axes(ax, width=width, height=height, title=title)
    for idx, comp in enumerate(frame.get("components", [])):
        outline = comp.get("outline")
        if not outline:
            continue
        patch = PolygonPatch(
            outline,
            closed=True,
            facecolor=PALETTE_CATEGORICAL[(idx + 1) % len(PALETTE_CATEGORICAL)],
            edgecolor=SPATIAL_LAYOUT_OUTLINE,
            linewidth=0.7,
            alpha=0.82,
        )
        ax.add_patch(patch)
    draw_component_labels(ax, frame.get("components", []), mode="layout")
    for sink in frame.get("line_sinks", []):
        edge = str(sink.get("edge", ""))
        if edge == "top":
            ax.plot([float(sink.get("start_x", 0.0)), float(sink.get("end_x", 0.0))], [height, height], color=SPATIAL_SINK_COLOR, linewidth=1.2)
        elif edge == "bottom":
            ax.plot([float(sink.get("start_x", 0.0)), float(sink.get("end_x", 0.0))], [0.0, 0.0], color=SPATIAL_SINK_COLOR, linewidth=1.2)
        elif edge == "left":
            ax.plot([0.0, 0.0], [float(sink.get("start_y", 0.0)), float(sink.get("end_y", 0.0))], color=SPATIAL_SINK_COLOR, linewidth=1.2)
        elif edge == "right":
            ax.plot([width, width], [float(sink.get("start_y", 0.0)), float(sink.get("end_y", 0.0))], color=SPATIAL_SINK_COLOR, linewidth=1.2)
```

```python
# In visualization/figures/temperature_field.py, extend the signature and render body
from matplotlib.colors import Normalize

from visualization.figures.spatial_annotations import draw_component_labels, hide_spatial_axes
from visualization.style.baseline import COLORMAP_TEMPERATURE

def render_temperature_field(
    *,
    grid: np.ndarray,
    xs: np.ndarray,
    ys: np.ndarray,
    output: Path,
    layout: dict[str, Any] | None = None,
    hotspot: dict[str, Any] | None = None,
    title: str | None = None,
    hires: bool = False,
    return_artifacts: bool = False,
) -> tuple[Any, Any, Any] | None:
    apply_baseline()
    shading = "gouraud" if hires else "auto"
    fig, ax = plt.subplots(figsize=(3.5, 3.5))
    im = ax.pcolormesh(xs, ys, grid, cmap=COLORMAP_TEMPERATURE, shading=shading)
    cbar = fig.colorbar(im, ax=ax, shrink=0.85)
    cbar.set_label("Temperature (K)")
    hide_spatial_axes(ax, width=float(xs.max()), height=float(ys.max()), title=title or "Temperature Field")
    _overlay_layout(ax, layout)
    if layout:
        norm = Normalize(vmin=float(np.nanmin(grid)), vmax=float(np.nanmax(grid)))

        def _sample_rgba(x_value: float, y_value: float):
            col_index = int(np.abs(xs - x_value).argmin())
            row_index = int(np.abs(ys - y_value).argmin())
            return im.cmap(norm(grid[row_index, col_index]))

        draw_component_labels(ax, layout.get("components", []), mode="field", sample_rgba=_sample_rgba)
    if hotspot:
        ax.plot([float(hotspot["x"])], [float(hotspot["y"])], marker="x", markersize=4.0, markeredgewidth=0.9, color="white")
    output = ensure_output_parent(Path(output))
    fig.savefig(output, dpi=DPI_FIELD_HIRES if hires else DPI_DEFAULT)
    if output.suffix.lower() == ".png":
        pdf_path = paired_pdf_path(output)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(pdf_path)
    if return_artifacts:
        return fig, im, cbar
    plt.close(fig)
    return None
```

```python
# In visualization/figures/gradient_field.py, mirror the same signature + render contract
from matplotlib.colors import Normalize

from visualization.figures.spatial_annotations import draw_component_labels, hide_spatial_axes

def render_gradient_field(
    *,
    grid: np.ndarray,
    xs: np.ndarray,
    ys: np.ndarray,
    output: Path,
    layout: dict[str, Any] | None = None,
    title: str | None = None,
    hires: bool = False,
) -> None:
    apply_baseline()
    shading = "gouraud" if hires else "auto"
    fig, ax = plt.subplots(figsize=(3.5, 3.5))
    im = ax.pcolormesh(xs, ys, grid, cmap=COLORMAP_GRADIENT, shading=shading)
    cbar = fig.colorbar(im, ax=ax, shrink=0.85)
    cbar.set_label(r"$|\\nabla T|$ (K/m)")
    hide_spatial_axes(ax, width=float(xs.max()), height=float(ys.max()), title=title or "Gradient Field")
    _overlay_layout(ax, layout)
    if layout:
        norm = Normalize(vmin=float(np.nanmin(grid)), vmax=float(np.nanmax(grid)))

        def _sample_rgba(x_value: float, y_value: float):
            col_index = int(np.abs(xs - x_value).argmin())
            row_index = int(np.abs(ys - y_value).argmin())
            return im.cmap(norm(grid[row_index, col_index]))

        draw_component_labels(ax, layout.get("components", []), mode="field", sample_rgba=_sample_rgba)
    output = ensure_output_parent(Path(output))
    fig.savefig(output, dpi=DPI_FIELD_HIRES if hires else DPI_DEFAULT)
    if output.suffix.lower() == ".png":
        pdf_path = paired_pdf_path(output)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(pdf_path)
    plt.close(fig)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n msfenicsx pytest tests/visualization/test_heatfield_orientation.py tests/visualization/test_spatial_figure_contract.py -v`

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add visualization/style/baseline.py visualization/figures/spatial_annotations.py visualization/figures/layout_evolution.py visualization/figures/temperature_field.py visualization/figures/gradient_field.py tests/visualization/test_spatial_figure_contract.py
git commit -m "feat(viz): polish spatial figure labels and axis-free layout"
```

### Task 3: Wire The New Trace And Panel Contract Into `render-assets`

**Files:**
- Modify: `optimizers/render_assets.py`
- Modify: `tests/visualization/test_render_assets_fixtures.py`

- [ ] **Step 1: Write the failing render-assets expectations**

```python
# In tests/visualization/test_render_assets_fixtures.py, extend the existing end-to-end assertion block
    assert (run_root / "figures" / "temperature_trace.png").exists()
    assert (run_root / "figures" / "gradient_trace.png").exists()
    assert (run_root / "figures" / "constraint_violation_progress.png").exists()
    assert (run_root / "figures" / "pdf" / "temperature_trace.pdf").exists()
    assert (run_root / "figures" / "pdf" / "gradient_trace.pdf").exists()
    assert (run_root / "figures" / "pdf" / "constraint_violation_progress.pdf").exists()
```

- [ ] **Step 2: Run the render-assets test to verify it fails**

Run: `conda run -n msfenicsx pytest tests/visualization/test_render_assets_fixtures.py -v`

Expected: FAIL on the missing new trace figure files.

- [ ] **Step 3: Implement the render-assets wiring**

```python
# In optimizers/render_assets.py, extend the progress figure block
from visualization.figures.trace_series import render_metric_trace

mode_label = _mode_label(run_root)
if optimization_result:
    progress_rows = build_progress_timeline(list(optimization_result.get("history", [])))
    _write_progress_timeline_csv(analytics / "progress_timeline.csv", progress_rows)
    if progress_rows:
        render_objective_progress(
            series={mode_label: progress_rows},
            output=figures / "objective_progress.png",
            hires=hires,
        )
        render_metric_trace(
            series={mode_label: progress_rows},
            current_key="current_temperature_max",
            best_key="best_temperature_max_so_far",
            ylabel="Temperature (K)",
            output=figures / "temperature_trace.png",
            hires=hires,
        )
        render_metric_trace(
            series={mode_label: progress_rows},
            current_key="current_gradient_rms",
            best_key="best_gradient_rms_so_far",
            ylabel=r"$\\nabla T_{\\mathrm{rms}}$ (K/m)",
            output=figures / "gradient_trace.png",
            hires=hires,
        )
        render_metric_trace(
            series={mode_label: progress_rows},
            current_key="current_total_constraint_violation",
            best_key="best_total_constraint_violation_so_far",
            ylabel="Constraint violation",
            output=figures / "constraint_violation_progress.png",
            hires=hires,
        )
```

```python
# In optimizers/render_assets.py, update representative titles and cleanup globs
def _representative_title(representative_id: str, prefix: str) -> str:
    label_map = {
        "knee-candidate": "Knee",
        "min-peak-temperature": "Min Peak",
        "min-temperature-gradient-rms": "Min Gradient",
    }
    return f"{prefix} · {label_map.get(representative_id, representative_id)}"

render_temperature_field(
    grid=temperature_grid,
    xs=xs,
    ys=ys,
    output=temperature_figure_path,
    layout=layout,
    hotspot=_temperature_hotspot(temperature_grid, xs, ys),
    title=_representative_title(repr_root.name, "Temperature Field"),
    hires=hires,
)
render_gradient_field(
    grid=gradient_grid,
    xs=xs,
    ys=ys,
    output=gradient_figure_path,
    layout=layout,
    title=_representative_title(repr_root.name, "Gradient Field"),
    hires=hires,
)

for pattern in (
        "hypervolume_progress.*",
        "objective_progress.*",
        "temperature_trace.*",
        "gradient_trace.*",
        "constraint_violation_progress.*",
        "pareto_front.*",
        "layout_initial.*",
        "layout_final.*",
    ):
    for path in figures.glob(pattern):
        if path.is_file():
            path.unlink()
```

- [ ] **Step 4: Run the render-assets test to verify it passes**

Run: `conda run -n msfenicsx pytest tests/visualization/test_render_assets_fixtures.py -v`

Expected: PASS with the new figure files present under `figures/` and `figures/pdf/`.

- [ ] **Step 5: Commit**

```bash
git add optimizers/render_assets.py tests/visualization/test_render_assets_fixtures.py
git commit -m "feat(viz): render current-vs-best trace figures"
```

### Task 4: Build Summary-First Seed-Level And Aggregate Compare Bundles

**Files:**
- Create: `optimizers/comparison_artifacts.py`
- Modify: `optimizers/compare_runs.py`
- Modify: `tests/optimizers/test_compare_runs.py`
- Create: `tests/optimizers/test_suite_comparisons.py`

- [ ] **Step 1: Write the failing compare tests**

```python
# Extend tests/optimizers/test_compare_runs.py
def test_compare_runs_writes_richer_seed_bundle(tmp_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")

    from optimizers.compare_runs import compare_runs

    run_a = tmp_path / "0416_2030__raw"
    run_b = tmp_path / "0416_2035__llm"
    _seed_run(run_a, "raw")
    _seed_run(run_b, "llm")

    output = tmp_path / "comparisons" / "0416_2100__raw_vs_llm"
    compare_runs(runs=[run_a, run_b], output=output)

    assert (output / "figures" / "temperature_trace_comparison.png").exists()
    assert (output / "figures" / "gradient_trace_comparison.png").exists()
    assert (output / "figures" / "constraint_violation_comparison.png").exists()
    assert (output / "figures" / "feasible_progress_comparison.png").exists()
    assert (output / "tables" / "mode_metrics.csv").exists()
    assert (output / "tables" / "summary_table.tex").exists()
    assert (output / "tables" / "pairwise_deltas.csv").exists()
    assert (output / "analytics" / "summary_rows.json").exists()
```

```python
# Create tests/optimizers/test_suite_comparisons.py
from __future__ import annotations

from pathlib import Path

from tests.optimizers.experiment_fixtures import create_mixed_run_root


def test_build_suite_comparisons_writes_by_seed_and_aggregate_outputs(tmp_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")

    from optimizers.comparison_artifacts import build_suite_comparisons

    suite_root = create_mixed_run_root(tmp_path, modes=("raw", "union", "llm"), seeds=(11, 17))
    comparisons_root = build_suite_comparisons(suite_root)

    assert (comparisons_root / "manifest.json").exists()
    assert (comparisons_root / "by_seed" / "seed-11" / "figures" / "temperature_trace_comparison.png").exists()
    assert (comparisons_root / "aggregate" / "figures" / "hypervolume_iqr_comparison.png").exists()
    assert (comparisons_root / "aggregate" / "figures" / "first_feasible_eval_boxplot.png").exists()
    assert (comparisons_root / "aggregate" / "tables" / "pairwise_win_rate.csv").exists()
    assert (comparisons_root / "aggregate" / "analytics" / "aggregate_mode_summary.json").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_compare_runs.py tests/optimizers/test_suite_comparisons.py -v`

Expected:
- `test_compare_runs.py` fails on missing `figures/` / `tables/` / `analytics/` bundle structure
- `test_suite_comparisons.py` fails with `ModuleNotFoundError: No module named 'optimizers.comparison_artifacts'`

- [ ] **Step 3: Implement the comparison builder and keep the CLI wrapper thin**

```python
# Create optimizers/comparison_artifacts.py
"""Seed-level and suite-level comparison artifact builders."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from optimizers.analytics.loaders import iter_jsonl
from optimizers.analytics.rollups import rollup_per_generation
from optimizers.compare_runs import _extract_final_front, _first_feasible_eval, _mode_of, _progress_rows, _resolve_single_run_root, _trace_path
from optimizers.render_assets import REFERENCE_POINT, normalize_evaluation_rows
from visualization.figures.hypervolume import render_hypervolume_progress
from visualization.figures.pareto import render_pareto_front
from visualization.figures.progress import render_objective_progress
from visualization.figures.trace_series import render_dual_metric_boxplot, render_feasible_progress, render_metric_band_comparison, render_metric_boxplot, render_metric_trace


def build_seed_comparison_bundle(*, runs: list[Path], output: Path) -> Path:
    output = Path(output)
    figures_root = output / "figures"
    tables_root = output / "tables"
    analytics_root = output / "analytics"
    figures_root.mkdir(parents=True, exist_ok=True)
    tables_root.mkdir(parents=True, exist_ok=True)
    analytics_root.mkdir(parents=True, exist_ok=True)
    fronts: dict[str, list[tuple[float, float]]] = {}
    hypervolume_series: dict[str, list[tuple[int, float]]] = {}
    progress_rows_by_mode: dict[str, list[dict[str, Any]]] = {}
    summary_rows: list[dict[str, Any]] = []
    for run_root in runs:
        mode = _mode_of(run_root)
        events = normalize_evaluation_rows(list(iter_jsonl(_trace_path(run_root, "evaluation_events.jsonl"))))
        fronts[mode] = _extract_final_front(events)
        hypervolume_rows = rollup_per_generation(events, reference_point=REFERENCE_POINT)
        hypervolume_series[mode] = [(int(row["generation"]), float(row["hypervolume"])) for row in hypervolume_rows]
        progress_rows = _progress_rows(run_root)
        progress_rows_by_mode[mode] = progress_rows
        final_progress = progress_rows[-1] if progress_rows else {}
        summary_rows.append(
            {
                "mode": mode,
                "run": str(run_root),
                "front_size": len(fronts[mode]),
                "final_hypervolume": hypervolume_rows[-1]["hypervolume"] if hypervolume_rows else None,
                "first_feasible_eval": _first_feasible_eval(progress_rows),
                "best_temperature_max": final_progress.get("best_temperature_max_so_far"),
                "best_gradient_rms": final_progress.get("best_gradient_rms_so_far"),
                "best_total_constraint_violation": final_progress.get("best_total_constraint_violation_so_far"),
                "final_feasible_rate": final_progress.get("feasible_rate_so_far"),
            }
        )
    render_pareto_front(fronts=fronts, output=figures_root / "pareto_overlay.png")
    render_hypervolume_progress(series=hypervolume_series, output=figures_root / "hypervolume_comparison.png")
    render_objective_progress(series=progress_rows_by_mode, output=figures_root / "objective_progress_comparison.png")
    render_metric_trace(series=progress_rows_by_mode, current_key="current_temperature_max", best_key="best_temperature_max_so_far", ylabel="Temperature (K)", output=figures_root / "temperature_trace_comparison.png")
    render_metric_trace(series=progress_rows_by_mode, current_key="current_gradient_rms", best_key="best_gradient_rms_so_far", ylabel=r"$\\nabla T_{\\mathrm{rms}}$ (K/m)", output=figures_root / "gradient_trace_comparison.png")
    render_metric_trace(series=progress_rows_by_mode, current_key="current_total_constraint_violation", best_key="best_total_constraint_violation_so_far", ylabel="Constraint violation", output=figures_root / "constraint_violation_comparison.png")
    render_feasible_progress(series=progress_rows_by_mode, output=figures_root / "feasible_progress_comparison.png")
    (analytics_root / "summary_rows.json").write_text(json.dumps(summary_rows, indent=2) + "\\n", encoding="utf-8")
    (analytics_root / "timeline_rollups.json").write_text(json.dumps(progress_rows_by_mode, indent=2) + "\\n", encoding="utf-8")
    _write_table_pair(tables_root / "summary_table", summary_rows)
    _write_table_pair(tables_root / "mode_metrics", summary_rows)
    _write_pairwise_delta_table(tables_root / "pairwise_deltas", summary_rows)
    return output


def build_suite_comparisons(suite_root: Path) -> Path:
    suite_root = Path(suite_root)
    manifest = json.loads((suite_root / "manifest.json").read_text(encoding="utf-8"))
    modes = [str(mode) for mode in manifest["mode_ids"]]
    seeds = [int(seed) for seed in manifest["benchmark_seeds"]]
    comparisons_root = suite_root / "comparisons"
    comparisons_root.mkdir(parents=True, exist_ok=True)
    if len(seeds) == 1:
        runs = [suite_root / mode / "seeds" / f"seed-{seeds[0]}" for mode in modes]
        build_seed_comparison_bundle(runs=runs, output=comparisons_root)
        comparison_kind = "single_seed"
        by_seed_paths = ["."] 
        aggregate_path = None
    else:
        by_seed_root = comparisons_root / "by_seed"
        by_seed_paths = []
        for seed in seeds:
            seed_output = by_seed_root / f"seed-{seed}"
            runs = [suite_root / mode / "seeds" / f"seed-{seed}" for mode in modes]
            build_seed_comparison_bundle(runs=runs, output=seed_output)
            by_seed_paths.append(str(seed_output.relative_to(comparisons_root).as_posix()))
        aggregate_root = comparisons_root / "aggregate"
        _build_aggregate_bundle(suite_root=suite_root, modes=modes, seeds=seeds, output=aggregate_root)
        comparison_kind = "multi_seed"
        aggregate_path = "aggregate"
    (comparisons_root / "manifest.json").write_text(
        json.dumps(
            {
                "suite_root": str(suite_root),
                "mode_ids": modes,
                "benchmark_seeds": seeds,
                "comparison_kind": comparison_kind,
                "by_seed_paths": by_seed_paths,
                "aggregate_path": aggregate_path,
            },
            indent=2,
        )
        + "\\n",
        encoding="utf-8",
    )
    return comparisons_root


def _build_aggregate_bundle(*, suite_root: Path, modes: list[str], seeds: list[int], output: Path) -> Path:
    output = Path(output)
    figures_root = output / "figures"
    tables_root = output / "tables"
    analytics_root = output / "analytics"
    figures_root.mkdir(parents=True, exist_ok=True)
    tables_root.mkdir(parents=True, exist_ok=True)
    analytics_root.mkdir(parents=True, exist_ok=True)
    metric_rows: list[dict[str, Any]] = []
    hv_by_mode: dict[str, list[list[tuple[int, float]]]] = defaultdict(list)
    progress_by_mode: dict[str, list[list[dict[str, Any]]]] = defaultdict(list)
    for mode in modes:
        for seed in seeds:
            run_root = suite_root / mode / "seeds" / f"seed-{seed}"
            events = normalize_evaluation_rows(list(iter_jsonl(_trace_path(run_root, "evaluation_events.jsonl"))))
            hv_by_mode[mode].append([(int(row["generation"]), float(row["hypervolume"])) for row in rollup_per_generation(events, reference_point=REFERENCE_POINT)])
            progress_rows = _progress_rows(run_root)
            progress_by_mode[mode].append(progress_rows)
            final_progress = progress_rows[-1] if progress_rows else {}
            metric_rows.append(
                {
                    "seed": seed,
                    "mode": mode,
                    "first_feasible_eval": _first_feasible_eval(progress_rows),
                    "best_temperature_max": final_progress.get("best_temperature_max_so_far"),
                    "best_gradient_rms": final_progress.get("best_gradient_rms_so_far"),
                    "final_feasible_rate": final_progress.get("feasible_rate_so_far"),
                }
            )
    hv_bands = _band_payload_from_series(hv_by_mode)
    if hv_bands:
        render_metric_band_comparison(
            xs=next(iter(hv_bands.values()))["xs"],
            bands={mode: {"median": payload["median"], "p25": payload["p25"], "p75": payload["p75"]} for mode, payload in hv_bands.items()},
            ylabel="Hypervolume",
            output=figures_root / "hypervolume_iqr_comparison.png",
        )
    temperature_bands = _band_payload_from_progress(progress_by_mode, metric_key="best_temperature_max_so_far")
    if temperature_bands:
        render_metric_band_comparison(
            xs=next(iter(temperature_bands.values()))["xs"],
            bands={mode: {"median": payload["median"], "p25": payload["p25"], "p75": payload["p75"]} for mode, payload in temperature_bands.items()},
            ylabel="Best temperature (K)",
            output=figures_root / "temperature_trace_median_band.png",
        )
    gradient_bands = _band_payload_from_progress(progress_by_mode, metric_key="best_gradient_rms_so_far")
    if gradient_bands:
        render_metric_band_comparison(
            xs=next(iter(gradient_bands.values()))["xs"],
            bands={mode: {"median": payload["median"], "p25": payload["p25"], "p75": payload["p75"]} for mode, payload in gradient_bands.items()},
            ylabel=r"Best $\\nabla T_{\\mathrm{rms}}$ (K/m)",
            output=figures_root / "gradient_trace_median_band.png",
        )
    render_metric_boxplot(
        values_by_mode={mode: [row["first_feasible_eval"] for row in metric_rows if row["mode"] == mode and row.get("first_feasible_eval") is not None] for mode in modes},
        ylabel="First feasible eval",
        output=figures_root / "first_feasible_eval_boxplot.png",
    )
    render_metric_boxplot(
        values_by_mode={mode: [row["final_feasible_rate"] for row in metric_rows if row["mode"] == mode and row.get("final_feasible_rate") is not None] for mode in modes},
        ylabel="Final feasible rate",
        output=figures_root / "feasible_rate_boxplot.png",
    )
    render_dual_metric_boxplot(
        left_values_by_mode={mode: [row["best_temperature_max"] for row in metric_rows if row["mode"] == mode and row.get("best_temperature_max") is not None] for mode in modes},
        right_values_by_mode={mode: [row["best_gradient_rms"] for row in metric_rows if row["mode"] == mode and row.get("best_gradient_rms") is not None] for mode in modes},
        left_ylabel="Best temperature (K)",
        right_ylabel=r"Best $\\nabla T_{\\mathrm{rms}}$ (K/m)",
        output=figures_root / "best_objectives_boxplot.png",
    )
    aggregate_rows = _aggregate_mode_rows(metric_rows)
    win_rate_rows = _pairwise_win_rate_rows(metric_rows)
    (analytics_root / "seed_metric_rows.json").write_text(json.dumps(metric_rows, indent=2) + "\\n", encoding="utf-8")
    (analytics_root / "aggregate_mode_summary.json").write_text(json.dumps(aggregate_rows, indent=2) + "\\n", encoding="utf-8")
    (analytics_root / "pairwise_win_rate.json").write_text(json.dumps(win_rate_rows, indent=2) + "\\n", encoding="utf-8")
    _write_table_pair(tables_root / "per_seed_metrics", metric_rows)
    _write_table_pair(tables_root / "aggregate_mode_summary", aggregate_rows)
    _write_table_pair(tables_root / "pairwise_win_rate", win_rate_rows)
    return output


def _band_payload_from_series(series_by_mode: dict[str, list[list[tuple[int, float]]]]) -> dict[str, dict[str, Any]]:
    payload: dict[str, dict[str, Any]] = {}
    for mode, mode_series in series_by_mode.items():
        if not mode_series:
            continue
        xs = [point[0] for point in mode_series[0]]
        matrix = np.asarray([[point[1] for point in points] for points in mode_series], dtype=np.float64)
        payload[mode] = {
            "xs": xs,
            "median": np.median(matrix, axis=0).tolist(),
            "p25": np.percentile(matrix, 25, axis=0).tolist(),
            "p75": np.percentile(matrix, 75, axis=0).tolist(),
        }
    return payload


def _band_payload_from_progress(progress_by_mode: dict[str, list[list[dict[str, Any]]]], *, metric_key: str) -> dict[str, dict[str, Any]]:
    payload: dict[str, dict[str, Any]] = {}
    for mode, mode_rows in progress_by_mode.items():
        if not mode_rows or not mode_rows[0]:
            continue
        xs = [int(row["evaluation_index"]) for row in mode_rows[0]]
        matrix = np.asarray([[float(row.get(metric_key) or np.nan) for row in rows] for rows in mode_rows], dtype=np.float64)
        payload[mode] = {
            "xs": xs,
            "median": np.nanmedian(matrix, axis=0).tolist(),
            "p25": np.nanpercentile(matrix, 25, axis=0).tolist(),
            "p75": np.nanpercentile(matrix, 75, axis=0).tolist(),
        }
    return payload


def _aggregate_mode_rows(metric_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in metric_rows:
        grouped[str(row["mode"])].append(row)
    rows: list[dict[str, Any]] = []
    for mode, items in grouped.items():
        rows.append(
            {
                "mode": mode,
                "seed_count": len(items),
                "best_temperature_mean": float(np.mean([float(item["best_temperature_max"]) for item in items if item.get("best_temperature_max") is not None])),
                "best_gradient_mean": float(np.mean([float(item["best_gradient_rms"]) for item in items if item.get("best_gradient_rms") is not None])),
                "feasible_rate_mean": float(np.mean([float(item["final_feasible_rate"]) for item in items if item.get("final_feasible_rate") is not None])),
            }
        )
    return rows


def _pairwise_win_rate_rows(metric_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    wins: list[dict[str, Any]] = []
    rows_by_seed: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in metric_rows:
        rows_by_seed[int(row["seed"])][str(row["mode"])] = row
    mode_ids = sorted({str(row["mode"]) for row in metric_rows})
    for left_index, left_mode in enumerate(mode_ids):
        for right_mode in mode_ids[left_index + 1 :]:
            compared = 0
            left_wins = 0
            for seed_rows in rows_by_seed.values():
                if left_mode not in seed_rows or right_mode not in seed_rows:
                    continue
                compared += 1
                if float(seed_rows[left_mode]["best_temperature_max"]) < float(seed_rows[right_mode]["best_temperature_max"]):
                    left_wins += 1
            wins.append({"left_mode": left_mode, "right_mode": right_mode, "compared_seeds": compared, "left_win_rate": float(left_wins / compared) if compared else None})
    return wins


def _write_table_pair(base_path: Path, rows: list[dict[str, Any]]) -> None:
    _write_csv(base_path.with_suffix(".csv"), rows)
    base_path.with_suffix(".tex").write_text(_rows_to_booktabs(rows), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    import csv

    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_pairwise_delta_table(path: Path, rows: list[dict[str, Any]]) -> None:
    deltas: list[dict[str, Any]] = []
    for left_index, left_row in enumerate(rows):
        for right_row in rows[left_index + 1 :]:
            deltas.append(
                {
                    "left_mode": left_row["mode"],
                    "right_mode": right_row["mode"],
                    "delta_best_temperature": (left_row.get("best_temperature_max") or 0.0) - (right_row.get("best_temperature_max") or 0.0),
                    "delta_best_gradient": (left_row.get("best_gradient_rms") or 0.0) - (right_row.get("best_gradient_rms") or 0.0),
                    "delta_feasible_rate": (left_row.get("final_feasible_rate") or 0.0) - (right_row.get("final_feasible_rate") or 0.0),
                }
            )
    _write_table_pair(path, deltas)


def _rows_to_booktabs(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    fieldnames = list(rows[0].keys())
    lines = ["\\\\begin{tabular}{" + "l" * len(fieldnames) + "}", "\\\\toprule", " & ".join(fieldnames) + " \\\\", "\\\\midrule"]
    for row in rows:
        lines.append(" & ".join("" if row.get(name) is None else str(row.get(name)) for name in fieldnames) + " \\\\")
    lines.extend(["\\\\bottomrule", "\\\\end{tabular}", ""])
    return "\\n".join(lines)
```

```python
# In optimizers/compare_runs.py, delegate to the shared builder
from optimizers.comparison_artifacts import build_seed_comparison_bundle


def compare_runs(*, runs: Sequence[Path], output: Path) -> None:
    resolved_runs = [_resolve_single_run_root(Path(run)) for run in runs]
    build_seed_comparison_bundle(runs=resolved_runs, output=Path(output))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_compare_runs.py tests/optimizers/test_suite_comparisons.py -v`

Expected: both test files PASS.

- [ ] **Step 5: Commit**

```bash
git add optimizers/comparison_artifacts.py optimizers/compare_runs.py tests/optimizers/test_compare_runs.py tests/optimizers/test_suite_comparisons.py
git commit -m "feat(viz): add suite comparison artifact builders"
```

### Task 5: Auto-Generate `comparisons/` From `run-benchmark-suite`

**Files:**
- Modify: `optimizers/run_suite.py`
- Modify: `tests/optimizers/test_run_suite.py`

- [ ] **Step 1: Write the failing suite orchestration tests**

```python
# Replace/extend tests/optimizers/test_run_suite.py with these checks
from optimizers.io import load_optimization_spec, save_optimization_spec


def _fake_run():
    return type(
        "FakeRun",
        (),
        {
            "result": type(
                "FakeResult",
                (),
                {
                    "run_meta": {
                        "run_id": "fixture-run",
                        "optimization_spec_id": "fixture-spec",
                        "evaluation_spec_id": "fixture-eval",
                    },
                    "history": [],
                    "pareto_front": [],
                },
            )(),
            "representative_artifacts": {},
            "generation_summary_rows": [],
        },
    )()


def test_run_benchmark_suite_skips_comparisons_for_single_mode(tmp_path: Path, monkeypatch) -> None:
    raw_spec_path = _write_small_raw_spec(tmp_path)
    monkeypatch.setattr(run_suite_module, "run_raw_optimization", lambda *args, **kwargs: _fake_run())
    monkeypatch.setattr(run_suite_module, "write_optimization_artifacts", lambda *args, **kwargs: Path(args[0]))
    monkeypatch.setattr(run_suite_module, "write_run_manifest", lambda *args, **kwargs: Path(args[0]))

    compare_calls: list[Path] = []

    def _fake_build_suite_comparisons(run_root: Path) -> Path:
        compare_calls.append(Path(run_root))
        return Path(run_root) / "comparisons"

    monkeypatch.setattr(run_suite_module, "build_suite_comparisons", _fake_build_suite_comparisons)

    run_root = run_benchmark_suite(
        optimization_spec_paths=[raw_spec_path],
        benchmark_seeds=[11],
        scenario_runs_root=tmp_path / "scenario_runs",
        modes=["raw"],
    )

    assert compare_calls == []
    assert not (run_root / "comparisons").exists()


def test_run_benchmark_suite_builds_comparisons_for_multi_mode(tmp_path: Path, monkeypatch) -> None:
    raw_spec_path = _write_small_raw_spec(tmp_path)
    union_payload = load_optimization_spec(raw_spec_path).to_dict()
    union_payload["algorithm"]["mode"] = "union"
    union_spec_path = tmp_path / "nsga2_union.yaml"
    save_optimization_spec(union_payload, union_spec_path)
    monkeypatch.setattr(run_suite_module, "run_raw_optimization", lambda *args, **kwargs: _fake_run())
    monkeypatch.setattr(run_suite_module, "run_union_optimization", lambda *args, **kwargs: _fake_run())
    monkeypatch.setattr(run_suite_module, "write_optimization_artifacts", lambda *args, **kwargs: Path(args[0]))
    monkeypatch.setattr(run_suite_module, "write_run_manifest", lambda *args, **kwargs: Path(args[0]))

    compare_calls: list[Path] = []

    def _fake_build_suite_comparisons(run_root: Path) -> Path:
        compare_calls.append(Path(run_root))
        target = Path(run_root) / "comparisons"
        target.mkdir(parents=True, exist_ok=True)
        return target

    monkeypatch.setattr(run_suite_module, "build_suite_comparisons", _fake_build_suite_comparisons)

    run_root = run_benchmark_suite(
        optimization_spec_paths=[raw_spec_path, union_spec_path],
        benchmark_seeds=[11],
        scenario_runs_root=tmp_path / "scenario_runs",
        modes=["raw", "union"],
    )

    assert compare_calls == [run_root]
    assert (run_root / "comparisons").exists()
```

- [ ] **Step 2: Run the suite tests to verify they fail**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_run_suite.py -v`

Expected: FAIL because `run_suite.py` does not import or call `build_suite_comparisons`.

- [ ] **Step 3: Wire the suite orchestrator**

```python
# In optimizers/run_suite.py
from optimizers.comparison_artifacts import build_suite_comparisons

for mode in selected_modes:
    spec_path, optimization_spec = spec_by_mode[mode]
    mode_root = initialize_mode_root(run_root, mode=mode)
    write_manifest(
        mode_root / "manifest.json",
        {
            "mode_id": mode,
            "optimization_spec_path": str(spec_path),
            "benchmark_seeds": list(effective_seeds),
            "directories": {"summaries": "summaries", "seeds": "seeds"},
        },
    )
    for seed in effective_seeds:
        seeded_spec = _with_benchmark_seed(optimization_spec, seed)
        base_case = generate_benchmark_case(spec_path, seeded_spec)
        evaluation_spec_path_for_seed = resolve_evaluation_spec_path(spec_path, seeded_spec)
        evaluation_spec = load_spec(evaluation_spec_path_for_seed)
        _wall_start = time.monotonic()
        run = _dispatch_run(
            base_case,
            seeded_spec,
            evaluation_spec,
            spec_path,
            evaluation_workers=evaluation_workers,
            trace_output_root=mode_root / "seeds" / f"seed-{seed}",
        )
        _wall_seconds = time.monotonic() - _wall_start
        evaluation_payload = evaluation_spec.to_dict() if hasattr(evaluation_spec, "to_dict") else dict(evaluation_spec)
        write_optimization_artifacts(
            mode_root / "seeds" / f"seed-{seed}",
            run,
            mode_id=mode,
            seed=seed,
            objective_definitions=list(evaluation_payload["objectives"]),
        )
        write_run_manifest(
            mode_root / "seeds" / f"seed-{seed}" / "run.yaml",
            mode=mode,
            benchmark_seed=int(seed),
            algorithm_seed=int(seeded_spec.algorithm["seed"]),
            optimization_spec_path=str(spec_path),
            evaluation_spec_path=str(evaluation_spec_path_for_seed),
            population_size=int(seeded_spec.algorithm["population_size"]),
            num_generations=int(seeded_spec.algorithm["num_generations"]),
            wall_seconds=_wall_seconds,
        )
    if not skip_render:
        from optimizers.render_assets import render_assets

        render_assets(mode_root, hires=False)
if len(selected_modes) >= 2:
    build_suite_comparisons(run_root)
return run_root
```

- [ ] **Step 4: Run the suite tests to verify they pass**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_run_suite.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add optimizers/run_suite.py tests/optimizers/test_run_suite.py
git commit -m "feat(viz): auto-generate suite comparisons"
```

### Task 6: Update Docs And Run Focused Verification Plus A Real 10x5 Suite

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Write the documentation updates**

```md
<!-- In README.md, update the optimizer output section -->
- suite runs with two or more modes automatically write `comparisons/`
- single-seed suites write compare artifacts directly under `<suite_root>/comparisons/`
- multi-seed suites write `<suite_root>/comparisons/by_seed/seed-<n>/` and `<suite_root>/comparisons/aggregate/`
- run-level figures now include `temperature_trace`, `gradient_trace`, and `constraint_violation_progress`
- spatial figures are axis-free and label components as `C01..C15`
```

```md
<!-- In AGENTS.md, update the data/artifact rules -->
- automatic suite-owned comparison output is allowed only under `comparisons/`
- never restore legacy `comparison/`
- per-seed compare bundles live under `comparisons/by_seed/seed-<n>/`
- aggregate multi-seed compare bundles live under `comparisons/aggregate/`
- spatial figures must hide coordinate axes and use short component labels `C01..C15`
```

- [ ] **Step 2: Run the focused test matrix**

Run:

```bash
conda run -n msfenicsx pytest \
  tests/optimizers/test_run_telemetry.py \
  tests/optimizers/test_compare_runs.py \
  tests/optimizers/test_suite_comparisons.py \
  tests/optimizers/test_run_suite.py \
  tests/visualization/test_trace_series_figure.py \
  tests/visualization/test_spatial_figure_contract.py \
  tests/visualization/test_heatfield_orientation.py \
  tests/visualization/test_render_assets_fixtures.py \
  -v
```

Expected: all selected tests PASS.

- [ ] **Step 3: Run one real 10x5 multi-mode, multi-seed verification**

Run:

```bash
conda run -n msfenicsx python -m optimizers.cli run-benchmark-suite \
  --optimization-spec scenarios/optimization/s2_staged_raw.yaml \
  --optimization-spec scenarios/optimization/s2_staged_union.yaml \
  --optimization-spec scenarios/optimization/s2_staged_llm.yaml \
  --mode raw \
  --mode union \
  --mode llm \
  --benchmark-seed 11 \
  --benchmark-seed 17 \
  --population-size 10 \
  --num-generations 5 \
  --evaluation-workers 2 \
  --scenario-runs-root ./scenario_runs
```

Expected:
- suite root exists under `scenario_runs/s2_staged/<run_id>/`
- each mode has `seeds/seed-11` and `seeds/seed-17`
- `comparisons/by_seed/seed-11/` and `comparisons/by_seed/seed-17/` exist
- `comparisons/aggregate/` exists
- run-level figures contain `temperature_trace.png`, `gradient_trace.png`, `constraint_violation_progress.png`
- layout/field figures show `C01..C15` and no axis ticks

- [ ] **Step 4: Spot-check the real artifacts**

Run:

```bash
find scenario_runs/s2_staged -maxdepth 4 -path '*comparisons*' | sort | sed -n '1,80p'
find scenario_runs/s2_staged -maxdepth 5 -path '*figures*temperature_trace.png' | sort | sed -n '1,20p'
find scenario_runs/s2_staged -maxdepth 5 -path '*figures*layout_final.png' | sort | sed -n '1,20p'
```

Expected:
- compare output is attached to the suite under `comparisons/`, not written into source runs
- new trace figures exist
- spatial figure files exist in both PNG and `pdf/` forms

- [ ] **Step 5: Commit**

```bash
git add README.md AGENTS.md
git commit -m "docs: document suite comparisons and spatial figure contract"
```

---

## Self-Review

- **Spec coverage:** this plan maps the spec into six concrete deliverables: telemetry extension, spatial figure contract, render-assets wiring, compare builder expansion, suite orchestration, and docs/verification. The automatic `comparisons/`, richer compare content, new trace figures, component labels, adaptive field chips, and axis-free presentation all have explicit implementation tasks.
- **Placeholder scan:** no `TODO`, `TBD`, or deferred “write tests later” steps remain inside the plan.
- **Type consistency:** the same field names are used throughout: `current_temperature_max`, `current_gradient_rms`, `current_total_constraint_violation`, `comparisons/`, `by_seed/`, `aggregate/`, and `C01..C15`.
