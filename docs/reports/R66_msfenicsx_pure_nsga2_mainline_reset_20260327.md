# R66 msfenicsx Pure NSGA-II Mainline Reset

Date: 2026-03-27

## Scope

This reset changes the active paper-facing optimizer mainline.

Historical note: this report captures the pure `NSGA-II` reset point. The repository has since added the first-batch six-backbone raw matrix runtime, but that later implementation does not change the paper-facing baseline established here.
Further update on 2026-03-28: the paper-facing controller line is now the separate `NSGA-II` hybrid-union track. Its `union-uniform` rung is already implemented and analyzed, and the immediate next paper-facing implementation step is `union-LLM NSGA-II`.

After this reset:

- the active classical baseline is plain `pymoo` `NSGA-II`
- the paired hot/cold four-component benchmark remains the active optimization problem
- the earlier heuristic hybrid `B1` direction is no longer an active supported repository baseline

## Why The Reset Was Made

The repository already established a meaningful paired hot/cold multiobjective benchmark, but the first hybrid `B1` direction mixed two distinct research questions:

1. whether a domain-operator action space helps compared with raw-vector `NSGA-II`
2. whether an intelligent controller such as an `LLM` can choose actions better than a non-LLM controller

For the paper-facing mainline, those questions should not be collapsed into one baseline. A plain `NSGA-II` optimizer is easier for reviewers to recognize immediately, easier to defend as a neutral classical reference, and cleaner as the main benchmark anchor.

## Active Baseline After Reset

The active optimizer entrypoint remains:

`python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml ...`

The active benchmark remains:

- benchmark template: `scenarios/templates/panel_four_component_hot_cold_benchmark.yaml`
- evaluation spec: `scenarios/evaluation/panel_four_component_hot_cold_baseline.yaml`
- optimizer spec: `scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml`

## Deferred Fairness Study

Operator-pool controller comparisons are intentionally deferred to a later dedicated phase.

That later phase must compare controllers under a matched setup:

- same action registry for the experiment class
- same repair logic
- same paired benchmark seeds
- same evaluation spec
- same simulation budget

The intended future comparison is:

- pure-native `NSGA-II`
- later `NSGA-II` hybrid-union uniform controller baseline
- later `NSGA-II` hybrid-union `LLM` controller comparison

## Verification

Executed in WSL with `/home/hymn/miniconda3/bin/conda run -n msfenicsx`:

1. `pytest tests/optimizers/test_nsga2_driver.py tests/optimizers/test_optimizer_cli.py tests/optimizers/test_optimizer_io.py -v`
   Result: `8 passed`
2. `pytest tests/optimizers tests/cli/test_cli_end_to_end.py -v`
   Result: `13 passed`
3. `pytest -v`
   Result: `58 passed`
4. `python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml --output-root ./scenario_runs/pure_nsga2_reset_smoke`
   Result: completed successfully

Fresh smoke-run output root:

- `scenario_runs/pure_nsga2_reset_smoke/optimization_result.json`
- `scenario_runs/pure_nsga2_reset_smoke/pareto_front.json`
- `scenario_runs/pure_nsga2_reset_smoke/manifest.json`
- representative bundles under `scenario_runs/pure_nsga2_reset_smoke/representatives/`

Fresh smoke-run summary:

- `run_id`: `panel-four-component-hot-cold-nsga2-b0-run`
- `num_evaluations`: `129`
- `feasible_rate`: `0.0310`
- `first_feasible_eval`: `73`
- `pareto_size`: `4`

## Status

The pure `NSGA-II` reset is now verified in the active repository mainline.

What changed materially:

- the heuristic hybrid `B1` path was removed from active code and active docs
- the active optimizer result contract no longer emits operator telemetry
- the only active classical optimizer spec is `panel_four_component_hot_cold_nsga2_b0.yaml`

What happened next:

- the separate `NSGA-II` hybrid-union ladder was defined
- the `union-uniform` rung was implemented and mechanism-analyzed
- the immediate next paper-facing implementation step is `union-LLM NSGA-II`
