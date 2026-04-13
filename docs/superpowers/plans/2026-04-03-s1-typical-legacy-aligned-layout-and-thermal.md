# S1 Typical Legacy-Aligned Layout And Thermal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retrofit the active `s1_typical` mainline so generated cases are denser and thermally less flat by adding zone-driven compact layout generation, moderate conductivity retuning, and localized heat-source support, while preserving the single-case `15`-component `x/y`-only paper-facing benchmark contract.

**Architecture:** Keep the current mixed-shape `s1_typical` stack and extend it instead of replacing it. Encode dense-core deck zones and load-localization hints in the template, teach the generator to pack by zone and occupancy targets, carry layout metrics into case provenance, interpret localized source regions in the solver, then revalidate repair and page/report outputs against the denser benchmark.

**Tech Stack:** Python 3.12, pytest, PyYAML, NumPy, Shapely, FEniCSx (`dolfinx`, `ufl`, `mpi4py`, `petsc4py`), existing repository YAML/JSON artifact pipeline

---

Spec reference:

- `docs/superpowers/specs/2026-04-03-s1-typical-legacy-aligned-layout-and-thermal-design.md`

Primary guardrails:

- Keep `s1_typical` as the only active paper-facing benchmark.
- Keep one operating case, fifteen named components, and `32` decision variables.
- Do not add optimized rotation, geometry, material, or power variables.
- Keep one top-edge sink as the official paper-facing sink model.
- Do not revive `radiation_gen` as a new runtime architecture or dataset workflow.
- Keep cheap legality checks before PDE solves and keep repair benchmark-agnostic.

## File Structure

### Template And Schema Surface

- Modify: `scenarios/templates/s1_typical.yaml`
- Modify: `core/schema/validation.py`
- Modify: `tests/schema/test_s1_typical_template.py`
- Modify: `tests/schema/test_schema_validation.py`

### Generator Densification

- Modify: `core/generator/layout_engine.py`
- Modify: `core/generator/layout_metrics.py`
- Modify: `core/generator/parameter_sampler.py`
- Modify: `tests/generator/test_layout_engine.py`
- Modify: `tests/generator/test_layout_metrics.py`

### Thermal Realism V1

- Modify: `core/generator/case_builder.py`
- Modify: `core/solver/case_to_geometry.py`
- Modify: `core/solver/physics_builder.py`
- Modify: `tests/solver/test_generated_case.py`
- Create: `tests/solver/test_case_to_geometry.py`

### Provenance, Reporting, And Repair Revalidation

- Modify: `evaluation/metrics.py`
- Modify: `visualization/case_pages.py`
- Modify: `optimizers/repair.py`
- Modify: `tests/evaluation/test_engine.py`
- Modify: `tests/visualization/test_case_pages.py`
- Modify: `tests/optimizers/test_repair.py`

### Calibration Evidence

- Create: `docs/reports/R71_msfenicsx_s1_typical_legacy_aligned_realism_validation_20260403.md`

## Task 1: Add Template Semantics For Dense-Core Generation And Localized Loads

**Files:**
- Modify: `scenarios/templates/s1_typical.yaml`
- Modify: `core/schema/validation.py`
- Modify: `tests/schema/test_s1_typical_template.py`
- Modify: `tests/schema/test_schema_validation.py`

- [ ] **Step 1: Write the failing template and schema tests**

Add coverage that requires the active template to declare:

- generation-only layout zones under `generation_rules`
- a default sink span that does not exceed the `0.48` budget
- optional per-load `source_area_ratio`

Example assertions:

```python
def test_s1_typical_template_declares_legacy_aligned_layout_strategy() -> None:
    payload = yaml.safe_load(Path("scenarios/templates/s1_typical.yaml").read_text(encoding="utf-8"))

    strategy = payload["generation_rules"]["layout_strategy"]
    assert strategy["kind"] == "legacy_aligned_dense_core_v1"
    assert {"dense_core", "top_sink_band", "left_io_edge", "right_service_edge"} <= set(strategy["zones"])
```

```python
def test_validate_scenario_template_accepts_optional_source_area_ratio() -> None:
    payload = _base_template_payload()
    payload["load_rules"] = [{"target_family": "c01", "total_power": 12.0, "source_area_ratio": 0.25}]

    validate_scenario_template_payload(payload)
```

- [ ] **Step 2: Run the focused schema tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/schema/test_s1_typical_template.py \
  tests/schema/test_schema_validation.py -v
```

Expected:

- FAIL because the current template does not define the new zone payload or load-localization semantics

- [ ] **Step 3: Update the template and validation**

Implement the minimal contract changes needed for the new design:

- add `generation_rules.layout_strategy.kind = legacy_aligned_dense_core_v1`
- add the four named deck zones
- retune template conductivities toward the `5/20` target
- narrow the default top sink span so the generated baseline does not exceed the `0.48` sink budget
- add optional load-rule `source_area_ratio`
- validate optional `source_area_ratio` and zone payload shapes explicitly in `core/schema/validation.py`

- [ ] **Step 4: Re-run the focused schema tests**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  scenarios/templates/s1_typical.yaml \
  core/schema/validation.py \
  tests/schema/test_s1_typical_template.py \
  tests/schema/test_schema_validation.py
git commit -m "feat: add legacy-aligned s1_typical template semantics"
```

## Task 2: Replace Broad-Band Placement With Zone-Driven Dense Packing

**Files:**
- Modify: `core/generator/layout_engine.py`
- Modify: `core/generator/layout_metrics.py`
- Modify: `core/generator/parameter_sampler.py`
- Modify: `tests/generator/test_layout_engine.py`
- Modify: `tests/generator/test_layout_metrics.py`

- [ ] **Step 1: Write the failing generator behavior tests**

Add tests that describe the desired layout behavior without pinning exact coordinates.

Required coverage:

- anchor families land in their named edge or sink zones
- dense-core occupancy exceeds the current loose-layout regime
- five calibration seeds generate legally with no dropped components

Example assertions:

```python
def test_measure_layout_quality_reports_active_deck_occupancy() -> None:
    case = generate_case("scenarios/templates/s1_typical.yaml", seed=11).to_dict()
    metrics = measure_layout_quality(case, placement_region=MAIN_DECK, active_deck=ACTIVE_DECK)

    assert metrics.active_deck_occupancy >= 0.38
    assert metrics.bbox_fill_ratio >= 0.38
```

```python
def test_place_components_generates_all_components_for_calibration_seed_sample() -> None:
    template = load_template_model("scenarios/templates/s1_typical.yaml")
    for seed in (11, 17, 23, 29, 31):
        sampled = sample_template_parameters(template, seed=seed)
        placed = place_components(template=template, sampled_components=sampled["components"], seed=seed)
        assert len(placed) == 15
```

- [ ] **Step 2: Run the focused generator tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/generator/test_layout_engine.py \
  tests/generator/test_layout_metrics.py -v
```

Expected:

- FAIL because the current engine still uses broad semantic bands and does not target the new occupancy floor

- [ ] **Step 3: Implement zone-driven placement and stronger layout metrics**

Refactor the generator so it:

- reads the named zone payload from `generation_rules`
- orders placement by anchors, dense-core large parts, then fillers
- packs dense-core families by area and thermal importance
- computes `active_deck_occupancy` in `core/generator/layout_metrics.py`
- retains a fallback to the current legal sampler when semantic placement fails

Keep the legality checks grounded in the existing polygon overlap and keep-out rules.

- [ ] **Step 4: Re-run the focused generator tests**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  core/generator/layout_engine.py \
  core/generator/layout_metrics.py \
  core/generator/parameter_sampler.py \
  tests/generator/test_layout_engine.py \
  tests/generator/test_layout_metrics.py
git commit -m "feat: densify s1_typical layout generation"
```

## Task 3: Add Localized Heat-Source Support And Thermal Realism V1

**Files:**
- Modify: `core/generator/case_builder.py`
- Modify: `core/solver/case_to_geometry.py`
- Modify: `core/solver/physics_builder.py`
- Modify: `tests/solver/test_generated_case.py`
- Create: `tests/solver/test_case_to_geometry.py`

- [ ] **Step 1: Write the failing solver-facing tests**

Add tests that require:

- generated loads can carry `source_area_ratio`
- `interpret_case()` produces a smaller effective source region when a load ratio is present
- generated `s1_typical` cases still solve end-to-end after the new source-localization logic is introduced

Example assertions:

```python
def test_interpret_case_builds_localized_source_region_from_load_ratio() -> None:
    payload = _case_with_source_ratio(0.25)
    interpreted = interpret_case(payload)
    component = interpreted["components"][0]

    assert component["source_area"] < component["area"]
    assert component["source_area"] == pytest.approx(component["area"] * 0.25, rel=0.15)
```

- [ ] **Step 2: Run the focused solver tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/solver/test_case_to_geometry.py \
  tests/solver/test_generated_case.py -v
```

Expected:

- FAIL because the current case interpretation and source interpolation always use the full component footprint

- [ ] **Step 3: Implement localized source support**

Make the minimal coordinated changes:

- propagate optional `source_area_ratio` from template sampling into generated case loads
- derive a centroid-scaled effective source polygon in `core/solver/case_to_geometry.py`
- use that effective source polygon and source area in `core/solver/physics_builder.py`
- keep total power unchanged

Do not change the official PDE class or introduce a second sink feature.

- [ ] **Step 4: Re-run the focused solver tests**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  core/generator/case_builder.py \
  core/solver/case_to_geometry.py \
  core/solver/physics_builder.py \
  tests/solver/test_generated_case.py \
  tests/solver/test_case_to_geometry.py
git commit -m "feat: localize s1_typical heat sources"
```

## Task 4: Surface Layout Metrics In Artifacts And Revalidate Repair

**Files:**
- Modify: `evaluation/metrics.py`
- Modify: `visualization/case_pages.py`
- Modify: `optimizers/repair.py`
- Modify: `tests/evaluation/test_engine.py`
- Modify: `tests/visualization/test_case_pages.py`
- Modify: `tests/optimizers/test_repair.py`

- [ ] **Step 1: Write the failing reporting and repair tests**

Add coverage that requires:

- generated-case layout metrics are visible in evaluation derived signals
- representative case pages show the new occupancy and gap diagnostics
- repair still restores legality for a deliberately over-dense seed vector under the updated template

Example assertions:

```python
def test_evaluate_case_solution_surfaces_layout_realism_signals() -> None:
    report = evaluate_case_solution(_case_with_layout_metrics(), _solution(), _spec())

    assert report.derived_signals["layout_active_deck_occupancy"] >= 0.38
    assert "layout_bbox_fill_ratio" in report.derived_signals
```

- [ ] **Step 2: Run the focused artifact and repair tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/evaluation/test_engine.py \
  tests/visualization/test_case_pages.py \
  tests/optimizers/test_repair.py -v
```

Expected:

- FAIL because the current evaluation and page layers do not surface the new layout signals

- [ ] **Step 3: Implement provenance surfacing and repair tuning**

Make the smallest necessary changes:

- persist layout metrics into generated-case provenance during case construction
- copy those metrics into evaluation derived signals
- add them to the representative page layout / metrics sections
- retune repair only if the denser template exposes overlap-restoration regressions

Do not add benchmark-specific hard layout rules to repair.

- [ ] **Step 4: Re-run the focused artifact and repair tests**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  evaluation/metrics.py \
  visualization/case_pages.py \
  optimizers/repair.py \
  tests/evaluation/test_engine.py \
  tests/visualization/test_case_pages.py \
  tests/optimizers/test_repair.py
git commit -m "feat: report layout realism signals and revalidate repair"
```

## Task 5: Run Calibration Smokes And Capture Evidence

**Files:**
- Create: `docs/reports/R71_msfenicsx_s1_typical_legacy_aligned_realism_validation_20260403.md`

- [ ] **Step 1: Run the focused regression suite for touched modules**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/schema/test_s1_typical_template.py \
  tests/schema/test_schema_validation.py \
  tests/generator/test_layout_engine.py \
  tests/generator/test_layout_metrics.py \
  tests/solver/test_case_to_geometry.py \
  tests/solver/test_generated_case.py \
  tests/evaluation/test_engine.py \
  tests/visualization/test_case_pages.py \
  tests/optimizers/test_repair.py -v
```

Expected:

- PASS

- [ ] **Step 2: Run five real calibration seeds through the canonical chain**

For each seed in `11 17 23 29 31`, first define a zero-padded seed variable:

```bash
seed4=$(printf "%04d" <seed>)
```

Then run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main generate-case \
  --template scenarios/templates/s1_typical.yaml \
  --seed <seed> \
  --output-root ./scenario_runs/real_checks/20260403_legacy_aligned_layout_and_thermal/generated_cases
```

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main solve-case \
  --case ./scenario_runs/real_checks/20260403_legacy_aligned_layout_and_thermal/generated_cases/s1_typical-seed-${seed4}.yaml \
  --output-root ./scenario_runs/real_checks/20260403_legacy_aligned_layout_and_thermal
```

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m evaluation.cli evaluate-case \
  --case ./scenario_runs/real_checks/20260403_legacy_aligned_layout_and_thermal/s1_typical/s1_typical-seed-${seed4}/case.yaml \
  --solution ./scenario_runs/real_checks/20260403_legacy_aligned_layout_and_thermal/s1_typical/s1_typical-seed-${seed4}/solution.yaml \
  --spec scenarios/evaluation/s1_typical_eval.yaml \
  --output ./scenario_runs/real_checks/20260403_legacy_aligned_layout_and_thermal/s1_typical/s1_typical-seed-${seed4}/evaluation_report.yaml \
  --bundle-root ./scenario_runs/real_checks/20260403_legacy_aligned_layout_and_thermal/s1_typical/s1_typical-seed-${seed4}
```

- [ ] **Step 3: Render a representative page bundle for visual inspection**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -c "from visualization.case_pages import render_case_page; render_case_page('./scenario_runs/real_checks/20260403_legacy_aligned_layout_and_thermal/s1_typical/s1_typical-seed-0011')"
```

Expected:

- the layout is visibly denser than the current `20260403_layout_realism_seed11` baseline
- the temperature field is no longer limited to a `~2 K` span

- [ ] **Step 4: Write the calibration report**

Create `docs/reports/R71_msfenicsx_s1_typical_legacy_aligned_realism_validation_20260403.md` with:

- the exact template path and seed list
- occupancy metrics per seed
- thermal span per seed
- representative artifact paths
- a short conclusion on whether the `0.38~0.45` occupancy and `8~20 K` span targets were met

- [ ] **Step 5: Commit**

```bash
git add docs/reports/R71_msfenicsx_s1_typical_legacy_aligned_realism_validation_20260403.md
git commit -m "docs: record legacy-aligned s1_typical realism validation"
```
