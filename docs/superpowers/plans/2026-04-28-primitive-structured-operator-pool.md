# Primitive Structured Operator Pool Implementation Plan

> **For agentic workers:** Implement this plan before S5/S6/S7. This plan owns all operator-pool code changes. Benchmark implementation branches should not edit the operator implementation files directly.

**Goal:** Add `primitive_structured` as a shared, fair, richer primitive operator registry profile for aggressive S5/S6/S7 benchmarks.

**Architecture:** Keep `primitive_clean` unchanged for existing S1/S2 work. Add `primitive_structured` as a superset containing all current clean primitives plus `component_block_translate_2_4` and `component_subspace_sbx`. Update route-family semantics, controller-state effects, and LLM prompt metadata so `union` and `llm` share the same candidate support while `llm` gets better semantic guidance.

**Spec:** [docs/superpowers/specs/2026-04-28-primitive-structured-operator-pool-design.md](../specs/2026-04-28-primitive-structured-operator-pool-design.md)

---

## File Map

Modify:

- `optimizers/operator_pool/primitive_registry.py`
- `optimizers/operator_pool/operators.py`
- `optimizers/operator_pool/route_families.py`
- `optimizers/operator_pool/state_builder.py`
- `optimizers/operator_pool/llm_controller.py`

Tests:

- create or extend `tests/optimizers/test_operator_pool_contracts.py`
- extend `tests/optimizers/test_llm_controller.py`
- extend `tests/optimizers/test_llm_controller_state.py`
- run existing prompt/policy tests

Do not modify:

- S5/S6/S7 templates in this plan
- evaluation specs
- optimization specs
- generated run artifacts

---

## Task 1: Add Registry Contract Tests

- [ ] Add a focused test that asserts `approved_operator_pool("primitive_structured")` returns the current `primitive_clean` ids plus:
  - `component_block_translate_2_4`
  - `component_subspace_sbx`
- [ ] Assert `primitive_clean` remains unchanged.
- [ ] Assert duplicate ids are not present in either profile.
- [ ] Assert unknown profiles still raise `KeyError`.

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_operator_pool_contracts.py
```

Expected before implementation: failing test for `primitive_structured`.

---

## Task 2: Add Structured Primitive IDs

- [ ] In `optimizers/operator_pool/primitive_registry.py`, keep `PRIMITIVE_OPERATOR_IDS` unchanged.
- [ ] Add a new tuple:

```python
STRUCTURED_PRIMITIVE_OPERATOR_IDS = (
    *PRIMITIVE_OPERATOR_IDS,
    "component_block_translate_2_4",
    "component_subspace_sbx",
)
```

- [ ] Import this tuple in `operators.py`.
- [ ] Extend `approved_operator_pool()`:

```python
if registry_profile == "primitive_structured":
    return STRUCTURED_PRIMITIVE_OPERATOR_IDS
```

Do not remove `primitive_plus_assisted`.

---

## Task 3: Implement `component_block_translate_2_4`

- [ ] Add a proposal helper in `operators.py` near the existing component operators.
- [ ] Select 2-4 components without using thermal fields or benchmark ids.
- [ ] Prefer a coherent spatial block by selecting a seed component and its nearest component neighbors from the current vector.
- [ ] Apply one bounded `(dx, dy)` translation to every selected component.
- [ ] Clip through the existing `VariableLayout` bounds.
- [ ] Keep the operation objective-agnostic and state-agnostic except for generic bounds/layout metadata.

Suggested behavior:

- block size: `min(component_count, rng.integers(2, 5))`
- translation magnitude: about `0.035-0.085` in normalized board units
- direction: random angle
- no hotspot targeting
- no sink coupling

---

## Task 4: Implement `component_subspace_sbx`

- [ ] Add a proposal helper in `operators.py` near `_native_sbx_pm`.
- [ ] Use both parents when available, matching the existing `ParentBundle` assumptions.
- [ ] Select a compact component subspace of 2-5 components.
- [ ] Apply SBX/PM only to the selected components' x/y slots.
- [ ] Copy all other variables from the primary parent.
- [ ] Clip through `VariableLayout`.

Suggested behavior:

- reuse `_resolve_native_parameters(state)` for eta/prob settings
- select seed + nearest neighbors from primary parent coordinates
- apply SBX/PM to selected x/y indices only
- leave sink variables unchanged

If the implementation shares code with `_sbx_pm_numeric`, keep the helper small and avoid broad refactors.

---

## Task 5: Register Operator Definitions And Behavior Profiles

- [ ] Add both operators to `_REGISTERED_OPERATORS` in `operators.py`.
- [ ] Add `OperatorBehaviorProfile` rows if this file has explicit behavior profiles for operator ids.
- [ ] Family/role suggestions:
  - `component_block_translate_2_4`: family `structured_block`, role `primitive_structured_block`, exploration class `structured`
  - `component_subspace_sbx`: family `structured_subspace`, role `primitive_structured_subspace`, exploration class `structured`

Do not mark them as assisted or objective-aware.

---

## Task 6: Update Route-Family Semantics

- [ ] In `route_families.py`, add:

```python
"component_block_translate_2_4": "structured_block",
"component_subspace_sbx": "structured_subspace",
```

- [ ] Keep `STABLE_ROUTE_FAMILIES = {"stable_local", "stable_global"}` unchanged.
- [ ] Add tests that `operator_route_family()` returns the new families.
- [ ] Ensure route-family entropy and family metrics handle the new families without special cases.

---

## Task 7: Update Controller-State Effects

- [ ] In `state_builder.py`, add `_OPERATOR_EFFECTS` entries:

```python
"component_block_translate_2_4": {
    "expected_peak_effect": "improve",
    "expected_gradient_effect": "neutral",
},
"component_subspace_sbx": {
    "expected_peak_effect": "diversify",
    "expected_gradient_effect": "diversify",
},
```

- [ ] Add/extend tests that the prompt operator panel exposes those effects.
- [ ] Verify objective-balance logic can list the new operators in peak/diversify-relevant candidates.

---

## Task 8: Update LLM Prompt Semantics

- [ ] In `llm_controller.py`, add role summaries for both operators.
- [ ] Add strategy groups:
  - `component_block_translate_2_4` -> `structured_block`
  - `component_subspace_sbx` -> `structured_subspace`
- [ ] Add operator intents:
  - `component_block_translate_2_4` -> `structured_block_reposition`
  - `component_subspace_sbx` -> `structured_subspace_recombine`
- [ ] Add intent summaries that describe them as shared primitive operators, not assisted operators.
- [ ] Include the new ids in stable/primitive prompt sets only if required by existing helper names; do not classify them as assisted semantic trials.
- [ ] Extend shared primitive trial candidate logic so:
  - peak pressure can include `component_block_translate_2_4`
  - frontier/diversify pressure can include `component_subspace_sbx`
  - candidate exposure remains advisory only

---

## Task 9: Focused Test Pass

Run exactly these focused tests first:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_operator_pool_contracts.py
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_llm_prompt_projection.py
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_llm_controller.py
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_llm_controller_state.py
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_llm_policy_kernel.py
```

Do not run the full repository suite unless these focused tests reveal broader contract uncertainty.

---

## Task 10: Handoff Criteria For S5/S6/S7

This plan is complete when:

- `primitive_clean` still returns exactly the old primitive set
- `primitive_structured` returns the old set plus two structured primitives
- both new operators can generate clipped numeric proposals
- route families and state effects are visible
- LLM prompt metadata can surface the new operators without changing candidate support
- focused optimizer tests pass

After this, S5/S6/S7 workers may reference `registry_profile: primitive_structured` without editing operator code.
