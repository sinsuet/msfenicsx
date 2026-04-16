# S1 Typical L2 LLM Controller Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the `s1_typical` `nsga2_llm` route from a stable-family selector into a true semantic-action controller while preserving the controller-only comparison boundary against `union`.

**Architecture:** Keep the fixed `union` operator registry, matched optimizer budget, shared repair, shared PDE solve, and shared survival semantics unchanged. Implement the `L2` upgrade entirely in the controller stack by restoring semantic candidate visibility inside `policy_kernel`, adding action-conditioned spatial state and regime-conditioned reflection, extending the `LLM` prompt to reason in intent-first form, and exposing diagnostics that prove the `LLM` actually saw and used semantic actions.

**Tech Stack:** Python 3.12, pytest, pymoo NSGA-II union adapter, `optimizers.operator_pool`, OpenAI-compatible transport in `llm/openai_compatible/`, YAML/JSON trace artifacts

---

## File Map

**Core controller files**

- `/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py`
  - controls pre-`LLM` candidate shaping and phase-aware guardrails
- `/home/hymn/msfenicsx/optimizers/operator_pool/domain_state.py`
  - computes run, parent, archive, phase, and layout-derived state summaries
- `/home/hymn/msfenicsx/optimizers/operator_pool/reflection.py`
  - builds operator credit summaries from controller/operator trace history
- `/home/hymn/msfenicsx/optimizers/operator_pool/state_builder.py`
  - assembles the controller-visible prompt panels
- `/home/hymn/msfenicsx/optimizers/operator_pool/prompt_projection.py`
  - projects controller state into the compact prompt payload
- `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py`
  - builds prompts, requests structured `LLM` decisions, and records decision metadata
- `/home/hymn/msfenicsx/optimizers/operator_pool/diagnostics.py`
  - aggregates controller trace diagnostics for post-run analysis

**Transport/schema files**

- `/home/hymn/msfenicsx/llm/openai_compatible/schemas.py`
  - structured-output schema for `LLM` operator decisions
- `/home/hymn/msfenicsx/llm/openai_compatible/client.py`
  - live chat-compatible and responses-native request handling

**Tests**

- `/home/hymn/msfenicsx/tests/optimizers/test_llm_policy_kernel.py`
- `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller_state.py`
- `/home/hymn/msfenicsx/tests/optimizers/test_llm_prompt_projection.py`
- `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller.py`
- `/home/hymn/msfenicsx/tests/optimizers/test_llm_client.py`
- `/home/hymn/msfenicsx/tests/optimizers/test_llm_decision_summary.py`

**Spec and docs**

- `/home/hymn/msfenicsx/docs/superpowers/specs/2026-04-14-s1-typical-llm-l2-controller-recovery-design.md`
- `/home/hymn/msfenicsx/scenarios/optimization/s1_typical_llm.yaml`

### Task 1: Restore Semantic Visibility in `policy_kernel`

**Files:**
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_policy_kernel.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/policy_kernel.py`

- [ ] **Step 1: Add a failing policy-kernel test that forbids stable-only collapse in post-feasible expand**

```python
def test_post_feasible_expand_keeps_stable_backbone_plus_semantic_visibility() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_expand_state(),
        (
            "native_sbx_pm",
            "global_explore",
            "local_refine",
            "move_hottest_cluster_toward_sink",
            "slide_sink",
            "rebalance_layout",
        ),
    )

    semantic_ids = {
        "move_hottest_cluster_toward_sink",
        "slide_sink",
        "rebalance_layout",
    }
    assert {"native_sbx_pm", "global_explore", "local_refine"}.issubset(policy.allowed_operator_ids)
    assert any(operator_id in semantic_ids for operator_id in policy.allowed_operator_ids)
```

- [ ] **Step 2: Add a failing policy-kernel test for post-feasible recover keeping bounded semantic visibility**

```python
def test_post_feasible_recover_retains_at_least_one_semantic_candidate() -> None:
    policy_kernel = _policy_kernel_module()
    policy = policy_kernel.build_policy_snapshot(_post_feasible_recover_state(), ...)

    assert "native_sbx_pm" in policy.allowed_operator_ids
    assert "local_refine" in policy.allowed_operator_ids
    assert any(
        operator_id in {"repair_sink_budget", "slide_sink", "move_hottest_cluster_toward_sink"}
        for operator_id in policy.allowed_operator_ids
    )
```

- [ ] **Step 3: Add a failing controller-level test that the effective candidate set can still contain semantic operators**

```python
def test_llm_controller_request_can_include_semantic_candidates_post_feasible() -> None:
    client = _FakeLLMClient(
        decision=OpenAICompatibleDecision(
            selected_operator_id="slide_sink",
            phase="post_feasible_expand",
            rationale="semantic visibility is available",
            provider="openai-compatible",
            model="gpt-5.4",
            capability_profile="chat_compatible_json",
            performance_profile="balanced",
            raw_payload={"selected_operator_id": "slide_sink"},
        )
    )
    controller = LLMOperatorController(controller_parameters=_controller_parameters(), client=client)

    controller.select_decision(_domain_grounded_state(), _full_union_registry(), np.random.default_rng(7))

    assert client.last_kwargs is not None
    assert "slide_sink" in tuple(client.last_kwargs["candidate_operator_ids"])
```

- [ ] **Step 4: Run the red tests and confirm the failure matches the current collapse behavior**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_policy_kernel.py::test_post_feasible_expand_keeps_stable_backbone_plus_semantic_visibility \
  tests/optimizers/test_llm_policy_kernel.py::test_post_feasible_recover_retains_at_least_one_semantic_candidate \
  tests/optimizers/test_llm_controller.py::test_llm_controller_request_can_include_semantic_candidates_post_feasible \
  -v
```

Expected:

- tests fail because post-feasible shaping currently suppresses all semantic operators

- [ ] **Step 5: Implement bounded semantic visibility in `policy_kernel.py`**

```python
_STABLE_BACKBONE_IDS = ("native_sbx_pm", "global_explore", "local_refine")
_POST_FEASIBLE_SEMANTIC_MIN_VISIBLE = 1
_POST_FEASIBLE_SEMANTIC_MAX_VISIBLE = 2

def _bounded_post_feasible_candidates(...):
    stable_ids = [...]
    semantic_ids = _rank_semantic_candidates(...)
    visible_semantic_ids = semantic_ids[:_POST_FEASIBLE_SEMANTIC_MAX_VISIBLE]
    if visible_semantic_ids:
        return tuple(dict.fromkeys([*stable_ids, *visible_semantic_ids]))
    return tuple(stable_ids)
```

- [ ] **Step 6: Preserve current safeguards but downgrade them from hard exclusion to bounded bias**

Implementation notes:

- keep recent-dominance guardrails
- keep recover versus expand phase handling
- do not allow the candidate set to shrink to semantic-only
- do not allow the candidate set to shrink to stable-only by default in post-feasible phases

- [ ] **Step 7: Re-run the focused tests and confirm green**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_llm_controller.py \
  -v
```

Expected: all touched tests pass

- [ ] **Step 8: Commit the semantic-visibility recovery**

```bash
git add \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_llm_controller.py \
  optimizers/operator_pool/policy_kernel.py
git commit -m "feat: restore bounded semantic visibility for llm controller"
```

### Task 2: Add Action-Conditioned Spatial State and Operator Applicability

**Files:**
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller_state.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_prompt_projection.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/domain_state.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/reflection.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/state_builder.py`

- [ ] **Step 1: Add a failing state-builder test for spatial motif summaries**

```python
def test_build_controller_state_emits_spatial_motif_panel() -> None:
    state = build_controller_state(...)

    spatial_panel = state.metadata["prompt_panels"]["spatial_panel"]
    assert spatial_panel["hotspot_to_sink_offset"] == pytest.approx(0.12)
    assert "local_congestion_pair" in spatial_panel
    assert "sink_budget_bucket" in spatial_panel
```

- [ ] **Step 2: Add a failing state-builder test for operator applicability fields**

```python
def test_build_controller_state_emits_operator_applicability_fields() -> None:
    state = build_controller_state(...)

    row = state.metadata["prompt_panels"]["operator_panel"]["slide_sink"]
    assert row["applicability"] in {"high", "medium", "low"}
    assert row["expected_peak_effect"] in {"improve", "neutral", "risk"}
    assert row["expected_gradient_effect"] in {"improve", "neutral", "risk"}
    assert row["spatial_match_reason"]
```

- [ ] **Step 3: Add a failing prompt-projection test that keeps spatial panel in post-feasible payloads**

```python
def test_post_feasible_prompt_projection_keeps_spatial_panel_and_operator_applicability() -> None:
    payload = build_prompt_projection(...)

    assert "spatial_panel" in payload["prompt_panels"]
    assert "applicability" in payload["prompt_panels"]["operator_panel"]["slide_sink"]
```

- [ ] **Step 4: Run the red tests and confirm missing spatial-panel failures**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller_state.py::test_build_controller_state_emits_spatial_motif_panel \
  tests/optimizers/test_llm_controller_state.py::test_build_controller_state_emits_operator_applicability_fields \
  tests/optimizers/test_llm_prompt_projection.py::test_post_feasible_prompt_projection_keeps_spatial_panel_and_operator_applicability \
  -v
```

Expected:

- tests fail because `spatial_panel` and operator applicability fields are not emitted yet

- [ ] **Step 5: Add spatial motif helpers in `domain_state.py`**

```python
def build_spatial_motif_state(...):
    return {
        "hotspot_to_sink_offset": ...,
        "hotspot_inside_sink_window": ...,
        "hottest_cluster_centroid": ...,
        "hottest_cluster_compactness": ...,
        "local_congestion_pair": ...,
        "nearest_neighbor_gap_min": ...,
        "sink_budget_bucket": ...,
    }
```

- [ ] **Step 6: Add semantic operator applicability synthesis in `reflection.py` or `state_builder.py`**

```python
operator_panel["slide_sink"].update(
    {
        "applicability": "high",
        "expected_peak_effect": "improve",
        "expected_gradient_effect": "neutral",
        "expected_feasibility_risk": "low",
        "spatial_match_reason": "hotspot sits to the right of the current sink window",
    }
)
```

- [ ] **Step 7: Inject the new `spatial_panel` and applicability fields into `state_builder.py` and `prompt_projection.py`**

Implementation notes:

- keep existing `run_panel`, `regime_panel`, and `parent_panel`
- add one new compact `spatial_panel`
- do not dump raw full-layout geometry into the prompt

- [ ] **Step 8: Re-run the touched tests and confirm green**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller_state.py \
  tests/optimizers/test_llm_prompt_projection.py \
  -v
```

Expected: all touched tests pass

- [ ] **Step 9: Commit the spatial-state upgrade**

```bash
git add \
  tests/optimizers/test_llm_controller_state.py \
  tests/optimizers/test_llm_prompt_projection.py \
  optimizers/operator_pool/domain_state.py \
  optimizers/operator_pool/reflection.py \
  optimizers/operator_pool/state_builder.py \
  optimizers/operator_pool/prompt_projection.py
git commit -m "feat: add spatial motifs and operator applicability for llm control"
```

### Task 3: Add Intent-First Prompting and Backward-Compatible Structured Output

**Files:**
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_client.py`
- Modify: `/home/hymn/msfenicsx/llm/openai_compatible/schemas.py`
- Modify: `/home/hymn/msfenicsx/llm/openai_compatible/client.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py`

- [ ] **Step 1: Add a failing controller test that the prompt asks for intent-first reasoning**

```python
def test_llm_controller_prompt_requests_intent_before_operator_choice() -> None:
    client = _FakeLLMClient(decision=_decision("slide_sink"))
    controller = LLMOperatorController(controller_parameters=_controller_parameters(), client=client)

    controller.select_decision(_domain_grounded_state(), _full_union_registry(), np.random.default_rng(7))

    assert client.last_kwargs is not None
    assert "intent" in str(client.last_kwargs["system_prompt"]).lower()
    assert "preserve_score" in str(client.last_kwargs["user_prompt"])
    assert "frontier_score" in str(client.last_kwargs["user_prompt"])
```

- [ ] **Step 2: Add a failing client/schema test for optional `selected_intent` support**

```python
def test_chat_compatible_json_schema_allows_optional_selected_intent() -> None:
    schema = build_operator_decision_schema(("native_sbx_pm", "slide_sink"))

    assert "selected_intent" in schema["properties"]
    assert "selected_intent" not in schema["required"]
```

- [ ] **Step 3: Add a failing client parse test that preserves backward compatibility when `selected_intent` is missing**

```python
def test_chat_compatible_json_client_accepts_payload_without_selected_intent(...) -> None:
    response = client.request_operator_decision(...)
    assert response.selected_operator_id == "global_explore"
```

- [ ] **Step 4: Run the red tests and confirm the current prompt/schema do not satisfy them**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller.py::test_llm_controller_prompt_requests_intent_before_operator_choice \
  tests/optimizers/test_llm_client.py::test_chat_compatible_json_schema_allows_optional_selected_intent \
  tests/optimizers/test_llm_client.py::test_chat_compatible_json_client_accepts_payload_without_selected_intent \
  -v
```

Expected:

- prompt test fails because intent-first language is missing
- schema test fails because `selected_intent` is not defined

- [ ] **Step 5: Extend the structured schema and parser in a backward-compatible way**

```python
"selected_intent": {
    "type": "string",
}
```

Implementation notes:

- keep `selected_operator_id`, `phase`, and `rationale` required
- keep `selected_intent` optional
- parse and retain it when present, ignore it safely when absent

- [ ] **Step 6: Rewrite `LLMOperatorController` prompts around intent-first reasoning**

Implementation sketch:

```python
prompt = (
    "First choose the operator intent that best matches the current phase and pressure. "
    "Then choose exactly one operator id from candidate_operator_ids that implements that intent. "
    "Use preserve_score, frontier_score, regression_risk, and operator applicability as the main decision axes."
)
```

- [ ] **Step 7: Re-run the touched tests and confirm green**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_llm_client.py \
  -v
```

Expected: all touched tests pass

- [ ] **Step 8: Commit the intent-first prompt/schema update**

```bash
git add \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_llm_client.py \
  llm/openai_compatible/schemas.py \
  llm/openai_compatible/client.py \
  optimizers/operator_pool/llm_controller.py
git commit -m "feat: add intent-first llm operator prompting"
```

### Task 4: Add Regime-Conditioned Reflection and Retrieval Panels

**Files:**
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller_state.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/reflection.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/state_builder.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py`

- [ ] **Step 1: Add a failing state test for regime-conditioned operator credit**

```python
def test_reflection_summary_tracks_credit_by_phase_family_and_sink_bucket() -> None:
    summary = summarize_operator_history(...)

    row = summary["slide_sink"]
    assert "credit_by_regime" in row
    assert ("post_feasible_expand", "thermal_limit", "full_sink") in row["credit_by_regime"]
```

- [ ] **Step 2: Add a failing state-builder test for retrieval panel emission**

```python
def test_build_controller_state_emits_retrieved_episode_panel() -> None:
    state = build_controller_state(...)

    retrieval_panel = state.metadata["prompt_panels"]["retrieval_panel"]
    assert retrieval_panel["query_regime"]["phase"] == "post_feasible_expand"
    assert retrieval_panel["matched_episodes"]
```

- [ ] **Step 3: Add a failing controller test that the prompt includes retrieved similar episodes**

```python
def test_llm_controller_prompt_includes_retrieved_episode_context() -> None:
    client = _FakeLLMClient(decision=_decision("slide_sink"))
    controller = LLMOperatorController(controller_parameters=_controller_parameters(), client=client)

    controller.select_decision(_retrieval_rich_state(), _full_union_registry(), np.random.default_rng(7))

    assert "matched_episodes" in str(client.last_kwargs["user_prompt"])
```

- [ ] **Step 4: Run the red tests and confirm retrieval support is missing**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller_state.py::test_reflection_summary_tracks_credit_by_phase_family_and_sink_bucket \
  tests/optimizers/test_llm_controller_state.py::test_build_controller_state_emits_retrieved_episode_panel \
  tests/optimizers/test_llm_controller.py::test_llm_controller_prompt_includes_retrieved_episode_context \
  -v
```

Expected:

- tests fail because no retrieval panel or regime-conditioned credit table exists yet

- [ ] **Step 5: Implement compact regime-conditioned credit in `reflection.py`**

```python
credit_key = (phase, dominant_violation_family, sink_budget_bucket)
credit_by_regime.setdefault(credit_key, {...})
credit_by_regime[credit_key]["frontier_add_count"] += 1
credit_by_regime[credit_key]["feasible_preservation_count"] += 1
```

- [ ] **Step 6: Implement top-k similar episode retrieval in `state_builder.py`**

Implementation notes:

- keep retrieval run-internal only
- retrieve from current-run operator outcomes only
- limit to a compact top `k <= 3` episode list
- expose only summary fields, not raw vectors

- [ ] **Step 7: Thread the retrieval panel into `llm_controller.py` prompt construction**

Implementation sketch:

```python
"Use retrieval_panel.matched_episodes as case-based evidence. "
"Prefer operators that helped in similar post-feasible regimes when preserve_score remains acceptable."
```

- [ ] **Step 8: Re-run the touched tests and confirm green**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller_state.py \
  tests/optimizers/test_llm_controller.py \
  -v
```

Expected: all touched tests pass

- [ ] **Step 9: Commit the reflection + retrieval layer**

```bash
git add \
  tests/optimizers/test_llm_controller_state.py \
  tests/optimizers/test_llm_controller.py \
  optimizers/operator_pool/reflection.py \
  optimizers/operator_pool/state_builder.py \
  optimizers/operator_pool/llm_controller.py
git commit -m "feat: add regime-conditioned reflection and llm retrieval panels"
```

### Task 5: Wire Live Config + Diagnostics for Proving Semantic Use

**Files:**
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_client.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_decision_summary.py`
- Modify: `/home/hymn/msfenicsx/llm/openai_compatible/client.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/diagnostics.py`

- [ ] **Step 1: Add a failing client test that `reasoning.effort` is forwarded in chat-compatible HTTP mode**

```python
def test_chat_compatible_json_http_request_forwards_reasoning_when_configured(...) -> None:
    response = client.request_operator_decision(...)

    assert http_client.last_json is not None
    assert http_client.last_json["reasoning"] == {"effort": "medium"}
```

- [ ] **Step 2: Add a failing diagnostics test for semantic visibility metrics**

```python
def test_controller_trace_summary_reports_semantic_visibility_rate(tmp_path: Path) -> None:
    summary = analyze_controller_trace(...)

    assert summary["semantic_visibility_rate"] > 0.0
    assert summary["semantic_candidate_count_avg"] >= 1.0
    assert "semantic_frontier_add_count" in summary
```

- [ ] **Step 3: Add a failing diagnostics test for stable-versus-semantic Pareto ownership**

```python
def test_controller_trace_summary_reports_stable_vs_semantic_pareto_ownership(tmp_path: Path) -> None:
    summary = analyze_controller_trace(...)

    assert summary["stable_vs_semantic_pareto_ownership"]["semantic"] >= 1
```

- [ ] **Step 4: Run the red tests and confirm the live-request and diagnostics fields are absent**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_client.py::test_chat_compatible_json_http_request_forwards_reasoning_when_configured \
  tests/optimizers/test_llm_decision_summary.py \
  -v
```

Expected:

- client test fails because `chat_compatible_json` HTTP payload does not include `reasoning`
- diagnostics assertions fail because semantic visibility fields are not summarized yet

- [ ] **Step 5: Forward `reasoning` in `client.py` when the provider path supports it**

```python
if self.config.reasoning:
    request_payload["reasoning"] = dict(self.config.reasoning)
```

Implementation notes:

- keep existing payload shape unchanged otherwise
- if a provider rejects `reasoning`, handle that in a compatibility-safe follow-up instead of silently dropping the field

- [ ] **Step 6: Extend `diagnostics.py` with semantic-usage metrics**

Implementation sketch:

```python
summary["semantic_visibility_rate"] = semantic_visible_decision_count / total_decision_count
summary["semantic_candidate_count_avg"] = semantic_candidate_total / total_decision_count
summary["semantic_selection_rate"] = semantic_selection_count / total_decision_count
summary["stable_vs_semantic_pareto_ownership"] = {"stable": ..., "semantic": ...}
```

- [ ] **Step 7: Re-run the touched tests and confirm green**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_client.py \
  tests/optimizers/test_llm_decision_summary.py \
  -v
```

Expected: all touched tests pass

- [ ] **Step 8: Run the full focused controller suite**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_llm_controller_state.py \
  tests/optimizers/test_llm_prompt_projection.py \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_llm_client.py \
  tests/optimizers/test_llm_decision_summary.py \
  -v
```

Expected: all focused `LLM` controller tests pass

- [ ] **Step 9: Commit the live-config + diagnostics finishing pass**

```bash
git add \
  tests/optimizers/test_llm_client.py \
  tests/optimizers/test_llm_decision_summary.py \
  llm/openai_compatible/client.py \
  optimizers/operator_pool/diagnostics.py
git commit -m "feat: expose live llm reasoning config and semantic usage diagnostics"
```

## Final Verification

- [ ] **Step 1: Re-run the official focused suite plus spec/IO guardrails**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_llm_controller_state.py \
  tests/optimizers/test_llm_prompt_projection.py \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_llm_client.py \
  tests/optimizers/test_llm_decision_summary.py \
  tests/optimizers/test_optimizer_io.py \
  tests/optimizers/test_operator_pool_adapters.py \
  -v
```

Expected:

- all touched tests pass
- no regression in spec round-trip or adapter behavior

- [ ] **Step 2: Run one matched live validation after code review**

Run:

```bash
/home/hymn/miniconda3/bin/conda run --no-capture-output -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/s1_typical_llm.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s1_typical/llm-l2-smoke
```

Expected:

- run completes without transport failure
- `llm_request_trace.jsonl` shows semantic candidates are visible post-feasible
- controller trace diagnostics show non-zero semantic visibility and semantic selection

- [ ] **Step 3: Generate a cheap post-run trace summary**

Run:

```bash
/home/hymn/miniconda3/bin/conda run --no-capture-output -n msfenicsx python -m optimizers.cli analyze-controller-trace \
  --controller-trace ./scenario_runs/s1_typical/llm-l2-smoke/llm/seeds/seed-11/controller_trace.json \
  --output ./scenario_runs/s1_typical/llm-l2-smoke/llm/reports/controller_trace_summary.json
```

Expected:

- summary includes `semantic_visibility_rate`
- summary includes `stable_vs_semantic_pareto_ownership`
- summary no longer indicates stable-only collapse across all post-feasible decisions

- [ ] **Step 4: Compare against the current `0414_1618__llm` baseline**

Compare:

- Pareto size
- pooled non-dominated ownership
- semantic visibility rate
- semantic frontier contribution
- fallback count
- average request latency

- [ ] **Step 5: Document outcome before any further tuning**

Write a short report note covering:

- whether semantic actions were truly visible
- whether semantic actions were actually selected
- whether they contributed frontier or preservation value
- whether the matched `llm` route improved over the current live baseline

- [ ] **Step 6: Commit the final implementation and verification note**

```bash
git add .
git commit -m "feat: implement l2 semantic llm controller recovery"
```
