# R62 msfenicsx Optimizer Baseline Rollout (2026-03-27)

## Summary

This rollout activates the first real `optimizers/` layer on top of the existing:

- `core/` canonical kernel
- `evaluation/` objective and constraint reporting layer

The delivered baseline is intentionally narrow:

- standalone `optimization_spec`
- numeric decision-vector codec over `thermal_case`
- `pymoo` constrained single-objective baseline driver
- best-candidate artifact export

## Implemented Contract

### Input

`optimization_spec` defines:

- `spec_meta`
- `design_variables`
- `algorithm`
- `evaluation_protocol`

### Output

`optimization_result` records:

- baseline candidate summary
- best candidate summary
- aggregate metrics
- candidate history
- provenance

### Current Algorithm Support

The initial implementation supports:

- `pymoo_ga`

The shipped baseline optimizer spec is:

- `scenarios/optimization/reference_case_position_search.yaml`

It searches payload position on:

- `scenarios/manual/reference_case.yaml`

using the existing:

- `scenarios/evaluation/panel_single_objective_baseline.yaml`

## Artifact Outputs

The optimizer CLI writes:

- `optimization_result.json`
- `best_case.yaml`
- `best_solution.yaml`
- `best_evaluation.yaml`

to an explicit output root.

## Baseline Workflow

```bash
conda run -n msfenicsx python -m optimizers.cli optimize-case \
  --case scenarios/manual/reference_case.yaml \
  --optimization-spec scenarios/optimization/reference_case_position_search.yaml \
  --output-root ./scenario_runs/optimizations/reference-case-position-search
```

## Verification Commands

This rollout was validated with fresh commands in the `msfenicsx` environment:

- `conda run -n msfenicsx pytest tests/optimizers tests/cli/test_module_entrypoints.py -v`
- `conda run -n msfenicsx pytest tests/evaluation tests/optimizers tests/cli/test_module_entrypoints.py tests/cli/test_cli_end_to_end.py -q`
- a fresh real optimizer CLI run on `scenarios/manual/reference_case.yaml`

## Current Limits

This rollout does not yet implement:

- multi-objective experiment protocols
- benchmark seed sweeps
- optimizer-side fidelity scheduling
- LLM priors or online policy guidance
- mixed discrete or operator-style search spaces
