# S3/S4 Scale Benchmarks Design

Date: 2026-04-27

Status: proposed design, approved direction; no implementation yet.

## 1. Goal

Add two new companion benchmarks after `s2_staged`:

- `s3_scale20`: a 20-component, 42-variable scale benchmark.
- `s4_dense25`: a 25-component, 52-variable dense benchmark.

Both benchmarks should keep the active platform identity:

- one operating case
- fixed named components
- all components optimize `x/y` only
- no optimized rotation
- one movable top-edge sink window with `start/end`
- same objectives as S1/S2:
  - `summary.temperature_max`
  - `summary.temperature_gradient_rms`
- cheap constraints before PDE
- raw / union / llm ladder with matched budgets and evaluation specs

The goal is not to replace `s2_staged`. S3 and S4 should extend the benchmark family so we can test whether the optimizer and controller behavior survives higher decision dimension and higher layout occupancy.

## 2. Current S2 Diagnosis

The current `s2_staged` template is a staged feasibility benchmark, not just a 15-component case.

Its intended mechanism is:

1. Generate a legal 15-component case with a compact right-side thermal core.
2. Start with a left-shifted top sink window whose raw span exceeds the evaluation budget.
3. Let optimizer legality project the sink into budget.
4. After projection, the sink becomes less aligned with the right-side thermal core.
5. The repaired baseline becomes infeasible through one dominant thermal violation, currently `c02_peak_temperature_limit`.

For seed 11 under the current template:

- component count: 15
- decision variables: 32
- raw component area ratio over the official placement region: about `0.445`
- generated sink: `start=0.08`, `end=0.46`, span `0.38`
- sink budget limit: `0.32`
- generated case cheap infeasibility: `radiator_span_budget = 0.06`
- generated PDE summary:
  - `summary.temperature_max ~= 322.87 K`
  - `summary.temperature_gradient_rms ~= 19.82`
- projected/repaired baseline:
  - sink becomes about `0.11..0.43`
  - `summary.temperature_max ~= 326.54 K`
  - `summary.temperature_gradient_rms ~= 19.81`
  - dominant positive violation is `c02_peak_temperature_limit ~= 3.02 K`

This is a useful benchmark shape. S3/S4 should preserve the staged structure, but increase occupancy and dimensionality.

## 3. Occupancy Policy

S3/S4 should not be forced to match the 15-component `~0.45` area ratio. More components should naturally occupy more of the placement region.

Target raw component area ratios:

| benchmark | components | variables | target raw area ratio | role |
| --- | ---: | ---: | ---: | --- |
| `s2_staged` | 15 | 32 | `~0.445` | staged controller benchmark |
| `s3_scale20` | 20 | 42 | `0.52-0.55` | scale-up benchmark |
| `s4_dense25` | 25 | 52 | `0.60-0.63` | dense benchmark |

These are raw footprint ratios. Clearance-aware effective occupancy will be higher. The implementation should keep clearances real, but avoid copying S2 large-component clearances onto every added module.

Recommended clearance range for added modules:

- normal small modules: `0.008-0.010`
- high-power or service-critical modules: `0.011-0.012`

If S4 cannot generate stable legal layouts under this range, reduce added-module clearances before reducing the benchmark role to an easier layout.

## 4. S3: `s3_scale20`

### 4.1 Benchmark Identity

`s3_scale20` should be a moderate scale extension of S2.

It should add five components to the S2 family while preserving the staged thermal-core mechanism.

Target contract:

- template id: `s3_scale20`
- components: 20
- design variables: 42
- panel: `1.0 x 0.8`
- placement region: about `x=0.06..0.94`, `y=0.05..0.70`
- target raw area ratio: `0.52-0.55`
- target total power: about `150-158 W`
- generated sink baseline: about `0.10..0.52`
- sink budget: about `0.35`

### 4.2 Added Components

S3 should keep S2 `c01..c15` as the inherited core and add:

| id | role | shape | nominal geometry | power | placement role |
| --- | --- | --- | --- | ---: | --- |
| `c16` | memory_stack_01 | rect | `0.130 x 0.100` | `5.5 W` | compute shoulder |
| `c17` | aux_power_stage | rect | `0.135 x 0.095` | `8.5 W` | secondary hot core |
| `c18` | rf_frontend | capsule | `length=0.205`, `radius=0.033` | `4.5 W` | right service edge |
| `c19` | sensor_hub | circle | `radius=0.058` | `3.2 W` | lower support band |
| `c20` | edge_io_micro | slot | `length=0.245`, `width=0.054` | `3.8 W` | left/bottom routing |

The five added components contribute about `0.062` raw area. With the slightly wider placement region, this should put S3 near `0.53` raw occupancy.

`c17` should join the staged thermal group. It gives the controller a second meaningful heat target without making S3 a multi-failure wall.

### 4.3 Layout Strategy

S3 should use an S2-like strategy with more space and one secondary thermal lane:

- `active_deck`: about `x=0.07..0.93`, `y=0.07..0.69`
- `dense_core`: about `x=0.48..0.82`, `y=0.15..0.42`
- `adversarial_core`: about `x=0.50..0.88`, `y=0.13..0.52`
- `secondary_core`: about `x=0.34..0.68`, `y=0.22..0.56`
- `top_sink_band`: about `x=0.12..0.52`, `y=0.56..0.69`
- `left_io_edge`: about `x=0.08..0.25`, `y=0.08..0.68`
- `right_service_edge`: about `x=0.78..0.94`, `y=0.08..0.68`

If the current layout engine does not understand `secondary_core`, the first implementation can map those components to existing hints and rely on `center_mass`, `adversarial_core`, `left_edge`, `right_edge`, `bottom_band`, and `top_band`.

### 4.4 Evaluation Shape

S3 should be infeasible after the official sink projection, but not dominated by geometry.

Target repaired-baseline behavior:

- cheap geometry issues: zero
- sink budget violation after projection: zero or numerical noise only
- positive thermal constraints: one or two
- total positive thermal violation: about `3-6 K`
- dominant constraints: `c02` and/or `c17`

Evaluation constraints should include:

- `radiator_span_budget <= 0.35`
- peak limits for the inherited thermal-core components:
  - `c02`
  - `c04`
  - `c06`
  - `c12`
- peak limit for the new secondary hot component:
  - `c17`
- panel spread limit

The exact numeric peak limits should be calibrated from the generated and projected seed-11 baseline, not guessed before the first solve.

## 5. S4: `s4_dense25`

### 5.1 Benchmark Identity

`s4_dense25` should be explicitly dense. It should not be judged by the S2 area ratio.

Target contract:

- template id: `s4_dense25`
- components: 25
- design variables: 52
- panel: `1.0 x 0.8`
- placement region: about `x=0.05..0.95`, `y=0.05..0.71`
- target raw area ratio: `0.60-0.63`
- target total power: about `172-182 W`
- generated sink baseline: about `0.10..0.56`
- sink budget: about `0.37-0.38`

S4 is allowed to be harder than S3. It should still be a feasible optimization benchmark, not a packing impossibility.

### 5.2 Added Components

S4 should inherit S3 `c01..c20` and add:

| id | role | shape | nominal geometry | power | placement role |
| --- | --- | --- | --- | ---: | --- |
| `c21` | micro_power_stage_02 | rect | `0.130 x 0.095` | `7.2 W` | secondary thermal core |
| `c22` | memory_stack_02 | rect | `0.125 x 0.092` | `5.0 W` | compute shoulder |
| `c23` | service_radio | rect | `0.150 x 0.078` | `4.8 W` | right service edge |
| `c24` | aux_sensor_disc | circle | `radius=0.058` | `3.0 W` | lower support band |
| `c25` | bottom_bus | slot | `length=0.255`, `width=0.054` | `3.5 W` | bottom/edge routing |

The five S4-only components contribute about `0.059` raw area. Combined with the S3 additions, S4 should land near `0.61` raw occupancy over the expanded placement region.

### 5.3 Layout Strategy

S4 should be denser than S3, but it needs enough structure that a controller can act on meaningful layout regimes.

Recommended structure:

- keep right-side staged hot core for `c02/c04/c06/c12`
- place `c17/c21` into a secondary thermal lane, not exactly on top of the original core
- place `c16/c22` as compute shoulders near center mass
- keep `c18/c23` near the right service edge
- keep `c20/c25` as edge or bottom bus elements
- use `c19/c24` as lower support components

The template should avoid forcing all new high-power modules into the same `adversarial_core`, because that would make clean baselines fail through geometry and clearance rather than thermal control.

### 5.4 Evaluation Shape

S4 should have a wider hard case than S3:

- repaired baseline infeasible
- cheap geometry issues zero after official projection/repair
- positive thermal constraints: two or three
- total positive thermal violation: about `5-10 K`
- first feasible point should be achievable by raw under the official budget, but it may occur later than S3

Evaluation constraints should include:

- `radiator_span_budget <= 0.37` or `<= 0.38`
- peak limits for:
  - `c02`
  - `c04`
  - `c06`
  - `c12`
  - `c17`
  - `c21`
- optionally `c16` or `c22` if the first calibration shows compute shoulders dominate
- panel spread limit

S4 should not add a long list of component limits just because there are 25 components. Too many constraints would hide optimizer behavior behind pass/fail noise.

## 6. Optimization Specs

Each benchmark should have:

- `scenarios/optimization/<id>_raw.yaml`
- `scenarios/optimization/<id>_union.yaml`
- `scenarios/optimization/<id>_llm.yaml`
- raw and union profiles under `scenarios/optimization/profiles/`

Dimension:

- S3: `c01_x/c01_y` through `c20_x/c20_y`, plus `sink_start/sink_end`
- S4: `c01_x/c01_y` through `c25_x/c25_y`, plus `sink_start/sink_end`

Mode split should mirror the active ladder:

- raw: native backbone, clean legality policy
- union: primitive registry, random controller, clean legality policy
- llm: primitive plus assisted registries, assisted legality policy

The current operator pool is mostly dimension-generic because it discovers paired `<component>_x` and `<component>_y` variables from the optimization spec. No benchmark-specific operator exception should be added for S3/S4.

## 7. Budgets

Smoke budgets:

- S3: `--population-size 20 --num-generations 10`
- S4: `--population-size 20 --num-generations 10`

Paper-facing validation budgets:

- S3: `24 x 12` or `28 x 12`
- S4: `32 x 14` or `32 x 16`

Raw, union, and llm must use matched evaluation budgets within a comparison. Different budgets between S3 and S4 are acceptable because S4 is a larger problem class.

## 8. Validation Gates

Focused implementation tests should cover:

1. Template schema loading for S3/S4.
2. `generate_case` for seed 11 returns 20/25 components and matching loads.
3. Generated case has no overlap or clearance violations.
4. Generated layout metrics land in the target occupancy bands:
   - S3: `0.52-0.55`
   - S4: `0.60-0.63`
5. Solver smoke for seed 11 converges.
6. Evaluation report contains the expected objectives and constraint ids.
7. Optimization specs load and expose 42/52 variables.
8. Variable layout resolves the final component and sink variables.
9. Cheap constraints run before PDE and geometry failures remain visible.

Smoke run gates:

- raw S3 and S4 produce at least one feasible candidate under smoke or near-smoke budget.
- union does not collapse entirely into solver-skipped geometry failures.
- llm trace contains valid controller decisions and does not depend on benchmark-specific prompt hacks.

## 9. Documentation Updates

If implemented, update:

- `README.md`
- `AGENTS.md`
- relevant docs under `docs/`

The docs should describe:

- S2 as the 15-component staged controller benchmark.
- S3 as the 20-component scale benchmark.
- S4 as the 25-component dense benchmark.
- S3/S4 occupancy targets as intentionally higher than S2.

Do not describe S3/S4 as directly comparable to S2 on density-normalized physical difficulty. Compare raw/union/llm within the same benchmark.

## 10. Non-Goals

This design does not:

- change S1/S2 contracts
- add optimized rotation
- add geometry, material, or power variables
- add multiple operating cases
- hardcode seed-specific repair or controller behavior
- manually edit generated artifacts to improve conclusions

## 11. Implementation Order

Implement S3 first.

After S3 passes schema, generation, solver, evaluation, and raw/union smoke gates, implement S4.

This order keeps calibration errors local. If S4 is implemented before S3 is stable, failures will be hard to attribute between component density, legality policy, controller selection, and solver behavior.
