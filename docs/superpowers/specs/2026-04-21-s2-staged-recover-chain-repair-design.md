# S2 Staged Recover-Chain Repair Design

> Status: active repair design for the paper-facing `s2_staged` controller line.
>
> Workspace policy for this cycle: implement directly on `main`; do not create
> or rely on a separate worktree.

## 1. Decision Summary

- benchmark id: `s2_staged`
- active paper-facing route: `raw / union / llm`
- fairness boundary:
  - `union` and `llm` must keep the same shared operator registry
  - the paper-facing difference remains controller policy, not operator-pool
    membership

This repair does not redesign the benchmark again. The benchmark and the shared
operator registry are already good enough to expose controller-sensitive signal.
The repair target is the controller chain itself:

1. recover must stop staying sticky for almost the entire post-feasible budget
2. recover must stop hiding route families that already hold positive credit
3. retrieval and guardrail phases must stop disagreeing inside the same prompt
4. preserve and expand must become real operating regimes rather than nominal
   labels
5. `llm` must get a fair chance to convert strong early control into both PDE
   efficiency and broader Pareto ownership

## 2. Honesty Boundary

This design must stay aligned with the current checked evidence.

As of the new `llm` rerun at:

- `/home/hymn/msfenicsx/scenario_runs/s2_staged/0421_0207__llm`

and the external comparison bundle at:

- `/home/hymn/msfenicsx/scenario_runs/compare_reports/s2_staged/0421_0217__raw_union_old_vs_llm_new`

the honest status is:

- `llm` already beats `union` on optimizer first feasible:
  - `llm first_feasible_eval = 46`
  - `union first_feasible_eval = 48`
- `llm` already beats `raw` and `union` on final hypervolume on this checked
  seed:
  - `llm final_hypervolume = 528.5815849955469`
  - `raw final_hypervolume = 516.6124094618752`
  - `union final_hypervolume = 330.57376222166533`
- `llm` still does **not** beat `union` on PDE first feasible:
  - `llm first_feasible_pde_eval = 23`
  - `union first_feasible_pde_eval = 20`
- `llm` still does **not** own the broadest final Pareto set:
  - `llm front_size = 1`
  - `raw front_size = 2`
  - `union front_size = 4`

So the current repair is not about recovering from global underperformance.
It is about converting a strong single-point controller into a controller that
also wins the chain-level metrics that still matter:

- PDE entry efficiency versus `union`
- broader post-feasible diversity
- a non-collapsed preserve/expand regime

## 3. Evidence Basis

This repair is grounded in the following checked evidence:

- active repair handoff:
  - `/home/hymn/msfenicsx/docs/reports/2026-04-21-s2-staged-llm-effect-repair-report.md`
- active benchmark-controller design:
  - `/home/hymn/msfenicsx/docs/superpowers/specs/2026-04-20-s2-staged-joint-design.md`
- active previous implementation plan:
  - `/home/hymn/msfenicsx/docs/superpowers/plans/2026-04-20-s2-staged-joint-implementation.md`
- old official suite:
  - `/home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm`
- new `llm` rerun:
  - `/home/hymn/msfenicsx/scenario_runs/s2_staged/0421_0207__llm`
- current comparison bundle:
  - `/home/hymn/msfenicsx/scenario_runs/compare_reports/s2_staged/0421_0217__raw_union_old_vs_llm_new`

The most relevant implementation files are:

- `/home/hymn/msfenicsx/optimizers/operator_pool/domain_state.py`
- `/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py`
- `/home/hymn/msfenicsx/optimizers/operator_pool/state_builder.py`
- `/home/hymn/msfenicsx/optimizers/operator_pool/reflection.py`
- `/home/hymn/msfenicsx/optimizers/operator_pool/prompt_projection.py`
- `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py`
- `/home/hymn/msfenicsx/optimizers/analytics/staged_audit.py`

## 4. Root-Cause Diagnosis

### 4.1 The Phase Machine Is Structurally Collapsed

Replaying progress state over the checked runs shows:

- `raw` after first feasible:
  - `recover = 129`
  - `preserve = 0`
  - `expand = 0`
- `union` after first feasible:
  - `recover = 153`
  - `preserve = 1`
  - `expand = 0`
- `llm` after first feasible:
  - `recover = 154`
  - `preserve = 2`
  - `expand = 0`

So the active post-feasible chain is not:

- recover -> preserve -> expand

It is effectively:

- first feasible -> brief label flicker -> recover forever

The key causes are:

- `new_dominant_violation_family` is currently set by walking backward through
  all recent infeasible rows and marking recover if any earlier row has a
  different dominant family
- recover exit currently requires all of:
  - `stable_preservation_streak >= 3`
  - `recent_feasible_regression_count <= 0`
  - `new_dominant_violation_family == False`

That combination is too brittle for a noisy evolutionary run.

### 4.2 Recover Gating Is Too Narrow Even When State Demands More Breadth

The recover filter currently starts from:

- stable trusted-preserve operators only

and then restores at most:

- one semantic slot in recover

This is why the effective post-feasible recover pool collapses to `1-4`
operators even though the original pool is `10`.

In the new `llm` rerun:

- `layout_rebalance` is filtered `147` times
- `congestion_relief` is filtered `147` times
- `hotspot_spread` is filtered `147` times
- `budget_guard` is filtered `101` times

This is not just a preference bias. It is a structural visibility problem.

### 4.3 Retrieval And Guardrail Use Different Phase Semantics

The state builder currently constructs retrieval queries using:

- `prefeasible_convert`
- `post_feasible_expand`
- everything else after first feasible collapsed to `post_feasible_preserve`

But the prompt projection later rewrites `regime_panel.phase` to the actual
policy phase from the policy kernel.

That creates a prompt that can say both:

- recover is the active controller phase
- retrieval evidence is queried as preserve

In the new `llm` rerun:

- `131` requests are `post_feasible_recover`
- those same `131` requests still use retrieval query phase
  `post_feasible_preserve`

This is a contract bug, not just an evidence-shortage issue.

### 4.4 Positive Credit Can Exist While The Family Remains Hidden

The latest request-trace audit still shows:

- `101` requests with positive route-family credit that remains hidden

Missing visible positive families include:

- `stable_local: 60`
- `budget_guard: 41`
- `stable_global: 19`
- `sink_retarget: 4`

This means the current chain allows retrieval/reflection to say:

- "this family helped in a similar regime"

while the guardrail simultaneously says:

- "do not let the controller compare that family now"

That is precisely the mismatch we need to remove.

### 4.5 `union` Remains Strong Because It Bypasses The Bottleneck

`union` is still strong for a simple reason:

- the shared operator registry is already benchmark-aligned
- `union` samples the full shared pool without state-conditioned phase gating

So `union` keeps the benefits of:

- strong semantic operators
- broad route-family diversity
- no recover sticky penalty

while `llm` pays the cost of a narrow recover-gated visible pool.

### 4.6 `raw` Remains Competitive For A Different Reason

`raw` is no longer the main controller story, but it remains competitive
because native NSGA-II still exploits feasible basins well once it lands there.

So the remaining gap versus `raw` is not early control.
It is:

- PDE cost control
- post-feasible diversity
- preventing the controller from collapsing to a single dominant track

## 5. Repair Goals

The repair must satisfy all of the following.

### 5.1 Structural Goals

1. The controller prompt must expose one coherent phase story.
2. Recover must become escapable under normal successful post-feasible behavior.
3. Positive route-family evidence must have a direct visibility effect.
4. Preserve and expand must become reachable without benchmark-specific hacks.

### 5.2 Fairness Goals

1. `union` and `llm` keep the same operator registry.
2. No benchmark-id-specific operator exceptions.
3. No seed-specific or case-specific hardcoding.

### 5.3 Evidence Goals

1. The repair must be auditable from tests and traces.
2. The repair must expose where the chain still fails if `llm` still does not
   win every target metric.
3. The repair must preserve scientific honesty in final reporting.

## 6. Considered Approaches

### 6.1 Approach A: Only Relax Recover Exit Thresholds

This would:

- reduce recover stickiness
- keep most of the current candidate filtering unchanged

Advantages:

- smallest code change
- quickest path to seeing more `preserve`

Disadvantages:

- does not solve hidden positive credit
- does not solve retrieval/guardrail phase mismatch
- risks moving to preserve labels while the visible pool is still crippled

This is not sufficient.

### 6.2 Approach B: Remove Most Gating And Let `llm` See The Full Pool

This would:

- likely improve diversity quickly
- make `llm` more comparable to `union`

Advantages:

- simple
- could improve frontier width fast

Disadvantages:

- throws away the portable controller-policy story
- blurs the intended staged semantics
- risks turning `llm` into "language-conditioned full-pool random search"

This is too blunt and weakens the paper claim.

### 6.3 Approach C: Recommended

Use a portable controller repair with four coordinated changes:

1. align prompt, retrieval, and guardrail phase contracts
2. replace binary recover stickiness with windowed recover pressure
3. restore route-family visibility using positive credit and state demand
4. make preserve and expand real policy regimes with distinct floor semantics

This keeps the controller story intact while directly targeting the observed
bottlenecks.

## 7. Recommended Design

### 7.1 Align Phase Contracts Across The Whole Prompt Surface

The system must stop using one phase for guardrails and another for retrieval.

Design decisions:

1. `policy_phase` becomes the canonical post-filter phase identity.
2. Retrieval queries must use the actual policy phase first.
3. If retrieval needs broader support, it may use a bounded fallback list of
   adjacent phases, but that fallback must be explicit in the prompt surface.
4. `regime_panel.phase`, retrieval `query_regime`, and trace-level
   `policy_phase` must no longer disagree silently.

Required prompt-surface behavior:

- if the controller is in `post_feasible_recover`, the prompt must show either:
  - retrieval queried as `post_feasible_recover`, or
  - retrieval queried with explicit ordered aliases such as
    `["post_feasible_recover", "post_feasible_preserve"]`

It must never appear as implicit preserve-only retrieval under a recover
guardrail.

### 7.2 Replace Recover Stickiness With Windowed Recover Pressure

The current `new_dominant_violation_family` boolean is too tail-sensitive.
Recover should instead be driven by recent pressure, not historical existence.

Design decisions:

1. Replace the current binary "different family seen anywhere in the recent
   infeasible tail" rule with a bounded recent-family switch measure.
2. Compute recover pressure from:
  - recent feasible regression surplus
  - recent dominant-violation persistence
  - recent dominant-violation family switching
3. Permit recover exit when pressure falls below a threshold for a short window.
4. Preserve should become the default post-feasible mode once recover pressure
   is low enough.
5. Expand should activate from preserve when frontier stagnation and objective
   stagnation remain high enough.

This keeps recover meaningful without requiring an unrealistic perfect streak.

### 7.3 Make Recover Visibility Credit-Aware And Family-Aware

Recover must stop treating all semantic families the same when the prompt
already contains evidence that some of them are useful.

Design decisions:

1. Recover keeps a stable anchor floor.
2. Recover must also keep a family floor for each of the following when active:
  - positive route-family credit
  - strong state demand from objective balance or spatial pressure
  - required budget-protection routes when sink budget is tight/full
3. A route family with positive retrieval credit must not be fully hidden
   unless a stronger recent negative signal overrides it under a documented rule.
4. Visibility restoration must happen at the route-family level before final
   operator ranking within that family.
5. Semantic visibility restoration must run before any dominance throttles that
   would otherwise erase the family entirely.

The key invariant is:

- positive credit implies family-level comparability, not guaranteed selection

That keeps the controller honest while removing the current self-contradiction.

### 7.4 Distinguish Recover, Preserve, And Expand By Policy Intent

The chain should no longer be:

- stable floor plus one semantic slot for every post-feasible phase

Instead:

- recover:
  - stable anchor floor
  - credit-aware family restoration
  - escape floors for active objective-pressure families
- preserve:
  - low-regression bias
  - still compare multiple families if they hold positive credit
  - allow bounded gradient-congestion escape under objective pressure
- expand:
  - route-family diversity bias
  - frontier-support bias
  - expand-budget throttling only after family visibility guarantees are met

This gives each phase a different purpose instead of only a different label.

### 7.5 Promote Route-Family Credit To A First-Class Signal

Operator-level evidence is not enough for the current failure mode.
The repair must make route-family credit first-class in both state building and
guardrail restoration.

Design decisions:

1. Reflection keeps operator credit, but also aggregates family-level credit by
   regime.
2. Retrieval surfaces both:
  - operator-level matches
  - route-family-level positive/negative support
3. Policy kernel may use family credit to restore visibility even when a
   specific operator in that family has weak local counts.
4. Negative family evidence must stay visible too, so restored visibility does
   not become unconditional optimism.

### 7.6 Keep The Final Action At Operator Level

The repair does not turn the controller into a pure family selector.

The final action remains:

- choose one operator from the shared operator registry

But the selection order becomes:

1. construct the route-family-comparable visible pool
2. expose the family competition explicitly
3. choose the specific operator within that visible pool

This preserves apples-to-apples fairness with `union`.

## 8. Required Audits And Invariants

The repair must ship with auditable invariants.

### 8.1 Contract Invariants

1. No silent phase mismatch between:
  - `policy_phase`
  - `regime_panel.phase`
  - retrieval query phase
2. If fallback retrieval phases exist, they are trace-visible.

### 8.2 Visibility Invariants

1. A positive route family cannot be fully hidden in recover/preserve without a
   trace-visible suppress reason.
2. Under gradient pressure, `congestion_relief` or `hotspot_spread` visibility
   must stop collapsing to zero by construction.
3. Under tight/full sink budget, `budget_guard` must remain comparable.

### 8.3 Phase Invariants

1. Post-feasible recover share must drop materially from the current near-total
   occupation.
2. Preserve must appear as a sustained regime, not only as a one- or two-event
   flicker.
3. Expand must become reachable in at least some checked runs.

## 9. Validation Gates

The repair has two gate classes.

### 9.1 Structural Gates

These must pass before performance claims.

1. Focused tests covering:
  - phase alignment
  - recover exit semantics
  - positive-credit visibility restoration
  - preserve/expand activation
2. Audit reports showing:
  - hidden positive credit count reduced to zero or explained only by explicit
    stronger-negative suppression
  - no silent recover/preserve retrieval mismatch
  - non-trivial preserve occupancy
  - non-zero expand availability

### 9.2 Performance Gates

After the structural gates pass, rerun the official `s2_staged` `llm` mode and
re-answer all paper-facing questions:

1. Does `llm` still beat `union` on optimizer first feasible?
2. Does `llm` now beat `union` on PDE first feasible?
3. Does `llm` keep the final hypervolume lead?
4. Does `llm` widen the Pareto front instead of only strengthening one point?
5. If `llm` still does not fully win, is the remaining bottleneck in:
  - recover
  - preserve
  - expand

## 10. Non-Goals

This repair does not:

- redesign `s2_staged` scenario physics again
- change the shared operator registry membership
- weaken fairness by letting `llm` see a controller-private pool
- claim success before a new official rerun exists

## 11. Implementation Targets

Primary code targets:

- `/home/hymn/msfenicsx/optimizers/operator_pool/domain_state.py`
- `/home/hymn/msfenicsx/optimizers/operator_pool/state_builder.py`
- `/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py`
- `/home/hymn/msfenicsx/optimizers/operator_pool/reflection.py`
- `/home/hymn/msfenicsx/optimizers/operator_pool/prompt_projection.py`
- `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py`
- `/home/hymn/msfenicsx/optimizers/analytics/staged_audit.py`

Primary focused tests:

- `/home/hymn/msfenicsx/tests/generator/test_s2_staged_template.py`
- `/home/hymn/msfenicsx/tests/optimizers/test_s2_staged_baseline.py`
- `/home/hymn/msfenicsx/tests/optimizers/test_s2_staged_controller_audit.py`
- `/home/hymn/msfenicsx/tests/optimizers/test_llm_policy_kernel.py`
- `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller.py`
- `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller_state.py`
