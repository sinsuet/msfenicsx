# Paper-Grade Multiobjective Thermal Baseline Design

> Status: approved direction for the next active mainline after the Phase 1 clean rebuild.
>
> This spec replaces the current toy multicase optimizer baseline. No compatibility layer is required. Obsolete baseline specs, examples, and tests may be deleted once the new path is implemented.
>
> Update on 2026-03-27: benchmark scene content, operating cases, physics scope, and evaluation targets in this document remain active. The optimizer-platform ladder originally written here as a single-backbone `NSGA-II` sequence is superseded by `docs/superpowers/specs/2026-03-27-multi-backbone-optimizer-matrix-design.md`.

## 1. Goal

Define the first paper-grade research baseline for `msfenicsx` after the Phase 1 clean rebuild:

- keep `core/` as the single-case canonical kernel
- replace the current degenerate one-component hot/cold optimizer example
- establish a realistic two-case, multiobjective, constrained satellite thermal benchmark
- make a pure `NSGA-II` reset the immediate active classical baseline and define a later multi-backbone optimizer matrix for operator-pool and controller research
- upgrade dataset generation where needed so the optimization benchmark is generated from the active platform rather than hand-carried as a toy example

This spec is a clean replacement plan, not an incremental compatibility plan.

## 2. Why the Current Baseline Must Be Replaced

The current hot/cold multicase line is a useful software checkpoint, but it is not a publishable research baseline because:

- it uses only one component
- one objective is effectively constant
- the radiator resource proxy is effectively constant
- the reference design is already feasible
- the optimization budget is too small to demonstrate convergence behavior
- the setup does not reflect the main engineering trade-off in spacecraft thermal design: hot-case cooling, cold-case survival, and finite thermal-control resources

Therefore, the current active public benchmark artifacts are migration artifacts and should not remain the long-term mainline.

## 3. Literature-Grounded Conclusions

Recent spacecraft thermal-control and satellite-layout literature points to a consistent design direction.

### 3.1 Real spacecraft thermal design is resource-constrained and multiobjective

- NASA's Small Spacecraft thermal-control guidance describes spacecraft thermal control as a balance of passive and active elements including coatings, insulation, heat pipes, radiators, and heaters, with strict temperature maintenance under changing orbital environments.
- The 2024 review "Advances in spacecraft thermal control" highlights increasingly high power density, limited available heat-rejection area, and the growing importance of integrated passive and active thermal-management design.
- The 2025 fixed-radiator optimization study shows radiator design is itself a meaningful trade-off variable: radiator optimization improved temperature uniformity by `3.09 K` to `4.98 K`, improved heat dissipation by `18.7%` to `28.8%`, and reduced mass by about one quarter under `NSGA-II`.

### 3.2 Satellite layout and thermal design should not be reduced to a single hotspot objective

- The 2025 `12U` CubeSat layout paper treats thermal management as one objective among competing engineering constraints and uses a hybrid feasibility-first plus MOEA workflow rather than a single scalar thermal target.
- The 2025 thermal-metamaterials satellite paper separates global layout optimization from local thermal shaping, which reinforces an important lesson for `msfenicsx`: first establish a strong global thermal layout benchmark before adding finer local-control mechanisms.

### 3.3 Different component roles have different thermal priorities

- The 2024 spacecraft thermal-control review summarizes typical subsystem limits such as batteries with narrow warm operating bands and power amplifiers or electronics boxes with higher hot-case limits.
- The 2025 thermal-metamaterials paper explicitly distinguishes components with diverse functional and thermal sensitivity properties.
- The 2024 and 2023 Applied Thermal Engineering papers on optical remote sensors show that payloads with strict thermal-stability requirements rapidly push the problem toward active thermal-control zoning, many-objective optimization, and expensive thermo-optical coupling.

### 3.4 A strong first baseline should stay below the active-control and optical-stability cliff

The literature supports a staged path:

1. Build a strong passive or quasi-passive multicase baseline with real thermal trade-offs.
2. Add hybrid domain operators on top of a classical MOEA.
3. Introduce LLM policy only after the classical baseline is nontrivial and stable.

For `msfenicsx`, this means the first paper-grade benchmark should use:

- hot and cold operating cases
- several named component roles with different priorities
- radiator resource as an explicit design variable
- `NSGA-II` as the first classical Pareto baseline
- custom domain operators for faster feasibility and better search efficiency

It should not yet use:

- active heater-zone optimization as the mainline
- many-objective `NSGA-III` as the primary baseline
- optical thermo-elastic stability as the mainline benchmark

## 4. Candidate Directions

Three benchmark directions were considered.

### Option A: Minimal extension of the current hot/cold toy baseline

Keep the current one-payload formulation and only increase optimization budget.

Pros:

- lowest implementation cost
- reuses nearly all current files

Cons:

- still not credible as a paper baseline
- still weakly coupled objectives
- still poor alignment with actual spacecraft thermal trade-offs

Decision: reject.

### Option B: Four-component passive thermal benchmark with hot/cold trade-off

Use a fixed set of thermally meaningful component roles on one panel, keep the current 2D steady conduction plus nonlinear radiator boundary physics, and optimize both placement and radiator geometry under hot and cold cases.

Pros:

- matches current solver physics well
- supports meaningful multiobjective trade-offs
- supports a clean `NSGA-II` plus domain-operator research story
- supports dataset generation from the rebuilt platform

Cons:

- requires generator and optimizer upgrades
- requires deleting current toy benchmark assets

Decision: select this option.

### Option C: Optical-payload or active-heater many-objective benchmark

Use optical stability zones, many heater regions, surrogate models, and many-objective optimization from the start.

Pros:

- close to advanced spacecraft thermal-control literature
- naturally motivates later LLM or surrogate strategy layers

Cons:

- overshoots the current physics and artifact maturity of `msfenicsx`
- likely forces new solver, new metrics, and new data costs too early

Decision: defer to a later phase.

## 5. Selected Baseline

## 5.1 Benchmark Identity

The new active research baseline is:

- a `2D` rectangular satellite panel benchmark
- `4` named onboard components
- `2` operating cases: `hot` and `cold`
- `3` competing objectives
- `4` thermal constraints
- hard geometry legality constraints
- `NSGA-II` as the first classical Pareto baseline
- domain-specific hybrid operators as the first strong traditional enhancement

This becomes the active mainline for `evaluation/` and `optimizers/`.

## 5.2 Scene Content

The baseline scene should contain:

- one panel domain, initially `1.0 m x 0.8 m`
- one radiator boundary feature on the top edge
- four fixed component roles:
  - `processor`
  - `rf_power_amp`
  - `obc`
  - `battery_pack`
- three effective thermal-material roles:
  - `panel_substrate`
  - `electronics_housing`
  - `battery_insulated_housing`

Rationale:

- `rf_power_amp` and `processor` create hot-case pressure
- `battery_pack` creates cold-case survival pressure
- `obc` provides background heat and coupling realism without exploding dimensionality

Optical payloads are intentionally excluded from the first paper-grade baseline because the recent remote-sensor literature shows they quickly force active zonal control and thermo-optical stability coupling that exceed the current platform scope.

## 5.3 Operating Cases

The baseline uses two operating cases derived from one shared geometric layout:

### Hot case

- high ambient condition
- weaker sink condition
- high `processor` and `rf_power_amp` power
- moderate `obc` power
- low battery self-heating

### Cold case

- low ambient condition
- colder sink condition
- lower electronics power
- battery becomes the critical survival component

The exact numeric values should be tuned during implementation so that:

- the initial reference design violates at least two thermal constraints
- feasible designs exist
- all three objectives vary meaningfully across the Pareto set

## 5.4 Physics Model

The baseline remains within the current `msfenicsx` solver envelope:

- `2D` steady conduction on a rectangular panel
- component regions as embedded conductive heat-source regions
- nonlinear radiator-style boundary sink on the panel edge
- no transient orbit propagation
- no explicit contact resistance network
- no active heater controller
- no thermo-elastic optical coupling

Mathematically, each operating case still uses:

- panel conduction
- uniform power density per component region
- boundary sink term with linear transfer coefficient
- nonlinear radiation-like term `epsilon * sigma * (T^4 - T_sink^4)`

This preserves the official FEniCSx baseline and keeps the research story focused on layout and search, not on changing physics midstream.

## 5.5 Design Variables

The first serious benchmark should use about `8` variables:

- `processor_x`
- `processor_y`
- `rf_power_amp_x`
- `rf_power_amp_y`
- `battery_pack_x`
- `battery_pack_y`
- `radiator_start`
- `radiator_end`

Notes:

- `obc` remains fixed in the first benchmark to keep the search space interpretable.
- `radiator_start` and `radiator_end` are easier to express in the current case schema than a center/span latent variable.
- a repair or projection step is required so `radiator_start < radiator_end` remains valid.

## 5.6 Objectives

The active baseline uses three objectives:

1. `minimize_hot_pa_peak`
   - metric intent: hot-case `rf_power_amp` maximum temperature
2. `maximize_cold_battery_min`
   - metric intent: cold-case `battery_pack` minimum temperature
3. `minimize_radiator_resource`
   - metric intent: total radiator span or equivalent resource proxy

This objective set is intentionally chosen because:

- all three objectives are easy to explain
- all three objectives can vary on the current solver model
- the trade-off is physically meaningful: stronger cooling tends to help hot electronics but hurts cold survivability and costs radiator resource

## 5.7 Constraints

The active thermal constraints should be:

1. hot `rf_power_amp` maximum temperature upper bound
2. hot `processor` maximum temperature upper bound
3. cold `battery_pack` minimum temperature lower bound
4. hot inter-component spread upper bound

The exact values should be set as benchmark limits rather than certification limits. They should be informed by recent spacecraft thermal-control literature but tuned for a nontrivial feasible region under the current `2D` solver.

Hard geometry legality remains outside the thermal objective system and continues to be enforced by contracts and repairs:

- within-domain
- keep-out compliance
- no overlap
- valid radiator interval

## 6. Dataset Generation Upgrade

The dataset-generation line must be upgraded so that the new benchmark is generated from the platform rather than manually patched.

## 6.1 Required Changes

### A. Replace the generic family sampler with a role-aware benchmark template

The current generator samples `1..3` generic `avionic-box` components. The new benchmark generator should instead sample one fixed role set:

- exactly one `processor`
- exactly one `rf_power_amp`
- exactly one `obc`
- exactly one `battery_pack`

Each role has its own:

- geometry range
- placement prior or allowed region
- material class
- hot and cold power profile

### B. Generate paired operating cases from one sampled layout

The active benchmark generator should produce:

- one shared layout realization
- one `hot` `thermal_case`
- one `cold` `thermal_case`

The canonical `thermal_case` object remains single-case. The pairing logic lives in generation and orchestration, not by introducing a new multicase canonical object inside `core/`.

### C. Add an explicit panel material reference

The current solver path uses the first material entry as the default panel conductivity and emissivity. This is too implicit for a paper-grade benchmark.

The clean replacement should introduce an explicit substrate reference, for example:

- `panel_material_ref` on `thermal_case`

or an equivalent unambiguous field.

This is an approved schema upgrade because the user explicitly requested a clean replacement rather than compatibility preservation.

### D. Generate an intentionally challenging reference design

The generator must support at least one deterministic baseline design that is intentionally infeasible at the start:

- hot electronics too warm
- cold battery too cold

This design becomes the standard reference point for optimizer experiments.

## 6.2 Non-Goals

The first dataset upgrade does not need to deliver:

- full field tensor export for ML training
- bulk multi-seed dataset builder for paper-scale sweeps
- LLM-specific prompt artifacts

Those can follow after the baseline benchmark is stable.

## 7. Optimizer Baseline Ladder

The optimizer ladder for this benchmark is now a multi-backbone matrix rather than a single-backbone `NSGA-II` sequence.

Implemented today:

- pure `NSGA-II` raw baseline

Approved next-stage matrix:

- `B0-matrix-raw`
  - `NSGA-II`
  - `NSGA-III`
  - `C-TAEA`
  - `RVEA`
  - constrained `MOEA/D`
  - `CMOPSO`
- `B1-matrix-pool-random`
  - the same six backbones
  - the same domain operator pool
  - the same legality repair
  - `random_uniform` controller
- `L1-matrix-pool-llm`
  - future phase only
  - same six backbones
  - same operator pool
  - only the controller changes

The design details for this matrix now live in `docs/superpowers/specs/2026-03-27-multi-backbone-optimizer-matrix-design.md`.

## 8. Domain Operator Pool

The shared operator pool for this benchmark remains numeric and benchmark-aware, but it is now explicitly algorithm-agnostic rather than tied to one backbone.

Approved shared operators:

1. `sbx_pm_global`
2. `local_refine`
3. `hot_pair_to_sink`
4. `hot_pair_separate`
5. `battery_to_warm_zone`
6. `radiator_align_hot_pair`
7. `radiator_expand`
8. `radiator_contract`

Design rules:

- operators act on numeric decision vectors
- operators are shared across the approved backbones
- legality repair remains a shared post-processing step rather than an operator
- future `LLM` work should guide this shared operator space rather than replace the optimizer or solver

## 9. Clean Replacement Scope

The following current public baseline artifacts are obsolete and should be removed or overwritten during implementation:

- current toy multicase evaluation spec
- current toy hot/cold optimization spec
- current one-component manual hot and cold cases
- tests that assert the toy one-component objective story as the active mainline
- docs that describe the current toy multicase benchmark as a paper-grade baseline

Reusable internals may stay only if they directly serve the new mainline:

- multicase evaluation contracts
- Pareto artifact protocol
- path-based decision-vector machinery where still useful
- `pymoo` integration boundary

The benchmark reset does not require preservation of obsolete example names, schema quirks, or legacy CLI examples.

## 10. Acceptance Criteria

The new baseline is acceptable only if all of the following are true:

1. The new reference design starts infeasible and violates at least two thermal constraints.
2. The three objectives all vary over the optimization run.
3. Raw and pool experiment variants both run on the same benchmark and matched evaluation budgets.
4. Pool-random and later pool-LLM comparisons differ only by controller choice on the same operator pool.
5. The new generator can create paired hot/cold cases from the active benchmark template.
6. The old toy multicase baseline is no longer presented as the active research path anywhere in docs or scenarios.

## 11. Implementation Guidance

Implementation should follow these boundary rules:

- keep `core/` as the canonical single-case kernel
- allow core schema and generator upgrades when they directly support the new benchmark
- keep objective and constraint logic in `evaluation/`
- keep optimizer search-space and operator logic in `optimizers/`
- do not reintroduce old demo architecture
- do not add LLM strategy code in this phase

The next step after this spec is a concrete implementation plan that deletes the old toy benchmark path and replaces it with the new multicase benchmark line.

## 12. References

- NASA Small Spacecraft Systems Virtual Institute, "Thermal Control," official Small Spacecraft state-of-the-art resource: <https://www.nasa.gov/smallsat-institute/sst-soa/thermal-control>
- Consolo, G. and Boetcher, S. K., "Advances in spacecraft thermal control," *Aerospace*, 2024 review page: <https://www.mdpi.com/2226-4310/11/10/803>
- Wang et al., "Optimization strategy of active thermal control based on Kriging metamodel and many-objective evolutionary algorithm for spaceborne optical remote sensors," *Applied Thermal Engineering*, 2024: <https://www.sciencedirect.com/science/article/abs/pii/S1359431124001625>
- Wang et al., "Reduction and reconstruction strategy of active thermal control system based on unsupervised learning and thermo-optics for spaceborne high-resolution remote sensor," *Applied Thermal Engineering*, 2023: <https://www.sciencedirect.com/science/article/abs/pii/S1359431123007056>
- Li et al., "A satellite layout-structure integrated optimization method based on thermal metamaterials," *Chinese Journal of Aeronautics*, 2025: <https://www.sciencedirect.com/science/article/pii/S1000936125004480>
- Zhang et al., "Engineering-Oriented Layout Optimization and Trade-Off Design of a 12U CubeSat with In-Orbit Validation," *Aerospace*, 2025: <https://www.mdpi.com/2226-4310/12/6/506>
- Wang et al., "Optimization of Fixed Honeycomb Panel Radiator Based on NSGA-II Algorithm," *Chinese Journal of Space Science*, 2025: <https://www.cjss.ac.cn/en/article/doi/10.11728/cjss2025.06.2024-0177>
