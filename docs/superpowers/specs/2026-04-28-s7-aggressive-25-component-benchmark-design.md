# S7 Aggressive 25-Component Benchmark Design

> Status: implemented; active 25-component dense aggressive companion in the S5-S7 mainline.
>
> This benchmark is the 25-component aggressive case in the S5/S6/S7 family. It should test whether the shared structured primitive pool and LLM controller remain useful when the layout becomes dense enough that naive full-vector variation and random primitive choice are both stressed.

## 1. Goal

Create `s7_aggressive25` as the high-density aggressive benchmark for the paper-facing optimizer ladder.

The benchmark must:

- keep one operating case
- keep 25 named components
- optimize `x/y` only
- use one movable top-edge sink window
- keep the same objectives
- use the shared `primitive_structured` pool for `union` and `llm`
- expose higher-dimensional and denser layout pressure than S5/S6
- remain feasible enough for matched raw / union / llm comparisons

S7 is not just “S6 plus five parts”. It should be the scalability and density stress case for the shared-pool controller story.

## 2. Why This Benchmark Exists

S7 exists to test the strongest version of the thesis:

- raw full-vector SBX/PM should become less reliable as the dense layout interaction grows
- random selection over the same pool should remain noisy
- LLM selection should benefit from semantic state, operator intent, and structured primitive choice

The benchmark should make the operator-selection story more visible without giving `llm` a private pool or hidden repair advantage.

## 3. Design Principles

### 3.1 Density should create meaningful interaction

S7 should have high occupancy, but not impossible geometry.

The extra components should create:

- cluster interactions
- local bottlenecks
- secondary thermal lanes
- edge routing pressure
- more cases where moving a block or recombining a subspace is better than one-component jitter

### 3.2 Feasibility must remain observable

The benchmark should not skip most PDE solves because of geometry failure.

If S7 becomes a geometry-only test, it no longer helps the paper narrative. Geometry and clearance should matter, but thermal objectives must remain the main story.

### 3.3 The comparison must stay matched

S7 must use matched budgets and matched operator support inside each raw / union / llm comparison.

The only controller difference should remain:

- `raw`: native backbone
- `union`: random selection over the shared primitive pool
- `llm`: semantic selection over the same shared primitive pool

## 4. Selected Template Shape

### 4.1 Template identity

- template id: `s7_aggressive25`
- component count: 25
- design variables: 52
- optimization ladder: raw / union / llm

### 4.2 Placement region

S7 should use a high-occupancy region without making the solver or generator brittle.

Recommended region:

- `x_min`: `0.04`
- `x_max`: `0.96`
- `y_min`: `0.04`
- `y_max`: `0.74`

This gives enough board area to place 25 components while still making the problem dense.

### 4.3 Sink configuration

The sink should remain a top-edge staged resource.

Recommended first-pass direction:

- raw span about `0.46-0.48`
- evaluation budget around `0.37-0.38`
- fixed sink temperature near `290.5 K`
- fixed transfer coefficient near `7.5`

The sink should be important but insufficient on its own. The best solutions should need both sink alignment and component-structure moves.

### 4.4 Thermal load shape

S7 should be the strongest aggressive load case.

Recommended total power band:

- about `176-190 W`

The load distribution should include:

- a primary high-power core
- a secondary high-power lane
- at least one high-power shoulder near center mass
- several medium-power support modules
- lower-power edge/service modules that still influence spacing and gradients

S7 should not simply assign high power to every component. That would remove the need for semantic selection.

## 5. Component Layout Story

S7 should create four recognizable layout regimes:

1. primary hot core
2. secondary hot lane
3. dense center/service shoulder
4. lower or edge routing belt

Recommended role bands:

- `c01-c06`: primary hot core and immediate shields
- `c07-c12`: secondary hot lane
- `c13-c18`: center-mass support and medium-power routing pressure
- `c19-c25`: edge, bus, service, and lower-band components

This structure gives `component_block_translate_2_4` and `component_subspace_sbx` clear opportunities without making them benchmark-specific.

## 6. Evaluation Shape

S7 should be hard enough that a 10x5 smoke may only be a sanity check, not a final performance read.

Target behavior for seed 11:

- baseline has multiple thermal violations
- solver converges reliably for legal layouts
- cheap geometry failures remain visible but do not dominate all proposals
- first feasible point is reachable under a moderate budget
- `llm` can plausibly beat `raw` and `union` by coordinating structured primitive choices

Recommended constraints:

- radiator span budget around `0.37-0.38`
- peak constraints for primary core modules
- peak constraints for one or two secondary-lane modules
- optional spread constraint if the first calibration shows thermal imbalance is too loose

Do not overfit constraints to force a predetermined winner. The thresholds should be calibrated to create an informative search problem, not to manufacture a result.

## 7. Operator Pool Requirement

S7 must use the same shared `primitive_structured` pool as S5 and S6.

That means:

- same registry profile
- same candidate ids
- same legality policy family inside matched comparisons
- no S7-specific controller wording
- no private LLM operator

S7 should stress the shared-pool story rather than changing the rules.

## 8. Validation Gates

Before S7 is considered ready:

1. template schema loads
2. generated seed-11 case has 25 components
3. generated layout is legal and solver-compatible
4. total power and occupancy land in the aggressive range
5. evaluation report shows multiple meaningful thermal constraints
6. optimization specs expose 52 variables
7. union and llm share the `primitive_structured` pool
8. focused tests pass
9. at least one smoke comparison completes without trace/artifact failures

Recommended budgets:

- quick smoke: `--population-size 10 --num-generations 5`
- first comparison read: `--population-size 20 --num-generations 10`
- later paper-facing read: likely larger than S5/S6 after calibration

## 9. Non-Goals

This benchmark does **not**:

- add rotation
- add additional sink windows
- add multiple operating cases
- make S7 directly comparable to S5/S6 by absolute hypervolume
- hide infeasibility or manually clean generated artifacts
- add special controller hacks for a 25-component case

## 10. Implementation Order

1. Validate `primitive_structured` on S5/S6 first.
2. Add the S7 template and evaluation spec.
3. Add raw / union / llm optimization specs and profiles.
4. Run schema and generator checks.
5. Run solver and evaluation smoke checks.
6. Run a small raw / union / llm smoke comparison.
7. Calibrate constraints only if the benchmark is too easy, too brittle, or geometry-dominated.

S7 should be implemented after S5 and S6 so failures can be attributed to density rather than to unresolved shared-pool or calibration problems.
