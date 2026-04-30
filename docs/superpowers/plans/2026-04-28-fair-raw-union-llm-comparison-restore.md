# Fair raw / union / llm Comparison Restore Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the paper-facing `raw / union / llm` comparison so `union` and `llm` share the same search substrate while `llm` keeps only representation-layer advantages.

**Architecture:** Phase 1 restores the B-shape contract from `docs/superpowers/specs/2026-04-27-fair-raw-union-llm-comparison-restore-design.md`: scenario specs declare identical `union` / `llm` substrate fields; `policy_kernel` becomes annotation-only; `llm_controller` always sends the full shared candidate pool and renders guardrails as soft advice. Phase 2 shared-pool rebalance is intentionally out of scope for this implementation plan and should get its own design after Phase 1 traces exist.

**Tech Stack:** Python 3, pytest, YAML scenario specs, existing optimizer operator-pool modules, existing Markdown documentation.

---

## File Structure

**Modify:**
- `scenarios/optimization/s1_typical_llm.yaml` — align `llm` substrate fields with `s1_typical_union.yaml` while keeping `controller: llm` and `controller_parameters`.
- `scenarios/optimization/s2_staged_llm.yaml` — align `llm` substrate fields with `s2_staged_union.yaml` while keeping `controller: llm` and `controller_parameters`.
- `optimizers/operator_pool/policy_kernel.py` — preserve evidence annotations but stop narrowing `allowed_operator_ids` or populating `suppressed_operator_ids`.
- `optimizers/operator_pool/llm_controller.py` — keep the full candidate pool after policy and guardrail analysis; convert guardrail wording from removal to soft advice; remove exact-positive candidate contraction from the paper-facing candidate support path.
- `README.md` — describe `union` / `llm` as sharing the same primitive pool and legality policy; remove paper-facing assisted-framework wording.
- `AGENTS.md` — align Codex guidance with the B-shape contract.
- `CLAUDE.md` — refine existing matched-registry wording into the representation-layer contract.

**Create or modify tests:**
- `tests/optimizers/test_operator_pool_contracts.py` — add scenario spec substrate-contract tests for `s1_typical` and `s2_staged`.
- `tests/optimizers/test_llm_policy_kernel.py` — update hard-filter expectations to annotation-only expectations.
- `tests/optimizers/test_llm_controller.py` — verify full candidate pool is preserved and guardrail text is soft advice.

**Do not modify in this plan:**
- `optimizers/operator_pool/primitive_registry.py` — Phase 1 keeps the current clean primitive pool.
- `optimizers/operator_pool/assisted_registry.py` — assisted operators remain available for non-paper-facing experiments, but are not used by `s1_typical_llm` or `s2_staged_llm`.
- `optimizers/algorithm_config.py` — no backbone default changes.
- `core/`, `evaluation/`, `visualization/` — no solver/evaluation/rendering changes.

**Commit policy:** The steps below include git checkpoint commands only as optional user-approved checkpoints. Do not create commits unless the user explicitly asks for commits during execution.

---

### Task 1: Lock scenario spec substrate equality

**Files:**
- Modify: `scenarios/optimization/s1_typical_llm.yaml:145-182`
- Modify: `scenarios/optimization/s2_staged_llm.yaml:145-182`
- Test: `tests/optimizers/test_operator_pool_contracts.py`

- [ ] **Step 1: Write the failing scenario substrate contract tests**

Append these tests to `tests/optimizers/test_operator_pool_contracts.py`:

```python
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_yaml(path: str) -> dict:
    with (REPO_ROOT / path).open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def _substrate_fields(spec: dict) -> dict:
    operator_control = spec["operator_control"]
    evaluation_protocol = spec["evaluation_protocol"]
    algorithm = spec["algorithm"]
    return {
        "decision_variables": spec["decision_variables"],
        "registry_profile": operator_control["registry_profile"],
        "operator_pool": operator_control["operator_pool"],
        "legality_policy_id": evaluation_protocol["legality_policy_id"],
        "evaluation_spec_path": evaluation_protocol["evaluation_spec_path"],
        "family": algorithm["family"],
        "backbone": algorithm["backbone"],
        "population_size": algorithm["population_size"],
        "num_generations": algorithm["num_generations"],
        "seed": algorithm["seed"],
    }


def test_s1_typical_union_and_llm_share_search_substrate() -> None:
    union_spec = _load_yaml("scenarios/optimization/s1_typical_union.yaml")
    llm_spec = _load_yaml("scenarios/optimization/s1_typical_llm.yaml")

    assert union_spec["operator_control"]["controller"] == "random_uniform"
    assert llm_spec["operator_control"]["controller"] == "llm"
    assert _substrate_fields(llm_spec) == _substrate_fields(union_spec)


def test_s2_staged_union_and_llm_share_search_substrate() -> None:
    union_spec = _load_yaml("scenarios/optimization/s2_staged_union.yaml")
    llm_spec = _load_yaml("scenarios/optimization/s2_staged_llm.yaml")

    assert union_spec["operator_control"]["controller"] == "random_uniform"
    assert llm_spec["operator_control"]["controller"] == "llm"
    assert _substrate_fields(llm_spec) == _substrate_fields(union_spec)
```

If `tests/optimizers/test_operator_pool_contracts.py` already imports `Path` or `yaml`, reuse existing imports instead of duplicating them.

- [ ] **Step 2: Run the new tests and verify they fail for the current split**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_operator_pool_contracts.py::test_s1_typical_union_and_llm_share_search_substrate tests/optimizers/test_operator_pool_contracts.py::test_s2_staged_union_and_llm_share_search_substrate
```

Expected: FAIL because current `llm` specs use `registry_profile: primitive_plus_assisted`, include assisted operators, and use `legality_policy_id: projection_plus_local_restore`.

- [ ] **Step 3: Align `s1_typical_llm.yaml` with the clean shared substrate**

Replace the `operator_control` and `evaluation_protocol` block in `scenarios/optimization/s1_typical_llm.yaml` with:

```yaml
operator_control:
  controller: llm
  registry_profile: primitive_clean
  operator_pool:
    - vector_sbx_pm
    - component_jitter_1
    - anchored_component_jitter
    - component_relocate_1
    - component_swap_2
    - sink_shift
    - sink_resize
  controller_parameters:
    provider: openai-compatible
    capability_profile: chat_compatible_json
    performance_profile: balanced
    model_env_var: LLM_MODEL
    api_key_env_var: LLM_API_KEY
    base_url_env_var: LLM_BASE_URL
    max_output_tokens: 256
    temperature: 1.0
    reasoning:
      effort: medium
    retry:
      max_attempts: 2
      timeout_seconds: 45
    memory:
      recent_window: 32
      reflection_interval: 1
    fallback_controller: random_uniform
evaluation_protocol:
  evaluation_spec_path: scenarios/evaluation/s1_typical_eval.yaml
  legality_policy_id: minimal_canonicalization
```

- [ ] **Step 4: Align `s2_staged_llm.yaml` with the clean shared substrate**

Replace the corresponding block in `scenarios/optimization/s2_staged_llm.yaml` with the same clean pool and `minimal_canonicalization`, preserving its existing `evaluation_spec_path`:

```yaml
operator_control:
  controller: llm
  registry_profile: primitive_clean
  operator_pool:
    - vector_sbx_pm
    - component_jitter_1
    - anchored_component_jitter
    - component_relocate_1
    - component_swap_2
    - sink_shift
    - sink_resize
  controller_parameters:
    provider: openai-compatible
    capability_profile: chat_compatible_json
    performance_profile: balanced
    model_env_var: LLM_MODEL
    api_key_env_var: LLM_API_KEY
    base_url_env_var: LLM_BASE_URL
    max_output_tokens: 256
    temperature: 1.0
    reasoning:
      effort: medium
    retry:
      max_attempts: 2
      timeout_seconds: 45
    memory:
      recent_window: 32
      reflection_interval: 1
    fallback_controller: random_uniform
evaluation_protocol:
  evaluation_spec_path: scenarios/evaluation/s2_staged_eval.yaml
  legality_policy_id: minimal_canonicalization
```

- [ ] **Step 5: Run the scenario substrate contract tests and verify they pass**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_operator_pool_contracts.py::test_s1_typical_union_and_llm_share_search_substrate tests/optimizers/test_operator_pool_contracts.py::test_s2_staged_union_and_llm_share_search_substrate
```

Expected: PASS.

- [ ] **Step 6: Optional user-approved checkpoint**

Do not commit unless the user explicitly asks for commits. If commits are authorized, run:

```bash
git status --short
git add tests/optimizers/test_operator_pool_contracts.py scenarios/optimization/s1_typical_llm.yaml scenarios/optimization/s2_staged_llm.yaml
git commit -m "$(cat <<'EOF'
Restore shared LLM scenario substrate.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Make `policy_kernel` annotation-only

**Files:**
- Modify: `optimizers/operator_pool/policy_kernel.py:451-727`
- Test: `tests/optimizers/test_llm_policy_kernel.py`

- [ ] **Step 1: Write or update policy support-preservation tests**

Add this helper near the top of `tests/optimizers/test_llm_policy_kernel.py` after `_policy_kernel_module()`:

```python
def _assert_snapshot_preserves_support(snapshot, candidate_operator_ids: tuple[str, ...]) -> None:
    assert snapshot.allowed_operator_ids == candidate_operator_ids
    assert snapshot.suppressed_operator_ids == ()
    assert set(snapshot.candidate_annotations) == set(candidate_operator_ids)
```

Add these tests after the existing state-builder helpers:

```python
def test_policy_snapshot_preserves_cold_start_candidate_support() -> None:
    policy_kernel = _policy_kernel_module()
    candidates = (
        "vector_sbx_pm",
        "component_jitter_1",
        "component_relocate_1",
        "sink_shift",
        "sink_resize",
    )

    snapshot = policy_kernel.build_policy_snapshot(_cold_start_state(), candidates)

    _assert_snapshot_preserves_support(snapshot, candidates)
    assert "cold_start_stable_bootstrap" in snapshot.reason_codes


def test_policy_snapshot_preserves_prefeasible_candidate_support() -> None:
    policy_kernel = _policy_kernel_module()
    candidates = (
        "native_sbx_pm",
        "global_explore",
        "local_refine",
        "move_hottest_cluster_toward_sink",
        "spread_hottest_cluster",
    )

    snapshot = policy_kernel.build_policy_snapshot(_prefeasible_family_collapse_state(), candidates)

    _assert_snapshot_preserves_support(snapshot, candidates)
    assert "prefeasible_speculative_family_collapse" in snapshot.reason_codes


def test_policy_snapshot_preserves_post_feasible_candidate_support() -> None:
    policy_kernel = _policy_kernel_module()
    candidates = (
        "native_sbx_pm",
        "local_refine",
        "hotspot_pull_toward_sink",
        "hotspot_spread",
        "sink_retarget",
    )

    snapshot = policy_kernel.build_policy_snapshot(_post_feasible_expand_state(), candidates)

    _assert_snapshot_preserves_support(snapshot, candidates)
    assert snapshot.phase.startswith("post_feasible")
```

If `_post_feasible_expand_state()` does not exist in the current file, create it with this complete fixture:

```python
def _post_feasible_expand_state() -> ControllerState:
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=8,
        evaluation_index=140,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "run_state": {
                "decision_index": 55,
                "evaluations_used": 139,
                "evaluations_remaining": 60,
                "feasible_rate": 0.85,
                "first_feasible_eval": 24,
            },
            "progress_state": {
                "phase": "post_feasible_stagnation",
                "post_feasible_mode": "expand",
                "recent_no_progress_count": 5,
                "recent_frontier_stagnation_count": 7,
            },
            "recent_decisions": [
                {
                    "evaluation_index": 130 + index,
                    "selected_operator_id": "hotspot_spread" if index < 5 else "sink_retarget",
                    "fallback_used": False,
                    "llm_valid": True,
                    "generation_local": True,
                }
                for index in range(8)
            ],
            "operator_summary": {
                "native_sbx_pm": {"selection_count": 8, "recent_selection_count": 0, "proposal_count": 8},
                "local_refine": {"selection_count": 8, "recent_selection_count": 0, "proposal_count": 8},
                "hotspot_pull_toward_sink": {"selection_count": 4, "recent_selection_count": 1, "proposal_count": 4},
                "hotspot_spread": {"selection_count": 12, "recent_selection_count": 5, "proposal_count": 12},
                "sink_retarget": {"selection_count": 7, "recent_selection_count": 3, "proposal_count": 7},
            },
        },
    )
```

- [ ] **Step 2: Run the policy tests and verify they fail on hard filtering**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_llm_policy_kernel.py::test_policy_snapshot_preserves_cold_start_candidate_support tests/optimizers/test_llm_policy_kernel.py::test_policy_snapshot_preserves_prefeasible_candidate_support tests/optimizers/test_llm_policy_kernel.py::test_policy_snapshot_preserves_post_feasible_candidate_support
```

Expected: At least one FAIL because current `build_policy_snapshot()` can shrink `allowed_operator_ids` and populate `suppressed_operator_ids`.

- [ ] **Step 3: Replace support mutation with annotation-only return**

In `optimizers/operator_pool/policy_kernel.py`, edit `build_policy_snapshot()` so all existing branch logic may append `reason_codes` and enrich `candidate_annotations`, but the returned support is always the original candidate tuple.

Use this final return block:

```python
    return PolicySnapshot(
        phase=phase,
        allowed_operator_ids=candidate_ids,
        suppressed_operator_ids=(),
        reset_active=reset_active,
        reason_codes=tuple(dict.fromkeys(reason_codes)),
        candidate_annotations=candidate_annotations,
    )
```

Then remove or neutralize assignments that shrink `allowed_operator_ids` and append to `suppressed_operator_ids`. The minimal safe implementation is:

```python
    allowed_operator_ids = list(candidate_ids)
    reason_codes: list[str] = []
    reset_active = False
```

and whenever an existing helper returns a filtered candidate tuple, keep only the reason-code side effect. For example, rewrite this current hard-filter block:

```python
            if filtered and filtered != tuple(allowed_operator_ids):
                allowed_operator_ids = list(filtered)
                suppressed_operator_ids.extend(
                    operator_id
                    for operator_id in candidate_ids
                    if operator_id not in allowed_operator_ids and operator_id not in suppressed_operator_ids
                )
                reason_codes.append("prefeasible_convert_entry_bias")
```

as:

```python
            if filtered and filtered != tuple(allowed_operator_ids):
                reason_codes.append("prefeasible_convert_entry_bias")
```

Apply the same pattern to every block that currently mutates `allowed_operator_ids` or `suppressed_operator_ids`.

- [ ] **Step 4: Preserve annotation semantics where helpers already annotate throttle/cooldown states**

Do not remove these annotation calls near the top of `build_policy_snapshot()`:

```python
        candidate_annotations = _annotate_post_feasible_route_budget(
            state,
            candidate_ids,
            candidate_annotations,
        )
        candidate_annotations = _annotate_post_feasible_expand_budget(
            candidate_ids,
            candidate_annotations,
        )
        candidate_annotations = _annotate_post_feasible_generation_probe_budget(
            state,
            candidate_ids,
            candidate_annotations,
        )
        candidate_annotations = _annotate_post_feasible_gradient_polish(
            state,
            phase,
            candidate_ids,
            candidate_annotations,
        )
        candidate_annotations = _annotate_post_feasible_stable_success(
            candidate_ids,
            candidate_annotations,
        )
        candidate_annotations = _annotate_post_feasible_preserve_plateau(
            state,
            phase,
            candidate_ids,
            candidate_annotations,
        )
```

These are the soft-advice substrate. They should continue to populate `route_budget_state`, `expand_budget_state`, `generation_probe_state`, `stable_success_state`, and related warning data.

- [ ] **Step 5: Run the focused policy tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_llm_policy_kernel.py
```

Expected: PASS. If older tests explicitly expect `suppressed_operator_ids` to be non-empty, update those assertions to check `reason_codes` and per-operator annotation fields instead.

- [ ] **Step 6: Optional user-approved checkpoint**

Do not commit unless explicitly authorized. If commits are authorized, run:

```bash
git status --short
git add optimizers/operator_pool/policy_kernel.py tests/optimizers/test_llm_policy_kernel.py
git commit -m "$(cat <<'EOF'
Make policy kernel preserve candidate support.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Convert LLM guardrails and exact-positive paths to soft advice

**Files:**
- Modify: `optimizers/operator_pool/llm_controller.py:215-304`
- Modify: `optimizers/operator_pool/llm_controller.py:727-797`
- Modify: `optimizers/operator_pool/llm_controller.py:1307-1399`
- Modify: `optimizers/operator_pool/llm_controller.py:1459-1762`
- Modify: `optimizers/operator_pool/llm_controller.py:2198-2267`
- Test: `tests/optimizers/test_llm_controller.py`

- [ ] **Step 1: Write tests for full candidate preservation**

Append these tests to `tests/optimizers/test_llm_controller.py`:

```python
def test_llm_controller_preserves_full_candidate_pool_with_recent_dominance() -> None:
    client = _FakeLLMClient(
        OpenAICompatibleDecision(
            selected_operator_id="local_refine",
            phase="repair",
            rationale="choose a viable alternative while keeping the full pool available.",
            provider="openai-compatible",
            model="GPT-5.4",
            capability_profile="chat_compatible_json",
            performance_profile="balanced",
            raw_payload={"selected_operator_id": "local_refine"},
        )
    )
    controller = LLMOperatorController(client=client)
    candidates = (
        "native_sbx_pm",
        "move_hottest_cluster_toward_sink",
        "local_refine",
    )

    decision = controller.select_decision(_dominance_state(), candidates, np.random.default_rng(7))

    assert decision.selected_operator_id == "local_refine"
    assert client.last_kwargs is not None
    assert tuple(client.last_kwargs["candidate_operator_ids"]) == candidates
    user_prompt = json.loads(str(client.last_kwargs["user_prompt"]))
    assert tuple(user_prompt["candidate_operator_ids"]) == candidates
    assert "move_hottest_cluster_toward_sink" in user_prompt["candidate_operator_ids"]


def test_llm_controller_guardrail_prompt_is_soft_advice_not_removal() -> None:
    controller = LLMOperatorController(
        client=_FakeLLMClient(
            OpenAICompatibleDecision(
                selected_operator_id="local_refine",
                phase="repair",
                rationale="avoid recent over-concentration.",
                provider="openai-compatible",
                model="GPT-5.4",
                capability_profile="chat_compatible_json",
                performance_profile="balanced",
                raw_payload={"selected_operator_id": "local_refine"},
            )
        )
    )
    state = _dominance_state()
    candidates = (
        "native_sbx_pm",
        "move_hottest_cluster_toward_sink",
        "local_refine",
    )
    policy_snapshot = PolicySnapshot(
        phase="prefeasible_convert",
        allowed_operator_ids=candidates,
        suppressed_operator_ids=(),
        reset_active=False,
        reason_codes=("recent_dominance_concentration",),
        candidate_annotations={operator_id: {} for operator_id in candidates},
    )
    guardrail = {
        "applied": True,
        "reason": "recent_dominance_concentration",
        "dominant_operator_id": "move_hottest_cluster_toward_sink",
        "dominant_operator_share": 0.75,
        "filtered_operator_ids": ["move_hottest_cluster_toward_sink"],
        "effective_candidate_operator_ids": list(candidates),
    }

    prompt = controller._build_system_prompt(
        state,
        candidates,
        policy_snapshot=policy_snapshot,
        guardrail=guardrail,
    )

    assert "removed" not in prompt
    assert "current candidate set" not in prompt
    assert "move_hottest_cluster_toward_sink" in prompt
    assert "recent concentration" in prompt
    assert "consider alternatives" in prompt
```

- [ ] **Step 2: Run the new LLM controller tests and verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_llm_controller.py::test_llm_controller_preserves_full_candidate_pool_with_recent_dominance tests/optimizers/test_llm_controller.py::test_llm_controller_guardrail_prompt_is_soft_advice_not_removal
```

Expected: FAIL because current guardrails can filter candidates and the prompt says an operator was removed.

- [ ] **Step 3: Keep effective candidates equal to the original full pool in `select_decision()`**

In `optimizers/operator_pool/llm_controller.py`, change the candidate pipeline around lines 215-244 from hard-filtering to soft metadata collection.

The effective flow should be:

```python
        original_candidate_operator_ids = tuple(str(operator_id) for operator_id in operator_ids)
        if not original_candidate_operator_ids:
            raise ValueError("LLMOperatorController requires at least one candidate operator.")
        policy_snapshot = build_policy_snapshot(state, original_candidate_operator_ids)
        candidate_operator_ids = original_candidate_operator_ids
        _, recent_dominance_guardrail = self._apply_recent_dominance_guardrail(
            state,
            candidate_operator_ids,
            policy_snapshot=policy_snapshot,
        )
        _, generation_local_dominance_guardrail = self._apply_generation_local_dominance_guardrail(
            state,
            candidate_operator_ids,
        )
        _, generation_local_strategy_group_guardrail = self._apply_generation_local_strategy_group_guardrail(
            state,
            candidate_operator_ids,
        )
        exact_positive_metadata = self._exact_positive_candidate_advice(
            state,
            candidate_operator_ids,
            policy_snapshot=policy_snapshot,
        )
        guardrail = self._merge_guardrail_metadata(
            original_candidate_operator_ids=original_candidate_operator_ids,
            effective_candidate_operator_ids=candidate_operator_ids,
            policy_snapshot=policy_snapshot,
            dominance_guardrails=[
                recent_dominance_guardrail,
                generation_local_dominance_guardrail,
                generation_local_strategy_group_guardrail,
                exact_positive_metadata,
            ],
        )
```

If adding `_exact_positive_candidate_advice()` is too large for the minimal implementation, first skip exact-positive metadata and simply stop calling `_prioritize_exact_positive_candidate_operator_ids()` and `_apply_prefeasible_convert_exact_positive_contract()` in the effective candidate path. Existing prompt metadata can still expose exact-positive evidence through `build_prompt_projection()` if already present.

- [ ] **Step 4: Make guardrail helpers return metadata without changing support**

For `_apply_recent_dominance_guardrail`, `_apply_generation_local_dominance_guardrail`, and `_apply_generation_local_strategy_group_guardrail`, keep their current detection logic, but make the returned candidate tuple always equal the input tuple.

For example, replace the end of `_apply_recent_dominance_guardrail()` with:

```python
        return tuple(candidate_operator_ids), {
            "applied": True,
            "reason": "recent_dominance_concentration",
            "threshold_profile": threshold_profile,
            "dominant_operator_id": dominant_operator_id,
            "dominant_operator_share": dominant_share,
            "recent_window_size": recent_window_size,
            "recent_counts": dict(counter),
            "filtered_operator_ids": [dominant_operator_id],
            "original_candidate_operator_ids": list(candidate_operator_ids),
            "effective_candidate_operator_ids": list(candidate_operator_ids),
            "viable_alternative_operator_ids": [
                operator_id
                for operator_id in candidate_operator_ids
                if operator_id != dominant_operator_id
            ],
        }
```

Do the same for the generation-local guardrail helpers: keep `filtered_operator_ids` as a trace/advice field naming what would have been filtered, but set `effective_candidate_operator_ids` to the full input `candidate_operator_ids` and return `tuple(candidate_operator_ids)` as the first tuple.

- [ ] **Step 5: Rewrite system-prompt guardrail wording as soft advice**

Replace the return block in `_build_system_prompt()` currently saying `A dominance guardrail removed ...` with:

```python
        return (
            f"{prompt} "
            f"A dominance guardrail detected {dominant_operator_id} at "
            f"{dominant_share:.0%} recent concentration. Treat this as soft advice: consider alternatives "
            "when they are comparably applicable, but keep every provided candidate operator available if the "
            "current state makes it necessary."
        )
```

- [ ] **Step 6: Preserve trace visibility without implying support removal**

In `_merge_guardrail_metadata()`, keep `filtered_operator_ids` for audit as `advised_against_operator_ids`, while preserving backwards-compatible keys only if existing tests require them.

Preferred new fields:

```python
            "advised_against_operator_ids": filtered_operator_ids,
            "original_candidate_operator_ids": list(original_candidate_operator_ids),
            "effective_candidate_operator_ids": list(original_candidate_operator_ids),
```

If existing trace consumers still read `guardrail_filtered_operator_ids`, leave that field populated in `_decision_guardrail_metadata()`, but tests must assert that it is advisory and that candidate support stays full.

- [ ] **Step 7: Run the focused LLM controller tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_llm_controller.py
```

Expected: PASS. If older tests expected guardrail removal, update them to assert soft-advice metadata and full candidate preservation.

- [ ] **Step 8: Optional user-approved checkpoint**

Do not commit unless explicitly authorized. If commits are authorized, run:

```bash
git status --short
git add optimizers/operator_pool/llm_controller.py tests/optimizers/test_llm_controller.py
git commit -m "$(cat <<'EOF'
Make LLM guardrails advisory.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Align documentation with the B-shape contract

**Files:**
- Modify: `README.md:10-37`
- Modify: `AGENTS.md:7-17`
- Modify: `AGENTS.md:74-78`
- Modify: `CLAUDE.md:284-290`
- Test: no code test; verify with grep.

- [ ] **Step 1: Update README active-mainline wording**

In `README.md`, replace the sentence at the active mainline section that currently says `union` is clean while `llm` is assisted with:

```markdown
At the time of this restore plan, the active paper-facing mainlines were `s1_typical` and `s2_staged`. The current active mainline is the S5-S7 aggressive family, with `s5_aggressive15` as the primary debugging template.
```

- [ ] **Step 2: Update README legality-policy bullet**

Replace the bullet that says clean baselines use `minimal_canonicalization` and assisted `llm` uses `projection_plus_local_restore` with:

```markdown
- paper-facing `union` and `llm` runs share the same clean legality policy; LLM-specific improvements are limited to representation-layer controller state, reflection, memory, and soft policy guidance
```

- [ ] **Step 3: Update AGENTS ladder split**

In `AGENTS.md`, replace the active optimizer ladder split bullets with:

```markdown
- The active optimizer ladder uses a matched paper-facing substrate:
  - `raw`: native backbone + clean legality policy
  - `union`: primitive operator registry + random controller + clean legality policy
  - `llm`: same primitive operator registry + LLM representation-layer controller + same clean legality policy
```

- [ ] **Step 4: Update AGENTS fixed benchmark legality bullet**

Replace the bullet about clean baselines and assisted framework runs with:

```markdown
- paper-facing `union` and `llm` runs must keep the same operator registry, operator pool, repair/canonicalization path, legality policy, and expensive-evaluation budget; `llm` may add only representation-layer prompt state, reflection, memory, and soft policy guidance
```

- [ ] **Step 5: Update CLAUDE evidence/reporting wording**

Replace the current bullets around `CLAUDE.md:288-289` with:

```markdown
- Keep the decision encoding, evaluation spec, repair/canonicalization path, legality policy, operator pool, and expensive-evaluation budget matched across paper-facing `union` / `llm` comparisons unless a document explicitly defines a different experiment class.
- Describe `nsga2_union` and `nsga2_llm` as using the same shared semantic primitive operator substrate; `llm` differs only through its representation-layer controller state, reflection, memory, and soft policy guidance over the same candidate support.
```

- [ ] **Step 6: Verify old split language is gone from paper-facing docs**

Run:

```bash
grep -nE "assisted framework line|primitive_plus_assisted|projection_plus_local_restore|clean baselines use|minimal_canonicalization; assisted" README.md AGENTS.md CLAUDE.md || true
```

Expected: no paper-facing split language remains in `README.md`, `AGENTS.md`, or `CLAUDE.md`. If `projection_plus_local_restore` remains only in historical references outside these files, do not edit them in this task.

- [ ] **Step 7: Optional user-approved checkpoint**

Do not commit unless explicitly authorized. If commits are authorized, run:

```bash
git status --short
git add README.md AGENTS.md CLAUDE.md
git commit -m "$(cat <<'EOF'
Document matched union and LLM substrate.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Focused verification and contract smoke audit

**Files:**
- Read/verify: `controller_trace.jsonl`, `operator_trace.jsonl`, and `run.yaml` from any smoke output produced by the commands below.
- No required source modifications unless verification reveals a concrete contract failure.

- [ ] **Step 1: Run all focused optimizer contract tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_operator_pool_contracts.py tests/optimizers/test_llm_policy_kernel.py tests/optimizers/test_llm_controller.py
```

Expected: PASS.

- [ ] **Step 2: Run a tiny LLM smoke only if credentials are available and the user approves external LLM use**

Because this uses external LLM credentials from the environment, ask the user before running it. If approved, run with a minimal budget and local output root:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s1_typical_llm.yaml --output-root ./scenario_runs/s1_typical/llm-contract-smoke --population-size 6 --num-generations 2 --evaluation-workers 1 --skip-render
```

Expected: command completes or fails for an environmental/provider reason. A provider/network failure is not a contract failure; inspect generated traces only if a run directory is produced.

- [ ] **Step 3: If a smoke run exists, verify trace candidate support manually**

Use Python rather than shell text parsing so JSONL parsing is strict. Replace `<run_dir>` with the concrete path produced by the smoke command:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python - <<'PY'
from pathlib import Path
import json

run_dir = Path("<run_dir>")
controller_trace = run_dir / "traces" / "controller_trace.jsonl"
rows = [json.loads(line) for line in controller_trace.read_text(encoding="utf-8").splitlines() if line.strip()]
lengths = {len(row.get("candidate_operator_ids", [])) for row in rows if row.get("candidate_operator_ids")}
print({"candidate_pool_lengths": sorted(lengths), "row_count": len(rows)})
assert lengths == {7}
PY
```

Expected: output includes `candidate_pool_lengths: [7]` for the current clean primitive pool.

- [ ] **Step 4: Verify scenario specs directly**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python - <<'PY'
from pathlib import Path
import yaml

pairs = [
    ("scenarios/optimization/s1_typical_union.yaml", "scenarios/optimization/s1_typical_llm.yaml"),
    ("scenarios/optimization/s2_staged_union.yaml", "scenarios/optimization/s2_staged_llm.yaml"),
]
for union_path, llm_path in pairs:
    union = yaml.safe_load(Path(union_path).read_text(encoding="utf-8"))
    llm = yaml.safe_load(Path(llm_path).read_text(encoding="utf-8"))
    assert union["operator_control"]["operator_pool"] == llm["operator_control"]["operator_pool"]
    assert union["operator_control"]["registry_profile"] == llm["operator_control"]["registry_profile"]
    assert union["evaluation_protocol"]["legality_policy_id"] == llm["evaluation_protocol"]["legality_policy_id"]
    print(llm_path, "OK")
PY
```

Expected:

```text
scenarios/optimization/s1_typical_llm.yaml OK
scenarios/optimization/s2_staged_llm.yaml OK
```

- [ ] **Step 5: Report verification state without overclaiming performance**

Report only these facts unless a real smoke run completed:

```text
Focused contract tests passed. The paper-facing LLM specs now share the union substrate. policy_kernel preserves candidate support and emits soft annotations. LLM guardrails are advisory and the model sees the full shared candidate pool. No new performance claim is made until matched reruns are completed.
```

- [ ] **Step 6: Optional user-approved checkpoint**

Do not commit unless explicitly authorized. If commits are authorized, run:

```bash
git status --short
git add scenarios/optimization/s1_typical_llm.yaml scenarios/optimization/s2_staged_llm.yaml optimizers/operator_pool/policy_kernel.py optimizers/operator_pool/llm_controller.py tests/optimizers/test_operator_pool_contracts.py tests/optimizers/test_llm_policy_kernel.py tests/optimizers/test_llm_controller.py README.md AGENTS.md CLAUDE.md docs/superpowers/specs/2026-04-27-fair-raw-union-llm-comparison-restore-design.md docs/superpowers/plans/2026-04-28-fair-raw-union-llm-comparison-restore.md
git commit -m "$(cat <<'EOF'
Restore fair LLM comparison contract.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review

**Spec coverage:**
- B-shape substrate equality is implemented by Task 1 and verified again in Task 5.
- `policy_kernel` annotation-only behavior is implemented by Task 2.
- LLM full-candidate preservation and soft guardrails are implemented by Task 3.
- Documentation alignment is implemented by Task 4.
- Phase 2 shared-pool rebalance is intentionally excluded and called out as a future design, matching the approved spec.

**Placeholder scan:** The plan contains concrete file paths, commands, expected results, and code blocks for each code-changing task. No unresolved placeholders are intentionally present.

**Type consistency:** The plan uses existing `PolicySnapshot` fields (`phase`, `allowed_operator_ids`, `suppressed_operator_ids`, `reset_active`, `reason_codes`, `candidate_annotations`), existing `ControllerState`, existing `OpenAICompatibleDecision`, and existing scenario YAML keys. New helper `_assert_snapshot_preserves_support()` is local to tests. Optional `_exact_positive_candidate_advice()` is explicitly not required for the minimal implementation.
