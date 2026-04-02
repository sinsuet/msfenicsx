# S1 Typical Visualization And Logging Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current experiment/dashboard logging stack with a single-case-first `s1_typical` observability system built around `scenario_runs/s1_typical/<MMDD_HHMM>__<mode_slug>/`, representative physical-field pages, mixed-mode comparison pages, and full LLM prompt/decision/report evidence.

**Architecture:** Introduce a new run-suite layer that owns run ids, shared snapshots, and `raw / union / llm` mode directories under one run root. Push representative bundles to carry page-ready field exports and derived summaries, then render single-case pages, mode indexes, mixed-mode comparison pages, and LLM decision/report surfaces from those summaries rather than from scattered raw logs. Remove the old experiment-root and template-comparison visualization path once the new tree is verified.

**Tech Stack:** Python 3.12, pytest, NumPy, PyYAML, JSON/JSONL artifacts, FEniCSx (`dolfinx`, `ufl`, `mpi4py`, `petsc4py`) field sampling, repository-local HTML/SVG renderers in `visualization/`

---

Spec reference:

- `docs/superpowers/specs/2026-04-02-s1-typical-visualization-and-logging-reset-design.md`

Scope note:

- Keep this as one implementation plan because run layout, artifact contracts, field exports, comparison pages, and LLM evidence all depend on the same new run tree and should not ship as disconnected partial workflows.

Implementation guardrails:

- The only active paper-facing root is `scenario_runs/s1_typical/<run_id>/`.
- `run_id` must use `<MMDD_HHMM>__<mode_slug>` with stable mode ordering: `raw`, `union`, `llm`.
- Single-case solved pages are the primary viewing object.
- Mixed-mode comparison pages are secondary and must compare matched evaluation budgets on `evaluation_index`.
- `llm` must preserve complete prompt and decision evidence, then derive readable key-decision summaries and a report from it.
- Do not keep compatibility shims that continue to emit `scenario_runs/optimizations/...`, `experiments/...`, or `template_comparison` outputs as active workflow paths.

## File Structure

### Run Layout And Suite Orchestration

- Create: `optimizers/run_layout.py`
  Own `run_id` generation, root allocation, manifest writing, and directory initialization for `scenario_runs/s1_typical/<run_id>/`.
- Create: `optimizers/run_suite.py`
  Orchestrate single-mode and mixed-mode runs under one root, snapshot shared inputs, dispatch per-mode runs, and trigger derived summaries/pages.
- Modify: `optimizers/cli.py`
  Replace `run-mode-experiment` with a run-suite entrypoint that accepts one or more modes and seed lists.
- Modify: `optimizers/io.py`
  Add helpers for loading multiple optimization specs into one suite invocation without duplicating template/evaluation resolution logic.
- Modify: `tests/optimizers/test_optimizer_cli.py`
  Replace old experiment-root assertions with new suite-root, per-mode, and comparison-path assertions.
- Modify: `tests/optimizers/experiment_fixtures.py`
  Replace experiment-style fixtures with new run-suite fixtures.
- Create: `tests/optimizers/test_run_layout.py`
  Cover `run_id` formatting, stable mode ordering, and root directory structure.

### Artifact Contracts And Derived Summaries

- Modify: `optimizers/problem.py`
  Extend `CandidateArtifacts` or equivalent to carry page-facing field-export payloads alongside case/solution/evaluation artifacts.
- Modify: `optimizers/artifacts.py`
  Write new mode/seed/representative bundle layout and preserve runtime logs plus derived summary placeholders.
- Modify: `optimizers/run_telemetry.py`
  Add progress-timeline and milestone generation keyed by `evaluation_index`.
- Create: `optimizers/mode_summary.py`
  Build per-mode summaries from seed bundles instead of experiment containers.
- Create: `optimizers/comparison_summary.py`
  Build mixed-mode scoreboard, seed delta, field alignment, and Pareto comparison summaries.
- Create: `optimizers/llm_decision_summary.py`
  Build `llm_decision_log.jsonl`, `llm_key_decisions.json`, and report-facing tables from raw traces.
- Modify: `optimizers/llm_summary.py`
  Keep runtime/prompt/decision aggregates, but redirect them into the new mode-local summary flow.
- Modify: `tests/optimizers/test_optimizer_cli.py`
  Add assertions for `shared/`, `comparison/`, `mode/`, `seed/`, and representative manifests.
- Create: `tests/optimizers/test_mode_summary.py`
  Cover per-mode summary generation.
- Create: `tests/optimizers/test_comparison_summary.py`
  Cover cross-mode scoreboard and delta-table generation.
- Create: `tests/optimizers/test_llm_decision_summary.py`
  Cover full-decision rows, key-decision triggers, and report-table payloads.

### Solver-Side Field Exports And Bundle Enrichment

- Create: `core/solver/field_export.py`
  Sample regular-grid temperature and gradient-magnitude arrays plus page-facing metadata from solved functions.
- Modify: `core/solver/field_sampler.py`
  Keep canonical `summary_metrics` and `component_summaries`, but align record metadata with exported field artifacts.
- Modify: `core/solver/nonlinear_solver.py`
  Return or expose enough solve-time data for artifact writers to persist field exports without polluting canonical contracts.
- Modify: `core/solver/solution_builder.py`
  Keep `ThermalSolution` canonical while allowing references to field-export artifacts in `field_records`.
- Modify: `core/io/scenario_runs.py`
  Extend standalone solve bundles to include `summaries/`, `pages/`, and richer figures/fields layout.
- Modify: `evaluation/artifacts.py`
  Keep `evaluation.yaml` wiring correct inside enriched single-case bundles.
- Modify: `core/cli/main.py`
  Trigger page-ready case bundle generation from `solve-case`.
- Modify: `evaluation/cli.py`
  Preserve `evaluation.yaml` inside enriched bundle roots.
- Modify: `tests/io/test_scenario_runs.py`
  Replace current minimal bundle assertions with new single-case bundle layout assertions.
- Create: `tests/solver/test_field_export.py`
  Cover regular-grid temperature export, gradient export, and `field_view.json` metadata generation.

### Page Rendering

- Create: `visualization/case_pages.py`
  Render representative and standalone single-case pages.
- Create: `visualization/mode_pages.py`
  Render per-mode index pages linking seeds, representatives, summaries, and single-case pages.
- Create: `visualization/comparison_pages.py`
  Render mixed-mode `index`, `progress`, `fields`, `pareto`, and `seeds` pages.
- Create: `visualization/llm_pages.py`
  Render `llm_decisions.html` and `llm_key_decisions.html`.
- Create: `visualization/llm_reports.py`
  Render `llm_experiment_summary.md` and `llm_experiment_summary.html`, plus comparison-side summary markdown when applicable.
- Modify: `visualization/static_assets.py`
  Add reusable primitives for panel layout, field heatmaps, aligned comparison strips, milestone cards, and decision cards.
- Modify: `visualization/__init__.py`
  Export only the new page/report rendering entrypoints.
- Create: `tests/visualization/test_case_pages.py`
- Create: `tests/visualization/test_mode_pages.py`
- Create: `tests/visualization/test_comparison_pages.py`
- Create: `tests/visualization/test_llm_pages.py`
- Create: `tests/visualization/test_llm_reports.py`

### Documentation And Cleanup

- Modify: `README.md`
  Replace old experiment/dashboard path documentation with the new run root and page/report outputs.
- Modify: `AGENTS.md`
  Update repository guidance so the new run tree and removal rules are authoritative.
- Delete: `optimizers/experiment_layout.py`
- Delete: `optimizers/experiment_runner.py`
- Delete: `optimizers/experiment_summary.py`
- Delete: `visualization/optimizer_overview.py`
- Delete: `visualization/controller_mechanism.py`
- Delete: `visualization/llm_dashboard.py`
- Delete: `visualization/template_comparison.py`
- Delete: `visualization/report_beamer_pack.py`
- Delete: `tests/visualization/test_optimizer_overview.py`
- Delete: `tests/visualization/test_render_optimizer_overview.py`
- Delete: `tests/visualization/test_controller_mechanism.py`
- Delete: `tests/visualization/test_llm_dashboard.py`
- Delete: `tests/visualization/test_template_comparison.py`
- Delete: `tests/artifacts/optimizer_overview/nsga2_three_mode_overview.json`
- Delete: `tests/artifacts/optimizer_overview/nsga2_three_mode_overview.png`

## Task 1: Introduce The New Run Layout And `run_id` Rules

**Files:**
- Create: `optimizers/run_layout.py`
- Modify: `tests/optimizers/experiment_fixtures.py`
- Create: `tests/optimizers/test_run_layout.py`

- [ ] **Step 1: Write the failing run-layout tests**

Add tests that require:

```python
def test_build_run_id_orders_modes_stably() -> None:
    assert build_run_id(datetime(2026, 4, 2, 15, 30), ["llm", "raw", "union"]) == "0402_1530__raw_union_llm"
```

```python
def test_initialize_run_root_creates_shared_and_mode_directories(tmp_path: Path) -> None:
    root = initialize_run_root(tmp_path / "scenario_runs", "s1_typical", "0402_1530__raw_union", ["raw", "union"])
    assert (root / "shared").is_dir()
    assert (root / "raw").is_dir()
    assert (root / "union").is_dir()
    assert not (root / "comparison").exists()
```

- [ ] **Step 2: Run the focused tests to confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_run_layout.py -v
```

Expected:

- FAIL because `optimizers.run_layout` and the new helpers do not exist yet

- [ ] **Step 3: Implement `run_id` generation and root allocation**

Create `optimizers/run_layout.py` with:

```python
MODE_ORDER = ("raw", "union", "llm")

def build_run_id(started_at: datetime, modes: Sequence[str]) -> str:
    ordered = [mode for mode in MODE_ORDER if mode in set(modes)]
    return f"{started_at:%m%d_%H%M}__{'_'.join(ordered)}"
```

Also add helpers for:

- root allocation under `scenario_runs/s1_typical/<run_id>/`
- manifest writing
- shared/mode/comparison directory creation

- [ ] **Step 4: Update test fixtures to emit new-style run roots**

Replace experiment-style fixture setup with helpers that can create:

- single-mode roots
- mixed-mode roots
- representative bundles inside `mode/seeds/seed-<n>/representatives/...`

- [ ] **Step 5: Re-run the focused run-layout tests**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add \
  optimizers/run_layout.py \
  tests/optimizers/experiment_fixtures.py \
  tests/optimizers/test_run_layout.py
git commit -m "feat: add s1_typical run layout helpers"
```

## Task 2: Replace Experiment CLI Flow With A Run-Suite Entry Point

**Files:**
- Create: `optimizers/run_suite.py`
- Modify: `optimizers/cli.py`
- Modify: `optimizers/io.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`

- [ ] **Step 1: Write the failing CLI and orchestration tests**

Add tests that require:

```python
def test_run_benchmark_suite_single_mode_writes_run_root(tmp_path: Path) -> None:
    exit_code = main([
        "run-benchmark-suite",
        "--mode", "raw",
        "--optimization-spec", str(_write_small_raw_spec(tmp_path)),
        "--benchmark-seed", "11",
        "--scenario-runs-root", str(tmp_path / "scenario_runs"),
        "--started-at", "2026-04-02T15:30:00",
    ])
    assert exit_code == 0
    assert (tmp_path / "scenario_runs" / "s1_typical" / "0402_1530__raw" / "raw").is_dir()
```

```python
def test_run_benchmark_suite_mixed_mode_writes_comparison_root(tmp_path: Path) -> None:
    ...
    assert (run_root / "comparison").is_dir()
    assert (run_root / "raw").is_dir()
    assert (run_root / "union").is_dir()
```

- [ ] **Step 2: Run the focused CLI tests to confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_optimizer_cli.py -k "run_benchmark_suite" -v
```

Expected:

- FAIL because `run-benchmark-suite` does not exist yet

- [ ] **Step 3: Implement the suite runner**

Create `optimizers/run_suite.py` with helpers that:

- accept one or more modes
- load the correct raw/union/llm spec(s)
- allocate one shared run root
- snapshot shared inputs into `shared/`
- dispatch each enabled mode into `<run_id>/<mode>/seeds/seed-<n>/`

- [ ] **Step 4: Replace the old CLI command**

Update `optimizers/cli.py` so:

- `run-mode-experiment` is removed
- `run-benchmark-suite` becomes the active entrypoint
- the command supports both single-mode and mixed-mode execution

- [ ] **Step 5: Re-run the focused CLI tests**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add \
  optimizers/run_suite.py \
  optimizers/cli.py \
  optimizers/io.py \
  tests/optimizers/test_optimizer_cli.py
git commit -m "feat: add run suite orchestration"
```

## Task 3: Enrich Solve Outputs With Page-Ready Field Exports

**Files:**
- Create: `core/solver/field_export.py`
- Modify: `core/solver/nonlinear_solver.py`
- Modify: `core/solver/field_sampler.py`
- Modify: `core/solver/solution_builder.py`
- Create: `tests/solver/test_field_export.py`

- [ ] **Step 1: Write the failing field-export tests**

Add tests that require:

```python
def test_export_field_views_writes_temperature_and_gradient_grids(tmp_path: Path) -> None:
    payload = export_field_views(temperature_function, panel_domain={"width": 1.0, "height": 0.8}, components=_components())
    assert payload["field_view"]["temperature"]["grid_shape"] == [81, 101]
    assert "gradient_magnitude" in payload["arrays"]
```

```python
def test_sample_solution_fields_records_exportable_field_paths(tmp_path: Path) -> None:
    sampled = sample_solution_fields(...)
    assert sampled["field_records"]["temperature"]["kind"] == "cg1_dofs"
    assert "temperature_gradient_rms" in sampled["summary_metrics"]
```

- [ ] **Step 2: Run the focused solver tests to confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/solver/test_field_export.py \
  tests/solver/test_gradient_metrics.py -v
```

Expected:

- FAIL because regular-grid field export helpers do not exist yet

- [ ] **Step 3: Implement grid export and metadata generation**

Create `core/solver/field_export.py` with helpers that:

- sample temperature onto a regular panel grid
- sample gradient magnitude onto the same grid
- produce `field_view.json` metadata with:
  - color ranges
  - contour levels
  - hotspot markers
  - sink geometry
  - component rectangles

- [ ] **Step 4: Thread field exports through solve-time outputs**

Update `nonlinear_solver.py` and `solution_builder.py` so solve results can hand representative bundles:

- canonical solution data
- page-facing field export payloads

without stuffing page-only arrays into canonical YAML structures

- [ ] **Step 5: Re-run the focused solver tests**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add \
  core/solver/field_export.py \
  core/solver/nonlinear_solver.py \
  core/solver/field_sampler.py \
  core/solver/solution_builder.py \
  tests/solver/test_field_export.py
git commit -m "feat: export page-ready thermal field grids"
```

## Task 4: Extend Case Bundles And Representative Artifacts

**Files:**
- Modify: `optimizers/problem.py`
- Modify: `optimizers/artifacts.py`
- Modify: `core/io/scenario_runs.py`
- Modify: `evaluation/artifacts.py`
- Modify: `core/cli/main.py`
- Modify: `evaluation/cli.py`
- Modify: `tests/io/test_scenario_runs.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`

- [ ] **Step 1: Write the failing bundle-layout tests**

Add tests that require:

```python
def test_write_case_solution_bundle_creates_summaries_pages_and_fields(tmp_path: Path) -> None:
    bundle_root = write_case_solution_bundle(tmp_path, case, solution)
    assert (bundle_root / "summaries").is_dir()
    assert (bundle_root / "pages").is_dir()
    assert (bundle_root / "fields").is_dir()
```

```python
def test_write_optimization_artifacts_writes_representative_case_bundle_with_field_view(tmp_path: Path) -> None:
    ...
    assert (representative_root / "summaries" / "field_view.json").exists()
    assert (representative_root / "pages" / "index.html").exists() is False
```

- [ ] **Step 2: Run the focused bundle tests to confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/io/test_scenario_runs.py \
  tests/optimizers/test_optimizer_cli.py -k "bundle or representative" -v
```

Expected:

- FAIL because bundle roots do not yet create the enriched structure

- [ ] **Step 3: Extend artifact writers**

Update `optimizers/problem.py` and `optimizers/artifacts.py` so representative bundles write:

- `case.yaml`
- `solution.yaml`
- `evaluation.yaml`
- `fields/*.npz`
- `summaries/field_view.json`
- `summaries/representative_summary.json`
- runtime logs and manifests in the new directory structure

- [ ] **Step 4: Extend standalone solve/evaluate bundle writing**

Update:

- `core/io/scenario_runs.py`
- `core/cli/main.py`
- `evaluation/artifacts.py`
- `evaluation/cli.py`

so standalone `solve-case` and `evaluate-case` bundles use the same enriched single-case layout philosophy

- [ ] **Step 5: Re-run the focused bundle tests**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add \
  optimizers/problem.py \
  optimizers/artifacts.py \
  core/io/scenario_runs.py \
  evaluation/artifacts.py \
  core/cli/main.py \
  evaluation/cli.py \
  tests/io/test_scenario_runs.py \
  tests/optimizers/test_optimizer_cli.py
git commit -m "feat: enrich single-case and representative bundles"
```

## Task 5: Build Per-Mode Summaries, Progress Timelines, And Milestones

**Files:**
- Modify: `optimizers/run_telemetry.py`
- Create: `optimizers/mode_summary.py`
- Create: `tests/optimizers/test_mode_summary.py`

- [ ] **Step 1: Write the failing mode-summary tests**

Add tests that require:

```python
def test_build_mode_summary_writes_progress_timeline_and_milestones(tmp_path: Path) -> None:
    written = build_mode_summaries(mode_root)
    assert (mode_root / "summaries" / "mode_summary.json").exists()
    assert (mode_root / "summaries" / "progress_timeline__seed-11.jsonl").exists()
    assert (mode_root / "summaries" / "milestones__seed-11.json").exists()
```

```python
def test_progress_timeline_tracks_first_feasible_and_pareto_growth() -> None:
    rows = build_progress_timeline(...)
    assert rows[-1]["feasible_count_so_far"] >= 1
    assert rows[-1]["pareto_size_so_far"] >= 1
```

- [ ] **Step 2: Run the focused summary tests to confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_mode_summary.py -v
```

Expected:

- FAIL because `build_mode_summaries` and progress helpers do not exist yet

- [ ] **Step 3: Add progress and milestone helpers**

Update `optimizers/run_telemetry.py` to generate per-evaluation rows containing:

- `budget_fraction`
- `feasible_count_so_far`
- `feasible_rate_so_far`
- `first_feasible_eval_so_far`
- `pareto_size_so_far`
- `best_temperature_max_so_far`
- `best_gradient_rms_so_far`
- `best_total_constraint_violation_so_far`

- [ ] **Step 4: Implement per-mode summary assembly**

Create `optimizers/mode_summary.py` to write:

- `mode_summary.json`
- `seed_summary.json`
- `progress_timeline__seed-<n>.jsonl`
- `milestones__seed-<n>.json`

and preserve mode-level manifest links for pages and reports

- [ ] **Step 5: Re-run the focused summary tests**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add \
  optimizers/run_telemetry.py \
  optimizers/mode_summary.py \
  tests/optimizers/test_mode_summary.py
git commit -m "feat: add mode progress summaries"
```

## Task 6: Render Single-Case Pages And Mode Indexes

**Files:**
- Create: `visualization/case_pages.py`
- Create: `visualization/mode_pages.py`
- Modify: `visualization/static_assets.py`
- Modify: `visualization/__init__.py`
- Create: `tests/visualization/test_case_pages.py`
- Create: `tests/visualization/test_mode_pages.py`

- [ ] **Step 1: Write the failing page-renderer tests**

Add tests that require:

```python
def test_render_case_page_writes_layout_temperature_and_gradient_sections(tmp_path: Path) -> None:
    output_path = render_case_page(representative_root)
    html = output_path.read_text(encoding="utf-8")
    assert "Temperature Field" in html
    assert "Gradient Magnitude" in html
    assert "Constraint Margins" in html
```

```python
def test_render_mode_index_links_seed_pages_and_representatives(tmp_path: Path) -> None:
    output_path = render_mode_pages(mode_root)["index"]
    html = output_path.read_text(encoding="utf-8")
    assert "seed-11" in html
    assert "knee" in html
```

- [ ] **Step 2: Run the focused page tests to confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/visualization/test_case_pages.py \
  tests/visualization/test_mode_pages.py -v
```

Expected:

- FAIL because the new renderers do not exist yet

- [ ] **Step 3: Add field and layout SVG/HTML primitives**

Extend `visualization/static_assets.py` with helpers for:

- panel layout rectangles and sink strips
- raster-like field heatmap tiles or SVG cells
- contour legends and metric cards
- component tables and margin tables

- [ ] **Step 4: Implement single-case and mode pages**

Create renderers that build:

- representative `pages/index.html`
- mode `pages/index.html`
- links between representative pages, mode pages, and summary artifacts

- [ ] **Step 5: Re-run the focused page tests**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add \
  visualization/case_pages.py \
  visualization/mode_pages.py \
  visualization/static_assets.py \
  visualization/__init__.py \
  tests/visualization/test_case_pages.py \
  tests/visualization/test_mode_pages.py
git commit -m "feat: render single-case thermal pages"
```

## Task 7: Build Mixed-Mode Comparison Summaries And Pages

**Files:**
- Create: `optimizers/comparison_summary.py`
- Create: `visualization/comparison_pages.py`
- Create: `tests/optimizers/test_comparison_summary.py`
- Create: `tests/visualization/test_comparison_pages.py`

- [ ] **Step 1: Write the failing comparison tests**

Add tests that require:

```python
def test_build_comparison_summary_writes_seed_delta_and_progress_matrix(tmp_path: Path) -> None:
    written = build_comparison_summaries(run_root)
    assert (run_root / "comparison" / "summaries" / "seed_delta_table.json").exists()
    assert (run_root / "comparison" / "summaries" / "progress_matrix.json").exists()
```

```python
def test_render_comparison_pages_writes_progress_and_fields_html(tmp_path: Path) -> None:
    outputs = render_comparison_pages(run_root)
    assert (run_root / "comparison" / "pages" / "progress.html").exists()
    assert (run_root / "comparison" / "pages" / "fields.html").exists()
    assert "first feasible" in outputs["progress"].read_text(encoding="utf-8").lower()
```

- [ ] **Step 2: Run the focused comparison tests to confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_comparison_summary.py \
  tests/visualization/test_comparison_pages.py -v
```

Expected:

- FAIL because mixed-mode summaries and pages do not exist yet

- [ ] **Step 3: Implement mixed-mode derived summaries**

Create summary builders for:

- `mode_scoreboard.json`
- `seed_delta_table.json`
- `progress_matrix.json`
- `pareto_comparison.json`
- `field_alignment.json`
- `controller_comparison.json` when both `union` and `llm` are present

- [ ] **Step 4: Implement comparison pages**

Render:

- `index.html`
- `progress.html`
- `fields.html`
- `pareto.html`
- `seeds.html`
- `controller.html` when applicable

with the primary x-axis always based on `evaluation_index`

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
git commit -m "feat: add mixed-mode comparison summaries and pages"
```

## Task 8: Add Full LLM Decision Logs And Key-Decision Detection

**Files:**
- Create: `optimizers/llm_decision_summary.py`
- Modify: `optimizers/llm_summary.py`
- Modify: `optimizers/artifacts.py`
- Modify: `optimizers/run_suite.py`
- Create: `tests/optimizers/test_llm_decision_summary.py`

- [ ] **Step 1: Write the failing LLM decision-summary tests**

Add tests that require:

```python
def test_build_llm_decision_log_preserves_prompt_response_and_outcome_refs(tmp_path: Path) -> None:
    written = build_llm_decision_summaries(llm_mode_root)
    rows = load_jsonl_rows(llm_mode_root / "summaries" / "llm_decision_log.jsonl")
    assert rows[0]["selected_operator_id"]
    assert rows[0]["prompt_ref"]
    assert rows[0]["response_ref"]
```

```python
def test_key_decision_detection_flags_first_feasible_and_pareto_expansion(tmp_path: Path) -> None:
    payload = load_json(llm_mode_root / "summaries" / "llm_key_decisions.json")
    trigger_ids = {row["trigger_type"] for row in payload["rows"]}
    assert "first_feasible_trigger" in trigger_ids
    assert "pareto_expansion_trigger" in trigger_ids
```

- [ ] **Step 2: Run the focused LLM summary tests to confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_decision_summary.py -v
```

Expected:

- FAIL because LLM decision-log builders do not exist yet

- [ ] **Step 3: Build full decision-log rows**

Create `optimizers/llm_decision_summary.py` to merge:

- request trace
- response trace
- controller trace
- operator trace
- progress timeline

into `llm_decision_log.jsonl`

- [ ] **Step 4: Add key-decision detection**

Implement trigger tagging for:

- first feasible
- feasible recovery
- Pareto expansion
- peak drop
- gradient drop
- violation collapse
- anti-collapse
- fallback rescue
- operator switch

- [ ] **Step 5: Re-run the focused LLM summary tests**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add \
  optimizers/llm_decision_summary.py \
  optimizers/llm_summary.py \
  optimizers/artifacts.py \
  optimizers/run_suite.py \
  tests/optimizers/test_llm_decision_summary.py
git commit -m "feat: add llm decision logs and key decisions"
```

## Task 9: Render LLM Decision Pages And Summary Reports

**Files:**
- Create: `visualization/llm_pages.py`
- Create: `visualization/llm_reports.py`
- Create: `tests/visualization/test_llm_pages.py`
- Create: `tests/visualization/test_llm_reports.py`

- [ ] **Step 1: Write the failing LLM page/report tests**

Add tests that require:

```python
def test_render_llm_decisions_page_includes_prompt_and_selected_operator(tmp_path: Path) -> None:
    outputs = render_llm_pages(llm_mode_root)
    html = outputs["decisions"].read_text(encoding="utf-8")
    assert "system prompt" in html.lower()
    assert "selected operator" in html.lower()
```

```python
def test_render_llm_experiment_summary_writes_markdown_with_tables(tmp_path: Path) -> None:
    report_paths = render_llm_reports(llm_mode_root, comparison_root=None)
    markdown = report_paths["markdown"].read_text(encoding="utf-8")
    assert "| Mode |" in markdown
    assert "Key Improvement Points" in markdown
    assert "Risk" in markdown
```

- [ ] **Step 2: Run the focused LLM page/report tests to confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/visualization/test_llm_pages.py \
  tests/visualization/test_llm_reports.py -v
```

Expected:

- FAIL because the new LLM pages and reports do not exist yet

- [ ] **Step 3: Implement decision pages**

Create `visualization/llm_pages.py` to render:

- `pages/llm_decisions.html`
- `pages/llm_key_decisions.html`

with expandable sections for:

- state summary
- full prompt
- full response
- guardrail details
- outcome deltas

- [ ] **Step 4: Implement deterministic LLM reports**

Create `visualization/llm_reports.py` to generate:

- `reports/llm_experiment_summary.md`
- `reports/llm_experiment_summary.html`
- `comparison/reports/llm_vs_union_vs_raw_summary.md` when mixed-mode outputs exist

using template-driven content plus summary tables rather than unconstrained free-form writing

- [ ] **Step 5: Re-run the focused LLM page/report tests**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add \
  visualization/llm_pages.py \
  visualization/llm_reports.py \
  tests/visualization/test_llm_pages.py \
  tests/visualization/test_llm_reports.py
git commit -m "feat: render llm decision pages and reports"
```

## Task 10: Remove The Old Visualization Stack And Update Docs

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Delete: `optimizers/experiment_layout.py`
- Delete: `optimizers/experiment_runner.py`
- Delete: `optimizers/experiment_summary.py`
- Delete: `visualization/optimizer_overview.py`
- Delete: `visualization/controller_mechanism.py`
- Delete: `visualization/llm_dashboard.py`
- Delete: `visualization/template_comparison.py`
- Delete: `visualization/report_beamer_pack.py`
- Delete: `tests/visualization/test_optimizer_overview.py`
- Delete: `tests/visualization/test_render_optimizer_overview.py`
- Delete: `tests/visualization/test_controller_mechanism.py`
- Delete: `tests/visualization/test_llm_dashboard.py`
- Delete: `tests/visualization/test_template_comparison.py`
- Delete: `tests/artifacts/optimizer_overview/nsga2_three_mode_overview.json`
- Delete: `tests/artifacts/optimizer_overview/nsga2_three_mode_overview.png`

- [ ] **Step 1: Write the failing cleanup regression tests**

Add or update tests that require:

```python
def test_new_suite_run_does_not_emit_experiment_or_template_comparison_paths(tmp_path: Path) -> None:
    ...
    assert not any(path.name == "experiments" for path in run_root.rglob("*"))
    assert not any(path.name == "comparisons" for path in run_root.rglob("*"))
```

- [ ] **Step 2: Run the focused cleanup tests to confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_optimizer_cli.py -k "not emit_experiment" -v
```

Expected:

- FAIL because old modules and path assumptions still exist

- [ ] **Step 3: Remove obsolete modules and docs**

Delete the retired experiment/dashboard modules and rewrite `README.md` and `AGENTS.md` so the new run tree is the only documented active workflow.

- [ ] **Step 4: Run the visualization and optimizer targeted suites**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers \
  tests/visualization \
  tests/io/test_scenario_runs.py \
  tests/solver/test_field_export.py -v
```

Expected:

- PASS

- [ ] **Step 5: Run the broader smoke suite**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/cli \
  tests/evaluation \
  tests/optimizers \
  tests/visualization \
  tests/io \
  tests/solver -v
```

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add README.md AGENTS.md tests
git rm \
  optimizers/experiment_layout.py \
  optimizers/experiment_runner.py \
  optimizers/experiment_summary.py \
  visualization/optimizer_overview.py \
  visualization/controller_mechanism.py \
  visualization/llm_dashboard.py \
  visualization/template_comparison.py \
  visualization/report_beamer_pack.py \
  tests/visualization/test_optimizer_overview.py \
  tests/visualization/test_render_optimizer_overview.py \
  tests/visualization/test_controller_mechanism.py \
  tests/visualization/test_llm_dashboard.py \
  tests/visualization/test_template_comparison.py \
  tests/artifacts/optimizer_overview/nsga2_three_mode_overview.json \
  tests/artifacts/optimizer_overview/nsga2_three_mode_overview.png
git commit -m "refactor: reset visualization and logging stack for s1_typical"
```

## Verification Checklist

Before calling the work complete, verify all of the following:

- single-mode run creates `scenario_runs/s1_typical/<run_id>/<mode>/...`
- mixed-mode run creates one shared root plus `comparison/`
- representative bundles contain:
  - canonical YAML snapshots
  - field arrays
  - field-view summaries
  - single-case pages
- comparison pages use `evaluation_index` as the primary progress axis
- LLM mode writes:
  - full request/response traces
  - full decision log
  - key-decision summary
  - decision pages
  - experiment summary report
- no active path writes `scenario_runs/optimizations/...`
- no active renderer depends on `template_comparison` or experiment-root assumptions

## Review Note

This plan was self-reviewed in the main session because the current thread did not include explicit user authorization to spawn a plan-review subagent. If plan changes are requested, update this file and repeat the self-review before execution.
