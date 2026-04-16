# S1 Typical LLM Controller Adaptation Design

## Context

`msfenicsx` now has an active single-case paper-facing ladder:

- `nsga2_raw`
- `nsga2_union`
- `nsga2_llm`

For `s1_typical`, the intended comparison contract is already fixed:

- all three routes optimize the same 32D decision encoding
- the same repair, cheap constraints, PDE solve, evaluation spec, and survival semantics stay matched
- `raw` uses native `NSGA-II` offspring proposal
- `union` and `llm` use the same fixed mixed operator registry
- `union` and `llm` differ only by controller

The current repository implementation already reflects most of this contract:

- `scenarios/optimization/s1_typical_llm.yaml` uses the same operator pool as `union`
- `optimizers/operator_pool/` is already rebuilt around `s1_typical` semantic operators
- `build_controller_state()` and the `LLMOperatorController` already consume compact domain-grounded state rather than legacy four-component benchmark semantics

However, the current `llm` route is still not ideal for the new paper-facing story. The main gap is not that it is still bound to the wrong scenario. The main gap is that its controller-state and prompt still behave too much like a generic compact JSON export, instead of a phase-aware decision surface that explicitly prioritizes:

1. first-feasible entry and stable feasible retention
2. then feasible preservation
3. then frontier growth and Pareto-quality improvement

## Problem Statement

We want to run the first real `nsga2_llm` validation on the rebuilt `s1_typical` mainline, but we want that run to support the intended paper narrative.

That means the new `llm` adaptation must satisfy two conditions at the same time:

1. It must preserve the paper-facing fairness contract:
   - no change to the optimization problem
   - no change to the fixed union operator registry
   - no change to evaluation budget, population size, generation count, repair, solve, or survival
   - no route-specific algorithm-profile tuning that would make `union` versus `llm` more than a controller comparison
2. It must make the `LLM` controller meaningfully more phase-aware and decision-oriented than the current version, so that a real run has a better chance to improve both:
   - feasible-entry / feasible-retention behavior
   - Pareto-quality signals

## Design Goals

- Keep `union` versus `llm` as a controller-only comparison on the same fixed action space.
- Rebuild the `llm` prompt surface so the model sees the current search phase and the current local decision pressure clearly.
- Make `memory.recent_window`, `reasoning.effort`, and `retry.timeout_seconds` real live execution inputs rather than mostly decorative spec fields.
- Preserve the existing semantic operator registry and trace semantics.
- Produce a real `llm` smoke run whose artifacts can be analyzed with the same run-layout and trace tooling already used for `raw` and `union`.

## Non-Goals

- Do not create a separate `s1_typical_llm` algorithm profile.
- Do not alter `population_size`, `num_generations`, native variation parameters, or evaluation budget for the `llm` route.
- Do not change the fixed operator pool or add `llm`-only operators.
- Do not change repair, cheap constraints, solver defaults, or evaluation metrics.
- Do not introduce benchmark-specific hardcoded component-name policies.

## Core Design

### 1. Preserve the Matched Experiment Contract

`scenarios/optimization/s1_typical_llm.yaml` will continue to reuse the same optimization-layer profile used by `union`.

That is intentional. The paper-facing claim must remain:

> `union` and `llm` share the same mixed operator registry, the same budget, and the same optimization problem. Only the controller changes.

Any route-specific algorithm tuning at the spec/profile layer would weaken this claim and blur the line between controller improvement and optimizer-parameter retuning.

### 2. Upgrade `llm` from Generic Compact State to Phase-Aware Decision Panels

The controller will still consume compact domain-grounded state, but that state will be reorganized into a clearer phase-aware decision surface.

The prompt-facing state should emphasize four panels:

- `run_panel`
  - evaluations used / remaining
  - first feasible evaluation
  - current best peak temperature
  - current best gradient RMS
  - current Pareto size
- `regime_panel`
  - current controller phase
  - dominant violation family
  - dominant-violation persistence
  - sink-budget utilization
  - whether the run is in a near-feasible conversion window
- `parent_panel`
  - the most decision-relevant parent summaries rather than broad raw parent dumps
  - especially the closest-to-feasible parent and the strongest feasible parent when available
- `operator_panel`
  - phase-specific evidence for each candidate operator, centered on:
    - `entry_fit`
    - `preserve_fit`
    - `expand_fit`
    - `recent_regression_risk`
    - `frontier_evidence`
    - `dominant_violation_relief`

This does not change what the controller is allowed to do. It changes how clearly the current search state is presented.

### 3. Make Prompt Policy Explicitly Phase-Ordered

The new system and user prompts will explicitly encode the paper-facing controller priorities:

- `prefeasible_convert`
  - first objective is to cross into the feasible region and avoid throwing away stable near-feasible progress
- `post_feasible_preserve`
  - first objective is to retain and stabilize feasibility while avoiding needless regression
- `post_feasible_expand`
  - only after feasible stability exists should the controller prefer frontier expansion and Pareto novelty

This should move the `LLM` away from generic “pick a plausible semantic operator” behavior and toward a more disciplined search-phase controller.

### 4. Wire Spec-Level LLM Runtime Parameters into Actual Execution

The current `llm` spec already declares:

- `memory.recent_window`
- `reasoning.effort`
- `retry.timeout_seconds`

The execution path should actually consume them.

In particular:

- `memory.recent_window` should flow into controller-state construction instead of using a fixed adapter-side constant
- `reasoning.effort` should continue to flow through the OpenAI-compatible client request payload
- `retry.timeout_seconds` should continue to control the live client timeout

This keeps the runtime configurable while staying inside the controller-only comparison boundary.

## Concrete Code Changes

### `scenarios/optimization/s1_typical_llm.yaml`

- keep the same design variables, algorithm profile, operator pool, and budget as `union`
- keep `controller=llm`
- keep `model=GPT-5.4`
- treat controller parameters as authoritative live settings rather than passive documentation

### `optimizers/adapters/genetic_family.py`

- replace the fixed `recent_window=32` controller-state input with the value resolved from `controller_parameters.memory.recent_window`
- keep default fallback behavior when the field is omitted

### `optimizers/operator_pool/state_builder.py`

- keep current `run_state`, `parent_state`, `archive_state`, `domain_regime`, and `progress_state`
- add or refine compact phase-aware prompt panels derived from those structures
- avoid dumping large low-signal history blocks directly into prompt metadata

### `optimizers/operator_pool/domain_state.py`

- strengthen the phase summaries that distinguish:
  - entry pressure
  - preservation pressure
  - frontier stagnation / expansion pressure
- preserve the existing controller-agnostic interpretation of history

### `optimizers/operator_pool/reflection.py`

- derive clearer phase-facing operator evidence summaries
- keep evidence portable and operator-level rather than benchmark-name-specific

### `optimizers/operator_pool/prompt_projection.py`

- replace generic metadata projection with a phase-aware projection that centers the current decision pressure
- keep post-feasible-only fields suppressed outside post-feasible phases

### `optimizers/operator_pool/llm_controller.py`

- rewrite phase guidance to enforce the desired policy order more strongly
- use the new compact panels in prompt generation
- preserve recent-dominance guardrails and fallback semantics

## Validation Plan

### Automated Verification

Update and run focused tests for:

- `tests/optimizers/test_llm_controller_state.py`
- `tests/optimizers/test_llm_controller.py`
- `tests/optimizers/test_llm_policy_kernel.py`
- relevant `tests/optimizers/test_optimizer_cli.py` coverage for diagnostics and spec validation

The tests should prove:

- `llm` still matches `union` on fixed operator-pool membership
- controller-state uses the configured recent-memory window
- prompt projection is phase-aware
- the controller prompt explicitly distinguishes entry, preserve, and expand priorities
- no route-specific algorithm-profile drift is introduced

### Live Smoke Run

After implementation, run one real `s1_typical` `llm` smoke using the official paper-facing spec:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/s1_typical_llm.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s1_typical/llm-smoke
```

### Paper-Facing Success Criteria

The run is only paper-positive if it shows both:

- at least one positive feasibility signal versus the current matched `union` baseline
  - earlier `first_feasible_eval`, or
  - higher feasible rate
- at least one positive Pareto-quality signal versus the current matched `union` baseline
  - larger Pareto set, or
  - more unique non-dominated objective pairs, or
  - a new non-dominated improvement relative to the union front

If the run is live-runnable but not paper-positive, it still remains useful controller evidence, but it should be reported as a partial outcome rather than as a successful paper-facing upgrade.

## Rationale

This design keeps the paper-facing experiment class clean:

- `raw` versus `union` remains a proposal-space comparison
- `union` versus `llm` remains a controller-only comparison on the same fixed registry

At the same time, it gives the `llm` route a stronger chance to behave like the controller we actually want to describe in the paper:

- not a free-form design generator
- not a hidden optimizer retuning
- but a phase-aware operator-selection policy on a fixed action space
