# Multi-Backbone Optimizer Matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> Later implementation update: the raw matrix runtime and exploratory `union-uniform` matrix runtime are now implemented across the first-batch six backbones. Treat any older `pool-random` wording below as superseded by the current `union` terminology and runtime path.
>
> Immediate-focus update on 2026-03-28: this plan remains the multi-backbone platform line, but the immediate paper-facing next implementation step is the separate `NSGA-II` `L1-union-llm` controller line rather than a broad matrix-`LLM` rollout.

**Goal:** Implement a multi-backbone optimizer matrix for the paired hot/cold benchmark, keeping the current pure `NSGA-II` path as the active paper-facing baseline while adding a unified raw/union experiment platform for `NSGA-II`, `NSGA-III`, `C-TAEA`, `RVEA`, constrained `MOEA/D`, and `CMOPSO`.

**Architecture:** Preserve the benchmark, solver, evaluation, decision-vector encoding, and legality repair as shared infrastructure. Introduce algorithm-agnostic operator-pool contracts plus family adapters so genetic, decomposition, and swarm backbones can all participate in the same raw and union experiment matrix without hard-coding `NSGA-II` assumptions into the operator layer.

**Tech Stack:** Python 3.12, PyYAML, NumPy, FEniCSx (`dolfinx`, `ufl`, `mpi4py`, `petsc4py`), `pymoo`, pytest

---

Spec reference: `docs/superpowers/specs/2026-03-27-multi-backbone-optimizer-matrix-design.md`

Status update:

- the first-batch raw matrix runtime is now implemented in the repository
- the exploratory union-uniform matrix runtime is now implemented across the same six backbones
- the shared proposal-layer operator contracts are implemented in the repository
- this plan remains the optimizer-platform track for multi-backbone raw/union work
- the next paper-facing controller work is now re-scoped into `docs/superpowers/plans/2026-03-28-nsga2-hybrid-union-controller.md`
- benchmark/profile-based parameter layering is already in place, so remaining optimizer work should keep tuning in defaults/profile/spec inputs rather than wrapper-local hardcoding

User preference override:

- execute in the shared inline workspace rather than creating a separate worktree

## File Structure

### Shared Optimizer Kernel

- Modify: `optimizers/models.py`
  Replace single-backbone optimizer mode assumptions with the new `family/backbone/mode` contract.
- Modify: `optimizers/validation.py`
  Validate raw and union forms across the six selected backbones.
- Modify: `optimizers/io.py`
  Load and save the new spec families while preserving benchmark-source generation.
- Modify: `optimizers/artifacts.py`
  Keep the stable result bundle and add optional union-mode sidecars.
- Modify: `optimizers/cli.py`
  Dispatch through a driver registry rather than a single `NSGA-II` entrypoint.

### Existing Shared Infrastructure Kept

- Keep: `optimizers/problem.py`
- Keep: `optimizers/repair.py`
- Keep: `optimizers/codec.py`

### New Backbone Registry

- Create: `optimizers/raw_backbones/__init__.py`
- Create: `optimizers/raw_backbones/registry.py`
- Create: `optimizers/raw_backbones/nsga2.py`
- Create: `optimizers/raw_backbones/nsga3.py`
- Create: `optimizers/raw_backbones/ctaea.py`
- Create: `optimizers/raw_backbones/rvea.py`
- Create: `optimizers/raw_backbones/moead.py`
- Create: `optimizers/raw_backbones/cmopso.py`

### New Operator-Pool Layer

- Create: `optimizers/operator_pool/__init__.py`
- Create: `optimizers/operator_pool/models.py`
- Create: `optimizers/operator_pool/layout.py`
- Create: `optimizers/operator_pool/state.py`
- Create: `optimizers/operator_pool/operators.py`
- Create: `optimizers/operator_pool/controllers.py`
- Create: `optimizers/operator_pool/random_controller.py`
- Create: `optimizers/operator_pool/trace.py`

### New Family Adapters

- Create: `optimizers/adapters/__init__.py`
- Create: `optimizers/adapters/genetic_family.py`
- Create: `optimizers/adapters/decomposition_family.py`
- Create: `optimizers/adapters/swarm_family.py`

### New Drivers

- Create: `optimizers/drivers/__init__.py`
- Create: `optimizers/drivers/registry.py`
- Create: `optimizers/drivers/raw_driver.py`
- Create: `optimizers/drivers/union_driver.py`

### Scenario Specs

- Create: `scenarios/optimization/panel_four_component_hot_cold_nsga2_raw_b0.yaml`
- Create: `scenarios/optimization/panel_four_component_hot_cold_nsga3_raw_b0.yaml`
- Create: `scenarios/optimization/panel_four_component_hot_cold_ctaea_raw_b0.yaml`
- Create: `scenarios/optimization/panel_four_component_hot_cold_rvea_raw_b0.yaml`
- Create: `scenarios/optimization/panel_four_component_hot_cold_moead_raw_b0.yaml`
- Create: `scenarios/optimization/panel_four_component_hot_cold_cmopso_raw_b0.yaml`
- Create: `scenarios/optimization/panel_four_component_hot_cold_nsga2_union_uniform_p1.yaml`
- Create: `scenarios/optimization/panel_four_component_hot_cold_nsga3_union_uniform_p1.yaml`
- Create: `scenarios/optimization/panel_four_component_hot_cold_ctaea_union_uniform_p1.yaml`
- Create: `scenarios/optimization/panel_four_component_hot_cold_rvea_union_uniform_p1.yaml`
- Create: `scenarios/optimization/panel_four_component_hot_cold_moead_union_uniform_p1.yaml`
- Create: `scenarios/optimization/panel_four_component_hot_cold_cmopso_union_uniform_p1.yaml`

### Tests

- Create: `tests/optimizers/test_backbone_registry.py`
- Create: `tests/optimizers/test_raw_driver_matrix.py`
- Create: `tests/optimizers/test_operator_pool_contracts.py`
- Create: `tests/optimizers/test_operator_pool_adapters.py`
- Create: `tests/optimizers/test_moead_constraint_adapter.py`
- Create: `tests/optimizers/test_cmopso_pool_adapter.py`
- Modify: `tests/optimizers/test_optimizer_io.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`

## Task 1: Replace The Single-Backbone Optimizer Contract

**Files:**
- Modify: `optimizers/models.py`
- Modify: `optimizers/validation.py`
- Modify: `optimizers/io.py`
- Test: `tests/optimizers/test_optimizer_io.py`
- Test: `tests/optimizers/test_backbone_registry.py`

- [ ] **Step 1: Write the failing contract tests**

Add tests that require:

```python
def test_matrix_spec_uses_family_backbone_mode_contract():
    spec = load_optimization_spec("scenarios/optimization/panel_four_component_hot_cold_nsga3_raw_b0.yaml")
    assert {key: spec.algorithm[key] for key in ("family", "backbone", "mode")} == {
        "family": "genetic",
        "backbone": "nsga3",
        "mode": "raw",
    }
```

```python
def test_pool_spec_requires_operator_control_block():
    with open("scenarios/optimization/panel_four_component_hot_cold_nsga2_pool_random_b1.yaml", "r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    payload.pop("operator_control")
    with pytest.raises(OptimizationValidationError):
        OptimizationSpec.from_dict(payload)
```

- [ ] **Step 2: Run the contract tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_optimizer_io.py \
  tests/optimizers/test_backbone_registry.py -v
```

Expected:

- FAIL because the current spec contract is still single-backbone oriented

- [ ] **Step 3: Implement the new spec schema**

Update the optimizer contracts so:

- `algorithm.family`
- `algorithm.backbone`
- `algorithm.mode`

replace the current single-name algorithm assumption.

Keep optimizer budget fields such as population size, generation count, and seed on the `algorithm` block for now.

For `mode: pool`, require:

- `operator_control.controller`
- `operator_control.operator_pool`

- [ ] **Step 4: Re-run the contract tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_optimizer_io.py \
  tests/optimizers/test_backbone_registry.py -v
```

Expected:

- PASS for the new platform-level spec contract

- [ ] **Step 5: Commit**

```bash
cd /home/hymn/msfenicsx
git add optimizers/models.py optimizers/validation.py optimizers/io.py \
  tests/optimizers/test_optimizer_io.py tests/optimizers/test_backbone_registry.py
git commit -m "feat: add multi-backbone optimizer spec contract"
```

## Task 2: Build The Raw Backbone Registry

**Files:**
- Create: `optimizers/raw_backbones/__init__.py`
- Create: `optimizers/raw_backbones/registry.py`
- Create: `optimizers/raw_backbones/nsga2.py`
- Create: `optimizers/raw_backbones/nsga3.py`
- Create: `optimizers/raw_backbones/ctaea.py`
- Create: `optimizers/raw_backbones/rvea.py`
- Create: `optimizers/raw_backbones/moead.py`
- Create: `optimizers/raw_backbones/cmopso.py`
- Create: `optimizers/drivers/raw_driver.py`
- Test: `tests/optimizers/test_raw_driver_matrix.py`

- [ ] **Step 1: Write the failing raw-registry tests**

Add tests that require:

```python
def test_raw_backbone_registry_contains_first_batch_algorithms():
    assert sorted(list_registered_backbones()) == [
        "cmopso",
        "ctaea",
        "moead",
        "nsga2",
        "nsga3",
        "rvea",
    ]
```

```python
def test_raw_driver_dispatches_nsga2_and_nsga3_specs():
    for spec_name in [
        "panel_four_component_hot_cold_nsga2_raw_b0.yaml",
        "panel_four_component_hot_cold_nsga3_raw_b0.yaml",
    ]:
        run = run_raw_optimization_from_spec(spec_name)
        assert run.result.aggregate_metrics["num_evaluations"] > 0
```

- [ ] **Step 2: Run the raw-registry tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_raw_driver_matrix.py -v
```

Expected:

- FAIL because the registry and raw driver do not exist yet

- [ ] **Step 3: Implement the raw backbone registry**

Create focused wrappers for the six algorithms and register them by:

- family
- backbone name
- constructor
- any algorithm-specific required config such as reference directions

- [ ] **Step 4: Implement the raw driver**

The raw driver should:

- resolve the backbone through the registry
- instantiate the algorithm
- run the shared expensive benchmark problem
- return the same `OptimizationResult` contract used by the current mainline

- [ ] **Step 5: Re-run the raw-registry tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_raw_driver_matrix.py -v
```

Expected:

- PASS for raw driver dispatch across the first-batch registry

- [ ] **Step 6: Commit**

```bash
cd /home/hymn/msfenicsx
git add optimizers/raw_backbones optimizers/drivers/raw_driver.py \
  tests/optimizers/test_raw_driver_matrix.py
git commit -m "feat: add raw optimizer backbone registry"
```

## Task 3: Generalize The Operator Pool Into An Algorithm-Agnostic Proposal Layer

**Files:**
- Create: `optimizers/operator_pool/__init__.py`
- Create: `optimizers/operator_pool/models.py`
- Create: `optimizers/operator_pool/layout.py`
- Create: `optimizers/operator_pool/state.py`
- Create: `optimizers/operator_pool/operators.py`
- Create: `optimizers/operator_pool/controllers.py`
- Create: `optimizers/operator_pool/random_controller.py`
- Create: `optimizers/operator_pool/trace.py`
- Test: `tests/optimizers/test_operator_pool_contracts.py`

- [ ] **Step 1: Write the failing operator-pool tests**

Add tests that require:

```python
def test_operator_pool_registry_matches_approved_shared_pool():
    assert list_registered_operator_ids() == [
        "sbx_pm_global",
        "local_refine",
        "hot_pair_to_sink",
        "hot_pair_separate",
        "battery_to_warm_zone",
        "radiator_align_hot_pair",
        "radiator_expand",
        "radiator_contract",
    ]
```

```python
def test_random_controller_is_algorithm_agnostic():
    controller = RandomUniformController()
    selection = controller.select_operator(make_state(), list_registered_operator_ids(), np.random.default_rng(7))
    assert selection in list_registered_operator_ids()
```

- [ ] **Step 2: Run the operator-pool tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_operator_pool_contracts.py -v
```

Expected:

- FAIL because the shared operator-pool layer does not exist yet

- [ ] **Step 3: Implement shared pool contracts**

Add focused contracts for:

- `VariableLayout`
- `ControllerState`
- `ParentBundle`
- `OperatorTraceRow`
- `ControllerTraceRow`

- [ ] **Step 4: Implement the approved operator pool**

Make each operator:

- vector-based
- benchmark-aware
- algorithm-agnostic
- bounded to the approved variables

- [ ] **Step 5: Implement the random controller**

Keep the first controller intentionally simple:

- `random_uniform`
- seeded RNG
- no hidden weighting or rule-based policy

- [ ] **Step 6: Re-run the operator-pool tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_operator_pool_contracts.py -v
```

Expected:

- PASS with the approved shared operator set and controller contract

- [ ] **Step 7: Commit**

```bash
cd /home/hymn/msfenicsx
git add optimizers/operator_pool tests/optimizers/test_operator_pool_contracts.py
git commit -m "feat: add algorithm-agnostic operator pool"
```

## Task 4: Implement The Genetic-Family Pool Adapter

**Files:**
- Create: `optimizers/adapters/__init__.py`
- Create: `optimizers/adapters/genetic_family.py`
- Create: `optimizers/drivers/pool_driver.py`
- Test: `tests/optimizers/test_operator_pool_adapters.py`

- [ ] **Step 1: Write the failing genetic-family adapter tests**

Add tests that require:

```python
def test_genetic_family_adapter_supports_nsga2_nsga3_ctaea_rvea():
    for backbone in ["nsga2", "nsga3", "ctaea", "rvea"]:
        run = run_pool_random_optimization(backbone)
        assert run.controller_trace is not None
```

- [ ] **Step 2: Run the adapter tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_operator_pool_adapters.py -v
```

Expected:

- FAIL because no family adapters exist yet

- [ ] **Step 3: Implement the genetic-family adapter**

The adapter should:

- use backbone-native parent selection
- convert the selected context into the shared proposal protocol
- apply the controller-selected operator
- feed the repaired proposal back into backbone-native survival

- [ ] **Step 4: Re-run the adapter tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_operator_pool_adapters.py -v
```

Expected:

- PASS for the genetic-family backbones in union-uniform mode

- [ ] **Step 5: Commit**

```bash
cd /home/hymn/msfenicsx
git add optimizers/adapters/__init__.py optimizers/adapters/genetic_family.py \
  optimizers/drivers/pool_driver.py tests/optimizers/test_operator_pool_adapters.py
git commit -m "feat: add genetic family pool adapter"
```

## Task 5: Implement The Constrained MOEA/D Adapter

**Files:**
- Create: `optimizers/adapters/decomposition_family.py`
- Modify: `optimizers/raw_backbones/moead.py`
- Test: `tests/optimizers/test_moead_constraint_adapter.py`

- [ ] **Step 1: Write the failing MOEA/D tests**

Add tests that require:

```python
def test_moead_adapter_uses_constraint_first_replacement():
    replacement = compare_moead_candidates(
        feasible_candidate=make_candidate(cv=0.0, scalar=1.3),
        infeasible_candidate=make_candidate(cv=2.0, scalar=0.2),
    )
    assert replacement == "feasible"
```

```python
def test_moead_pool_random_run_completes_on_constrained_benchmark():
    run = run_pool_random_optimization("moead")
    assert run.result.aggregate_metrics["num_evaluations"] > 0
```

- [ ] **Step 2: Run the MOEA/D tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_moead_constraint_adapter.py -v
```

Expected:

- FAIL because constrained MOEA/D support does not exist yet

- [ ] **Step 3: Implement the constrained replacement rule**

Preserve:

- neighborhood mating
- decomposition-based comparison

Add:

- total-constraint-violation comparison before decomposition value

- [ ] **Step 4: Re-run the MOEA/D tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_moead_constraint_adapter.py -v
```

Expected:

- PASS with constrained MOEA/D support for raw and pool paths

- [ ] **Step 5: Commit**

```bash
cd /home/hymn/msfenicsx
git add optimizers/adapters/decomposition_family.py optimizers/raw_backbones/moead.py \
  tests/optimizers/test_moead_constraint_adapter.py
git commit -m "feat: add constrained moead adapter"
```

## Task 6: Implement The CMOPSO Pool-Augmentation Adapter

**Files:**
- Create: `optimizers/adapters/swarm_family.py`
- Modify: `optimizers/raw_backbones/cmopso.py`
- Test: `tests/optimizers/test_cmopso_pool_adapter.py`

- [ ] **Step 1: Write the failing CMOPSO tests**

Add tests that require:

```python
def test_cmopso_pool_adapter_augments_raw_proposal_instead_of_replacing_swarm_identity():
    trace = run_pool_random_optimization("cmopso").operator_trace
    assert any(row["backbone"] == "cmopso" for row in trace)
```

- [ ] **Step 2: Run the CMOPSO tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_cmopso_pool_adapter.py -v
```

Expected:

- FAIL because no swarm-family adapter exists yet

- [ ] **Step 3: Implement the swarm-family adapter**

The adapter should:

- preserve particle, leader, and archive logic
- take the raw swarm proposal as input to the shared operator layer
- output one repaired final candidate for evaluation

- [ ] **Step 4: Re-run the CMOPSO tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_cmopso_pool_adapter.py -v
```

Expected:

- PASS with proposal augmentation rather than swarm replacement

- [ ] **Step 5: Commit**

```bash
cd /home/hymn/msfenicsx
git add optimizers/adapters/swarm_family.py optimizers/raw_backbones/cmopso.py \
  tests/optimizers/test_cmopso_pool_adapter.py
git commit -m "feat: add cmopso pool adapter"
```

## Task 7: Add Matrix Specs, CLI Dispatch, And Artifact Sidecars

**Files:**
- Modify: `optimizers/cli.py`
- Modify: `optimizers/artifacts.py`
- Create: `scenarios/optimization/panel_four_component_hot_cold_nsga2_raw_b0.yaml`
- Create: `scenarios/optimization/panel_four_component_hot_cold_nsga3_raw_b0.yaml`
- Create: `scenarios/optimization/panel_four_component_hot_cold_ctaea_raw_b0.yaml`
- Create: `scenarios/optimization/panel_four_component_hot_cold_rvea_raw_b0.yaml`
- Create: `scenarios/optimization/panel_four_component_hot_cold_moead_raw_b0.yaml`
- Create: `scenarios/optimization/panel_four_component_hot_cold_cmopso_raw_b0.yaml`
- Create: `scenarios/optimization/panel_four_component_hot_cold_nsga2_pool_random_b1.yaml`
- Create: `scenarios/optimization/panel_four_component_hot_cold_nsga3_pool_random_b1.yaml`
- Create: `scenarios/optimization/panel_four_component_hot_cold_ctaea_pool_random_b1.yaml`
- Create: `scenarios/optimization/panel_four_component_hot_cold_rvea_pool_random_b1.yaml`
- Create: `scenarios/optimization/panel_four_component_hot_cold_moead_pool_random_b1.yaml`
- Create: `scenarios/optimization/panel_four_component_hot_cold_cmopso_pool_random_b1.yaml`
- Modify: `tests/optimizers/test_optimizer_cli.py`

- [ ] **Step 1: Write the failing matrix-spec and artifact tests**

Add tests that require:

```python
def test_pool_runs_write_controller_and_operator_trace_sidecars(tmp_path):
    run_cli_pool_random("nsga2", tmp_path)
    assert (tmp_path / "controller_trace.json").exists()
    assert (tmp_path / "operator_trace.json").exists()
```

```python
def test_raw_and_pool_specs_share_same_benchmark_source():
    raw_spec = load_optimization_spec("scenarios/optimization/panel_four_component_hot_cold_nsga2_raw_b0.yaml")
    pool_spec = load_optimization_spec("scenarios/optimization/panel_four_component_hot_cold_nsga2_pool_random_b1.yaml")
    assert raw_spec.benchmark_source == pool_spec.benchmark_source
```

- [ ] **Step 2: Run the matrix-spec tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_optimizer_cli.py \
  tests/optimizers/test_optimizer_io.py -v
```

Expected:

- FAIL because matrix specs and sidecars do not exist yet

- [ ] **Step 3: Create the first-batch matrix specs**

Each spec should:

- share the same benchmark source and design variables
- declare the selected backbone through the new algorithm contract
- reuse the same evaluation spec
- use matched expensive-evaluation budgets across raw and pool forms

- [ ] **Step 4: Add sidecar artifact writing**

Keep `optimization_result.json` stable.

For pool mode only, also write:

- `controller_trace.json`
- `operator_trace.json`

- [ ] **Step 5: Re-run the matrix-spec tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_optimizer_cli.py \
  tests/optimizers/test_optimizer_io.py -v
```

Expected:

- PASS for matrix-spec loading and sidecar artifacts

- [ ] **Step 6: Commit**

```bash
cd /home/hymn/msfenicsx
git add optimizers/cli.py optimizers/artifacts.py scenarios/optimization \
  tests/optimizers/test_optimizer_cli.py tests/optimizers/test_optimizer_io.py
git commit -m "feat: add optimizer matrix specs and artifacts"
```

## Task 8: Fresh Verification And Matrix Smoke Evidence

**Files:**
- Verify only

- [ ] **Step 1: Run targeted optimizer tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers -v
```

Expected:

- PASS across raw and pool matrix coverage

- [ ] **Step 2: Run CLI end-to-end verification**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/cli/test_cli_end_to_end.py -v
```

Expected:

- PASS for the updated optimizer CLI dispatch

- [ ] **Step 3: Run one raw smoke optimization**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/panel_four_component_hot_cold_nsga2_raw_b0.yaml \
  --output-root ./scenario_runs/nsga2_raw_b0_smoke
```

Expected:

- run completes successfully

- [ ] **Step 4: Run one union-uniform smoke optimization**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/panel_four_component_hot_cold_nsga2_union_uniform_p1.yaml \
  --output-root ./scenario_runs/nsga2_union_uniform_p1_smoke
```

Expected:

- run completes successfully
- pool-mode sidecars exist

- [ ] **Step 5: Run one non-genetic smoke optimization**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/panel_four_component_hot_cold_cmopso_pool_random_b1.yaml \
  --output-root ./scenario_runs/cmopso_pool_random_b1_smoke
```

Expected:

- run completes successfully
- swarm-family adapter evidence is produced

- [ ] **Step 6: Summarize matrix-readiness**

Record:

- raw and pool smoke metadata
- at least one constrained `MOEA/D` run result
- at least one `CMOPSO` run result
- artifact sidecar evidence

- [ ] **Step 7: Commit**

```bash
git add .
git commit -m "test: verify multi-backbone optimizer matrix"
```

## Exit Criteria

This plan is complete only when:

1. the current pure `NSGA-II` path remains valid during the transition
2. the six approved backbones run through one shared contract surface
3. raw and pool forms exist for all six backbones
4. the operator pool is no longer tied to `NSGA-II`
5. constrained `MOEA/D` and pool-augmented `CMOPSO` both work on the benchmark
6. future `LLM` work can replace only the controller while leaving the rest of the matrix unchanged
