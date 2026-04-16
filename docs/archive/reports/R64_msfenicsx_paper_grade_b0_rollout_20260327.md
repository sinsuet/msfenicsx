# R64 msfenicsx Paper-Grade B0 Rollout

Date: 2026-03-27

## Scope

This rollout advances the approved paper-grade multiobjective baseline from the completed paired benchmark and evaluation layers into the active optimizer mainline.

Completed in this slice:

- replaced optimizer CLI entry with benchmark-source-driven `optimize-benchmark`
- added `benchmark_source` to the optimizer contract
- created the active `B0` optimization spec at `scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml`
- calibrated the active benchmark and evaluation thresholds so the deterministic baseline starts infeasible but the default `B0` run reaches feasible Pareto candidates
- expanded the B0 search space to 8 variables:
  - `processor_x`, `processor_y`
  - `rf_power_amp_x`, `rf_power_amp_y`
  - `battery_pack_x`, `battery_pack_y`
  - `radiator_start`, `radiator_end`
- introduced optimizer-side geometry and radiator repair in `optimizers/repair.py`
- separated the `pymoo` problem definition into `optimizers/problem.py`
- cut optimizer outputs over to manifest-backed optimization bundles with representative case/solution/evaluation snapshots
- constrained `generate-case` so paired benchmark templates must use `generate-operating-case-pair`

## Active Baseline After This Rollout

Active benchmark template:

- `scenarios/templates/panel_four_component_hot_cold_benchmark.yaml`

Active multicase evaluation spec:

- `scenarios/evaluation/panel_four_component_hot_cold_baseline.yaml`

Active optimizer spec:

- `scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml`

Active optimizer CLI:

- `python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml --output-root <path>`

Default calibrated `B0` settings after this rollout:

- cold battery floor: `259.5 K`
- population size: `16`
- generations: `8`

## Verification

Executed in WSL with `/home/hymn/miniconda3/bin/conda run -n msfenicsx`:

1. `pytest tests/optimizers/test_optimizer_io.py tests/optimizers/test_optimizer_cli.py -v`
2. `pytest tests/optimizers/test_codec.py tests/optimizers/test_nsga2_driver.py tests/solver/test_generated_case.py tests/solver/test_reference_case.py -v`
3. `pytest tests/cli/test_cli_end_to_end.py tests/generator/test_pipeline.py tests/evaluation tests/optimizers tests/solver/test_generated_case.py tests/solver/test_reference_case.py -v`

Latest focused verification result:

- `25 passed`

## Remaining Follow-Up

- implement `B1` hybrid-operator `NSGA-II`
- complete end-to-end benchmark reporting and seed-sweep evidence
