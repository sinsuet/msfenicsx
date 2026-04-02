# S1 Typical Mainline Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the retired four-component hot/cold paper-facing line with a single active `s1_typical` mainline built around one operating case, `15` movable `x/y`-only components, two objectives (`peak_temperature`, `temperature_gradient_rms`), a hard radiator-span budget, and shared `nsga2_raw` / `nsga2_union` / `nsga2_llm` execution paths.

**Architecture:** Collapse the repository back to a single-case-first stack from `scenario_template` through optimizer artifacts. Add solver-side finite-element gradient RMS as an official `thermal_solution.summary_metrics` field, refactor the optimizer pipeline to evaluate one case instead of multicase bundles, insert cheap legality checks ahead of PDE solves, rebuild repair around projection plus local legality restoration, then replace the old four-component union/LLM action registry with semantic cluster/gradient/budget operators that auto-target components from compact controller state.

**Tech Stack:** Python 3.12, pytest, NumPy, PyYAML, `pymoo`, FEniCSx (`dolfinx`, `ufl`, `mpi4py`, `petsc4py`), JSON/JSONL optimizer artifacts

---

Spec reference:

- `docs/superpowers/specs/2026-04-02-s1-typical-mainline-reset-design.md`

Primary implementation guardrails:

- `s1_typical` is the only active paper-facing mainline after this work.
- Keep all `15` components optimization-active in `x/y`; do not introduce optimized rotation, geometry, material, or power variables.
- The official gradient objective is `summary.temperature_gradient_rms = sqrt((1 / |Omega|) * integral_Omega |grad(T_h)|^2 dx)`.
- Cheap legality checks must run before expensive PDE solves.
- The new union/LLM registry must use semantic operator families with auto-targeting; do not encode benchmark-specific component-name logic into permanent operator semantics.
- Delete obsolete old-mainline files after the new path is verified; do not keep compatibility wrappers that preserve the retired paper line.

## File Structure

### New Mainline Inputs

- Create: `scenarios/templates/s1_typical.yaml`
  Single-case `15`-component template with no `operating_case_profiles`.
- Create: `scenarios/evaluation/s1_typical_eval.yaml`
  Single-case evaluation spec with `summary.temperature_max`, `summary.temperature_gradient_rms`, thermal safety limits, and `case.total_radiator_span` budget constraint.
- Create: `scenarios/optimization/s1_typical_raw.yaml`
- Create: `scenarios/optimization/s1_typical_union.yaml`
- Create: `scenarios/optimization/s1_typical_llm.yaml`
- Create: `scenarios/optimization/profiles/s1_typical_raw.yaml`
- Create: `scenarios/optimization/profiles/s1_typical_union.yaml`

### Core Single-Case Contract Simplification

- Modify: `core/schema/models.py`
- Modify: `core/schema/validation.py`
- Modify: `core/cli/main.py`
- Modify: `core/generator/pipeline.py`
- Delete: `core/generator/paired_pipeline.py`

### Solver And Evaluation Support

- Create: `core/solver/gradient_metrics.py`
- Modify: `core/solver/nonlinear_solver.py`
- Modify: `core/solver/field_sampler.py`
- Modify: `evaluation/models.py`
- Modify: `evaluation/validation.py`
- Modify: `evaluation/metrics.py`
- Modify: `evaluation/engine.py`
- Modify: `evaluation/cli.py`
- Delete: `evaluation/multicase_engine.py`
- Delete: `evaluation/operating_cases.py`

### Optimizer Core

- Create: `optimizers/cheap_constraints.py`
- Modify: `optimizers/io.py`
- Modify: `optimizers/models.py`
- Modify: `optimizers/problem.py`
- Modify: `optimizers/repair.py`
- Modify: `optimizers/drivers/raw_driver.py`
- Modify: `optimizers/drivers/union_driver.py`
- Modify: `optimizers/cli.py`
- Modify: `optimizers/experiment_runner.py`
- Modify: `optimizers/artifacts.py`
- Modify: `optimizers/generation_callback.py`
- Modify: `optimizers/experiment_summary.py`

### Union / LLM Controller Layer

- Modify: `optimizers/operator_pool/operators.py`
- Modify: `optimizers/operator_pool/domain_state.py`
- Modify: `optimizers/operator_pool/policy_kernel.py`
- Modify: `optimizers/operator_pool/prompt_projection.py`
- Modify: `optimizers/operator_pool/llm_controller.py`
- Modify: `optimizers/operator_pool/trace.py`

### Docs And Repository Guidance

- Modify: `README.md`
- Modify: `AGENTS.md`
- Create: `docs/reports/R70_msfenicsx_s1_typical_mainline_reset_validation_20260402.md`

### New Tests

- Create: `tests/schema/test_s1_typical_template.py`
- Create: `tests/evaluation/test_s1_typical_eval.py`
- Create: `tests/solver/test_gradient_metrics.py`
- Create: `tests/optimizers/test_single_case_problem.py`
- Create: `tests/optimizers/test_cheap_constraints.py`

### Legacy Inputs And Docs To Delete After Verification

- Delete: `scenarios/templates/panel_four_component_hot_cold_benchmark.yaml`
- Delete: `scenarios/evaluation/panel_four_component_hot_cold_baseline.yaml`
- Delete: `scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml`
- Delete: `scenarios/optimization/panel_four_component_hot_cold_nsga2_raw_b0.yaml`
- Delete: `scenarios/optimization/panel_four_component_hot_cold_nsga3_raw_b0.yaml`
- Delete: `scenarios/optimization/panel_four_component_hot_cold_ctaea_raw_b0.yaml`
- Delete: `scenarios/optimization/panel_four_component_hot_cold_rvea_raw_b0.yaml`
- Delete: `scenarios/optimization/panel_four_component_hot_cold_moead_raw_b0.yaml`
- Delete: `scenarios/optimization/panel_four_component_hot_cold_cmopso_raw_b0.yaml`
- Delete: `scenarios/optimization/panel_four_component_hot_cold_nsga2_union_uniform_p1.yaml`
- Delete: `scenarios/optimization/panel_four_component_hot_cold_nsga3_union_uniform_p1.yaml`
- Delete: `scenarios/optimization/panel_four_component_hot_cold_ctaea_union_uniform_p1.yaml`
- Delete: `scenarios/optimization/panel_four_component_hot_cold_rvea_union_uniform_p1.yaml`
- Delete: `scenarios/optimization/panel_four_component_hot_cold_moead_union_uniform_p1.yaml`
- Delete: `scenarios/optimization/panel_four_component_hot_cold_cmopso_union_uniform_p1.yaml`
- Delete: `scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1.yaml`
- Delete: `scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1_dashscope_live.yaml`
- Delete: `scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1_dashscope_smoke.yaml`
- Delete: `scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1_gpt54_live.yaml`
- Delete: `scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1_gpt54_smoke.yaml`
- Delete: `scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1_kimi_live.yaml`
- Delete: `scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1_kimi_smoke.yaml`
- Delete: `scenarios/optimization/profiles/panel_four_component_hot_cold_nsga2_raw.yaml`
- Delete: `scenarios/optimization/profiles/panel_four_component_hot_cold_nsga2_union.yaml`
- Delete: `scenarios/optimization/profiles/panel_four_component_hot_cold_nsga3_raw.yaml`
- Delete: `scenarios/optimization/profiles/panel_four_component_hot_cold_nsga3_union.yaml`
- Delete: `docs/superpowers/specs/2026-03-27-paper-grade-multiobjective-thermal-baseline-design.md`
- Delete: `docs/superpowers/specs/2026-03-27-multi-backbone-optimizer-matrix-design.md`
- Delete: `docs/superpowers/specs/2026-03-28-nsga2-hybrid-union-controller-design.md`
- Delete: `docs/superpowers/specs/2026-03-28-openai-union-llm-controller-design.md`
- Delete: `docs/superpowers/specs/2026-04-01-nsga2-three-mode-experiment-logging-visualization-design.md`
- Delete: `docs/superpowers/specs/2026-04-01-s1-dense-benchmark-design.md`
- Delete: `docs/superpowers/plans/2026-03-27-paper-grade-multiobjective-thermal-baseline.md`
- Delete: `docs/superpowers/plans/2026-03-27-multi-backbone-optimizer-matrix.md`
- Delete: `docs/superpowers/plans/2026-03-28-nsga2-hybrid-union-controller.md`
- Delete: `docs/superpowers/plans/2026-03-31-l1-domain-grounded-controller-state-completion.md`
- Delete: `docs/superpowers/plans/2026-03-31-l1-llm-stability-diagnostics-and-repair.md`
- Delete: `docs/superpowers/plans/2026-03-31-l1-reusable-controller-kernel-stabilization.md`
- Delete: `docs/superpowers/plans/2026-04-01-nsga2-three-mode-experiment-logging-visualization.md`

## Task 1: Scaffold `s1_typical` Inputs And Freeze The New Contract

**Files:**
- Create: `scenarios/templates/s1_typical.yaml`
- Create: `scenarios/evaluation/s1_typical_eval.yaml`
- Create: `scenarios/optimization/s1_typical_raw.yaml`
- Create: `scenarios/optimization/s1_typical_union.yaml`
- Create: `scenarios/optimization/s1_typical_llm.yaml`
- Create: `scenarios/optimization/profiles/s1_typical_raw.yaml`
- Create: `scenarios/optimization/profiles/s1_typical_union.yaml`
- Create: `tests/schema/test_s1_typical_template.py`
- Create: `tests/evaluation/test_s1_typical_eval.py`

- [ ] **Step 1: Write the red contract tests**

Add tests that require:

```python
def test_s1_typical_template_has_15_components_and_no_operating_case_profiles():
    template = load_template("scenarios/templates/s1_typical.yaml")
    assert template.template_meta["template_id"] == "s1_typical"
    assert len(template.component_families) == 15
    assert not getattr(template, "operating_case_profiles", [])
```

```python
def test_s1_typical_eval_has_two_objectives_and_sink_budget_constraint():
    spec = load_spec("scenarios/evaluation/s1_typical_eval.yaml")
    objective_ids = [item["objective_id"] for item in spec.objectives]
    assert objective_ids == ["minimize_peak_temperature", "minimize_temperature_gradient_rms"]
    assert any(item["metric"] == "case.total_radiator_span" for item in spec.constraints)
```

- [ ] **Step 2: Run the red tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/schema/test_s1_typical_template.py \
  tests/evaluation/test_s1_typical_eval.py -v
```

Expected:

- FAIL because the `s1_typical` inputs do not exist yet

- [ ] **Step 3: Author the new inputs**

Create the new template, evaluation spec, and three optimization specs with:

- `15` fixed component ids
- `x/y` variables only
- no optimized rotation
- single-case objective ids and hard constraints
- `nsga2_raw`, `nsga2_union`, `nsga2_llm` as the only paper-facing modes

- [ ] **Step 4: Re-run the focused contract tests**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  scenarios/templates/s1_typical.yaml \
  scenarios/evaluation/s1_typical_eval.yaml \
  scenarios/optimization/s1_typical_raw.yaml \
  scenarios/optimization/s1_typical_union.yaml \
  scenarios/optimization/s1_typical_llm.yaml \
  scenarios/optimization/profiles/s1_typical_raw.yaml \
  scenarios/optimization/profiles/s1_typical_union.yaml \
  tests/schema/test_s1_typical_template.py \
  tests/evaluation/test_s1_typical_eval.py
git commit -m "feat: add s1_typical scenario inputs"
```

## Task 2: Add Solver-Side Gradient RMS And Evaluation Support

**Files:**
- Create: `core/solver/gradient_metrics.py`
- Modify: `core/solver/nonlinear_solver.py`
- Modify: `core/solver/field_sampler.py`
- Modify: `evaluation/metrics.py`
- Modify: `evaluation/engine.py`
- Modify: `tests/solver/test_gradient_metrics.py`
- Modify: `tests/evaluation/test_engine.py`
- Modify: `tests/evaluation/test_cli.py`

- [ ] **Step 1: Write the red tests for `temperature_gradient_rms`**

Add tests that require:

```python
def test_compute_temperature_gradient_rms_returns_zero_for_constant_field():
    value = compute_temperature_gradient_rms(temperature, panel_area=1.0)
    assert value == pytest.approx(0.0)
```

```python
def test_evaluate_case_solution_supports_summary_temperature_gradient_rms():
    report = evaluate_case_solution(_case(), _solution_with_gradient_rms(12.5), _spec(metric="summary.temperature_gradient_rms"))
    assert report.metric_values["summary.temperature_gradient_rms"] == pytest.approx(12.5)
```

- [ ] **Step 2: Run the focused tests to confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/solver/test_gradient_metrics.py \
  tests/evaluation/test_engine.py \
  tests/evaluation/test_cli.py -v
```

Expected:

- FAIL because the gradient metric helper and evaluation support do not exist yet

- [ ] **Step 3: Implement the official gradient algorithm**

Implement:

```python
def compute_temperature_gradient_rms(temperature_function, panel_area: float) -> float:
    grad_energy = fem.assemble_scalar(fem.form(ufl.inner(ufl.grad(temperature_function), ufl.grad(temperature_function)) * ufl.dx))
    grad_energy = temperature_function.function_space.mesh.comm.allreduce(grad_energy, op=MPI.SUM)
    return math.sqrt(max(0.0, grad_energy) / panel_area)
```

Write the resulting value into:

- `thermal_solution.summary_metrics["temperature_gradient_rms"]`

- [ ] **Step 4: Re-run the focused tests**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  core/solver/gradient_metrics.py \
  core/solver/nonlinear_solver.py \
  core/solver/field_sampler.py \
  evaluation/metrics.py \
  evaluation/engine.py \
  tests/solver/test_gradient_metrics.py \
  tests/evaluation/test_engine.py \
  tests/evaluation/test_cli.py
git commit -m "feat: add official temperature gradient rms metric"
```

## Task 3: Simplify Core And Evaluation To Single-Case First

**Files:**
- Modify: `core/schema/models.py`
- Modify: `core/schema/validation.py`
- Modify: `core/cli/main.py`
- Modify: `core/generator/pipeline.py`
- Delete: `core/generator/paired_pipeline.py`
- Modify: `evaluation/models.py`
- Modify: `evaluation/validation.py`
- Modify: `evaluation/cli.py`
- Delete: `evaluation/multicase_engine.py`
- Delete: `evaluation/operating_cases.py`
- Modify: `tests/schema/test_schema_models.py`
- Modify: `tests/schema/test_schema_validation.py`
- Modify: `tests/generator/test_pipeline.py`
- Modify: `tests/cli/test_cli_end_to_end.py`
- Delete: `tests/evaluation/test_multicase_engine.py`

- [ ] **Step 1: Write the red simplification tests**

Add tests that require:

```python
def test_generate_case_is_the_only_mainline_generation_command():
    parser = build_parser()
    command_names = {action.dest for action in parser._subparsers._group_actions[0].choices.values()}
    assert "generate-operating-case-pair" not in command_names
```

```python
def test_scenario_template_accepts_single_case_templates_without_operating_case_profiles():
    ScenarioTemplate.from_dict(_single_case_template_payload())
```

- [ ] **Step 2: Run the focused tests to confirm failure**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/schema/test_schema_models.py \
  tests/schema/test_schema_validation.py \
  tests/generator/test_pipeline.py \
  tests/cli/test_cli_end_to_end.py -v
```

Expected:

- FAIL because the schema and CLI still preserve the retired multicase path

- [ ] **Step 3: Remove multicase-first contracts**

Simplify the core and evaluation layers so that:

- single-case templates are first-class
- `generate-operating-case-pair` is removed
- the retired multicase models and CLI code are deleted
- single-case evaluation remains the only active public path

- [ ] **Step 4: Re-run the focused tests**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  core/schema/models.py \
  core/schema/validation.py \
  core/cli/main.py \
  core/generator/pipeline.py \
  evaluation/models.py \
  evaluation/validation.py \
  evaluation/cli.py \
  tests/schema/test_schema_models.py \
  tests/schema/test_schema_validation.py \
  tests/generator/test_pipeline.py \
  tests/cli/test_cli_end_to_end.py
git rm \
  core/generator/paired_pipeline.py \
  evaluation/multicase_engine.py \
  evaluation/operating_cases.py \
  tests/evaluation/test_multicase_engine.py
git commit -m "refactor: make core and evaluation single-case first"
```

## Task 4: Refactor The Optimizer Core To Evaluate One Case

**Files:**
- Modify: `optimizers/io.py`
- Modify: `optimizers/models.py`
- Modify: `optimizers/problem.py`
- Modify: `optimizers/drivers/raw_driver.py`
- Modify: `optimizers/drivers/union_driver.py`
- Modify: `optimizers/cli.py`
- Modify: `optimizers/experiment_runner.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`
- Create: `tests/optimizers/test_single_case_problem.py`

- [ ] **Step 1: Write the red optimizer tests**

Add tests that require:

```python
def test_generate_benchmark_case_returns_single_case():
    case = generate_benchmark_case(spec_path, optimization_spec)
    assert case.case_meta["scenario_id"] == "s1_typical"
```

```python
def test_problem_evaluates_single_case_report_and_history():
    record, objective_vector, constraint_vector = problem.evaluate_vector(vector, source="optimizer")
    assert "evaluation_report" in record
    assert "case_reports" not in record
```

- [ ] **Step 2: Run the focused tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_single_case_problem.py \
  tests/optimizers/test_optimizer_cli.py -v
```

Expected:

- FAIL because the optimizer stack still expects multicase inputs and reports

- [ ] **Step 3: Refactor the optimizer path**

Refactor so that:

- `optimizers/io.py` generates one benchmark case
- `optimizers/problem.py` evaluates one case and one solution via `evaluate_case_solution`
- artifacts and history store one evaluation report instead of `case_reports`
- `raw` and `union` drivers share the same single-case core

- [ ] **Step 4: Re-run the focused tests**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  optimizers/io.py \
  optimizers/models.py \
  optimizers/problem.py \
  optimizers/drivers/raw_driver.py \
  optimizers/drivers/union_driver.py \
  optimizers/cli.py \
  optimizers/experiment_runner.py \
  tests/optimizers/test_single_case_problem.py \
  tests/optimizers/test_optimizer_cli.py
git commit -m "refactor: make optimizer stack single-case first"
```

## Task 5: Add Cheap Constraint Screening And Upgrade Repair

**Files:**
- Create: `optimizers/cheap_constraints.py`
- Modify: `optimizers/repair.py`
- Modify: `optimizers/problem.py`
- Modify: `tests/optimizers/test_repair.py`
- Create: `tests/optimizers/test_cheap_constraints.py`

- [ ] **Step 1: Write the red cheap-constraint and repair tests**

Add tests that require:

```python
def test_sink_budget_projection_caps_span_without_breaking_order():
    projected = project_sink_interval(start=0.2, end=0.9, span_max=0.4)
    assert projected.end - projected.start == pytest.approx(0.4)
```

```python
def test_problem_skips_pde_when_cheap_constraints_remain_violated(monkeypatch):
    record, _, _ = problem.evaluate_vector(vector, source="optimizer")
    assert record["failure_reason"] == "cheap_constraint_violation"
    assert record["solver_skipped"] is True
```

- [ ] **Step 2: Run the focused tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_repair.py \
  tests/optimizers/test_cheap_constraints.py \
  tests/optimizers/test_single_case_problem.py -v
```

Expected:

- FAIL because the cheap-constraint gate and new sink-budget repair do not exist yet

- [ ] **Step 3: Implement projection plus local legality restoration**

Implement:

- normalized cheap-constraint calculators
- sink-budget interval projection
- geometry restoration that escalates from local separation to targeted re-placement of the worst offenders
- PDE skipping when cheap constraints still violate after repair

- [ ] **Step 4: Re-run the focused tests**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  optimizers/cheap_constraints.py \
  optimizers/repair.py \
  optimizers/problem.py \
  tests/optimizers/test_repair.py \
  tests/optimizers/test_cheap_constraints.py \
  tests/optimizers/test_single_case_problem.py
git commit -m "feat: add cheap constraint screening and upgraded repair"
```

## Task 6: Generalize Artifacts, Summaries, And Raw Telemetry

**Files:**
- Modify: `optimizers/artifacts.py`
- Modify: `optimizers/generation_callback.py`
- Modify: `optimizers/experiment_summary.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`
- Modify: `tests/visualization/test_report_beamer_pack.py`

- [ ] **Step 1: Write the red generic-summary tests**

Add tests that require:

```python
def test_generation_summary_uses_generic_objective_ids():
    row = callback.rows[0]
    assert "best_minimize_peak_temperature" in row
    assert "best_minimize_temperature_gradient_rms" in row
```

```python
def test_artifacts_write_single_case_representatives():
    manifest = json.loads((output_root / "representatives" / "min-peak-temperature" / "manifest.json").read_text())
    assert manifest["case_snapshot"] == "case.yaml"
    assert manifest["evaluation_snapshot"] == "evaluation.yaml"
```

- [ ] **Step 2: Run the focused tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_optimizer_cli.py \
  tests/visualization/test_report_beamer_pack.py -v
```

Expected:

- FAIL because the current summaries and artifacts still assume old fixed objective names and multicase bundles

- [ ] **Step 3: Refactor artifacts and summaries**

Make summaries generic over objective ids and single-case outputs:

- derive best-objective field names from the actual objective list
- write one case, one solution, one evaluation report per representative
- remove hardcoded hot/cold summary fields

- [ ] **Step 4: Re-run the focused tests**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  optimizers/artifacts.py \
  optimizers/generation_callback.py \
  optimizers/experiment_summary.py \
  tests/optimizers/test_optimizer_cli.py \
  tests/visualization/test_report_beamer_pack.py
git commit -m "refactor: make optimizer artifacts and summaries single-case generic"
```

## Task 7: Replace The Old Union Operator Registry And Controller State

**Files:**
- Modify: `optimizers/operator_pool/operators.py`
- Modify: `optimizers/operator_pool/domain_state.py`
- Modify: `optimizers/operator_pool/policy_kernel.py`
- Modify: `optimizers/operator_pool/prompt_projection.py`
- Modify: `optimizers/operator_pool/llm_controller.py`
- Modify: `optimizers/operator_pool/trace.py`
- Modify: `tests/optimizers/test_operator_pool_contracts.py`
- Modify: `tests/optimizers/test_llm_controller_state.py`
- Modify: `tests/optimizers/test_llm_controller.py`

- [ ] **Step 1: Write the red semantic-operator tests**

Add tests that require:

```python
def test_operator_registry_exposes_semantic_s1_typical_actions():
    assert approved_union_operator_ids_for_backbone("genetic", "nsga2") == (
        "native_sbx_pm",
        "global_explore",
        "local_refine",
        "move_hottest_cluster_toward_sink",
        "spread_hottest_cluster",
        "smooth_high_gradient_band",
        "reduce_local_congestion",
        "repair_sink_budget",
        "slide_sink",
        "rebalance_layout",
    )
```

```python
def test_controller_state_reports_peak_gradient_budget_and_congestion():
    state = build_controller_state(...)
    assert "peak_temperature" in state.metadata["run_state"]
    assert "temperature_gradient_rms" in state.metadata["run_state"]
    assert "sink_budget_utilization" in state.metadata["domain_regime"]
```

- [ ] **Step 2: Run the focused tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_operator_pool_contracts.py \
  tests/optimizers/test_llm_controller_state.py \
  tests/optimizers/test_llm_controller.py -v
```

Expected:

- FAIL because the current operator registry and controller state are still tied to the retired four-component scene

- [ ] **Step 3: Rebuild the semantic action registry**

Implement new family-level operators that:

- express search intent instead of benchmark-specific component names
- auto-select target clusters or regions from current state
- preserve the same shared registry between union-uniform and union-llm

- [ ] **Step 4: Re-run the focused tests**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  optimizers/operator_pool/operators.py \
  optimizers/operator_pool/domain_state.py \
  optimizers/operator_pool/policy_kernel.py \
  optimizers/operator_pool/prompt_projection.py \
  optimizers/operator_pool/llm_controller.py \
  optimizers/operator_pool/trace.py \
  tests/optimizers/test_operator_pool_contracts.py \
  tests/optimizers/test_llm_controller_state.py \
  tests/optimizers/test_llm_controller.py
git commit -m "feat: rebuild union and llm controller semantics for s1_typical"
```

## Task 8: Update Public Docs, Remove Legacy Assets, And Run Verification

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Create: `docs/reports/R70_msfenicsx_s1_typical_mainline_reset_validation_20260402.md`
- Delete all retired old-mainline files listed above
- Modify: `tests/optimizers/test_raw_driver_matrix.py`
- Delete or rewrite any other tests that enforce the retired hot/cold or multi-backbone paper-facing line

- [ ] **Step 1: Write the final red documentation and cleanup checks**

Add checks that require:

```python
def test_repository_has_no_panel_four_component_hot_cold_specs():
    assert not any(Path("scenarios").rglob("panel_four_component_hot_cold*.yaml"))
```

```python
def test_readme_mentions_only_s1_typical_as_active_mainline():
    text = Path("README.md").read_text(encoding="utf-8")
    assert "s1_typical" in text
    assert "panel_four_component_hot_cold" not in text
```

- [ ] **Step 2: Run the targeted tests to confirm cleanup is still pending**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/schema \
  tests/generator \
  tests/solver \
  tests/evaluation \
  tests/optimizers -v
```

Expected:

- FAIL until the old references, docs, and cleanup gaps are removed

- [ ] **Step 3: Update docs and remove retired assets**

Do all of the following in one cleanup pass:

- update `README.md` and `AGENTS.md` so `s1_typical` is the only active mainline
- write the validation report documenting benchmark id, objective definitions, constraint set, verification commands, and artifact paths
- delete retired scenarios, optimizer specs, profiles, docs, outputs, figures, and tests listed in the cleanup section
- remove any leftover code paths that only serve the retired hot/cold or multi-backbone paper-facing line

- [ ] **Step 4: Run the full relevant verification**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/schema \
  tests/generator \
  tests/solver \
  tests/evaluation \
  tests/optimizers -v
```

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main validate-scenario-template \
  --template scenarios/templates/s1_typical.yaml
```

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main generate-case \
  --template scenarios/templates/s1_typical.yaml \
  --seed 11 \
  --output-root ./scenario_runs/generated_cases/s1_typical/seed-11
```

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/s1_typical_raw.yaml \
  --output-root ./scenario_runs/optimizations/s1_typical/raw-smoke
```

Expected:

- all tests PASS
- template validation exits `0`
- single-case generation succeeds
- raw optimization writes a manifest-backed bundle for `s1_typical`

- [ ] **Step 5: Commit**

```bash
git add README.md AGENTS.md docs/reports/R70_msfenicsx_s1_typical_mainline_reset_validation_20260402.md
git add tests/schema tests/generator tests/solver tests/evaluation tests/optimizers
git add scenario_runs/.gitignore
git rm \
  scenarios/templates/panel_four_component_hot_cold_benchmark.yaml \
  scenarios/evaluation/panel_four_component_hot_cold_baseline.yaml \
  scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml \
  scenarios/optimization/panel_four_component_hot_cold_nsga2_raw_b0.yaml \
  scenarios/optimization/panel_four_component_hot_cold_nsga3_raw_b0.yaml \
  scenarios/optimization/panel_four_component_hot_cold_ctaea_raw_b0.yaml \
  scenarios/optimization/panel_four_component_hot_cold_rvea_raw_b0.yaml \
  scenarios/optimization/panel_four_component_hot_cold_moead_raw_b0.yaml \
  scenarios/optimization/panel_four_component_hot_cold_cmopso_raw_b0.yaml \
  scenarios/optimization/panel_four_component_hot_cold_nsga2_union_uniform_p1.yaml \
  scenarios/optimization/panel_four_component_hot_cold_nsga3_union_uniform_p1.yaml \
  scenarios/optimization/panel_four_component_hot_cold_ctaea_union_uniform_p1.yaml \
  scenarios/optimization/panel_four_component_hot_cold_rvea_union_uniform_p1.yaml \
  scenarios/optimization/panel_four_component_hot_cold_moead_union_uniform_p1.yaml \
  scenarios/optimization/panel_four_component_hot_cold_cmopso_union_uniform_p1.yaml \
  scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1.yaml \
  scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1_dashscope_live.yaml \
  scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1_dashscope_smoke.yaml \
  scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1_gpt54_live.yaml \
  scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1_gpt54_smoke.yaml \
  scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1_kimi_live.yaml \
  scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1_kimi_smoke.yaml \
  scenarios/optimization/profiles/panel_four_component_hot_cold_nsga2_raw.yaml \
  scenarios/optimization/profiles/panel_four_component_hot_cold_nsga2_union.yaml \
  scenarios/optimization/profiles/panel_four_component_hot_cold_nsga3_raw.yaml \
  scenarios/optimization/profiles/panel_four_component_hot_cold_nsga3_union.yaml \
  docs/superpowers/specs/2026-03-27-paper-grade-multiobjective-thermal-baseline-design.md \
  docs/superpowers/specs/2026-03-27-multi-backbone-optimizer-matrix-design.md \
  docs/superpowers/specs/2026-03-28-nsga2-hybrid-union-controller-design.md \
  docs/superpowers/specs/2026-03-28-openai-union-llm-controller-design.md \
  docs/superpowers/specs/2026-04-01-nsga2-three-mode-experiment-logging-visualization-design.md \
  docs/superpowers/specs/2026-04-01-s1-dense-benchmark-design.md \
  docs/superpowers/plans/2026-03-27-paper-grade-multiobjective-thermal-baseline.md \
  docs/superpowers/plans/2026-03-27-multi-backbone-optimizer-matrix.md \
  docs/superpowers/plans/2026-03-28-nsga2-hybrid-union-controller.md \
  docs/superpowers/plans/2026-03-31-l1-domain-grounded-controller-state-completion.md \
  docs/superpowers/plans/2026-03-31-l1-llm-stability-diagnostics-and-repair.md \
  docs/superpowers/plans/2026-03-31-l1-reusable-controller-kernel-stabilization.md \
  docs/superpowers/plans/2026-04-01-nsga2-three-mode-experiment-logging-visualization.md
git commit -m "refactor: reset mainline around s1_typical"
```

