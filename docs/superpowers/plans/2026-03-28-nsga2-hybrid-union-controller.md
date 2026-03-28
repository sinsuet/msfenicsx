# NSGA-II Hybrid-Union Controller Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> Implementation update on 2026-03-28: the union contract, shared operator registry, `NSGA-II` union adapter, union specs, doc sync, focused verification, and mechanism analysis are now implemented. `P1-union-uniform-nsga2` is no longer just planned; the immediate next paper-facing implementation step is `L1-union-llm-nsga2`, using the same mixed action registry and the analysis in `docs/reports/R68_msfenicsx_nsga2_union_mechanism_analysis_20260328.md`.

**Goal:** Add a paper-facing `NSGA-II` hybrid-union line that compares pure native `NSGA-II`, a uniform controller over a mixed native-plus-custom action space, and a later `LLM` controller on that same action space.

**Architecture:** Keep the current pure `NSGA-II` baseline intact. Reuse the existing numeric-vector operator infrastructure, but add one explicit native action and a new `mode: union` path for `NSGA-II` only. Preserve benchmark generation, repair, evaluation, artifacts, and traces as shared infrastructure.

**Tech Stack:** Python 3.12, PyYAML, NumPy, FEniCSx (`dolfinx`, `ufl`, `mpi4py`, `petsc4py`), `pymoo`, pytest

---

Spec reference: `docs/superpowers/specs/2026-03-28-nsga2-hybrid-union-controller-design.md`

Status context:

- pure `NSGA-II` remains the active classical paper baseline
- the multi-backbone raw/pool matrix remains the optimizer-platform track
- this plan adds a separate `NSGA-II`-only hybrid-union controller track for paper-facing controller experiments

## File Structure

### Spec And Validation Layer

- Modify: `optimizers/validation.py`
  Accept `algorithm.mode: union` for `family=genetic`, `backbone=nsga2` only, and validate the union action registry.
- Modify: `optimizers/models.py`
  Keep the existing optimizer payload model, but ensure the new union specs round-trip cleanly.
- Modify: `optimizers/io.py`
  Load and save the new union specs while preserving the raw matrix specs.
- Modify: `tests/optimizers/test_optimizer_io.py`

### Action Registry And Controllers

- Modify: `optimizers/operator_pool/operators.py`
  Add `native_sbx_pm` as an explicit union action wrapper while preserving the approved shared custom operator list inside the union action registry.
- Modify: `optimizers/operator_pool/controllers.py`
  Keep `random_uniform` and reserve the `llm` controller ID contract for later.
- Modify: `optimizers/operator_pool/random_controller.py`
  Reuse the same uniform-selection behavior on the union action registry.
- Modify: `tests/optimizers/test_operator_pool_contracts.py`

### NSGA-II Union Adapter

- Modify: `optimizers/adapters/genetic_family.py`
  Add a union path for `NSGA-II` that can dispatch either `native_sbx_pm` or one custom action per offspring while preserving native selection and survival.
- Create: `optimizers/drivers/union_driver.py`
  Support `mode: union` for the approved `NSGA-II` paper line without reviving the removed matrix `pool` runtime path.
- Modify: `optimizers/cli.py`
  Dispatch `mode: union` through the correct driver path.
- Modify: `optimizers/artifacts.py`
  Keep trace sidecars for union-mode runs.
- Modify: `tests/optimizers/test_operator_pool_adapters.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`

### Scenario Specs

- Create: `scenarios/optimization/panel_four_component_hot_cold_nsga2_union_uniform_p1.yaml`
- Create: `scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1.yaml`

### Documentation

- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/superpowers/specs/2026-03-27-paper-grade-multiobjective-thermal-baseline-design.md`
- Modify: `docs/superpowers/specs/2026-03-27-multi-backbone-optimizer-matrix-design.md`
- Modify: `docs/superpowers/plans/2026-03-27-paper-grade-multiobjective-thermal-baseline.md`
- Modify: `docs/superpowers/plans/2026-03-27-pure-nsga2-mainline-reset.md`
- Modify: `docs/superpowers/plans/2026-03-27-multi-backbone-optimizer-matrix.md`
- Modify: `docs/reports/R66_msfenicsx_pure_nsga2_mainline_reset_20260327.md`
- Modify: `docs/reports/R67_msfenicsx_multi_backbone_optimizer_matrix_doc_reset_20260327.md`

## Task 1: Add The Union-Mode Contract

**Files:**
- Modify: `optimizers/validation.py`
- Modify: `optimizers/models.py`
- Modify: `optimizers/io.py`
- Modify: `tests/optimizers/test_optimizer_io.py`

- [ ] **Step 1: Write the failing contract tests**

Add tests that require:

```python
def test_union_spec_uses_nsga2_union_mode_contract():
    spec = load_optimization_spec("scenarios/optimization/panel_four_component_hot_cold_nsga2_union_uniform_p1.yaml")
    assert {key: spec.algorithm[key] for key in ("family", "backbone", "mode")} == {
        "family": "genetic",
        "backbone": "nsga2",
        "mode": "union",
    }
```

```python
def test_union_spec_requires_native_action_in_registry():
    payload = load_optimization_spec("scenarios/optimization/panel_four_component_hot_cold_nsga2_union_uniform_p1.yaml").to_dict()
    payload["operator_control"]["operator_pool"] = [
        action for action in payload["operator_control"]["operator_pool"] if action != "native_sbx_pm"
    ]
    with pytest.raises(OptimizationValidationError):
        OptimizationSpec.from_dict(payload)
```

- [ ] **Step 2: Run the contract tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_optimizer_io.py -v
```

Expected:

- FAIL because `mode: union` is not yet accepted

- [ ] **Step 3: Implement the new contract**

Implement the minimum rules:

- `mode: union` is accepted only for `family=genetic`, `backbone=nsga2`
- `operator_control.controller` remains required
- `operator_control.operator_pool` must include `native_sbx_pm`
- the raw matrix path remains unchanged

- [ ] **Step 4: Re-run the contract tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_optimizer_io.py -v
```

Expected:

- PASS

## Task 2: Extend The Action Registry With `native_sbx_pm`

**Files:**
- Modify: `optimizers/operator_pool/operators.py`
- Modify: `tests/optimizers/test_operator_pool_contracts.py`

- [ ] **Step 1: Write the failing registry tests**

Add tests that require:

```python
def test_union_action_registry_exposes_native_sbx_pm():
    assert "native_sbx_pm" in list_registered_operator_ids()
```

```python
def test_native_sbx_pm_proposes_bounded_numeric_vector():
    ...
```

- [ ] **Step 2: Run the operator tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_operator_pool_contracts.py -v
```

Expected:

- FAIL because the native action wrapper does not yet exist

- [ ] **Step 3: Implement `native_sbx_pm`**

Implement a repository-owned wrapper that:

- consumes the same parent-bundle and layout contract
- emits one numeric proposal equivalent to the native `NSGA-II` `SBX + PM` move
- does not embed legality repair

- [ ] **Step 4: Re-run the operator tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_operator_pool_contracts.py -v
```

Expected:

- PASS

## Task 3: Add The NSGA-II Union Driver Path

**Files:**
- Modify: `optimizers/adapters/genetic_family.py`
- Modify: `optimizers/drivers/pool_driver.py`
- Modify: `optimizers/cli.py`
- Modify: `optimizers/artifacts.py`
- Modify: `tests/optimizers/test_operator_pool_adapters.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`

- [ ] **Step 1: Write the failing adapter tests**

Add tests that require:

```python
def test_nsga2_union_uniform_run_keeps_native_selection_and_survival():
    ...
```

```python
def test_union_cli_writes_controller_and_operator_trace_sidecars():
    ...
```

- [ ] **Step 2: Run the adapter tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_operator_pool_adapters.py \
  tests/optimizers/test_optimizer_cli.py -v
```

Expected:

- FAIL because `mode: union` is not yet dispatched

- [ ] **Step 3: Implement the union adapter path**

For `NSGA-II` union mode:

- keep native parent selection
- keep native survival
- let the controller choose one action per proposal decision
- dispatch `native_sbx_pm` through the native wrapper in mixed generations, while preserving an exact all-native fast path for raw-parity sanity checks
- dispatch custom actions through the existing shared custom operator path
- emit traces that preserve proposal-level rows while exposing shared `decision_index` metadata when one native decision yields sibling offspring

- [ ] **Step 4: Re-run the adapter tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_operator_pool_adapters.py \
  tests/optimizers/test_optimizer_cli.py -v
```

Expected:

- PASS

## Task 4: Add The `P1` And `L1` Scenario Specs

**Files:**
- Create: `scenarios/optimization/panel_four_component_hot_cold_nsga2_union_uniform_p1.yaml`
- Create: `scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1.yaml`
- Modify: `tests/optimizers/test_optimizer_io.py`

- [ ] **Step 1: Write the failing spec-load tests**

Add tests that require both new specs to load and round-trip.

- [ ] **Step 2: Run the spec tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_optimizer_io.py -v
```

Expected:

- FAIL because the new scenario specs do not exist

- [ ] **Step 3: Create the new specs**

`P1` must use:

- `family: genetic`
- `backbone: nsga2`
- `mode: union`
- `controller: random_uniform`
- the full union registry with `native_sbx_pm` plus the eight shared custom operators

`L1` must:

- use the same benchmark source
- use the same budget and registry
- differ only by `controller: llm`

- [ ] **Step 4: Re-run the spec tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_optimizer_io.py -v
```

Expected:

- PASS

## Task 5: Synchronize Repository Narrative

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/superpowers/specs/2026-03-27-paper-grade-multiobjective-thermal-baseline-design.md`
- Modify: `docs/superpowers/specs/2026-03-27-multi-backbone-optimizer-matrix-design.md`
- Modify: `docs/superpowers/plans/2026-03-27-paper-grade-multiobjective-thermal-baseline.md`
- Modify: `docs/superpowers/plans/2026-03-27-pure-nsga2-mainline-reset.md`
- Modify: `docs/superpowers/plans/2026-03-27-multi-backbone-optimizer-matrix.md`
- Modify: `docs/reports/R66_msfenicsx_pure_nsga2_mainline_reset_20260327.md`
- Modify: `docs/reports/R67_msfenicsx_multi_backbone_optimizer_matrix_doc_reset_20260327.md`

- [ ] **Step 1: Write the doc checklist**

Record the truths that must hold:

- pure `NSGA-II` remains the active paper-facing classical baseline
- the multi-backbone matrix remains the optimizer-platform line
- the next paper and `LLM` controller line is now `NSGA-II hybrid-union`

- [ ] **Step 2: Update the active status docs**

Rewrite status summaries so they distinguish:

- active baseline
- platform matrix track
- paper and `LLM` hybrid-union track

- [ ] **Step 3: Update the old plans and reports**

Add concise historical notes explaining that:

- the pure `NSGA-II` reset remains valid implemented history
- the matrix docs remain the platform story
- the next paper-facing controller plan is now the hybrid-union line

- [ ] **Step 4: Run a doc sanity check**

Run:

```bash
cd /home/hymn/msfenicsx
git diff --check
```

Expected:

- clean

## Task 6: Run Focused Verification

**Files:**
- Test only

- [ ] **Step 1: Run focused union tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_operator_pool_contracts.py \
  tests/optimizers/test_operator_pool_adapters.py \
  tests/optimizers/test_optimizer_io.py \
  tests/optimizers/test_optimizer_cli.py -v
```

Expected:

- PASS for the new union-mode contract and CLI path

- [ ] **Step 2: Run the full optimizer suite**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers -v
```

Expected:

- PASS

- [ ] **Step 3: Run one `P1` smoke optimization**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/panel_four_component_hot_cold_nsga2_union_uniform_p1.yaml \
  --output-root ./scenario_runs/optimizations/nsga2_union_uniform_p1_smoke
```

Expected:

- union-mode bundle written successfully
- `controller_trace.json` and `operator_trace.json` exist

- [ ] **Step 4: Run `git diff --check`**

Run:

```bash
cd /home/hymn/msfenicsx
git diff --check
```

Expected:

- clean
