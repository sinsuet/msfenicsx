# msfenicsx Clean Rebuild

`msfenicsx` now provides a clean baseline for:

- two-dimensional thermal dataset generation
- official FEniCSx solving of steady conduction problems with nonlinear radiation sink boundaries
- derived evaluation reports for objectives and constraint checks without contaminating `core/`

## Active Research Direction

The active optimization mainline is now organized around:

- paired hot/cold operating cases
- multiobjective thermal evaluation
- Pareto search as the optimizer output contract

The previous single-objective optimizer path has been retired from the active mainline.

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

`base design -> hot/cold operating cases -> FEniCSx solves -> multicase evaluation_report -> Pareto search -> representative solutions + Pareto artifacts`

Seed inputs live under `scenarios/`, and generated run artifacts are written under `scenario_runs/` at runtime and ignored by git.

The active multicase evaluation spec lives at `scenarios/evaluation/panel_hot_cold_multiobjective_baseline.yaml`.
The active multicase optimization spec lives at `scenarios/optimization/reference_hot_cold_nsga2.yaml`.

Current built-in evaluation metric namespaces are:

- `summary.*` from `thermal_solution.summary_metrics`
- `solver.*` from `thermal_solution.solver_diagnostics`
- `component.<component_id>.*` from `thermal_solution.component_summaries`
- `components.*` derived across component summaries
- `case.*` derived from `thermal_case`, currently including total power, panel area, power density, component count, and total radiator span

## CLI

Available commands:

- `conda run -n msfenicsx python -m core.cli.main validate-scenario-template --template scenarios/templates/panel_radiation_baseline.yaml`
- `conda run -n msfenicsx python -m core.cli.main generate-case --template scenarios/templates/panel_radiation_baseline.yaml --seed 3 --output-root ./generated_cases`
- `conda run -n msfenicsx python -m core.cli.main solve-case --case ./generated_cases/<case_id>.yaml --output-root ./scenario_runs`
- `conda run -n msfenicsx python -m evaluation.cli evaluate-case --case ./scenario_runs/<scenario_id>/<case_id>/case.yaml --solution ./scenario_runs/<scenario_id>/<case_id>/solution.yaml --spec scenarios/evaluation/panel_hot_cold_multiobjective_baseline.yaml --output ./evaluation_report.yaml --bundle-root ./scenario_runs/<scenario_id>/<case_id>`
- `conda run -n msfenicsx python -m evaluation.cli evaluate-operating-cases --case hot=scenarios/manual/reference_case_hot.yaml --case cold=scenarios/manual/reference_case_cold.yaml --solution hot=/tmp/hot_solution.yaml --solution cold=/tmp/cold_solution.yaml --spec scenarios/evaluation/panel_hot_cold_multiobjective_baseline.yaml --output ./multicase_evaluation.yaml`
- `conda run -n msfenicsx python -m optimizers.cli optimize-operating-cases --case hot=scenarios/manual/reference_case_hot.yaml --case cold=scenarios/manual/reference_case_cold.yaml --optimization-spec scenarios/optimization/reference_hot_cold_nsga2.yaml --output-root ./scenario_runs/optimizations/reference-hot-cold-nsga2`

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
