# S1 Typical Mainline Reset Design

> Status: historical S1 reset design; superseded as active paper-facing mainline by the S5-S7 aggressive family.
>
> This spec replaces the current four-component hot/cold mainline completely. No compatibility layer is required. Old scenarios, optimizer specs, experiment outputs, figures, docs, and tests that only serve the previous mainline should be removed once `s1_typical` is implemented and validated.

## 1. Goal

Define the next active research mainline for `msfenicsx` as a single-case, fifteen-component, two-objective thermal layout problem that:

- uses one operating condition instead of hot/cold paired cases
- optimizes peak temperature and full-field thermal-gradient RMS together
- treats radiator-window usage as a hard resource constraint instead of a third objective
- uses `15` movable components with `x/y` placement variables only
- becomes the shared problem definition for `nsga2_raw`, `nsga2_union`, and `nsga2_llm`
- fully retires the previous paper-facing four-component hot/cold line

This is a mainline reset, not a partial migration.

## 2. Why The Current Mainline Must Be Replaced

The current paper-facing line is no longer aligned with the approved research question because it is built around:

- paired `hot/cold` operating cases
- a four-component scene
- a three-objective story where radiator span is minimized directly
- union and LLM actions specialized to a four-component hot-pair layout

The approved next question is different:

- single operating case
- `15` components
- objective trade-off between peak temperature and whole-field temperature-gradient smoothness
- radiator usage limited by a hard budget rather than optimized as an explicit resource objective

Therefore the old line should not remain as an active supported baseline.

## 3. Naming And Identity

The new mainline should use short stable names.

Selected naming:

- scenario template id: `s1_typical`
- template file: `scenarios/templates/s1_typical.yaml`
- evaluation spec: `scenarios/evaluation/s1_typical_eval.yaml`
- raw optimization spec: `scenarios/optimization/s1_typical_raw.yaml`
- union-uniform optimization spec: `scenarios/optimization/s1_typical_union.yaml`
- union-llm optimization spec: `scenarios/optimization/s1_typical_llm.yaml`
- raw profile: `scenarios/optimization/profiles/s1_typical_raw.yaml`
- union profile: `scenarios/optimization/profiles/s1_typical_union.yaml`

Rationale:

- short names reduce clutter in experiment paths and reports
- the same scene id can remain stable across all three official modes
- `s1_typical` is easier to discuss than a long descriptive benchmark name

## 4. Selected Design Direction

Three directions were considered.

### Option A: Keep the current mainline and patch it

Keep the four-component hot/cold structure and reinterpret it as single-case where possible.

Pros:

- lowest short-term implementation cost

Cons:

- leaves the wrong scientific framing in the repository
- preserves multicase-first optimizer assumptions
- keeps old scene-specific controller logic alive

Decision: reject.

### Option B: Add `s1_typical` beside the old line

Introduce a clean new benchmark but keep the old paper-facing line in parallel.

Pros:

- lower migration risk
- easier short-term comparison against old experiments

Cons:

- creates dual-mainline ambiguity
- increases accidental misuse risk
- keeps obsolete docs, outputs, and controller semantics in circulation

Decision: reject.

### Option C: Full mainline reset around `s1_typical`

Replace the old line with a new single-case fifteen-component problem and rebuild raw, union, and llm around the same new contract.

Pros:

- matches the approved research question exactly
- removes ambiguity about which line is active
- gives the optimizer, repair, and controller layers one consistent problem definition

Cons:

- requires broader coordinated implementation
- requires deliberate cleanup of old code and docs

Decision: select this option.

## 5. Benchmark Identity

At the time of this reset, `s1_typical` became the only active paper-facing benchmark.

Its defining properties are:

- one rectangular panel domain
- one active operating case
- `15` named components
- one top-edge radiator window with adjustable span and position
- two optimization objectives
- hard geometry legality constraints
- a hard radiator-span budget constraint
- `NSGA-II` raw as the first validation rung
- union-uniform and union-llm as controller-guided extensions of the same exact problem

The benchmark should remain within the current steady 2D conduction plus nonlinear radiator-boundary solver envelope.

## 6. Physics Scope

The mainline remains inside the current physics contract:

- `2D` steady conduction on a rectangular panel
- component regions embedded in the panel
- distributed heat loads over component regions
- one radiator-style boundary sink on the panel edge
- linear transfer coefficient plus nonlinear radiation-style sink term
- no transient orbit propagation
- no active heater control
- no thermo-elastic optical coupling

This keeps the solver scope stable while changing the optimization question.

## 7. Single-Case Contract

The new mainline is single-case by design.

Selected direction:

- `s1_typical` should not define `operating_case_profiles`
- generation should use the single-case path rather than paired-case generation
- evaluation should use `EvaluationSpec` / `EvaluationReport` as the official mainline contracts
- optimizer drivers, artifacts, experiment summaries, and dashboards should become single-case first

Implication:

- old multicase-first optimizer assumptions should be removed rather than preserved behind compatibility wrappers

## 8. Component Model

The benchmark should contain `15` fixed named components.

Requirements:

- each component has a fixed `component_id`
- each component has fixed material and fixed nominal power assignment for the single operating case
- each component may have its own geometry range in the template
- each component may carry group tags for controller and analysis use, such as:
  - high-power
  - thermally sensitive
  - moderate-coupling

Selected control rule:

- all `15` components are optimization-active in position
- all `15` components expose `x` and `y`
- no component exposes `rotation_deg` as an optimization variable
- no component exposes geometry, material, or power as an optimization variable

This makes the mainline a pure layout problem instead of a mixed layout-and-design-physics problem.

## 9. Decision Encoding

The `s1_typical` decision vector should contain:

- `c01_x`, `c01_y`
- `c02_x`, `c02_y`
- `c03_x`, `c03_y`
- `c04_x`, `c04_y`
- `c05_x`, `c05_y`
- `c06_x`, `c06_y`
- `c07_x`, `c07_y`
- `c08_x`, `c08_y`
- `c09_x`, `c09_y`
- `c10_x`, `c10_y`
- `c11_x`, `c11_y`
- `c12_x`, `c12_y`
- `c13_x`, `c13_y`
- `c14_x`, `c14_y`
- `c15_x`, `c15_y`
- `sink_start`, `sink_end`

Total dimension:

- `15 * 2 + 2 = 32`

Rules:

- variable ordering must be fixed and stable across raw, union, and llm
- encoding must not depend on role-name lookup
- component ids and vector slots should stay one-to-one

## 10. Objectives

`s1_typical` uses exactly two optimization objectives.

### 10.1 Objective 1: Peak temperature

Selected metric:

- `summary.temperature_max`

Objective:

- `minimize_peak_temperature`

Interpretation:

- minimize the hottest temperature reached anywhere on the panel

### 10.2 Objective 2: Thermal-gradient RMS

Selected metric:

- `summary.temperature_gradient_rms`

Objective:

- `minimize_temperature_gradient_rms`

Selected formal definition:

`temperature_gradient_rms = sqrt((1 / |Omega|) * integral_Omega |grad(T_h)|^2 dx)`

where:

- `T_h` is the FEniCSx finite-element temperature solution
- `Omega` is the full panel domain
- `|Omega|` is the panel area

Selected implementation rule:

- compute this value directly from the finite-element field using UFL/DOLFINx domain integration
- do not compute it from hand-written node-wise finite differences
- store it in `thermal_solution.summary_metrics`

Selected exclusions:

- do not use `max(|grad(T)|)` as the official mainline objective
- do not use component temperature spread as the official mainline objective
- do not use recovered-gradient or proxy-gradient metrics as the official mainline objective

Selected stability rule:

- mainline experiments should keep a fixed `mesh_profile`
- mesh-sensitivity checks may be added later as validation, but the mainline objective definition itself does not change with mesh

## 11. Constraints

`s1_typical` should use hard constraints only for conditions that must not be violated.

### 11.1 Geometry legality constraints

Required hard constraints:

- no component overlap
- no keep-out intrusion
- no outside-domain placement

These should remain optimizer-layer legality requirements, not user-facing evaluation objectives.

### 11.2 Radiator-span budget

Selected hard constraint:

- `case.total_radiator_span <= radiator_span_max`

Interpretation:

- radiator usage remains adjustable
- the span may move and resize
- the total span must not exceed the approved budget

This is explicitly not:

- a fixed-span equality requirement
- a soft preference for smaller span
- a third optimization objective

### 11.3 Thermal safety constraints

The evaluation spec should also include a small set of benchmark-appropriate hard thermal limits.

Examples:

- selected component temperature ceilings for sensitive electronics
- any scene-specific safety bound the final benchmark requires

These bounds should be written against explicit `component_id` metrics or explicit aggregate metrics, not against ambiguous repeated roles.

## 12. Cheap Constraints Before PDE

The optimizer should separate cheap legality checks from expensive PDE solves.

Selected runtime sequence:

1. decode decision vector
2. apply repair
3. evaluate cheap constraints
4. if cheap constraints remain violated, record infeasible result and skip PDE solve
5. only solve the thermal field for cheap-constraint-feasible candidates

Required cheap-constraint signals:

- overlap violation
- keep-out violation
- outside-domain violation
- radiator-budget violation

Recommended normalized forms:

- overlap area over panel area
- keep-out intrusion area over panel area
- outside-domain area over panel area
- `max(0, span - span_max) / span_max`

Rationale:

- reduces wasted expensive evaluations
- gives raw and controller-guided modes better feasibility signals
- makes dominant failure modes visible in telemetry and reports

## 13. Repair Architecture

The repair layer must be upgraded for `32`-dimensional placement optimization.

Selected design:

- move from small-scene nudging to a two-stage repair path

### 13.1 Stage A: Projection

Repair should first project the proposal into obvious bound-safe regions:

- clamp all `x/y` variables to their declared bounds
- enforce valid sink interval ordering
- project radiator span into `span <= span_max`

### 13.2 Stage B: Local legality restoration

Repair should then resolve remaining geometric conflicts using:

- local separation for mild collisions
- targeted local re-placement for the most conflicted components

Selected principle:

- prioritize minimum-change legality restoration
- if repeated pairwise nudging stalls, re-place a small number of worst offenders instead of endlessly perturbing all components

This repair path should remain deterministic for a given candidate and seed.

## 14. Raw Baseline Strategy

The first implementation rung should be:

- `NSGA-II` raw

Selected requirements:

- feasible-first initial population around a legal reference layout
- a controlled mix of local perturbations and broader exploratory samples
- no controller-specific assumptions in the raw path

The raw rung is the validation gate for the new mainline. Union and llm should not be treated as complete until raw is working and producing interpretable Pareto trade-offs.

## 15. Union And LLM Redesign

The current union and llm action spaces are too specialized to the old four-component hot/cold scene and must be retired.

### 15.1 What must be removed

Remove actions and logic whose semantics depend on old scene-specific stories such as:

- fixed hot-pair assumptions
- battery-specific relocation heuristics tied to the old benchmark
- radiator alignment rules defined around one special pair of components

### 15.2 New action-registry principle

The new registry should be semantic and portable.

Selected action-family direction:

- `native_sbx_pm`
- `global_explore`
- `local_refine`
- `move_hottest_cluster_toward_sink`
- `spread_hottest_cluster`
- `smooth_high_gradient_band`
- `reduce_local_congestion`
- `repair_sink_budget`
- `slide_sink`
- `rebalance_layout`

Action rule:

- operator names express intent
- operator internals auto-select affected components or regions from the current domain state
- operators must not hardcode benchmark-specific component names in their core logic

### 15.3 Controller-state principle

The compact controller state should shift from old hot/cold role summaries to the new mainline signals:

- peak temperature
- temperature-gradient RMS
- total constraint violation
- dominant constraint family
- sink budget utilization
- top hotspot components or groups
- high-gradient-region summary
- congestion-cluster summary
- recent operator-family credit

### 15.4 LLM decision role

The LLM controller should choose among a small semantic action set rather than emit direct geometry edits.

Selected rule:

- the LLM selects a strategy family from the approved operator registry
- operator code then applies that strategy to automatically selected targets

This keeps controller reasoning portable while reducing brittle scene scripting.

## 16. Artifacts And Experiment Layout

The experiment root convention may remain template-first:

- `scenario_runs/s1_typical/experiments/<mode>__<timestamp>/`

The active modes remain:

- `nsga2_raw`
- `nsga2_union`
- `nsga2_llm`

However, representative artifacts should become single-case oriented:

- one case snapshot per representative
- one solution snapshot per representative
- one single-case evaluation report per representative

Experiment summaries and dashboards should stop assuming multicase fields such as separate hot/cold case reports.

## 17. Deletion Policy

After `s1_typical` is implemented and validated, the repository should remove obsolete assets rather than preserve them for compatibility.

Remove:

- previous four-component hot/cold templates
- previous evaluation specs and optimizer specs for that line
- previous profiles tied only to that line
- old experiment outputs, figures, and dashboard assets tied only to that line
- old paper-facing docs that describe the retired mainline as active reality
- old tests whose only purpose is to enforce the retired line
- old union and llm operators that depend on the retired scene

Do not keep:

- shadow compatibility wrappers
- alternate active mainlines
- legacy figures or outputs that may confuse future runs

## 18. Validation Plan

Implementation should validate the new mainline in three stages.

### 18.1 Contract validation

- template validation passes
- single-case generation succeeds
- solve succeeds
- `thermal_solution` includes `temperature_gradient_rms`
- single-case evaluation report computes both objectives and hard constraints correctly

### 18.2 Raw validation

- `s1_typical_raw` completes end to end
- feasible layouts exist under the selected span budget
- Pareto trade-offs appear between peak temperature and gradient RMS
- cheap-constraint skipping works correctly

### 18.3 Controller validation

- `s1_typical_union` runs using the new semantic operators
- `s1_typical_llm` runs using the same action registry
- controller diagnostics expose feasibility, congestion, sink-budget, and gradient signals clearly

## 19. Implementation Sequence

Implementation should proceed in this order:

1. create the new `s1_typical` template and single-case evaluation spec
2. add `temperature_gradient_rms` to solver-side solution generation
3. refactor the optimizer path to become single-case first
4. implement cheap constraints and upgraded repair
5. implement and validate `s1_typical_raw`
6. replace the old union operator registry with the new semantic registry
7. implement and validate `s1_typical_union`
8. implement and validate `s1_typical_llm`
9. remove obsolete old-mainline code, docs, tests, outputs, and assets

## 20. Final Approved Decisions

The following decisions are fixed for the `s1_typical` mainline:

- the repository keeps only one active paper-facing mainline: `s1_typical`
- the mainline is single-case, not hot/cold multicase
- the benchmark contains `15` components
- all `15` components optimize `x/y`
- no component uses optimized rotation
- the decision vector has `32` dimensions
- the objectives are peak temperature and whole-domain gradient RMS
- the formal gradient algorithm is the area-normalized finite-element gradient RMS over the full panel domain
- radiator usage is a hard span-budget constraint, not an objective
- cheap legality checks must run before expensive PDE solves
- repair must be upgraded to projection plus local legality restoration
- union and llm must use a new semantic, portable action registry instead of the old four-component scene logic
