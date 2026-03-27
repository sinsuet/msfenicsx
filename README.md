# msfenicsx Clean Rebuild

`msfenicsx` now provides a clean baseline for:

- two-dimensional thermal dataset generation
- official FEniCSx solving of steady conduction problems with nonlinear radiation sink boundaries
- derived evaluation reports for objectives and constraint checks without contaminating `core/`

## Active Research Direction

The active optimization mainline is now organized around:

- paired hot/cold operating cases
- multiobjective thermal evaluation
- plain `pymoo` `NSGA-II` as the active classical optimizer baseline
- Pareto search as the optimizer output contract

The previous single-objective optimizer path has been retired from the active mainline.
The previous heuristic hybrid `B1` path is no longer part of the active supported baseline ladder.

## Top-Level Module Boundaries

- `core/`: canonical schema, geometry, generator, solver, artifact I/O, and CLI
- `evaluation/`: evaluation specs, report contracts, metric extraction, and standalone evaluation CLI
- `optimizers/`: optimization specs, decision-vector codecs, `pymoo` baseline search, and standalone optimizer CLI
- `llm/`: reserved boundary for future strategy-layer integrations
- `visualization/`: reserved boundary for future read-only rendering and reporting

## Active Flows

Canonical flow:

`scenario_template -> thermal_case -> thermal_solution -> scenario_runs/ bundle`

Single-case evaluation flow:

`thermal_case + thermal_solution + evaluation_spec -> evaluation_report`

Active multicase evaluation flow:

`{hot,cold} thermal_case + {hot,cold} thermal_solution + multicase evaluation_spec -> multicase evaluation_report`

Active optimizer mainline:

`base design -> hot/cold operating cases -> FEniCSx solves -> multicase evaluation_report -> Pareto search -> manifest-backed optimization bundle + representative solutions`

Seed inputs live under `scenarios/`, and generated run artifacts are written under `scenario_runs/` at runtime and ignored by git.

The active benchmark template lives at `scenarios/templates/panel_four_component_hot_cold_benchmark.yaml`.
The active multicase evaluation spec lives at `scenarios/evaluation/panel_four_component_hot_cold_baseline.yaml`.
The active multicase optimization spec lives at `scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml`.
Benchmark-specific optimizer tuning now lives in optimizer-layer profile files under `scenarios/optimization/profiles/`, while repository-wide backbone defaults live under `optimizers/`.
The active effective algorithm settings are resolved as `global backbone defaults < benchmark profile < spec inline parameter overrides`.
Future operator-pool controller work is approved only under the newer multi-backbone optimizer-matrix direction. It should not be reintroduced as an `NSGA-II`-only branch.

Current built-in evaluation metric namespaces are:

- `summary.*` from `thermal_solution.summary_metrics`
- `solver.*` from `thermal_solution.solver_diagnostics`
- `component.<component_id>.*` from `thermal_solution.component_summaries`
- `components.*` derived across component summaries
- `case.*` derived from `thermal_case`, currently including total power, panel area, power density, component count, and total radiator span

## CLI

Available commands:

- `conda run -n msfenicsx python -m core.cli.main validate-scenario-template --template scenarios/templates/panel_four_component_hot_cold_benchmark.yaml`
- `conda run -n msfenicsx python -m core.cli.main generate-operating-case-pair --template scenarios/templates/panel_four_component_hot_cold_benchmark.yaml --seed 11 --output-root ./scenario_runs/generated_cases/panel-four-component-hot-cold-benchmark/seed-11`
- `conda run -n msfenicsx python -m core.cli.main solve-case --case ./scenario_runs/generated_cases/panel-four-component-hot-cold-benchmark/seed-11/<case_id>.yaml --output-root ./scenario_runs`
- `conda run -n msfenicsx python -m evaluation.cli evaluate-case --case ./scenario_runs/<scenario_id>/<case_id>/case.yaml --solution ./scenario_runs/<scenario_id>/<case_id>/solution.yaml --spec scenarios/evaluation/panel_four_component_hot_cold_baseline.yaml --output ./evaluation_report.yaml --bundle-root ./scenario_runs/<scenario_id>/<case_id>`
- `conda run -n msfenicsx python -m evaluation.cli evaluate-operating-cases --case hot=./scenario_runs/generated_cases/panel-four-component-hot-cold-benchmark/seed-11/<hot_case_id>.yaml --case cold=./scenario_runs/generated_cases/panel-four-component-hot-cold-benchmark/seed-11/<cold_case_id>.yaml --solution hot=./scenario_runs/<scenario_id>/<hot_case_id>/solution.yaml --solution cold=./scenario_runs/<scenario_id>/<cold_case_id>/solution.yaml --spec scenarios/evaluation/panel_four_component_hot_cold_baseline.yaml --output ./scenario_runs/evaluations/panel-four-component-hot-cold-baseline/seed-11/report.yaml`
- `conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml --output-root ./scenario_runs/optimizations/panel-four-component-b0`

For templates with `operating_case_profiles`, use `generate-operating-case-pair`; `generate-case` is intentionally rejected for the active benchmark to avoid unloaded single-case artifacts.
Text artifacts in the active repository workflows should default to UTF-8 encoding.

## Baseline Ladder

Implemented today:

- `B0`: plain `pymoo` `NSGA-II` over the eight benchmark design variables

Approved next-stage optimizer architecture:

- `B0-matrix-raw`: raw runs for `NSGA-II`, `NSGA-III`, `C-TAEA`, `RVEA`, constrained `MOEA/D`, and `CMOPSO`
- `B1-matrix-pool-random`: the same six backbones under one shared operator pool with a `random_uniform` controller
- `L1-matrix-pool-llm`: future phase only, replacing only the controller on the same operator pool

The repository now includes the first-batch raw matrix runtime for `NSGA-II`, `NSGA-III`, `C-TAEA`, `RVEA`, constrained `MOEA/D`, and `CMOPSO`, together with the matrix spec contract and raw scenario specs. Shared pool adapters, pool-random drivers, and pool-LLM drivers remain to be implemented. The design and plan live in:

- `docs/superpowers/specs/2026-03-27-multi-backbone-optimizer-matrix-design.md`
- `docs/superpowers/plans/2026-03-27-multi-backbone-optimizer-matrix.md`

Current optimizer parameter layering:

- backbone wrappers instantiate algorithms from resolved `algorithm.parameters` rather than hardcoded benchmark-specific values
- repository-wide defaults live in `optimizers/algorithm_config.py`
- benchmark-specific overrides live in per-backbone profile files such as `scenarios/optimization/profiles/panel_four_component_hot_cold_nsga2_raw.yaml`
- individual optimization specs can still add final inline `algorithm.parameters` overrides when a one-off experiment needs to deviate from the benchmark profile

## Verification

The current baseline is covered by targeted tests in:

- `tests/schema/`
- `tests/geometry/`
- `tests/generator/`
- `tests/solver/`
- `tests/io/`
- `tests/cli/`
- `tests/evaluation/`
- `tests/optimizers/`
