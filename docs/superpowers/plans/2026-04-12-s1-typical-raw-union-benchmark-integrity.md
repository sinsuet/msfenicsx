# S1 Typical Raw/Union Benchmark Integrity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `s1_typical` raw/union paper-facing runs semantically correct before any `llm` comparison by fixing benchmark-seed semantics, optimizer-only feasibility accounting, and candidate-level layout metrics.

**Architecture:** Keep `s1_typical` as a fixed single-case benchmark: one generated `base_case`, baseline stored as a reference point, and optimizer progress measured only from `source=optimizer` evaluations. Persist enough layout context in the case provenance to recompute layout metrics from actual candidate geometry after repair, then feed those recomputed metrics through evaluation, summaries, and pages. Reject misleading multi-`benchmark_seed` suite runs for `s1_typical` and update docs/examples to use a single benchmark case.

**Tech Stack:** Python, pytest, YAML/JSON artifacts, current `core/`, `evaluation/`, `optimizers/`, `visualization/` stack, `/home/hymn/miniconda3/bin/conda run -n msfenicsx ...`

---

## File Map

### Runtime code

- Modify: `core/generator/layout_metrics.py`
- Modify: `core/generator/pipeline.py`
- Modify: `evaluation/metrics.py`
- Modify: `optimizers/repair.py`
- Modify: `optimizers/drivers/raw_driver.py`
- Modify: `optimizers/run_telemetry.py`
- Modify: `optimizers/mode_summary.py`
- Modify: `optimizers/comparison_summary.py`
- Modify: `optimizers/operator_pool/domain_state.py`
- Modify: `optimizers/operator_pool/diagnostics.py`
- Modify: `optimizers/run_suite.py`
- Modify: `visualization/case_pages.py`

### CLI / docs

- Modify: `optimizers/cli.py`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/reports/2026-04-10-s1-typical-end-to-end-flow-and-seed11-walkthrough.md`

### Tests

- Modify: `tests/evaluation/test_engine.py`
- Modify: `tests/optimizers/test_repair.py`
- Modify: `tests/optimizers/test_mode_summary.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`
- Modify: `tests/optimizers/experiment_fixtures.py`
- Modify: `tests/visualization/test_case_pages.py`
- Create: `tests/optimizers/test_run_telemetry.py`
- Create: `tests/optimizers/test_run_suite.py`

## Task 1: Lock `s1_typical` To A Single Benchmark Case

**Files:**
- Modify: `optimizers/run_suite.py`
- Modify: `optimizers/cli.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`
- Create: `tests/optimizers/test_run_suite.py`
- Modify: `README.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Write a failing suite-policy test for multiple benchmark seeds**

Add `tests/optimizers/test_run_suite.py` with a regression test that passes an `s1_typical` optimization spec plus `benchmark_seeds=[11, 17]` into `run_benchmark_suite(...)` and asserts `ValueError` with a message like:

```python
with pytest.raises(ValueError, match="s1_typical.*single benchmark_seed"):
    run_benchmark_suite(
        optimization_spec_paths=[raw_spec_path],
        benchmark_seeds=[11, 17],
        scenario_runs_root=tmp_path / "scenario_runs",
        modes=["raw"],
    )
```

- [ ] **Step 2: Write a failing CLI regression test for the same policy**

Extend `tests/optimizers/test_optimizer_cli.py` with a `run-benchmark-suite` invocation that passes two `--benchmark-seed` values for an `s1_typical` spec and assert the CLI raises `ValueError`.

- [ ] **Step 3: Implement the suite guardrail**

In `optimizers/run_suite.py`, add a helper near `run_benchmark_suite(...)`:

```python
def _validate_benchmark_seed_policy(*, scenario_template_id: str, benchmark_seeds: Sequence[int]) -> None:
    if scenario_template_id == "s1_typical" and len(set(int(seed) for seed in benchmark_seeds)) > 1:
        raise ValueError("s1_typical is a fixed single-case benchmark; pass exactly one benchmark_seed.")
```

Call it after `_resolve_template_id(...)` and after effective seeds are computed.

- [ ] **Step 4: Keep the CLI thin**

Do not duplicate the rule in `optimizers/cli.py`; let the CLI surface the `run_suite.py` error directly so the policy lives in one place.

- [ ] **Step 5: Update repository guidance and examples**

Change the `run-benchmark-suite` examples in:

- `README.md`
- `AGENTS.md`

from three `--benchmark-seed` entries to one canonical `--benchmark-seed 11` example.

- [ ] **Step 6: Run the focused policy tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_run_suite.py tests/optimizers/test_optimizer_cli.py
```

Expected:

- the new suite-policy tests pass
- existing nearby CLI tests still pass

## Task 2: Add Shared Candidate-Geometry Layout Metric Recalculation

**Files:**
- Modify: `core/generator/layout_metrics.py`
- Modify: `core/generator/pipeline.py`
- Modify: `visualization/case_pages.py`
- Modify: `tests/evaluation/test_engine.py`
- Modify: `tests/visualization/test_case_pages.py`

- [ ] **Step 1: Write a failing evaluation test that proves stale provenance is wrong**

Extend `tests/evaluation/test_engine.py` with a case that includes:

- `provenance.layout_metrics` set to obviously stale values like `0.999`
- `provenance.layout_context` holding `placement_region`, `active_deck`, and `dense_core`
- component geometry whose recomputed metrics are not `0.999`

Assert `evaluate_case_solution(...)` reports recomputed `layout_*` values, not the stale ones.

- [ ] **Step 2: Keep the existing page-level recompute behavior as a guardrail**

Do not remove `tests/visualization/test_case_pages.py::test_render_case_page_recomputes_layout_metrics_from_representative_case_geometry`; use it to prove the shared helper preserves current page behavior.

- [ ] **Step 3: Introduce a shared helper in `core/generator/layout_metrics.py`**

Add small, reusable helpers such as:

```python
def build_layout_context(
    *,
    placement_region: Mapping[str, float],
    active_deck: Mapping[str, float] | None,
    dense_core: Mapping[str, float] | None,
) -> dict[str, dict[str, float]]:
    ...

def measure_case_layout_metrics(
    case_payload: Mapping[str, Any],
    *,
    layout_context: Mapping[str, Any],
) -> dict[str, float] | None:
    ...
```

`measure_case_layout_metrics(...)` should call the existing `measure_layout_quality(...)` and return the same metric keys already used in provenance:

- `component_area_ratio`
- `active_deck_occupancy`
- `bbox_fill_ratio`
- `nearest_neighbor_gap_mean`
- `centroid_dispersion`
- `largest_dense_core_void_ratio`

- [ ] **Step 4: Persist `layout_context` at generation time**

Update `core/generator/pipeline.py` so every generated `thermal_case` provenance contains both:

```python
"layout_context": {
    "placement_region": primary_region,
    "active_deck": active_deck,
    "dense_core": dense_core,
}
```

and the initial `layout_metrics`.

- [ ] **Step 5: Replace duplicated page recompute logic with the shared helper**

Refactor `visualization/case_pages.py` so `_recompute_layout_metrics(...)` delegates to the new helper instead of carrying a separate copy of the recomputation logic.

- [ ] **Step 6: Run the focused layout-helper tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/evaluation/test_engine.py tests/visualization/test_case_pages.py
```

Expected:

- the new evaluation regression fails before implementation, then passes after
- the page recompute tests still pass

## Task 3: Refresh Candidate Provenance Layout Metrics After Repair

**Files:**
- Modify: `optimizers/repair.py`
- Modify: `evaluation/metrics.py`
- Modify: `tests/optimizers/test_repair.py`
- Modify: `tests/evaluation/test_engine.py`

- [ ] **Step 1: Write a failing repair regression test**

Extend `tests/optimizers/test_repair.py` with a test that:

1. generates the baseline case
2. captures `case.provenance["layout_metrics"]`
3. applies a vector that visibly changes layout geometry
4. runs `repair_case_from_vector(...)`
5. asserts the repaired case now carries different `layout_metrics`

Use one metric with a stable directional change, for example `bbox_fill_ratio` or `centroid_dispersion`.

- [ ] **Step 2: Update repair to recompute layout provenance**

In `optimizers/repair.py`, after sink repair and overlap restoration, recompute:

```python
payload["provenance"]["layout_metrics"] = measure_case_layout_metrics(
    payload,
    layout_context=payload["provenance"]["layout_context"],
)
```

Do this only when `layout_context` is present so legacy artifacts still load.

- [ ] **Step 3: Make evaluation defensive for older cases**

In `evaluation/metrics.py`, update `build_derived_signals(...)` so it prefers:

1. recomputation from `provenance.layout_context` when available
2. fallback to `provenance.layout_metrics` for older cases without context

Use the shared helper from `core/generator/layout_metrics.py`.

- [ ] **Step 4: Preserve legacy compatibility**

If a case lacks `layout_context`, do not raise. Keep the current behavior:

```python
layout_metrics = provenance.get("layout_metrics", {})
```

This lets old saved artifacts still render and evaluate.

- [ ] **Step 5: Run focused repair/evaluation tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_repair.py tests/evaluation/test_engine.py
```

Expected:

- the new repair regression passes
- evaluation now reports candidate-geometry `layout_*`

## Task 4: Redefine Feasibility Progress As Optimizer-Only

**Files:**
- Modify: `optimizers/drivers/raw_driver.py`
- Modify: `optimizers/run_telemetry.py`
- Modify: `optimizers/mode_summary.py`
- Modify: `optimizers/comparison_summary.py`
- Modify: `optimizers/operator_pool/domain_state.py`
- Modify: `optimizers/operator_pool/diagnostics.py`
- Modify: `tests/optimizers/experiment_fixtures.py`
- Modify: `tests/optimizers/test_mode_summary.py`
- Create: `tests/optimizers/test_run_telemetry.py`

- [ ] **Step 1: Write a failing telemetry regression for a feasible baseline**

Create `tests/optimizers/test_run_telemetry.py` with a tiny history like:

1. `evaluation_index=1`, `source="baseline"`, `feasible=True`
2. `evaluation_index=2`, `source="optimizer"`, `feasible=False`
3. `evaluation_index=3`, `source="optimizer"`, `feasible=True`

Assert:

- `first_feasible_eval_so_far` ends at `3`
- `feasible_count_so_far` counts optimizer-feasible entries only
- `feasible_rate_so_far` excludes the baseline row

- [ ] **Step 2: Update the fixture expectations to match intended semantics**

Keep `tests/optimizers/experiment_fixtures.py` and `tests/optimizers/test_mode_summary.py` on the optimizer-only semantics:

- `aggregate_metrics["first_feasible_eval"] == 3`
- progress timeline milestone stays at `3`

These tests already encode the desired behavior; use them as regression proof instead of rewriting them toward `1`.

- [ ] **Step 3: Implement optimizer-only aggregate metrics**

In `optimizers/drivers/raw_driver.py`, compute aggregates using:

```python
optimizer_history = [row for row in history if row.get("source") == "optimizer"]
optimizer_feasible = [row for row in optimizer_history if row.get("feasible")]
```

Set:

```python
"baseline_feasible": bool(baseline_record["feasible"]),
"optimizer_num_evaluations": len(optimizer_history),
"optimizer_feasible_rate": ...,
"first_feasible_eval": first optimizer-feasible evaluation index,
```

Keep `baseline_candidates` unchanged so the reference point still exists in artifacts.

- [ ] **Step 4: Rework progress telemetry to exclude baseline from progress accounting**

In `optimizers/run_telemetry.py`:

- ignore `source="baseline"` when updating:
  - `feasible_count_so_far`
  - `feasible_rate_so_far`
  - `first_feasible_eval_so_far`
  - `best_temperature_max_so_far`
  - `best_gradient_rms_so_far`
  - `best_total_constraint_violation_so_far` if the metric is meant to track optimizer progress

Keep the baseline row in the timeline, but treat it as reference-only.

- [ ] **Step 5: Propagate the same semantics into controller-facing state**

Update:

- `optimizers/operator_pool/domain_state.py`
- `optimizers/operator_pool/diagnostics.py`

so `run_state["first_feasible_eval"]` and all pre/post-feasible phase splits use optimizer-only feasible rows.

This is the critical fix that prevents future `llm` runs from starting in a false post-feasible state.

- [ ] **Step 6: Make mode and comparison summaries read the new fields**

In:

- `optimizers/mode_summary.py`
- `optimizers/comparison_summary.py`

prefer the optimizer-only aggregate fields and carry `baseline_feasible` through the JSON summaries if it helps debugging and reporting.

- [ ] **Step 7: Run the focused telemetry and summary tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_run_telemetry.py tests/optimizers/test_mode_summary.py tests/optimizers/test_optimizer_cli.py
```

Expected:

- `first_feasible_eval` regressions now resolve to `3`
- suite/page summaries stop reporting the misleading `1`

## Task 5: Update User-Facing Reporting To Match The Fixed Semantics

**Files:**
- Modify: `docs/reports/2026-04-10-s1-typical-end-to-end-flow-and-seed11-walkthrough.md`
- Modify: `README.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Update the explainer report**

Revise [2026-04-10-s1-typical-end-to-end-flow-and-seed11-walkthrough.md](/home/hymn/msfenicsx/docs/reports/2026-04-10-s1-typical-end-to-end-flow-and-seed11-walkthrough.md) so it no longer describes the old caveats as unresolved. Replace them with the new implemented semantics:

- single benchmark seed for `s1_typical`
- optimizer-only `first_feasible_eval`
- candidate-level `layout_*`

- [ ] **Step 2: Update README benchmark instructions**

Make the benchmark command block use one `--benchmark-seed 11` and explain that repeated runs should vary `algorithm.seed`, not `benchmark_seed`.

- [ ] **Step 3: Update AGENTS repository guidance**

Replace the multi-`benchmark-seed` example in `AGENTS.md` with the fixed single-case example and add one short note clarifying:

> `s1_typical` is a fixed single-case benchmark; do not use multiple benchmark seeds to simulate multiple problem instances.

## Task 6: Verification And Real Raw/Union Reruns

**Files:**
- No source edits in this task beyond any small follow-up fixes found during verification

- [ ] **Step 1: Run the full focused test set**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v \
  tests/evaluation/test_engine.py \
  tests/optimizers/test_repair.py \
  tests/optimizers/test_run_telemetry.py \
  tests/optimizers/test_run_suite.py \
  tests/optimizers/test_mode_summary.py \
  tests/optimizers/test_optimizer_cli.py \
  tests/visualization/test_case_pages.py
```

Expected:

- all tests pass

- [ ] **Step 2: Re-run the baseline single-case validate chain**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main validate-scenario-template --template scenarios/templates/s1_typical.yaml
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main generate-case --template scenarios/templates/s1_typical.yaml --seed 11 --output-root ./scenario_runs/stage2_fix_validate/generated_cases/s1_typical/seed-11
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main solve-case --case ./scenario_runs/stage2_fix_validate/generated_cases/s1_typical/seed-11/s1_typical-seed-0011.yaml --output-root ./scenario_runs/stage2_fix_validate
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m evaluation.cli evaluate-case --case ./scenario_runs/stage2_fix_validate/s1_typical/s1_typical-seed-0011/case.yaml --solution ./scenario_runs/stage2_fix_validate/s1_typical/s1_typical-seed-0011/solution.yaml --spec scenarios/evaluation/s1_typical_eval.yaml --output ./scenario_runs/stage2_fix_validate/s1_typical/s1_typical-seed-0011/evaluation_report.yaml --bundle-root ./scenario_runs/stage2_fix_validate/s1_typical/s1_typical-seed-0011
```

Expected:

- template validates
- generated baseline remains feasible
- evaluation report writes candidate-geometry `layout_*`

- [ ] **Step 3: Run real raw and union reruns with one benchmark seed**

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

- run root ends with `__raw_union`
- `raw` and `union` seed bundles are present
- `comparison` artifacts render successfully

- [ ] **Step 4: Inspect the new raw/union outputs**

Check the new `optimization_result.json`, `mode_summary.json`, and one representative `evaluation.yaml` / `case.yaml` per mode.

Confirm all of the following before considering the task complete:

- `aggregate_metrics.first_feasible_eval` is no longer `1` just because the baseline is feasible
- `aggregate_metrics.baseline_feasible` is present
- `aggregate_metrics.optimizer_feasible_rate` is present
- representative `evaluation.yaml` carries candidate-level `layout_*` matching its `case.yaml`
- no paper-facing command example still suggests multiple `benchmark_seed` values for `s1_typical`

- [ ] **Step 5: Record the final evidence**

In the implementation close-out, report:

- what changed
- the exact test commands run
- the exact real rerun command run
- the new `first_feasible_eval` / `optimizer_feasible_rate` values for raw and union
- any residual risk that remains before enabling `llm`
