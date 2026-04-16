# S1 Typical L3 LLM Controller Diversity Design

## Context

The active paper-facing ladder for `s1_typical` remains:

- `nsga2_raw`
- `nsga2_union`
- `nsga2_llm`

The comparison contract is fixed and must remain visible in both implementation and paper writing:

- all three routes optimize the same `32D` decision encoding
- all three routes use the same case template, repair, cheap constraints, PDE solve, evaluation spec, and survival semantics
- `raw` uses native `NSGA-II` proposal only
- `union` and `llm` share the same fixed mixed operator registry
- `union` and `llm` differ only by controller

The latest repaired live `llm` run is:

- `scenario_runs/s1_typical/0415_0015__llm/`

That run is now the correct evidence base for the next controller iteration because it already includes:

- restored semantic visibility in post-feasible phases
- action-conditioned prompt panels
- intent-first prompting
- retrieval-conditioned reflection
- chat-compatible live transport with forwarded `reasoning`

So the remaining blocker is no longer basic runtime viability.
The remaining blocker is controller quality under the matched paper contract.

## Validated Facts From The Current Full Run

### Runtime And Transport Facts

The current live `llm` path is operational with:

- `provider: openai-compatible`
- `base_url: https://rust.cat/v1`
- `model: gpt-5.4`
- `capability_profile: chat_compatible_json`

The completed run reports:

- `request_count = 469`
- `response_count = 469`
- `fallback_count = 0`
- `invalid_response_count = 0`
- `schema_invalid_count = 0`
- `semantic_invalid_count = 0`
- `elapsed_seconds_avg ~= 5.57`
- `elapsed_seconds_max ~= 34.39`

So the current `llm` route is not losing because of provider instability, malformed outputs, or repeated fallback.

### Outcome Facts

Matched `seed-11` aggregate outcomes are:

- `raw`
  - feasible rate `0.763671875`
  - Pareto size `5`
  - best peak `304.4342415107047`
  - best gradient `9.659754416176332`
- `union`
  - feasible rate `0.822265625`
  - Pareto size `7`
  - best peak `305.8793871745624`
  - best gradient `10.999479788598341`
- repaired full `llm`
  - feasible rate `0.806640625`
  - Pareto size `5`
  - best peak `305.4234947390854`
  - best gradient `10.814851282343104`

Current interpretation:

- `llm` is better than `raw` on feasible-set stability, but still worse than `raw` on both extreme objectives
- `llm` is better than `union` on single-point extremes, but still worse than `union` on feasible rate and Pareto width
- current `llm` is therefore improved but not yet dominant

### Physics And Realism Facts

Representative bundles under `0415_0015__llm/representatives/` remain physically credible:

- no `NaN` fields
- feasible solutions remain feasible under the official evaluation spec
- sink-span versus thermal-tradeoff behavior is physically sensible
- no sign of artifact editing or solver corruption

So the current problem is not a broken physics chain.

### Controller Behavior Facts

The repaired live controller now does use semantic actions, but it still collapses too hard:

- selected operators:
  - `local_refine: 232`
  - `native_sbx_pm: 99`
  - `global_explore: 24`
  - `move_hottest_cluster_toward_sink: 8`
  - `spread_hottest_cluster: 122`
- semantic selection rate is about `26.8%`
- `post_feasible_recover` count is `293`
- `post_feasible_expand` count is `192`

Most important observed collapse:

- in `post_feasible_expand`, `semantic_trial_mode = encourage_bounded_trial` occurs `93` times
- those `93` requests select `spread_hottest_cluster` in all `93` cases

By contrast, `union` distributes decisions across the whole mixed registry much more evenly and gets a larger Pareto set.

## Problem Statement

The repaired `llm` route is now live-runnable and scientifically credible, but it still under-realizes the intended controller-only story.

The intended paper narrative is:

- `raw -> union` isolates action-space expansion
- `union -> llm` isolates controller intelligence on the same action space

The current full `llm` run does not yet satisfy the second step strongly enough because the controller still over-concentrates decisions into a narrow route subset, especially:

- prolonged `recover`
- `expand` collapse toward `spread_hottest_cluster`
- insufficient semantic family diversity
- insufficient regime-local negative credit

## Root-Cause Diagnosis

### 1. Post-Feasible Phase Logic Is Still Too Coarse

The current controller reasons at the level of:

- `recover`
- `preserve`
- `expand`

That is better than the old generic compact prompt, but it is still too coarse for the active thermal search.

In the current state, `post_feasible_expand` often means:

- high frontier pressure
- nontrivial preservation pressure
- hotspot already inside sink corridor
- persistent local crowding

Those conditions do not uniquely imply one semantic move.
They define a small family of plausible routes.

### 2. `semantic_trial_mode` Behaves Like A Near-Hard Route Directive

The present `decision_axes` logic upgrades a valid spatial cue into a near-deterministic routing bias:

- if hotspot is already inside sink corridor
- and `spread_hottest_cluster` is in the trial set
- then `semantic_trial_mode = encourage_bounded_trial`

In practice, this becomes:

- the prompt says a bounded semantic trial is explicitly encouraged
- the candidate panel says `spread_hottest_cluster` has high applicability
- the LLM then repeatedly chooses `spread_hottest_cluster`

This is no longer only "LLM chooses from a mixed action set."
It becomes "controller-state all but pre-routes one semantic move."

### 3. Diversity Is Enforced At Visibility Level, Not At Family-Budget Level

The current `policy_kernel` correctly restored semantic visibility, but visibility alone is not enough.

The system presently guarantees only:

- semantic actions are not fully filtered out

It does not guarantee:

- semantic subfamilies receive balanced trial opportunity
- repeated low-yield routes are cooled down
- high-yield but underused routes are re-opened

So the controller solved the old starvation problem, but replaced it with a softer route-collapse problem.

### 4. Reflection Credit Is Still Too Operator-Global

Current operator reflection is much stronger than before, but it is still not motif-local enough.

What the controller really needs is short-horizon, regime-conditioned credit such as:

- under `post_feasible_expand + sink-aligned hotspot + low gap`, which family adds frontier most reliably?
- under `post_feasible_expand + full/tight sink budget`, which family improves gradient without creating regressions?
- under `recover` after recent regression, which family best stabilizes feasibility before re-expansion?

The current evidence summaries are informative, but still too coarse to regulate route allocation tightly.

### 5. Recover Exit Is Too Sticky

The repaired run spends `293` decisions in `post_feasible_recover`.

That is not a transport failure.
It is a policy-logic symptom:

- recent regression raises preservation pressure
- high preservation pressure keeps the controller in a protect-first posture
- the controller eventually expands again, but the recover window remains too long

This reduces total opportunity for diverse Pareto-shaping actions.

## Design Goals

- Preserve the controller-only comparison boundary exactly.
- Keep the same operator pool, problem, repair, evaluation, and survival semantics.
- Increase semantic route diversity without allowing uncontrolled risky expansion.
- Replace route collapse with bounded, evidence-driven route allocation.
- Shorten overlong recover behavior.
- Improve Pareto width and frontier-add rate without sacrificing the newly recovered live stability.

## Non-Goals

- Do not change the optimization problem.
- Do not add or remove operators from the official `union` / `llm` registry.
- Do not create `llm`-only operators.
- Do not retune population size, generation count, or the official paper-facing budget.
- Do not alter repair, cheap constraints, PDE solve, or survival rules.
- Do not solve the problem by benchmark-specific hardcoded prompt hacks.

## Core Design

### 1. Introduce Hierarchical Route Selection Inside The Controller

The controller should reason in two stages while still returning one final operator id:

Stage A: choose a route family

- `stable_local`
- `stable_global`
- `sink_retarget`
- `hotspot_spread`
- `congestion_relief`
- `budget_guard`
- `layout_rebalance`

Stage B: choose one concrete operator within that route family

- for example, `sink_retarget -> move_hottest_cluster_toward_sink` or `slide_sink`

This does not change the action space.
It only makes the controller's internal choice structure explicit and controllable.

### 2. Replace Semantic Visibility With Route-Budget Allocation

The controller should maintain a short-horizon route budget in post-feasible search.

The budget should regulate:

- how often each route family has been tried recently
- which route families produced frontier adds recently
- which route families produced regressions recently
- whether a route family is being overused without payoff

The key shift is:

- from "make semantic operators visible"
- to "allocate bounded expansion opportunity across semantic route families"

### 3. Upgrade Reflection From Operator Credit To Motif-Conditioned Route Credit

Credit should be indexed by compact regime keys such as:

- search phase
- sink-budget bucket
- hotspot-inside-sink boolean
- hotspot compactness bucket
- nearest-gap bucket
- frontier tradeoff direction

For each route family, the controller should aggregate:

- frontier-add yield
- preserve yield
- regression yield
- peak-temperature direction
- gradient direction

This creates a controller memory that is still compact, but far less blunt than global operator tallies.

### 4. Add Negative Evidence To Retrieval

Current retrieval is too positive-biased.

The next version should retrieve:

- strongest similar positive route evidence
- strongest similar negative route evidence

for the current regime.

The prompt should then reason over:

- what helped recently in similar states
- what failed recently in similar states

This is more consistent with reflective hyper-heuristic literature than a positive-only reminder panel.

### 5. Add Explicit Recover Exit Logic

Recover should remain conservative, but it should no longer be allowed to linger indefinitely.

The controller should exit recover when:

- recent regression count cools below threshold
- there are consecutive stable preserve outcomes
- no new dominant violation family appears

This keeps preservation-first logic, but avoids spending too much of the run in defensive mode.

## Concrete Implementation Direction

### `optimizers/operator_pool/llm_controller.py`

- add route-family construction and route-budget decision axes
- replace singleton `semantic_trial_candidates` with route baskets
- expose route-local positive and negative evidence to the prompt
- keep final output as one operator id

### `optimizers/operator_pool/policy_kernel.py`

- keep phase-aware shaping
- add bounded route-family quotas in post-feasible phases
- prevent one semantic family from monopolizing `expand` without recent payoff

### `optimizers/operator_pool/reflection.py`

- add motif-conditioned route credit summaries
- retain current operator-level summaries for diagnostics
- compute compact negative evidence summaries alongside positive ones

### `optimizers/operator_pool/state_builder.py`

- add route-budget panel
- add route-level retrieval panel
- preserve current spatial/operator applicability panel

### `optimizers/operator_pool/domain_state.py`

- derive motif buckets needed for route credit:
  - sink bucket
  - compactness bucket
  - nearest-gap bucket
  - hotspot-inside-sink bucket
  - tradeoff-direction bucket

### `optimizers/operator_pool/diagnostics.py`

- add route-family usage summaries
- add route entropy metrics
- add route-level frontier/regression counts

## Validation Plan

### Focused Tests

Add or update tests that prove:

- route families are exposed without changing the operator registry
- post-feasible expand no longer collapses to a singleton semantic trial route
- negative evidence enters retrieval summaries
- recover exit conditions are triggered correctly
- final controller decisions still resolve to valid operator ids

### Low-Budget Smoke Validation

Run a reduced-budget inline validation first to confirm:

- operator entropy increases
- route-family entropy increases
- `spread_hottest_cluster` no longer dominates `expand`
- no regression in transport stability

### Full-Budget Validation

Only after smoke success, rerun full `s1_typical_llm` with the official matched budget and compare against:

- `0413_1715__raw_union/raw`
- `0413_1715__raw_union/union`

Primary success signals:

- Pareto size improves over current `0415_0015__llm`
- feasible rate stays near current repaired `llm` or better
- route diversity approaches `union`
- best-point quality does not materially degrade

## Paper-Facing Interpretation

If this design succeeds, the paper story becomes stronger without changing the fairness boundary:

- `raw -> union` still means mixed action-space expansion
- `union -> llm` now means controller intelligence on the same mixed action set
- the new contribution is not "LLM can call semantic operators"
- the new contribution is "LLM can allocate mixed operator families adaptively under motif-conditioned feedback"

That is a defensible and better-supported claim than the current repaired `llm`, which still behaves too much like a partially collapsed route selector.
