# Objective Balance Signal Design

**Date:** 2026-04-15
**Status:** Approved
**Scope:** Controller-layer only (prompt soft signal), no optimizer/problem changes

## Problem

The nsga2_llm controller achieves excellent grad_rms convergence (2-3x faster than raw/union) but T_max stagnates at ~307K while raw reaches ~304K. Root cause: the controller's operator selection is biased toward grad_rms-improving operators (spread_hottest_cluster 26%) while T_max-relevant operators (slide_sink, move_hottest_cluster_toward_sink) receive zero selections. The controller has no mechanism to detect single-objective stagnation and rebalance.

## Target

Reduce T_max from 307.09K to 305-306K within a 20x10 (201 eval) smoke run while preserving the grad_rms advantage.

## Design

Four coordinated changes, all prompt-layer soft signals only.

### 1. Per-objective stagnation detection (domain_state.py)

Add to `build_progress_state` return value:

```python
"objective_stagnation": {
    "temperature_max": {
        "best_value": 307.09,
        "evaluations_since_improvement": 15,
        "stagnant": True,
    },
    "gradient_rms": {
        "best_value": 10.14,
        "evaluations_since_improvement": 2,
        "stagnant": False,
    },
}
```

**Logic:** Iterate feasible records in `ordered_history`, track per-objective best value and last improvement eval. Stagnation threshold: `_OBJECTIVE_STAGNATION_THRESHOLD = 6` consecutive feasible evaluations without improvement.

**Objective keys:** Hard-coded `summary.temperature_max` and `summary.temperature_gradient_rms` (matching s1_typical objective spec). Use existing `_metric_from_record` for extraction.

**Propagation:** `build_progress_state` → `state_metadata["progress_state"]` → consumed by `build_prompt_regime_panel`.

### 2. Objective balance sub-panel in regime_panel (domain_state.py)

Add to `build_prompt_regime_panel` return value:

```python
"objective_balance": {
    "stagnant_objectives": ["temperature_max"],
    "improving_objectives": ["gradient_rms"],
    "balance_pressure": "high",
    "preferred_effect": "peak_improve",
}
```

**balance_pressure rules:**
- `high`: one objective stagnant, the other still improving (clear imbalance)
- `medium`: both objectives stagnant (global stagnation)
- `low`: no stagnant objectives

**preferred_effect mapping:**
- `temperature_max` stagnant, `gradient_rms` not → `"peak_improve"`
- `gradient_rms` stagnant, `temperature_max` not → `"gradient_improve"`
- both stagnant → `"balanced"`
- none stagnant → `None`

### 3. decision_axes + system_prompt guidance (llm_controller.py)

**`_build_decision_axes` additions:**

```python
"objective_balance_pressure": "high",
"preferred_effect": "peak_improve",
"peak_improve_candidates": ["slide_sink", "move_hottest_cluster_toward_sink", "local_refine"],
```

`peak_improve_candidates`: filter `operator_panel` for `expected_peak_effect == "improve"`, sorted by applicability descending. Symmetrically `gradient_improve_candidates` when `preferred_effect == "gradient_improve"`.

**`_build_system_prompt` guidance injection** (after phase_policy_guidance, before route_family_guidance):

When `objective_balance_pressure` is `high` or `medium`:
- `preferred_effect == "peak_improve"`:
  > "Objective balance alert: temperature_max has stagnated while gradient_rms continues improving. Prefer operators with expected_peak_effect=improve (especially {candidates}) over operators that only improve gradient. A bounded T_max-focused trial is justified even if it slightly risks gradient_rms."
- `preferred_effect == "gradient_improve"`:
  > Symmetric text prioritizing gradient direction.
- `preferred_effect == "balanced"`:
  > "Both objectives have stagnated. Diversify operator selection to break out of the current basin."

### 4. Applicability boost (state_builder.py)

In `_build_operator_applicability_row`, when `objective_balance.preferred_effect == "peak_improve"`:

| operator | boost condition | boost |
|---|---|---|
| slide_sink | unconditional | +1 |
| move_hottest_cluster_toward_sink | unconditional | +1 |
| local_refine | unconditional | +1 |
| spread_hottest_cluster | only when compact_cluster | +1 |

Symmetrically for `gradient_improve`: boost smooth_high_gradient_band, spread_hottest_cluster, reduce_local_congestion.

**Effect:** Operators like slide_sink go from applicability `low` → `medium` or `medium` → `high`, enabling entry into `semantic_trial_candidates` (requires `applicability == "high"`).

**Call chain change:** `_build_prompt_operator_panel` passes `objective_balance` (from `regime_panel.get("objective_balance")`) to `_build_operator_applicability_row`.

## Files Changed

| File | Change |
|---|---|
| `optimizers/operator_pool/domain_state.py` | `build_progress_state`: add `objective_stagnation`; `build_prompt_regime_panel`: add `objective_balance` |
| `optimizers/operator_pool/llm_controller.py` | `_build_decision_axes`: consume `objective_balance`; `_build_system_prompt`: add guidance text |
| `optimizers/operator_pool/state_builder.py` | `_build_operator_applicability_row`: add `objective_balance` param + applicability boost; `_build_prompt_operator_panel`: pass through |
| `tests/optimizers/test_llm_controller_state.py` | Tests for objective_stagnation detection |
| `tests/optimizers/test_llm_policy_kernel.py` | Tests for applicability boost and decision_axes signal |

## Architectural Constraints

- No changes to policy_kernel.py hard filters
- No changes to optimizer, problem, design variables, operator registry, or evaluation spec
- All signals are prompt-layer soft hints; LLM retains autonomy
- Constants are module-level, not benchmark-specific

## Verification

1. All tests pass: `conda run -n msfenicsx pytest tests/optimizers/ -v`
2. Full suite: `conda run -n msfenicsx pytest -v`
3. Smoke run: 20x10 with `s1_typical_llm.yaml`, verify T_max < 306K
