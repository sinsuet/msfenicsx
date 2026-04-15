# S1 Typical LLM Controller Adaptation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adapt the `s1_typical` `nsga2_llm` route so it remains a controller-only comparison against `union` while presenting the `LLM` with clearer phase-aware state and prompt guidance, then run one real `llm` smoke validation.

**Architecture:** Keep the current matched experiment contract intact: the `llm` route must continue to share the same problem, operator pool, budget, repair, solve, and survival semantics as `union`. Implement the adaptation entirely in the controller layer by wiring spec-declared runtime controls into execution, restructuring prompt-facing state into compact phase-aware panels, and tightening the `LLM` system/user prompt around `prefeasible_convert`, `post_feasible_preserve`, and `post_feasible_expand` priorities.

**Tech Stack:** Python 3.12, pytest, pymoo NSGA-II union adapter, existing `optimizers.operator_pool` controller stack, OpenAI-compatible client in `llm/openai_compatible/`

---

### Task 1: Lock the Matched Comparison Boundary and Wire `memory.recent_window`

**Files:**
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_optimizer_io.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_operator_pool_adapters.py`
- Modify: `/home/hymn/msfenicsx/optimizers/adapters/genetic_family.py`

- [ ] **Step 1: Add a failing spec-level invariant test for the `llm` route**

```python
def test_llm_spec_stays_controller_only_against_union() -> None:
    union_spec = load_optimization_spec("scenarios/optimization/s1_typical_union.yaml")
    llm_spec = load_optimization_spec("scenarios/optimization/s1_typical_llm.yaml")

    assert union_spec.algorithm["profile_path"] == llm_spec.algorithm["profile_path"]
    assert union_spec.algorithm["population_size"] == llm_spec.algorithm["population_size"]
    assert union_spec.algorithm["num_generations"] == llm_spec.algorithm["num_generations"]
    assert union_spec.operator_control["operator_pool"] == llm_spec.operator_control["operator_pool"]
    assert llm_spec.operator_control["controller_parameters"]["memory"]["recent_window"] > 0
    assert llm_spec.operator_control["controller_parameters"]["retry"]["timeout_seconds"] > 0
```

- [ ] **Step 2: Add a failing adapter test for configured recent-memory window plumbing**

```python
def test_genetic_union_llm_uses_configured_recent_window(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, int] = {}

    def _fake_build_controller_state(*args, **kwargs):
        captured["recent_window"] = kwargs["recent_window"]
        return _minimal_controller_state()

    monkeypatch.setattr("optimizers.adapters.genetic_family.build_controller_state", _fake_build_controller_state)
    ...
    assert captured["recent_window"] == 12
```

- [ ] **Step 3: Run the new red tests and confirm they fail for the right reason**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_optimizer_io.py::test_llm_spec_stays_controller_only_against_union \
  tests/optimizers/test_operator_pool_adapters.py::test_genetic_union_llm_uses_configured_recent_window \
  -v
```

Expected:

- the spec invariant test should fail if the current assertions are not yet present
- the adapter test should fail because `recent_window` is still hard-coded to `32`

- [ ] **Step 4: Implement `recent_window` resolution in the genetic union adapter**

```python
memory_cfg = controller_parameters.get("memory", {}) if isinstance(controller_parameters, dict) else {}
self.recent_window = max(1, int(memory_cfg.get("recent_window", 32)))

state = build_controller_state(
    ...,
    recent_window=self.recent_window,
)
```

- [ ] **Step 5: Keep the `llm` route matched to `union` and avoid profile drift**

Implementation notes:

- do not add a separate `llm` profile
- do not change `population_size`, `num_generations`, or `algorithm.profile_path` in `s1_typical_llm.yaml`
- if the spec test needs more assertions, add them in `test_optimizer_io.py`, not in production code

- [ ] **Step 6: Re-run the focused tests and confirm green**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_optimizer_io.py::test_llm_spec_stays_controller_only_against_union \
  tests/optimizers/test_operator_pool_adapters.py::test_genetic_union_llm_uses_configured_recent_window \
  -v
```

Expected: `2 passed`

- [ ] **Step 7: Commit the boundary + wiring changes**

```bash
git add \
  tests/optimizers/test_optimizer_io.py \
  tests/optimizers/test_operator_pool_adapters.py \
  optimizers/adapters/genetic_family.py
git commit -m "feat: wire llm controller memory window into union adapter"
```

### Task 2: Build Compact Phase-Aware Prompt Panels from Run/Regime/Parent/Operator Evidence

**Files:**
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller_state.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/domain_state.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/reflection.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/state_builder.py`

- [ ] **Step 1: Add a failing controller-state test for compact phase-aware panels**

```python
def test_build_controller_state_emits_phase_aware_prompt_panels() -> None:
    state = build_controller_state(...)

    assert state.metadata["prompt_panels"]["run_panel"]["first_feasible_eval"] == 3
    assert state.metadata["prompt_panels"]["regime_panel"]["phase"] == "prefeasible_convert"
    assert "closest_to_feasible_parent" in state.metadata["prompt_panels"]["parent_panel"]
    assert "operator_panel" in state.metadata["prompt_panels"]
```

- [ ] **Step 2: Add a failing operator-evidence test for phase-facing fit/risk summaries**

```python
def test_operator_summary_exposes_entry_preserve_expand_fit_fields() -> None:
    state = build_controller_state(...)
    row = state.metadata["prompt_panels"]["operator_panel"]["slide_sink"]

    assert set(["entry_fit", "preserve_fit", "expand_fit", "recent_regression_risk"]).issubset(row)
```

- [ ] **Step 3: Run the red tests and confirm the missing-panel failure**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller_state.py::test_build_controller_state_emits_phase_aware_prompt_panels \
  tests/optimizers/test_llm_controller_state.py::test_operator_summary_exposes_entry_preserve_expand_fit_fields \
  -v
```

Expected:

- tests fail because `prompt_panels` and phase-facing operator fit/risk fields do not exist yet

- [ ] **Step 4: Extend domain summaries with clearer phase pressure fields**

Implementation sketch:

```python
regime_panel = {
    "phase": phase,
    "dominant_violation_family": ...,
    "dominant_violation_persistence_count": ...,
    "sink_budget_utilization": ...,
    "entry_pressure": ...,
    "preservation_pressure": ...,
    "frontier_pressure": ...,
}
```

- [ ] **Step 5: Extend reflection summaries with phase-facing operator evidence**

Implementation sketch:

```python
operator_panel[operator_id] = {
    "entry_fit": "trusted" | "supported" | "weak",
    "preserve_fit": ...,
    "expand_fit": ...,
    "recent_regression_risk": "high" | "medium" | "low",
    "frontier_evidence": ...,
    "dominant_violation_relief": ...,
}
```

- [ ] **Step 6: Assemble compact prompt panels in `state_builder.py`**

Implementation notes:

- keep existing `run_state`, `parent_state`, `archive_state`, `domain_regime`, and `progress_state`
- add a derived `prompt_panels` block
- do not dump large low-signal raw history into the new block

- [ ] **Step 7: Re-run the focused state tests and confirm green**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller_state.py -v
```

Expected: all `test_llm_controller_state.py` tests pass

- [ ] **Step 8: Commit the state-panel changes**

```bash
git add \
  tests/optimizers/test_llm_controller_state.py \
  optimizers/operator_pool/domain_state.py \
  optimizers/operator_pool/reflection.py \
  optimizers/operator_pool/state_builder.py
git commit -m "feat: add phase-aware llm controller state panels"
```

### Task 3: Rewrite Prompt Projection and Controller Guidance Around Entry / Preserve / Expand Priorities

**Files:**
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_controller.py`
- Modify: `/home/hymn/msfenicsx/tests/optimizers/test_llm_policy_kernel.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/prompt_projection.py`
- Modify: `/home/hymn/msfenicsx/optimizers/operator_pool/llm_controller.py`

- [ ] **Step 1: Add a failing prompt-projection test for the new panelized payload**

```python
def test_llm_controller_user_payload_uses_prompt_panels_not_raw_generic_metadata() -> None:
    decision = controller.select_decision(_domain_grounded_state(), ...)
    payload = json.loads(client.last_kwargs["user_prompt"])

    assert "prompt_panels" in payload["metadata"]
    assert "run_panel" in payload["metadata"]["prompt_panels"]
    assert "problem_history" not in payload["metadata"]
```

- [ ] **Step 2: Add a failing system-prompt test for explicit phase-ordering guidance**

```python
def test_llm_system_prompt_prioritizes_entry_before_pareto_in_prefeasible_convert() -> None:
    ...
    system_prompt = str(client.last_kwargs["system_prompt"])
    assert "first feasible conversion" in system_prompt
    assert "before frontier expansion" in system_prompt
```

- [ ] **Step 3: Run the red prompt/controller tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_llm_policy_kernel.py \
  -v
```

Expected:

- prompt/controller assertions fail because the current payload and wording are still too generic

- [ ] **Step 4: Rework `prompt_projection.py` to emit the compact phase-aware panel structure**

Implementation sketch:

```python
metadata["prompt_panels"] = {
    "run_panel": ...,
    "regime_panel": ...,
    "parent_panel": ...,
    "operator_panel": ...,
}
```

- [ ] **Step 5: Tighten `llm_controller.py` system prompt around ordered phase priorities**

Implementation notes:

- `prefeasible_convert`: first cross into feasibility, then avoid unstable regressions
- `post_feasible_preserve`: first keep feasibility stable
- `post_feasible_expand`: only then favor frontier growth / Pareto novelty
- keep recent-dominance guardrails and fallback semantics intact

- [ ] **Step 6: Keep the prompt controller-only and avoid route drift**

Implementation notes:

- do not add operator ids outside the fixed registry
- do not ask the model for raw vectors, parameter values, or direct geometry edits
- keep the output schema as one selected operator id plus brief rationale

- [ ] **Step 7: Re-run the prompt/controller suite and confirm green**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_optimizer_cli.py::test_analyze_controller_trace_reports_near_feasible_conversion_metrics \
  -v
```

Expected: all selected tests pass

- [ ] **Step 8: Commit the prompt/controller changes**

```bash
git add \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_llm_policy_kernel.py \
  optimizers/operator_pool/prompt_projection.py \
  optimizers/operator_pool/llm_controller.py
git commit -m "feat: refocus llm prompts on phase-aware controller goals"
```

### Task 4: Run Full Verification and a Real `s1_typical` LLM Smoke Validation

**Files:**
- Read/Verify: `/home/hymn/msfenicsx/scenarios/optimization/s1_typical_llm.yaml`
- Read/Verify: `/home/hymn/msfenicsx/scenario_runs/s1_typical/0413_1715__raw_union/union/seeds/seed-11/optimization_result.json`
- Output: `/home/hymn/msfenicsx/scenario_runs/s1_typical/llm-smoke/`

- [ ] **Step 1: Run the focused optimizers verification suite**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_optimizer_io.py \
  tests/optimizers/test_operator_pool_adapters.py \
  tests/optimizers/test_llm_controller_state.py \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_optimizer_cli.py \
  -v
```

Expected: all selected optimizer tests pass

- [ ] **Step 2: Run the real `llm` smoke benchmark**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/s1_typical_llm.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s1_typical/llm-smoke
```

Expected:

- run completes without crashing
- `controller_trace.json`, `operator_trace.json`, `llm_request_trace.jsonl`, and `llm_response_trace.jsonl` are emitted

- [ ] **Step 3: Check trace health before judging optimization quality**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli analyze-controller-trace \
  --controller-trace ./scenario_runs/s1_typical/llm-smoke/seeds/seed-11/controller_trace.json \
  --output ./scenario_runs/s1_typical/llm-smoke/reports/controller_trace_summary.json
```

Expected:

- trace summary is written
- fallback / invalid-response counts are visible

- [ ] **Step 4: Compare the live `llm` result against the current matched `union` baseline**

Use:

- `/home/hymn/msfenicsx/scenario_runs/s1_typical/0413_1715__raw_union/union/seeds/seed-11/optimization_result.json`
- the new `llm` run `optimization_result.json`

Comparison checklist:

- `first_feasible_eval`
- `optimizer_feasible_rate`
- `pareto_size`
- unique non-dominated objective pairs
- whether the `llm` front adds a new non-dominated point versus `union`

- [ ] **Step 5: Record the result honestly**

Outcome rules:

- if `llm` improves at least one feasibility signal and at least one Pareto-quality signal, label it paper-positive
- if it only improves one side, label it partial evidence
- if it regresses, label it as a hypothesis-disconfirming smoke result and keep the traces for diagnosis

