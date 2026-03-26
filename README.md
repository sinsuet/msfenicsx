# msfenicsx Clean Rebuild (Phase 1)

`msfenicsx` now targets a clean Phase 1 baseline for two-dimensional thermal dataset generation and official FEniCSx solving of steady conduction problems with nonlinear radiation sink boundaries.

## Top-Level Module Boundaries

- `core/`: canonical schema, geometry, generator, solver, artifact I/O, and CLI
- `evaluation/`: reserved boundary for future evaluation logic
- `optimizers/`: reserved boundary for future optimization integrations
- `llm/`: reserved boundary for future strategy-layer integrations
- `visualization/`: reserved boundary for future read-only rendering and reporting

## Phase 1 Flow

The current baseline flow is:

`scenario_template -> thermal_case -> thermal_solution -> scenario_runs/ bundle`

Seed inputs live under `scenarios/`, and generated run artifacts are written under `scenario_runs/` at runtime and ignored by git.

## CLI

Available commands:

- `msfenicsx validate-scenario-template --template scenarios/templates/panel_radiation_baseline.yaml`
- `msfenicsx generate-case --template scenarios/templates/panel_radiation_baseline.yaml --seed 3 --output-root ./generated_cases`
- `msfenicsx solve-case --case ./generated_cases/<case_id>.yaml --output-root ./scenario_runs`

## Verification

The rebuilt Phase 1 baseline is currently covered by targeted tests in:

- `tests/schema/`
- `tests/geometry/`
- `tests/generator/`
- `tests/solver/`
- `tests/io/`
- `tests/cli/`
