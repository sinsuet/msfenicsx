# S5 Aggressive 15-Component Benchmark Design

> Status: approved design direction; not implemented yet.
>
> This benchmark is the first aggressive paper-facing benchmark that will use the shared `primitive_structured` pool. It is intentionally more spacious and more thermally demanding than `s2_staged`, so `raw` weakens, `union` remains meaningful, and `llm` has room to win through better semantic operator choice.

## 1. Goal

Create a new 15-component benchmark, `s5_aggressive15`, that is harder and more multi-bottleneck than `s2_staged` while remaining a clean single-case thermal layout optimization problem.

The benchmark must:

- keep one operating case
- keep 15 named components
- optimize `x/y` only
- keep one movable top-edge sink window
- use the same two paper-facing objectives
  - `summary.temperature_max`
  - `summary.temperature_gradient_rms`
- use the shared `primitive_structured` operator pool for `union` and `llm`
- preserve the fair `raw / union / llm` ladder
- make the optimization space larger than S2 so the native baseline does not dominate trivially

This benchmark is the first one where we want the aggressive narrative to show up clearly in the data.

## 2. Why This Benchmark Exists

The S2 template ended up too narrow:

- the sink budget bottleneck dominated too much of the search story
- the overall temperature/gradient improvement band was too small
- raw was already too competitive against the calibrated `llm` line
- the current primitive pool was not enough to open a stronger Pareto shape

S5 should change that by increasing thermal load, layout slack, and interaction complexity at the same time.

## 3. Design Principles

### 3.1 Make the improvement band wider

The initial layout should be significantly farther from the best feasible layouts than in S2.

Target behavior:

- initial projected baseline remains thermally worse than the best search results by a visibly larger margin
- the raw search needs more room to improve
- the `llm` controller can exploit structured primitives rather than just local jitter or sink adjustment

### 3.2 Keep the benchmark feasible

The benchmark must be hard, not pathological.

That means:

- no impossible packing
- no dead-end clearance geometry
- no requirement for assisted-only macros to obtain any feasible point
- no benchmark-specific operator exceptions

### 3.3 Force more than one bottleneck

S5 should create at least two meaningful pressure zones so that different operators have distinct roles.

Desired pressure structure:

- one primary hot core
- one secondary hot shoulder or lane
- one routing/spacing pressure near the sink band
- one lower-band congestion pressure that rewards structured local moves

## 4. Selected Template Shape

### 4.1 Template identity

- template id: `s5_aggressive15`
- component count: 15
- design variables: 32
- objective set: same as S1/S2
- optimization ladder: raw / union / llm

### 4.2 Layout region

The placement region should be slightly larger and more permissive than S2, while still leaving enough structure for thermal competition.

Recommended region:

- `x_min`: `0.05`
- `x_max`: `0.95`
- `y_min`: `0.04`
- `y_max`: `0.72`

This is still a single-case layout, not a broader envelope model.

### 4.3 Sink configuration

The sink should remain a top-edge line sink, but with a wider raw span and a stricter budget tension than S2.

Recommended direction:

- raw span should start wider than the evaluation budget
- projected sink should still remain meaningful after legality handling
- the sink should no longer be the only dominant search bottleneck

Suggested values for the first implementation pass:

- raw span about `0.42-0.44`
- evaluation budget about `0.34-0.35`
- sink temperature fixed near `290.5 K`
- transfer coefficient fixed near `7.5`

### 4.4 Thermal load shape

S5 should have a stronger total load and a more uneven heat distribution than S2.

Recommended total power band:

- about `138-146 W`

The load distribution should include:

- one very hot core component near the adversarial core region
- two medium-hot support components
- several cooler routing/support components so the controller still has room to improve layout diversity

The heat map should make the raw baseline visibly worse than in S2, but not so extreme that the PDE becomes numerically unstable.

## 5. Component Layout Story

The 15 components should be arranged to create a more aggressive and less symmetric thermal landscape than S2.

Recommended roles:

- `c01-c04`: strong core cluster with one dominant hot module
- `c05-c08`: shoulder or buffer modules that can either relieve or amplify the hot core
- `c09-c12`: edge and lane modules that create routing and congestion pressure
- `c13-c15`: lower-band / auxiliary modules that give structured primitives a reason to act

The template should avoid the old “single rescue point” feeling. The controller should face a layout where a reasonable move may improve one objective while worsening the other unless it is chosen semantically well.

## 6. Evaluation Shape

S5 should still be solvable under the standard pipeline, but the repaired baseline should be materially worse than the best discovered points.

Target evaluation behavior for seed 11:

- repaired baseline is feasible or near-feasible on geometry
- thermal constraints expose multiple positive violations
- first feasible point appears later than in S2 or at least with a broader search trail
- `raw` does not trivially dominate the benchmark
- `union` remains a useful mixed-primitive baseline
- `llm` has room to improve by choosing structured primitives better than random selection

Recommended constraint shape:

- radiator span budget around `0.34-0.35`
- 3-5 thermal constraints across the hottest components
- one spread or balance constraint if needed, but not a long constraint list

The exact numeric thresholds should be calibrated from the generated seed-11 baseline, not guessed too rigidly in advance.

## 7. Operator Pool Requirement

S5 must use the shared `primitive_structured` pool.

That means:

- `union` and `llm` must see the same shared primitive support
- the benchmark does not get private operator ids
- the benchmark does not add assisted-only actions
- the benchmark does not add hard filtering

The point is to make structured primitives more useful, not to make the controller cheat.

## 8. Validation Gates

Before the benchmark is treated as ready, validate:

1. template schema loads
2. generated seed-11 case has 15 components and the right sink geometry
3. occupancy and total power land in the aggressive band
4. solver smoke converges
5. evaluation report shows the expected objectives and constraints
6. raw / union / llm specs resolve the same design-variable layout
7. `primitive_structured` is the shared registry profile for the baseline comparison
8. focused optimizer tests still pass after the operator-pool change

Recommended smoke validation budgets:

- `--population-size 10 --num-generations 5` for fast smoke
- `--population-size 20 --num-generations 10` for the first meaningful benchmark read

## 9. Non-Goals

This benchmark does **not**:

- add optimized rotation
- add multiple cases
- change the thermal PDE model
- introduce benchmark-specific controller hacks
- require assisted-only operators to reach feasibility
- change the fair comparison contract between `raw`, `union`, and `llm`

## 10. Implementation Order

1. Implement the shared `primitive_structured` pool.
2. Add `s5_aggressive15` template and evaluation spec.
3. Add raw / union / llm optimization specs and profiles.
4. Run schema, generator, and solver smoke checks.
5. Run a small raw / union / llm smoke comparison.
6. Calibrate constraints if the baseline is either too easy or too pathological.

S6 and S7 should only be implemented after S5 has passed the first calibration loop.
