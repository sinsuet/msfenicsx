# S1 Typical Scientific Figure Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the current `s1_typical` figure outputs from dashboard-style SVGs into white-background scientific figures with disciplined text layout, correct figure semantics, and publication-friendly single-case, mode, and comparison visuals.

**Architecture:** Keep the current deterministic SVG rendering path and run-tree structure, but introduce a scientific-figure foundation layer for themes, text layout, axes, legends, and color bars. Then refactor `case_pages.py`, `mode_pages.py`, and `comparison_pages.py` so figures focus on geometry, fields, and progress while long prose and detailed notes move back into HTML tables and reports.

**Tech Stack:** Python 3.12, pytest, NumPy, PyYAML, repository-local SVG/HTML generation in `visualization/`, JSON/JSONL summaries under `scenario_runs/s1_typical/`

---

Spec reference:

- `docs/superpowers/specs/2026-04-02-s1-typical-scientific-figure-refinement-design.md`

Scope note:

- Keep this as one implementation plan because the style system, single-case figures, mode figures, and comparison figures all share the same SVG helper layer and should move together rather than diverge again.

Implementation guardrails:

- Keep the new `scenario_runs/s1_typical/<run_id>/` tree unchanged.
- Preserve stable figure filenames already used by pages:
  - `layout.svg`
  - `temperature-field.svg`
  - `temperature-contours.svg`
  - `gradient-field.svg`
  - `mode-summary.svg`
  - `progress.svg`
  - `fields.svg`
- Exported figures under `figures/` must use white backgrounds.
- Long prose and detailed geometry notes belong in HTML pages, not in the SVG figure body.
- `fields.svg` must become a real physical-field comparison figure, not a hotspot-stat surrogate.
- `progress.svg` must become a true cross-mode progress figure across required metrics.
- Follow TDD strictly: red, verify red, green, verify green, then refactor.

## File Structure

### Scientific Figure Foundation

- Create: `visualization/figure_theme.py`
  Own white-background figure presets, typography tokens, scientific palettes, and export-size presets.
- Create: `visualization/figure_text.py`
  Own wrapped text, max-line truncation, ellipsis behavior, and clipping-safe text box helpers for SVG.
- Create: `visualization/figure_axes.py`
  Own axis panels, tick generation, legends, milestone markers, and color-bar helpers.
- Modify: `visualization/static_assets.py`
  Keep low-level SVG shape helpers and dashboard HTML helpers, but delegate scientific figure concerns to the new focused modules.
- Create: `tests/visualization/test_figure_system.py`
  Cover white backgrounds, text wrapping/clipping behavior, and axis/color-bar rendering primitives.

### Single-Case Figure Builders

- Modify: `visualization/case_pages.py`
  Rebuild `layout.svg`, `temperature-field.svg`, `temperature-contours.svg`, and `gradient-field.svg` around the new scientific figure helpers.
- Modify: `tests/visualization/test_case_pages.py`
  Replace dashboard-style expectations with white-background, no-overflow, no-prose-in-figure, and color-bar expectations.

### Mode Summary Figures

- Modify: `visualization/mode_pages.py`
  Replace single-seed bar-card composition with evaluation-progress-first scientific panels and milestone-aware summaries.
- Modify: `tests/visualization/test_mode_pages.py`
  Require line or step-style progress panels, milestone labels, and white scientific styling.

### Comparison Figures

- Modify: `visualization/comparison_pages.py`
  Rebuild `progress.svg` as a true multi-metric comparison figure and `fields.svg` as a true aligned field-comparison figure.
- Modify: `optimizers/comparison_summary.py`
  Ensure field-comparison summaries carry enough metadata for shared representative alignment and shared scales.
- Modify: `tests/visualization/test_comparison_pages.py`
  Require actual field-comparison figure content and decomposed progress-comparison content.
- Modify: `tests/optimizers/test_comparison_summary.py`
  Require field-alignment metadata sufficient for real field panels rather than hotspot-only surrogates.

### Documentation And Final Verification

- Modify: `README.md`
  Update the visualization section so figure expectations match the new scientific export behavior.
- Modify: `docs/superpowers/specs/2026-04-02-s1-typical-visualization-and-logging-reset-design.md`
  Add a cross-reference pointing readers to the scientific-figure refinement spec.

## Task 1: Build The Scientific Figure Foundation

**Files:**
- Create: `visualization/figure_theme.py`
- Create: `visualization/figure_text.py`
- Create: `visualization/figure_axes.py`
- Modify: `visualization/static_assets.py`
- Create: `tests/visualization/test_figure_system.py`

- [ ] **Step 1: Write the failing scientific-figure foundation tests**

Add tests that require:

```python
def test_scientific_figure_canvas_uses_white_background() -> None:
    svg = build_scientific_canvas(title="demo", width=800, height=600, body="")
    assert "fill='#ffffff'" in svg.lower()
```

```python
def test_wrap_text_lines_respect_width_and_max_lines() -> None:
    lines = wrap_text_lines(
        "c01-001: x=[0.27, 0.35], y=[0.61, 0.67]",
        max_chars=18,
        max_lines=2,
    )
    assert len(lines) == 2
    assert lines[-1].endswith("...")
```

```python
def test_render_colorbar_panel_writes_scale_labels() -> None:
    svg = render_colorbar_panel(
        title="Temperature",
        value_min=300.0,
        value_max=305.0,
        x=0.0,
        y=0.0,
        width=60.0,
        height=220.0,
    )
    assert "300.000" in svg
    assert "305.000" in svg
```

- [ ] **Step 2: Run the focused foundation tests to confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/visualization/test_figure_system.py -v
```

Expected:

- FAIL because the scientific figure helper modules do not exist yet

- [ ] **Step 3: Implement the theme, text, and axis helper modules**

Create a white scientific theme layer:

```python
SCIENTIFIC_COLORS = {
    "background": "#FFFFFF",
    "ink": "#1A1A1A",
    "muted": "#666666",
    "panel_stroke": "#C8C8C8",
}
```

Create text helpers such as:

```python
def wrap_text_lines(text: str, *, max_chars: int, max_lines: int) -> list[str]:
    ...
```

Create axis and legend helpers such as:

```python
def render_axis_panel(...): ...
def render_colorbar_panel(...): ...
def render_mode_legend(...): ...
```

Wire `visualization/static_assets.py` so existing renderers can keep using shared SVG writing and shape helpers while the new figure logic imports the focused modules.

- [ ] **Step 4: Re-run the focused foundation tests**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  visualization/figure_theme.py \
  visualization/figure_text.py \
  visualization/figure_axes.py \
  visualization/static_assets.py \
  tests/visualization/test_figure_system.py
git commit -m "feat: add scientific figure foundation"
```

## Task 2: Rebuild The Single-Case Layout Figure

**Files:**
- Modify: `visualization/case_pages.py`
- Modify: `tests/visualization/test_case_pages.py`

- [ ] **Step 1: Write the failing single-case layout tests**

Add tests that require:

```python
def test_layout_figure_uses_white_background_and_compact_legend(tmp_path: Path) -> None:
    representative_root = _build_case_bundle(tmp_path)
    render_case_page(representative_root)
    svg = (representative_root / "figures" / "layout.svg").read_text(encoding="utf-8").lower()
    assert "fill='#ffffff'" in svg
    assert "legend" in svg
```

```python
def test_layout_figure_moves_geometry_notes_out_of_svg(tmp_path: Path) -> None:
    representative_root = _build_case_bundle(tmp_path)
    render_case_page(representative_root)
    svg = (representative_root / "figures" / "layout.svg").read_text(encoding="utf-8")
    html = (representative_root / "pages" / "index.html").read_text(encoding="utf-8")
    assert "Geometry Notes" not in svg
    assert "Component Thermal Table" in html
```

- [ ] **Step 2: Run the focused layout tests to confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/visualization/test_case_pages.py::test_layout_figure_uses_white_background_and_compact_legend \
  tests/visualization/test_case_pages.py::test_layout_figure_moves_geometry_notes_out_of_svg -v
```

Expected:

- FAIL because the current layout figure still uses dashboard cards and text panels

- [ ] **Step 3: Implement the clean geometry figure**

Refactor the layout builder so it writes:

```python
def _render_layout_figure(...) -> str:
    return render_geometry_figure(
        title=f"{case_id} layout",
        panel_domain=...,
        components=...,
        sinks=...,
        hotspot=...,
        legend_items=["component", "sink", "hotspot"],
    )
```

Move all long geometry note strings into the HTML page as:

- component bounds table
- sink table
- optional geometry detail section

- [ ] **Step 4: Re-run the focused layout tests**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  visualization/case_pages.py \
  tests/visualization/test_case_pages.py
git commit -m "feat: rebuild single-case layout figure"
```

## Task 3: Rebuild The Single-Case Field Figures

**Files:**
- Modify: `visualization/case_pages.py`
- Modify: `tests/visualization/test_case_pages.py`

- [ ] **Step 1: Write the failing field-figure tests**

Add tests that require:

```python
def test_field_figures_use_colorbars_and_white_background(tmp_path: Path) -> None:
    representative_root = _build_case_bundle(tmp_path)
    render_case_page(representative_root)
    temperature_svg = (representative_root / "figures" / "temperature-field.svg").read_text(encoding="utf-8").lower()
    gradient_svg = (representative_root / "figures" / "gradient-field.svg").read_text(encoding="utf-8").lower()
    assert "fill='#ffffff'" in temperature_svg
    assert "colorbar" in temperature_svg
    assert "colorbar" in gradient_svg
```

```python
def test_field_figures_do_not_embed_long_reading_guides(tmp_path: Path) -> None:
    representative_root = _build_case_bundle(tmp_path)
    render_case_page(representative_root)
    svg = (representative_root / "figures" / "temperature-field.svg").read_text(encoding="utf-8")
    assert "Interpretation" not in svg
    assert "Temperature Field" in (representative_root / "pages" / "index.html").read_text(encoding="utf-8")
```

- [ ] **Step 2: Run the focused field tests to confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/visualization/test_case_pages.py::test_field_figures_use_colorbars_and_white_background \
  tests/visualization/test_case_pages.py::test_field_figures_do_not_embed_long_reading_guides -v
```

Expected:

- FAIL because the current field figures still use dashboard cards and prose sidebars

- [ ] **Step 3: Implement scientific field figures**

Refactor the field builders so they compose:

```python
def _render_field_figure(...) -> str:
    return render_field_panel(
        title=title,
        raster=sampled_grid,
        overlays=component_outlines,
        hotspot=hotspot,
        colorbar=render_colorbar_panel(...),
    )
```

Ensure:

- white figure background
- dominant plot area
- compact field annotations only
- no long prose boxes
- component outlines remain visible
- contour export remains separate as `temperature-contours.svg`

- [ ] **Step 4: Re-run the focused field tests**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  visualization/case_pages.py \
  tests/visualization/test_case_pages.py
git commit -m "feat: rebuild single-case field figures"
```

## Task 4: Rebuild The Mode Summary Figure

**Files:**
- Modify: `visualization/mode_pages.py`
- Modify: `tests/visualization/test_mode_pages.py`

- [ ] **Step 1: Write the failing mode-summary tests**

Add tests that require:

```python
def test_mode_summary_figure_uses_progress_panels_for_single_seed(tmp_path: Path) -> None:
    mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="raw", seeds=(11,))
    render_mode_pages(mode_root)
    svg = (mode_root / "figures" / "mode-summary.svg").read_text(encoding="utf-8")
    assert "Best Peak vs Evaluation" in svg
    assert "Pareto Size vs Evaluation" in svg
    assert "First Feasible Eval by Seed" not in svg
```

```python
def test_mode_summary_figure_uses_white_scientific_theme(tmp_path: Path) -> None:
    mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="raw", seeds=(11,))
    render_mode_pages(mode_root)
    svg = (mode_root / "figures" / "mode-summary.svg").read_text(encoding="utf-8").lower()
    assert "fill='#ffffff'" in svg
```

- [ ] **Step 2: Run the focused mode-summary tests to confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/visualization/test_mode_pages.py -v
```

Expected:

- FAIL because the current mode summary still uses bar cards and prose panels

- [ ] **Step 3: Implement the new mode overview figure**

Refactor `visualization/mode_pages.py` so `mode-summary.svg` is built from progress-aware panels such as:

```python
panels = [
    render_progress_panel(title="Best Peak vs Evaluation", ...),
    render_progress_panel(title="Best Gradient vs Evaluation", ...),
    render_progress_panel(title="Feasible Rate vs Evaluation", ...),
    render_progress_panel(title="Pareto Size vs Evaluation", ...),
]
```

Keep concise mode metadata and milestone markers, but move descriptive text to HTML tables and reports.

- [ ] **Step 4: Re-run the focused mode-summary tests**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  visualization/mode_pages.py \
  tests/visualization/test_mode_pages.py
git commit -m "feat: rebuild mode summary figure"
```

## Task 5: Rebuild The Comparison Progress And Field Figures

**Files:**
- Modify: `visualization/comparison_pages.py`
- Modify: `optimizers/comparison_summary.py`
- Modify: `tests/visualization/test_comparison_pages.py`
- Modify: `tests/optimizers/test_comparison_summary.py`

- [ ] **Step 1: Write the failing comparison-figure tests**

Add tests that require:

```python
def test_progress_figure_renders_multi_metric_comparison_panels(tmp_path: Path) -> None:
    run_root = create_mixed_run_root(tmp_path, modes=("raw", "union", "llm"), seeds=(11,))
    build_comparison_summaries(run_root)
    render_comparison_pages(run_root)
    svg = (run_root / "comparison" / "figures" / "progress.svg").read_text(encoding="utf-8")
    assert "Best Peak vs Evaluation" in svg
    assert "Best Gradient vs Evaluation" in svg
    assert "Feasible Rate vs Evaluation" in svg
    assert "Pareto Size vs Evaluation" in svg
```

```python
def test_fields_figure_renders_actual_field_comparison_panels(tmp_path: Path) -> None:
    run_root = create_mixed_run_root(tmp_path, modes=("raw", "union"), seeds=(11,))
    build_comparison_summaries(run_root)
    render_comparison_pages(run_root)
    svg = (run_root / "comparison" / "figures" / "fields.svg").read_text(encoding="utf-8")
    assert "Shared Color Scale" in svg
    assert "Hotspot X by Mode" not in svg
```

```python
def test_comparison_summary_exposes_representative_alignment_metadata(tmp_path: Path) -> None:
    run_root = create_mixed_run_root(tmp_path, modes=("raw", "union"), seeds=(11,))
    build_comparison_summaries(run_root)
    payload = json.loads((run_root / "comparison" / "summaries" / "field_alignment.json").read_text())
    assert "representative_id" in payload["rows"][0]
    assert "temperature_grid_shape" in payload["rows"][0]
```

- [ ] **Step 2: Run the focused comparison tests to confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_comparison_summary.py \
  tests/visualization/test_comparison_pages.py -v
```

Expected:

- FAIL because `progress.svg` is still too narrow semantically and `fields.svg` is still a hotspot-stat overview

- [ ] **Step 3: Implement the multi-metric progress figure**

Refactor `progress.svg` so it uses four compact scientific panels:

```python
progress_panels = [
    ("Best Peak vs Evaluation", ...),
    ("Best Gradient vs Evaluation", ...),
    ("Feasible Rate vs Evaluation", ...),
    ("Pareto Size vs Evaluation", ...),
]
```

Include:

- explicit mode legend
- milestone markers
- sensible tick spacing
- white background

- [ ] **Step 4: Implement the real field-comparison figure**

Extend `optimizers/comparison_summary.py` so aligned rows carry enough metadata for figure assembly, then refactor `fields.svg` so it renders:

```python
field_panels = [
    render_aligned_field_panel(mode_id="raw", representative_id="knee-candidate", ...),
    render_aligned_field_panel(mode_id="union", representative_id="knee-candidate", ...),
]
```

with:

- actual field rasters
- component overlays
- hotspot markers
- shared color bar
- optional later extension points for difference fields

- [ ] **Step 5: Re-run the focused comparison tests**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add \
  optimizers/comparison_summary.py \
  visualization/comparison_pages.py \
  tests/optimizers/test_comparison_summary.py \
  tests/visualization/test_comparison_pages.py
git commit -m "feat: rebuild comparison progress and field figures"
```

## Task 6: Reflow Pages, Refresh Docs, And Verify On A Real Run

**Files:**
- Modify: `visualization/case_pages.py`
- Modify: `visualization/mode_pages.py`
- Modify: `visualization/comparison_pages.py`
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-04-02-s1-typical-visualization-and-logging-reset-design.md`

- [ ] **Step 1: Write the failing page-integration checks**

Add or extend tests that require:

```python
def test_case_page_keeps_long_notes_in_html_tables_not_svg(tmp_path: Path) -> None:
    ...
    assert "Geometry Details" in html
    assert "Geometry Details" not in layout_svg
```

```python
def test_comparison_fields_page_embeds_real_field_figure(tmp_path: Path) -> None:
    ...
    assert "figures/fields.svg" in html
    assert "Representative field alignment" in html
```

- [ ] **Step 2: Run the focused integration tests to confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/visualization/test_case_pages.py \
  tests/visualization/test_mode_pages.py \
  tests/visualization/test_comparison_pages.py -v
```

Expected:

- FAIL until the pages and figure wiring fully match the new scientific split

- [ ] **Step 3: Finish page reflow and docs updates**

Update the HTML pages so they:

- embed the new scientific figures
- keep detail-heavy content in tables
- use captions that match the scientific figure semantics

Update docs so they state clearly:

- figures are white-background scientific exports
- comparison field figures show actual fields
- progress figures are multi-metric comparisons

- [ ] **Step 4: Re-run the visualization suite**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/visualization \
  tests/optimizers/test_comparison_summary.py -v
```

Expected:

- PASS

- [ ] **Step 5: Run a real `raw + union` verification suite**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli run-benchmark-suite \
  --optimization-spec scenarios/optimization/s1_typical_raw.yaml \
  --optimization-spec scenarios/optimization/s1_typical_union.yaml \
  --mode raw \
  --mode union \
  --benchmark-seed 11 \
  --scenario-runs-root ./scenario_runs
```

Expected:

- a new run under `scenario_runs/s1_typical/<MMDD_HHMM>__raw_union/`
- white-background scientific SVGs under representative, mode, and comparison `figures/`
- no overflow text in exported SVGs
- `comparison/figures/fields.svg` showing actual field panels
- `comparison/figures/progress.svg` showing multiple progress metrics

- [ ] **Step 6: Verify required outputs exist**

Run:

```bash
latest=$(ls -1 scenario_runs/s1_typical | sort | tail -n 1)
find "scenario_runs/s1_typical/$latest" -name "*.svg" | sort
find "scenario_runs/s1_typical/$latest" -name "*.html" | sort
```

Expected:

- representative `layout.svg`, `temperature-field.svg`, `temperature-contours.svg`, `gradient-field.svg`
- mode `mode-summary.svg`
- comparison `progress.svg` and `fields.svg`

- [ ] **Step 7: Commit**

```bash
git add \
  visualization/case_pages.py \
  visualization/mode_pages.py \
  visualization/comparison_pages.py \
  README.md \
  docs/superpowers/specs/2026-04-02-s1-typical-visualization-and-logging-reset-design.md \
  tests/visualization/test_case_pages.py \
  tests/visualization/test_mode_pages.py \
  tests/visualization/test_comparison_pages.py
git commit -m "feat: refine s1_typical figures for scientific export"
```
