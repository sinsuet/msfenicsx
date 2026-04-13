# S1 Typical Realism V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tighten `s1_typical` layout realism and raise thermal contrast without adding optimizer-specific spatial policy, while correcting gradient diagnostics and representative bundle layout metrics.

**Architecture:** Keep the active `s1_typical` benchmark and optimizer contracts unchanged. Improve realism only through template calibration, generator legality/compactness, FE-based gradient export, and truthful representative-bundle diagnostics.

**Tech Stack:** Python 3.12, pytest, PyYAML, NumPy, Shapely, FEniCSx (`dolfinx`, `ufl`, `mpi4py`, `petsc4py`)

---

Spec reference:

- `docs/superpowers/specs/2026-04-07-s1-typical-realism-v2-design.md`

### Task 1: Add Failing Tests For Clearance, Compactness, Gradient Export, And Representative Metrics

**Files:**
- Modify: `tests/generator/test_layout_engine.py`
- Modify: `tests/generator/test_layout_metrics.py`
- Modify: `tests/solver/test_field_export.py`
- Modify: `tests/visualization/test_case_pages.py`

- [ ] **Step 1: Write a failing generator test for clearance-aware legality**

Add a focused test showing two components that do not overlap geometrically but do violate required buffered clearance.

- [ ] **Step 2: Write a failing compactness test for dense-core empty-void diagnostics**

Add a layout-metrics or layout-penalty-facing test that distinguishes a clustered layout from a layout with a large dense-core void.

- [ ] **Step 3: Write a failing solver export test for FE-based gradient sampling**

Add a test that verifies gradient export is derived from a true gradient field path rather than only raster differencing.

- [ ] **Step 4: Write a failing representative-page test for recomputed layout metrics**

Add a test showing representative page metrics must reflect the representative `case.yaml`, not stale provenance.

- [ ] **Step 5: Run the focused tests and confirm failure**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/generator/test_layout_engine.py \
  tests/generator/test_layout_metrics.py \
  tests/solver/test_field_export.py \
  tests/visualization/test_case_pages.py -v
```

### Task 2: Implement Clearance-Aware Layout Legality And Stronger Compactness Scoring

**Files:**
- Modify: `core/generator/layout_engine.py`
- Modify: `core/generator/layout_metrics.py`
- Modify: `tests/generator/test_layout_engine.py`
- Modify: `tests/generator/test_layout_metrics.py`

- [ ] **Step 1: Implement clearance-aware overlap testing in generation/refinement**

Use family-level `clearance` to buffer polygons when checking generation-time legality.

- [ ] **Step 2: Add dense-core large-empty-patch penalty**

Implement a generic void diagnostic/penalty based on coarse occupancy over the dense-core zone.

- [ ] **Step 3: Keep penalty generic**

Do not add family-aware optimizer windows, optimizer policy, or benchmark-specific repair hooks.

- [ ] **Step 4: Re-run generator tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/generator/test_layout_engine.py \
  tests/generator/test_layout_metrics.py -v
```

### Task 3: Retune Template Geometry And Thermal Parameters

**Files:**
- Modify: `scenarios/templates/s1_typical.yaml`
- Modify: `tests/schema/test_s1_typical_template.py`
- Modify: `tests/solver/test_generated_case.py`

- [ ] **Step 1: Write/update failing template expectations**

Cover:

- narrower generation zones
- adjusted conductivity targets
- tighter high-power `source_area_ratio`
- moderate geometry enlargement where needed

- [ ] **Step 2: Run focused schema/solver tests and confirm failure**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/schema/test_s1_typical_template.py \
  tests/solver/test_generated_case.py -v
```

- [ ] **Step 3: Update template parameters minimally**

Retune only the hand-authored template values needed for this phase.

- [ ] **Step 4: Re-run focused schema/solver tests**

Run the same command and confirm pass.

### Task 4: Export Gradient Diagnostics From FE Gradient And Recompute Representative Layout Metrics

**Files:**
- Modify: `core/solver/field_export.py`
- Modify: `core/solver/field_sampler.py`
- Modify: `visualization/case_pages.py`
- Modify: `tests/solver/test_field_export.py`
- Modify: `tests/visualization/test_case_pages.py`

- [ ] **Step 1: Implement FE-gradient-based sampling**

Sample gradient magnitude from the FE solution path rather than reconstructing from rasterized temperature.

- [ ] **Step 2: Recompute representative layout metrics from actual case geometry**

Ensure representative pages and related diagnostics use metrics recomputed from the representative case bundle.

- [ ] **Step 3: Re-run focused solver/visualization tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/solver/test_field_export.py \
  tests/visualization/test_case_pages.py -v
```

### Task 5: Full Focused Verification And Real Reruns

**Files:**
- Modify as needed from prior tasks only

- [ ] **Step 1: Run the maintained focused regression set**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/schema/test_s1_typical_template.py \
  tests/generator/test_layout_engine.py \
  tests/generator/test_layout_metrics.py \
  tests/solver/test_field_export.py \
  tests/solver/test_generated_case.py \
  tests/visualization/test_case_pages.py \
  tests/optimizers/test_optimizer_cli.py \
  tests/optimizers/test_repair.py -v
```

- [ ] **Step 2: Run real `raw` and `union` optimizations**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s1_typical_raw.yaml --output-root /home/hymn/msfenicsx/scenario_runs/real_checks/20260407_realism_v2/raw
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s1_typical_union.yaml --output-root /home/hymn/msfenicsx/scenario_runs/real_checks/20260407_realism_v2/union
```

- [ ] **Step 3: Render representative pages if needed and inspect metrics**

Confirm:

- gradient figures exist
- layout metrics are recomputed
- representative figures are viewable

- [ ] **Step 4: Summarize observed layout density and thermal span**

Report baseline and representative signals with artifact paths.
