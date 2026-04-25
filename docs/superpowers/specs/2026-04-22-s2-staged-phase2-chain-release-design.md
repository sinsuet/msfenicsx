# S2 Staged Phase-2 Chain Release Design

> Status: active continuation design for the paper-facing `s2_staged` controller
> line.
>
> Workspace policy for this cycle: continue directly on `main`; do not create a
> new worktree.

## 1. Decision Summary

The next repair cycle should not restart the benchmark redesign. The current
`s2_staged` route is already exposing useful controller-sensitive signal, and
the shared operator registry is still the correct fairness boundary.

The phase-2 repair target is narrower and more structural:

1. keep the already-repaired `prefeasible_convert` route-family surface intact
2. stop losing current positive retrieval matches when they are compressed into
   mixed-sign family aggregates
3. make `recover` releasable under bounded regression instead of waiting for an
   unrealistically clean low-pressure window
4. make `expand` reachable before the front is already broad enough that expand
   is no longer needed
5. preserve the honest paper-facing story while continuing to improve:
   - PDE first-feasible efficiency versus `union`
   - post-feasible diversity
   - chain coherence across recover / preserve / expand

## 2. Honesty Boundary

The current checked evidence is the newest official rerun at:

- `/home/hymn/msfenicsx/scenario_runs/s2_staged/0421_1434__llm`

and the newest external comparison bundle at:

- `/home/hymn/msfenicsx/scenario_runs/compare_reports/s2_staged/0421_1456__raw_union_old_vs_llm_expand_fix`

The honest status from those artifacts is:

- optimizer first feasible:
  - `llm = 48`
  - `union = 48`
  - `raw = 73`
- PDE first feasible:
  - `llm = 23`
  - `union = 20`
  - `raw = 40`
- final hypervolume:
  - `llm = 475.37373977139913`
  - `union = 330.57376222166533`
  - `raw = 516.6124094618752`
- final front size:
  - `llm = 4`
  - `union = 4`
  - `raw = 2`

So the current problem is no longer:

- "LLM still cannot enter feasible space"
- "LLM still has no preserve phase"

The remaining paper-facing problem is:

- `llm` still does not beat `union` on PDE first feasible
- `llm` still does not own a cleaner post-feasible chain than `union`
- `expand` still does not become a real operating phase in live traces

## 3. Evidence Progression Across This Repair Line

The current cycle has already established a clear improvement ladder:

1. `0421_0207__llm`
   - first feasible strong: `46 / 23`
   - but post-feasible chain collapsed to recover-only
   - hidden positive credit requests: `101`
   - convert route-family mode: `none`
2. `0421_1230__llm`
   - preserve appears in traces
   - front size improves to `3`
   - convert is still effectively hidden
3. `0421_1315__llm`
   - convert family mix becomes live
   - but first feasible collapses badly to `145 / 95`
   - preserve disappears again
4. `0421_1343__llm`
   - stable-local handoff becomes live
   - hidden-positive count falls sharply
   - but recover still dominates and first feasible remains poor
5. `0421_1409__llm`
   - preserve becomes a real phase
   - hidden-positive contract drops to zero
   - first feasible returns to `48 / 22`
   - expand still absent
6. `0421_1434__llm`
   - front size reaches `4`
   - hypervolume stays strong against `union`
   - preserve remains live
   - but hidden-positive requests reappear (`20`)
   - `expand` remains absent

This progression matters because it shows the remaining faults are not global.
They are later-stage contract and gating faults introduced by the current
interaction between:

- retrieval matching
- family-level aggregation
- recover release semantics
- expand gating and expand demotion

## 4. Remaining Root Causes

### 4.1 Match-Level Positive Evidence Is Still Lost During Family Aggregation

Current traces show requests where:

- `positive_matches` contains route families such as:
  - `stable_local`
  - `stable_global`
  - `sink_retarget`

but the aggregated `route_family_credit` still emits:

- `positive_families = []`
- `negative_families` including the same family

and the effective visible pool then hides the family again.

This happens because:

- `reflection.summarize_route_family_credit(...)` aggregates all matched regime
  evidence into a single mixed-sign family summary
- `state_builder._build_retrieval_panel(...)` keeps the match-level episodes,
  but the policy layer restores visibility mainly from aggregated
  `positive_families` plus special-case handoff
- mixed long-horizon evidence can therefore overrule the current request's best
  positive matches

This is the main reason hidden-positive requests reappeared in
`0421_1434__llm`.

### 4.2 Recover Pressure And Recover Release Are Still Coupled Too Tightly

The latest live traces show:

- `recover_exit_ready_count = 0`
- all recover requests reporting:
  - `recover_reentry_pressure = high`
  - `preservation_pressure = high`

But preserve still appears in live traces, which means the controller is
already partially leaving recover via preserve dwell even while the explicit
release signal remains dead.

That is a semantic contract bug:

- the chain now behaves as if recover can release
- the state contract still says recover never became ready to release

The root issue is that the current logic still makes `recover_exit_ready`
effectively equivalent to:

- `recover_pressure_level == low`

That is too strict for noisy post-feasible windows where we still want:

- bounded regression
- real preservation evidence
- temporary preserve comparison

without waiting for a perfectly clean low-pressure regime.

### 4.3 Expand Is Still Blocked By Overly Hard Admission Gates

Replaying `build_progress_state(...)` against the latest official run shows:

- `post_feasible_mode = expand` never occurs

The dominant blockers are:

- `preserve_dwell_remaining > 0`
- `recent_feasible_regression_count > 0`
- `pareto_size > 1`

The hardest problem is the current expand gate:

- it allows expand only when:
  - preserve dwell has fully completed
  - frontier stagnation is already present
  - `pareto_size <= 1`
  - `recent_feasible_regression_count <= 0`

That means expand is only allowed when diversity is already almost collapsed to
one point and the local regression window is perfectly clean.

This is too brittle. Expand should become available earlier, when diversity is
still deficient but not yet fully collapsed.

### 4.4 Expand Saturation Still Uses A Diversity-Blind Threshold

The previous fix already stopped expand saturation from demoting a true single-
point front, but the current contract is still too coarse.

What we want is not:

- "expand saturates after N steps unless pareto_size <= 1"

What we actually need is:

- "expand saturates only after the diversity deficit has cooled enough that
  further expand pressure is no longer justified"

This requires a more explicit diversity-deficit signal.

## 5. Considered Approaches

### 5.1 Approach A: Visibility-Only Repair

Repair only the match-to-visible-pool contract.

Pros:

- smallest change
- most likely to remove the remaining hidden-positive requests quickly
- least likely to destabilize first-feasible behavior

Cons:

- does not solve the dead `recover_exit_ready` signal
- does not make `expand` reachable
- likely preserves the current PDE gap versus `union`

### 5.2 Approach B: Phase-Machine-Only Repair

Ignore match-level visibility and focus only on recover-release and expand
gating.

Pros:

- directly targets chain occupancy
- easiest path to making `expand` appear in traces

Cons:

- phase transitions would still operate on a partially dishonest visible pool
- can create a nominally richer chain that is still comparing the wrong families

### 5.3 Approach C: Layered Contract Repair

Repair the chain in three layers:

1. current-match visibility floor
2. recover release semantics
3. diversity-deficit expand gating

Pros:

- matches the actual order of remaining evidence failures
- keeps each TDD step narrow and auditable
- gives each rerun a clean causal interpretation

Cons:

- takes more than one minimal patch
- requires discipline not to blend the layers together

### 5.4 Recommendation

Use Approach C.

The remaining failures are not independent, but they are layered. If we repair
phase transitions before repairing visibility floors, the controller can enter
preserve/expand while still hiding its best current positive families. That
would create a less honest chain, not a better one.

## 6. Recommended Design

### 6.1 Introduce A Match-Level Visibility Floor

The retrieval panel should expose two different concepts instead of one
compressed family summary:

1. long-horizon family credit
   - current `route_family_credit`
   - still useful as a memory signal
2. current-match visibility floor
   - derived directly from `positive_matches`
   - candidate-constrained
   - similarity-ranked

New retrieval-panel fields should include:

- `positive_match_families`
- `negative_match_families`
- `visibility_floor_families`

Contract:

- any route family present in `visibility_floor_families` must stay visible in
  recover/preserve unless there is an explicitly surfaced stronger suppressor in
  the same request
- aggregated negative long-horizon credit alone is not sufficient to hide a
  current positive match family

This design keeps:

- long-horizon memory
- match-level honesty

separate instead of letting one erase the other.

### 6.2 Separate Recover Release From Recover Reentry Pressure

The current state already uses:

- `recover_pressure_level`
- `recover_reentry_pressure`

but the live chain also needs a separate release boolean.

Add a release-ready signal such as:

- `recover_release_ready`

derived from:

- presence of preservation evidence in the recent window
- bounded regression surplus rather than strict zero regression
- recent preserve dwell signal

Recommended contract:

- `recover_reentry_pressure` remains the risk signal
- `recover_release_ready` becomes the leave-recover signal
- prompt / request traces must expose both

This allows the chain to say:

- "recover is still risky to re-enter"

while also saying:

- "we have enough preservation evidence to compare preserve-family options now"

That is more honest and better matches the current live behavior.

### 6.3 Replace Single-Point Expand Gating With Diversity Deficit

The chain needs an explicit diversity-deficit state instead of using
`pareto_size <= 1` as a proxy for "expand still needed".

Add a derived signal such as:

- `diversity_deficit_level`

with a generic interpretation:

- `high`
  - front is very narrow
- `medium`
  - front is still narrow enough that expand is justified
- `low`
  - front is broad enough that preserve/native exploitation can dominate again

Recommended initial policy:

- `high` when `pareto_size <= 1`
- `medium` when:
  - `pareto_size == 2`
  - frontier stagnation is already non-trivial
- `low` otherwise

Then:

- expand promotion should require:
  - preserve dwell completed
  - frontier stagnation present
  - diversity deficit in `{high, medium}`
  - bounded regression rather than regression strictly equal to zero
- expand saturation demotion should only apply when:
  - expand is saturated
  - diversity deficit has cooled to `low`

This allows expand to appear while diversity is still weak, instead of after it
is already too late.

### 6.4 Keep Live Evidence Auditable

The request-trace surface should expose the new chain diagnostics directly so
that later audits do not need prompt-markdown reparsing for core conclusions.

The live request trace should surface:

- `recover_release_ready`
- `recover_reentry_pressure`
- `diversity_deficit_level`
- `positive_match_families`
- `visibility_floor_families`

This will make it possible to answer, from one run:

- whether hidden positive matches still exist
- whether recover can release
- whether expand was gated by diversity or by regression

## 7. Expected Evidence Outcomes

The next repair round should be judged in this order:

1. structural contract outcomes
   - zero hidden positive-match requests
   - non-zero recover release
   - non-zero expand occupancy
2. controller-chain outcomes
   - preserve remains non-zero
   - expand becomes non-zero
   - recover occupancy reduces without collapsing first feasible
3. paper-facing metrics
   - first feasible should stay at least tied with `union`
   - PDE first feasible should move toward or below `union`
   - hypervolume should stay above `union`
   - front diversity should stay at least tied with `union`

## 8. Non-Goals

This phase-2 design does not:

- change the benchmark
- change the shared operator registry
- add benchmark-specific operator exceptions
- hardcode seed-specific controller behavior
- attempt to beat `raw` on every metric in this cycle

## 9. Operational Note For Reruns

The last cycle exposed a runtime-wrapper issue:

- `shell_command` could receive `SIGTERM`
- the underlying `optimize-benchmark` child process could still continue

So the stable rerun protocol for the next cycle should be:

- launch with `nohup`
- capture the PID
- poll for completion
- only then run `render-assets`

This is an execution detail, not a controller design change, but it should stay
in the implementation plan to avoid false-negative rerun status.
