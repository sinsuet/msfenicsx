# S2 Staged Joint Benchmark-Controller Design

> Status: active paper-facing S2 benchmark-controller design.
>
> This document defines the current `s2_staged` benchmark and controller line.

## 1. Decision Summary

- benchmark id: `s2_staged`
- role: controller-sensitive staged companion benchmark to `s1_typical`

This is a deliberate benchmark-plus-controller redesign, not a small retuning
pass. The target story is:

- `raw` remains the matched native baseline
- `union` remains the shared mixed-action registry with random-uniform control
- `llm` keeps the same mixed-action registry as `union`
- `llm` gains advantage from portable controller policy, not benchmark-specific
  prompt hacks

The benchmark must be staged so that:

1. the shared pre-controller prefix stays infeasible
2. first feasible entry becomes controller-sensitive
3. post-feasible progress still requires semantic tradeoff shaping before local
   native finishing

The controller must be redesigned so that:

1. first-feasible entry is decided in a route-family-aware `prefeasible_convert`
   window rather than a stable-only convert loop
2. recover does not collapse to a stable-plus-peak-only corner
3. route-family reasoning is available before full expand
4. congestion and gradient families receive the same structural protection as
   sink and peak families when state demands them
5. semantic macro moves hand off back to native or local micro finishing

## 2. Honesty Boundary

This redesign must not assume that the repository has already proven
`llm` dominance on `s1_typical`.

Current checked-in S1 evidence says:

- `raw` still won the extreme single-point endpoints in the referenced S1 runs
- `union` still held broader feasible-set and Pareto advantages in the main
  recovery handoff
- current LLM controller work improved behavior, but did not already prove a
  clean `llm > raw and union on all fronts` paper claim

So the new S2 is not a confirmation benchmark for an already-solved S1 story.
It is a new paper-facing benchmark candidate that must stand on its own
evidence.

## 3. Evidence Basis

This design is grounded on the currently available repository evidence:

- docs:
  - `docs/reports/2026-04-15-s1-typical-llm-controller-recovery-handoff.md`
  - `docs/archive/specs/2026-04-14-s1-typical-llm-l2-controller-recovery-design.md`
  - `docs/archive/specs/2026-04-15-s1-typical-llm-l3-controller-diversity-design.md`
- earlier internal S2 calibration evidence that established the scenario-first
  regime reached feasibility too early
- optimizer chain:
  - `optimizers/problem.py`
  - `optimizers/repair.py`
  - `optimizers/cheap_constraints.py`
  - `optimizers/adapters/genetic_family.py`
  - `optimizers/operator_pool/operators.py`
  - `optimizers/operator_pool/state_builder.py`
  - `optimizers/operator_pool/domain_state.py`
  - `optimizers/operator_pool/policy_kernel.py`
  - `optimizers/operator_pool/llm_controller.py`
  - `optimizers/operator_pool/reflection.py`
  - `optimizers/operator_pool/prompt_projection.py`
  - `optimizers/artifacts.py`
  - `optimizers/traces/prompt_store.py`
  - `optimizers/traces/llm_trace_io.py`
- current staged validation artifacts:
  - `scenario_runs/s2_staged/0420_1841__raw_union_llm/raw`
  - `scenario_runs/s2_staged/0420_1841__raw_union_llm/union`
  - `scenario_runs/s2_staged/0420_1841__raw_union_llm/llm`
  - `scenario_runs/comparisons/s2_staged_0420_1841__raw_union_llm`

## 4. Verified Findings And Corrections

### 4.1 Shared Prefix And First Feasible Timing

The three completed `20 x 10` S2 runs are identical through history row `21`:

- row `1`: repaired baseline
- rows `2-21`: shared initial population evaluations

They first diverge at history row `22`.

The first feasible optimizer record appears at `evaluation_index = 4` in all
three runs, before controller divergence.

The shared prefix already contains six feasible optimizer records.

This means the current benchmark is not controller-sensitive at the point where
feasibility is first entered.

### 4.2 Repaired Baseline Is The Real Acceptance Object

`optimizers/problem.py` evaluates:

1. decision vector application
2. `repair_case_payload_from_vector(...)`
3. `evaluate_cheap_constraints(...)`
4. PDE solve and evaluation

So the optimizer never scores the raw scenario template directly.

The current repaired baseline recorded in the finished runs is:

- infeasible
- dominated by exactly one positive constraint:
  - `c02_peak_temperature_limit = +1.5240586856422738`
- total positive violation:
  - `1.5240586856422738`

This matches the checked-in acceptance test, but it is too close to feasibility
to keep the shared prefix infeasible.

### 4.3 Earlier Scenario-First Calibration Reached Feasibility Too Early

Current final `20 x 10` results:

- `raw`
  - feasible rate: `0.55`
  - Pareto size: `1`
  - best peak: `318.2087372477349`
  - best gradient: `13.362361827534428`
- `union`
  - feasible rate: `0.385`
  - Pareto size: `6`
  - best peak: `322.3793297916972`
  - best gradient: `15.121646396877349`
- `llm`
  - feasible rate: `0.50`
  - Pareto size: `14`
  - best peak: `321.6861937371288`
  - best gradient: `14.569331936845714`

So the current benchmark allows `llm` to beat `union`, but not to beat `raw`.
The resulting late budget becomes dominated by feasible-region numerical
refinement, which favors the native baseline.

### 4.4 Current PDE-Efficiency Signal Is Real But Not Comprehensive

Counting feasible PDE attempts only, current S2 already shows a partial
controller-efficiency signal:

- to reach `union`'s final gradient level, `llm` needs `68` feasible PDE solves
  while `union` needs `135`
- to reach `union`'s final peak level, `llm` needs `43` feasible PDE solves
  while `union` needs `67`

But the same evidence is not enough for the desired paper claim against `raw`:

- `raw` reaches `union`'s final peak level in `18` feasible PDE solves
- `raw` reaches `llm`'s final gradient level in `107` feasible PDE solves while
  `llm` needs `148` to reach its own final gradient point

So current S2 does contain useful efficiency signal, but it is not yet a clean
`llm > raw and union` efficiency benchmark.

### 4.5 The Current LLM Action Space Is Structurally Smaller Than Union's

In the earlier scenario-first S2 calibration, `union` always saw the full
ten-operator registry.

By contrast, the corresponding `174` unique LLM prompt requests in that same
calibration exposed:

- original candidate pool size is always `10`
- effective candidate pool size is only `1-4`
- `route_family_mode = none` in all `174` prompts
- `semantic_trial_mode = none` in all `174` prompts

The current comparison is therefore not:

- `union`: full shared registry, random policy
- `llm`: full shared registry, intelligent policy

It is functionally:

- `union`: full shared registry, random policy
- `llm`: heavily filtered sub-registry, intelligent policy

### 4.6 The Current LLM Is Locked In Recover

The raw `controller_trace.json` contains duplicate rows for native two-child
events, so phase accounting must be done by unique `decision_id`, not raw row
count.

On unique LLM decisions:

- `173 / 174` are `post_feasible_recover`
- `1 / 174` is `feasible_refine`
- `0 / 174` are `post_feasible_expand`
- `0 / 174` are `post_feasible_preserve`

So the current report is directionally correct that the controller is locked in
recover, but the auditable unit is `173 / 174` unique decisions, not the raw
`179 / 180` row count.

### 4.7 Congestion And Gradient Families Are Starved

The current state builder does know about congestion-sensitive state:

- `nearest_neighbor_gap_min`
- `local_congestion_pair`
- `hottest_cluster_compactness`
- `frontier_tradeoff_direction`

And it can assign high applicability to:

- `reduce_local_congestion`
- `smooth_high_gradient_band`
- `spread_hottest_cluster`

But current LLM prompts show:

- `smooth_high_gradient_band` filtered in `174 / 174` prompts
- `reduce_local_congestion` filtered in `174 / 174` prompts
- `rebalance_layout` filtered in `174 / 174` prompts

Under `objective_balance.preferred_effect = gradient_improve`:

- total requests: `80`
- requests with any `congestion_relief` family in the effective pool: `0`

So the controller is not merely choosing sink and peak routes more often. It is
often not allowed to compare congestion routes at all.

### 4.8 Current Pareto Ownership Confirms The Route Collapse

Union Pareto contributions include:

- `reduce_local_congestion`
- `spread_hottest_cluster`
- `smooth_high_gradient_band`
- `repair_sink_budget`
- `slide_sink`

LLM Pareto contributions include only:

- `repair_sink_budget`
- `slide_sink`
- `move_hottest_cluster_toward_sink`

Current LLM Pareto ownership does not show meaningful congestion-family
participation.

### 4.9 Reflection Credit Is Expand-Only

`optimizers/operator_pool/reflection.py` only increments:

- `recent_expand_selection_count`
- `recent_expand_feasible_preservation_count`
- `recent_expand_feasible_regression_count`
- `recent_expand_frontier_add_count`

when `controller_phase == "post_feasible_expand"`.

Since the current run never reaches expand, semantic families that are filtered
in recover or preserve never accumulate the credit that would later make them
look trusted.

### 4.10 Trace Observability Is Good Enough But Still Too Indirect

The current trace stack is usable:

- request and response JSONL sidecars exist
- prompt markdown dumps are content-addressed and reproducible
- `llm_trace_io.py` can materialize prompts from `prompt_ref`

But detailed controller-pool analysis currently requires joining:

- `traces/llm_request_trace.jsonl`
- prompt markdown under `prompts/*.md`
- `controller_trace.json`

The next paper-facing S2 should promote a flatter analytics surface for:

- unique decision count
- effective pool size
- route-family visibility
- filtered family reasons

### 4.11 First Official `s2_staged` Validation Moves The Blocker To Controller Entry

The latest official staged run,
`scenario_runs/s2_staged/0420_1841__raw_union_llm`, changes the diagnosis.

For this run:

- in `traces/evaluation_events.jsonl`, optimizer eval rows `1-20` are identical
  and infeasible across `raw`, `union`, and `llm`
- row `21` (`eval_index = 20`) is the first optimizer-side divergence
- no mode reaches feasibility before controller divergence
- normalized `first_feasible_eval` is:
  - `raw = 73`
  - `union = 48`
  - `llm = 57`

So the benchmark-side staging objective is now substantially satisfied.
The remaining blocker is not "shared prefix enters feasibility too early".
It is that `llm` still loses the first-feasible race after divergence.

### 4.12 `union` Wins First Feasible Through Semantic Entry, While `llm` Is Still Stable-Only

In the same official staged run:

- `union` reaches first feasible through `spread_hottest_cluster`
- before first feasible, `union` uses:
  - `sink_retarget`
  - `hotspot_spread`
  - `congestion_relief`
  - `budget_guard`
  - `layout_rebalance`
  - plus stable routes
- before first feasible, `llm` uses only:
  - `native_sbx_pm`
  - `local_refine`
  - `global_explore`

Prompt and request-trace evidence around decisions
`g003-e0042-d15` through `g003-e0055-d25` shows:

- `policy_phase = prefeasible_convert`
- `route_family_mode = none`
- `semantic_trial_mode = none`
- effective candidates only:
  - `native_sbx_pm`
  - `global_explore`
  - `local_refine`
- all semantic routes filtered out:
  - `move_hottest_cluster_toward_sink`
  - `spread_hottest_cluster`
  - `smooth_high_gradient_band`
  - `reduce_local_congestion`
  - `repair_sink_budget`
  - `slide_sink`
  - `rebalance_layout`

This is the decisive current failure mode.
`union` is allowed to win with semantic entry routes from the shared registry.
`llm` is still denied those same route families in the exact window that
determines `first_feasible_eval`.

### 4.13 Hidden Semantic Routes Are State-Applicable, Not Irrelevant

The current spatial and regime state in that `prefeasible_convert` window is
not semantically empty.

The prompt-visible state still shows:

- a persistent `thermal_limit` dominant violation
- `near_feasible_window = true`
- hotspot structure informative enough to classify:
  - sink alignment
  - cluster compactness
  - local congestion
  - sink-budget pressure

Re-running the current applicability logic on the hidden operators in that
window yields:

- `repair_sink_budget`: `high`
- `rebalance_layout`: `high`
- `move_hottest_cluster_toward_sink`: `medium`
- `spread_hottest_cluster`: `medium`
- `reduce_local_congestion`: `medium`
- `slide_sink`: `medium`

So the issue is not that semantic routes are inapplicable.
The issue is that they are structurally hidden from the LLM despite remaining
state-relevant.

### 4.14 `llm` Already Finds Near-Feasible Basins But Fails To Convert Them

The latest staged run also shows that `llm` is not simply farther from
feasibility throughout pre-entry search.

It reaches stronger pre-feasible basins earlier, including:

- `eval_index = 33` with total positive violation `0.548228553065087`
- `eval_index = 37` with total positive violation `0.8684484211665904`

By comparison, `union`'s best pre-feasible point before its first feasible
crossing is:

- `eval_index = 43` with total positive violation `0.8593387382986748`

So the main failure is convert-stage control, not only basin discovery.
`llm` can touch strong near-feasible states, then fall back into a stable-only
reset and convert loop that fails to finish the crossing.

### 4.15 Reflection And Retrieval Still Over-Credit Stable Prefeasible History

Current reflection averages raw total-violation deltas, including `1e12`
penalty events from failed solves or immediate penalty records.

In the latest staged prompts this yields exaggerated positive retrieval evidence
such as:

- `local_refine.avg_total_violation_delta ~= -3.5e12`

That does not create the primary failure mode by itself, but it amplifies it:

- stable operators look artificially dominant in retrieval
- semantic operators remain both filtered and under-credited
- the LLM is pushed even harder toward stable-only convert behavior

## 5. Root Cause Tree

### 5.1 Benchmark-Side Root Causes

- for the earlier scenario-first line, repaired-baseline staging was too weak
  and feasibility arrived inside the shared prefix
- for the current `s2_staged` line, that benchmark-side defect is largely fixed:
  the shared optimizer prefix is now identical and infeasible through the
  pre-controller window
- remaining benchmark work is calibration margin, not the primary blocker for
  `first_feasible_eval`

### 5.2 Controller-Side Root Causes

- `prefeasible_convert` collapses the effective pool to stable operators unless a
  semantic route already has entry evidence
- `prefeasible_convert` has no route-family comparison mode and no bounded
  semantic-trial mode
- peak and sink entry routes are easier to preserve than congestion and spread
  routes, but in the latest run even those semantic routes are hidden from the
  LLM before first feasible
- reflection and retrieval are still distorted by penalty-heavy pre-feasible
  deltas, which over-credit stable routes
- forced reset and stable-only convert interact to trap the LLM in a
  "touch near-feasible, regress, retry stable" loop

### 5.3 Comparison-Side Root Causes

- `union` samples the full shared registry in the decisive entry window
- `llm` sees a filtered and phase-compressed subset exactly in that same window
- `union` can therefore enter feasibility through semantic reshaping, while
  `llm` is often forced to attempt the crossing with stable-only routes
- resulting comparison still understates true controller quality because the two
  modes are not yet functionally symmetric at first-feasible time

### 5.4 Paper-Narrative Root Cause

The current staged line is no longer blocked primarily by benchmark design.
It is blocked because the intended LLM advantage has not yet been placed on the
critical first-feasible path. The controller wins late and loses early.

## 6. Non-Negotiable Invariants

The redesign must preserve:

- one operating case
- fifteen named components
- `x / y` optimization only for all fifteen components
- no optimized rotation
- `32` design variables
- the same paper ladder:
  - `raw`
  - `union`
  - `llm`
- the same optimizer fairness boundary:
  - identical problem
  - identical repair
  - identical cheap constraints
  - identical PDE solve
  - identical evaluation chain
  - identical operator registry for `union` and `llm`
- hard sink-budget enforcement inside the optimizer contract

The redesign must not:

- hardcode benchmark ids into controller policy
- hardcode operator names as seed-specific exceptions
- make `llm` use a private operator family unavailable to `union`
- rely on transport-side excuses for controller underperformance

## 7. New Benchmark Identity: `s2_staged`

### 7.1 Why The Current Id Must Stay Stable

The current evidence shows that S2 needs a joint benchmark-controller design,
not another scenario-only retuning pass.

So the clean repository story is:

- `s2_staged`: the active joint benchmark-controller paper candidate
- the earlier S2 attempts are retired and no longer part of the active tree

### 7.2 Identity Statement

`s2_staged` should be described as:

- a controller-sensitive staged thermal benchmark
- calibrated on the repaired optimizer baseline
- designed so semantic recovery matters before first feasibility
- designed so semantic tradeoff shaping matters before native local finishing

## 8. Benchmark Design For `s2_staged`

### 8.1 Stage Structure

`s2_staged` should have four practical stages.

#### Stage A: Shared Prefix Infeasible

Target property:

- baseline plus initial population remain infeasible under official `20 x 10`
  settings

This is the hard boundary that the earlier scenario-first calibration failed.

#### Stage B: Semantic Recovery

Target property:

- first feasible entry requires coordinated semantic recovery
- the controller must choose between at least two non-stable route families
  before first feasible entry

Preferred early families:

- `sink_retarget`
- `hotspot_spread`
- `budget_guard`

#### Stage C: Semantic Tradeoff Shaping

Target property:

- first feasible entry does not immediately settle the objective tradeoff
- congestion and gradient relief remain materially useful after recovery

Preferred midgame families:

- `congestion_relief`
- `hotspot_spread`
- `layout_rebalance`

#### Stage D: Native Finishing

Target property:

- once semantic routes restore a good feasible basin, native or local finishing
  can refine the frontier

Preferred late families:

- `local_refine`
- `native_sbx_pm`
- `global_explore` only as bounded diversification

### 8.2 Repaired-Baseline Targets

The repaired baseline should satisfy all of the following at benchmark seed
`11`:

- `baseline_feasible = false`
- exactly one positive constraint at the repaired baseline
- dominant positive constraint family: `thermal_limit`
- dominant positive constraint id: `c02_peak_temperature_limit`
- total positive violation target band: `2.5 K` to `4.0 K`
- no secondary positive constraint above `0.5 K`

The repaired baseline should also satisfy prompt-visible spatial targets:

- `hotspot_inside_sink_window = false`
- `abs(hotspot_to_sink_offset)` in roughly `0.08` to `0.18`
- `nearest_neighbor_gap_min <= 0.06`
- `hottest_cluster_compactness <= 0.13`
- `sink_budget_bucket` should be `tight` or `full_sink`

The point is not to make recovery impossible.
The point is to make random initial feasibility unlikely while keeping
controller-guided recovery plausible.

### 8.3 Shared-Prefix Targets

At official seed and official `20 x 10` budget, benchmark acceptance must be
checked directly from `traces/evaluation_events.jsonl`, not from ambiguous
history-row summaries.

Required properties:

- optimizer eval rows `1-20` are identical across `raw`, `union`, and `llm`
- optimizer eval rows `1-20` are all infeasible
- first divergence occurs no earlier than optimizer eval row `21`
- no mode reaches feasibility before that divergence
- reporting must preserve both:
  - raw trace `eval_index`
  - normalized run-summary `first_feasible_eval`

This is a benchmark acceptance rule, not a prompt hack.
The benchmark is single-case and seed-fixed by design.

### 8.4 Scenario Calibration Guidance

The scenario should be tuned against prompt-visible state, not only scalar
constraint magnitudes.

Recommended physical and geometric direction:

- keep one dominant c02 entry gate
- keep the hot three-module cluster compact
- keep the cluster outside the sink corridor at the repaired baseline
- keep sink utilization tight enough that sink routing matters
- keep at least one crowding bottleneck so congestion relief still matters after
  feasibility
- avoid a many-constraint thermal wall

Compared with the earlier scenario-first calibration, the staged benchmark
likely needs:

- a slightly harder repaired baseline than `+1.524 K`
- stronger hotspot-to-sink misalignment
- tighter local crowding
- no extra thermal constraint family trick, because controller-side family
  classification collapses thermal ids anyway

### 8.5 Evaluation-Spec Guidance

Keep:

- `summary.temperature_max`
- `summary.temperature_gradient_rms`
- `radiator_span_budget`

Do not use:

- sink-budget violation as the main paper narrative
- multiple thermal constraint ids as a fake route-family generator

Do use:

- one dominant entry gate on `c02`
- slack-but-nearby supporting hotspot limits on `c04`, `c06`, `c12`, `c01`,
  and `c08`
- a loose `panel_temperature_spread_limit` that remains diagnostic, not the
  primary binding gate

The key change from the earlier scenario-first calibration is not a new
objective pair.
It is a different staged feasible-basin geometry after repair.

## 9. Portable Controller Redesign

### 9.1 Make `prefeasible_convert` A Route-Family Entry Window

The current decisive failure is pre-feasible, not post-feasible.

`prefeasible_convert` must stop behaving like a stable-only cleanup phase.
When the state shows persistent dominant violation plus near-feasible pressure,
the controller should treat this as a bounded entry-routing problem.

The entry window must guarantee, when relevant:

- one stable floor candidate
- one sink or budget entry family
- one spread or congestion entry family

This must be triggered by portable state, not by benchmark id.

### 9.2 Allow Route-Family Reasoning In `prefeasible_convert`

Current `route_family_mode` and `semantic_trial_mode` are absent exactly where
`first_feasible_eval` is decided.

The redesign must allow bounded route-family comparison in:

- `prefeasible_convert`
- `post_feasible_recover`
- `post_feasible_preserve`
- `post_feasible_expand`

`prefeasible_convert` should be the first place where route-family reasoning is
possible, not the only place where it is impossible.

### 9.3 Protect State-Applicable Semantic Entry Routes From Stable-Only Collapse

Current semantic entry routes can be medium or high applicability and still be
fully filtered out before the LLM sees them.

The redesign must preserve bounded semantic entry visibility when state shows:

- persistent `thermal_limit` pressure
- hotspot-to-sink misalignment
- compact hotspot cluster
- local congestion
- sink-budget saturation or near-saturation

This should hold even if those semantic routes do not yet have strong historical
entry credit.

### 9.4 Add Symmetric Entry Escape Families

Current policy bias is asymmetric.

Portable entry escapes should include both:

- sink and budget:
  - `slide_sink`
  - `move_hottest_cluster_toward_sink`
  - `repair_sink_budget`
- spread and congestion:
  - `spread_hottest_cluster`
  - `reduce_local_congestion`
  - `smooth_high_gradient_band`
  - `rebalance_layout` when layout-wide pressure is visible

The controller must not protect only sink-retarget moves in early entry.

### 9.5 De-Bias Reflection And Retrieval In Penalty-Heavy Prefeasible History

Reflection should not let `1e12` penalty events dominate convert-stage evidence.

The redesign must:

- separate normal violation deltas from penalty-coded failure deltas
- avoid using penalty-distorted averages as primary positive retrieval evidence
- preserve counts for:
  - dominant-violation relief
  - near-feasible improvement
  - feasible entry
  - feasible preservation
  - feasible regression
  - frontier add

This is required so stable-only retrieval pressure does not swamp bounded
semantic entry evidence.

### 9.6 Redesign Recover And Preserve Around Route-Family Floors

Once first feasibility is fixed, recover and preserve still need structural
protection.

The redesign must guarantee, when the state indicates relevance:

- one stable floor candidate
- one sink or peak semantic family
- one congestion or gradient semantic family

State signals that can trigger the gradient or congestion floor include:

- `objective_balance.preferred_effect == gradient_improve`
- `nearest_neighbor_gap_min` below threshold
- compact hot cluster with unresolved crowding
- persistent `frontier_tradeoff_direction == gradient_pressure`

### 9.7 Add Explicit Macro-To-Micro Handoff

Once a semantic route produces one of:

- first feasible entry
- frontier add
- meaningful objective milestone

the controller should open a bounded local finishing window that restores:

- `local_refine`
- `native_sbx_pm`
- low-risk cleanup choices

This is necessary if `llm` is expected to beat `raw` on final extremes rather
than only on search breadth.

### 9.8 Guardrail Rule: Do Not Collapse To Stable-Only Or One Route Family Unless Emergency

Future guardrails must preserve at least two route families whenever:

- more than one non-stable family is state-applicable
- the run is not in a one-family emergency regime

This rule applies before the final LLM choice, not only after the fact in
diagnostics.

## 10. Trace And Prompt-Dump Requirements

The new S2 line must make controller analysis cheap and auditable.

Each unique LLM decision should expose, without prompt-file joins, at least:

- unique `decision_id`
- original candidate pool size
- effective candidate pool size
- original route families
- effective route families
- filtered route families
- filter reason codes
- `semantic_trial_mode`
- `route_family_mode`
- `recover_exit_ready`
- `objective_balance.preferred_effect`

Prompt dumps should remain content-addressed, but summary JSONL should be rich
enough that a route-family audit does not require reparsing markdown.

## 11. Promotion Gates

### 11.1 Structural Gates

Before any paper-facing promotion:

- repaired baseline satisfies the staged target band
- in `traces/evaluation_events.jsonl`, optimizer eval rows `1-20` are identical
  and infeasible for all three modes
- first divergence occurs no earlier than optimizer eval row `21`
- no mode reaches feasibility before divergence
- unique LLM decisions show all of:
  - `prefeasible_convert`
  - `recover`
  - `preserve`
  - `expand`
- no single LLM post-feasible phase occupies more than `85%` of unique LLM
  decisions at official `20 x 10`

### 11.2 Visibility Gates

At official `20 x 10`:

- during `prefeasible_convert`, the effective LLM pool must contain at least
  one non-stable route family for at least `80%` of prompts in that phase
- when `preferred_effect == gradient_improve`, a `congestion_relief` route must
  be present in the effective LLM pool for at least `80%` of such prompts
- when hotspot is outside the sink window and peak pressure dominates, a
  `sink_retarget` or `budget_guard` route must be present for at least `80%` of
  such prompts
- when hotspot is already sink-aligned but compact and crowded, a
  `hotspot_spread` or `congestion_relief` route must be present for at least
  `80%` of such prompts
- request-side traces must identify which operator actually generated the first
  feasible offspring
- the effective LLM pool should average at least `5` operators and at least `3`
  route families during post-feasible search

### 11.3 Official `20 x 10` Gates

Require all of:

- all three modes complete cleanly
- LLM first feasible earlier than both baselines
- LLM final best peak better than `union`
- LLM final best gradient better than `union`
- LLM reaches at least one baseline final objective level with fewer feasible
  PDE solves than that baseline

### 11.4 Paper-Facing `32 x 16` Gates

This is the promotion gate.

Require all of:

- LLM final best peak better than both `raw` and `union`
- LLM final best gradient better than both `raw` and `union`
- LLM feasible rate is within `0.10` of the best baseline
- LLM Pareto set is non-empty and thermally meaningful
- for each objective, LLM either:
  - reaches the best baseline final level with at least `15%` fewer feasible PDE
    solves, or
  - finishes strictly better at comparable feasible PDE solves (within `10%`)

If these are not met, `s2_staged` does not become paper-facing active.

## 12. Expected Paper Narrative If Successful

If this design succeeds, the paper claim becomes:

- `raw` is the matched native search backbone
- `union` shows what happens when the action vocabulary is expanded without
  intelligent scheduling
- `llm` uses the same action vocabulary as `union`
- `llm` wins because it:
  - enters feasibility through state-appropriate semantic recovery
  - preserves route-family diversity while shaping the tradeoff
  - hands off to native local finishing at the right time

That is a publishable controller story.
It is stronger and more honest than the earlier scenario-first narrative.
