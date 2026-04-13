# S1 Typical Desktop-Safe Parallel Benchmark Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add conservative parallel candidate evaluation for `s1_typical` `raw` and `union` so single-run latency improves without changing benchmark semantics, summary semantics, or controller trace semantics.

**Architecture:** Keep proposal generation, repair, cheap constraints, `evaluation_index` allocation, and trace/history submission on the main process. Push only the expensive solve-and-evaluate segment into a bounded worker pool, then commit results back in deterministic `evaluation_index` order. Default to a small desktop-safe worker budget and validate first with low-cost smoke runs before any real single-seed rerun.

**Tech Stack:** Python, pytest, pymoo, multiprocessing/concurrent-futures style worker pool, current `core/`, `evaluation/`, `optimizers/`, `visualization/` stack, `/home/hymn/miniconda3/bin/conda run -n msfenicsx ...`

---

## File Map

### Runtime code

- Modify: `optimizers/problem.py`
- Modify: `optimizers/drivers/raw_driver.py`
- Modify: `optimizers/drivers/union_driver.py`
- Modify: `optimizers/run_suite.py`
- Modify: `optimizers/cli.py`
- Modify: `optimizers/adapters/genetic_family.py`
- Modify: `optimizers/models.py` if execution metadata needs a stable schema slot
- Create: `optimizers/parallel_evaluator.py`

### Tests

- Modify: `tests/optimizers/experiment_fixtures.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`
- Modify: `tests/optimizers/test_raw_driver_matrix.py`
- Create: `tests/optimizers/test_parallel_evaluator.py`
- Create: `tests/optimizers/test_parallel_problem.py`
- Create: `tests/optimizers/test_union_parallel_trace.py`

### Documentation

- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-04-13-s1-typical-desktop-safe-parallel-benchmark-execution-design.md`

## Task 1: Add Execution Config Surface And Guardrails

**Files:**
- Modify: `optimizers/cli.py`
- Modify: `optimizers/run_suite.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`
- Modify: `README.md`

- [ ] **Step 1: Write a failing CLI/config regression**

Add or extend CLI tests to cover:

- `run-benchmark-suite` accepts `--evaluation-workers`
- default remains conservative when the flag is omitted
- invalid values such as `0` fail early

- [ ] **Step 2: Run the CLI regression to confirm failure**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_optimizer_cli.py
```

Expected: the new worker-config assertions fail before implementation.

- [ ] **Step 3: Implement a minimal execution-config surface**

Add a small execution config path that supports:

- explicit `evaluation_workers`
- default `desktop-safe` behavior when omitted

Keep the surface small; do not introduce multiple scheduling modes yet.

- [ ] **Step 4: Thread the config through suite and driver entry points**

Ensure `run_benchmark_suite(...)`, `run_raw_optimization(...)`, and `run_union_optimization(...)` can receive the worker budget without changing benchmark semantics.

- [ ] **Step 5: Update README command examples**

Document the conservative default and one explicit example such as:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli run-benchmark-suite ... --evaluation-workers 2
```

- [ ] **Step 6: Re-run the focused CLI test**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_optimizer_cli.py
```

Expected: the new CLI/config tests pass.

## Task 2: Extract Worker-Safe Candidate Solve/Evaluate Logic

**Files:**
- Create: `optimizers/parallel_evaluator.py`
- Modify: `optimizers/problem.py`
- Create: `tests/optimizers/test_parallel_evaluator.py`

- [ ] **Step 1: Write a failing worker-task test**

Create `tests/optimizers/test_parallel_evaluator.py` covering a worker task that:

- accepts a repaired candidate payload plus evaluation spec
- returns objective values, constraint values, feasibility, and field exports on success
- returns a structured penalty/error payload on failure

- [ ] **Step 2: Run the new test to verify it fails**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_parallel_evaluator.py
```

Expected: fail because the worker helper does not exist yet.

- [ ] **Step 3: Implement the worker helper**

In `optimizers/parallel_evaluator.py`, add a small serializable task boundary, for example:

```python
def evaluate_candidate_payload(candidate_payload: dict[str, Any], evaluation_spec: dict[str, Any]) -> dict[str, Any]:
    ...
```

It should:

- construct `ThermalCase`
- assert geometry contracts
- call `solve_case_artifacts`
- call `evaluate_case_solution`
- return a serializable result payload

- [ ] **Step 4: Keep penalty mapping outside the worker**

Do not let the worker write optimizer history directly. It should return data or an exception payload only.

- [ ] **Step 5: Re-run the worker test**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_parallel_evaluator.py
```

Expected: pass.

## Task 3: Add Ordered-Commit Parallel Evaluation To The Problem Layer

**Files:**
- Modify: `optimizers/problem.py`
- Create: `tests/optimizers/test_parallel_problem.py`

- [ ] **Step 1: Write failing problem-layer regressions**

Create tests that prove:

- cheap-constraint failures are recorded immediately and never dispatched
- out-of-order worker completions still append `history` in `evaluation_index` order
- `artifacts_by_index` keys align with committed evaluation indices
- `first_feasible_eval` semantics remain correct after ordered commit

- [ ] **Step 2: Run the new problem-layer tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_parallel_problem.py
```

Expected: fail before implementation.

- [ ] **Step 3: Refactor `ThermalOptimizationProblem` for two-phase evaluation**

Add helpers that separate:

- pre-solve preparation on the main thread
- post-solve record construction on ordered commit

This should preserve existing serial behavior when `evaluation_workers == 1` or parallelism is disabled.

- [ ] **Step 4: Add bounded parallel dispatch**

Use a small worker pool to evaluate only cheap-constraint-feasible candidates. Maintain a pending-results buffer keyed by `evaluation_index`.

- [ ] **Step 5: Commit results in deterministic order**

Ensure all writes to:

- `history`
- `artifacts_by_index`

occur on the main thread and in ascending `evaluation_index`.

- [ ] **Step 6: Re-run the problem-layer tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_parallel_problem.py
```

Expected: pass.

## Task 4: Integrate Parallel Evaluation Into Raw And Add Low-Cost Smoke Coverage

**Files:**
- Modify: `optimizers/drivers/raw_driver.py`
- Modify: `tests/optimizers/experiment_fixtures.py`
- Modify: `tests/optimizers/test_raw_driver_matrix.py`

- [ ] **Step 1: Write a failing raw-driver regression**

Add a low-cost raw-driver test using a tiny budget fixture, for example:

- small population
- one generation
- single `benchmark_seed`

Assert:

- run completes with `evaluation_workers=1`
- run completes with `evaluation_workers=2`
- aggregate metrics remain structurally valid

- [ ] **Step 2: Run the raw-driver regression**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_raw_driver_matrix.py
```

Expected: fail before the driver is wired up.

- [ ] **Step 3: Thread worker config into the raw driver**

Update `run_raw_optimization(...)` so it configures the problem-level evaluator without changing baseline handling, representative selection, or aggregate metric semantics.

- [ ] **Step 4: Keep smoke fixtures cheap**

Add a tiny-budget test fixture for development validation rather than changing the paper-facing `s1_typical` specs.

- [ ] **Step 5: Re-run the raw-driver tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_raw_driver_matrix.py
```

Expected: pass for the low-cost smoke matrix.

## Task 5: Integrate Parallel Evaluation Into Union Without Breaking Trace Semantics

**Files:**
- Modify: `optimizers/drivers/union_driver.py`
- Modify: `optimizers/adapters/genetic_family.py`
- Create: `tests/optimizers/test_union_parallel_trace.py`

- [ ] **Step 1: Write a failing union trace regression**

Add a low-cost union test that asserts:

- controller decisions are still produced sequentially
- committed `controller_trace` evaluation indices remain ordered
- committed `operator_trace` evaluation indices remain ordered even if solve completion is out of order

- [ ] **Step 2: Run the union regression to confirm failure**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_union_parallel_trace.py
```

Expected: fail before implementation.

- [ ] **Step 3: Keep the controller sequential**

Do not parallelize the decision stage in `genetic_family.py`. Only parallelize the expensive candidate evaluation after event records and predicted indices are established.

- [ ] **Step 4: Thread worker config into the union driver**

Update `run_union_optimization(...)` so it uses the same problem-level bounded worker pool.

- [ ] **Step 5: Re-run the union trace test**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_union_parallel_trace.py
```

Expected: pass.

## Task 6: Run Focused Verification, Then One Real Single-Seed Raw/Union Validation

**Files:**
- No intended source edits in this task beyond small follow-up fixes found during verification

- [ ] **Step 1: Run the focused verification suite**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v \
  tests/optimizers/test_optimizer_cli.py \
  tests/optimizers/test_parallel_evaluator.py \
  tests/optimizers/test_parallel_problem.py \
  tests/optimizers/test_raw_driver_matrix.py \
  tests/optimizers/test_union_parallel_trace.py
```

Expected: all focused tests pass.

- [ ] **Step 2: Run a low-cost smoke benchmark first**

Use a tiny-budget development fixture or smoke command path with:

- single `benchmark_seed`
- `evaluation_workers=1`
- then `evaluation_workers=2`

Expected:

- smoke runs complete
- ordering/summary semantics remain sane
- no desktop-hostile runaway behavior

- [ ] **Step 3: Run one real raw/union validation with conservative settings**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli run-benchmark-suite \
  --optimization-spec scenarios/optimization/s1_typical_raw.yaml \
  --optimization-spec scenarios/optimization/s1_typical_union.yaml \
  --mode raw \
  --mode union \
  --benchmark-seed 11 \
  --evaluation-workers 2 \
  --scenario-runs-root ./scenario_runs
```

Expected:

- one single-seed run root ending in `__raw_union`
- `raw` and `union` seed bundles complete successfully
- summaries and comparison artifacts render

- [ ] **Step 4: Inspect the real outputs**

Confirm from the resulting artifacts:

- `first_feasible_eval` remains meaningful
- `optimizer_feasible_rate` remains meaningful
- raw and union histories remain ordered
- controller/operator traces remain index-aligned

- [ ] **Step 5: Record the final evidence**

In the close-out, report:

- what changed
- exact focused test commands
- exact smoke commands if any
- exact real validation command
- resulting `first_feasible_eval` and `optimizer_feasible_rate`
- residual risks before any future `llm` rollout
