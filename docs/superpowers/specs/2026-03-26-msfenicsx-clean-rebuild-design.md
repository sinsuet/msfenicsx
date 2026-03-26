# Msfenicsx Clean Rebuild Design

> Status: approved design draft for a full platform reset. Old implementation code is disposable. `docs/` remains the long-term knowledge base.

## 1. Goal

Rebuild `msfenicsx` as a clean research platform for two-dimensional thermal simulation and dataset generation focused on nonlinear radiation boundary conditions on satellite panel or deck layout problems.

Phase 1 only delivers:

- a unified canonical schema
- a scenario-driven dataset generator
- an official FEniCSx nonlinear radiation solver baseline
- a stable `scenario_runs/` artifact protocol

Everything else, including the current demo solver chain, current LLM optimization flow, current visualization flow, and the standalone `radiation_gen/` project layout, is considered disposable implementation.

## 2. Project Context

User-approved context:

- Project name remains `msfenicsx`
- Repository mainline is `main`
- The repository has already been committed and pushed to `origin/main`
- The first commit message is `ylq`
- Existing `docs/` content remains the durable research asset
- Existing code can be deleted after the new baseline is in place

Methodology reference:

- [R60](/home/hymn/msfenicsx/docs/msgalaxy/R60_msfenicsx_2d_fenicsx_migration_initial_report_20260326.md) remains the top-level migration and research-direction reference

## 3. Problem Definition

The platform targets:

- two-dimensional steady thermal conduction
- nonlinear radiation boundary conditions
- satellite panel or deck planar component layout scenarios
- dataset generation that can support both:
  - scenario and solver truth libraries for future optimization
  - derived training tensors for surrogate or neural-operator workflows

The platform does not treat the current demo stack as a long-term foundation. It uses only the useful ideas in legacy code, especially layout sampling and scenario synthesis logic.

## 4. Hard Decisions

The following decisions are fixed by design:

1. The rebuild is a clean reset.
2. `docs/` is the only mandatory retained asset from the old repository.
3. The new canonical input format is a new unified `thermal_case.yaml/json` family, not the old `radiation_gen` sample protocol.
4. Phase 1 is limited to:
   - schema
   - scenario generator
   - official FEniCSx baseline solver
   - `scenario_runs/`
5. The physical baseline keeps the nonlinear radiation problem but is rebuilt in a more formal FEniCSx architecture.
6. The primary geometry abstraction is a two-dimensional satellite panel or deck layout, not a generic toy heat problem and not a section-only abstraction.
7. The data strategy is:
   - scenario and solver truth library first
   - derived ML tensors second
8. `radiation_gen/` will not survive as a top-level folder after migration.

## 5. Design Principles

- Keep the canonical problem definition independent from optimization, LLM logic, visualization, and future CAD export.
- Treat every solver result as a derived artifact, never as part of the canonical input object.
- Preserve physically meaningful, SI-based internal units.
- Make all downstream systems consume the same canonical objects rather than inventing parallel schemas.
- Keep module boundaries visible at the repository root.
- Preserve knowledge from legacy code, but not legacy code structure.

## 6. Canonical Objects

Three canonical object families define the Phase 1 platform.

### 6.1 `scenario_template`

Purpose:

- defines distributions, constraints, allowed component families, and generation rules
- acts as the generator input

Contains:

- scenario metadata
- panel or deck domain rules
- placement region rules
- keep-out regions
- component family definitions and sampling ranges
- boundary feature families such as `line_sink`
- load generation rules
- material generation rules
- mesh and solver profile defaults

It is not directly solved.

### 6.2 `thermal_case`

Purpose:

- defines one deterministic, solver-ready scenario instance
- acts as the single source of truth for simulation input

Contains:

- `schema_version`
- `case_meta`
- `coordinate_system`
- `panel_domain`
- `materials`
- `components`
- `boundary_features`
- `loads`
- `physics`
- `mesh_profile`
- `solver_profile`
- `provenance`

It does not contain:

- probability distributions
- generator ranges
- optimization metadata
- LLM metadata
- artifact paths
- solver outputs

### 6.3 `thermal_solution`

Purpose:

- defines one formal solver result for one `thermal_case`

Contains:

- `solution_meta`
- mesh and solver diagnostics
- convergence information
- field references or field index records
- summary metrics
- component-level thermal summaries
- provenance back to `case_id`

It is a derived object and never becomes the canonical problem definition.

## 7. Geometry Model

### 7.1 Main Geometry Intent

The geometry layer models a planar satellite panel or deck layout.

The geometry system should feel like a formalized two-dimensional engineering abstraction of panel-mounted thermal layouts, not a general-purpose CAD system.

### 7.2 Supported Component Primitives

Phase 1 geometry should support:

- `rect`
- `circle`
- `capsule`
- constrained `polygon`
- `slot`

### 7.3 Boundary Thermal Features

Boundary thermal features are not regular components.

Phase 1 explicitly supports:

- `line_sink`

`line_sink` belongs under `boundary_features`, not under `components`, because it is a thermal boundary feature rather than a panel-occupying device.

### 7.4 Geometry Expression Rules

Each component should be expressed through:

- identity
- role
- primitive shape
- pose
- geometry parameters
- material reference
- optional placement constraints
- optional thermal tags

Recommended conventions:

- local parameterization for primitive geometry
- local-vertex-plus-pose for `polygon`
- clear rotation handling at the schema level

## 8. Unit Policy

All canonical schema values use SI-style internal units.

Canonical units:

- length: `m`
- temperature: `K`
- conductivity: `W/(m*K)`
- total power: `W`
- derived heat densities with explicit SI semantics

Human-facing engineering unit conversions belong only in reporting and visualization layers.

## 9. Repository Architecture

The rebuilt repository should expose module boundaries at the top level.

### 9.1 Top-Level Directories

- `docs/`
- `core/`
- `evaluation/`
- `optimizers/`
- `llm/`
- `visualization/`
- `scenarios/`
- `scenario_runs/`
- `tests/`

### 9.2 `core/`

`core/` is the platform kernel.

Recommended internal structure:

- `core/schema/`
- `core/geometry/`
- `core/generator/`
- `core/solver/`
- `core/io/`
- `core/contracts/`
- `core/cli/`

### 9.3 Dependency Rule

Hard dependency rule:

- `core/` must not depend on `evaluation/`, `optimizers/`, `llm/`, or `visualization/`
- `evaluation/` may depend on `core/`
- `optimizers/`, `llm/`, and `visualization/` may depend on `core/` and, where justified, `evaluation/`
- `scenarios/` contains data, not business logic

This rule protects the physical baseline from later experimentation layers.

## 10. Phase 1 Execution Pipeline

The official Phase 1 flow is:

```text
scenario_template
  -> generator pipeline
  -> thermal_case
  -> schema validation
  -> official FEniCSx solver baseline
  -> thermal_solution
  -> scenario_runs artifact pack
```

### 10.1 Generator Pipeline

Recommended sublayers:

- template loader
- parameter sampler
- layout engine
- feature synthesizer
- case builder
- case validator

The generator pipeline produces `thermal_case` only. It must not do solving, plotting, or final artifact packaging.

### 10.2 Solver Pipeline

Recommended sublayers:

- case-to-geometry interpreter
- mesh builder
- physics builder
- nonlinear solver
- field sampler
- solution builder

The solver pipeline reads `thermal_case` and emits `thermal_solution` only.

### 10.3 Artifact Pack Pipeline

Artifact packaging is a separate responsibility.

It gathers:

- input snapshot
- solution summary
- field files
- tensors
- logs
- figures
- machine-readable manifest

## 11. `scenario_runs/` Protocol

All run artifacts are stored under:

```text
scenario_runs/
  <scenario_id>/
    <case_id>/
      case.yaml
      solution.yaml
      logs/
      fields/
      tensors/
      figures/
      manifest.json
```

Definitions:

- `case.yaml`: canonical input snapshot
- `solution.yaml`: summary of the solved result and references
- `logs/`: solver logs, convergence traces, failures
- `fields/`: raw or semi-raw field outputs
- `tensors/`: ML-oriented derived arrays
- `figures/`: future visualization outputs
- `manifest.json`: machine-readable index for the run bundle

This directory is the traceable bridge between Phase 1 physics and future optimization or ML workflows.

## 12. Legacy Asset Extraction

Legacy code is not retained as architecture, but some ideas are worth preserving.

### 12.1 Migrate as Rewritten Concepts

- layout sampling ideas from `SeqLS`
- component-size and power sampling ideas
- line-based cooling feature synthesis ideas
- structured field-derivation ideas such as SDF and tensor packaging

### 12.2 Rebuild from Scratch

- solver implementation
- schema and I/O
- directory organization
- post-processing pipeline
- visualization pipeline
- CLI contract
- dataset protocol
- any script that mixes generation, solving, and artifact writing in one flow

### 12.3 Legacy Knowledge to Capture Before Deletion

- what the old nonlinear radiation formulation assumed
- what the old dataset protocol produced
- where old coupling between generator and solver caused design problems
- which old geometry or placement assumptions should survive

This knowledge should live in docs, not in preserved code folders.

## 13. Future Extension Interfaces

Phase 1 does not implement these systems, but its data model must support them.

### 13.1 `evaluation/`

Future `evaluation/` should derive structured summaries from:

- `thermal_case`
- `thermal_solution`

Expected future outputs:

- hotspot location
- component thermal summaries
- boundary heat-flow summaries
- objective summaries
- constraint reports

### 13.2 `optimizers/`

Future `optimizers/` should introduce an `optimization_spec` rather than contaminating `thermal_case`.

Expected contents:

- design variables
- objective definitions
- constraint definitions
- candidate encoding and decoding rules
- evaluation protocol
- optional fidelity policy

### 13.3 `llm/`

Future `llm/` should not directly mutate files ad hoc.

Recommended future protocol:

- `llm_context_pack`
- `llm_policy_output`

Expected outputs:

- variable-priority guidance
- category-switch guidance
- warm-start or seed biases
- shortlist preferences
- multi-variable coordination hints
- future fidelity-promotion hints

### 13.4 `visualization/`

Future `visualization/` should remain a read-only presentation layer over canonical inputs and derived solutions.

Recommended future scopes:

- case visualization
- solution visualization
- experiment visualization

## 14. Phase 1 Milestones

### M1: Schema

Deliver:

- `scenario_template`
- `thermal_case`
- `thermal_solution`
- load, save, and validate routines

Acceptance:

- one hand-authored scenario parses cleanly
- one generated case validates cleanly

### M2: Generator

Deliver:

- parameter sampler
- layout engine
- line-sink generation
- case assembly

Acceptance:

- batch generation produces valid deterministic cases for fixed seeds
- generation passes geometry and schema checks without solver involvement

### M3: Solver

Deliver:

- official FEniCSx baseline for steady conduction with nonlinear radiation boundaries
- deterministic `thermal_case -> thermal_solution` pipeline

Acceptance:

- at least one hand-authored case solves successfully
- at least one generated case solves successfully
- convergence and summary diagnostics are recorded

### M4: Artifact Protocol

Deliver:

- stable `scenario_runs/` layout
- input and solution snapshots
- run manifests
- minimal fields, tensors, and logs

Acceptance:

- each run is fully reconstructible from stored artifacts

## 15. Testing and Verification Strategy

Phase 1 verification must be part of the architecture, not an afterthought.

### 15.1 Schema Tests

Check:

- required fields
- shape parameter validity
- SI unit expectations
- line-sink validity

### 15.2 Geometry Tests

Check:

- inside-domain placement
- non-overlap
- keep-out compliance
- primitive geometry correctness

### 15.3 Generator Determinism Tests

Check:

- seed reproducibility
- template constraint satisfaction

### 15.4 Solver Verification Tests

Check:

- numerical sanity on simple reference cases
- mesh-refinement trend reasonableness
- nonlinear solver stability
- diagnostics on solver failure

### 15.5 Artifact Protocol Tests

Check:

- `scenario_runs/` structure consistency
- correct linkage between case and solution
- manifest completeness

Solver validation should explicitly include:

- numerical verification
- regression consistency checks

## 16. Migration Sequence

### Stage 0: Freeze the Design

Write and approve the architecture and object contracts.

### Stage 1: Create New Skeleton

Create the new top-level module layout with no legacy coupling.

### Stage 2: Reimplement Generator Concepts

Rebuild generation logic from legacy ideas, not legacy file layout.

### Stage 3: Rebuild Official FEniCSx Solver

Connect the new solver to the new canonical schema.

### Stage 4: Establish `scenario_runs/`

Make runs reproducible and machine-indexable.

### Stage 5: Delete Legacy Code

Only after the new minimal baseline works:

- delete old `src/`
- delete `radiation_gen/`
- delete old `examples/`
- delete old `states/`
- delete old demo execution chains

## 17. Non-Goals for Phase 1

The following are intentionally excluded from Phase 1 implementation:

- `pymoo` integration
- LLM policy integration
- advanced experiment dashboards
- CAD export implementation
- full paper-grade visualization pipeline
- multi-fidelity orchestration
- mixed optimization-plus-policy control loops

These are future layers, not baseline requirements.

## 18. Why This Architecture Matches the Research Direction

This design aligns with the migration logic in [R60](/home/hymn/msfenicsx/docs/msgalaxy/R60_msfenicsx_2d_fenicsx_migration_initial_report_20260326.md):

- the physical truth loop is formalized first
- direct LLM control is not treated as the foundation
- traditional optimization can later attach cleanly
- LLM can later live as a strategy layer over formal contracts
- visualization becomes a read-only interpretation layer rather than a core dependency

In short:

- `core/` becomes the trustworthy physics and dataset platform
- `optimizers/` becomes the future numerical search layer
- `llm/` becomes the future strategy layer
- `visualization/` becomes the future expression layer

That separation is the intended long-term platform identity of `msfenicsx`.
