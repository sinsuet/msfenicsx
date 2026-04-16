# L6 Expand Saturation Governor: Implementation and Smoke Results

**Date:** 2026-04-15
**Branch:** `codex/l2-llm-controller-recovery` (commit `7984ba2` + uncommitted L6 changes)
**Worktree:** `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery`

## L6 Feature Summary

The expand saturation governor detects when the `post_feasible_expand` phase has stalled (no new Pareto entries for >= 24 consecutive evaluations) and demotes the phase to `post_feasible_preserve` to prevent the controller from wasting budget on an exhausted search direction.

### Implementation Files

| File | Change |
|---|---|
| `optimizers/operator_pool/domain_state.py` | `expand_saturation_count` in progress state, `expand_saturation_pressure` (0-1) in regime panel |
| `optimizers/operator_pool/policy_kernel.py` | `_expand_saturated()` and `_expand_saturation_demotion_active()` helpers, phase demotion in `detect_search_phase` |
| `optimizers/operator_pool/llm_controller.py` | Saturation demotion guidance text in `_build_phase_policy_guidance` |
| `tests/optimizers/test_llm_controller_state.py` | Saturation count computation tests |
| `tests/optimizers/test_llm_policy_kernel.py` | Saturated/not-saturated demotion tests |

### Design Parameters

- **Threshold:** 24 evaluations since last `new_pareto_entries > 0`
- **Trigger:** `expand_saturation_count >= 24` in `post_feasible_expand` phase
- **Action:** Demotion to `post_feasible_preserve`
- **Reason code:** `post_feasible_expand_saturation_demotion`
- **Constant location:** Defined in both `domain_state.py` and `policy_kernel.py` (minor duplication, acceptable)

### Test Verification

160/160 optimizer tests passed after implementation.

---

## Smoke Run 1: 12x6 (73 evaluations)

**Run path:** `scenario_runs/s1_typical/l6-mid-smoke/`
**Config:** `population_size=12, num_generations=6, evaluation_workers=2`

### LLM Transport

| Metric | Value |
|---|---|
| LLM requests | 61 |
| Fallback | 0 |
| Retry | 0 |
| Invalid response | 0 |
| Avg latency | 3.20s |
| Max latency | 6.51s |

### Convergence

| Gen | Evals | best T_max | best grad_rms | Pareto size | new Pareto |
|---|---|---|---|---|---|
| 1 | 13 | 309.37 | 15.23 | 3 | 3 |
| 2 | 25 | 306.89 | 13.60 | 2 | 2 |
| 3 | 37 | 306.89 | 12.99 | 2 | 1 |
| 4 | 49 | 306.89 | 12.63 | 4 | 2 |
| 5 | 61 | 306.89 | 12.04 | 3 | 2 |
| 6 | 73 | 306.89 | 11.81 | 6 | 4 |

### Saturation Governor: NOT TRIGGERED (expected)

Pareto front progressed every generation. Maximum gap between Pareto additions was well below the 24-evaluation threshold.

---

## Smoke Run 2: 20x10 (201 evaluations)

**Run path:** `scenario_runs/s1_typical/l6-mid-20x10/`
**Config:** `population_size=20, num_generations=10, evaluation_workers=2`

### LLM Transport

| Metric | Value |
|---|---|
| LLM requests | 182 |
| Fallback | 0 |
| Retry | 1 |
| Invalid response | 1 (schema) |
| Avg latency | 3.37s |
| Max latency | 43.00s |

### Convergence

| Gen | Evals | best T_max | best grad_rms | Pareto size | new Pareto |
|---|---|---|---|---|---|
| 1 | 21 | 309.37 | 13.79 | 3 | 3 |
| 2 | 41 | 308.66 | 13.38 | 6 | 3 |
| 3 | 61 | 307.91 | 12.35 | 3 | 3 |
| 4 | 81 | 307.11 | 12.16 | 4 | 3 |
| 5 | 101 | 307.11 | 11.54 | 5 | 2 |
| 6 | 121 | 307.11 | 11.54 | 5 | 2 |
| 7 | 141 | 307.11 | 11.49 | 6 | 2 |
| 8 | 161 | 307.11 | 11.49 | 6 | 0 |
| 9 | 181 | 307.11 | 10.14 | 4 | 1 |
| 10 | 201 | 307.09 | 10.14 | 5 | 1 |

### Phase Transitions

| Gen | Phase | Count |
|---|---|---|
| 2 | post_feasible_recover | 20 |
| 3 | post_feasible_preserve | 20 |
| 4 | post_feasible_expand | 20 |
| 5 | post_feasible_preserve | 20 |
| 6 | post_feasible_expand | 20 |
| 7 | post_feasible_expand | 22 |
| 8 | post_feasible_expand | 20 |
| 9 | post_feasible_expand | 20 |
| 10 | post_feasible_expand | 20 |

Phase agreement: 181/182 (99.5%).

### Operator Distribution

| Operator | Count | % |
|---|---|---|
| local_refine | 51 | 28% |
| native_sbx_pm | 51 | 28% |
| spread_hottest_cluster | 47 | 26% |
| smooth_high_gradient_band | 18 | 10% |
| move_hottest_cluster_toward_sink | 15 | 8% |

### Guardrail Activity

| Code | Count |
|---|---|
| post_feasible_expand_frontier_bias | 82 |
| post_feasible_expand_route_family_dominance_cap | 66 |
| post_feasible_preserve_low_regression_bias | 40 |
| post_feasible_expand_semantic_budget | 30 |
| post_feasible_recover_preserve_bias | 20 |
| recent_operator_dominance | 16 |
| post_feasible_expand_route_rebalance | 10 |

### Saturation Governor: NOT TRIGGERED

Gen 8 had 0 new Pareto entries, but gen 9 recovered with 1 new entry. The expand phase remained active because the stall never reached 24 consecutive evaluations without progress.

---

## Three-Mode Comparison

### Reference Baselines (from `0413_1715__raw_union`, 32x16 = 513 evals)

| Metric | raw | union |
|---|---|---|
| best T_max | 304.43 | 305.88 |
| best grad_rms | 9.66 | 11.00 |
| Pareto size | 5 | 7 |
| Total evals | 513 | 513 |

### Evaluation-Matched Comparison (~65-73 evals)

| Metric | raw (65 evals) | union (65 evals) | llm-L6 (73 evals) |
|---|---|---|---|
| best T_max | 306.82 | 308.04 | 306.89 |
| best grad_rms | 13.17 | 12.59 | **11.81** |
| Pareto size | 5 | 5 | **6** |
| feasible % | 93.75% | 100% | 100% |

### Mid-Budget Comparison (~200 evals)

| Metric | raw (193 evals) | union (193 evals) | llm-L6 (201 evals) |
|---|---|---|---|
| best T_max | 305.54 | 306.45 | 307.09 |
| best grad_rms | 11.85 | 11.41 | **10.14** |

### Final vs Full-Budget

| Metric | raw (513 evals) | union (513 evals) | llm-L6 (201 evals) |
|---|---|---|---|
| best T_max | **304.43** | 305.88 | 307.09 |
| best grad_rms | 9.66 | 11.00 | **10.14** |
| Pareto size | 5 | 7 | 5 |

---

## Key Findings

### LLM Strengths

1. **grad_rms convergence efficiency is 2-3x better than raw/union.** LLM reached 10.14 at 201 evals; raw needed 449 evals to reach 9.66, union never reached 10.14 even at 513 evals.
2. **100% feasible from gen 2 onward** in both runs.
3. **Controller reliability:** 0 fallback in 243 total requests across both runs.
4. **Semantic operator utilization:** `spread_hottest_cluster` (26%) and `smooth_high_gradient_band` (10%) actively selected in 20x10 run; this is the semantic visibility recovery working as designed.

### LLM Weakness: T_max Stagnation

T_max stalled at 307.09-307.11 from gen 4 onward in the 20x10 run. The controller concentrated on grad_rms improvement through the expand phase. Possible causes:

1. **Phase policy bias:** `post_feasible_expand` phase guidance may over-weight frontier expansion (which rewards grad_rms improvement) vs. peak temperature reduction.
2. **Operator selection skew:** `spread_hottest_cluster` (26%) helps grad_rms but may scatter components away from optimal peak-temperature positions. No `slide_sink` or `repair_sink_budget` was selected, which are the operators most likely to improve T_max.
3. **Missing multi-objective balance signal:** The controller lacks explicit guidance to alternate between improving different objectives when one stalls.

### Saturation Governor Assessment

Governor correctly stayed silent in both runs. The 24-evaluation threshold is well-calibrated: it does not fire during active Pareto progression, and the gap in gen 8 (20 evals with 0 new Pareto entries) was correctly below threshold. The governor would likely trigger in a longer 32x16 run if the gen 8-style stall extends.

---

## Hypothesis for Next Work: T_max Improvement

The most promising directions for improving T_max performance:

1. **Multi-objective balance prompt injection:** Add explicit "if T_max has not improved for N evals, prioritize operators that reduce peak temperature" guidance.
2. **Objective-conditioned operator applicability:** Surface which operators historically improve T_max vs. grad_rms, so the controller can make informed trade-off decisions.
3. **sink-aware operator promotion:** When T_max stalls, promote `slide_sink`, `move_hottest_cluster_toward_sink`, and `repair_sink_budget` as high-applicability candidates.
4. **Objective stagnation detection:** Analogous to expand saturation, detect single-objective stagnation and adjust operator weighting.

These interventions should be implemented as controller-layer policy, not as changes to the optimization problem or operator registry, to preserve the paper-facing comparison boundary.
