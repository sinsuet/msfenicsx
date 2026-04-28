# Primitive Structured Operator Pool Design

> Status: approved design direction; not implemented yet.
>
> This spec defines the shared operator-layer prerequisite for the new S5/S6/S7 aggressive benchmarks. It is intentionally separate from the benchmark templates so the operator pool can be implemented once and reused without three parallel conversations editing the same files.

## 1. Goal

Introduce a new shared primitive operator registry profile, `primitive_structured`, that remains fair and shared across the paper-facing `raw / union / llm` ladder while giving the controller a richer but still primitive action surface.

The design must:

- keep `raw` on the native NSGA-II backbone
- keep `union` and `llm` on the same shared candidate support
- avoid assisted-only or benchmark-specific operators in the paper-facing pool
- make the shared primitive space more expressive than the current `primitive_clean` pool
- give `llm` better semantic choices without hard filtering or hidden legality advantages

This is not a new assisted framework. It is a shared primitive pool redesign.

## 2. Why This Comes First

The new aggressive benchmarks will all depend on the same shared operator contract.

If the operator pool is changed inside each benchmark branch separately, the implementation will drift immediately:

- route-family mapping will diverge
- state-builder semantics will diverge
- prompt guidance will diverge
- benchmark comparisons will no longer share the same operator substrate

This spec therefore owns the operator-layer change exactly once, before S5/S6/S7 are implemented.

## 3. Non-Goals

This spec does **not**:

- add assisted framework operators to the paper-facing `union` pool
- change the native `raw` backbone
- add hard filtering to controller selection
- add benchmark-specific operator exceptions
- introduce hotspot-aware or sink-aware macros into the shared pool
- change legality policy or repair policy

If later experiments need higher-level assisted actions, that should be a separate assisted-framework design.

## 4. Selected Registry Shape

`primitive_structured` should be a strict superset of the current clean primitive pool.

### 4.1 Shared operator catalog v1

The registry should contain these operators:

| operator id | status | role |
| --- | --- | --- |
| `vector_sbx_pm` | existing | native real-coded recombination anchor |
| `component_jitter_1` | existing | local single-component perturbation |
| `anchored_component_jitter` | existing | local perturbation with anchor bias |
| `component_relocate_1` | existing | single-component basin jump |
| `component_swap_2` | existing | pairwise layout exchange |
| `sink_shift` | existing | sink alignment adjustment |
| `sink_resize` | existing | sink budget adjustment |
| `component_block_translate_2_4` | new | coherent block translation over 2-4 nearby components |
| `component_subspace_sbx` | new | structured SBX/PM over a small component subspace |

The first release should only add the two new structured primitives. Existing primitive ids stay intact.

### 4.2 Structured primitive intent

The new operators should fill the gap between a tiny local jitter and a full assisted macro-action.

#### `component_block_translate_2_4`

- selects a small coherent block of 2-4 components
- translates the block as a unit by a bounded offset
- preserves the block’s internal arrangement
- is useful when the incumbent layout has the right local shape but the wrong basin or side of the deck
- should remain representation-aware and legality-safe, not hotspot-aware

#### `component_subspace_sbx`

- performs SBX/PM style variation over a small, structured component subspace rather than the full vector
- can span a compact cluster, a lane, or a related pair/triple of components
- is useful when the controller needs more diversity than `component_jitter_1` but less disruption than a global recombination pass
- should stay primitive and should not inspect thermal fields or hidden controller state

### 4.3 Route-family mapping

The new operators need explicit route families so controller traces can distinguish structured primitive use from stable local/global use.

Proposed families:

- `stable_local`
- `stable_global`
- `structured_block`
- `structured_subspace`

Mapping:

- `vector_sbx_pm` -> `stable_local`
- `component_jitter_1` -> `stable_local`
- `anchored_component_jitter` -> `stable_local`
- `sink_shift` -> `stable_local`
- `sink_resize` -> `stable_local`
- `component_relocate_1` -> `stable_global`
- `component_swap_2` -> `stable_global`
- `component_block_translate_2_4` -> `structured_block`
- `component_subspace_sbx` -> `structured_subspace`

`STABLE_ROUTE_FAMILIES` should remain the stable local/global pair. The new structured families are a third semantic group, not a replacement for the stable families.

## 5. State Semantics

The LLM controller already reasons through soft objective balance, route families, and candidate panels. The new operators need meaningful but non-absolute semantics there.

Recommended state semantics:

| operator id | expected peak effect | expected gradient effect | comment |
| --- | --- | --- | --- |
| `component_block_translate_2_4` | improve | neutral | move a coherent block to a better basin |
| `component_subspace_sbx` | diversify | diversify | recombine a compact layout subspace |

The existing primitives can keep their current semantics, but the controller must stop treating `sink_resize` as a generic preserve-feasible answer. It should remain a budget-adjustment primitive, not a default fallback.

## 6. LLM Guidance Surface

The controller prompt and prompt-projection layer should surface the new operators as legitimate shared primitive options.

Required behavioral shape:

- `llm` sees the same candidate support as `union`
- the new structured operators are described as primitive, not assisted
- the controller can treat them as a third strategy group when frontier pressure or repeated stable-local usage is visible
- no hard filtering is added to force selection order
- `shared_primitive_trial_candidates` may include `component_block_translate_2_4` and `component_subspace_sbx` when they are viable under the current objective balance

The prompt should make one point explicit: structured primitives are not fallback-only novelty actions. They are meant to be compared directly against the existing stable primitive pool.

## 7. Validation Contract

The operator-pool implementation should be considered complete only when the following are true:

1. `primitive_structured` loads as a valid registry profile.
2. The new operator ids are available in the shared pool.
3. `route_families.py` recognizes the new structured families.
4. `state_builder.py` exposes meaningful peak/gradient semantics for the new operators.
5. `llm_controller.py` can surface the new operators in prompt metadata without changing `candidate_operator_ids`.
6. Focused optimizer tests still pass.

Recommended focused tests:

- `tests/optimizers/test_llm_prompt_projection.py`
- `tests/optimizers/test_llm_controller.py`
- `tests/optimizers/test_llm_controller_state.py`
- `tests/optimizers/test_llm_policy_kernel.py`

## 8. Implementation Order

1. Add the new structured operator implementations.
2. Register them in `primitive_structured`.
3. Update route-family mapping and state semantics.
4. Update LLM prompt projection and controller guidance.
5. Run the focused optimizer tests.

The new aggressive benchmarks should not be implemented until this shared pool contract is in place.
