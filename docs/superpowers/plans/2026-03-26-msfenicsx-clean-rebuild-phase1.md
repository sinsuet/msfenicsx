# Msfenicsx Phase 1 Clean Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild `msfenicsx` Phase 1 into a clean platform with canonical schema objects, a scenario-driven dataset generator, an official FEniCSx nonlinear-radiation solver baseline, and a stable `scenario_runs/` artifact protocol.

**Architecture:** The new platform is built around three canonical objects: `scenario_template`, `thermal_case`, and `thermal_solution`. The new `core/` kernel owns schema, geometry, generator, solver, I/O, contracts, and CLI orchestration; future `evaluation/`, `optimizers/`, `llm/`, and `visualization/` remain separate top-level modules. Legacy demo code is not preserved as architecture and is deleted only after the new Phase 1 baseline is verified end-to-end.

**Tech Stack:** Python 3.12, PyYAML, NumPy, Shapely, FEniCSx (`dolfinx`, `ufl`, `mpi4py`, `petsc4py`), pytest

---

## File Structure

### New Runtime Kernel

- Create: `pyproject.toml`
  Defines package metadata, dependencies, and CLI entrypoints for the rebuilt platform.
- Create: `core/__init__.py`
- Create: `core/schema/__init__.py`
- Create: `core/schema/models.py`
  Canonical object definitions for `scenario_template`, `thermal_case`, and `thermal_solution`.
- Create: `core/schema/io.py`
  Load/save helpers for YAML and JSON canonical objects.
- Create: `core/schema/validation.py`
  Schema validation and shape-specific field checks.
- Create: `core/geometry/__init__.py`
- Create: `core/geometry/primitives.py`
  Primitive geometry constructors for `rect`, `circle`, `capsule`, constrained `polygon`, and `slot`.
- Create: `core/geometry/transforms.py`
  Pose application, local-to-world transforms, rotation helpers.
- Create: `core/geometry/layout_rules.py`
  Domain containment, overlap checks, keep-out checks, and boundary-feature placement rules.
- Create: `core/generator/__init__.py`
- Create: `core/generator/template_loader.py`
- Create: `core/generator/parameter_sampler.py`
- Create: `core/generator/layout_engine.py`
  Rewritten placement engine based on legacy `SeqLS` ideas, but outputting canonical `thermal_case` geometry only.
- Create: `core/generator/feature_synthesizer.py`
  `line_sink` synthesis and future non-component thermal features.
- Create: `core/generator/case_builder.py`
- Create: `core/generator/pipeline.py`
  Scenario-template to thermal-case orchestration.
- Create: `core/solver/__init__.py`
- Create: `core/solver/case_to_geometry.py`
  Converts canonical case objects into solver-ready domain and feature descriptions.
- Create: `core/solver/mesh_builder.py`
  Official FEniCSx mesh construction for the new schema.
- Create: `core/solver/physics_builder.py`
  Variational forms for steady conduction with nonlinear radiation boundaries.
- Create: `core/solver/nonlinear_solver.py`
  PETSc/SNES configuration and solve orchestration.
- Create: `core/solver/field_sampler.py`
  Sampling solved fields into structured arrays for artifact export.
- Create: `core/solver/solution_builder.py`
  Builds canonical `thermal_solution` objects.
- Create: `core/io/__init__.py`
- Create: `core/io/scenario_runs.py`
  Writes `scenario_runs/<scenario_id>/<case_id>/...` artifact bundles.
- Create: `core/contracts/__init__.py`
- Create: `core/contracts/case_contracts.py`
  Runtime legality checks between generator output and solver input.
- Create: `core/cli/__init__.py`
- Create: `core/cli/main.py`
  Commands for schema validation, scenario generation, and case solving.

### Top-Level Platform Modules

- Create: `evaluation/__init__.py`
  Minimal placeholder package to reserve the approved top-level boundary.
- Create: `optimizers/__init__.py`
  Minimal placeholder package for future `pymoo` work.
- Create: `llm/__init__.py`
  Minimal placeholder package for future strategy-layer work.
- Create: `visualization/__init__.py`
  Minimal placeholder package for future case and solution visualization.
- Create: `scenarios/templates/`
  Hand-authored scenario-template library.
- Create: `scenarios/manual/`
  Hand-authored deterministic cases for reference and verification.

### Tests

- Create: `tests/schema/test_schema_models.py`
- Create: `tests/schema/test_schema_io.py`
- Create: `tests/schema/test_schema_validation.py`
- Create: `tests/geometry/test_primitives.py`
- Create: `tests/geometry/test_layout_rules.py`
- Create: `tests/generator/test_parameter_sampler.py`
- Create: `tests/generator/test_layout_engine.py`
- Create: `tests/generator/test_pipeline.py`
- Create: `tests/solver/test_reference_case.py`
- Create: `tests/solver/test_generated_case.py`
- Create: `tests/io/test_scenario_runs.py`
- Create: `tests/cli/test_cli_smoke.py`

### Repository Hygiene

- Modify: `/home/hymn/msfenicsx/.gitignore`
  Add ignores for `scenario_runs/`, temporary generated fields, and local rebuild outputs.
- Modify: `/home/hymn/msfenicsx/README.md`
  Replace demo-oriented instructions with Phase 1 rebuilt platform guidance.
- Modify: `/home/hymn/msfenicsx/docs/superpowers/specs/2026-03-26-msfenicsx-clean-rebuild-design.md`
  Only if implementation planning uncovers a genuine spec contradiction that must be reflected back into the design.

### Legacy Removal Targets

- Delete later: `src/`
- Delete later: `radiation_gen/`
- Delete later: `examples/`
- Delete later: `states/`
- Delete later: legacy demo-specific tests after new coverage is in place

Do not delete legacy directories until Tasks 1 through 6 are passing and verified.

## Task 1: Establish the New Repository Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `core/__init__.py`
- Create: `core/cli/__init__.py`
- Create: `core/cli/main.py`
- Create: `evaluation/__init__.py`
- Create: `optimizers/__init__.py`
- Create: `llm/__init__.py`
- Create: `visualization/__init__.py`
- Modify: `/home/hymn/msfenicsx/.gitignore`
- Modify: `/home/hymn/msfenicsx/README.md`
- Test: `tests/cli/test_cli_smoke.py`

- [ ] **Step 1: Write the failing CLI smoke test**

```python
from core.cli.main import build_parser


def test_build_parser_exposes_generate_and_solve_commands():
    parser = build_parser()
    actions = [action.dest for action in parser._actions]
    assert "command" in actions
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /home/hymn/msfenicsx && pytest tests/cli/test_cli_smoke.py -v`
Expected: FAIL with `ModuleNotFoundError` or missing `build_parser`

- [ ] **Step 3: Create the package skeleton and minimal parser**

```python
import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="msfenicsx")
    parser.add_argument("command", nargs="?")
    return parser
```

- [ ] **Step 4: Add project packaging and top-level module placeholders**

Create a minimal `pyproject.toml` with:

- project name `msfenicsx`
- Python requirement matching the active environment
- dependencies for YAML, NumPy, Shapely, and FEniCSx-adjacent runtime packages
- console script entrypoint pointing at `core.cli.main:main`

- [ ] **Step 5: Update `.gitignore` and `README.md` for the new top-level layout**

Add:

```gitignore
scenario_runs/
```

and replace README directions so they describe the clean rebuild, not the legacy demo stack.

- [ ] **Step 6: Run the test to verify the parser smoke test passes**

Run: `cd /home/hymn/msfenicsx && pytest tests/cli/test_cli_smoke.py -v`
Expected: PASS

- [ ] **Step 7: Commit the skeleton**

```bash
cd /home/hymn/msfenicsx
git add pyproject.toml core evaluation optimizers llm visualization .gitignore README.md tests/cli/test_cli_smoke.py
git commit -m "chore: establish clean rebuild skeleton"
```

## Task 2: Implement Canonical Schema Objects and I/O

**Files:**
- Create: `core/schema/__init__.py`
- Create: `core/schema/models.py`
- Create: `core/schema/io.py`
- Create: `core/schema/validation.py`
- Create: `scenarios/templates/panel_radiation_baseline.yaml`
- Create: `scenarios/manual/reference_case.yaml`
- Test: `tests/schema/test_schema_models.py`
- Test: `tests/schema/test_schema_io.py`
- Test: `tests/schema/test_schema_validation.py`

- [ ] **Step 1: Write failing schema-model tests**

```python
from core.schema.models import ThermalCase


def test_thermal_case_requires_case_meta_and_components():
    payload = {
        "schema_version": "1.0",
        "case_meta": {"case_id": "case-001"},
        "coordinate_system": {"plane": "panel_xy"},
        "panel_domain": {"width": 1.0, "height": 1.0},
        "materials": {},
        "components": [],
        "boundary_features": [],
        "loads": [],
        "physics": {"kind": "steady_heat_radiation"},
        "mesh_profile": {"nx": 32, "ny": 32},
        "solver_profile": {"nonlinear_solver": "snes"},
        "provenance": {},
    }
    case = ThermalCase.from_dict(payload)
    assert case.case_meta["case_id"] == "case-001"
```

- [ ] **Step 2: Run schema tests to verify they fail**

Run: `cd /home/hymn/msfenicsx && pytest tests/schema/test_schema_models.py tests/schema/test_schema_io.py tests/schema/test_schema_validation.py -v`
Expected: FAIL because schema modules do not exist

- [ ] **Step 3: Implement canonical schema models**

Implement explicit constructors for:

- `ScenarioTemplate`
- `ThermalCase`
- `ThermalSolution`

Each must support:

- `from_dict`
- `to_dict`
- stable field names matching the approved spec

- [ ] **Step 4: Implement YAML/JSON load-save helpers**

Add helpers that can:

- load template, case, and solution files from YAML
- save them back deterministically
- preserve field order in the canonical writer where practical

- [ ] **Step 5: Implement validation for primitive shapes and `line_sink`**

Validation must reject:

- missing required blocks
- unsupported shape names
- invalid polygon vertex lists
- invalid slot dimensions
- invalid line-sink support definitions

- [ ] **Step 6: Add one hand-authored template and one hand-authored manual reference case**

These files become the seed fixtures for the rest of Phase 1.

- [ ] **Step 7: Run schema tests again**

Run: `cd /home/hymn/msfenicsx && pytest tests/schema/test_schema_models.py tests/schema/test_schema_io.py tests/schema/test_schema_validation.py -v`
Expected: PASS

- [ ] **Step 8: Commit the schema layer**

```bash
cd /home/hymn/msfenicsx
git add core/schema scenarios/templates/panel_radiation_baseline.yaml scenarios/manual/reference_case.yaml tests/schema
git commit -m "feat: add canonical schema objects and validation"
```

## Task 3: Build Geometry Primitives and Case Contracts

**Files:**
- Create: `core/geometry/__init__.py`
- Create: `core/geometry/primitives.py`
- Create: `core/geometry/transforms.py`
- Create: `core/geometry/layout_rules.py`
- Create: `core/contracts/__init__.py`
- Create: `core/contracts/case_contracts.py`
- Test: `tests/geometry/test_primitives.py`
- Test: `tests/geometry/test_layout_rules.py`

- [ ] **Step 1: Write failing geometry tests**

```python
from core.geometry.primitives import rectangle_polygon


def test_rectangle_polygon_returns_four_vertices():
    vertices = rectangle_polygon(width=0.4, height=0.2)
    assert len(vertices) == 4
```

- [ ] **Step 2: Run geometry tests to verify they fail**

Run: `cd /home/hymn/msfenicsx && pytest tests/geometry/test_primitives.py tests/geometry/test_layout_rules.py -v`
Expected: FAIL because geometry modules do not exist

- [ ] **Step 3: Implement primitive constructors and pose transforms**

Implement helpers for:

- rectangle
- circle surrogate representation
- capsule surrogate representation
- constrained polygon
- slot

Also implement world transforms from local geometry plus pose.

- [ ] **Step 4: Implement layout rules**

Rules must check:

- component-inside-domain
- component overlap
- keep-out exclusion
- valid `line_sink` edge segments

- [ ] **Step 5: Implement case-level contracts**

Create reusable checks that the generator and solver can both call before processing a case.

- [ ] **Step 6: Run geometry and contract tests**

Run: `cd /home/hymn/msfenicsx && pytest tests/geometry/test_primitives.py tests/geometry/test_layout_rules.py -v`
Expected: PASS

- [ ] **Step 7: Commit the geometry layer**

```bash
cd /home/hymn/msfenicsx
git add core/geometry core/contracts tests/geometry
git commit -m "feat: add geometry primitives and case contracts"
```

## Task 4: Rebuild the Scenario Generator

**Files:**
- Create: `core/generator/__init__.py`
- Create: `core/generator/template_loader.py`
- Create: `core/generator/parameter_sampler.py`
- Create: `core/generator/layout_engine.py`
- Create: `core/generator/feature_synthesizer.py`
- Create: `core/generator/case_builder.py`
- Create: `core/generator/pipeline.py`
- Test: `tests/generator/test_parameter_sampler.py`
- Test: `tests/generator/test_layout_engine.py`
- Test: `tests/generator/test_pipeline.py`

- [ ] **Step 1: Write failing generator tests**

```python
from core.generator.pipeline import generate_case


def test_generate_case_is_deterministic_for_fixed_seed():
    case_a = generate_case("/home/hymn/msfenicsx/scenarios/templates/panel_radiation_baseline.yaml", seed=7)
    case_b = generate_case("/home/hymn/msfenicsx/scenarios/templates/panel_radiation_baseline.yaml", seed=7)
    assert case_a.to_dict() == case_b.to_dict()
```

- [ ] **Step 2: Run generator tests to verify they fail**

Run: `cd /home/hymn/msfenicsx && pytest tests/generator/test_parameter_sampler.py tests/generator/test_layout_engine.py tests/generator/test_pipeline.py -v`
Expected: FAIL because generator modules do not exist

- [ ] **Step 3: Implement template loading and parameter sampling**

The parameter sampler should:

- read scenario distributions from `scenario_template`
- sample deterministic values under a fixed seed
- keep all outputs in SI units

- [ ] **Step 4: Rebuild the placement engine using legacy ideas but new contracts**

Do not port the old `SeqLS.py` file directly.

Implement a new layout engine that:

- places components inside `panel_domain`
- rejects overlap
- respects keep-out zones
- emits geometry only

- [ ] **Step 5: Implement `line_sink` synthesis**

Boundary features should be generated separately from occupied components and attached under `boundary_features`.

- [ ] **Step 6: Build final `thermal_case` assembly**

The pipeline should output only validated canonical cases.

- [ ] **Step 7: Run generator tests**

Run: `cd /home/hymn/msfenicsx && pytest tests/generator/test_parameter_sampler.py tests/generator/test_layout_engine.py tests/generator/test_pipeline.py -v`
Expected: PASS

- [ ] **Step 8: Commit the generator pipeline**

```bash
cd /home/hymn/msfenicsx
git add core/generator tests/generator
git commit -m "feat: rebuild scenario generator pipeline"
```

## Task 5: Implement the Official FEniCSx Radiation Solver Baseline

**Files:**
- Create: `core/solver/__init__.py`
- Create: `core/solver/case_to_geometry.py`
- Create: `core/solver/mesh_builder.py`
- Create: `core/solver/physics_builder.py`
- Create: `core/solver/nonlinear_solver.py`
- Create: `core/solver/field_sampler.py`
- Create: `core/solver/solution_builder.py`
- Test: `tests/solver/test_reference_case.py`
- Test: `tests/solver/test_generated_case.py`

- [ ] **Step 1: Write failing solver tests**

```python
from core.schema.io import load_case
from core.solver.nonlinear_solver import solve_case


def test_reference_case_solves_and_reports_temperature_bounds():
    case = load_case("/home/hymn/msfenicsx/scenarios/manual/reference_case.yaml")
    solution = solve_case(case)
    assert solution.summary_metrics["temperature_max"] >= solution.summary_metrics["temperature_min"]
```

- [ ] **Step 2: Run solver tests to verify they fail**

Run: `cd /home/hymn/msfenicsx && pytest tests/solver/test_reference_case.py tests/solver/test_generated_case.py -v`
Expected: FAIL because solver modules do not exist

- [ ] **Step 3: Implement canonical case-to-geometry interpretation**

Translate:

- component geometry
- material maps
- line-sink boundary features
- nonlinear radiation parameters

into solver-ready geometry and physics inputs.

- [ ] **Step 4: Implement official FEniCSx mesh construction**

The new mesh builder must read the canonical case shape definitions rather than legacy grid-only assumptions.

- [ ] **Step 5: Implement steady conduction with nonlinear radiation boundaries**

Build:

- variational form
- facet tagging for `line_sink`
- SNES/Newton nonlinear solve
- convergence diagnostics capture

- [ ] **Step 6: Implement field sampling and canonical `thermal_solution` creation**

Sample at least:

- temperature field
- summary metrics
- component-level temperature summaries
- runtime diagnostics

- [ ] **Step 7: Run solver tests**

Run: `cd /home/hymn/msfenicsx && pytest tests/solver/test_reference_case.py tests/solver/test_generated_case.py -v`
Expected: PASS

- [ ] **Step 8: Run a broader focused verification pass**

Run: `cd /home/hymn/msfenicsx && pytest tests/schema tests/geometry tests/generator tests/solver -v`
Expected: PASS

- [ ] **Step 9: Commit the solver baseline**

```bash
cd /home/hymn/msfenicsx
git add core/solver tests/solver
git commit -m "feat: add official fenicsx radiation solver baseline"
```

## Task 6: Build the `scenario_runs/` Artifact Protocol

**Files:**
- Create: `core/io/__init__.py`
- Create: `core/io/scenario_runs.py`
- Test: `tests/io/test_scenario_runs.py`

- [ ] **Step 1: Write the failing artifact-protocol test**

```python
from pathlib import Path

from core.io.scenario_runs import write_run_bundle


def test_write_run_bundle_creates_expected_layout(tmp_path: Path):
    output = write_run_bundle(tmp_path, scenario_id="panel-baseline", case_id="case-001", case_payload={}, solution_payload={})
    assert (output / "case.yaml").exists()
    assert (output / "solution.yaml").exists()
    assert (output / "manifest.json").exists()
```

- [ ] **Step 2: Run the artifact test to verify it fails**

Run: `cd /home/hymn/msfenicsx && pytest tests/io/test_scenario_runs.py -v`
Expected: FAIL because `scenario_runs` writer does not exist

- [ ] **Step 3: Implement the run-bundle writer**

The writer must create:

```text
scenario_runs/<scenario_id>/<case_id>/
  case.yaml
  solution.yaml
  logs/
  fields/
  tensors/
  figures/
  manifest.json
```

- [ ] **Step 4: Make the solver pipeline capable of writing a minimal bundle**

Support:

- canonical case snapshot
- canonical solution snapshot
- manifest with relative references

- [ ] **Step 5: Run the artifact test**

Run: `cd /home/hymn/msfenicsx && pytest tests/io/test_scenario_runs.py -v`
Expected: PASS

- [ ] **Step 6: Commit the artifact protocol**

```bash
cd /home/hymn/msfenicsx
git add core/io tests/io
git commit -m "feat: add scenario runs artifact protocol"
```

## Task 7: Wire the CLI End-to-End for Phase 1

**Files:**
- Modify: `core/cli/main.py`
- Modify: `tests/cli/test_cli_smoke.py`
- Create: `tests/cli/test_cli_end_to_end.py`

- [ ] **Step 1: Write the failing CLI end-to-end test**

```python
from core.cli.main import main


def test_generate_then_solve_cli_smoke(tmp_path, monkeypatch):
    code = main([
        "generate",
        "--template",
        "/home/hymn/msfenicsx/scenarios/templates/panel_radiation_baseline.yaml",
        "--seed",
        "3",
        "--output-root",
        str(tmp_path),
    ])
    assert code == 0
```

- [ ] **Step 2: Run CLI tests to verify they fail**

Run: `cd /home/hymn/msfenicsx && pytest tests/cli/test_cli_smoke.py tests/cli/test_cli_end_to_end.py -v`
Expected: FAIL because commands are not implemented

- [ ] **Step 3: Implement Phase 1 CLI commands**

Commands should include:

- `validate-scenario-template`
- `generate-case`
- `solve-case`

Use the new kernel only; do not call any legacy scripts.

- [ ] **Step 4: Run CLI tests**

Run: `cd /home/hymn/msfenicsx && pytest tests/cli/test_cli_smoke.py tests/cli/test_cli_end_to_end.py -v`
Expected: PASS

- [ ] **Step 5: Run the full Phase 1 verification suite**

Run: `cd /home/hymn/msfenicsx && pytest tests/schema tests/geometry tests/generator tests/solver tests/io tests/cli -v`
Expected: PASS

- [ ] **Step 6: Commit the CLI integration**

```bash
cd /home/hymn/msfenicsx
git add core/cli tests/cli
git commit -m "feat: wire phase1 cli commands"
```

## Task 8: Remove Legacy Demo Implementation and Finalize the Cutover

**Files:**
- Delete: `src/`
- Delete: `radiation_gen/`
- Delete: `examples/`
- Delete: `states/`
- Delete or replace: legacy tests in `tests/` that target removed demo modules
- Modify: `/home/hymn/msfenicsx/README.md`
- Modify: `/home/hymn/msfenicsx/docs/superpowers/specs/2026-03-26-msfenicsx-clean-rebuild-design.md` only if cutover decisions require a documented clarification

- [ ] **Step 1: Verify the new baseline before deleting anything**

Run: `cd /home/hymn/msfenicsx && pytest tests/schema tests/geometry tests/generator tests/solver tests/io tests/cli -v`
Expected: PASS

- [ ] **Step 2: Identify and remove legacy implementation directories**

Delete only after the Phase 1 suite is green:

- `src/`
- `radiation_gen/`
- `examples/`
- `states/`

- [ ] **Step 3: Remove legacy tests or replace them with new-module equivalents**

Legacy test files that target removed demo modules should be deleted in the same commit as the removed code.

- [ ] **Step 4: Update the README to describe only the new platform**

The README must:

- describe canonical schema objects
- describe top-level module boundaries
- describe `scenario_runs/`
- stop referencing deleted demo paths

- [ ] **Step 5: Run the remaining test suite after deletion**

Run: `cd /home/hymn/msfenicsx && pytest -v`
Expected: PASS with only the rebuilt platform tests remaining

- [ ] **Step 6: Commit the cutover**

```bash
cd /home/hymn/msfenicsx
git add -A
git commit -m "refactor: remove legacy demo stack after phase1 cutover"
```

## Notes for Execution

- Keep all canonical values in SI units.
- Do not preserve legacy directory structure just for familiarity.
- Reuse legacy ideas, not legacy file boundaries.
- Do not implement `pymoo`, LLM strategy logic, advanced visualization, or CAD export in this plan.
- Do not delete legacy code before the new baseline is independently verified.
- If new implementation details contradict the approved spec, update the spec in a separate small commit before proceeding further.

## Local Review Limitation

This plan was reviewed locally against the approved spec at:

- `/home/hymn/msfenicsx/docs/superpowers/specs/2026-03-26-msfenicsx-clean-rebuild-design.md`

Subagent-based plan review was not performed in-session because delegation was not explicitly requested for this conversation.
