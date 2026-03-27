# AGENTS.md

This file gives Codex-style agents repository-specific guidance for `msfenicsx`.

## Repository Status

- `main` already contains the Phase 1 clean rebuild baseline.
- The old demo stack has been removed from active repository structure.
- The active implemented optimizer mainline is multicase, multiobjective, and centered on a plain `pymoo` `NSGA-II` baseline.
- The approved next-stage optimizer architecture is a multi-backbone raw/pool matrix rather than an `NSGA-II`-only operator-pool branch.
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

`base design -> hot/cold operating cases -> multicase evaluation_report -> Pareto search -> manifest-backed optimization bundle + representative solutions`

The only active paper-facing classical optimizer spec is:

`scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml`

The earlier heuristic hybrid `B1` direction is superseded and should not be reintroduced as an active supported baseline without an explicit new plan.
Future operator-pool work should follow the multi-backbone optimizer-matrix spec and plan.

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
- Repository text artifacts should default to UTF-8 encoding without BOM, and Python text I/O should explicitly use `encoding="utf-8"` for repository files.
- Prefer commands like:
  - `conda run -n msfenicsx pytest -v`
  - `conda run -n msfenicsx python -m core.cli.main validate-scenario-template --template scenarios/templates/panel_four_component_hot_cold_benchmark.yaml`
  - `conda run -n msfenicsx python -m core.cli.main generate-operating-case-pair --template scenarios/templates/panel_four_component_hot_cold_benchmark.yaml --seed 11 --output-root ./scenario_runs/generated_cases/panel-four-component-hot-cold-benchmark/seed-11`
  - `conda run -n msfenicsx python -m core.cli.main solve-case --case ./scenario_runs/generated_cases/panel-four-component-hot-cold-benchmark/seed-11/<case_id>.yaml --output-root ./scenario_runs`
  - `conda run -n msfenicsx python -m evaluation.cli evaluate-operating-cases --case hot=./scenario_runs/generated_cases/panel-four-component-hot-cold-benchmark/seed-11/<hot_case_id>.yaml --case cold=./scenario_runs/generated_cases/panel-four-component-hot-cold-benchmark/seed-11/<cold_case_id>.yaml --solution hot=./scenario_runs/<scenario_id>/<hot_case_id>/solution.yaml --solution cold=./scenario_runs/<scenario_id>/<cold_case_id>/solution.yaml --spec scenarios/evaluation/panel_four_component_hot_cold_baseline.yaml --output ./scenario_runs/evaluations/panel-four-component-hot-cold-baseline/seed-11/report.yaml`
  - `conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml --output-root ./scenario_runs/optimizations/panel-four-component-b0`

## Data and Artifact Rules

- Treat `scenario_template`, `thermal_case`, and `thermal_solution` as the active canonical contracts.
- Keep evaluation criteria in standalone `evaluation_spec` files instead of adding objective or constraint metadata to `thermal_case`.
- Keep optimizer search settings and design-variable bounds in standalone `optimization_spec` files instead of adding optimizer metadata to `thermal_case`.
- Active optimization reporting should name operating cases and Pareto outputs instead of implying one scalar best result.
- The active classical baseline should remain plain `NSGA-II` unless a newer plan explicitly replaces it.
- Any future operator-pool controller comparison must be treated as a separate experimental track rather than silently folded into the mainline.
- Any future operator-pool controller comparison should be algorithm-agnostic and multi-backbone rather than `NSGA-II`-only.
- Runtime outputs should go to `scenario_runs/` or another explicit artifact location, not source folders.
- Prefer `scenario_runs/` as the canonical runtime root for generated cases, solved case bundles, evaluation reports, and optimization bundles.
- Active optimizer runs should write manifest-backed bundles under paths such as `scenario_runs/optimizations/...`.
- Templates with `operating_case_profiles` should be generated through `generate-operating-case-pair`, not `generate-case`.
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
- `docs/superpowers/specs/2026-03-27-paper-grade-multiobjective-thermal-baseline-design.md`
- `docs/superpowers/specs/2026-03-27-multi-backbone-optimizer-matrix-design.md`
- `docs/superpowers/plans/2026-03-27-paper-grade-multiobjective-thermal-baseline.md`
- `docs/superpowers/plans/2026-03-27-pure-nsga2-mainline-reset.md`
- `docs/superpowers/plans/2026-03-27-multi-backbone-optimizer-matrix.md`
- `docs/msgalaxy/R60_msfenicsx_2d_fenicsx_migration_initial_report_20260326.md`
- `docs/reports/R63_msfenicsx_multicase_multiobjective_reset_20260327.md`
- `docs/reports/R64_msfenicsx_paper_grade_b0_rollout_20260327.md`
- `docs/reports/R66_msfenicsx_pure_nsga2_mainline_reset_20260327.md`
- `docs/reports/R67_msfenicsx_multi_backbone_optimizer_matrix_doc_reset_20260327.md`
