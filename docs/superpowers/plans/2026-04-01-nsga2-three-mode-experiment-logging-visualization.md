# NSGA-II Three-Mode Experiment Logging and Visualization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-grade three-mode experiment system for `nsga2_raw`, `nsga2_union`, and `nsga2_llm` with stable experiment containers, shared run-level telemetry, multi-seed summaries, and formal dashboards.

**Architecture:** Keep one shared experiment backbone for all three modes, keep the existing `controller_trace.json` and `operator_trace.json` as the canonical controller-guided mechanism logs for `union` and `llm`, and layer `llm` request/response/runtime summaries on top without contaminating `raw`. Use optimizer-layer summary builders for compact JSON outputs and a small visualization package for static HTML dashboards and comparison pages.

**Tech Stack:** Python, pytest, JSON/JSONL, PyYAML, Plotly or lightweight HTML templating, existing `pymoo`/FEniCSx optimizer pipeline, `/home/hymn/miniconda3/bin/conda run -n msfenicsx`

---

## Target File Map

### New optimizer modules

- Create: `/home/hymn/msfenicsx/optimizers/experiment_layout.py`
- Create: `/home/hymn/msfenicsx/optimizers/experiment_runner.py`
- Create: `/home/hymn/msfenicsx/optimizers/generation_callback.py`
- Create: `/home/hymn/msfenicsx/optimizers/run_telemetry.py`
- Create: `/home/hymn/msfenicsx/optimizers/experiment_summary.py`
- Create: `/home/hymn/msfenicsx/optimizers/llm_summary.py`

### Modified optimizer modules

- Modify: `/home/hymn/msfenicsx/optimizers/artifacts.py`
- Modify: `/home/hymn/msfenicsx/optimizers/cli.py`
- Modify: `/home/hymn/msfenicsx/optimizers/drivers/raw_driver.py`
- Modify: `/home/hymn/msfenicsx/optimizers/drivers/union_driver.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/diagnostics.py`
- Modify: `/home/hymn/msfenicsx/optimizers/__init__.py`

### New visualization modules

- Create: `/home/hymn/msfenicsx/visualization/optimizer_overview.py`
- Create: `/home/hymn/msfenicsx/visualization/controller_mechanism.py`
- Create: `/home/hymn/msfenicsx/visualization/llm_dashboard.py`
- Create: `/home/hymn/msfenicsx/visualization/template_comparison.py`

### Modified visualization package files

- Modify: `/home/hymn/msfenicsx/visualization/__init__.py`

### New tests

- Create: `/home/hymn/msfenicsx/tests/optimizers/test_experiment_layout.py`
- Create: `/home/hymn/msfenicsx/tests/optimizers/test_generation_callback.py`
- Create: `/home/hymn/msfenicsx/tests/optimizers/test_run_telemetry.py`
- Create: `/home/hymn/msfenicsx/tests/optimizers/test_experiment_runner.py`
- Create: `/home/hymn/msfenicsx/tests/optimizers/test_experiment_summary.py`
- Create: `/home/hymn/msfenicsx/tests/optimizers/test_llm_summary.py`
- Create: `/home/hymn/msfenicsx/tests/visualization/test_optimizer_overview.py`
- Create: `/home/hymn/msfenicsx/tests/visualization/test_controller_mechanism.py`
- Create: `/home/hymn/msfenicsx/tests/visualization/test_llm_dashboard.py`
- Create: `/home/hymn/msfenicsx/tests/visualization/test_template_comparison.py`

### Modified existing tests

- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_optimizer_cli.py`
- Modify: `/home/hymn/msfenicsx/tests/visualization/test_render_optimizer_overview.py`

### Documentation updates

- Modify: `/home/hymn/msfenicsx/README.md`
- Modify: `/home/hymn/msfenicsx/AGENTS.md`

## Task 1: Formalize The Single-Mode Experiment Container

**Files:**
- Create: `/home/hymn/msfenicsx/optimizers/experiment_layout.py`
- Modify: `/home/hymn/msfenicsx/optimizers/cli.py`
- Create: `/home/hymn/msfenicsx/tests/optimizers/test_experiment_layout.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_optimizer_cli.py`

- [ ] **Step 1: Write the failing layout tests**

```python
def test_allocate_experiment_root_uses_template_first_mode_timestamp_layout(tmp_path):
    root = allocate_experiment_root(
        scenario_runs_root=tmp_path,
        scenario_template_id="panel_four_component_hot_cold_benchmark",
        mode_id="nsga2_union",
        started_at=datetime(2026, 4, 1, 14, 30),
    )
    assert root == (
        tmp_path
        / "panel_four_component_hot_cold_benchmark"
        / "experiments"
        / "nsga2_union__0401_1430"
    )


def test_allocate_experiment_root_appends_sequence_when_same_minute_exists(tmp_path):
    first = tmp_path / "panel_four_component_hot_cold_benchmark" / "experiments" / "nsga2_union__0401_1430"
    first.mkdir(parents=True)
    second = allocate_experiment_root(
        scenario_runs_root=tmp_path,
        scenario_template_id="panel_four_component_hot_cold_benchmark",
        mode_id="nsga2_union",
        started_at=datetime(2026, 4, 1, 14, 30),
    )
    assert second.name == "nsga2_union__0401_1430__01"
```

- [ ] **Step 2: Run the layout tests and confirm they fail**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_experiment_layout.py -v
```

Expected: FAIL with missing `optimizers.experiment_layout` symbols.

- [ ] **Step 3: Implement the experiment-root allocator and snapshot directory helpers**

```python
def allocate_experiment_root(...):
    ...


def build_experiment_manifest(...):
    ...


def initialize_experiment_directories(experiment_root: Path) -> None:
    ...
```

- [ ] **Step 4: Add CLI coverage for experiment-root creation**

Add a dedicated CLI path such as:

```bash
python -m optimizers.cli run-mode-experiment ...
```

that resolves:

- scenario template id
- mode id
- experiment root
- seed runs directory

- [ ] **Step 5: Re-run the layout and CLI tests**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_experiment_layout.py tests/optimizers/test_optimizer_cli.py -v
```

Expected: PASS for the new layout tests and updated CLI expectations.

- [ ] **Step 6: Commit**

```bash
git add tests/optimizers/test_experiment_layout.py tests/optimizers/test_optimizer_cli.py optimizers/experiment_layout.py optimizers/cli.py
git commit -m "feat: add three-mode experiment container layout"
```

## Task 2: Add Shared Generation And Evaluation Telemetry For All Three Modes

**Files:**
- Create: `/home/hymn/msfenicsx/optimizers/generation_callback.py`
- Create: `/home/hymn/msfenicsx/optimizers/run_telemetry.py`
- Modify: `/home/hymn/msfenicsx/optimizers/drivers/raw_driver.py`
- Modify: `/home/hymn/msfenicsx/optimizers/drivers/union_driver.py`
- Modify: `/home/hymn/msfenicsx/optimizers/artifacts.py`
- Create: `/home/hymn/msfenicsx/tests/optimizers/test_generation_callback.py`
- Create: `/home/hymn/msfenicsx/tests/optimizers/test_run_telemetry.py`

- [ ] **Step 1: Write failing tests for compact evaluation and generation sidecars**

```python
def test_build_evaluation_events_derives_compact_constraint_fields():
    rows = build_evaluation_events(
        mode_id="nsga2_raw",
        seed=7,
        history=[...],
    )
    assert rows[0]["total_constraint_violation"] == pytest.approx(2.5)
    assert rows[0]["dominant_violation_constraint_id"] == "cold_battery_floor"


def test_generation_callback_records_generation_boundaries():
    callback = GenerationSummaryCallback(...)
    ...
    assert callback.rows[-1]["generation_index"] == 3
```

- [ ] **Step 2: Run the new telemetry tests and confirm they fail**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_generation_callback.py tests/optimizers/test_run_telemetry.py -v
```

Expected: FAIL because the callback and telemetry builders do not exist yet.

- [ ] **Step 3: Implement a generation callback that records generation-level compact summaries**

```python
class GenerationSummaryCallback(Callback):
    def notify(self, algorithm):
        ...
```

It should capture:

- generation index
- evaluations used so far
- feasible fraction
- best total CV
- best objective values
- Pareto size

- [ ] **Step 4: Implement compact evaluation-event derivation from run history**

```python
def build_evaluation_events(*, mode_id: str, seed: int, history: list[dict[str, Any]], ...):
    ...
```

It should derive:

- `total_constraint_violation`
- `dominant_violation_constraint_id`
- `dominant_violation_constraint_family`
- `entered_feasible_region`
- `preserved_feasibility`
- `pareto_membership_after_eval`

- [ ] **Step 5: Wire the callback into raw and union drivers and write the new sidecars in artifacts**

Required sidecars for every run:

- `evaluation_events.jsonl`
- `generation_summary.jsonl`

- [ ] **Step 6: Re-run the telemetry tests**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_generation_callback.py tests/optimizers/test_run_telemetry.py tests/optimizers/test_optimizer_cli.py -v
```

Expected: PASS and CLI artifact tests now confirm both new sidecars exist.

- [ ] **Step 7: Commit**

```bash
git add tests/optimizers/test_generation_callback.py tests/optimizers/test_run_telemetry.py tests/optimizers/test_optimizer_cli.py optimizers/generation_callback.py optimizers/run_telemetry.py optimizers/drivers/raw_driver.py optimizers/drivers/union_driver.py optimizers/artifacts.py
git commit -m "feat: add shared run telemetry sidecars"
```

## Task 3: Build The Multi-Seed Single-Mode Experiment Runner

**Files:**
- Create: `/home/hymn/msfenicsx/optimizers/experiment_runner.py`
- Modify: `/home/hymn/msfenicsx/optimizers/cli.py`
- Create: `/home/hymn/msfenicsx/tests/optimizers/test_experiment_runner.py`

- [ ] **Step 1: Write a failing test for a multi-seed experiment container**

```python
def test_run_mode_experiment_writes_seed_runs_and_spec_snapshots(tmp_path, monkeypatch):
    ...
    assert (experiment_root / "spec_snapshot" / "optimization_spec.yaml").exists()
    assert (experiment_root / "runs" / "seed-11" / "optimization_result.json").exists()
    assert (experiment_root / "runs" / "seed-17" / "optimization_result.json").exists()
```

- [ ] **Step 2: Run the experiment-runner test and confirm it fails**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_experiment_runner.py -v
```

Expected: FAIL with missing experiment-runner entrypoints.

- [ ] **Step 3: Implement the experiment runner**

```python
def run_mode_experiment(
    *,
    optimization_spec_path: Path,
    benchmark_seeds: Sequence[int],
    scenario_runs_root: Path,
) -> Path:
    ...
```

It should:

- allocate one single-mode experiment root
- snapshot the optimization spec, template, evaluation spec, and profile
- run one seed bundle under `runs/seed-*`
- preserve existing raw/union/llm run writing behavior inside each seed directory

- [ ] **Step 4: Expose the runner through the optimizer CLI**

Add a stable command such as:

```bash
python -m optimizers.cli run-mode-experiment --optimization-spec ... --benchmark-seed 11 --benchmark-seed 17 --scenario-runs-root ...
```

- [ ] **Step 5: Re-run the experiment-runner and CLI tests**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_experiment_runner.py tests/optimizers/test_optimizer_cli.py -v
```

Expected: PASS and seed run roots appear under the experiment container.

- [ ] **Step 6: Commit**

```bash
git add tests/optimizers/test_experiment_runner.py tests/optimizers/test_optimizer_cli.py optimizers/experiment_runner.py optimizers/cli.py
git commit -m "feat: add single-mode multi-seed experiment runner"
```

## Task 4: Build Shared Experiment Summaries For All Three Modes

**Files:**
- Create: `/home/hymn/msfenicsx/optimizers/experiment_summary.py`
- Create: `/home/hymn/msfenicsx/tests/optimizers/test_experiment_summary.py`
- Modify: `/home/hymn/msfenicsx/optimizers/cli.py`

- [ ] **Step 1: Write failing tests for shared experiment summaries**

```python
def test_build_experiment_summaries_writes_run_index_and_aggregate_summary(tmp_path):
    ...
    assert (experiment_root / "summaries" / "run_index.json").exists()
    assert (experiment_root / "summaries" / "aggregate_summary.json").exists()
    assert (experiment_root / "summaries" / "constraint_summary.json").exists()
    assert (experiment_root / "summaries" / "generation_summary.json").exists()
```

- [ ] **Step 2: Run the summary tests and confirm they fail**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_experiment_summary.py -v
```

Expected: FAIL with missing experiment summary builder.

- [ ] **Step 3: Implement run indexing and aggregate summary builders**

```python
def build_run_index(experiment_root: Path) -> list[dict[str, Any]]:
    ...


def build_aggregate_summary(run_rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    ...
```

- [ ] **Step 4: Implement constraint and generation aggregation**

```python
def build_constraint_summary(...):
    ...


def build_generation_summary(...):
    ...
```

Aggregate:

- dominant violation frequency
- per-constraint activation and mean violation
- generation-wise feasible fraction and best CV curves

- [ ] **Step 5: Add a CLI command or runner hook that always refreshes shared summaries after multi-seed runs**

- [ ] **Step 6: Re-run the summary tests**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_experiment_summary.py tests/optimizers/test_experiment_runner.py -v
```

Expected: PASS and the new summary JSON files are materialized under `summaries/`.

- [ ] **Step 7: Commit**

```bash
git add tests/optimizers/test_experiment_summary.py tests/optimizers/test_experiment_runner.py optimizers/experiment_summary.py optimizers/cli.py
git commit -m "feat: add shared experiment summaries"
```

## Task 5: Formalize The Controller-Guided Mechanism Summary Layer For Union And LLM

**Files:**
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/diagnostics.py`
- Modify: `/home/hymn/msfenicsx/optimizers/experiment_summary.py`
- Create: `/home/hymn/msfenicsx/tests/optimizers/test_controller_mechanism_summary.py`

- [ ] **Step 1: Write failing tests that treat `controller_trace.json` and `operator_trace.json` as canonical raw mechanism logs**

```python
def test_union_experiment_builds_operator_and_regime_summaries(tmp_path):
    ...
    assert (experiment_root / "summaries" / "controller_trace_summary.json").exists()
    assert (experiment_root / "summaries" / "operator_summary.json").exists()
    assert (experiment_root / "summaries" / "regime_operator_summary.json").exists()
```

- [ ] **Step 2: Run the mechanism-summary tests and confirm they fail**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_controller_mechanism_summary.py -v
```

Expected: FAIL because experiment-level mechanism summaries are not yet generated.

- [ ] **Step 3: Reuse the existing diagnostics and reflection utilities instead of inventing a second raw mechanism format**

Add summary builders that derive:

- controller trace phase buckets
- fallback and llm-valid counts
- operator counts
- feasible-entry and feasible-preservation counts
- mean total-violation deltas
- regime-conditioned operator success aggregates

- [ ] **Step 4: Persist the derived mechanism summaries only for `nsga2_union` and `nsga2_llm`**

- [ ] **Step 5: Re-run the mechanism-summary tests**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_controller_mechanism_summary.py tests/optimizers/test_operator_pool_contracts.py tests/optimizers/test_llm_controller_state.py -v
```

Expected: PASS and no new raw trace names are introduced.

- [ ] **Step 6: Commit**

```bash
git add tests/optimizers/test_controller_mechanism_summary.py tests/optimizers/test_operator_pool_contracts.py tests/optimizers/test_llm_controller_state.py optimizers/operator_pool/diagnostics.py optimizers/experiment_summary.py
git commit -m "feat: add controller-guided mechanism summaries"
```

## Task 6: Strengthen LLM Runtime Logging And Build LLM Compact Summaries

**Files:**
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py`
- Create: `/home/hymn/msfenicsx/optimizers/llm_summary.py`
- Create: `/home/hymn/msfenicsx/tests/optimizers/test_llm_summary.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_client.py`

- [ ] **Step 1: Write failing tests for richer `llm_metrics.json` and compact llm summaries**

```python
def test_llm_controller_metrics_count_retries_and_invalid_attempts():
    ...
    assert metrics["retry_count"] == 1
    assert metrics["invalid_response_count"] == 1


def test_build_llm_runtime_summary_extracts_provider_model_and_latency(tmp_path):
    ...
    assert summary["provider"] == "openai-compatible"
    assert summary["model"] == "GPT-5.4"
```

- [ ] **Step 2: Run the LLM summary tests and confirm they fail**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_llm_summary.py tests/optimizers/test_llm_controller.py tests/optimizers/test_llm_client.py -v
```

Expected: FAIL because retry/invalid/runtime summary fields are not yet formalized.

- [ ] **Step 3: Extend `LLMOperatorController` metrics and response logging**

Add counters or derived fields for:

- retry count
- invalid response count
- schema invalid count
- semantic invalid count
- max elapsed seconds
- provider/model/capability profile in compact summaries

- [ ] **Step 4: Implement compact LLM summary builders**

```python
def build_llm_runtime_summary(...):
    ...


def build_llm_decision_summary(...):
    ...


def build_llm_prompt_summary(...):
    ...
```

Reflection handling rule:

- treat `llm_reflection_trace.jsonl` as optional
- do not fail summary generation when it is absent

- [ ] **Step 5: Re-run the LLM tests**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_llm_summary.py tests/optimizers/test_llm_controller.py tests/optimizers/test_llm_client.py tests/optimizers/test_optimizer_cli.py -v
```

Expected: PASS and live/smoke artifact expectations now include the new compact summaries.

- [ ] **Step 6: Commit**

```bash
git add tests/optimizers/test_llm_summary.py tests/optimizers/test_llm_controller.py tests/optimizers/test_llm_client.py tests/optimizers/test_optimizer_cli.py optimizers/operator_pool/llm_controller.py optimizers/llm_summary.py
git commit -m "feat: add llm runtime and decision summaries"
```

## Task 7: Extract Production Visualization Modules And Render Experiment Dashboards

**Files:**
- Create: `/home/hymn/msfenicsx/visualization/optimizer_overview.py`
- Create: `/home/hymn/msfenicsx/visualization/controller_mechanism.py`
- Create: `/home/hymn/msfenicsx/visualization/llm_dashboard.py`
- Modify: `/home/hymn/msfenicsx/visualization/__init__.py`
- Create: `/home/hymn/msfenicsx/tests/visualization/test_optimizer_overview.py`
- Create: `/home/hymn/msfenicsx/tests/visualization/test_controller_mechanism.py`
- Create: `/home/hymn/msfenicsx/tests/visualization/test_llm_dashboard.py`
- Modify: `/home/hymn/msfenicsx/tests/visualization/test_render_optimizer_overview.py`

- [ ] **Step 1: Write failing dashboard tests for the three page types**

```python
def test_render_optimizer_overview_writes_overview_html(tmp_path):
    ...
    assert (experiment_root / "dashboards" / "overview.html").exists()


def test_render_controller_mechanism_writes_mechanism_html_for_union(tmp_path):
    ...
    assert (experiment_root / "dashboards" / "mechanism.html").exists()


def test_render_llm_dashboard_writes_llm_html_for_llm_mode(tmp_path):
    ...
    assert (experiment_root / "dashboards" / "llm.html").exists()
```

- [ ] **Step 2: Run the visualization tests and confirm they fail**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/visualization/test_optimizer_overview.py tests/visualization/test_controller_mechanism.py tests/visualization/test_llm_dashboard.py -v
```

Expected: FAIL with missing production visualization modules.

- [ ] **Step 3: Extract the current proof-of-concept three-mode overview logic out of `tests/visualization/test_render_optimizer_overview.py`**

Move the reusable rendering logic into production modules and leave the test file as an actual test harness.

- [ ] **Step 4: Implement the three dashboard renderers**

Minimum outputs:

- `overview.html` for all modes
- `mechanism.html` for `nsga2_union` and `nsga2_llm`
- `llm.html` for `nsga2_llm`

- [ ] **Step 5: Re-run the visualization tests**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/visualization/test_render_optimizer_overview.py tests/visualization/test_optimizer_overview.py tests/visualization/test_controller_mechanism.py tests/visualization/test_llm_dashboard.py -v
```

Expected: PASS and the proof-of-concept overview test now uses the production rendering modules.

- [ ] **Step 6: Commit**

```bash
git add tests/visualization/test_render_optimizer_overview.py tests/visualization/test_optimizer_overview.py tests/visualization/test_controller_mechanism.py tests/visualization/test_llm_dashboard.py visualization/__init__.py visualization/optimizer_overview.py visualization/controller_mechanism.py visualization/llm_dashboard.py
git commit -m "feat: add experiment dashboards for raw union and llm"
```

## Task 8: Add Template-Level Comparison Rendering

**Files:**
- Create: `/home/hymn/msfenicsx/visualization/template_comparison.py`
- Create: `/home/hymn/msfenicsx/tests/visualization/test_template_comparison.py`
- Modify: `/home/hymn/msfenicsx/optimizers/cli.py`

- [ ] **Step 1: Write a failing test for template-level comparison output**

```python
def test_render_template_comparison_builds_three_mode_summary(tmp_path):
    ...
    assert (template_root / "comparisons" / "raw-vs-union-vs-llm" / "overview.html").exists()
```

- [ ] **Step 2: Run the comparison test and confirm it fails**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/visualization/test_template_comparison.py -v
```

Expected: FAIL because no template-level comparison renderer exists.

- [ ] **Step 3: Implement comparison discovery from single-mode experiment roots**

It should compare:

- `nsga2_raw` vs `nsga2_union`
- `nsga2_union` vs `nsga2_llm`
- `nsga2_raw` vs `nsga2_union` vs `nsga2_llm`

using compact experiment summaries instead of reparsing heavy raw artifacts.

- [ ] **Step 4: Expose comparison rendering through the optimizer CLI**

- [ ] **Step 5: Re-run the comparison tests**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/visualization/test_template_comparison.py tests/optimizers/test_optimizer_cli.py -v
```

Expected: PASS and comparison pages land under the template root.

- [ ] **Step 6: Commit**

```bash
git add tests/visualization/test_template_comparison.py tests/optimizers/test_optimizer_cli.py visualization/template_comparison.py optimizers/cli.py
git commit -m "feat: add template-level mode comparisons"
```

## Task 9: Update Documentation And Repository Guidance

**Files:**
- Modify: `/home/hymn/msfenicsx/README.md`
- Modify: `/home/hymn/msfenicsx/AGENTS.md`

- [ ] **Step 1: Update README mode naming, directory layout, and dashboard workflow**

Add:

- the three official mode ids
- the template-first experiment layout
- the shared versus mechanism versus llm-specific log layers
- the new CLI workflow for running experiments and rendering dashboards

- [ ] **Step 2: Update AGENTS guidance for the new canonical experiment layout**

Update repository guidance so future agents know:

- experiment roots are template-first
- one experiment container equals one mode
- comparisons are generated at the template root

- [ ] **Step 3: Run documentation-oriented smoke verification**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_experiment_layout.py tests/optimizers/test_experiment_runner.py tests/optimizers/test_experiment_summary.py tests/optimizers/test_llm_summary.py tests/visualization/test_optimizer_overview.py tests/visualization/test_controller_mechanism.py tests/visualization/test_llm_dashboard.py tests/visualization/test_template_comparison.py -v
```

Expected: PASS for the new experiment-system test surface.

- [ ] **Step 4: Run the broader regression suite that covers the optimizer line**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers tests/visualization -v
```

Expected: PASS with the new experiment-system tests plus the existing raw/union/llm controller coverage.

- [ ] **Step 5: Commit**

```bash
git add README.md AGENTS.md
git commit -m "docs: document three-mode experiment system"
```

## Final Verification Checklist

- [ ] Run `git diff --check`
- [ ] Run the targeted new test surface listed in Task 9 Step 3
- [ ] Run `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers tests/visualization -v`
- [ ] Manually inspect one generated `nsga2_raw` experiment root
- [ ] Manually inspect one generated `nsga2_union` experiment root
- [ ] Manually inspect one generated `nsga2_llm` experiment root
- [ ] Open:
  - `overview.html`
  - `mechanism.html`
  - `llm.html`
  - one template-level comparison page

## Review Note

The `writing-plans` skill recommends a dedicated plan-reviewer subagent loop after drafting the plan. This thread does not have explicit user authorization to spawn subagents, so that review step is blocked by thread policy. The plan was therefore self-reviewed in the main thread and should be treated as ready for human approval or direct execution.
