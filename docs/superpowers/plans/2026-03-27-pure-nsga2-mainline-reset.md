# Pure NSGA-II Mainline Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reset the paper mainline so the active classical baseline is a plain `pymoo` `NSGA-II` layout optimizer, delete the current heuristic hybrid `B1`, and leave a clean path for a later same-operator-pool random-vs-LLM strategy comparison.

**Architecture:** Keep the paired hot/cold benchmark, multicase evaluation, and FEniCSx solve loop exactly as they are. Simplify the active optimizer path to one raw-vector `NSGA-II` baseline that uses standard `pymoo` variation plus shared legality repair. Treat domain operators as a future experiment track, not the active classical baseline, and remove the current hand-written heuristic selector from the repository mainline.

**Tech Stack:** Python 3.12, PyYAML, NumPy, FEniCSx (`dolfinx`, `ufl`, `mpi4py`, `petsc4py`), `pymoo`, pytest

---

Spec context:

- active benchmark design: `docs/superpowers/specs/2026-03-27-paper-grade-multiobjective-thermal-baseline-design.md`
- this reset supersedes the heuristic-hybrid direction in `docs/reports/R65_msfenicsx_hybrid_b1_rollout_20260327.md`

This plan is intentionally split into two scopes:

1. **Now:** reset the active mainline to pure `NSGA-II`
2. **Later:** build a neutral operator-pool experiment track for `random` vs `LLM` controller comparison

Update on 2026-03-27:

- the reset itself remains active implemented history
- the later operator-pool direction is now re-scoped by `docs/superpowers/specs/2026-03-27-multi-backbone-optimizer-matrix-design.md`
- future operator-pool work should follow the multi-backbone matrix plan rather than a single-backbone extension
- later matrix-contract work replaces `algorithm.name` with `algorithm.family/backbone/mode` even though raw `NSGA-II` remains the only active implemented execution path at this stage

Do **not** keep the current heuristic `B1` as an active or supported baseline.

## File Structure

### Active Mainline After Reset

- Keep: `core/`
  No business-logic changes are expected beyond compatibility with the already-landed paired benchmark path.
- Keep: `evaluation/`
  The current four-component hot/cold multicase benchmark remains the active evaluation target.
- Modify: `optimizers/models.py`
  Remove heuristic-only assumptions from optimizer contracts and make the active result schema baseline-centric again.
- Modify: `optimizers/validation.py`
  Accept the pure `NSGA-II` active spec and remove the active `operator_mode: hybrid` path.
- Modify: `optimizers/io.py`
  Keep benchmark-source generation and evaluation-spec resolution, but remove hybrid-only branching.
- Modify: `optimizers/problem.py`
  Keep the shared expensive evaluation loop and legality repair; this remains the kernel used by all later optimizer experiments.
- Modify: `optimizers/pymoo_driver.py`
  Reduce the active driver to the pure `pymoo` `NSGA-II` path only.
- Modify: `optimizers/artifacts.py`
  Keep manifest-backed bundles but remove operator telemetry from the active output contract.
- Modify: `optimizers/cli.py`
  Keep `optimize-benchmark` but make the active examples and tests pure-baseline only.
- Keep: `optimizers/repair.py`
  Shared repair is part of the fair raw baseline because legality projection is a problem constraint, not an LLM advantage.
- Delete: `optimizers/operators.py`
  The current heuristic-coupled operator module must not remain active after the reset. If operator experiments return later, they should come back under a neutral experiment boundary.
- Delete: `scenarios/optimization/panel_four_component_hot_cold_hybrid_nsga2_b1.yaml`
- Delete: `docs/reports/R65_msfenicsx_hybrid_b1_rollout_20260327.md`

### Deferred Experiment Track

This reset does **not** implement the later operator-pool experiment track, but it should preserve room for it:

- Future create: `optimizers/operator_pool/`
- Future create: `optimizers/controllers/random.py`
- Future create: `llm/controller/`

Those pieces belong to a later dedicated plan after the pure baseline is stable.

## Task 1: Rewrite the Active Research Narrative Around a Plain NSGA-II Baseline

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `RULES.md`
- Modify: `docs/superpowers/plans/2026-03-27-paper-grade-multiobjective-thermal-baseline.md`
- Create: `docs/reports/R66_msfenicsx_pure_nsga2_mainline_reset_20260327.md`

- [ ] **Step 1: Write the failing documentation checklist**

Record the truths that must hold after the reset:

- the active classical baseline is `pure NSGA-II`
- the active docs do not present heuristic `B1` as a supported baseline
- the future `LLM` comparison is described as `pure NSGA-II` mainline plus a later same-pool controller experiment

- [ ] **Step 2: Update the README baseline narrative**

Rewrite the optimizer section so it says:

- active optimizer baseline: plain `pymoo NSGA-II`
- active benchmark: four-component paired hot/cold multicase problem
- heuristic hybrid `B1` is not part of the supported mainline

- [ ] **Step 3: Update repository guidance docs**

Update `AGENTS.md` and `RULES.md` so they describe:

- `panel_four_component_hot_cold_nsga2_b0.yaml` as the only active classical optimizer spec
- the hybrid heuristic path as removed
- future operator-pool work as a separate experimental track rather than the mainline

- [ ] **Step 4: Rewrite the old baseline implementation plan header**

At the top of `docs/superpowers/plans/2026-03-27-paper-grade-multiobjective-thermal-baseline.md`, add a short note that:

- Tasks `1-5` remain part of the implemented platform history
- the heuristic `B1` direction is superseded by `docs/superpowers/plans/2026-03-27-pure-nsga2-mainline-reset.md`

- [ ] **Step 5: Write the reset rollout note**

Create `docs/reports/R66_msfenicsx_pure_nsga2_mainline_reset_20260327.md` covering:

- why the heuristic `B1` was dropped
- why pure `NSGA-II` is the active paper-facing baseline
- why operator-pool comparisons are deferred to a separate fairness study

- [ ] **Step 6: Run a doc sanity check**

Run:

```bash
cd /home/hymn/msfenicsx
grep -R "hybrid B1\|hybrid-operator\|panel_four_component_hot_cold_hybrid_nsga2_b1" README.md AGENTS.md RULES.md docs || true
```

Expected:

- only historical reports and superseded-plan notes may still mention the heuristic path

- [ ] **Step 7: Commit**

```bash
cd /home/hymn/msfenicsx
git add README.md AGENTS.md RULES.md \
  docs/superpowers/plans/2026-03-27-paper-grade-multiobjective-thermal-baseline.md \
  docs/superpowers/plans/2026-03-27-pure-nsga2-mainline-reset.md \
  docs/reports/R66_msfenicsx_pure_nsga2_mainline_reset_20260327.md
git commit -m "docs: reset active optimizer narrative to pure nsga2"
```

## Task 2: Remove Heuristic-Hybrid Contracts From the Active Optimizer Layer

**Files:**
- Modify: `optimizers/models.py`
- Modify: `optimizers/validation.py`
- Modify: `optimizers/io.py`
- Modify: `optimizers/pymoo_driver.py`
- Modify: `optimizers/artifacts.py`
- Modify: `optimizers/cli.py`
- Delete: `optimizers/operators.py`
- Delete: `scenarios/optimization/panel_four_component_hot_cold_hybrid_nsga2_b1.yaml`

- [ ] **Step 1: Write the failing optimizer contract tests**

Add tests that require:

```python
def test_active_optimizer_spec_is_plain_nsga2():
    spec = load_optimization_spec("scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml")
    assert spec.algorithm["name"] == "pymoo_nsga2"
    assert "operator_mode" not in spec.algorithm
```

```python
def test_optimization_result_active_contract_has_no_operator_usage():
    result = load_optimization_result("...")
    assert "operator_usage" not in result.aggregate_metrics
```

- [ ] **Step 2: Run the optimizer tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_nsga2_driver.py \
  tests/optimizers/test_optimizer_cli.py \
  tests/optimizers/test_optimizer_io.py -v
```

Expected:

- FAIL because the active code still accepts and emits heuristic-hybrid fields

- [ ] **Step 3: Remove hybrid-only validation and model assumptions**

Implement the minimum reset:

- `OptimizationSpec` remains benchmark-source-driven
- `algorithm.operator_mode` and `algorithm.operator_pool` are no longer part of the active supported contract
- `OptimizationResult.aggregate_metrics` keeps:
  - `num_evaluations`
  - `feasible_rate`
  - `first_feasible_eval`
  - `pareto_size`

- [ ] **Step 4: Reduce the driver to a plain NSGA-II mainline**

In `optimizers/pymoo_driver.py`:

- delete the `_run_hybrid_search(...)` branch
- keep `NSGA2(pop_size=...)` plus `minimize(...)`
- keep Pareto extraction and representative-candidate export unchanged

- [ ] **Step 5: Remove heuristic telemetry from artifacts**

In `optimizers/artifacts.py` and the result payload:

- stop writing `operator_usage`
- keep manifest-backed bundles and representative snapshots

- [ ] **Step 6: Delete the hybrid spec and operator module**

Delete:

- `optimizers/operators.py`
- `scenarios/optimization/panel_four_component_hot_cold_hybrid_nsga2_b1.yaml`

- [ ] **Step 7: Run the optimizer tests again**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_nsga2_driver.py \
  tests/optimizers/test_optimizer_cli.py \
  tests/optimizers/test_optimizer_io.py -v
```

Expected:

- PASS with the pure-baseline-only contract

- [ ] **Step 8: Commit**

```bash
cd /home/hymn/msfenicsx
git add optimizers/models.py optimizers/validation.py optimizers/io.py \
  optimizers/pymoo_driver.py optimizers/artifacts.py optimizers/cli.py \
  tests/optimizers/test_nsga2_driver.py tests/optimizers/test_optimizer_cli.py tests/optimizers/test_optimizer_io.py
git add -u optimizers scenarios/optimization
git commit -m "refactor: remove heuristic hybrid optimizer path"
```

## Task 3: Re-baseline the Tests and CLI Around the Pure NSGA-II Mainline

**Files:**
- Modify: `tests/optimizers/test_nsga2_driver.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`
- Modify: `tests/optimizers/test_codec.py`
- Modify: `tests/cli/test_cli_end_to_end.py`
- Modify: `README.md`

- [ ] **Step 1: Rewrite the optimizer driver tests**

Keep the tests that matter for the paper baseline:

- deterministic benchmark generation from `benchmark_source`
- baseline candidate is infeasible
- pure `NSGA-II` finds feasible candidates and non-empty Pareto under the active checked-in budget

Delete tests that require:

- `operator_mode == "hybrid"`
- `operator_pool`
- `operator_id` in history

- [ ] **Step 2: Rewrite the CLI artifact expectations**

Require:

- `optimization_result.json`
- `pareto_front.json`
- `manifest.json`
- representative bundles

Do not require:

- operator telemetry

- [ ] **Step 3: Keep the end-to-end CLI story paper-simple**

The active examples should now be:

```bash
conda run -n msfenicsx python -m core.cli.main generate-operating-case-pair ...
conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml ...
```

Remove any active CLI examples for the hybrid heuristic spec.

- [ ] **Step 4: Run the CLI and optimizer suites**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/cli/test_cli_end_to_end.py \
  tests/optimizers/test_nsga2_driver.py \
  tests/optimizers/test_optimizer_cli.py -v
```

Expected:

- PASS with only the pure baseline path

- [ ] **Step 5: Commit**

```bash
cd /home/hymn/msfenicsx
git add tests/cli/test_cli_end_to_end.py \
  tests/optimizers/test_nsga2_driver.py \
  tests/optimizers/test_optimizer_cli.py \
  tests/optimizers/test_codec.py README.md
git commit -m "test: rebaseline optimizer coverage around pure nsga2"
```

## Task 4: Fresh Verification of the Reset Mainline

**Files:**
- Modify: none

- [ ] **Step 1: Run the focused optimizer and CLI suites**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers tests/cli/test_cli_end_to_end.py -v
```

Expected:

- PASS

- [ ] **Step 2: Run the full repository suite**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v
```

Expected:

- PASS

- [ ] **Step 3: Run a fresh active optimizer smoke example**

Run:

```bash
cd /home/hymn/msfenicsx
rm -rf scenario_runs/pure_nsga2_reset_smoke
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml \
  --output-root ./scenario_runs/pure_nsga2_reset_smoke
```

Expected:

- the run completes successfully
- `optimization_result.json`, `pareto_front.json`, and `manifest.json` are present
- representative bundles are present under `representatives/`

- [ ] **Step 4: Capture the fresh evidence in the reset rollout note**

Add:

- the exact verification commands
- the pass status
- the active output root layout

- [ ] **Step 5: Commit**

```bash
cd /home/hymn/msfenicsx
git add docs/reports/R66_msfenicsx_pure_nsga2_mainline_reset_20260327.md
git commit -m "chore: verify pure nsga2 mainline reset"
```

## Task 5: Prepare the Follow-On Operator-Pool Fairness Study as a Separate Phase

**Files:**
- Modify: `docs/reports/R66_msfenicsx_pure_nsga2_mainline_reset_20260327.md`
- Future plan target: `docs/superpowers/plans/2026-03-27-operator-pool-controller-comparison.md`

- [ ] **Step 1: Record the follow-on scope explicitly**

At the end of `R66`, state that the next phase is:

- fixed operator pool
- non-LLM random selector baseline
- later LLM selector comparison

- [ ] **Step 2: Record the fairness rule**

Write that all future controller comparisons must share:

- the same operator pool
- the same repair
- the same paired benchmark seeds
- the same evaluation spec
- the same simulation budget

- [ ] **Step 3: Do not implement the operator-pool experiment in this reset**

This reset is complete only when:

- heuristic `B1` is gone
- pure `NSGA-II` is the active paper baseline
- the repository is ready for the next dedicated plan
