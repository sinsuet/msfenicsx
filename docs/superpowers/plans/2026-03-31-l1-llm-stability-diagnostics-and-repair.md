# L1 LLM Stability Diagnostics And Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a paper-facing diagnostic path that separates transport instability from search behavior, then tighten the existing NSGA-II union-LLM controller state so fallback-heavy history does not poison later LLM decisions.

**Architecture:** Keep the active `NSGA-II union-LLM` runtime unchanged at the algorithm-contract level, but add one diagnostics utility that replays recorded LLM controller requests against the same OpenAI-compatible boundary and one compact reflection path that feeds the controller summary statistics instead of verbose recent history. Preserve the same action registry, repair path, evaluation path, budget framing, and survival logic.

**Tech Stack:** Python 3.12, pytest, argparse, JSON/JSONL artifacts, existing `openai` SDK boundary, optimizer trace sidecars.

---

## Status Update - 2026-03-31

- The transport-diagnostics and replay portions of this plan are now implemented, and the current live route is transport-stable rather than fallback-dominated.
- Subsequent multi-seed validation showed that the remaining instability is a controller-policy problem concentrated in the pre-feasible search stage, not primarily a provider/schema problem.
- The next repair direction should therefore not be read as "add special handling for the current thermal scenario." It should be read as "extract a reusable controller-policy kernel" that is phase-aware, evidence-aware, family-aware, and progress-aware while keeping benchmark-specific domain summaries as optional context only.
- Future repairs under this plan should avoid hardcoded operator-name, scenario-name, seed-specific, or backbone-specific exceptions unless they are explicitly marked as temporary diagnostics.

### Task 1: Add failing tests for compact reflection and fallback-separated history

**Files:**
- Modify: `tests/optimizers/test_llm_controller_state.py`
- Modify: `optimizers/operator_pool/reflection.py`
- Modify: `optimizers/operator_pool/state_builder.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_build_controller_state_compacts_recent_history_and_exposes_recent_counts():
    ...


def test_summarize_operator_history_separates_fallback_and_llm_valid_counts():
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/optimizers/test_llm_controller_state.py -v`
Expected: FAIL because the new compact fields and separated counters do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
def summarize_operator_history(...):
    return {
        operator_id: {
            "selection_count": ...,
            "llm_valid_selection_count": ...,
            "fallback_selection_count": ...,
            "recent_selection_count": ...,
        }
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/optimizers/test_llm_controller_state.py -v`
Expected: PASS

### Task 2: Add failing tests for trace replay diagnostics

**Files:**
- Create: `llm/openai_compatible/replay.py`
- Modify: `tests/optimizers/test_llm_client.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`
- Modify: `optimizers/cli.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_replay_trace_rows_returns_validity_summary(...):
    ...


def test_optimizer_cli_replay_llm_trace_writes_summary_artifact(...):
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/optimizers/test_llm_client.py tests/optimizers/test_optimizer_cli.py -v`
Expected: FAIL because replay helpers and CLI wiring do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
def replay_request_trace(...):
    ...
    return {"rows": [...], "aggregate": {...}}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/optimizers/test_llm_client.py tests/optimizers/test_optimizer_cli.py -v`
Expected: PASS

### Task 3: Tighten the controller prompt/state payload without changing the union contract

**Files:**
- Modify: `optimizers/operator_pool/llm_controller.py`
- Modify: `optimizers/operator_pool/state_builder.py`
- Modify: `tests/optimizers/test_llm_controller.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_llm_controller_user_prompt_uses_compact_state_fields():
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/optimizers/test_llm_controller.py -v`
Expected: FAIL because the prompt still forwards the larger raw metadata payload.

- [ ] **Step 3: Write minimal implementation**

```python
payload = {
    "metadata": {
        "search_phase": ...,
        "candidate_operator_ids": ...,
        "recent_operator_counts": ...,
        "operator_summary": ...,
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/optimizers/test_llm_controller.py -v`
Expected: PASS

### Task 4: Run focused verification and one live diagnostic replay

**Files:**
- No source edits required

- [ ] **Step 1: Run the focused optimizer verification suite**

Run: `pytest tests/optimizers/test_llm_client.py tests/optimizers/test_llm_controller.py tests/optimizers/test_llm_controller_state.py tests/optimizers/test_optimizer_cli.py tests/optimizers/test_optimizer_io.py -v`
Expected: PASS

- [ ] **Step 2: Run one live replay diagnostic against an existing request trace**

Run: `python -m optimizers.cli replay-llm-trace --request-trace <trace> --output <summary>`
Expected: JSON summary with valid-rate, retry-rate, fallback-equivalent rate, and latency.

- [ ] **Step 3: Report the diagnosis and next live-run recommendation**

Summarize whether instability is dominated by:
- transport/schema compliance
- prompt/state overload
- controller search utility
