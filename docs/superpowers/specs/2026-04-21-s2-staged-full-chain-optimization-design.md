# S2 Staged Full-Chain Optimization Design

> Status: active next-cycle design for the paper-facing `s2_staged` controller line.
>
> Workspace policy for this cycle: continue directly on `main`; do not create
> or depend on any deleted worktree.

## 1. Decision Summary

The previous repair cycle fixed the broad contract breakages in `s2_staged`.
The next cycle should not repeat a generic recover tweak. The bottleneck has
become a full-chain activation problem:

1. `prefeasible_convert` still enters as a stable-only window, so `llm` wins
   optimizer first-feasible timing but still loses PDE first-feasible timing to
   `union`.
2. `post_feasible_recover` still monopolizes the entire post-feasible budget, so
   the controller never reaches live `preserve` or `expand`.
3. the remaining hidden positive credit is now concentrated in
   `stable_local`, which indicates a macro-to-micro handoff failure rather than
   a general retrieval mismatch.
4. `expand`-side diversity logic exists in code but never becomes an operating
   regime, so final front diversity collapses to a single-point outcome.

The recommended next design is a staged chain repair:

- `convert entry -> preserve dwell -> stable-local handoff -> expand diversity`

This keeps the shared operator registry fixed and continues to treat the
paper-facing difference between `union` and `llm` as a controller-only change.

## 2. Honesty Boundary

The checked evidence for this design comes from:

- new `llm` rerun root:
  - `/home/hymn/msfenicsx/scenario_runs/s2_staged`
- comparison bundle built from old official `raw/union` plus the new `llm`
  rerun:
  - `/home/hymn/msfenicsx/scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair`

The current honest status is:

- optimizer first feasible:
  - `llm = 47`
  - `union = 48`
  - `raw = 73`
- PDE first feasible:
  - `llm = 23`
  - `union = 20`
  - `raw = 40`
- final hypervolume:
  - `llm = 580.7972666760692`
  - `raw = 516.6124094618752`
  - `union = 330.57376222166533`
- final front size:
  - `llm = 1`
  - `raw = 2`
  - `union = 4`

So this is no longer a story of `llm` globally losing. The unresolved story is
more specific:

- `llm` now beats `union` on optimizer first-feasible timing
- `llm` still does not beat `union` on PDE first-feasible timing
- `llm` still keeps the best single-point quality and hypervolume
- `llm` still does not own the broadest final Pareto front

## 3. Evidence Basis

The active design and implementation context remains:

- `/home/hymn/msfenicsx/docs/reports/2026-04-21-s2-staged-llm-effect-repair-report.md`
- `/home/hymn/msfenicsx/docs/superpowers/specs/2026-04-20-s2-staged-joint-design.md`
- `/home/hymn/msfenicsx/docs/superpowers/plans/2026-04-20-s2-staged-joint-implementation.md`
- `/home/hymn/msfenicsx/docs/superpowers/specs/2026-04-21-s2-staged-recover-chain-repair-design.md`
- `/home/hymn/msfenicsx/docs/superpowers/plans/2026-04-21-s2-staged-recover-chain-repair.md`

The key runtime evidence is:

- compare summary:
  - `/home/hymn/msfenicsx/scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair/analytics/summary_rows.json`
- request trace:
  - `/home/hymn/msfenicsx/scenario_runs/s2_staged/traces/llm_request_trace.jsonl`
- controller trace:
  - `/home/hymn/msfenicsx/scenario_runs/s2_staged/traces/controller_trace.jsonl`

The most important implementation surfaces remain:

- `/home/hymn/msfenicsx/optimizers/operator_pool/domain_state.py`
- `/home/hymn/msfenicsx/optimizers/operator_pool/state_builder.py`
- `/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py`
- `/home/hymn/msfenicsx/optimizers/operator_pool/reflection.py`
- `/home/hymn/msfenicsx/optimizers/operator_pool/prompt_projection.py`
- `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py`
- `/home/hymn/msfenicsx/optimizers/analytics/staged_audit.py`

## 4. Root-Cause Diagnosis

### 4.1 Convert Still Fails To Open A Real Entry Window

The latest rerun shows:

- `prefeasible_convert` decision count = `15`
- `convert route_family_mode_counts = {"none": 15}`
- `convert semantic_trial_mode_counts = {"none": 15}`
- visible families in convert are only:
  - `stable_global`
  - `stable_local`
- suppressed families in convert across all `15` requests:
  - `budget_guard = 15`
  - `congestion_relief = 15`
  - `hotspot_spread = 15`
  - `layout_rebalance = 15`
  - `sink_retarget = 15`

So the contract is repaired enough to name `prefeasible_convert`, but the live
convert window still behaves like a stable-only shortlist. That explains why
`llm` can already beat `union` on optimizer first-feasible timing while still
missing on PDE first-feasible timing: the controller is entering feasibility
without using the full staged semantic entry surface.

### 4.2 Recover Still Owns The Entire Post-Feasible Budget

The live run now has:

- `decision_count = 154`
- `phase_counts = {"prefeasible_stagnation": 15, "prefeasible_convert": 15, "post_feasible_recover": 124}`
- `post_feasible_preserve = 0`
- `post_feasible_expand = 0`
- `recover_exit_ready = False` on all `124` recover requests

This means the chain is still:

- `first feasible -> recover forever`

rather than:

- `first feasible -> recover -> preserve -> expand`

The previous repair made recover coherent and less contradictory, but it did
not make preserve dwell long enough to become a stable live phase.

### 4.3 Remaining Hidden Positive Credit Has Concentrated Into Stable-Local Handoff

The new audit now reports:

- `phase_mismatch_count = 0`
- `hidden_positive_credit_requests = 42`
- `hidden_positive_credit_family_counts = {"stable_local": 42}`

This is an important shift. The old problem was a general contract mismatch.
The new problem is narrower:

- retrieval still discovers `stable_local`-positive evidence in regimes that
  matter
- the effective candidate surface still hides that positive family in `42`
  requests

That indicates a macro-to-micro handoff failure after useful semantic progress,
not a broad retrieval collapse.

### 4.4 Recover Visibility Is Still Too Narrow For Diversity Growth

The new recover audit still shows:

- `recover_pool_size_summary = {"count": 124, "min": 1, "max": 4, "avg": 3.4274193548387095}`

Across recover requests, suppression remains heavy:

- `budget_guard` suppressed `124` times
- `hotspot_spread` suppressed `124` times
- `sink_retarget` suppressed `124` times
- `congestion_relief` suppressed `105` times
- `layout_rebalance` suppressed `50` times

Recover has become more coherent, but not broad enough to seed the next phase.
That is why the run still lands on a strong single point while failing to grow
front diversity.

### 4.5 Expand Logic Exists But Never Activates

The current codebase already contains:

- expand-budget annotations in `policy_kernel.py`
- expand-fit and frontier evidence in `state_builder.py`
- expand saturation tracking in `domain_state.py`

But the live run shows zero expand occupancy. That means diversity is currently
blocked upstream. Injecting more expand rules without fixing convert and
preserve would likely create noisy regressions rather than real Pareto growth.

## 5. Design Goals

### 5.1 Outcome Goals

The next cycle should target all of the following on the checked seed:

1. keep `llm` ahead of `union` on optimizer first-feasible timing
2. improve `llm` enough to beat `union` on PDE first-feasible timing
3. preserve the current `llm` hypervolume advantage
4. produce non-zero live `preserve` occupancy
5. produce non-zero live `expand` occupancy after preserve exists
6. improve final front diversity beyond the current `front_size = 1`

### 5.2 Structural Goals

1. `prefeasible_convert` must become family-aware, not just phase-labeled.
2. `post_feasible_recover` must hand off into a durable preserve window.
3. positive `stable_local` credit must become visible during the handoff window.
4. `expand` must activate only after preserve is live, not by shortcutting the
   chain.

### 5.3 Fairness Goals

1. `union` and `llm` keep the same shared operator registry.
2. no benchmark-id hardcoding
3. no seed-specific exceptions
4. no one-off prompt hacks that bypass controller state

## 6. Considered Approaches

### 6.1 Approach A: Keep Tuning Recover Alone

This would:

- relax recover filters again
- try to expose more families inside recover
- hope preserve and expand appear as a side effect

This is not recommended. The current evidence shows the main missing link is
upstream convert activation and downstream preserve dwell, not just recover
breadth.

### 6.2 Approach B: Push Expand Diversity First

This would:

- add stronger expand entry rules
- try to force more semantic diversity quickly

This is also not recommended. With zero live preserve occupancy, forcing expand
earlier is likely to trade away the newly won hypervolume and first-feasible
advantage.

### 6.3 Approach C: Repair The Chain In Order

This would:

1. open convert with state-conditioned family floors
2. make recover hand off into preserve with explicit dwell and hysteresis
3. make positive `stable_local` handoff visible during recover/preserve
4. activate expand only after preserve is actually live

This is the recommended approach because it matches the current evidence:
`llm` is already strong enough at single-point quality, so the next gains need
to come from chain continuity rather than from a new source of raw aggression.

## 7. Recommended Design

### 7.1 Convert Entry Repair

`prefeasible_convert` should stop behaving like a stable-only shortlist.

The design change is:

- keep the stable floor:
  - `native_sbx_pm`
  - `global_explore`
  - `local_refine`
- add state-conditioned semantic entry floors when convert is active

The convert family floors should be driven by actual state:

- show `budget_guard` when sink budget is `tight` or `full_sink`
- show `sink_retarget` when the hotspot is outside the sink corridor and peak
  pressure dominates
- show `congestion_relief` or `layout_rebalance` when local congestion or
  gradient pressure is already visible
- allow `hotspot_spread` only when the hotspot is already sink-aligned and the
  semantic move is a bounded trial rather than a speculative detour

This requires three surfaces to agree:

- `policy_kernel.py` must preserve at least one operator per active convert
  family floor
- `llm_controller.py` must expose a non-`none` convert
  `route_family_mode` when those floors are active
- `state_builder.py` and `prompt_projection.py` must make the convert route
  surface and its fallbacks visible in the prompt metadata

The expected outcome is not generic diversity. It is specifically faster PDE
entry into feasibility.

### 7.2 Preserve Dwell And Hysteresis

The next live phase after recover must be preserve, and preserve must survive
for more than a single decision.

The design change is:

- derive a preserve-entry condition from cooled recover pressure
- once preserve is entered, keep it live for a minimum dwell window
- only allow re-entry to recover when new regression pressure exceeds a higher
  re-entry threshold than the one used for the original exit

This needs to be encoded in `domain_state.py` as explicit counters, not as an
implicit side effect. The controller should surface:

- `preserve_dwell_count`
- `preserve_dwell_remaining`
- `recover_reentry_pressure`

Then `policy_kernel.py` should consume those fields so phase transitions are
trace-visible and auditable.

The expected outcome is non-zero `post_feasible_preserve` occupancy on the live
run and a chain that can finally progress beyond recover.

### 7.3 Stable-Local Macro-To-Micro Handoff

The remaining hidden positive credit now points almost entirely to
`stable_local`. That suggests semantic progress is not handing off correctly to
the local micro-operators that should exploit it.

The design change is:

- when retrieval surfaces positive `stable_local` credit after convert or after
  a recover success, activate a short handoff window
- during that handoff window, preserve visibility for the stable-local micro
  family even if the broader phase filter would otherwise hide it
- keep the handoff window explicit in prompt metadata so the audit can see when
  and why it was active

This is not a new benchmark-specific rule. It is a generic controller rule:
when the controller has evidence that a route family recently improved the
current regime, the local exploiters for that family should remain visible long
enough to capitalize on the opening.

The expected outcome is:

- `hidden_positive_credit_family_counts["stable_local"] == 0`
- better feasible-set preservation after first feasible

### 7.4 Expand Activation And Diversity Floors

Only after preserve is live should the controller start spending explicit
attention on diversity growth.

The expand design should:

- trigger from preserve when feasibility is stable and frontier pressure remains
  high or front size remains narrow
- expose at least one underused frontier-growth family when expand is active
- keep bounded semantic trial behavior, not unbounded semantic spread

The preferred expand floors are:

- `hotspot_spread`
- `congestion_relief`
- `layout_rebalance`

with `budget_guard` remaining available when sink-span pressure is still a real
constraint rather than a solved condition.

The expected outcome is not necessarily that `llm` must beat `union` on front
size immediately, but that the live run finally produces real expand occupancy
and improves beyond `front_size = 1`.

## 8. Implementation Surfaces

The intended code ownership for the next cycle is:

- `domain_state.py`
  - derive explicit convert, preserve-dwell, and recover-reentry state
- `policy_kernel.py`
  - enforce family floors and phase-transition rules
- `state_builder.py`
  - project the new chain state into retrieval and prompt metadata
- `reflection.py`
  - expose compact handoff-credit summaries by route family and regime
- `prompt_projection.py`
  - keep prompt panels coherent after the new chain state is added
- `llm_controller.py`
  - expose convert/preserve/expand route-family modes and handoff cues in the
    LLM-facing decision axes and policy text
- `staged_audit.py`
  - summarize convert coverage, phase occupancy, handoff visibility, and
    remaining hidden-positive families

## 9. Validation Plan

The next implementation cycle should treat the following as hard gates:

1. focused TDD for each chain segment before implementation
2. required focused test gate:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/generator/test_s2_staged_template.py tests/optimizers/test_s2_staged_baseline.py tests/optimizers/test_s2_staged_controller_audit.py tests/optimizers/test_llm_policy_kernel.py tests/optimizers/test_llm_controller.py tests/optimizers/test_llm_controller_state.py -v
```

3. official `s2_staged` `llm` rerun after the focused gate passes
4. `render-assets` on the new run
5. external compare bundle against:
   - `/home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm/raw/seeds/seed-11`
   - `/home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm/union/seeds/seed-11`
   - the new `llm` run root

## 10. Success Criteria

This design should be considered successful only if the rerun evidence shows:

1. `llm` still beats or matches `union` on optimizer first-feasible timing
2. `llm` now beats `union` on PDE first-feasible timing
3. `llm` still leads on final hypervolume or remains within a defensible margin
4. live `preserve` occupancy is non-zero
5. live `expand` occupancy is non-zero
6. final front diversity improves beyond the current single-point collapse

If those goals are not all met, the post-rerun report must say exactly which
segment still fails:

- convert entry
- recover to preserve handoff
- stable-local handoff
- expand diversity growth
