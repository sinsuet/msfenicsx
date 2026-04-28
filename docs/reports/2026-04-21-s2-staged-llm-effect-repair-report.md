# S2 Staged LLM Effect Repair Report

## 1. Purpose

This report is a detailed handoff for continuing the `s2_staged` LLM-effect
repair line in a new conversation.

It records:

- the active experiment boundary
- the problem background behind the current `s2_staged` route
- the main implementation and analysis problems encountered in this cycle
- the fixes that were completed and merged back into the main workspace
- the newest evidence from the latest official rerun now stored on `main`
- the remaining bottlenecks
- the recommended next repair direction

This document is intentionally operational. It is not only a narrative summary;
it also points to the concrete files, traces, and run artifacts needed for the
next fix cycle.

---

## 2. Current Continuation Boundary

Continue from:

- repo root:
  - `/home/hymn/msfenicsx`
- environment:
  - `/home/hymn/miniconda3/bin/conda run -n msfenicsx ...`
- active paper-facing S2 route:
  - `s2_staged`

Do not continue from the old inline worktree:

- removed worktree:
  - `/home/hymn/msfenicsx/.worktrees/s2-staged-inline`

That worktree has already been merged back into the main workspace where needed,
and its latest official run was copied into the main tree and rerendered there.

The most important current evidence roots are:

- current design:
  - `docs/superpowers/specs/2026-04-20-s2-staged-joint-design.md`
- current implementation plan:
  - `docs/superpowers/plans/2026-04-20-s2-staged-joint-implementation.md`
- old official staged run:
  - `/home/hymn/msfenicsx/scenario_runs/s2_staged/0420_1841__raw_union_llm`
- old official comparison bundle:
  - `/home/hymn/msfenicsx/scenario_runs/comparisons/s2_staged_0420_1841__raw_union_llm`
- newest official rerun now on main:
  - `/home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm`
- newest suite-owned comparison bundle on main:
  - `/home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm/comparisons`

---

## 3. Background

### 3.1 Paper Ladder And Fairness Constraint

The active S2 paper ladder remains:

- `raw`
- `union`
- `llm`

The intended paper claim is still a controller claim, not an operator-pool
claim:

- `raw` is the matched native baseline
- `union` uses the shared mixed operator registry with random-uniform control
- `llm` must use the same shared mixed operator registry as `union`
- the only paper-facing difference between `union` and `llm` should be the
  controller policy

That fairness constraint remains the core boundary for all continuing work.

### 3.2 Why `s2_staged` Exists

This line exists because the earlier scenario-first S2 attempt did not create a
controller-sensitive first-feasible regime. The redesign in `s2_staged` was
meant to force the benchmark into a staged shape where:

1. the shared prefix stays infeasible
2. first feasible entry becomes controller-sensitive
3. post-feasible progress still requires semantic route shaping before native
   finishing dominates

### 3.3 Honesty Boundary

This line still does **not** justify any claim that `llm` has already beaten
`union` on first-feasible entry in the current official rerun.

The old official `s2_staged` run at:

- `/home/hymn/msfenicsx/scenario_runs/s2_staged/0420_1841__raw_union_llm`

had the historically important first-feasible numbers:

- `raw first_feasible_eval = 73`
- `union first_feasible_eval = 48`
- `llm first_feasible_eval = 57`

The newest official rerun on main did **not** improve that headline result.
Details are in Section 7.

---

## 4. Problems Encountered In This Cycle

### 4.1 Shared Prefix And First-Feasible Metrics Were Easy To Misread

This line used multiple related but different counters:

- history row index
- optimizer `evaluation_index`
- PDE solve count
- the new comparison summary field `first_feasible_pde_eval`

That created ambiguity when comparing:

- older official notes based on optimizer eval index
- newer comparison bundles based on PDE solve counts
- helper audits that include the repaired baseline as history row `1`

Operationally, the safest rule is:

- use `optimization_result.json -> history` for optimizer-eval claims
- use comparison `summary_rows.json` for PDE-solve claims
- treat helper row numbers as audit aids, not paper-facing metrics

### 4.2 Convert-Stage Visibility Was Still Too Stable-Biased

Before the recent fixes, `prefeasible_convert` could still collapse into an
effectively stable-only window on the request side, even though several semantic
families were already state-applicable.

In practice that meant:

- `route_family_mode = none`
- `semantic_trial_mode = none`
- the visible/effective pool often exposed only stable families

This directly undermined the staged-design goal that first-feasible entry should
be decided in a route-family-aware convert window.

### 4.3 Reflection And Retrieval Were Polluted By Penalty-Coded Failures

Cheap-screen and other penalty-coded failures were entering reflection and
retrieval as if they were ordinary numerical violation transitions.

That was dangerous because:

- `1e12`-scale penalty records could dominate average violation deltas
- the retrieval panel could show misleadingly strong positive prefeasible
  evidence
- reflection credit could incorrectly promote or demote operators based on
  penalty artifacts rather than real physical progress

This was one of the most important root-cause issues in the reflection chain.

### 4.4 Mixed Penalty + Real Improvement Evidence Was Misclassified

Even after separating penalty-coded records from ordinary deltas, one subtle
retrieval bug remained:

- a regime bucket containing both
  - one penalty event
  - one real violation improvement
- could still be placed in both:
  - `positive_matches`
  - `negative_matches`

That made the prompt surface internally inconsistent and could still bias the
controller toward unstable interpretations of the same route family.

### 4.5 Post-Feasible Recover Still Collapses The Actionable Pool

After the convert-side fixes, the major remaining bottleneck moved downstream.

In the newest official rerun, positive semantic route credit can already appear
in the prompt, but `post_feasible_recover` still filters those credited families
out of the effective candidate pool too often.

This is now the most important unresolved controller problem.

### 4.6 The Latest Run Initially Carried Old Visualization Outputs

The newest official rerun was first produced inside the now-removed inline
worktree, and its original comparison bundle used the older comparison output
set.

That was not a numerical bug, but it created a documentation and continuation
problem:

- the current main workspace had newer visualization/logging code
- the copied run initially still carried the older comparison figures

This was cleaned up by migrating the run into main and rerendering it there.

---

## 5. What Was Implemented And Fixed

### 5.1 Audit Harness For Staged Controller Analysis

The staged analysis helpers now live in:

- `optimizers/analytics/staged_audit.py`

Key helpers:

- `compare_history_prefix_by_mode(...)`
- `summarize_llm_prompt_surface(...)`
- unique `decision_id` accounting for controller-phase summaries

These helpers make it possible to audit:

- where the shared prefix ends
- which prompt-side route families were visible
- which route families were filtered
- whether route-family mode was active
- whether semantic trial mode was active

without manually scraping prompt markdown first.

### 5.2 Convert-Stage Route-Family Surface Was Opened Up

The staged controller redesign already in main now allows:

- `prefeasible_convert`
- bounded semantic entry
- request-side `route_family_mode`
- request-side `semantic_trial_mode`

The request surface now records:

- `route_family_mode`
- `route_family_candidates`
- `semantic_trial_mode`
- `visible_route_families`
- `filtered_route_families`

via the controller request trace path and audit helpers.

### 5.3 Penalty-Coded Reflection Pollution Was Repaired

The key repair merged back into main in this cycle was:

- `optimizers/operator_pool/reflection.py`
- `optimizers/operator_pool/state_builder.py`
- `tests/optimizers/test_llm_controller_state.py`

What changed:

- penalty-coded records are now detected explicitly
- penalty transitions increment `penalty_event_count`
- penalty transitions do **not** contribute ordinary violation deltas
- route/regime credit records now preserve penalty counts separately
- retrieval evidence now exposes:
  - `route_family`
  - `penalty_event_count`

This means prompt retrieval can now distinguish:

- real helpful evidence
- real harmful evidence
- penalty-coded failure episodes

instead of flattening them into one misleading scalar history.

### 5.4 Mixed Retrieval Classification Was Repaired

`state_builder` was further fixed so that:

- `positive_matches` require `penalty_event_count <= 0`

This prevents one mixed regime bucket from appearing as both positive and
negative route evidence.

### 5.5 Mainline Integration And Rerendering Were Completed

The inline worktree is gone. The relevant code and evidence now live in main.

Merged repair files:

- `optimizers/operator_pool/reflection.py`
- `optimizers/operator_pool/state_builder.py`
- `tests/optimizers/test_llm_controller_state.py`

The newest run was copied into:

- `/home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm`

Then rerendered on main with the current asset pipeline, producing the newer
comparison outputs:

- `comparisons/figures/summary_overview.png`
- `comparisons/figures/progress_dashboard.png`
- `comparisons/figures/final_layout_comparison.png`
- `comparisons/figures/temperature_field_comparison.png`
- `comparisons/figures/gradient_field_comparison.png`

The new per-mode/per-seed timeline summary also exists on main, for example:

- `/home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm/llm/summaries/progress_timeline__seed-11.jsonl`

---

## 6. Fresh Verification Already Completed On Main

Focused suite rerun on the main workspace:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/generator/test_s2_staged_template.py \
  tests/optimizers/test_s2_staged_baseline.py \
  tests/optimizers/test_s2_staged_controller_audit.py \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_llm_controller_state.py \
  -v
```

Fresh result on main:

- `58 passed`

This validates that the penalty/retrieval fixes were successfully integrated
back into the main workspace after the worktree was removed.

---

## 7. Current Evidence From The Latest Official Rerun

### 7.1 Artifact Roots

Newest official rerun on main:

- `/home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm`

Newest suite-owned comparison bundle on main:

- `/home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm/comparisons`

Most useful evidence files:

- comparison summary:
  - `/home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm/comparisons/analytics/summary_rows.json`
- comparison timeline rollups:
  - `/home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm/comparisons/analytics/timeline_rollups.json`
- LLM runtime summary:
  - `/home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm/llm/summaries/llm_runtime_summary.json`
- LLM decision summary:
  - `/home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm/llm/summaries/llm_decision_summary.json`
- request trace:
  - `/home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm/llm/seeds/seed-11/traces/llm_request_trace.jsonl`
- response trace:
  - `/home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm/llm/seeds/seed-11/traces/llm_response_trace.jsonl`

### 7.2 Runtime Stability

The current run is **not** blocked by transport instability.

From `llm_runtime_summary.json`:

- provider: `openai-compatible`
- model: `gpt-5.4`
- request count: `156`
- response count: `156`
- fallback count: `0`
- retry count: `0`

So the live problem is controller policy quality, not API reliability.

### 7.3 First-Feasible Metrics

Important metric note:

- old historical comparisons often quoted optimizer `evaluation_index`
- the new main comparison bundle reports `first_feasible_pde_eval`

Both are useful, but they are not the same number.

#### Optimizer-Eval First Feasible

Derived from `optimization_result.json -> history`:

| mode | optimizer evals | first_feasible_eval |
| --- | ---: | ---: |
| raw | 200 | 73 |
| union | 200 | 48 |
| llm | 200 | 66 |

Conclusion:

- `llm` still does **not** beat `union` on first-feasible optimizer eval
- `llm` regressed relative to the old official `0420_1841` result (`57 -> 66`)

#### PDE-Solve First Feasible

Derived from the new comparison summary schema:

| mode | pde_evaluations | solver_skipped_evaluations | first_feasible_pde_eval |
| --- | ---: | ---: | ---: |
| raw | 140 | 60 | 40 |
| union | 155 | 45 | 20 |
| llm | 146 | 54 | 38 |

Conclusion:

- `llm` also does **not** beat `union` on first-feasible PDE efficiency
- `llm` is slightly better than `raw` on first-feasible PDE solves
- the extra cheap-screen skips in `llm` do not translate into earlier feasible
  entry

### 7.4 Final Pareto Quality

From the newest comparison summary on main:

| mode | front_size | final_hypervolume | best_temperature_max | best_gradient_rms |
| --- | ---: | ---: | ---: | ---: |
| raw | 2 | 516.6124094618752 | 319.51091723025024 | 13.576563017513323 |
| union | 4 | 330.57376222166533 | 322.8734345968548 | 15.698968255335402 |
| llm | 3 | 439.9770054012587 | 319.33720818828965 | 14.530363367535628 |

Conclusion:

- `llm` beats `union` on final Pareto quality
- `llm` does **not** beat `raw` on final Pareto quality

This is a mixed result:

- better controller-guided final tradeoff shaping than `union`
- but still not the desired comprehensive paper-facing dominance story

### 7.5 Prompt-Surface Summary

Using `summarize_llm_prompt_surface(...)` on the newest request trace:

- request count: `156`
- effective candidate pool size: `1-5`
- `route_family_mode_counts`:
  - `none: 17`
  - `convert_family_mix: 31`
  - `recover_family_mix: 108`
- `semantic_trial_mode_counts`:
  - `none: 125`
  - `encourage_bounded_trial: 31`
- visible route family counts:
  - `stable_global: 113`
  - `stable_local: 96`
  - `sink_retarget: 112`
  - `budget_guard: 62`
  - `congestion_relief: 31`
- filtered route family counts:
  - `hotspot_spread: 141`
  - `layout_rebalance: 141`
  - `congestion_relief: 141`
  - `sink_retarget: 107`
  - `budget_guard: 79`
  - `stable_local: 65`
  - `stable_global: 43`

Key reading:

- convert-side route-family activation is now real
- semantic visibility still contracts heavily after feasibility
- `hotspot_spread` remains the most persistently hidden family

### 7.6 Key Prompt-Level Observations

#### First Convert Request

First convert request:

- decision id: `g003-e0042-d15`
- evaluation index: `42`

Observed request-side state:

- `route_family_mode = convert_family_mix`
- `semantic_trial_mode = encourage_bounded_trial`
- visible route families:
  - `budget_guard`
  - `congestion_relief`
  - `stable_global`
  - `stable_local`

This confirms the convert-stage visibility fix is live.

#### First Post-Feasible Recover Request

First post-feasible recover request:

- decision id: `g005-e0082-d48`
- evaluation index: `82`

Visible families:

- `sink_retarget`
- `stable_global`
- `stable_local`

Filtered families:

- `budget_guard`
- `congestion_relief`
- `hotspot_spread`
- `layout_rebalance`
- `sink_retarget`

But the prompt retrieval panel at that same request already contains positive
semantic evidence for:

- `reduce_local_congestion` -> `congestion_relief`
- `repair_sink_budget` -> `budget_guard`

This is the central contradiction of the current line:

- positive semantic route credit is already in the prompt
- yet those same semantic families are not allowed into the actionable pool

#### Late Recover Still Narrows Down

Late recover sample:

- decision id: `g010-e0182-d136`
- evaluation index: `182`

Visible families:

- `budget_guard`
- `sink_retarget`

Filtered families:

- `congestion_relief`
- `hotspot_spread`
- `layout_rebalance`
- `stable_global`
- `stable_local`

This shows the late-run pool still does not broaden into a more expressive
post-feasible semantic search.

#### Hidden Positive Route Credit Count

Count of requests where positive retrieval credit exists for one or more route
families that are still hidden from the visible pool:

- `94`

This is the strongest compact statistic for the remaining bottleneck.

### 7.7 Current Selection Behavior

From `llm_decision_summary.json`:

- unique decisions: `156`
- fallback selections: `0`
- valid LLM selections: `156`
- phase counts:
  - `prefeasible_stagnation: 15`
  - `prefeasible_convert: 33`
  - `post_feasible_recover: 108`

Important consequence:

- there were no live `post_feasible_preserve` controller decisions in this run
- there were no live `post_feasible_expand` controller decisions in this run

Overall operator counts:

- `local_refine: 40`
- `native_sbx_pm: 29`
- `move_hottest_cluster_toward_sink: 29`
- `repair_sink_budget: 16`
- `reduce_local_congestion: 15`
- `global_explore: 15`
- `slide_sink: 12`

Post-feasible recover operator counts only:

- `move_hottest_cluster_toward_sink: 28`
- `local_refine: 24`
- `native_sbx_pm: 15`
- `repair_sink_budget: 15`
- `global_explore: 14`
- `slide_sink: 12`

Notably absent from post-feasible recover:

- `reduce_local_congestion`

So congestion relief appears in this run, but only before feasibility, not as a
meaningful post-feasible recovery route.

---

## 8. What Is Solved

The following points are meaningfully improved relative to the earlier staged
line and are not the main blocker anymore:

1. `prefeasible_convert` is no longer purely stable-only on the request side.
2. Route-family reasoning now appears before first feasible in live traces.
3. Bounded semantic trial activation exists in the convert window.
4. Penalty-coded retrieval pollution has been repaired.
5. Mixed penalty + real improvement evidence no longer appears as a false
   positive retrieval match.
6. Request-side traces now expose the route-family surface directly enough to
   audit.
7. The newest official rerun and its comparison bundle now live in the main
   workspace and have been rerendered with the current visualization/logging
   architecture.

---

## 9. What Is Still Not Solved

### 9.1 `llm` Still Does Not Beat `union` On First Feasible

This remains the primary unresolved paper-facing issue.

Current newest official rerun:

- `union first_feasible_eval = 48`
- `llm first_feasible_eval = 66`
- `union first_feasible_pde_eval = 20`
- `llm first_feasible_pde_eval = 38`

### 9.2 Recover Still Hides Semantically Credited Families

This is now the strongest root-cause hypothesis.

The crucial pattern is:

- reflection/retrieval credit is now better
- positive semantic evidence enters the prompt
- but `post_feasible_recover` still filters those families out of the actionable
  candidate pool

### 9.3 `hotspot_spread` Is Still Structurally Starved

This matters because earlier historical analysis of the old official run
pointed to `spread_hottest_cluster` as the important union-side first-feasible
route.

Current newest rerun still shows:

- `hotspot_spread` filtered `141` times

So the route family most likely to replicate the old union entry advantage is
still mostly unavailable to `llm`.

### 9.4 Objective-Balance Gradient Pressure Is Not Activating Live

The newest prompt-surface summary reports:

- `gradient_improve.request_count = 0`

That suggests a second-order issue:

- even when congestion families are state-relevant, the objective-balance layer
  is not frequently framing the problem as explicit gradient-pressure recovery

This is likely downstream of the recover gating, but it may also need its own
follow-up calibration.

### 9.5 No Live Expand Phase Yet

The reflection code and tests now support broader route-family credit, but the
newest official rerun still never reached a live `post_feasible_expand`
controller phase.

That means:

- expand-side logic is still largely unvalidated by live evidence in this run
- the next fix cycle should prioritize unlocks earlier in the chain rather than
  starting with expand-specific tuning

---

## 10. Recommended Next Repair Direction

### 10.1 Primary Recommendation

Focus next on **post-feasible recover candidate-pool logic**, not on transport,
not on further penalty cleanup, and not on benchmark retuning first.

The most important current code locations are:

- `optimizers/operator_pool/policy_kernel.py`
  - `_post_feasible_candidate_filter(...)`
  - `_gradient_balance_escape_candidates(...)`
  - `_restore_semantic_visibility(...)`
  - `_rank_semantic_candidates(...)`
- `optimizers/operator_pool/llm_controller.py`
  - request-side decision axis construction and route-family trace fields
- `optimizers/operator_pool/state_builder.py`
  - retrieval panel construction
- `optimizers/operator_pool/reflection.py`
  - route/regime credit accounting

### 10.2 Concrete Repair Hypothesis

The next fix should make recover visibility retrieval-aware.

Specifically:

1. when `positive_matches` already contain non-stable route families with clean
   evidence
2. and those families are state-applicable
3. and their recent regression risk is not dominant

then `post_feasible_recover` should guarantee that at least one such family
enters the effective candidate pool, instead of letting the stable-preserve
filter suppress it completely.

This should be done as a **portable policy rule**, not a benchmark-specific
allowlist hack.

### 10.3 Specific Candidate Changes To Try

Recommended order:

1. In `_post_feasible_candidate_filter(...)`, add a retrieval-aware semantic
   visibility floor for `post_feasible_recover`.
2. In `_restore_semantic_visibility(...)`, change ranking so families with
   positive retrieval credit can outrank semantically weaker but historically
   safer preserve routes when recover is clearly stalled.
3. In `_rank_semantic_candidates(...)`, allow route-family credit from
   `positive_matches` to influence recover ranking, not only static role and
   evidence-level fields.
4. Recheck whether `gradient_improve` should activate more aggressively once
   positive congestion-route evidence exists but recover is stagnating.

### 10.4 Tests To Add Before The Next Implementation Pass

Recommended focused tests:

1. A `policy_kernel` test showing that `post_feasible_recover` surfaces a
   semantically credited route family when retrieval positive matches exist.
2. A `policy_kernel` test showing that `hotspot_spread` is not always filtered
   when:
   - positive retrieval credit exists
   - compact hotspot state still applies
   - regression risk is not dominant.
3. A `state_builder` or controller-state test proving that positive retrieval
   credit for a family can be consumed by recover visibility rules.
4. An audit test asserting the number of requests with hidden positive route
   credit drops materially from the current `94`.

### 10.5 Acceptance Target For The Next Official Rerun

Do not declare success merely because final Pareto quality remains good.

The next fix should be judged against all of:

1. `llm first_feasible_eval < union first_feasible_eval`
2. `llm first_feasible_pde_eval < union first_feasible_pde_eval`
3. `llm` retains at least its current final-Pareto advantage over `union`
4. prompt-surface audit shows:
   - lower `hidden_positive_route_requests`
   - lower `hotspot_spread` filtering frequency
   - more post-feasible semantic-family visibility

Only after a new official rerun meets those conditions should any stronger
paper-facing claim be considered.

---

## 11. Suggested Starting Commands For The Next Conversation

Re-read the core docs first:

```bash
sed -n '1,260p' /home/hymn/msfenicsx/AGENTS.md
sed -n '1,260p' /home/hymn/msfenicsx/docs/reports/2026-04-21-s2-staged-llm-effect-repair-report.md
sed -n '1,260p' /home/hymn/msfenicsx/docs/superpowers/specs/2026-04-20-s2-staged-joint-design.md
sed -n '1,260p' /home/hymn/msfenicsx/docs/superpowers/plans/2026-04-20-s2-staged-joint-implementation.md
```

Run the focused staged/controller suite:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/generator/test_s2_staged_template.py \
  tests/optimizers/test_s2_staged_baseline.py \
  tests/optimizers/test_s2_staged_controller_audit.py \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_llm_controller_state.py \
  -v
```

Re-audit the newest official rerun:

```bash
/home/hymn/miniconda3/envs/msfenicsx/bin/python - <<'PY'
import json
from pathlib import Path
from optimizers.analytics.staged_audit import compare_history_prefix_by_mode, summarize_llm_prompt_surface

suite = Path('/home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm')
roots = {mode: suite / mode / 'seeds' / 'seed-11' for mode in ['raw', 'union', 'llm']}
print(compare_history_prefix_by_mode(roots, prefix_rows=40))
rows = [json.loads(line) for line in (roots['llm'] / 'traces' / 'llm_request_trace.jsonl').open()]
print(summarize_llm_prompt_surface(rows, run_root=roots['llm']))
PY
```

After the next controller fix, rerun the official suite with conservative
parallelism:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli run-benchmark-suite \
  --optimization-spec scenarios/optimization/s2_staged_raw.yaml \
  --optimization-spec scenarios/optimization/s2_staged_union.yaml \
  --optimization-spec scenarios/optimization/s2_staged_llm.yaml \
  --mode raw \
  --mode union \
  --mode llm \
  --llm-profile default \
  --benchmark-seed 11 \
  --evaluation-workers 2 \
  --scenario-runs-root ./scenario_runs
```

---

## 12. Bottom Line

This cycle did **not** solve the headline paper problem, but it did move the
diagnosis forward in an important way.

The strongest current interpretation is now:

- the benchmark is no longer the primary blocker
- transport is not the blocker
- penalty-coded reflection pollution is no longer the primary blocker
- convert-stage route-family visibility is now real
- the current dominant bottleneck is post-feasible recover gating, where
  semantically useful families can already earn positive prompt-visible credit
  but are still filtered out of the actionable pool

That is the next repair target.
