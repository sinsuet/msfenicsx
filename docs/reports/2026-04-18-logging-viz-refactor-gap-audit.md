# Logging & Visualization Refactor Gap Audit

- Date: 2026-04-18
- Baseline audited: recovered `feat/logging-viz-refactor` merge at commit `3fdc4bb`
- Compared against:
  - `docs/superpowers/specs/2026-04-16-logging-visualization-refactor-design.md`
  - `docs/superpowers/plans/2026-04-16-logging-visualization-refactor.md`

## 0. 2026-04-20 Status Update

The concrete follow-up gaps called out in §§4.2-4.6 have now been closed on `main`.

- `render-assets` now renders:
  - `pareto_front`
  - `objective_progress`
  - `layout_initial` / `layout_final`
  - `layout_evolution.gif` + frame PNGs
  - representative `temperature_field_<repr>` / `gradient_field_<repr>`
  - `tables/summary_statistics.*`
  - `tables/representative_points.*`
  - `analytics/decision_outcomes.csv`
- `compare-runs` now writes:
  - `pareto_overlay.*`
  - `hypervolume_comparison.*`
  - `objective_progress_comparison.*`
  - `summary_table.csv`
  - `summary_table.tex`
- `run-benchmark-suite` now auto-invokes the new render pipeline (unless `--skip-render` is passed).
- A real `10x5` smoke run via `scripts/smoke_render_assets.sh` passed on 2026-04-20.

The deferred items listed in §3 remain deferred.

## 1. Provenance Conclusion

The missing visualization/logging outputs are **not primarily a merge-loss problem after `3fdc4bb`**.

- The recovered baseline worktree at `/home/hymn/msfenicsx/.claude/worktrees/logging-viz-refactor-recovered` matches the 2026-04-16 refactor merge.
- Reflog and unreachable-commit inspection did **not** reveal a later, more-complete deleted visualization worktree.
- The only related unreachable commit found after the merge was telemetry-only WIP (`4f0f807`), not a fuller figure/CLI integration branch.

So the correct interpretation is:

- some refactor deliverables were merged and are recoverable;
- several spec items were explicitly deferred in the implementation plan;
- several other spec-promised items were never fully wired in the recovered baseline.

## 2. Implemented In The Recovered Baseline

These parts of the 2026-04-16 refactor are present and wired enough to count as real implementation:

- Matplotlib style baseline:
  - `visualization/style/baseline.py`
- Figure modules exist:
  - `visualization/figures/pareto.py`
  - `visualization/figures/hypervolume.py`
  - `visualization/figures/operator_heatmap.py`
  - `visualization/figures/temperature_field.py`
  - `visualization/figures/gradient_field.py`
  - `visualization/figures/layout_evolution.py`
- Core trace helpers exist:
  - `optimizers/traces/correlation.py`
  - `optimizers/traces/jsonl_writer.py`
  - `optimizers/traces/operator_trace.py`
  - `optimizers/traces/prompt_store.py`
- Core analytics modules exist:
  - `optimizers/analytics/loaders.py`
  - `optimizers/analytics/pareto.py`
  - `optimizers/analytics/rollups.py`
  - `optimizers/analytics/decisions.py`
  - `optimizers/analytics/heatmap.py`
- CLI subcommands exist:
  - `render-assets`
  - `compare-runs`
- `optimize-benchmark` auto-renders assets by default and exposes `--skip-render`:
  - `optimizers/cli.py`
- Colorbar regression coverage exists:
  - `tests/visualization/test_heatfield_orientation.py`
- End-to-end synthetic render-assets smoke coverage exists:
  - `tests/visualization/test_render_assets_fixtures.py`
- Layout helper coverage for flat vs wrapped seed layout exists:
  - `tests/optimizers/test_multi_seed_layout.py`

## 3. Explicitly Deferred In The 2026-04-16 Plan

The following gaps are already acknowledged by the plan itself in the "Deferred Scope" section and should not be treated as accidental merge omissions:

| Spec item | Status | Reason already recorded in plan |
| --- | --- | --- |
| `generation_summary.jsonl` schema alignment | Deferred | Existing writer kept; analytics read `evaluation_events.jsonl` directly |
| `optimizers/analytics/correlate.py` | Deferred | Join logic done inline for now |
| `optimizers/analytics/guardrails.py` | Deferred | Upstream controller does not emit full guardrail events |
| `optimizers/analytics/aggregate/{iqr,attainment,stats}.py` | Deferred | Depends on real multi-seed benchmark generation |
| `pareto.parquet` | Deferred | `pyarrow` intentionally skipped for the smoke-path implementation |
| `phase_alignment.csv` | Deferred | Depends on post-hoc phase labeling |
| `cost_per_improvement.csv` | Deferred | Depends on per-decision HV delta correlation |
| `guardrail_timeline.csv` | Deferred | Depends on guardrail event emission |
| `visualization/figures/guardrail_timeline.py` | Deferred | Blocked on `guardrail_timeline.csv` |

## 4. Spec-Promised But Not Actually Completed In The Recovered Baseline

These are the real follow-up gaps that remain after restoring the recovered baseline.

### 4.1 Prompt Externalization Was Implemented As Library Code But Never Wired Into Runtime

Evidence:

- `optimizers/traces/prompt_store.py` exists and works.
- `optimizers/operator_pool/llm_controller.py` defines:
  - `configure_trace_outputs(...)`
  - `_emit_controller_trace(...)`
- repository-wide search finds no caller of `configure_trace_outputs(...)` outside its own definition.
- `LLMOperatorController.request_trace` still stores raw `system_prompt` and `user_prompt`.
- `optimizers/llm_decision_summary.py` fabricates `prompt_ref` / `response_ref` using JSONL anchors instead of reading real `prompts/<sha1>.md`.

Impact:

- `prompts/<sha1>.md` is not produced during normal runs.
- `llm_request_trace.jsonl` still carries wide prompt bodies rather than narrow refs.
- spec § 4.5/§ 4.6 and the plan success criterion about `<1KB` request lines are not satisfied.
- `controller_trace.jsonl` new-schema emission exists in code but is not the active runtime path.

### 4.2 `render-assets` Only Renders A Narrow Slice Of The Figure Factory

Evidence:

- `optimizers/render_assets.py` currently writes:
  - `analytics/hypervolume.csv`
  - `analytics/operator_phase_heatmap.csv`
  - `figures/hypervolume_progress.*`
  - `figures/operator_phase_heatmap.*`
- it does not call:
  - `visualization.figures.pareto.render_pareto_front`
  - `visualization.figures.temperature_field.render_temperature_field`
  - `visualization.figures.gradient_field.render_gradient_field`
  - `visualization.figures.layout_evolution.render_layout_evolution`

Impact:

- per-run `pareto_front.pdf/.png` is missing;
- representative `temperature_field_<repr>` and `gradient_field_<repr>` figures are missing;
- `layout_evolution.gif` and preserved frame PNGs are missing;
- the figure modules exist, but the main asset pipeline does not reach them.

### 4.3 `render-assets` Does Not Emit The Planned Tables

Evidence:

- no repository code writes:
  - `tables/summary_statistics.csv`
  - `tables/summary_statistics.tex`
  - `tables/representative_points.csv`
  - `tables/representative_points.tex`
- `optimizers/render_assets.py` has no table-writing path.

Impact:

- spec § 3.1 / § 8.1 "reads traces, writes analytics/figures/tables" is only partially realized.

### 4.4 `decision_outcomes.csv` Exists As A Pure Helper But Is Never Persisted

Evidence:

- `optimizers/analytics/decisions.py` defines `decision_outcomes(...)`.
- repository search shows it is only exercised by `tests/optimizers/test_analytics_decisions.py`.
- no code path in `render-assets` or `compare-runs` writes `analytics/decision_outcomes.csv`.

Impact:

- spec § 5.3's only non-deferred llm-only analytics artifact is still missing from runtime output.

### 4.5 `compare-runs` Is Missing Part Of The Spec Output Contract

Evidence:

- `optimizers/compare_runs.py` currently writes:
  - `pareto_overlay.pdf/.png`
  - `summary_table.csv`
  - `inputs.yaml`
- it does not write:
  - `hypervolume_comparison.pdf/.png`
  - `summary_table.tex`

Impact:

- spec § 3.3 / § 8.2 is only partially implemented.

### 4.6 Run Layout Still Carries Legacy Scaffolding That The Spec Said To Remove

Evidence:

- `optimizers/artifacts.py` still creates seed-bundle directories:
  - `logs/`
  - `summaries/`
  - `representatives/`
  - `traces/`
- representative bundles still create:
  - `logs/`
  - `fields/`
  - `summaries/`
  - `figures/`
  - `pages/`
- `optimizers/run_layout.py` still creates mode/comparison roots with:
  - `logs`
  - `pages`
  - `reports`
- artifact filenames still include:
  - `optimization_result.json`
  - `pareto_front.json`
  - `manifest.json`
  instead of the spec's simplified `results.yaml`-centric presentation.

Impact:

- spec § 3.1 "empty logs removed" is not met;
- representative bundles are not yet reduced to the spec's minimal `case/solution/evaluation/fields` form;
- the success criterion "no empty `logs/` directories" is not met.

### 4.7 New-Schema Controller-Trace Integration Remains Unproven

Evidence:

- `tests/optimizers/test_controller_trace_new_schema.py` is still skipped with:
  - `requires harness wiring`
- `optimizers/artifacts.py` writes `traces/controller_trace.jsonl` by coercing in-memory legacy controller rows rather than by consuming the `_emit_controller_trace(...)` path.

Impact:

- the codebase contains the new trace schema implementation pieces, but the end-to-end runtime path is still legacy-biased.

## 5. Practical Reading Of The Current State

After recovery, the 2026-04-16 refactor baseline should be treated as:

- **real and worth preserving** for style baseline, JSONL trace helpers, render-assets/compare-runs CLI, field/pareto/heatmap figure modules, and representative-layout cleanup;
- **intentionally partial** for guardrail analytics, aggregate statistics, parquet, and several llm-only analytics artifacts;
- **unfinished in wiring** for prompt externalization, full figure-factory integration, tables, and complete compare-runs output.

## 6. Recommended Continuation Order

If we continue from the recovered baseline instead of drifting back into ad hoc compatibility code, the clean follow-up order is:

1. Wire `PromptStore` / `_emit_controller_trace(...)` into the live llm runtime path.
2. Extend `render_run_assets(...)` to emit:
   - `decision_outcomes.csv`
   - per-run Pareto figure
   - representative temperature/gradient figures
   - layout evolution GIF + frames
   - `tables/summary_statistics.*`
   - `tables/representative_points.*`
3. Extend `compare_runs(...)` with:
   - `hypervolume_comparison.*`
   - `summary_table.tex`
4. Remove leftover empty `logs/`, `pages/`, and `reports/` scaffolding from run artifacts, or update the spec if that scaffolding is intentionally retained.

This preserves the recovered 2026-04-16 direction and avoids reintroducing the old SVG page stack as the mainline.
