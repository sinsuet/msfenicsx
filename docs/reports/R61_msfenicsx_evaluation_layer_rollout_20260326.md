# R61 msfenicsx Evaluation Layer Rollout (2026-03-26)

## Summary

This rollout adds the first active `evaluation/` layer on top of the Phase 1 clean-rebuild baseline.

The implementation keeps `core/` unchanged as the canonical kernel and introduces a separate evaluation contract that consumes:

- `thermal_case`
- `thermal_solution`
- external `evaluation_spec`

and produces one derived `evaluation_report`.

## Implemented Contract

### Inputs

- `evaluation_spec` defines:
  - `spec_meta`
  - `objectives`
  - `constraints`

### Output

- `evaluation_report` provides:
  - `feasible`
  - `metric_values`
  - `objective_summary`
  - `constraint_reports`
  - `violations`
  - `derived_signals`

### Supported Metric Namespaces

- `summary.*`
- `solver.*`
- `component.<component_id>.*`
- `case.*`

Current `case.*` derived metrics are:

- `case.total_power`
- `case.panel_area`
- `case.power_density`
- `case.component_count`

## Architecture Decision in Practice

The evaluation contract is intentionally external to `core/`:

- `thermal_case` stays free of objective and constraint metadata
- `core/cli` still handles validation, generation, and solving only
- `evaluation/cli` owns report generation
- `optimizers/` and `llm/` can later consume `evaluation_report` without forcing back-edges into `core/`

## Delivered Files

- `evaluation/models.py`
- `evaluation/validation.py`
- `evaluation/io.py`
- `evaluation/metrics.py`
- `evaluation/engine.py`
- `evaluation/artifacts.py`
- `evaluation/cli.py`
- `scenarios/evaluation/panel_single_objective_baseline.yaml`

## Baseline Workflow

1. Solve a case into a `scenario_runs/` bundle:

   `conda run -n msfenicsx python -m core.cli.main solve-case --case scenarios/manual/reference_case.yaml --output-root ./scenario_runs`

2. Evaluate the solved bundle against a spec:

   `conda run -n msfenicsx python -m evaluation.cli evaluate-case --case ./scenario_runs/panel-radiation-baseline/reference-case-001/case.yaml --solution ./scenario_runs/panel-radiation-baseline/reference-case-001/solution.yaml --spec scenarios/evaluation/panel_single_objective_baseline.yaml --output ./scenario_runs/panel-radiation-baseline/reference-case-001/evaluation.yaml --bundle-root ./scenario_runs/panel-radiation-baseline/reference-case-001`

## Verification Commands

The rollout was validated with the following fresh commands in the `msfenicsx` environment:

- `conda run -n msfenicsx pytest tests/evaluation -v`
- `conda run -n msfenicsx pytest tests/cli/test_cli_end_to_end.py -v`
- a fresh `solve-case` plus `evaluate-case` CLI chain against `scenarios/manual/reference_case.yaml`

## Follow-On Work

This rollout deliberately stops before:

- `pymoo` optimizer integration
- LLM policy-layer contracts
- richer hotspot localization based on exported field coordinates
- benchmark protocols across multiple seeds
