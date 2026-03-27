# Msfenicsx Multicase Multiobjective Mainline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current single-objective optimizer mainline with a multicase, multiobjective satellite thermal optimization workflow that reflects realistic hot/cold trade-offs and produces Pareto-style outputs.

**Architecture:** Keep `core/` unchanged as the canonical single-case physics kernel around `thermal_case` and `thermal_solution`. Move the new realism into outer layers by adding multicase evaluation contracts, paired hot/cold operating-case handling, richer thermal metrics, and a Pareto-oriented `optimizers/` layer built around `NSGA-II` before any LLM policy work resumes.

**Tech Stack:** Python 3.12, PyYAML, NumPy, Shapely, FEniCSx (`dolfinx`, `ufl`, `mpi4py`, `petsc4py`), `pymoo`, pytest

---

## File Structure

### Docs and Active Guidance

- Modify: `README.md`
  Rewrite the active optimization narrative around multicase multiobjective search and remove single-objective CLI examples from the mainline description.
- Modify: `AGENTS.md`
  Update repository status and execution examples to reference the new multicase optimizer workflow.
- Modify: `RULES.md`
  Add explicit wording that active optimization claims must identify operating cases and Pareto reporting rather than a single scalar best score.
- Create: `docs/reports/R63_msfenicsx_multicase_multiobjective_reset_20260327.md`
  Document the design reset, why single-objective is no longer the active path, and what replaces it.

### Evaluation Layer

- Modify: `evaluation/models.py`
  Extend the contracts to support multicase evaluation specs and reports instead of only one case and one solution.
- Modify: `evaluation/validation.py`
  Validate multicase operating-point definitions, objective reducers, and report structure.
- Modify: `evaluation/io.py`
  Load and save the new multicase evaluation spec and report contracts.
- Modify: `evaluation/metrics.py`
  Add metrics needed for realistic thermal trade-offs, especially component spread and worst-component summaries.
- Create: `evaluation/multicase_engine.py`
  Aggregate multiple solved operating cases into one multicase evaluation report.
- Create: `evaluation/operating_cases.py`
  Materialize explicit hot/cold operating cases from base cases or case families.
- Modify: `evaluation/cli.py`
  Replace the current single-case CLI mainline with multicase evaluation commands.

### Scenario Data

- Create: `scenarios/manual/reference_case_hot.yaml`
  Hot-case deterministic operating point for the reference layout.
- Create: `scenarios/manual/reference_case_cold.yaml`
  Cold-case deterministic operating point for the reference layout.
- Create: `scenarios/evaluation/panel_hot_cold_multiobjective_baseline.yaml`
  The new baseline evaluation spec with two or three objectives and explicit hot/cold constraints.
- Create: `scenarios/optimization/reference_hot_cold_nsga2.yaml`
  The new baseline optimization spec for `NSGA-II`.
- Delete later: `scenarios/evaluation/panel_single_objective_baseline.yaml`
- Delete later: `scenarios/optimization/reference_case_position_search.yaml`

### Optimizer Layer

- Modify: `optimizers/models.py`
  Replace the single-best result contract with Pareto-front and representative-candidate contracts.
- Modify: `optimizers/validation.py`
  Validate `NSGA-II` configuration and Pareto result payloads.
- Modify: `optimizers/io.py`
  Read and write the new optimizer result structure.
- Modify: `optimizers/artifacts.py`
  Export Pareto bundles rather than one best bundle.
- Modify: `optimizers/pymoo_driver.py`
  Replace the single-objective `GA` baseline with multicase multiobjective `NSGA-II` orchestration.
- Modify: `optimizers/cli.py`
  Expose a multicase optimize command and write Pareto outputs.

### Tests

- Create: `tests/evaluation/test_multicase_engine.py`
- Create: `tests/evaluation/test_operating_cases.py`
- Modify: `tests/evaluation/test_io.py`
- Modify: `tests/evaluation/test_cli.py`
- Create: `tests/optimizers/test_nsga2_driver.py`
- Modify: `tests/optimizers/test_optimizer_io.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`
- Delete later: single-objective-only tests that assert `best_candidate` or `primary_objective` as the active output contract

## Task 1: Reset the Active Problem Statement and Remove Single-Objective Mainline Language

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `RULES.md`
- Create: `docs/reports/R63_msfenicsx_multicase_multiobjective_reset_20260327.md`

- [ ] **Step 1: Write the failing documentation expectation test or checklist**

Record the new required truths:

- active optimization is multicase and multiobjective
- hot/cold operating cases are part of the baseline problem definition
- single-objective search is no longer the active mainline

- [ ] **Step 2: Rewrite the active flow in `README.md`**

The new top-level flow should read conceptually like:

```text
base design case
  -> operating-case expansion (hot/cold)
  -> FEniCSx solve for each operating case
  -> multicase evaluation report
  -> NSGA-II Pareto search
  -> Pareto artifacts and representative solutions
```

- [ ] **Step 3: Update `AGENTS.md` and `RULES.md` to match**

Add wording that:

- multicase objective claims require naming operating cases
- Pareto outputs replace single best-score claims
- active optimizer examples should use the new multicase spec

- [ ] **Step 4: Write the reset report**

The report must explain:

- why the single-objective path is no longer the mainline
- why `NSGA-II` is the first multicase baseline instead of `NSGA-III`
- which parts of the old implementation are reusable internals versus deleted active interfaces

- [ ] **Step 5: Commit the doc reset**

```bash
cd /home/hymn/msfenicsx
git add README.md AGENTS.md RULES.md docs/reports/R63_msfenicsx_multicase_multiobjective_reset_20260327.md
git commit -m "docs: reset active optimization path to multicase multiobjective"
```

## Task 2: Add Explicit Hot/Cold Reference Operating Cases

**Files:**
- Create: `scenarios/manual/reference_case_hot.yaml`
- Create: `scenarios/manual/reference_case_cold.yaml`
- Test: `tests/evaluation/test_operating_cases.py`

- [ ] **Step 1: Write the failing operating-case test**

```python
from core.schema.io import load_case


def test_reference_hot_and_cold_cases_share_geometry_but_differ_in_environment():
    hot = load_case("scenarios/manual/reference_case_hot.yaml")
    cold = load_case("scenarios/manual/reference_case_cold.yaml")
    assert hot.components == cold.components
    assert hot.loads != cold.loads or hot.boundary_features != cold.boundary_features
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `conda run -n msfenicsx pytest tests/evaluation/test_operating_cases.py -v`
Expected: FAIL because the files do not exist

- [ ] **Step 3: Create deterministic hot/cold paired cases**

Use the same geometry and component identities, but change the thermal operating conditions deliberately:

- hot case: higher internal dissipation and weaker external rejection
- cold case: lower internal dissipation and stronger tendency to overcool

The pair should still be plausible within the current 2D panel abstraction.

- [ ] **Step 4: Document the intended engineering meaning inside the YAML provenance**

Each file should make it obvious whether it represents:

- hot operational load
- cold survival or low-load condition

- [ ] **Step 5: Run the test again**

Run: `conda run -n msfenicsx pytest tests/evaluation/test_operating_cases.py -v`
Expected: PASS

- [ ] **Step 6: Commit the operating cases**

```bash
cd /home/hymn/msfenicsx
git add scenarios/manual/reference_case_hot.yaml scenarios/manual/reference_case_cold.yaml tests/evaluation/test_operating_cases.py
git commit -m "feat: add hot and cold reference operating cases"
```

## Task 3: Extend Evaluation from Single-Case to Multicase Aggregation

**Files:**
- Modify: `evaluation/models.py`
- Modify: `evaluation/validation.py`
- Modify: `evaluation/io.py`
- Modify: `evaluation/metrics.py`
- Create: `evaluation/multicase_engine.py`
- Modify: `evaluation/cli.py`
- Create: `tests/evaluation/test_multicase_engine.py`
- Modify: `tests/evaluation/test_io.py`
- Modify: `tests/evaluation/test_cli.py`

- [ ] **Step 1: Write the failing multicase engine test**

```python
from evaluation.multicase_engine import evaluate_operating_cases


def test_multicase_evaluation_reports_all_operating_cases():
    report = evaluate_operating_cases(...)
    assert set(report.case_reports) == {"hot", "cold"}
    assert len(report.objective_summary) >= 2
```

- [ ] **Step 2: Run the multicase evaluation tests to verify they fail**

Run: `conda run -n msfenicsx pytest tests/evaluation/test_multicase_engine.py tests/evaluation/test_io.py tests/evaluation/test_cli.py -v`
Expected: FAIL because the multicase engine and contracts do not exist

- [ ] **Step 3: Define the new evaluation contracts**

The new spec should allow:

- named operating cases such as `hot` and `cold`
- objectives defined by case-scoped metrics or reducers
- constraints defined per operating case or across all cases

The new report should include:

- `case_reports` keyed by operating case id
- `objective_summary`
- `constraint_reports`
- `derived_signals`
- `worst_case_signals`

- [ ] **Step 4: Add realistic baseline metrics**

Add at least these metric families:

- `summary.temperature_span`
  - `temperature_max - temperature_min`
- `summary.temperature_rise`
  - `temperature_max - ambient-like reference` when available
- `components.max_temperature_spread`
  - the spread between hottest and coolest component means
- `case.total_radiator_span`
  - sum of `line_sink` extents as a 2D radiator-resource proxy

Do not add metrics that require new unsupported field exports in this task.

- [ ] **Step 5: Implement multicase aggregation**

The aggregation should support a first baseline with:

- `Obj 1`: minimize hot-case worst component or worst-field maximum temperature
- `Obj 2`: minimize cold-case radiator burden proxy or equivalent thermal-control resource proxy
- optional `Obj 3`: minimize temperature non-uniformity

- [ ] **Step 6: Add a multicase evaluation CLI**

Preferred command shape:

```bash
conda run -n msfenicsx python -m evaluation.cli evaluate-operating-cases \
  --case hot=scenarios/manual/reference_case_hot.yaml \
  --case cold=scenarios/manual/reference_case_cold.yaml \
  --spec scenarios/evaluation/panel_hot_cold_multiobjective_baseline.yaml \
  --output ./multicase_evaluation.yaml
```

- [ ] **Step 7: Run the focused evaluation tests**

Run: `conda run -n msfenicsx pytest tests/evaluation -v`
Expected: PASS

- [ ] **Step 8: Commit the multicase evaluation layer**

```bash
cd /home/hymn/msfenicsx
git add evaluation scenarios/evaluation/panel_hot_cold_multiobjective_baseline.yaml tests/evaluation
git commit -m "feat: add multicase multiobjective evaluation layer"
```

## Task 4: Replace the Single-Objective Optimizer Contract with a Pareto-First Baseline

**Files:**
- Modify: `optimizers/models.py`
- Modify: `optimizers/validation.py`
- Modify: `optimizers/io.py`
- Modify: `optimizers/pymoo_driver.py`
- Modify: `tests/optimizers/test_optimizer_io.py`
- Create: `tests/optimizers/test_nsga2_driver.py`

- [ ] **Step 1: Write the failing optimizer result contract test**

```python
from optimizers.models import OptimizationResult


def test_optimization_result_requires_pareto_front():
    payload = {...}
    result = OptimizationResult.from_dict(payload)
    assert result.pareto_front
```

- [ ] **Step 2: Run the optimizer contract tests to verify they fail**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_optimizer_io.py tests/optimizers/test_nsga2_driver.py -v`
Expected: FAIL because the result model still assumes `best_candidate`

- [ ] **Step 3: Redefine optimizer outputs**

The active result payload should contain:

- `baseline_candidates`
- `pareto_front`
- `representative_candidates`
- `aggregate_metrics`
- `history`

Representative candidates should include at least:

- `min_hot_peak`
- `min_resource_proxy`
- `knee_candidate` when identifiable

- [ ] **Step 4: Support `NSGA-II` as the new baseline algorithm**

The algorithm config should look like:

```yaml
algorithm:
  name: pymoo_nsga2
  population_size: 32
  num_generations: 20
  seed: 7
```

Do not implement `NSGA-III` in the first cut unless the objective count immediately exceeds three.

- [ ] **Step 5: Replace single-best selection logic with Pareto dominance logic**

Remove active dependencies on:

- `primary_objective`
- `best_candidate`
- `objective_improvement_ratio`

and replace them with:

- Pareto set extraction
- feasible Pareto rate
- hypervolume or a simpler first-pass Pareto quality metric if hypervolume is not yet stable

- [ ] **Step 6: Run optimizer tests**

Run: `conda run -n msfenicsx pytest tests/optimizers -v`
Expected: PASS

- [ ] **Step 7: Commit the Pareto contract reset**

```bash
cd /home/hymn/msfenicsx
git add optimizers tests/optimizers
git commit -m "refactor: replace single-objective optimizer contract with pareto baseline"
```

## Task 5: Implement Multicase Objective Evaluation Inside the Optimizer Loop

**Files:**
- Modify: `optimizers/pymoo_driver.py`
- Modify: `optimizers/cli.py`
- Modify: `tests/optimizers/test_nsga2_driver.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`
- Create: `scenarios/optimization/reference_hot_cold_nsga2.yaml`

- [ ] **Step 1: Write the failing multicase optimizer test**

```python
from optimizers.pymoo_driver import run_optimization


def test_nsga2_solves_hot_and_cold_cases_for_each_candidate():
    run = run_optimization(...)
    assert run.result.pareto_front
    assert {"hot", "cold"} <= set(run.result.history[0]["case_reports"])
```

- [ ] **Step 2: Run the focused driver test to verify it fails**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_nsga2_driver.py::test_nsga2_solves_hot_and_cold_cases_for_each_candidate -v`
Expected: FAIL because the driver still evaluates only one case

- [ ] **Step 3: Implement multicase candidate evaluation**

For each decision vector:

1. apply the vector to the shared design variables
2. materialize the hot operating case
3. solve the hot case
4. materialize the cold operating case
5. solve the cold case
6. aggregate them through the multicase evaluation engine
7. return the objective and constraint vectors to `pymoo`

- [ ] **Step 4: Add the new baseline optimization spec**

The spec should search the design variables that are meaningful in the current dataset, prioritizing:

- payload position
- payload size or count only if the geometry contract remains stable
- radiator span only after the generator or manual cases genuinely support it as a controllable design variable

- [ ] **Step 5: Add a multicase optimizer CLI**

Preferred command shape:

```bash
conda run -n msfenicsx python -m optimizers.cli optimize-operating-cases \
  --case hot=scenarios/manual/reference_case_hot.yaml \
  --case cold=scenarios/manual/reference_case_cold.yaml \
  --optimization-spec scenarios/optimization/reference_hot_cold_nsga2.yaml \
  --output-root ./scenario_runs/optimizations/reference-hot-cold-nsga2
```

- [ ] **Step 6: Run the optimizer verification**

Run: `conda run -n msfenicsx pytest tests/optimizers tests/cli/test_module_entrypoints.py -v`
Expected: PASS

- [ ] **Step 7: Run one fresh real CLI verification**

Run:

```bash
conda run -n msfenicsx python -m optimizers.cli optimize-operating-cases \
  --case hot=scenarios/manual/reference_case_hot.yaml \
  --case cold=scenarios/manual/reference_case_cold.yaml \
  --optimization-spec scenarios/optimization/reference_hot_cold_nsga2.yaml \
  --output-root /tmp/msfenicsx_hot_cold_nsga2
```

Expected:

- a non-empty Pareto output
- at least one feasible representative candidate
- written artifacts under the output root

- [ ] **Step 8: Commit the multicase optimizer loop**

```bash
cd /home/hymn/msfenicsx
git add optimizers scenarios/optimization/reference_hot_cold_nsga2.yaml tests/optimizers tests/cli
git commit -m "feat: add multicase nsga2 thermal optimizer baseline"
```

## Task 6: Export Pareto Artifacts Instead of a Single Best Bundle

**Files:**
- Modify: `optimizers/artifacts.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`

- [ ] **Step 1: Write the failing artifact test**

```python
def test_optimizer_artifacts_write_pareto_front(tmp_path):
    ...
    assert (tmp_path / "pareto_front.json").exists()
    assert (tmp_path / "representatives").is_dir()
```

- [ ] **Step 2: Run the artifact test to verify it fails**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_optimizer_cli.py -v`
Expected: FAIL because only one best bundle is exported

- [ ] **Step 3: Implement Pareto artifact layout**

The output root should contain at least:

```text
optimization_result.json
pareto_front.json
representatives/
  min-hot-peak/
    case_hot.yaml
    case_cold.yaml
    evaluation.yaml
  min-resource-proxy/
    case_hot.yaml
    case_cold.yaml
    evaluation.yaml
```

- [ ] **Step 4: Run the artifact tests**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_optimizer_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit the artifact format change**

```bash
cd /home/hymn/msfenicsx
git add optimizers/artifacts.py tests/optimizers/test_optimizer_cli.py
git commit -m "feat: export pareto optimizer artifacts"
```

## Task 7: Remove the Old Single-Objective Active Path

**Files:**
- Delete: `scenarios/evaluation/panel_single_objective_baseline.yaml`
- Delete: `scenarios/optimization/reference_case_position_search.yaml`
- Delete or rewrite: tests that require `best_candidate` or `baseline_primary_objective`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/reports/` references that still advertise the single-objective path as active

- [ ] **Step 1: Confirm the multicase baseline is green before deleting the old path**

Run:

```bash
conda run -n msfenicsx pytest tests/evaluation tests/optimizers tests/cli -v
```

Expected: PASS

- [ ] **Step 2: Delete obsolete single-objective scenario specs and active references**

Delete the files listed above and remove any CLI examples that point users back to them.

- [ ] **Step 3: Remove single-objective result language from tests and docs**

Delete assertions or examples centered on:

- `best_candidate`
- `primary_objective`
- `objective_improvement_ratio`

unless they survive only as private compatibility shims during the cutover.

- [ ] **Step 4: Run the post-cutover verification**

Run:

```bash
conda run -n msfenicsx pytest -v
```

Expected: PASS with the multicase multiobjective path as the only active optimizer mainline

- [ ] **Step 5: Commit the cutover**

```bash
cd /home/hymn/msfenicsx
git add -A
git commit -m "refactor: remove obsolete single-objective optimizer path"
```

## Task 8: Prepare the Next LLM Phase Against the New Mainline

**Files:**
- Modify later: `docs/msgalaxy/R60_msfenicsx_2d_fenicsx_migration_initial_report_20260326.md` only if active framing must be clarified
- Create later: `docs/superpowers/specs/2026-03-27-msfenicsx-multicase-llm-prior-design.md`
- Create later: `llm/` contracts after the multicase optimizer is stable

- [ ] **Step 1: Freeze the non-LLM multicase baseline first**

Do not start `llm/` implementation until:

- multicase evaluation is stable
- `NSGA-II` Pareto outputs are stable
- representative candidate selection is stable

- [ ] **Step 2: Define the future LLM context against Pareto search**

The future `llm_context_pack` should consume:

- hot/cold case summaries
- Pareto history
- violated operating-case constraints
- objective trade-off signals

- [ ] **Step 3: Treat the old single-objective LLM framing as deleted**

Do not design the next LLM phase around:

- one scalar best score
- one best candidate
- one case only

The active future framing is strategy over Pareto search under multicase thermal constraints.

## Notes for Execution

- `NSGA-II` is the correct first baseline for two or three objectives; do not jump to `NSGA-III` until the objective count justifies it.
- The first realism upgrade is multicase hot/cold behavior, not adding many loosely justified objectives.
- Keep `core/` single-case and canonical. Multicase grouping, aggregation, and Pareto logic belong outside `core/`.
- Reuse the existing single-case solve and single-case evaluation internals where they remain useful, but delete obsolete single-objective public contracts and scenario specs once the replacement is verified.
- Do not invent structural-mass or wiring-complexity proxies in the first cut unless they are grounded in current case data.
- Prefer two strong objectives plus hard thermal constraints over four weakly justified objectives.

## Local Review Limitation

This plan was reviewed locally against the current repository docs and the new user-approved direction, but subagent-based plan review was not performed in-session because delegation was not explicitly requested for this conversation.
