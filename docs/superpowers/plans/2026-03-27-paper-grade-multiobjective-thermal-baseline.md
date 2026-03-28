# Paper-Grade Multiobjective Thermal Baseline Implementation Plan

> Superseded note: Tasks `1-5` in this plan remain part of the implemented platform history for the paired hot/cold benchmark. The earlier heuristic-hybrid `B1` direction described later in this file is no longer the active paper-facing mainline and is superseded first by `docs/superpowers/plans/2026-03-27-pure-nsga2-mainline-reset.md`, then for multi-backbone platform work by `docs/superpowers/plans/2026-03-27-multi-backbone-optimizer-matrix.md`, and now for the paper-facing controller line by `docs/superpowers/plans/2026-03-28-nsga2-hybrid-union-controller.md`. The `P1-union-uniform-nsga2` rung has since been implemented, and the immediate next paper-facing implementation step is `L1-union-llm-nsga2`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current toy multicase optimizer path with a paper-grade hot/cold multiobjective thermal benchmark generated from the active platform, using `NSGA-II` and a hybrid-operator extension as the new research baseline.

**Architecture:** Keep `core/` as the single-case canonical kernel, but upgrade its schema and generator so one sampled layout can produce paired hot/cold `thermal_case` instances. Keep all objectives, constraints, multicase aggregation, optimizer contracts, and operator logic outside `core/` in `evaluation/` and `optimizers/`, then delete the old one-component benchmark assets instead of carrying compatibility.

**Tech Stack:** Python 3.12, PyYAML, NumPy, Shapely, FEniCSx (`dolfinx`, `ufl`, `mpi4py`, `petsc4py`), `pymoo`, pytest

---

Spec reference: `docs/superpowers/specs/2026-03-27-paper-grade-multiobjective-thermal-baseline-design.md`

This plan is the active implementation plan for the paper-grade baseline. Do not reintroduce the earlier toy multicase reset path.

## File Structure

### Canonical Schema and Solver Input

- Modify: `core/schema/models.py`
  Add explicit benchmark-supporting contract fields:
  - `ScenarioTemplate.operating_case_profiles`
  - `ThermalCase.panel_material_ref`
- Modify: `core/schema/validation.py`
  Validate the new template and case fields, especially explicit panel material selection and named hot/cold profile structure.
- Modify: `core/solver/case_to_geometry.py`
  Stop inferring the panel material from the first material entry and instead use `panel_material_ref`.
- Modify: `tests/schema/test_schema_models.py`
- Modify: `tests/schema/test_schema_validation.py`
- Modify: `tests/schema/test_schema_io.py`

### Generator and Core CLI

- Modify: `core/generator/parameter_sampler.py`
  Replace the generic `avionic-box` sampling assumptions with role-aware fixed-family sampling for `processor`, `rf_power_amp`, `obc`, and `battery_pack`.
- Modify: `core/generator/case_builder.py`
  Split shared-layout payload assembly from per-operating-case thermal payload assembly.
- Create: `core/generator/operating_case_builder.py`
  Build one `thermal_case` from a shared layout sample plus one named operating-case profile.
- Create: `core/generator/paired_pipeline.py`
  Generate a shared layout once and emit paired `hot` and `cold` cases.
- Modify: `core/generator/pipeline.py`
  Keep `generate_case()` as the low-level single-case path only if it remains internally useful, but move the active benchmark path to paired generation.
- Modify: `core/cli/main.py`
  Add a clean benchmark-generation command such as `generate-operating-case-pair`.
- Create: `scenarios/templates/panel_four_component_hot_cold_benchmark.yaml`
  Active benchmark template with four named roles and hot/cold operating profiles.
- Modify: `tests/generator/test_parameter_sampler.py`
- Modify: `tests/generator/test_pipeline.py`
- Modify: `tests/cli/test_cli_end_to_end.py`
- Modify: `tests/cli/test_module_entrypoints.py`

### Evaluation Layer

- Modify: `evaluation/metrics.py`
  Add the component-specific and resource metrics required by the new benchmark.
- Modify: `evaluation/validation.py`
  Tighten validation around the new objective and constraint IDs and any component-scoped metrics.
- Modify: `evaluation/multicase_engine.py`
  Ensure the multicase report exposes the exact summary structure needed by the new baseline.
- Modify: `evaluation/io.py`
  Load and save the new active multicase evaluation spec cleanly.
- Modify: `evaluation/cli.py`
  Keep multicase evaluation as the active CLI path and update examples to the new benchmark names.
- Create: `scenarios/evaluation/panel_four_component_hot_cold_baseline.yaml`
  Active evaluation spec with three objectives and four constraints.
- Modify: `tests/evaluation/test_multicase_engine.py`
- Modify: `tests/evaluation/test_operating_cases.py`
- Modify: `tests/evaluation/test_io.py`
- Modify: `tests/evaluation/test_cli.py`

### Optimizer Layer

- Modify: `optimizers/models.py`
  Extend `OptimizationSpec` to carry a reproducible benchmark source instead of relying on hand-authored case files.
- Modify: `optimizers/validation.py`
  Validate the new `benchmark_source` and hybrid-operator settings.
- Modify: `optimizers/io.py`
  Resolve benchmark templates, seeds, evaluation specs, and algorithm variants from the new optimizer specs.
- Modify: `optimizers/codec.py`
  Keep the vector codec path-based, but verify the new component and radiator variables cleanly.
- Create: `optimizers/repair.py`
  Project mutated vectors back into legal geometry and radiator intervals.
- Create: `optimizers/problem.py`
  Keep the `pymoo` problem definition focused and separate from driver orchestration.
- Modify: `optimizers/pymoo_driver.py`
  Orchestrate both `B0` vanilla `NSGA-II` and `B1` hybrid-operator `NSGA-II`.
- Create: `optimizers/operators.py`
  Implement domain-aware operators such as `hotspot_pull`, `battery_relief`, `pair_separate`, `radiator_slide`, and `radiator_expand_contract`.
- Modify: `optimizers/artifacts.py`
  Export representative bundles and operator telemetry for the new baseline.
- Modify: `optimizers/cli.py`
  Replace the case-file-driven mainline with an optimization-spec-driven benchmark command.
- Create: `scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml`
- Create: `scenarios/optimization/panel_four_component_hot_cold_hybrid_nsga2_b1.yaml`
- Modify: `tests/optimizers/test_codec.py`
- Modify: `tests/optimizers/test_optimizer_io.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`
- Modify: `tests/optimizers/test_nsga2_driver.py`

### Solver and Benchmark Smoke Coverage

- Modify: `tests/solver/test_generated_case.py`
  Solve a generated benchmark operating case from the new template.
- Modify: `tests/solver/test_reference_case.py`
  Replace the old `scenarios/manual/reference_case.yaml` dependency with a generated benchmark pair or a deterministic hot/cold reference generated during the test.

### Cleanup and Active Documentation

- Delete: `scenarios/templates/panel_radiation_baseline.yaml`
- Delete: `scenarios/manual/reference_case.yaml`
- Delete: `scenarios/manual/reference_case_hot.yaml`
- Delete: `scenarios/manual/reference_case_cold.yaml`
- Delete: `scenarios/evaluation/panel_hot_cold_multiobjective_baseline.yaml`
- Delete: `scenarios/optimization/reference_hot_cold_nsga2.yaml`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Create: `docs/reports/R64_msfenicsx_paper_grade_multiobjective_baseline_rollout_20260327.md`

## Task 1: Upgrade Canonical Contracts for an Explicit Panel Substrate and Hot/Cold Profiles

**Files:**
- Modify: `core/schema/models.py`
- Modify: `core/schema/validation.py`
- Modify: `core/solver/case_to_geometry.py`
- Modify: `tests/schema/test_schema_models.py`
- Modify: `tests/schema/test_schema_validation.py`
- Modify: `tests/schema/test_schema_io.py`

- [ ] **Step 1: Write the failing schema tests**

Add tests that require:

```python
def test_thermal_case_requires_explicit_panel_material_ref():
    payload = _case_payload()
    payload["panel_material_ref"] = "panel_substrate"
    case = ThermalCase.from_dict(payload)
    assert case.panel_material_ref == "panel_substrate"
```

```python
def test_scenario_template_supports_named_operating_case_profiles():
    payload = _template_payload()
    payload["operating_case_profiles"] = [
        {
            "operating_case_id": "hot",
            "ambient_temperature": 300.0,
            "component_power_overrides": {"processor": 24.0},
            "boundary_feature_overrides": {"radiator_top": {"sink_temperature": 292.0}},
        }
    ]
    template = ScenarioTemplate.from_dict(payload)
    assert template.operating_case_profiles[0]["operating_case_id"] == "hot"
```

- [ ] **Step 2: Run the schema tests to verify they fail**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/schema/test_schema_models.py tests/schema/test_schema_validation.py tests/schema/test_schema_io.py -v`
Expected: FAIL because the new fields are not yet accepted.

- [ ] **Step 3: Add the new contract fields**

Implement these minimum structures:

```python
@dataclass(slots=True)
class ScenarioTemplate:
    ...
    operating_case_profiles: list[dict[str, Any]]
```

```python
@dataclass(slots=True)
class ThermalCase:
    ...
    panel_material_ref: str
```

Validation must enforce:

- `panel_material_ref` exists in `materials`
- each `operating_case_profile` has a unique `operating_case_id`
- each override targets known component roles or boundary feature IDs

- [ ] **Step 4: Update solver interpretation to use `panel_material_ref`**

Replace the current implicit logic:

```python
first_material = next(iter(materials.values()))
default_conductivity = float(first_material["conductivity"])
```

with explicit substrate lookup:

```python
panel_material = materials[payload["panel_material_ref"]]
default_conductivity = float(panel_material["conductivity"])
default_emissivity = float(panel_material.get("emissivity", 0.8))
```

- [ ] **Step 5: Run the schema tests again**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/schema/test_schema_models.py tests/schema/test_schema_validation.py tests/schema/test_schema_io.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd /home/hymn/msfenicsx
git add core/schema/models.py core/schema/validation.py core/solver/case_to_geometry.py tests/schema/test_schema_models.py tests/schema/test_schema_validation.py tests/schema/test_schema_io.py
git commit -m "feat: add explicit panel substrate and operating case profiles"
```

## Task 2: Build the New Paired Hot/Cold Benchmark Generator

**Files:**
- Modify: `core/generator/parameter_sampler.py`
- Modify: `core/generator/case_builder.py`
- Create: `core/generator/operating_case_builder.py`
- Create: `core/generator/paired_pipeline.py`
- Modify: `core/generator/pipeline.py`
- Modify: `core/cli/main.py`
- Create: `scenarios/templates/panel_four_component_hot_cold_benchmark.yaml`
- Modify: `tests/generator/test_parameter_sampler.py`
- Modify: `tests/generator/test_pipeline.py`
- Modify: `tests/cli/test_cli_end_to_end.py`
- Modify: `tests/cli/test_module_entrypoints.py`

- [ ] **Step 1: Write the failing generator tests**

Add tests for the active benchmark path:

```python
from core.generator.paired_pipeline import generate_operating_case_pair


def test_generate_operating_case_pair_returns_hot_and_cold_cases():
    cases = generate_operating_case_pair("scenarios/templates/panel_four_component_hot_cold_benchmark.yaml", seed=11)
    assert set(cases) == {"hot", "cold"}
    assert cases["hot"].components == cases["cold"].components
    assert cases["hot"].loads != cases["cold"].loads
```

```python
def test_generate_operating_case_pair_uses_four_named_roles():
    cases = generate_operating_case_pair("scenarios/templates/panel_four_component_hot_cold_benchmark.yaml", seed=5)
    roles = {component["role"] for component in cases["hot"].to_dict()["components"]}
    assert roles == {"processor", "rf_power_amp", "obc", "battery_pack"}
```

- [ ] **Step 2: Run the generator tests to verify they fail**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/generator/test_parameter_sampler.py tests/generator/test_pipeline.py -v`
Expected: FAIL because the paired benchmark pipeline does not yet exist.

- [ ] **Step 3: Implement role-aware sampling**

Replace the old generic-family assumptions with fixed benchmark families:

```yaml
component_families:
  - family_id: processor
    role: processor
    count_range: {min: 1, max: 1}
  - family_id: rf_power_amp
    role: rf_power_amp
    count_range: {min: 1, max: 1}
  - family_id: obc
    role: obc
    count_range: {min: 1, max: 1}
  - family_id: battery_pack
    role: battery_pack
    count_range: {min: 1, max: 1}
```

The sampler should continue to be deterministic by seed.

- [ ] **Step 4: Split shared layout from operating-case thermal overrides**

Use one shared layout sample, then build one case per operating profile:

```python
def build_operating_case(template, sampled_layout, operating_case_profile, seed) -> ThermalCase:
    ...
```

Each case should differ only in:

- `case_meta.case_id`
- `loads`
- `boundary_features` thermal sink values
- `physics.ambient_temperature`
- `provenance.operating_case`

- [ ] **Step 5: Add the benchmark CLI command**

Add a new command in `core/cli/main.py`:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main generate-operating-case-pair \
  --template scenarios/templates/panel_four_component_hot_cold_benchmark.yaml \
  --seed 11 \
  --output-root ./generated_cases
```

Expected files:

- `generated_cases/<case-id>-hot.yaml`
- `generated_cases/<case-id>-cold.yaml`

- [ ] **Step 6: Create the active benchmark template**

The template must contain:

- explicit `panel_material_ref` target material
- four named component families
- one radiator boundary feature family
- two operating profiles: `hot`, `cold`
- a deterministic reference seed that is intentionally infeasible before optimization

- [ ] **Step 7: Run the generator and CLI tests again**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/generator/test_parameter_sampler.py tests/generator/test_pipeline.py tests/cli/test_cli_end_to_end.py tests/cli/test_module_entrypoints.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
cd /home/hymn/msfenicsx
git add core/generator/parameter_sampler.py core/generator/case_builder.py core/generator/operating_case_builder.py core/generator/paired_pipeline.py core/generator/pipeline.py core/cli/main.py scenarios/templates/panel_four_component_hot_cold_benchmark.yaml tests/generator/test_parameter_sampler.py tests/generator/test_pipeline.py tests/cli/test_cli_end_to_end.py tests/cli/test_module_entrypoints.py
git commit -m "feat: generate paired hot cold benchmark cases"
```

## Task 3: Replace the Active Evaluation Baseline with the New Paper-Grade Benchmark

**Files:**
- Modify: `evaluation/metrics.py`
- Modify: `evaluation/validation.py`
- Modify: `evaluation/multicase_engine.py`
- Modify: `evaluation/io.py`
- Modify: `evaluation/cli.py`
- Create: `scenarios/evaluation/panel_four_component_hot_cold_baseline.yaml`
- Modify: `tests/evaluation/test_multicase_engine.py`
- Modify: `tests/evaluation/test_operating_cases.py`
- Modify: `tests/evaluation/test_io.py`
- Modify: `tests/evaluation/test_cli.py`

- [ ] **Step 1: Write the failing evaluation tests**

Add tests that pin the new objective and constraint story:

```python
def test_multicase_report_contains_component_specific_hot_and_cold_metrics():
    report = evaluate_operating_cases(cases, solutions, spec)
    objective_ids = {item["objective_id"] for item in report.objective_summary}
    assert objective_ids == {
        "minimize_hot_pa_peak",
        "maximize_cold_battery_min",
        "minimize_radiator_resource",
    }
```

```python
def test_multicase_constraints_cover_hot_electronics_and_cold_battery():
    report = evaluate_operating_cases(cases, solutions, spec)
    constraint_ids = {item["constraint_id"] for item in report.constraint_reports}
    assert constraint_ids == {
        "hot_pa_limit",
        "hot_processor_limit",
        "cold_battery_floor",
        "hot_component_spread_limit",
    }
```

- [ ] **Step 2: Run the evaluation tests to verify they fail**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/evaluation/test_multicase_engine.py tests/evaluation/test_operating_cases.py tests/evaluation/test_io.py tests/evaluation/test_cli.py -v`
Expected: FAIL because the new spec and metric set do not exist yet.

- [ ] **Step 3: Add the missing metric keys**

Ensure `evaluation/metrics.py` can resolve:

- `component.rf_power_amp.temperature_max`
- `component.processor.temperature_max`
- `component.battery_pack.temperature_min`
- `components.max_temperature_spread`
- `case.total_radiator_span`

If the current component metric namespace is already `component.<component_id>.*`, add a deterministic mapping layer so the benchmark can resolve role-based IDs cleanly without leaking unstable generated IDs into specs.

- [ ] **Step 4: Define the new active evaluation spec**

Create:

```yaml
schema_version: "1.0"
spec_meta:
  spec_id: panel-four-component-hot-cold-baseline
operating_cases:
  - operating_case_id: hot
  - operating_case_id: cold
objectives:
  - objective_id: minimize_hot_pa_peak
    operating_case: hot
    metric: component.rf_power_amp.temperature_max
    sense: minimize
  - objective_id: maximize_cold_battery_min
    operating_case: cold
    metric: component.battery_pack.temperature_min
    sense: maximize
  - objective_id: minimize_radiator_resource
    operating_case: hot
    metric: case.total_radiator_span
    sense: minimize
constraints:
  - constraint_id: hot_pa_limit
    operating_case: hot
    metric: component.rf_power_amp.temperature_max
    relation: "<="
    limit: 355.0
```

Tune the exact numeric limits after solver trial runs, but keep the intended qualitative meaning unchanged.

- [ ] **Step 5: Keep multicase evaluation as the active CLI path**

Update examples and tests to use generated or runtime-produced `hot` and `cold` cases from the new template rather than checked-in manual reference cases.

- [ ] **Step 6: Run the full evaluation suite**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/evaluation -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
cd /home/hymn/msfenicsx
git add evaluation/metrics.py evaluation/validation.py evaluation/multicase_engine.py evaluation/io.py evaluation/cli.py scenarios/evaluation/panel_four_component_hot_cold_baseline.yaml tests/evaluation/test_multicase_engine.py tests/evaluation/test_operating_cases.py tests/evaluation/test_io.py tests/evaluation/test_cli.py
git commit -m "feat: replace evaluation baseline with four component hot cold benchmark"
```

## Task 4: Replace the Optimizer Entry Contract with a Reproducible Benchmark Source

**Files:**
- Modify: `optimizers/models.py`
- Modify: `optimizers/validation.py`
- Modify: `optimizers/io.py`
- Modify: `optimizers/cli.py`
- Modify: `tests/optimizers/test_optimizer_io.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`

- [ ] **Step 1: Write the failing optimizer spec tests**

Add a test that requires the optimizer to load from a benchmark template and seed:

```python
def test_optimization_spec_accepts_benchmark_source():
    spec = OptimizationSpec.from_dict(
        {
            "schema_version": "1.0",
            "spec_meta": {"spec_id": "panel-b0"},
            "benchmark_source": {
                "template_path": "scenarios/templates/panel_four_component_hot_cold_benchmark.yaml",
                "seed": 11,
            },
            "design_variables": [],
            "algorithm": {"name": "pymoo_nsga2", "population_size": 16, "num_generations": 8, "seed": 7},
            "evaluation_protocol": {"evaluation_spec_path": "scenarios/evaluation/panel_four_component_hot_cold_baseline.yaml"},
        }
    )
    assert spec.benchmark_source["seed"] == 11
```

- [ ] **Step 2: Run the optimizer I/O tests to verify they fail**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_optimizer_io.py tests/optimizers/test_optimizer_cli.py -v`
Expected: FAIL because `benchmark_source` is not yet part of the optimizer contract.

- [ ] **Step 3: Add `benchmark_source` to the optimizer contract**

Use this minimum shape:

```yaml
benchmark_source:
  template_path: scenarios/templates/panel_four_component_hot_cold_benchmark.yaml
  seed: 11
```

This replaces the old assumption that the active optimizer mainline starts from source-controlled manual `hot` and `cold` cases.

- [ ] **Step 4: Replace the active CLI entrypoint**

Change the active command to:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml \
  --output-root ./scenario_runs/optimizations/panel-four-component-b0
```

The CLI should generate the benchmark pair internally from `benchmark_source`.

- [ ] **Step 5: Run the optimizer I/O and CLI tests again**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_optimizer_io.py tests/optimizers/test_optimizer_cli.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd /home/hymn/msfenicsx
git add optimizers/models.py optimizers/validation.py optimizers/io.py optimizers/cli.py tests/optimizers/test_optimizer_io.py tests/optimizers/test_optimizer_cli.py
git commit -m "feat: load optimization baselines from benchmark generator sources"
```

## Task 5: Implement `B0` Vanilla `NSGA-II` for the New 8-Variable Benchmark

**Files:**
- Modify: `optimizers/codec.py`
- Create: `optimizers/repair.py`
- Create: `optimizers/problem.py`
- Modify: `optimizers/pymoo_driver.py`
- Modify: `optimizers/artifacts.py`
- Create: `scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml`
- Modify: `tests/optimizers/test_codec.py`
- Modify: `tests/optimizers/test_nsga2_driver.py`
- Modify: `tests/solver/test_generated_case.py`
- Modify: `tests/solver/test_reference_case.py`

- [ ] **Step 1: Write the failing optimization-driver tests**

Add tests that pin the new search space:

```python
def test_b0_driver_optimizes_three_components_and_radiator_interval():
    run = run_multicase_optimization(...)
    variable_ids = set(run.result.history[0]["decision_vector"])
    assert variable_ids == {
        "processor_x",
        "processor_y",
        "rf_power_amp_x",
        "rf_power_amp_y",
        "battery_pack_x",
        "battery_pack_y",
        "radiator_start",
        "radiator_end",
    }
```

```python
def test_b0_baseline_records_infeasible_starting_point():
    run = run_multicase_optimization(...)
    assert run.result.baseline_candidates[0]["feasible"] is False
```

- [ ] **Step 2: Run the driver and solver smoke tests to verify they fail**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_codec.py tests/optimizers/test_nsga2_driver.py tests/solver/test_generated_case.py tests/solver/test_reference_case.py -v`
Expected: FAIL because the new benchmark variables and infeasible baseline conditions are not yet wired up.

- [ ] **Step 3: Expand the decision vector and repair logic**

Use design variables like:

```yaml
design_variables:
  - variable_id: processor_x
    path: components[0].pose.x
  - variable_id: rf_power_amp_y
    path: components[1].pose.y
  - variable_id: radiator_start
    path: boundary_features[0].start
  - variable_id: radiator_end
    path: boundary_features[0].end
```

`optimizers/repair.py` must enforce:

- `radiator_start < radiator_end`
- all positions remain within legal placement bounds
- component overlap is resolved by projection or clipping before solve

- [ ] **Step 4: Implement the clean `B0` spec**

Create `scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml` with:

- `benchmark_source`
- `8` design variables
- `pymoo_nsga2`
- a real budget, for example `population_size >= 16` and `num_generations >= 8`

Tune final values after first real runs, but do not leave the toy budget of `4 x 1`.

- [ ] **Step 5: Update the driver and artifact exports**

Ensure the run writes:

- `optimization_result.json`
- `pareto_front.json`
- representative bundles
- the generated baseline `hot` and `cold` cases used to start the run

- [ ] **Step 6: Run the optimizer and solver tests again**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_codec.py tests/optimizers/test_nsga2_driver.py tests/solver/test_generated_case.py tests/solver/test_reference_case.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
cd /home/hymn/msfenicsx
git add optimizers/codec.py optimizers/repair.py optimizers/problem.py optimizers/pymoo_driver.py optimizers/artifacts.py scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml tests/optimizers/test_codec.py tests/optimizers/test_nsga2_driver.py tests/solver/test_generated_case.py tests/solver/test_reference_case.py
git commit -m "feat: add b0 nsga2 baseline for the paper grade benchmark"
```

## Task 6: Implement `B1` Hybrid-Operator `NSGA-II`

**Files:**
- Create: `optimizers/operators.py`
- Modify: `optimizers/pymoo_driver.py`
- Modify: `optimizers/models.py`
- Modify: `optimizers/validation.py`
- Modify: `optimizers/artifacts.py`
- Create: `scenarios/optimization/panel_four_component_hot_cold_hybrid_nsga2_b1.yaml`
- Modify: `tests/optimizers/test_nsga2_driver.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`

- [ ] **Step 1: Write the failing hybrid-operator tests**

Add tests that require domain-operator selection to be visible:

```python
def test_b1_run_records_operator_usage():
    run = run_multicase_optimization(...)
    history = run.result.history
    assert any("operator_id" in entry for entry in history if entry["source"] == "optimizer")
```

```python
def test_b1_spec_accepts_hybrid_operator_pool():
    spec = load_optimization_spec("scenarios/optimization/panel_four_component_hot_cold_hybrid_nsga2_b1.yaml")
    assert spec.algorithm["operator_mode"] == "hybrid"
```

- [ ] **Step 2: Run the hybrid tests to verify they fail**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_nsga2_driver.py tests/optimizers/test_optimizer_cli.py -v`
Expected: FAIL because the hybrid operator layer does not exist yet.

- [ ] **Step 3: Implement the required domain operators**

Create at least:

```python
OPERATORS = {
    "standard_sbx_pm": ...,
    "hotspot_pull": ...,
    "battery_relief": ...,
    "pair_separate": ...,
    "radiator_slide": ...,
    "radiator_expand_contract": ...,
    "repair_project": ...,
    "local_refine": ...,
}
```

Each operator should return a numeric vector, not a free-form case object.

- [ ] **Step 4: Extend the driver to support `B1` under matched budget**

`B1` must:

- use the same evaluation spec as `B0`
- use the same budget as `B0`
- log operator IDs in history
- keep Pareto output contracts unchanged

- [ ] **Step 5: Create the `B1` optimization spec**

Create `scenarios/optimization/panel_four_component_hot_cold_hybrid_nsga2_b1.yaml` with:

- the same `benchmark_source`
- the same variable bounds
- `algorithm.name: pymoo_nsga2`
- `algorithm.operator_mode: hybrid`
- explicit operator pool names

- [ ] **Step 6: Run the hybrid optimizer tests again**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_nsga2_driver.py tests/optimizers/test_optimizer_cli.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
cd /home/hymn/msfenicsx
git add optimizers/operators.py optimizers/pymoo_driver.py optimizers/models.py optimizers/validation.py optimizers/artifacts.py scenarios/optimization/panel_four_component_hot_cold_hybrid_nsga2_b1.yaml tests/optimizers/test_nsga2_driver.py tests/optimizers/test_optimizer_cli.py
git commit -m "feat: add hybrid operator nsga2 baseline"
```

## Task 7: Delete the Old Toy Baseline and Synchronize Active Docs

**Files:**
- Delete: `scenarios/templates/panel_radiation_baseline.yaml`
- Delete: `scenarios/manual/reference_case.yaml`
- Delete: `scenarios/manual/reference_case_hot.yaml`
- Delete: `scenarios/manual/reference_case_cold.yaml`
- Delete: `scenarios/evaluation/panel_hot_cold_multiobjective_baseline.yaml`
- Delete: `scenarios/optimization/reference_hot_cold_nsga2.yaml`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Create: `docs/reports/R64_msfenicsx_paper_grade_multiobjective_baseline_rollout_20260327.md`

- [ ] **Step 1: Write the failing cleanup checklist**

Record the truths that must hold after cleanup:

- no active docs point to the toy one-component benchmark
- no active scenario path uses `panel_radiation_baseline.yaml`
- no active CLI example starts from checked-in manual `hot` and `cold` case files

- [ ] **Step 2: Delete obsolete scenario assets**

Delete the old toy benchmark inputs after the new tests and new CLI examples are already passing.

- [ ] **Step 3: Rewrite the active docs**

`README.md` and `AGENTS.md` must describe:

- paired benchmark generation from template plus seed
- `B0` and `B1` as the active classical baseline ladder
- `optimize-benchmark` as the active optimizer entrypoint

- [ ] **Step 4: Write the rollout report**

`docs/reports/R64_msfenicsx_paper_grade_multiobjective_baseline_rollout_20260327.md` should capture:

- what was deleted
- what the new benchmark contains
- what remains intentionally deferred, especially LLM strategy work and ML tensor export

- [ ] **Step 5: Run a docs and path sanity check**

Run:

```bash
cd /home/hymn/msfenicsx
grep -R "panel_radiation_baseline.yaml" README.md AGENTS.md docs scenarios tests || true
grep -R "reference_case_hot.yaml\\|reference_case_cold.yaml" README.md AGENTS.md docs scenarios tests || true
```

Expected: no active references remain outside historical reports or the new plan/spec context.

- [ ] **Step 6: Commit**

```bash
cd /home/hymn/msfenicsx
git add README.md AGENTS.md docs/reports/R64_msfenicsx_paper_grade_multiobjective_baseline_rollout_20260327.md
git add -u scenarios
git commit -m "docs: cut over to the paper grade benchmark baseline"
```

## Task 8: Fresh Verification and End-to-End Evidence

**Files:**
- Modify: none
- Verify: repository state only

- [ ] **Step 1: Run the focused test suites**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/schema tests/generator tests/solver tests/evaluation tests/optimizers tests/cli/test_module_entrypoints.py tests/cli/test_cli_end_to_end.py -q
```

Expected: all targeted suites PASS.

- [ ] **Step 2: Run fresh paired-case generation**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main generate-operating-case-pair \
  --template scenarios/templates/panel_four_component_hot_cold_benchmark.yaml \
  --seed 11 \
  --output-root /tmp/msfenicsx_paper_grade_cases
```

Expected:

- `/tmp/msfenicsx_paper_grade_cases/*hot.yaml`
- `/tmp/msfenicsx_paper_grade_cases/*cold.yaml`

- [ ] **Step 3: Run fresh solves for both operating cases**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main solve-case \
  --case /tmp/msfenicsx_paper_grade_cases/<hot-case>.yaml \
  --output-root /tmp/msfenicsx_paper_grade_runs
```

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main solve-case \
  --case /tmp/msfenicsx_paper_grade_cases/<cold-case>.yaml \
  --output-root /tmp/msfenicsx_paper_grade_runs
```

Expected: both runs converge and emit `case.yaml`, `solution.yaml`, and `manifest.json`.

- [ ] **Step 4: Run fresh multicase evaluation**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m evaluation.cli evaluate-operating-cases \
  --case hot=/tmp/msfenicsx_paper_grade_cases/<hot-case>.yaml \
  --case cold=/tmp/msfenicsx_paper_grade_cases/<cold-case>.yaml \
  --solution hot=/tmp/msfenicsx_paper_grade_runs/<hot-bundle>/solution.yaml \
  --solution cold=/tmp/msfenicsx_paper_grade_runs/<cold-bundle>/solution.yaml \
  --spec scenarios/evaluation/panel_four_component_hot_cold_baseline.yaml \
  --output /tmp/msfenicsx_paper_grade_evaluation.yaml
```

Expected:

- report writes successfully
- baseline is infeasible
- at least two constraint violations appear

- [ ] **Step 5: Run fresh `B0` optimization**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml \
  --output-root /tmp/msfenicsx_paper_grade_b0
```

Expected:

- `optimization_result.json`
- `pareto_front.json`
- representative bundles
- objective values vary across history

- [ ] **Step 6: Run fresh `B1` optimization**

Run:

```bash
cd /home/hymn/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/panel_four_component_hot_cold_hybrid_nsga2_b1.yaml \
  --output-root /tmp/msfenicsx_paper_grade_b1
```

Expected:

- same artifact family as `B0`
- operator telemetry recorded
- feasible-rate or first-feasible behavior is comparable to or better than `B0`

- [ ] **Step 7: Record the evidence in the rollout report**

Summarize:

- benchmark seed
- constraint violations at baseline
- `B0` aggregate metrics
- `B1` aggregate metrics
- any tuning needed if the benchmark is still too easy or infeasible everywhere

- [ ] **Step 8: Final commit**

```bash
cd /home/hymn/msfenicsx
git add docs/reports/R64_msfenicsx_paper_grade_multiobjective_baseline_rollout_20260327.md
git commit -m "test: verify the paper grade benchmark end to end"
```
