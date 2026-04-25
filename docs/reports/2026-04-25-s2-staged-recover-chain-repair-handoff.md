# S2 Staged Recover-Chain Repair Handoff

## 1. Purpose

This document is the handoff note for continuing the paper-facing `s2_staged`
controller repair line in a fresh conversation.

It records:

- the repair background and honesty boundary
- the repair plan lineage that was followed
- what was actually changed during the latest execution cycle
- the latest verified benchmark state
- the remaining bottlenecks
- the recommended next repair steps

All paths below are repository-local absolute paths under
`/home/hymn/msfenicsx`.

## 2. Active Scope And Constraints

The active paper-facing S2 route is:

- `s2_staged`

The current comparison baseline roots are:

- old official suite:
  - `/home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm`
- old official raw seed root:
  - `/home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm/raw/seeds/seed-11`
- old official union seed root:
  - `/home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm/union/seeds/seed-11`

Execution constraints that were explicitly followed:

- all work stayed on `main`
- no new worktree was created
- no attempt was made to return to deleted old worktrees
- focused tests were run before every new official rerun
- no conclusion was claimed before rerun evidence existed

## 3. Source Design And Plan Lineage

The repair work was not started from scratch. It continued the existing
controller-side repair line defined in these documents:

- `/home/hymn/msfenicsx/docs/reports/2026-04-21-s2-staged-llm-effect-repair-report.md`
- `/home/hymn/msfenicsx/docs/superpowers/specs/2026-04-20-s2-staged-joint-design.md`
- `/home/hymn/msfenicsx/docs/superpowers/plans/2026-04-20-s2-staged-joint-implementation.md`
- `/home/hymn/msfenicsx/docs/superpowers/specs/2026-04-21-s2-staged-recover-chain-repair-design.md`
- `/home/hymn/msfenicsx/docs/superpowers/plans/2026-04-21-s2-staged-recover-chain-repair.md`

The continuation phase also read and used:

- `/home/hymn/msfenicsx/docs/superpowers/specs/2026-04-22-s2-staged-phase2-chain-release-design.md`
- `/home/hymn/msfenicsx/docs/superpowers/plans/2026-04-22-s2-staged-phase2-chain-release.md`

The design intent across these documents stayed consistent:

- keep the shared operator registry fixed
- repair only controller-side contracts
- preserve honesty about what `llm` has and has not beaten
- repair the chain in order:
  - current positive retrieval match visibility
  - recover release semantics
  - expand admission and diversity handling

## 4. Honesty Boundary Before This Cycle

At the start of this continuation, the user explicitly required that the old
stale narrative be retired.

The already-confirmed truth before the latest work was:

- `llm first_feasible_eval = 46`
- `union first_feasible_eval = 48`
- `raw first_feasible_eval = 73`
- `llm first_feasible_pde_eval = 23`
- `union first_feasible_pde_eval = 20`
- `raw first_feasible_pde_eval = 40`
- `llm final_hypervolume = 528.5815849955469`
- `raw final_hypervolume = 516.6124094618752`
- `union final_hypervolume = 330.57376222166533`
- `llm front_size = 1`
- `raw front_size = 2`
- `union front_size = 4`

So the real unresolved issues were:

- `llm` had not beaten `union` on PDE first feasible
- `llm` had not beaten `union` on final front diversity
- recover / preserve / expand chain behavior was still collapsing
- positive credit / visible pool / retrieval phase contracts still had structural faults

## 5. What Had Already Been Repaired Before The Final Latest Fix

Earlier in the same repair line, the following controller-side changes were
already in place:

- recover and expand visibility-floor restoration
- split audit and state signals:
  - `hidden_positive_match_requests`
  - `hidden_positive_credit_requests`
  - `positive_match_families`
  - `visibility_floor_families`
  - `recover_release_ready`
  - `recover_reentry_pressure`
  - `diversity_deficit_level`
  - `recover_release_evidence_active`
- direct `recover -> expand` gating support
- congestion-relief floor restoration
- restore positive route-family visibility during `prefeasible_convert`
- emit and trace exact positive retrieval match fields:
  - `exact_positive_match_mode`
  - `exact_positive_match_operator_ids`
  - `exact_positive_match_route_families`
- protect `budget_guard` visibility-floor operators from:
  - `recent_operator_dominance`
  - `generation_local_operator_dominance`

The key point is that the late-stage work below did not replace those fixes. It
built on them.

## 6. Root Cause Found In The Latest Iteration

After the visibility-floor and guardrail protections were in place, the newest
bad run evidence no longer pointed to "hidden positive evidence" as the main
problem.

The decisive finding was:

- positive route families were visible
- exact positive matches were exposed in `decision_axes`
- but the actual `candidate_operator_ids` sent to the model still kept the
  stable trio at the front of the list
- exact positive operators were often listed in positions `4+`

This created a soft contract only:

- the prompt said "prefer exact positive matches"
- the actual candidate pool ordering still privileged stable fallbacks

Live evidence from `/home/hymn/msfenicsx/scenario_runs/s2_staged/0422_2237__llm`
showed:

- `87` requests with `prefer_exact_match`
- the first exact positive operator was never first in the candidate list
- many convert decisions still fell back to `local_refine` or `native_sbx_pm`

That is why convert stayed too long even after hidden-positive counts fell to
zero.

## 7. Latest Code Change

The final minimal fix in this cycle was:

- reorder `candidate_operator_ids` before the LLM call so exact positive match
  operators are front-loaded when
  `exact_positive_match_mode == "prefer_exact_match"`

Implementation location:

- `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py`

Key entry points:

- candidate-order application:
  - `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py:174`
- exact-positive pool reordering helper:
  - `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py:1199`

The matching TDD regression test was added at:

- `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller.py:2745`

That test locks the contract:

- if exact positive match operators exist for a convert decision, they must be
  moved to the front of the candidate pool passed to the model

## 8. Focused Verification That Was Run

The required focused gate was rerun after the code change:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
tests/generator/test_s2_staged_template.py \
tests/optimizers/test_s2_staged_baseline.py \
tests/optimizers/test_s2_staged_controller_audit.py \
tests/optimizers/test_llm_policy_kernel.py \
tests/optimizers/test_llm_controller.py \
tests/optimizers/test_llm_controller_state.py -v
```

Result:

- `109 passed`

This was the last focused verification run before the newest official rerun.

## 9. Official Reruns And Comparison Bundles In This Cycle

Important reruns during the later repair line:

- `/home/hymn/msfenicsx/scenario_runs/s2_staged/0422_1908__llm`
- `/home/hymn/msfenicsx/scenario_runs/s2_staged/0422_2138__llm`
- `/home/hymn/msfenicsx/scenario_runs/s2_staged/0422_2208__llm`
- `/home/hymn/msfenicsx/scenario_runs/s2_staged/0422_2237__llm`
- latest official rerun after exact-positive front-loading:
  - `/home/hymn/msfenicsx/scenario_runs/s2_staged/0422_2311__llm`

Important compare bundles during this line:

- `/home/hymn/msfenicsx/scenario_runs/compare_reports/s2_staged/0422_1932__raw_union_old_vs_llm_convert_visibility_restore`
- `/home/hymn/msfenicsx/scenario_runs/compare_reports/s2_staged/0422_2201__raw_union_old_vs_llm_exact_positive_priority`
- `/home/hymn/msfenicsx/scenario_runs/compare_reports/s2_staged/0422_2233__raw_union_old_vs_llm_budget_guard_protection`
- compare for the final latest rerun:
  - `/home/hymn/msfenicsx/scenario_runs/compare_reports/s2_staged/0422_2332__raw_union_old_vs_llm_exact_frontload`

## 10. Latest Verified State

The current truth should be taken from:

- latest `llm` rerun:
  - `/home/hymn/msfenicsx/scenario_runs/s2_staged/0422_2311__llm`
- latest compare bundle:
  - `/home/hymn/msfenicsx/scenario_runs/compare_reports/s2_staged/0422_2332__raw_union_old_vs_llm_exact_frontload`

Latest verified metrics:

- `llm first_feasible_eval = 68`
- `union first_feasible_eval = 48`
- `raw first_feasible_eval = 73`
- `llm first_feasible_pde_eval = 41`
- `union first_feasible_pde_eval = 20`
- `raw first_feasible_pde_eval = 40`
- `llm front_size = 4`
- `union front_size = 4`
- `raw front_size = 2`
- `llm final_hypervolume = 461.7324877958623`
- `union final_hypervolume = 330.57376222166533`
- `raw final_hypervolume = 516.6124094618752`
- `llm feasible_rate = 0.28`
- `union feasible_rate = 0.14`
- `raw feasible_rate = 0.09`

Source files:

- `/home/hymn/msfenicsx/scenario_runs/s2_staged/0422_2311__llm/tables/summary_statistics.csv`
- `/home/hymn/msfenicsx/scenario_runs/s2_staged/0422_2311__llm/analytics/progress_timeline.csv`
- `/home/hymn/msfenicsx/scenario_runs/compare_reports/s2_staged/0422_2332__raw_union_old_vs_llm_exact_frontload/tables/summary_table.csv`
- `/home/hymn/msfenicsx/scenario_runs/compare_reports/s2_staged/0422_2332__raw_union_old_vs_llm_exact_frontload/tables/pairwise_deltas.csv`

## 11. What Is Fixed Now

The following claims are now supported by fresh evidence:

- hidden positive-match and hidden positive-credit requests are at zero again
- recover / preserve / expand is no longer collapsed into recover-only
- final front diversity recovered from `1` back to `4`
- `llm` still clearly beats `union` on final hypervolume
- exact positive front-loading materially changed the live chain shape

Current latest chain occupancy from the rerun trace:

- `prefeasible_stagnation = 15`
- `prefeasible_convert = 34`
- `post_feasible_expand = 37`
- `post_feasible_preserve = 55`
- `post_feasible_recover = 20`

Trace-backed structural signals:

- `hidden_positive_match_requests = 0`
- `hidden_positive_credit_requests = 0`
- recover effective pool size summary:
  - count `20`
  - min `6`
  - max `6`
  - avg `6.0`

This means the post-feasible chain is now alive enough to support diversity.

## 12. What Is Still Not Fixed

The latest rerun did not solve early feasible entry.

The remaining paper-facing failures are:

- `llm` still loses to `union` on optimizer first feasible:
  - `68` vs `48`
- `llm` still loses to `union` on PDE first feasible:
  - `41` vs `20`
- `llm` still loses to `raw` on final hypervolume:
  - `461.7324877958623` vs `516.6124094618752`

So the honest current summary is:

- `llm` has recovered post-feasible chain quality against `union`
- `llm` has not yet recovered early entry efficiency against `union`
- `llm` has not yet recovered final hypervolume superiority against `raw`

## 13. Current Bottleneck Interpretation

The dominant bottleneck is no longer "recover / preserve / expand collapse."

The current dominant bottleneck is:

- `prefeasible_convert` still consumes too many decisions before first feasible

Evidence:

- first feasible appears only at:
  - `evaluation_index = 68`
  - `pde_evaluation_index = 41`
- convert still occupies `34` decisions before release
- exact-positive matching improved materially, but not fully:
  - exact-positive rows: `34`
  - exact-positive selected: `21`

Misses among exact-positive rows still exist:

- selected non-exact `native_sbx_pm` `7` times
- selected non-target `spread_hottest_cluster` `5` times in rows where it was
  not the exact target set
- selected `repair_sink_budget` once outside the exact set

Phase distribution of misses:

- `prefeasible_convert`: `5`
- `post_feasible_expand`: `8`

Interpretation:

- the exact-positive front-loading fix was necessary and effective
- but convert still lacks a strong enough early-entry contract to close the
  `union` PDE gap
- the next problem is convert precision, not post-feasible phase collapse

## 14. Recommended Next Step

The next repair should stay narrow and continue from the current evidence.

Recommended next target:

- strengthen `prefeasible_convert` selection when:
  - `entry_pressure` is high
  - `exact_positive_match_mode == "prefer_exact_match"`
  - first feasible has not been found yet

Recommended direction:

1. add an audit or controller test that locks a stronger convert-time contract
   around exact-positive choice, not just ordering
2. implement the smallest controller-side shortlist or bounded convert contract
   that reduces fallback selection of `native_sbx_pm`
3. rerun the same focused gate
4. rerun official `s2_staged` `llm`
5. rerender assets and rebuild compare bundle against the same old official
   `raw/union`

The next cycle should avoid broad changes to recover / preserve / expand unless
new rerun evidence shows a fresh regression there. The latest evidence says the
main remaining gap has moved upstream into convert.

## 15. Files Touched In This Repair Line

Do not revert these user-visible working files without checking intent. They
carry the current repair line:

- `/home/hymn/msfenicsx/optimizers/operator_pool/domain_state.py`
- `/home/hymn/msfenicsx/optimizers/operator_pool/state_builder.py`
- `/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py`
- `/home/hymn/msfenicsx/optimizers/operator_pool/reflection.py`
- `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py`
- `/home/hymn/msfenicsx/optimizers/analytics/staged_audit.py`
- `/home/hymn/msfenicsx/tests/optimizers/test_llm_policy_kernel.py`
- `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller.py`
- `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller_state.py`
- `/home/hymn/msfenicsx/tests/optimizers/test_s2_staged_controller_audit.py`

## 16. Minimal Resume Checklist For The Next Conversation

If continuing in a new conversation, the fastest correct resume path is:

1. read this handoff file first
2. treat `/home/hymn/msfenicsx/scenario_runs/s2_staged/0422_2311__llm` as the
   latest verified `llm` evidence
3. treat `/home/hymn/msfenicsx/scenario_runs/compare_reports/s2_staged/0422_2332__raw_union_old_vs_llm_exact_frontload`
   as the latest verified compare bundle
4. keep the honesty boundary from Section 12
5. focus the next repair on `prefeasible_convert` entry efficiency

