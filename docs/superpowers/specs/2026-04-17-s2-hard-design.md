# S2 Hard Benchmark Design

> Status: approved design direction for a new paper-facing companion benchmark.
>
> `s2_hard` does not replace `s1_typical`. Both benchmarks continue to exist and
> both receive paper-facing optimizer runs. `s1_typical` remains the easy
> reference scenario. `s2_hard` is a harder companion scenario engineered
> specifically to expose the value of LLM-guided operator scheduling.

## 1. Goal

Define a second paper-facing benchmark scenario for `msfenicsx` that:

- keeps the single-case, fifteen-component, two-objective frame of `s1_typical`
- is structurally harder in a way that makes LLM scheduling's contribution
  visible in the paper's objective-function evidence, not only in feasibility rate
- produces a baseline layout that is infeasible on exactly two constraints drawn
  from **two non-overlapping operator categories**, so that state-dependent
  operator selection becomes necessary rather than optional
- shares the same shared semantic operator registry with `s1_typical` so that
  the `raw` / `union` / `llm` comparison remains an apples-to-apples ablation
  of controller behavior

`s2_hard` is added alongside `s1_typical`, not in place of it.

## 2. Why S1 Typical Is Not Enough

Budget-matched `201`-evaluation runs on `s1_typical` show:

| mode | feasible rate | best T_max | best grad_rms |
|---|---|---|---|
| union (random uniform over the full pool) | 72.1% | 306.45 K | 11.35 |
| llm (6 recent reruns) | 82–88% | 305.18–307.76 K | 10.42–12.40 |
| raw (nsga2 with sbx+pm) | 66.7% | 305.54 K | 11.85 |

The llm controller wins on feasibility rate by ~13 percentage points but its
best objective values sit inside the seed noise band of its own reruns
(~2.6 K on T_max). The controller cannot claim objective-function dominance
over the random-uniform baseline on this benchmark.

Diagnostic investigation identified three structural reasons:

- **`s1_typical` baseline is already feasible at eval 3.** All four evaluation
  constraints are slack by 10–97%. Every search phase is `post_feasible_*`.
  The llm controller's recovery-phase reasoning never activates.
- **Nine of ten operators encode thermal priors** (hottest-cluster, sink
  budget, gradient-band). A `random_uniform` selection over this pool is
  already a strong "expert bagging" ensemble. Its objective-function ceiling
  is close to the controller's.
- **The optimization window is narrow.** Baseline T_max is `311 K`; the best
  achievable is around `305 K`. The signal is approximately `6 K` against a
  seed noise of `2.6 K`.

A second, harder benchmark is required to show that LLM scheduling contributes
beyond feasibility rate.

## 3. Core Design Principle

LLM scheduling only demonstrates an objective-function advantage when the
optimal operator varies with search state. If the difficulty of the problem
is concentrated on a single axis (only cooling-starved, only high-power,
only spatially adversarial), a single expert operator is usually the correct
answer, and a random ensemble that samples that operator ~`10%` of the time
still accumulates enough correct actions over `200` evaluations to match the
controller.

`s2_hard` must therefore be **multi-dimensional in its difficulty**, not
single-axis extreme. Different operator categories must be mission-critical at
different search phases. The baseline violates two constraints drawn from two
non-overlapping operator categories so that neither category alone can finish
the optimization.

## 4. Operator-Coverage Violation Plan

`s2_hard` baseline violates exactly two constraints:

1. `radiator_span_budget`
2. `c02_peak_temperature_limit` (the highest-power component's thermal limit)

These are chosen because they can only be repaired by disjoint operator categories:

| Violated constraint | Repairing operator category | Design variables touched |
|---|---|---|
| `radiator_span_budget` | `repair_sink_budget`, `slide_sink`, parts of `rebalance_layout` | `sink_start`, `sink_end` (variables `31–32`) |
| `c02_peak_temperature_limit` | `move_hottest_cluster_toward_sink`, `spread_hottest_cluster`, parts of `reduce_local_congestion` | component `x/y` coordinates of `c02` (variables inside `1–30`) |

The two categories act on non-overlapping design variables. A controller that
selects the wrong category wastes its evaluation. A `random_uniform` controller
has roughly a `50%` chance per step of selecting the wrong category during
infeasibility.

## 5. Naming And Identity

Following `s1_typical` conventions:

- scenario template id: `s2_hard`
- template file: `scenarios/templates/s2_hard.yaml`
- evaluation spec: `scenarios/evaluation/s2_hard_eval.yaml`
- raw optimization spec: `scenarios/optimization/s2_hard_raw.yaml`
- union optimization spec: `scenarios/optimization/s2_hard_union.yaml`
- llm optimization spec: `scenarios/optimization/s2_hard_llm.yaml`
- raw profile: `scenarios/optimization/profiles/s2_hard_raw.yaml`
- union profile: `scenarios/optimization/profiles/s2_hard_union.yaml`
- run artifacts root: `scenario_runs/s2_hard/<MMDD_HHMM>__<mode_slug>/`

The scenario id is stable across `raw` / `union` / `llm` modes.

## 6. Template Changes From s1_typical

### 6.1 Physics

Only the boundary-layer heat evacuation pathway is adjusted. Materials, mesh,
and solver profile are unchanged, to keep FEniCSx solve behavior identical.

| Field | `s1_typical` | `s2_hard` |
|---|---|---|
| `boundary_feature_families[0].sink_temperature.min/max` | `286.0 K` | `293.0 K` |
| `boundary_feature_families[0].transfer_coefficient.min/max` | `10.0` | `5.0` |
| `physics.background_boundary_cooling.transfer_coefficient` | `0.15` | `0.0` |
| `physics.background_boundary_cooling.emissivity` | `0.08` | `0.02` |
| `physics.ambient_temperature` | `292.0 K` | `292.0 K` (unchanged) |
| `material_rules[*]` | unchanged | unchanged |
| `mesh_profile` | unchanged | unchanged |
| `solver_profile` | unchanged | unchanged |

Effect: the sink throat is approximately `50%` narrower and offset by `+7 K`,
and the non-sink boundary is effectively adiabatic. Heat must flow through the
sink; there is no background cooling to mask a bad placement.

### 6.2 Heat Load

Only the four `power_dense` / `sink_coupled` modules are amplified. The other
eleven components keep their `s1_typical` powers. The fifteen-component count
and component family definitions do not change.

| Component | Role | `s1_typical` power | `s2_hard` power |
|---|---|---|---|
| c02 | power_module_01 | `14.0 W` | `20.0 W` |
| c04 | power_module_02 | `13.0 W` | `19.0 W` |
| c06 | power_module_03 | `12.5 W` | `18.0 W` |
| c12 | sink_side_bus | `11.0 W` | `16.0 W` |
| other 11 components | unchanged | `63.5 W total` | `63.5 W total` |
| **Total** | | `114.0 W` | `145.0 W` (+27%) |

These four components are the natural targets for the `move_hottest_cluster`
and `spread_hottest_cluster` operators; concentrating the power bump on them
keeps the hotspot structure interpretable for the semantic operator registry.

### 6.3 Placement Hints (Layout Adversarialization)

The four amplified power-dense / sink-coupled modules are moved away from the
sink. All other placement hints are preserved.

| Component | `s1_typical` hint | `s2_hard` hint |
|---|---|---|
| c02 | `top_band` | `adversarial_core` |
| c04 | `top_band` | `adversarial_core` |
| c06 | `top_band` | `adversarial_core` |
| c12 | `top_band` | `adversarial_core` |
| c01, c03, c07 | `center_mass` | `center_mass` (unchanged) |
| c05, c10, c14 | `bottom_band` | `bottom_band` (unchanged) |
| c08, c13 | `right_edge` | `right_edge` (unchanged) |
| c09, c11 | `left_edge` | `left_edge` (unchanged) |
| c15 | `center_mass` | `center_mass` (unchanged) |

### 6.4 Layout Strategy Zones

`generation_rules.layout_strategy` is adjusted so baseline layouts form an
adversarial initial condition rather than a pre-optimized one:

| Zone | `s1_typical` | `s2_hard` |
|---|---|---|
| `kind` | `legacy_aligned_dense_core_v1` | `s2_adversarial_v1` |
| `active_deck` | `[0.12, 0.88] × [0.10, 0.67]` | `[0.08, 0.92] × [0.08, 0.68]` (slightly larger) |
| `dense_core` | present | **removed** |
| `adversarial_core` | not present | **added**: `[0.15, 0.85] × [0.10, 0.35]` — bottom half, where amplified power-dense modules are forced to land |
| `top_sink_band` | `[0.22, 0.78] × [0.56, 0.68]` | `[0.20, 0.80] × [0.55, 0.68]` (kept but now sees mostly sensors and low-power components) |
| `left_io_edge`, `right_service_edge` | present | unchanged |

`generation_rules.seed_policy` and `max_placement_attempts` are unchanged.

### 6.5 Unchanged Template Fields

To keep the ablation story clean, the following are **not** modified:

- `coordinate_system`, `panel_domain`
- `placement_regions` (`main-deck`)
- `keep_out_regions` (`top-edge-harness-strip`)
- component family count, shapes, sizes, clearances, rotation constraints,
  thermal/layout tags, `adjacency_group`
- `material_rules`, `mesh_profile`, `solver_profile`

## 7. Evaluation Spec Changes

`scenarios/evaluation/s2_hard_eval.yaml` uses the same two objectives as
`s1_typical_eval.yaml` (`minimize_peak_temperature`, `minimize_temperature_gradient_rms`)
and the following eight constraints.

| Constraint id | Metric | Relation | Limit | Baseline behavior |
|---|---|---|---|---|
| `radiator_span_budget` | `case.total_radiator_span` | `<=` | `0.32` | **violates by ~+0.06** |
| `c02_peak_temperature_limit` | `component.c02-001.temperature_max` | `<=` | `320.0` | **violates by ~+5 K** |
| `c04_peak_temperature_limit` | `component.c04-001.temperature_max` | `<=` | `330.0` | slack |
| `c06_peak_temperature_limit` | `component.c06-001.temperature_max` | `<=` | `330.0` | slack |
| `c12_peak_temperature_limit` | `component.c12-001.temperature_max` | `<=` | `330.0` | slack |
| `c01_peak_temperature_limit` | `component.c01-001.temperature_max` | `<=` | `330.0` | slack |
| `c08_peak_temperature_limit` | `component.c08-001.temperature_max` | `<=` | `330.0` | slack |
| `panel_temperature_spread_limit` | `components.max_temperature_spread` | `<=` | `35.0` | slack |

**Why six slack constraints are kept:** they remain `active` in the spec so
that (a) the controller sees rich feasibility signal during search,
(b) reflections can reason about near-miss constraints, and (c) poor
intermediate layouts that push other components across their limits are
correctly flagged as infeasible rather than accepted.

## 8. Optimization Specs

`s2_hard_raw.yaml`, `s2_hard_union.yaml`, `s2_hard_llm.yaml` are structurally
copies of their `s1_typical` counterparts with the following edits:

- `benchmark_source.template_path` → `scenarios/templates/s2_hard.yaml`
- `benchmark_source.seed` unchanged (`11`)
- `design_variables`: all `32` variable definitions kept verbatim from
  `s1_typical`. Bounds, ids, and `path` pointers are unchanged.
- `algorithm.population_size`, `num_generations`, `seed`, `backbone`, `family`,
  `mode` unchanged
- `algorithm.profile_path` → `scenarios/optimization/profiles/s2_hard_<mode>.yaml`
- `operator_control.controller` unchanged per mode
- `operator_control.operator_pool`: **identical 10-operator list** to the
  corresponding `s1_typical_<mode>.yaml`. This is the load-bearing invariant —
  any drift here invalidates the ablation.
- `operator_control.controller_parameters` for llm mode: **identical** to
  `s1_typical_llm.yaml` (same provider profile, retry, memory, reflection,
  fallback). The controller binary configuration is not tuned to `s2_hard`.
- `evaluation_protocol.evaluation_spec_path` →
  `scenarios/evaluation/s2_hard_eval.yaml`

`scenarios/optimization/profiles/s2_hard_raw.yaml` and
`scenarios/optimization/profiles/s2_hard_union.yaml` copy the algorithm
parameters from their `s1_typical` counterparts verbatim (SBX `eta=10`,
`prob=0.9`; PM `eta=15`). The tuning of the underlying NSGA-II operator
remains shared between benchmarks.

## 9. Generator Implementation Notes

The `s2_adversarial_v1` layout strategy kind does not require a schema change.
Its responsibilities:

- read the same `zones` map as `legacy_aligned_dense_core_v1`
- honor `placement_hint` values (`top_band`, `bottom_band`, `center_mass`,
  `left_edge`, `right_edge`, `adversarial_core`) already present on each
  component family
- route `top_band` placements through the `top_sink_band` zone
- route `adversarial_core` placements directly into the `adversarial_core`
  zone (used only by the four amplified power-dense / sink-coupled families
  c02 / c04 / c06 / c12)
- keep `bottom_band` placements on the derived bottom-band region for
  c05 / c10 / c14 (continuing to mirror `s1_typical` semantics); when the
  `adversarial_core` zone is also declared, `bottom_band` will prefer it as a
  fallback for scenarios that do not opt into the new explicit hint
- continue to respect `keep_out_regions`, per-component `clearance`, and the
  `max_placement_attempts` budget

The split between the new `adversarial_core` hint and the existing
`bottom_band` hint exists to avoid zone-capacity overflow: the
`adversarial_core` zone has finite area (`~0.175` in normalized panel units)
and cannot legally host all seven families in the bottom half under
per-component clearance. Routing all seven through `bottom_band` caused the
generator to overflow, spilling the later-placed amplified modules into the
full placement region and landing them near the sink — which inverts the
spec's intent that the four amplified modules occupy the adversarial zone
far from the sink to drive the `c02_peak_temperature_limit` violation. The
explicit `adversarial_core` hint narrows zone competition to exactly the
four amplified families and preserves the cross-category infeasibility
narrative.

No changes to the thermal_case schema, solver contracts, repair logic,
cheap-constraint module, evaluation runner, optimizer backbones, or trace/
analytics layers are required. All of these consume `scenario_id` as an
opaque string and operate on canonical contracts.

## 10. Expected Baseline Targets (Verification Criteria)

These are the acceptance targets for `s2_hard` baseline on `benchmark_seed=11`,
`layout_strategy=s2_adversarial_v1`:

| Quantity | `s1_typical` baseline | `s2_hard` design target | Acceptance band |
|---|---|---|---|
| `summary.temperature_max` | `311.16 K` | `~336 K` | `330–343 K` |
| `summary.temperature_span` | `11.58 K` | `~27 K` | `22–33 K` |
| `components.max_temperature_spread` | `2.77 K` | `~12 K` | `9–16 K` |
| `case.total_radiator_span` | `0.38` | `0.38` (generator default) | ≥ `0.33` (so budget binds) |
| `radiator_span_budget` violation (value−limit) | `−0.10` (feasible) | `+0.06` | `> 0` (must violate) |
| `c02-001.temperature_max` | `~311 K` | `~325 K` | `321–330 K` |
| `c02_peak_temperature_limit` violation (value−limit) | not defined | `+5 K` | `> 0` (must violate) |
| number of violated constraints | `0 / 4` | `2 / 8` | exactly `2` |
| signal / noise ratio on `T_max` | ~`2` | ~`8–10` | ≥ `6` |

If the dry-run baseline lands outside these bands, `sink_transfer_coefficient`,
`sink_temperature`, and the `power_dense` amplification factors are the
intended adjustment knobs. The eight evaluation-spec constraint values are
not tuning knobs and must not be adjusted to force the baseline into the
acceptance band — the constraints are the definition of "hard", not a
rubber-stamp.

## 11. Non-Goals

`s2_hard` does not:

- introduce additional operating cases (single operating case is still a hard
  constraint of the paper)
- add or remove components (component count remains `15`)
- modify the semantic action registry (`operator_pool`)
- modify `algorithm_config.py` backbone defaults
- modify repair, cheap-constraint, or evaluation contracts
- modify the llm controller, reflection, or memory logic
- replace `s1_typical` as the easy reference scenario
- change visualization or render-assets code paths

## 12. Known Risks And Required Verification Before Paper Claims

1. **Baseline T_max calibration.** The `145 W` total power and weakened sink
   are calibrated from first-principles intuition, not from a prior solve.
   The implementation plan must include a dry-run `solve-case` on seed `11`
   before any full optimizer run, and must adjust sink or power if the
   baseline T_max is outside `330–343 K`.

2. **200-evaluation reachability.** It is possible the combined violations
   are too severe for `200` evaluations to recover feasibility, in which case
   all modes (raw, union, llm) would show low feasibility and the comparison
   would again collapse into noise. The implementation plan must include a
   smoke run of one llm seed and one union seed, and require that llm
   reaches ≥ `70%` feasibility by eval `200` before declaring the benchmark
   usable for paper claims.

3. **Layout strategy implementation surface.** If the minimal-effort route is
   adding a `s2_adversarial_v1` branch to [layout_engine.py](core/generator/layout_engine.py),
   the change surface is expected to be under `80` lines. If a larger
   refactor is required, the plan phase should re-scope this spec before
   implementation.

4. **Operator-coverage claim is design-level, not measured.** The claim that
   `radiator_span_budget` violations require `repair_sink_budget`/`slide_sink`
   and `c02` violations require `move_hottest_cluster`/`spread_hottest_cluster`
   reflects operator design, not measured effect. The evaluation phase of
   the implementation plan must include an operator-attribution check
   (`operator_trace` ↔ `evaluation_events`) on at least one seed to confirm
   the expected attribution pattern before paper claims are written.

## 13. Paper Narrative Implication

Once `s2_hard` is validated, the paper's comparison table and discussion
should present two benchmarks side by side:

- `s1_typical` — baseline-feasible reference scenario; shows that LLM
  scheduling contributes primarily to feasibility rate when the operator
  registry already encodes strong thermal priors
- `s2_hard` — baseline-infeasible scenario with cross-category constraint
  violations; shows that LLM scheduling contributes to **both feasibility
  rate and objective values** when state-dependent operator selection is
  required

The `nsga2_union` line retains its interpretation as "shared operator pool
with random-uniform scheduling" on both benchmarks. It remains the core
ablation against `nsga2_llm`, not a weak random baseline. The paper should
describe `nsga2_union` as "expert-ensemble random scheduling" rather than
"random baseline".
