# S6 Aggressive 20-Component Benchmark Design

> Status: implemented; active 20-component aggressive companion in the S5-S7 mainline.
>
> This benchmark extends the aggressive family to 20 components. It is denser than S5 and should expose whether the shared primitive pool still gives `llm` a semantic advantage when congestion, thermal load, and spatial interaction all rise together.

## 1. Goal

Create `s6_aggressive20` as a 20-component benchmark that is harder than S5 but still suitable for the same paper-facing `raw / union / llm` ladder.

The benchmark must:

- keep one operating case
- keep 20 named components
- optimize `x/y` only
- use a top-edge sink window
- keep the same two objectives
- use the shared `primitive_structured` operator pool
- stay feasible under the standard pipeline
- produce a wider and more multi-bottleneck optimization surface than S5

S6 is where we expect the stronger occupancy to make random operator selection visibly worse, while semantic structured selection remains useful.

## 2. Why This Benchmark Exists

S5 is intended to prove the new operator pool and benchmark style.

S6 is intended to test scale.

The question here is whether the controller still has room to make good semantic choices when:

- the layout is more crowded
- local congestion matters more
- component interactions become more entangled
- naive global variation becomes less reliable

If S6 is designed well, `union` should remain an honest baseline, but `llm` should get more value from structured primitives than from repeated local jitter.

## 3. Design Principles

### 3.1 Increase congestion without collapsing feasibility

S6 should feel tighter than S5, but not like a packing failure.

That means:

- more components are in play
- more of them are thermally meaningful
- clearances remain real
- the generated case is still solvable

### 3.2 Make structured moves visibly useful

The new structured primitives should matter because the case has:

- clusters that can be translated together
- compact subspaces that can be recombined
- competing local basins
- enough density that one-component jitter is often too small

### 3.3 Avoid over-constraining the benchmark

S6 should not be loaded with so many limits that success becomes a constraint-satisfaction artifact.

The benchmark should remain about thermal layout optimization, not about surviving a wall of hard rules.

## 4. Selected Template Shape

### 4.1 Template identity

- template id: `s6_aggressive20`
- component count: 20
- design variables: 42
- optimization ladder: raw / union / llm

### 4.2 Placement region

S6 should use a slightly broader but more crowded placement space than S5.

Recommended region:

- `x_min`: `0.05`
- `x_max`: `0.95`
- `y_min`: `0.04`
- `y_max`: `0.73`

This keeps the same general board style while increasing effective layout pressure.

### 4.3 Sink configuration

The sink should remain a meaningful bottleneck, but not the only interesting one.

Recommended first-pass direction:

- raw span about `0.44-0.46`
- evaluation budget around `0.36`
- sink temperature fixed near `290.5 K`
- transfer coefficient fixed near `7.5`

The sink should still matter for feasibility and peak control, but the template should also have enough internal heat pressure that sink adjustment alone cannot solve the whole problem.

### 4.4 Thermal load shape

S6 should raise the total heat load relative to S5 and distribute it across more interacting modules.

Recommended total power band:

- about `155-166 W`

This power band should create:

- one primary thermal core
- one secondary hot cluster
- at least one lateral shoulder region
- one lower-band or service-edge pressure zone

That gives the new structured primitives something to optimize beyond a single hotspot.

## 5. Component Layout Story

S6 should feel like a crowded but still readable system layout.

Recommended role structure:

- `c01-c05`: primary hot cluster and adjacent support
- `c06-c10`: secondary hot lane and buffer modules
- `c11-c15`: center-mass and routing pressure components
- `c16-c20`: lower-band, edge, and service components

The main idea is to create at least three distinct layout regimes:

1. a hot core
2. a secondary lane or shoulder
3. a routing/clearance belt where structured translation or subspace recombination matters

The layout should not degrade into pure random packing. The controller should still be able to reason about meaningful neighborhoods.

## 6. Evaluation Shape

S6 should be harder than S5 but still calibratable with the same general metrics.

Target behavior for seed 11:

- repaired baseline is thermally worse than in S5
- positive thermal violations are broader and less single-point dominated
- raw should not be trivially unbeatable
- union should remain reasonable
- llm should be able to exploit semantic structure when it chooses well

Recommended constraint shape:

- radiator span budget around `0.36`
- peak constraints for the main thermal core components
- one or two additional constraints for the secondary hot lane
- optional spread constraint if the first calibration shows the layout is too loose

The exact thresholds should be calibrated after generating the seed-11 baseline.

## 7. Operator Pool Requirement

S6 must use the same shared `primitive_structured` pool as S5.

No benchmark-specific operator ids.
No private assisted actions.
No hard filtering.
No divergence from the shared pool contract.

That shared contract is what lets us compare S5, S6, and S7 consistently.

## 8. Validation Gates

Before S6 is considered ready:

1. template schema loads
2. generated seed-11 case has 20 components
3. occupancy is higher than S5 but still legal
4. solver smoke converges
5. evaluation report exposes the intended thermal constraints
6. raw / union / llm specs map to the same decision-vector layout
7. structured operator pool is still the shared baseline pool
8. focused optimizer tests still pass

Recommended smoke budgets:

- `--population-size 10 --num-generations 5` for a quick calibration pass
- `--population-size 20 --num-generations 10` for the comparison read

## 9. Non-Goals

This benchmark does **not**:

- change the PDE model
- add rotation
- add multiple cases
- introduce assisted-only operators
- hardcode controller behavior for a specific seed
- require manual artifact edits to make the benchmark look better

## 10. Implementation Order

1. Implement and validate the shared `primitive_structured` pool.
2. Add the S6 template and evaluation spec.
3. Add raw / union / llm optimization specs and profiles.
4. Run schema, generator, and solver smoke checks.
5. Run a small raw / union / llm comparison.
6. Calibrate thresholds if needed.

S6 should be implemented after S5 is stable so we can judge whether the extra density actually helps the paper narrative.
