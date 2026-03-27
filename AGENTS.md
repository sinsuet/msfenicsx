# AGENTS.md

This file gives Codex-style agents repository-specific guidance for `msfenicsx`.

## Repository Status

- `main` already contains the Phase 1 clean rebuild baseline.
- The old demo stack has been removed from active repository structure.
- The active optimizer mainline is now multicase and multiobjective.
- The active platform is organized around:
  - `core/`
  - `evaluation/`
  - `optimizers/`
  - `llm/`
  - `visualization/`
  - `scenarios/`
  - `tests/`
  - `docs/`

## Current Platform Identity

`msfenicsx` is now a clean research platform for:

- 2D thermal dataset generation
- steady conduction with nonlinear radiation-style sink boundaries
- canonical case generation and official FEniCSx baseline solving

The active canonical object flow is:

`scenario_template -> thermal_case -> thermal_solution -> scenario_runs/ bundle`

The active derived evaluation flow is:

`thermal_case + thermal_solution + evaluation_spec -> evaluation_report`

The active multicase evaluation flow is:

`{hot,cold} thermal_case + {hot,cold} thermal_solution + multicase evaluation_report`

The active optimizer mainline is:

`base design -> hot/cold operating cases -> multicase evaluation_report -> Pareto search -> representative solutions + Pareto artifacts`

## Architectural Expectations

- Keep `core/` as the kernel for:
  - schema
  - geometry
  - generator
  - solver
  - artifact I/O
  - contracts
  - CLI
- Keep `evaluation/`, `optimizers/`, `llm/`, and `visualization/` as separate top-level layers that consume `core/` rather than contaminating it.
- Do not add business logic to `scenarios/`; it is for hand-authored data inputs.
- Do not recreate legacy runtime folders such as `src/`, `radiation_gen/`, `examples/`, or `states/` as active architecture without explicit approval.

## Environment and Execution

- Canonical execution context for this repository is WSL2 Ubuntu.
- Even if the workspace is opened from Windows through a UNC path such as `\\wsl$\Ubuntu\home\hymn\msfenicsx`, agents should treat the repo as Linux-first and use `/home/hymn/msfenicsx` as the working path.
- Use the `msfenicsx` conda environment for Python, CLI, and tests.
- Prefer running verification with `/home/hymn/miniconda3/bin/conda run -n msfenicsx ...` inside WSL rather than relying on Windows Conda discovery.
- Avoid Windows-native environment paths such as `D:\...` for repo execution unless the user explicitly requests Windows-side validation.
- Prefer commands like:
  - `conda run -n msfenicsx pytest -v`
  - `conda run -n msfenicsx python -m core.cli.main validate-scenario-template --template scenarios/templates/panel_radiation_baseline.yaml`
  - `conda run -n msfenicsx python -m core.cli.main generate-case --template scenarios/templates/panel_radiation_baseline.yaml --seed 3 --output-root ./generated_cases`
  - `conda run -n msfenicsx python -m core.cli.main solve-case --case ./generated_cases/<case_id>.yaml --output-root ./scenario_runs`
  - `conda run -n msfenicsx python -m evaluation.cli evaluate-operating-cases --case hot=scenarios/manual/reference_case_hot.yaml --case cold=scenarios/manual/reference_case_cold.yaml --solution hot=/tmp/hot_solution.yaml --solution cold=/tmp/cold_solution.yaml --spec scenarios/evaluation/panel_hot_cold_multiobjective_baseline.yaml --output ./multicase_evaluation.yaml`
  - `conda run -n msfenicsx python -m optimizers.cli optimize-operating-cases --case hot=scenarios/manual/reference_case_hot.yaml --case cold=scenarios/manual/reference_case_cold.yaml --optimization-spec scenarios/optimization/reference_hot_cold_nsga2.yaml --output-root ./scenario_runs/optimizations/reference-hot-cold-nsga2`

## Data and Artifact Rules

- Treat `scenario_template`, `thermal_case`, and `thermal_solution` as the active canonical contracts.
- Keep evaluation criteria in standalone `evaluation_spec` files instead of adding objective or constraint metadata to `thermal_case`.
- Keep optimizer search settings and design-variable bounds in standalone `optimization_spec` files instead of adding optimizer metadata to `thermal_case`.
- Active optimization reporting should name operating cases and Pareto outputs instead of implying one scalar best result.
- Runtime outputs should go to `scenario_runs/` or another explicit artifact location, not source folders.
- Do not manually edit generated artifacts to change conclusions.

## Testing Expectations

- Maintained tests belong under `tests/`.
- Add or update focused tests for new behavior.
- Run fresh relevant verification before claiming completion.

Current Phase 1 test areas are:

- `tests/schema/`
- `tests/geometry/`
- `tests/generator/`
- `tests/solver/`
- `tests/io/`
- `tests/cli/`
- `tests/evaluation/`
- `tests/optimizers/`

## Documentation Expectations

- For major contract or workflow changes, update:
  - `README.md`
  - relevant docs under `docs/`
  - `RULES.md` and `AGENTS.md` when guidance changes
- Keep active docs aligned with implemented reality.

## Useful References

- `README.md`
- `docs/superpowers/specs/2026-03-26-msfenicsx-clean-rebuild-design.md`
- `docs/superpowers/plans/2026-03-26-msfenicsx-clean-rebuild-phase1.md`
- `docs/superpowers/plans/2026-03-27-msfenicsx-multicase-multiobjective-mainline.md`
- `docs/msgalaxy/R60_msfenicsx_2d_fenicsx_migration_initial_report_20260326.md`
- `docs/reports/R61_msfenicsx_evaluation_layer_rollout_20260326.md`
- `docs/reports/R62_msfenicsx_optimizer_baseline_rollout_20260327.md`
- `docs/reports/R63_msfenicsx_multicase_multiobjective_reset_20260327.md`
