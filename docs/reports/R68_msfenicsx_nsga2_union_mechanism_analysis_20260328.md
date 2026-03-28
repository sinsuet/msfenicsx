# R68 msfenicsx NSGA-II Hybrid-Union Mechanism Analysis

Date: 2026-03-28

## Scope

This report is the first `LLM`-reference analysis written after the `NSGA-II` hybrid-union mechanism became stable enough to support a clean research narrative.

It is intentionally limited to the current paper-facing `NSGA-II` line:

- pure native `NSGA-II`
- union-uniform `NSGA-II`
- later union-`LLM` `NSGA-II`

It does not reopen the older removed `NSGA-II`-only operator-pool branch, and it does not treat the six-backbone union matrix as the active paper analysis target.

## Executive Conclusion

The current `NSGA-II` union mechanism is now mature enough to support the intended paper and `LLM` story.

The key reason is not that `union_uniform` is always better than raw `NSGA-II`.
The key reason is that the mechanism is now interpretable and scientifically separable:

1. pure raw `NSGA-II` remains a clean baseline
2. union mode changes the proposal or action space, not the eight-variable decision encoding
3. native-only union can be forced to collapse back to raw `NSGA-II`
4. mixed union now has a cleaner decision-level trace semantics for later controller analysis

This means the remaining problem is no longer "is the mechanism broken?".
The remaining problem is "how should actions be scheduled inside a valid mixed action space?".

That is exactly the right place for a later `LLM` controller study.

## Verified Facts And Trust Boundary

The following statements are now supported by code and fresh verification:

- `algorithm.mode: raw` and `algorithm.mode: union` are separate optimizer contracts
- raw `NSGA-II` still uses native `pymoo` `NSGA-II` variation only
- union mode keeps native `NSGA-II` parent selection and survival, and only swaps the offspring proposal layer
- the union action registry is fixed and matched across controller variants
- legality repair remains a shared post-processing step rather than being hidden inside custom operators
- native-only union reproduces raw `NSGA-II` aggregate behavior on the checked seeds

Fresh verification executed on 2026-03-28:

1. `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_operator_pool_adapters.py tests/optimizers/test_operator_pool_contracts.py tests/optimizers/test_optimizer_cli.py -v`
   Result: `46 passed`
2. `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers -v`
   Result: `81 passed`
3. `git diff --check`
   Result: clean

Important trust boundary:

- this report makes mechanism claims with high confidence
- it makes seed-level performance observations from the checked comparison artifact
- it does not claim that the current union-uniform controller is already the right scheduler

## End-To-End Runtime Chain

The actual current union chain is:

`optimization spec -> resolved algorithm config -> union driver -> genetic-family union adapter -> controller decision -> operator proposal -> shared repair -> multicase expensive evaluation -> native NSGA-II survival -> result bundle + trace sidecars`

### 1. Spec And Contract Layer

Union mode is declared explicitly in the optimization spec.
The active `NSGA-II` paper-facing union baseline is:

- `scenarios/optimization/panel_four_component_hot_cold_nsga2_union_uniform_p1.yaml`

The action registry is fixed to:

1. `native_sbx_pm`
2. `sbx_pm_global`
3. `local_refine`
4. `hot_pair_to_sink`
5. `hot_pair_separate`
6. `battery_to_warm_zone`
7. `radiator_align_hot_pair`
8. `radiator_expand`
9. `radiator_contract`

Validation rejects arbitrary registry drift, so the later `LLM` controller cannot silently gain extra actions relative to `union_uniform`.

### 2. Controller Layer

The current non-`LLM` controller is `random_uniform`.
It is intentionally algorithm-agnostic and uniform.
It does not apply hidden weights or benchmark heuristics.

This is weak by design.
Its role is not to be good.
Its role is to answer:

- what happens if we enlarge the action space but do not schedule intelligently?

### 3. Proposal Layer

The mixed union mode now has two important semantics:

- in mixed generations, one controller decision produces one proposal
- in all-native sanity runs, the exact native fast path is preserved so native-only union can still be checked against raw `NSGA-II`

This distinction matters.
Before the current tightening, native events inside mixed generations could still behave like multi-child native mating events, which made action accounting less clean.
After the tightening, mixed-mode analysis is closer to the intended controller semantics.

### 4. Repair Layer

Custom operators act only on numeric decision vectors.
They do not silently perform legality repair.

Shared repair still happens afterward through the common case repair path:

- clamp variable bounds
- repair radiator interval span
- resolve component overlaps

This keeps operator meaning and legality handling separated.

### 5. Expensive Evaluation Layer

Every repaired proposal is turned into hot and cold operating cases, solved, and evaluated with the same multicase thermal evaluation contract.
This is the expensive step.
Nothing about union mode changes the underlying physics solve, evaluation spec, or objective and constraint definitions.

### 6. Survival Layer

For the paper-facing line, union mode keeps `NSGA-II` identity at survival time.
The controller changes proposal generation only.
Selection and survival remain native `NSGA-II`.

This is important for the research narrative:

- raw vs union is not a comparison between two unrelated optimizers
- it is a comparison between the same optimizer skeleton under different proposal vocabularies

### 7. Trace Layer

Union runs write sidecar traces:

- `controller_trace.json`
- `operator_trace.json`

These sidecars stay outside `optimization_result.json`, so optimizer result contracts remain clean.

The traces are now useful for later `LLM` work because:

- mixed-mode decisions can be analyzed at proposal granularity
- `decision_index` can link controller decisions to generated proposals
- native-only sanity runs can still represent sibling offspring through a shared `decision_index`

## Why The Current Mixed Space Underperforms On Some Seeds

The first important result is negative:

- the current failure pattern is not evidence that the union mechanism is fundamentally broken

The strongest reason is the native-only sanity result.
In the checked comparison artifact:

- `union_native_only` matches raw aggregate metrics on all five analyzed seeds

This removes the most dangerous explanation:

- "union is bad because it secretly corrupted the raw `NSGA-II` backbone"

That explanation is now inconsistent with the evidence.

The more plausible explanation is narrower and more useful:

- the mixed action space is valid
- the current random scheduler is too weak for the coupled feasibility structure
- some custom operators are helpful only conditionally, not uniformly

## Seed-Level Evidence From The Current Comparison

Reference artifact:

- `scenario_runs/optimizations/comparisons/2026-03-28-nsga2-raw-vs-union-v2/summary.json`

### Seed 7

Union is clearly better than raw:

- raw feasible rate: `0.0465`
- union feasible rate: `0.1783`
- raw first feasible evaluation: `56`
- union first feasible evaluation: `34`
- raw Pareto size: `3`
- union Pareto size: `11`

Interpretation:

- the mixed action space can genuinely help
- this is not just a theoretical fairness construction

### Seed 37

Raw finds no feasible point, while union recovers feasibility:

- raw feasible rate: `0.0`
- union feasible rate: `0.0233`
- raw Pareto size: `0`
- union Pareto size: `2`
- best infeasible total violation improves from `0.0898` to `0.0060`

Interpretation:

- the custom operators can help raw `NSGA-II` escape a near-feasible trap

### Seeds 17, 27, 47

These seeds are the warning signs.
Raw has at least some feasible solutions, but union-uniform loses them.

Seed 17:

- raw feasible rate: `0.0310`
- union feasible rate: `0.0`
- best infeasible total violation worsens from `0.0049` to `0.3707`
- dominant violation frequency for `cold_battery_floor` rises from `69` to `91`

Seed 27:

- raw feasible rate: `0.0078`
- union feasible rate: `0.0`
- best infeasible total violation worsens from `0.2181` to `0.3255`
- `hot_component_spread_limit` remains dominant and worsens in frequency from `107` to `116`
- `cold_battery_floor` mean violation becomes much worse

Seed 47:

- raw feasible rate: `0.0310`
- union feasible rate: `0.0`
- best infeasible total violation improves from `0.0564` to `0.0329`
- median infeasible total violation also improves slightly
- but union still does not close the last gap into feasibility

Interpretation:

- seed 17 and seed 27 look like bad scheduling plus harmful action mixing
- seed 47 is especially important because it shows a subtler failure mode:
  union can move the population closer to the feasible frontier without consistently crossing it

That seed is likely very useful for later `LLM` controller debugging.

## Mechanistic Interpretation Of The Failures

### 1. The Custom Operators Encode Partial Physical Intuitions

The current custom operators are not random noise.
They encode directional moves such as:

- move the hot pair toward the sink
- separate the hot pair
- move the battery toward a warmer zone
- align or resize the radiator
- apply global or local vector perturbation

These are meaningful priors.
But each operator mostly captures one local intuition.
The actual feasible manifold is a coupled multicase manifold involving:

- hot processor temperature
- hot power amplifier temperature
- component spread geometry
- cold battery temperature
- radiator resource usage

So an operator can improve one pressure while worsening another.

### 2. Uniform Scheduling Ignores Constraint Context

This is the main current weakness.

When the dominant active violation is `cold_battery_floor`, not all actions are equally useful.
When the dominant active violation is `hot_component_spread_limit`, the same is true.

Uniform random selection ignores:

- which constraint family is currently dominant
- whether the current parent is near-feasible or deeply infeasible
- whether the recent effect of an operator was helpful or harmful
- whether a move should be followed by a complementary move

This means the current controller spends expensive evaluations on actions that are physically meaningful in the abstract, but mistimed for the local state.

### 3. The Search Problem Is Sequential, Not Stateless

The mixed action space behaves less like a bag of independent one-step moves and more like a staged control problem.

Typical pattern:

1. reduce one dominant violation family
2. preserve the gains already achieved
3. avoid reopening a previously solved violation family
4. only then refine objective tradeoffs

Uniform random does not represent this sequential structure.
It keeps sampling actions as if each step were independent.

### 4. Near-Feasible Regimes Need Different Behavior From Far-Infeasible Regimes

Seed 47 is the clearest signal here.
Union seems able to reduce total violation but still misses feasibility.

That suggests at least two controller regimes are needed:

- far-infeasible regime:
  more exploratory, larger corrective moves
- near-feasible regime:
  smaller, more conservative, violation-specific refinement

The current controller does not switch behavior by regime.

### 5. The Operators Are Not The Primary Problem

Based on current evidence, the most defensible conclusion is:

- the operator set is imperfect but not the main reason the current union study underperforms

Why:

- the set clearly helps on seed 7 and seed 37
- the mechanism is clean enough that raw parity still holds under native-only union
- several failure seeds show not pure chaos, but structured movement toward different violation regimes

The higher-probability problem is:

- useful operators are being activated at the wrong times, under the wrong local state, with no memory or follow-through

That is a controller problem first.

## What This Means For The LLM Layer

The `LLM` should not be asked to invent a different optimizer.
It should be asked to solve the right next problem:

- choose better actions on the same validated mixed action space

That is both fair and scientifically cleaner.

## Concrete LLM Optimization Targets

### Target 1: Dominant-Violation-Aware Action Selection

The most obvious upgrade is to condition action choice on the current violation regime.

Candidate controller inputs:

- dominant active constraints in recent history
- magnitude of current or recent total violation
- whether the parent or archive member is near-feasible
- recent action-success statistics by violation regime

Desired behavior:

- if `cold_battery_floor` dominates, prefer actions that plausibly help battery warming or preserve already-warm battery placement
- if `hot_component_spread_limit` dominates, avoid repeatedly selecting actions that likely worsen spread until the spread violation is reduced
- if hot thermal limits dominate, bias toward actions that improve hot-side cooling geometry

### Target 2: Phase-Specific Scheduling

The controller should probably learn a phased policy rather than a single stationary rule.

One plausible ladder is:

1. early phase:
   keep broader exploration, including native and global perturbation
2. middle phase:
   focus on dominant-violation reduction
3. late phase:
   use smaller or more conservative refinements near the feasible boundary

### Target 3: Action-Sequence Reasoning

Some operators are likely most useful as part of short sequences rather than as isolated choices.

Example pattern:

- move battery toward a warm zone
- then preserve that gain while adjusting hot-side geometry
- then locally refine instead of making another large disruptive move

A later `LLM` controller does not need full long-horizon planning on day one.
But it should at least reason over short recent action history and avoid destructive oscillation.

### Target 4: Near-Feasible Protection

When the search is already close to feasibility, the controller should become more conservative.

Good candidate rules for later `LLM` prompting or policy shaping:

- preserve operators that recently reduced total violation
- downweight disruptive large-step actions near feasibility
- use repaired-vector deltas and recent outcome deltas as part of the context window

### Target 5: Decision-Level Credit Assignment

The new `decision_index` trace semantics make later analysis much cleaner.

This should be used to build a joined training or analysis table with:

- decision state
- selected operator
- repaired proposal vector
- resulting objective and constraint outcome
- improvement or regression relative to parent and recent frontier

That is the right granularity for later `LLM` reflection.

## Recommended Inputs For A Future LLM Controller

The first useful `LLM` controller does not need the whole repository context.
A compact structured state should be enough.

Recommended state blocks:

1. current generation index
2. current evaluation budget remaining
3. parent decision vector
4. repaired parent or proposal summary
5. recent best feasible and near-feasible archive summaries
6. dominant recent constraint violations
7. recent operator outcomes by operator id
8. current phase label such as `explore`, `repair`, or `refine`

The `LLM` should output:

- one selected operator id from the fixed union registry

Not recommended for the first `LLM` stage:

- direct emission of new decision vectors
- changing the registry contents on the fly
- altering repair rules
- altering budget allocation or survival rules

## What The LLM Layer Should Not Change

To preserve the experiment class, the later `LLM` controller should not change:

1. the eight-variable decision encoding
2. the evaluation spec
3. the benchmark seeds
4. the shared legality repair
5. the union action registry contents
6. `NSGA-II` survival semantics
7. expensive-evaluation budget

If any of those move, the comparison stops being:

- `union_uniform` vs `union_LLM` on the same mixed action space

and becomes a different experiment.

## Practical Recommendation For The Next LLM Iteration

The next `LLM` step should not start from full free-form reasoning over everything.
It should start from a narrow controller brief:

- read a compact state summary
- identify the dominant violation regime
- choose one action from the fixed union registry
- explain the local reasoning in one short structured rationale

This is enough to test the core hypothesis:

- can a context-aware strategy layer outperform uniform random on the same mixed action space?

## Final Status

This line is now ready for `LLM`-oriented controller analysis.

What is established:

- the union mechanism is scientifically clean enough
- raw `NSGA-II` remains a valid baseline
- mixed action-space effects are real but seed-dependent
- the current main weakness is controller quality rather than baseline contamination

What the current evidence suggests:

- the mixed operator space is worth keeping
- uniform random is too weak to exploit it reliably
- the most promising next gain is state-aware action scheduling rather than immediate operator-set redesign
