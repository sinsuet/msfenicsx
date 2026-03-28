# AGENTS.md

This file gives Codex-style agents repository-specific guidance for `msfenicsx`.

## Repository Status

- `main` already contains the Phase 1 clean rebuild baseline.
- The old demo stack has been removed from active repository structure.
- The active paper-facing classical optimizer baseline is multicase, multiobjective, and centered on a plain `pymoo` `NSGA-II` run.
- The repository now also includes the first implemented raw multi-backbone runtime batch for:
  - `NSGA-II`
  - `NSGA-III`
  - `C-TAEA`
  - `RVEA`
  - constrained `MOEA/D`
  - `CMOPSO`
- The approved next-stage optimizer architecture is a multi-backbone raw/union matrix rather than an `NSGA-II`-only operator-pool branch.
- The repository currently keeps the raw multi-backbone matrix runtime, an exploratory multi-backbone `union-uniform` runtime across the same six backbones, and the shared proposal-layer contracts.
- The paper-facing controller line is now a separate `NSGA-II` hybrid-union ladder:
  - pure-native `NSGA-II`
  - union-uniform `NSGA-II`
  - union-`LLM` `NSGA-II`
- The paper-facing `union-uniform` rung is now implemented and mechanism-analyzed.
- The immediate next paper-facing implementation step is `union-LLM` on `NSGA-II`, using the same mixed action registry, repair, evaluation contract, and budget framing.
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

The implemented optimizer runtime also supports a first-batch raw matrix and exploratory union-uniform matrix across the six approved backbones, using the same benchmark generation, evaluation, repair, and artifact contract.
For the paper-facing controller line, `NSGA-II union-uniform` is now implemented and analyzed, and the next implementation focus is `NSGA-II union-LLM` rather than further broadening the exploratory matrix runtime.

The earlier heuristic hybrid `B1` direction is superseded and should not be reintroduced as an active supported baseline without an explicit new plan.
Future multi-backbone operator-pool work should follow the multi-backbone optimizer-matrix spec and plan.
Future paper-facing `LLM` controller work on `NSGA-II` should follow the hybrid-union spec and plan.

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
- Use explicit repository-relative paths with forward slashes (`/`) whenever practical.
- Use the `msfenicsx` conda environment for Python, CLI, and tests.
- Prefer running verification with `/home/hymn/miniconda3/bin/conda run -n msfenicsx ...` inside WSL rather than relying on Windows Conda discovery.
- Avoid Windows-native environment paths such as `D:\...` for repo execution unless the user explicitly requests Windows-side validation.
- Repository text artifacts should default to UTF-8 encoding without BOM, and Python text I/O should explicitly use `encoding="utf-8"` for repository files.
- Treat terminal-side mojibake from the host or WSL bridge as environment noise unless the same corruption is present in the saved repository artifact itself.
- Prefer commands like:
  - `conda run -n msfenicsx pytest -v`
  - `conda run -n msfenicsx python -m core.cli.main validate-scenario-template --template scenarios/templates/panel_four_component_hot_cold_benchmark.yaml`
  - `conda run -n msfenicsx python -m core.cli.main generate-operating-case-pair --template scenarios/templates/panel_four_component_hot_cold_benchmark.yaml --seed 11 --output-root ./scenario_runs/generated_cases/panel-four-component-hot-cold-benchmark/seed-11`
  - `conda run -n msfenicsx python -m core.cli.main solve-case --case ./scenario_runs/generated_cases/panel-four-component-hot-cold-benchmark/seed-11/<case_id>.yaml --output-root ./scenario_runs`
  - `conda run -n msfenicsx python -m evaluation.cli evaluate-operating-cases --case hot=./scenario_runs/generated_cases/panel-four-component-hot-cold-benchmark/seed-11/<hot_case_id>.yaml --case cold=./scenario_runs/generated_cases/panel-four-component-hot-cold-benchmark/seed-11/<cold_case_id>.yaml --solution hot=./scenario_runs/<scenario_id>/<hot_case_id>/solution.yaml --solution cold=./scenario_runs/<scenario_id>/<cold_case_id>/solution.yaml --spec scenarios/evaluation/panel_four_component_hot_cold_baseline.yaml --output ./scenario_runs/evaluations/panel-four-component-hot-cold-baseline/seed-11/report.yaml`
  - `conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml --output-root ./scenario_runs/optimizations/panel-four-component-b0`

## Engineering Guardrails

- Read the exact source before editing and preserve precise edit context.
- If a write looks risky because of locking, permissions, or unclear ownership, stop and notify first.
- Never hardcode API keys, tokens, or private credentials; load secrets from environment variables or explicit local configuration.
- Do not silently change important runtime or solver defaults without documenting the change.
- Fix root causes with physically and architecturally defensible changes instead of fake passes, temporary bypasses, or scientifically invalid shortcuts.

## Data and Artifact Rules

- Treat `scenario_template`, `thermal_case`, and `thermal_solution` as the active canonical contracts.
- Keep evaluation criteria in standalone `evaluation_spec` files instead of adding objective or constraint metadata to `thermal_case`.
- Keep optimizer search settings and design-variable bounds in standalone `optimization_spec` files instead of adding optimizer metadata to `thermal_case`.
- Keep optimizer hyperparameters and backbone-specific variation settings in optimizer-layer config, not in `core/` contracts and not in hand-tuned wrapper code.
- Repository-wide backbone defaults belong in `optimizers/algorithm_config.py`.
- Benchmark-specific optimizer tuning belongs in profile/spec layer inputs such as `scenarios/optimization/profiles/` and `algorithm.parameters`, with effective resolution ordered as `global defaults < benchmark profile < spec inline overrides`.
- Backbone wrappers and raw drivers should consume resolved `algorithm.parameters` instead of hiding scenario-specific tuning in constructor logic.
- Active optimization reporting should name operating cases and Pareto outputs instead of implying one scalar best result.
- The active classical baseline should remain plain `NSGA-II` unless a newer plan explicitly replaces it.
- The approved multi-backbone comparison track should keep benchmark source, evaluation spec, decision encoding, repair, and artifact bundle contract aligned across backbones unless a document explicitly defines a different experiment class.
- Any future operator-pool controller comparison must be treated as a separate experimental track rather than silently folded into the mainline.
- Any future operator-pool controller comparison should be algorithm-agnostic and multi-backbone rather than `NSGA-II`-only.
- Runtime outputs should go to `scenario_runs/` or another explicit artifact location, not source folders.
- Prefer `scenario_runs/` as the canonical runtime root for generated cases, solved case bundles, evaluation reports, and optimization bundles.
- Active optimizer runs should write manifest-backed bundles under paths such as `scenario_runs/optimizations/...`.
- Templates with `operating_case_profiles` should be generated through `generate-operating-case-pair`, not `generate-case`.
- Remove temporary scripts, debug files, caches, and one-off intermediate outputs after validation when they are not part of the intended repository state.
- Human-authored source and docs stay in source and docs paths.
- Update `.gitignore` when new generated artifact classes appear.
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

## Evidence and Reporting Expectations

- Scientific or performance claims must identify the relevant template, case, solver profile, seed, and runtime path or artifact bundle.
- For multicase optimization claims, identify the operating cases and whether the evidence comes from one representative Pareto point or the Pareto set as a whole.
- If comparing future controller methods, keep the operator pool, repair, benchmark seeds, evaluation spec, and simulation budget matched unless the comparison is explicitly framed as a different experiment class.
- If comparing future backbone methods, keep benchmark source, evaluation spec, design-variable encoding, repair, and total expensive-evaluation budget matched unless the comparison is explicitly framed as a different experiment class.
- In the `NSGA-II` hybrid-union line, keep the mixed native-plus-custom action registry matched between the non-LLM and `LLM` controllers.
- In the `NSGA-II` hybrid-union line, describe the change as an action-space expansion, not as a change to the eight-variable decision encoding.
- If something is not validated yet, label it as a hypothesis rather than a confirmed result.
- Comparative claims should use more than one seed unless the work is explicitly exploratory.
- Keep infeasible cases, failed solves, regressions, and anomalies visible in analysis instead of hiding them.
- Failure reasons and dominant violations are valid evidence and should be retained in reports or run artifacts when relevant.

## Documentation Expectations

- For major contract or workflow changes, update:
  - `README.md`
  - relevant docs under `docs/`
  - `AGENTS.md` when repository guidance changes
- Keep active docs aligned with implemented reality.
- Treat `AGENTS.md` as the single authoritative repository guidance file.

## Useful References

- `README.md`
- `docs/superpowers/specs/2026-03-26-msfenicsx-clean-rebuild-design.md`
- `docs/superpowers/plans/2026-03-26-msfenicsx-clean-rebuild-phase1.md`
- `docs/superpowers/specs/2026-03-27-paper-grade-multiobjective-thermal-baseline-design.md`
- `docs/superpowers/specs/2026-03-27-multi-backbone-optimizer-matrix-design.md`
- `docs/superpowers/specs/2026-03-28-nsga2-hybrid-union-controller-design.md`
- `docs/superpowers/plans/2026-03-27-paper-grade-multiobjective-thermal-baseline.md`
- `docs/superpowers/plans/2026-03-27-pure-nsga2-mainline-reset.md`
- `docs/superpowers/plans/2026-03-27-multi-backbone-optimizer-matrix.md`
- `docs/superpowers/plans/2026-03-28-nsga2-hybrid-union-controller.md`
- `docs/reports/R60_msfenicsx_2d_fenicsx_migration_initial_report_20260326.md`
- `docs/reports/R63_msfenicsx_multicase_multiobjective_reset_20260327.md`
- `docs/reports/R64_msfenicsx_paper_grade_b0_rollout_20260327.md`
- `docs/reports/R66_msfenicsx_pure_nsga2_mainline_reset_20260327.md`
- `docs/reports/R67_msfenicsx_multi_backbone_optimizer_matrix_doc_reset_20260327.md`
- `docs/reports/R68_msfenicsx_nsga2_union_mechanism_analysis_20260328.md`
- `optimizers/algorithm_config.py`
- `optimizers/drivers/raw_driver.py`
- `optimizers/validation.py`
- `scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml`
- `scenarios/optimization/panel_four_component_hot_cold_nsga2_raw_b0.yaml`
- `scenarios/optimization/panel_four_component_hot_cold_nsga3_raw_b0.yaml`
- `scenarios/optimization/panel_four_component_hot_cold_ctaea_raw_b0.yaml`
- `scenarios/optimization/panel_four_component_hot_cold_rvea_raw_b0.yaml`
- `scenarios/optimization/panel_four_component_hot_cold_moead_raw_b0.yaml`
- `scenarios/optimization/panel_four_component_hot_cold_cmopso_raw_b0.yaml`
- `scenarios/optimization/panel_four_component_hot_cold_nsga2_union_uniform_p1.yaml`
- `scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1.yaml`
- `scenarios/optimization/profiles/panel_four_component_hot_cold_nsga2_raw.yaml`
- `scenarios/optimization/profiles/panel_four_component_hot_cold_nsga2_union.yaml`
- `scenarios/optimization/profiles/panel_four_component_hot_cold_nsga3_raw.yaml`
- `tests/optimizers/test_raw_driver_matrix.py`
- `tests/optimizers/test_repair.py`
