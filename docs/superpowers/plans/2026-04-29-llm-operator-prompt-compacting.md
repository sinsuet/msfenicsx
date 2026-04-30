# LLM Operator Prompt Compacting and Fallback Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> Status: superseded for active S5-S7 LLM configs by the `semantic_ranked_pick` route. Current S5/S6/S7 LLM specs use `max_output_tokens: 512` and shared S5 controller parameters.

**Goal:** Make the LLM operator-selection prompt smaller and more state-aligned while separating prompt/protocol failures from external concurrency-induced fallback.

**Architecture:** Keep the existing state-builder and policy-kernel semantics intact. Add compact prompt projection helpers that turn the current audit-style metadata into a decision table, make the response contract tolerate short JSON decisions, and add trace summarization fields so timeout-heavy runs can be diagnosed without assuming the prompt is the only root cause.

**Tech Stack:** Python 3.12, pytest, YAML optimization specs, OpenAI-compatible chat JSON transport, existing `optimizers.operator_pool` and `llm.openai_compatible` modules.

---

## Files and Responsibilities

- Modify `optimizers/operator_pool/prompt_projection.py`: compact post-feasible `operator_panel` rows and add request-budget metadata without changing controller state construction.
- Modify `optimizers/operator_pool/llm_controller.py`: shorten static system prompt, keep structured metadata as the decision surface, and emit prompt size diagnostics in request trace rows.
- Modify `llm/openai_compatible/schemas.py`: make `phase` and `rationale` optional in structured schema so short responses do not fail when `selected_operator_id` is valid.
- Modify `llm/openai_compatible/client.py`: parse minimal valid JSON decisions, default missing `phase`/`rationale` to empty strings, and make retry guidance match the relaxed schema.
- Modify `scenarios/optimization/s5_aggressive15_llm.yaml` and `scenarios/optimization/s6_aggressive20_llm.yaml`: raise `max_output_tokens` from 72 to 128 to avoid JSON truncation while keeping responses short.
- Modify `tests/optimizers/test_llm_prompt_projection.py`: add compactness and field-retention tests for projection.
- Modify `tests/optimizers/test_llm_controller.py`: add prompt-size diagnostic and shortened-system-prompt tests.
- Modify `tests/optimizers/test_llm_client.py`: add minimal-response parsing and schema tests.
- Modify `tests/optimizers/test_s5_aggressive15_specs.py` and `tests/optimizers/test_s6_aggressive20_specs.py`: assert the small-scenario LLM output token budget is 128.

Do not modify generated run artifacts under `scenario_runs/`. Use them only as evidence for thresholds and reproduction context.

---

### Task 1: Relax the response contract for short JSON decisions

**Files:**
- Modify: `llm/openai_compatible/schemas.py:8-29`
- Modify: `llm/openai_compatible/client.py:125-160,317-360`
- Test: `tests/optimizers/test_llm_client.py`

- [ ] **Step 1: Add failing schema and parser tests**

Append these tests to `tests/optimizers/test_llm_client.py`:

```python
def test_operator_decision_schema_requires_only_selected_operator_id() -> None:
    schema = build_operator_decision_schema(("native_sbx_pm", "local_refine"))

    assert schema["required"] == ["selected_operator_id"]
    assert schema["properties"]["selected_operator_id"]["enum"] == ["native_sbx_pm", "local_refine"]
    assert "phase" in schema["properties"]
    assert "rationale" in schema["properties"]


def test_chat_compatible_json_client_accepts_minimal_operator_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    chat_api = _FakeChatCompletionsAPI('{"selected_operator_id": "local_refine"}')
    client = OpenAICompatibleClient(
        _build_config(capability_profile="chat_compatible_json"),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    response = client.request_operator_decision(
        system_prompt="system prompt",
        user_prompt="user prompt",
        candidate_operator_ids=("native_sbx_pm", "local_refine"),
    )

    assert response.selected_operator_id == "local_refine"
    assert response.phase == ""
    assert response.rationale == ""
```

- [ ] **Step 2: Run the focused client test and verify it fails**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_llm_client.py
```

Expected: FAIL because `build_operator_decision_schema()` still requires `phase` and `rationale`, or because parser assumes those keys are present in downstream prompt text.

- [ ] **Step 3: Relax the schema requirement**

Change `llm/openai_compatible/schemas.py` so the returned schema keeps `phase` and `rationale` as allowed properties but only requires `selected_operator_id`:

```python
def build_operator_decision_schema(candidate_operator_ids: Sequence[str]) -> dict[str, Any]:
    operator_ids = [str(operator_id) for operator_id in candidate_operator_ids]
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "selected_operator_id": {
                "type": "string",
                "enum": operator_ids,
            },
            "selected_intent": {
                "type": "string",
            },
            "phase": {
                "type": "string",
            },
            "rationale": {
                "type": "string",
            },
        },
        "required": ["selected_operator_id"],
    }
```

- [ ] **Step 4: Make client instructions match the relaxed contract**

In `llm/openai_compatible/client.py`, update `_build_chat_json_system_prompt()` to request short JSON while making `phase` and `rationale` optional:

```python
        return (
            f"{normalized_prompt.rstrip()} "
            "Return exactly one JSON object. "
            "Required key: selected_operator_id. Optional keys: phase, rationale, selected_intent. "
            f"The selected_operator_id value must exactly equal one of {list(candidate_operator_ids)}. "
            "If rationale is present, keep it under 12 words. "
            "If selected_intent is present, keep it short and route-like."
        )
```

Update `_build_retry_system_prompt()` similarly:

```python
        return (
            f"{system_prompt.rstrip()} "
            "Previous response was invalid. "
            "It must return JSON only. Required key: selected_operator_id. "
            "Optional keys: phase, rationale, selected_intent. "
            f"The selected_operator_id value must exactly equal one of {list(operator_ids)}. "
            "If rationale is present, keep it under 12 words. "
            f"Invalid reason: {error_message}"
        )
```

The parser at `llm/openai_compatible/client.py:153-154` already uses `payload.get()` for `phase` and `rationale`; keep that behavior and do not add fallback-specific logic.

- [ ] **Step 5: Run the focused client test and verify it passes**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_llm_client.py
```

Expected: PASS.

- [ ] **Step 6: Commit the response contract change**

Run:

```bash
git add llm/openai_compatible/schemas.py llm/openai_compatible/client.py tests/optimizers/test_llm_client.py
git commit -m "fix: relax llm operator decision response contract"
```

---

### Task 2: Compact the operator prompt projection into a decision table

**Files:**
- Modify: `optimizers/operator_pool/prompt_projection.py:73-124,165-230,308-314,410-437`
- Test: `tests/optimizers/test_llm_prompt_projection.py`

- [ ] **Step 1: Add failing compactness tests**

Append this test to `tests/optimizers/test_llm_prompt_projection.py`:

```python
def test_post_feasible_operator_panel_projects_compact_decision_rows() -> None:
    prompt_projection = _prompt_projection_module()
    state = _post_feasible_state()
    state.metadata["prompt_panels"]["operator_panel"]["repair_sink_budget"].update(
        {
            "dominant_violation_relief": "supported",
            "dominant_violation_relief_count": 4,
            "entry_evidence_level": "trusted",
            "evidence_level": "trusted",
            "feasible_entry_count": 3,
            "feasible_preservation_count": 8,
            "feasible_regression_count": 1,
            "operator_family": "primitive_sink",
            "pareto_contribution_count": 2,
            "post_feasible_role": "trusted_preserve",
            "recent_expand_feasible_preservation_count": 4,
            "recent_expand_feasible_regression_count": 1,
            "recent_expand_frontier_add_count": 2,
            "role": "sink_resize",
            "route_cooldown_active": False,
        }
    )

    payload = prompt_projection.build_prompt_projection(
        state,
        candidate_operator_ids=("native_sbx_pm", "repair_sink_budget"),
        original_candidate_operator_ids=("native_sbx_pm", "repair_sink_budget"),
        policy_snapshot=_policy_snapshot("post_feasible_expand"),
        guardrail=None,
    )

    row = payload["prompt_panels"]["operator_panel"]["repair_sink_budget"]
    assert row == {
        "applicability": "medium",
        "entry_fit": "supported",
        "preserve_fit": "trusted",
        "expand_fit": "trusted",
        "frontier_evidence": "positive",
        "expected_peak_effect": "neutral",
        "expected_gradient_effect": "neutral",
        "expected_feasibility_risk": "low",
        "recent_regression_risk": "low",
        "role": "sink_resize",
        "post_feasible_role": "trusted_preserve",
    }
```

Add this test below the existing retrieval compaction test:

```python
def test_post_feasible_projection_omits_false_and_count_only_annotation_noise() -> None:
    prompt_projection = _prompt_projection_module()
    state = _post_feasible_state()
    policy_snapshot = PolicySnapshot(
        phase="post_feasible_expand",
        allowed_operator_ids=("native_sbx_pm", "repair_sink_budget"),
        suppressed_operator_ids=(),
        reset_active=False,
        reason_codes=(),
        candidate_annotations={
            "repair_sink_budget": {
                "operator_family": "primitive_sink",
                "role": "sink_resize",
                "evidence_level": "trusted",
                "post_feasible_role": "trusted_preserve",
                "feasible_entry_count": 1,
                "feasible_preservation_count": 3,
                "feasible_regression_count": 0,
                "pareto_contribution_count": 1,
                "route_budget_state": {"cooldown_active": False},
                "expand_budget_state": {
                    "expand_budget_status": "preferred",
                    "recent_expand_frontier_add_count": 2,
                    "recent_expand_feasible_preservation_count": 2,
                    "recent_expand_feasible_regression_count": 0,
                },
            }
        },
    )

    payload = prompt_projection.build_prompt_projection(
        state,
        candidate_operator_ids=("native_sbx_pm", "repair_sink_budget"),
        original_candidate_operator_ids=("native_sbx_pm", "repair_sink_budget"),
        policy_snapshot=policy_snapshot,
        guardrail=None,
    )

    row = payload["prompt_panels"]["operator_panel"]["repair_sink_budget"]
    assert row["expand_budget_status"] == "preferred"
    assert row["role"] == "sink_resize"
    assert row["post_feasible_role"] == "trusted_preserve"
    assert "route_cooldown_active" not in row
    assert "feasible_entry_count" not in row
    assert "feasible_preservation_count" not in row
    assert "feasible_regression_count" not in row
    assert "pareto_contribution_count" not in row
    assert "recent_expand_frontier_add_count" not in row
    assert "recent_expand_feasible_preservation_count" not in row
    assert "recent_expand_feasible_regression_count" not in row
```

- [ ] **Step 2: Run the focused prompt projection test and verify it fails**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_llm_prompt_projection.py
```

Expected: FAIL because projection still includes count-heavy annotation fields and `route_cooldown_active: False`.

- [ ] **Step 3: Define compact post-feasible row keys**

In `optimizers/operator_pool/prompt_projection.py`, replace `_OPERATOR_PANEL_PROMPT_KEYS` with two phase-specific key sets:

```python
_PREFEASIBLE_OPERATOR_PANEL_PROMPT_KEYS = frozenset(
    {
        "applicability",
        "dominant_violation_relief",
        "entry_fit",
        "expand_fit",
        "expected_feasibility_risk",
        "expected_gradient_effect",
        "expected_peak_effect",
        "preserve_fit",
        "recent_regression_risk",
    }
)
_POST_FEASIBLE_OPERATOR_PANEL_PROMPT_KEYS = frozenset(
    {
        "applicability",
        "entry_fit",
        "preserve_fit",
        "expand_fit",
        "frontier_evidence",
        "expected_peak_effect",
        "expected_gradient_effect",
        "expected_feasibility_risk",
        "recent_regression_risk",
        "role",
        "post_feasible_role",
        "expand_budget_status",
    }
)
```

Keep `_CANDIDATE_ANNOTATION_PROMPT_KEYS` for now; the next step filters the projected annotations by phase.

- [ ] **Step 4: Make operator row projection phase-aware**

Change the call at `optimizers/operator_pool/prompt_projection.py:217` from:

```python
            projected_summary = _project_operator_panel_row(summary)
```

to:

```python
            projected_summary = _project_operator_panel_row(
                summary,
                post_feasible_active=post_feasible_active,
            )
```

Replace `_project_operator_panel_row()` with:

```python
def _project_operator_panel_row(
    summary: Mapping[str, Any],
    *,
    post_feasible_active: bool,
) -> dict[str, Any]:
    keys = (
        _POST_FEASIBLE_OPERATOR_PANEL_PROMPT_KEYS
        if post_feasible_active
        else _PREFEASIBLE_OPERATOR_PANEL_PROMPT_KEYS
    )
    return {
        key: summary[key]
        for key in keys
        if key in summary
    }
```

- [ ] **Step 5: Filter annotation noise after merging**

In `_project_candidate_annotation()`, make post-feasible annotations keep only decision-role/status fields and omit false cooldowns/count-only evidence:

```python
    if post_feasible_active:
        projected.pop("prefeasible_role", None)
        for key in (
            "operator_family",
            "evidence_level",
            "entry_evidence_level",
            "feasible_entry_count",
            "feasible_preservation_count",
            "feasible_regression_count",
            "pareto_contribution_count",
            "dominant_violation_relief_count",
            "recent_expand_frontier_add_count",
            "recent_expand_feasible_preservation_count",
            "recent_expand_feasible_regression_count",
        ):
            projected.pop(key, None)
        if projected.get("route_cooldown_active") is False:
            projected.pop("route_cooldown_active", None)
        return projected
```

Keep the existing pre-feasible branch:

```python
    projected.pop("post_feasible_role", None)
    return projected
```

- [ ] **Step 6: Run the focused prompt projection test and verify it passes**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_llm_prompt_projection.py
```

Expected: PASS.

- [ ] **Step 7: Commit the prompt projection compaction**

Run:

```bash
git add optimizers/operator_pool/prompt_projection.py tests/optimizers/test_llm_prompt_projection.py
git commit -m "refactor: compact llm operator prompt projection"
```

---

### Task 3: Shorten the static system prompt and add request-size diagnostics

**Files:**
- Modify: `optimizers/operator_pool/llm_controller.py:604-680,727-795`
- Test: `tests/optimizers/test_llm_controller.py`

- [ ] **Step 1: Add failing tests for system prompt size and trace diagnostics**

Append these tests to `tests/optimizers/test_llm_controller.py`:

```python
def test_llm_system_prompt_stays_compact_for_primitive_pool() -> None:
    controller = LLMOperatorController(
        controller_parameters={
            "provider": "openai-compatible",
            "capability_profile": "chat_compatible_json",
            "performance_profile": "balanced",
            "model": "test-model",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 128,
        },
        client=object(),
    )
    state = ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=5,
        evaluation_index=51,
        parent_count=2,
        vector_size=32,
        metadata={"search_phase": "feasible_refine"},
    )
    policy_snapshot = PolicySnapshot(
        phase="post_feasible_preserve",
        allowed_operator_ids=(
            "vector_sbx_pm",
            "component_jitter_1",
            "anchored_component_jitter",
            "component_relocate_1",
            "component_swap_2",
            "sink_shift",
            "sink_resize",
            "component_block_translate_2_4",
            "component_subspace_sbx",
        ),
        suppressed_operator_ids=(),
        reset_active=False,
        reason_codes=(),
        candidate_annotations={},
    )

    prompt = controller._build_system_prompt(
        state,
        policy_snapshot.allowed_operator_ids,
        policy_snapshot=policy_snapshot,
        guardrail=None,
    )

    assert len(prompt) < 1800
    assert "Intent menu:" not in prompt
    assert "Candidate operator intents:" not in prompt
    assert "metadata.intent_panel" in prompt
    assert "metadata.decision_axes" in prompt


def test_llm_request_trace_records_prompt_size_fields(tmp_path: Path) -> None:
    controller_trace_path = tmp_path / "controller_trace.jsonl"
    request_trace_path = tmp_path / "llm_request_trace.jsonl"
    response_trace_path = tmp_path / "llm_response_trace.jsonl"
    prompt_store = PromptStore(tmp_path / "prompts")
    controller = LLMOperatorController(
        controller_parameters={
            "provider": "openai-compatible",
            "capability_profile": "chat_compatible_json",
            "performance_profile": "balanced",
            "model": "test-model",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 128,
        },
        client=object(),
    )
    controller.configure_trace_outputs(
        controller_trace_path=controller_trace_path,
        llm_request_trace_path=request_trace_path,
        llm_response_trace_path=response_trace_path,
        prompt_store=prompt_store,
    )

    controller._emit_controller_trace(
        decision_id="g001-e0001-d00",
        phase="post_feasible_preserve",
        operator_selected="component_jitter_1",
        operator_pool_snapshot=["component_jitter_1"],
        input_state_digest="abc123",
        system_prompt="system text",
        user_prompt="user text",
        response_body='{"selected_operator_id":"component_jitter_1"}',
        rationale="",
        fallback_used=False,
        latency_ms=12.0,
        http_status=200,
        retries=0,
        tokens={},
        finish_reason="stop",
        request_surface={"generation_index": 1},
        response_surface={"fallback_used": False},
    )

    request_row = json.loads(request_trace_path.read_text(encoding="utf-8").splitlines()[0])
    assert request_row["prompt_size"]["system_chars"] == len("system text")
    assert request_row["prompt_size"]["user_chars"] == len("user text")
    assert request_row["prompt_size"]["total_chars"] == len("system text") + len("user text")
```

If `Path`, `json`, `ControllerState`, `PolicySnapshot`, or `PromptStore` are not imported at the top of `tests/optimizers/test_llm_controller.py`, add the exact imports:

```python
import json
from pathlib import Path
from optimizers.operator_pool.policy_kernel import PolicySnapshot
from optimizers.operator_pool.state import ControllerState
from optimizers.traces.prompt_store import PromptStore
```

Do not duplicate imports that already exist.

- [ ] **Step 2: Run the focused controller test and verify it fails**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_llm_controller.py
```

Expected: FAIL because the current system prompt includes the full intent menu/candidate intent map and request trace rows do not include `prompt_size`.

- [ ] **Step 3: Shorten `_build_system_prompt()`**

Replace the large base string at `optimizers/operator_pool/llm_controller.py:740-760` with this compact instruction block:

```python
        prompt = (
            "You are an operator-selection controller for constrained multiobjective thermal optimization. "
            "Return one operator from candidate_operator_ids; do not emit raw design vectors. "
            "Use metadata.decision_axes as the primary decision surface, metadata.prompt_panels.operator_panel "
            "as candidate evidence, and metadata.intent_panel only to interpret route intent. "
            "Prefer operators that match the current phase, objective balance, preserve/frontier pressure, "
            "applicability, expected effects, retrieval evidence, and regression risk. "
            "Policy guidance is soft unless the candidate list itself changes. "
            "Keep native_baseline as a valid fair-pool anchor when it is comparably applicable. "
            "Use sink-budget operators only when sink span, sink budget, or sink alignment is the active bottleneck."
        )
```

Keep the later calls that append phase policy, objective balance, generation-local, route-family, and guardrail guidance. Do not append `intent_panel` or `operator_intent_map` to the system prompt.

Remove these local variables if they become unused:

```python
        intent_panel = self._build_intent_panel(candidate_operator_ids)
        operator_intent_map = {
            str(operator_id): _OPERATOR_INTENTS.get(str(operator_id), "native_baseline")
            for operator_id in candidate_operator_ids
        }
```

- [ ] **Step 4: Add prompt size diagnostics to request trace rows**

In `_emit_controller_trace()`, before `append_jsonl(self._llm_request_trace_path, ...)`, compute:

```python
        prompt_size = {
            "system_chars": len(system_prompt),
            "user_chars": len(user_prompt),
            "total_chars": len(system_prompt) + len(user_prompt),
        }
```

Then add this key to the request trace row:

```python
                "prompt_size": prompt_size,
```

The surrounding request row should look like:

```python
        append_jsonl(
            self._llm_request_trace_path,
            {
                "decision_id": decision_id,
                "prompt_ref": prompt_ref,
                "model": self.config.model,
                "http_status": http_status,
                "retries": int(retries),
                "latency_ms": float(latency_ms),
                "prompt_size": prompt_size,
                **({} if request_surface is None else dict(request_surface)),
            },
        )
```

- [ ] **Step 5: Run the focused controller test and verify it passes**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_llm_controller.py
```

Expected: PASS.

- [ ] **Step 6: Commit the system prompt and diagnostics change**

Run:

```bash
git add optimizers/operator_pool/llm_controller.py tests/optimizers/test_llm_controller.py
git commit -m "refactor: shorten llm operator prompt surface"
```

---

### Task 4: Update S5/S6 short-output budgets without masking concurrency failures

**Files:**
- Modify: `scenarios/optimization/s5_aggressive15_llm.yaml:164-169`
- Modify: `scenarios/optimization/s6_aggressive20_llm.yaml:205-209`
- Test: `tests/optimizers/test_s5_aggressive15_specs.py`
- Test: `tests/optimizers/test_s6_aggressive20_specs.py`

- [ ] **Step 1: Add failing spec tests for the small-scenario LLM output budget**

Append this test to `tests/optimizers/test_s5_aggressive15_specs.py`:

```python
def test_s5_llm_controller_uses_short_but_safe_output_budget() -> None:
    llm = load_optimization_spec(LLM).to_dict()
    params = llm["operator_control"]["controller_parameters"]

    assert params["max_output_tokens"] == 128
    assert params["retry"]["timeout_seconds"] == 35
    assert params["retry"]["max_attempts"] == 2
```

Append this test to `tests/optimizers/test_s6_aggressive20_specs.py`:

```python
def test_s6_llm_controller_uses_short_but_safe_output_budget() -> None:
    llm = load_optimization_spec(LLM).to_dict()
    params = llm["operator_control"]["controller_parameters"]

    assert params["max_output_tokens"] == 128
    assert params["retry"]["timeout_seconds"] == 35
    assert params["retry"]["max_attempts"] == 2
```

- [ ] **Step 2: Run the focused S5/S6 spec tests and verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_s5_aggressive15_specs.py tests/optimizers/test_s6_aggressive20_specs.py
```

Expected: FAIL because S5 and S6 still use `max_output_tokens: 72`.

- [ ] **Step 3: Raise S5/S6 max output tokens to 128 only**

In `scenarios/optimization/s5_aggressive15_llm.yaml`, change:

```yaml
    max_output_tokens: 72
```

to:

```yaml
    max_output_tokens: 128
```

In `scenarios/optimization/s6_aggressive20_llm.yaml`, change:

```yaml
    max_output_tokens: 72
```

to:

```yaml
    max_output_tokens: 128
```

Do not change `timeout_seconds` in this task. Keeping 35 seconds preserves the ability to diagnose external concurrency pressure separately from protocol truncation.

- [ ] **Step 4: Run the focused S5/S6 spec tests and verify they pass**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_s5_aggressive15_specs.py tests/optimizers/test_s6_aggressive20_specs.py
```

Expected: PASS.

- [ ] **Step 5: Commit the spec budget change**

Run:

```bash
git add scenarios/optimization/s5_aggressive15_llm.yaml scenarios/optimization/s6_aggressive20_llm.yaml tests/optimizers/test_s5_aggressive15_specs.py tests/optimizers/test_s6_aggressive20_specs.py
git commit -m "fix: use safe short llm output budgets for aggressive scenarios"
```

---

### Task 5: Add a deterministic prompt budget regression test

**Files:**
- Modify: `tests/optimizers/test_llm_controller.py`

- [ ] **Step 1: Add a failing end-to-end prompt budget test using synthetic S5-like panels**

Append this test to `tests/optimizers/test_llm_controller.py`:

```python
def test_llm_user_prompt_budget_for_s5_like_primitive_pool() -> None:
    candidate_ids = (
        "vector_sbx_pm",
        "component_jitter_1",
        "anchored_component_jitter",
        "component_relocate_1",
        "component_swap_2",
        "sink_shift",
        "sink_resize",
        "component_block_translate_2_4",
        "component_subspace_sbx",
    )
    operator_panel = {
        operator_id: {
            "applicability": "high" if operator_id in {"component_jitter_1", "sink_shift"} else "medium",
            "entry_fit": "supported",
            "preserve_fit": "trusted" if operator_id in {"component_jitter_1", "sink_shift"} else "supported",
            "expand_fit": "trusted" if operator_id in {"component_swap_2", "component_block_translate_2_4"} else "supported",
            "frontier_evidence": "positive" if operator_id in {"component_jitter_1", "component_swap_2"} else "limited",
            "expected_peak_effect": "improve" if operator_id in {"component_jitter_1", "sink_shift"} else "neutral",
            "expected_gradient_effect": "improve" if operator_id in {"anchored_component_jitter", "component_swap_2"} else "neutral",
            "expected_feasibility_risk": "low" if operator_id in {"component_jitter_1", "sink_shift"} else "high",
            "recent_regression_risk": "low" if operator_id in {"component_jitter_1", "sink_shift"} else "high",
            "role": "native_baseline" if operator_id == "vector_sbx_pm" else "primitive_route",
            "post_feasible_role": "trusted_preserve" if operator_id in {"component_jitter_1", "sink_shift"} else "fragile_preserve",
        }
        for operator_id in candidate_ids
    }
    state = ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=5,
        evaluation_index=51,
        parent_count=2,
        vector_size=32,
        metadata={
            "search_phase": "feasible_refine",
            "prompt_panels": {
                "run_panel": {
                    "evaluations_used": 50,
                    "evaluations_remaining": 1,
                    "feasible_rate": 0.25,
                    "first_feasible_eval": 4,
                    "peak_temperature": 331.78,
                    "temperature_gradient_rms": 24.14,
                    "sink_span": 0.35,
                    "sink_budget_utilization": 1.0,
                    "pareto_size": 2,
                },
                "regime_panel": {
                    "phase": "post_feasible_preserve",
                    "dominant_violation_family": "layout_spacing",
                    "frontier_pressure": "medium",
                    "preservation_pressure": "high",
                    "objective_balance": {
                        "balance_pressure": "medium",
                        "preferred_effect": "balanced",
                        "stagnant_objectives": ["temperature_max", "gradient_rms"],
                        "improving_objectives": [],
                    },
                    "sink_budget_utilization": 1.0,
                    "recover_exit_ready": True,
                    "recover_release_ready": True,
                },
                "parent_panel": {
                    "closest_to_feasible_parent": {"evaluation_index": 50, "feasible": True, "total_violation": 0.0},
                    "strongest_feasible_parent": {"evaluation_index": 50, "feasible": True, "total_violation": 0.0},
                },
                "spatial_panel": {
                    "hotspot_inside_sink_window": True,
                    "hotspot_to_sink_offset": -0.0889,
                    "hottest_cluster_compactness": 0.1089,
                    "nearest_neighbor_gap_min": 0.1013,
                    "sink_budget_bucket": "full_sink",
                },
                "retrieval_panel": {
                    "query_regime": {
                        "phase": "post_feasible_preserve",
                        "dominant_violation_family": "layout_spacing",
                        "sink_budget_bucket": "full_sink",
                    },
                    "positive_match_families": ["stable_local", "structured_subspace"],
                    "negative_match_families": ["structured_block"],
                    "visibility_floor_families": ["stable_global", "stable_local"],
                    "positive_matches": [
                        {
                            "operator_id": "sink_shift",
                            "route_family": "stable_local",
                            "similarity_score": 4,
                            "evidence": {"frontier_add_count": 0, "feasible_regression_count": 0, "feasible_preservation_count": 2},
                        }
                    ],
                    "negative_matches": [
                        {
                            "operator_id": "component_subspace_sbx",
                            "route_family": "structured_subspace",
                            "similarity_score": 4,
                            "evidence": {"frontier_add_count": 0, "feasible_regression_count": 0, "feasible_preservation_count": 2},
                        }
                    ],
                },
                "operator_panel": operator_panel,
                "generation_panel": {
                    "accepted_count": 9,
                    "target_offsprings": 10,
                    "accepted_share": 0.9,
                    "dominant_operator_id": "component_relocate_1",
                    "dominant_operator_count": 2,
                    "dominant_operator_share": 0.22,
                    "dominant_operator_streak": 1,
                    "route_family_counts": {"stable_local": 3, "structured_block": 2},
                },
            },
        },
    )
    policy_snapshot = PolicySnapshot(
        phase="post_feasible_preserve",
        allowed_operator_ids=candidate_ids,
        suppressed_operator_ids=(),
        reset_active=False,
        reason_codes=(),
        candidate_annotations={},
    )

    metadata = LLMOperatorController._build_prompt_metadata(
        state,
        candidate_ids,
        original_candidate_operator_ids=candidate_ids,
        policy_snapshot=policy_snapshot,
        guardrail=None,
    )
    user_prompt = LLMOperatorController._serialize_user_prompt(state, candidate_ids, metadata=metadata)

    assert len(user_prompt) < 9000
    assert len(json.dumps(metadata["prompt_panels"]["operator_panel"], sort_keys=True)) < 4500
```

- [ ] **Step 2: Run the focused controller test and verify it passes after Tasks 2-3**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_llm_controller.py
```

Expected: PASS if the compact projection and shortened system prompt are already implemented. If this fails only because imports are missing, add the exact missing imports at the top of `tests/optimizers/test_llm_controller.py` without changing production code.

- [ ] **Step 3: Commit the prompt budget regression test**

Run:

```bash
git add tests/optimizers/test_llm_controller.py
git commit -m "test: guard llm operator prompt budget"
```

---

### Task 6: Verify focused behavior without rerunning live LLM by default

**Files:**
- No source modifications expected.

- [ ] **Step 1: Run the focused tests touched by this plan**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_llm_client.py tests/optimizers/test_llm_prompt_projection.py tests/optimizers/test_llm_controller.py tests/optimizers/test_s5_aggressive15_specs.py tests/optimizers/test_s6_aggressive20_specs.py
```

Expected: PASS.

- [ ] **Step 2: Inspect git diff for accidental generated-artifact edits**

Run:

```bash
git diff --stat
```

Expected: changed files are limited to `llm/openai_compatible/`, `optimizers/operator_pool/`, `scenarios/optimization/s5_aggressive15_llm.yaml`, `scenarios/optimization/s6_aggressive20_llm.yaml`, and the listed focused tests. No `scenario_runs/` files should appear.

- [ ] **Step 3: Do not claim live fallback is fixed unless a fresh isolated live run is executed**

Record this in the final implementation summary:

```text
Focused unit/spec tests verify prompt compaction and response contract behavior. They do not prove live provider timeout behavior, because the observed fallback may also be caused by concurrent live processes saturating provider/network capacity.
```

If the user explicitly asks for a live rerun, run only one isolated S5 LLM smoke with low workers and no parallel live LLM jobs. Use a new run root under `scenario_runs/s5_aggressive15/` and do not compare scientific outcomes until `render-assets` is completed.

- [ ] **Step 4: Final commit if Task 6 found only test/reporting changes**

If Step 1 or Step 2 required small fixes, commit them:

```bash
git add <exact files changed>
git commit -m "test: verify llm prompt compaction"
```

If no files changed after Step 1 and Step 2, do not create an empty commit.

---

## Self-Review

- Spec coverage: The plan covers the four distinct issues identified from traces: prompt size, response JSON truncation, trace diagnostics, and S5/S6 short-output config. It explicitly treats concurrent live process saturation as a separate hypothesis and does not claim live fallback is fixed by unit tests.
- Placeholder scan: No `TBD`, `TODO`, or vague implementation steps remain. Each code-changing step includes concrete code snippets and exact commands.
- Type consistency: The plan uses existing names from the codebase: `build_prompt_projection`, `PolicySnapshot`, `ControllerState`, `LLMOperatorController`, `PromptStore`, `OpenAICompatibleClient`, and `build_operator_decision_schema`. Response fields remain `selected_operator_id`, `phase`, `rationale`, and `selected_intent`.
