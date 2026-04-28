# S2 LLM Peak-Polish Stabilization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove `anchored_component_jitter` from the default LLM operator pool while preserving the union clean baseline, reclassify `component_jitter_1` as a peak-improving local refiner, and stop peak-pressure post-feasible logic from cooling it away before the controller can reuse the low-peak basin.

**Architecture:** Keep the exact-pool validation contract intact instead of weakening `operator_control.operator_pool` checks. Split the full clean primitive pool from the LLM-approved primitive subset, so `primitive_clean` keeps `anchored_component_jitter` for union while `primitive_plus_assisted` becomes the exact LLM pool without it. Then route peak-pressure handling through existing prompt and policy-kernel signals: mark `component_jitter_1` as `expected_peak_effect=improve`, add it to the peak-balance escape lane, and exempt it from low-success cooldown only while the controller is explicitly under `peak_improve` pressure.

**Tech Stack:** Python 3.11, pytest, YAML optimization specs, optimizer operator registry, LLM controller prompt state, policy kernel.

---

## File Map

- Modify: `optimizers/operator_pool/primitive_registry.py` — keep the full clean primitive tuple and add an explicit LLM-approved primitive subset without `anchored_component_jitter`.
- Modify: `optimizers/operator_pool/operators.py` — make `approved_operator_pool("primitive_plus_assisted")` use the LLM-approved primitive subset plus assisted operators; leave `primitive_clean` unchanged.
- Modify: `scenarios/optimization/s1_typical_llm.yaml` — remove `anchored_component_jitter` from the explicit LLM operator pool.
- Modify: `scenarios/optimization/s2_staged_llm.yaml` — remove `anchored_component_jitter` from the explicit LLM operator pool.
- Modify: `scenarios/optimization/s1_typical_cmopso_llm.yaml` — mirror the same LLM-pool removal for the branch’s CMOPSO LLM spec.
- Modify: `scenarios/optimization/s1_typical_spea2_llm.yaml` — mirror the same LLM-pool removal for the branch’s SPEA2 LLM spec.
- Modify: `optimizers/operator_pool/state_builder.py` — change prompt-surface effect metadata so `component_jitter_1` and legacy `local_refine` count as peak-improving operators.
- Modify: `optimizers/operator_pool/policy_kernel.py` — keep `component_jitter_1` available when `preferred_effect=peak_improve`, including low-success cooldown escape and peak-balance escape-candidate merging.
- Modify: `tests/optimizers/test_operator_pool_contracts.py` — lock the clean-vs-LLM pool split and keep the controller-agnostic registry contract.
- Modify: `tests/optimizers/test_optimizer_io.py` — keep spec-loading tests aligned with the new exact `primitive_plus_assisted` pool.
- Modify: `tests/optimizers/test_s2_staged_baseline.py` — assert the S2 union/llm split now excludes `anchored_component_jitter` only from LLM, and assert `component_jitter_1` now advertises peak-improve semantics.
- Modify: `tests/optimizers/test_llm_policy_kernel.py` — add a regression that low-success cooldown still throttles `anchored_component_jitter` but keeps `component_jitter_1` alive under peak pressure.
- Modify: `README.md` — document that the assisted LLM line uses a curated primitive subset, excluding `anchored_component_jitter`.
- Modify: `AGENTS.md` — keep the Codex-facing repository contract aligned with the new LLM pool wording.

---

### Task 1: Split the clean primitive pool from the LLM-approved primitive subset

**Files:**
- Modify: `tests/optimizers/test_operator_pool_contracts.py:77-95`
- Modify: `tests/optimizers/test_optimizer_io.py:314-324`
- Modify: `tests/optimizers/test_s2_staged_baseline.py:81-109`
- Modify: `optimizers/operator_pool/primitive_registry.py:6-14`
- Modify: `optimizers/operator_pool/operators.py:37-42`
- Modify: `scenarios/optimization/s1_typical_llm.yaml:148-161`
- Modify: `scenarios/optimization/s2_staged_llm.yaml:148-161`
- Modify: `scenarios/optimization/s1_typical_cmopso_llm.yaml:148-161`
- Modify: `scenarios/optimization/s1_typical_spea2_llm.yaml:148-161`

- [ ] **Step 1: Write the failing contract tests for the new LLM pool split**

```python
# tests/optimizers/test_operator_pool_contracts.py
from optimizers.operator_pool.primitive_registry import (
    LLM_PRIMITIVE_OPERATOR_IDS,
    PRIMITIVE_OPERATOR_IDS,
)


def test_registry_profiles_expose_clean_vs_assisted_pools() -> None:
    from optimizers.operator_pool.operators import approved_operator_pool

    assert approved_operator_pool("primitive_clean") == PRIMITIVE_OPERATOR_IDS
    assert approved_operator_pool("primitive_plus_assisted") == (
        *LLM_PRIMITIVE_OPERATOR_IDS,
        *ASSISTED_OPERATOR_IDS,
    )


# tests/optimizers/test_optimizer_io.py
assert tuple(llm_spec.operator_control["operator_pool"]) == approved_operator_pool("primitive_plus_assisted")
assert "anchored_component_jitter" not in llm_spec.operator_control["operator_pool"]


# tests/optimizers/test_s2_staged_baseline.py
assert "anchored_component_jitter" in union["operator_control"]["operator_pool"]
assert "anchored_component_jitter" not in llm["operator_control"]["operator_pool"]
assert set(llm["operator_control"]["operator_pool"]) - set(union["operator_control"]["operator_pool"]) == assisted_ids
assert set(union["operator_control"]["operator_pool"]) - set(llm["operator_control"]["operator_pool"]) == {
    "anchored_component_jitter"
}
```

- [ ] **Step 2: Run the focused contract tests to verify they fail before the code change**

Run:
```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v \
  tests/optimizers/test_operator_pool_contracts.py::test_registry_profiles_expose_clean_vs_assisted_pools \
  tests/optimizers/test_optimizer_io.py::test_llm_spec_shares_benchmark_source_and_extends_union_operator_pool \
  tests/optimizers/test_s2_staged_baseline.py::test_s2_staged_union_uses_clean_registry_while_llm_retains_assisted_pool
```

Expected:
- FAIL because `primitive_plus_assisted` still expands to `PRIMITIVE_OPERATOR_IDS + ASSISTED_OPERATOR_IDS`
- FAIL because the active LLM specs still enumerate `anchored_component_jitter`

- [ ] **Step 3: Implement the registry split without weakening validation**

```python
# optimizers/operator_pool/primitive_registry.py
PRIMITIVE_OPERATOR_IDS = (
    "vector_sbx_pm",
    "component_jitter_1",
    "anchored_component_jitter",
    "component_relocate_1",
    "component_swap_2",
    "sink_shift",
    "sink_resize",
)

LLM_PRIMITIVE_OPERATOR_IDS = (
    "vector_sbx_pm",
    "component_jitter_1",
    "component_relocate_1",
    "component_swap_2",
    "sink_shift",
    "sink_resize",
)
```

```python
# optimizers/operator_pool/operators.py
from optimizers.operator_pool.primitive_registry import (
    LLM_PRIMITIVE_OPERATOR_IDS,
    PRIMITIVE_OPERATOR_IDS,
)


def approved_operator_pool(registry_profile: str) -> tuple[str, ...]:
    if registry_profile == "primitive_clean":
        return PRIMITIVE_OPERATOR_IDS
    if registry_profile == "primitive_plus_assisted":
        return (*LLM_PRIMITIVE_OPERATOR_IDS, *ASSISTED_OPERATOR_IDS)
    raise KeyError(f"Unsupported registry profile: {registry_profile!r}")
```

- [ ] **Step 4: Make every LLM spec on this branch exactly match the new approved pool**

```yaml
# scenarios/optimization/s1_typical_llm.yaml
operator_control:
  controller: llm
  registry_profile: primitive_plus_assisted
  operator_pool:
    - vector_sbx_pm
    - component_jitter_1
    - component_relocate_1
    - component_swap_2
    - sink_shift
    - sink_resize
    - hotspot_pull_toward_sink
    - hotspot_spread
    - gradient_band_smooth
    - congestion_relief
    - sink_retarget
    - layout_rebalance
```

```yaml
# scenarios/optimization/s2_staged_llm.yaml
operator_control:
  controller: llm
  registry_profile: primitive_plus_assisted
  operator_pool:
    - vector_sbx_pm
    - component_jitter_1
    - component_relocate_1
    - component_swap_2
    - sink_shift
    - sink_resize
    - hotspot_pull_toward_sink
    - hotspot_spread
    - gradient_band_smooth
    - congestion_relief
    - sink_retarget
    - layout_rebalance
```

```yaml
# scenarios/optimization/s1_typical_cmopso_llm.yaml
operator_control:
  controller: llm
  registry_profile: primitive_plus_assisted
  operator_pool:
    - vector_sbx_pm
    - component_jitter_1
    - component_relocate_1
    - component_swap_2
    - sink_shift
    - sink_resize
    - hotspot_pull_toward_sink
    - hotspot_spread
    - gradient_band_smooth
    - congestion_relief
    - sink_retarget
    - layout_rebalance
```

```yaml
# scenarios/optimization/s1_typical_spea2_llm.yaml
operator_control:
  controller: llm
  registry_profile: primitive_plus_assisted
  operator_pool:
    - vector_sbx_pm
    - component_jitter_1
    - component_relocate_1
    - component_swap_2
    - sink_shift
    - sink_resize
    - hotspot_pull_toward_sink
    - hotspot_spread
    - gradient_band_smooth
    - congestion_relief
    - sink_retarget
    - layout_rebalance
```

- [ ] **Step 5: Re-run the same contract/spec tests and make sure they pass**

Run:
```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v \
  tests/optimizers/test_operator_pool_contracts.py::test_registry_profiles_expose_clean_vs_assisted_pools \
  tests/optimizers/test_optimizer_io.py::test_llm_spec_shares_benchmark_source_and_extends_union_operator_pool \
  tests/optimizers/test_s2_staged_baseline.py::test_s2_staged_union_uses_clean_registry_while_llm_retains_assisted_pool
```

Expected:
- PASS
- The printed collected tests should finish without `OptimizationValidationError`

- [ ] **Step 6: Commit the registry/profile split**

```bash
git add \
  optimizers/operator_pool/primitive_registry.py \
  optimizers/operator_pool/operators.py \
  scenarios/optimization/s1_typical_llm.yaml \
  scenarios/optimization/s2_staged_llm.yaml \
  scenarios/optimization/s1_typical_cmopso_llm.yaml \
  scenarios/optimization/s1_typical_spea2_llm.yaml \
  tests/optimizers/test_operator_pool_contracts.py \
  tests/optimizers/test_optimizer_io.py \
  tests/optimizers/test_s2_staged_baseline.py

git commit -m "refactor(optimizers): split llm operator pool from clean primitives"
```

---

### Task 2: Reclassify `component_jitter_1` as a peak-improving local refiner

**Files:**
- Modify: `tests/optimizers/test_s2_staged_baseline.py:113-121`
- Modify: `optimizers/operator_pool/state_builder.py:35-100`

- [ ] **Step 1: Write the failing prompt-metadata assertion**

```python
# tests/optimizers/test_s2_staged_baseline.py
panel = _build_prompt_operator_panel(
    operator_summary={},
    candidate_operator_ids=("component_jitter_1", "anchored_component_jitter", "sink_retarget"),
    regime_panel={"phase": "post_feasible_expand"},
)
assert panel["component_jitter_1"]["expected_peak_effect"] == "improve"
assert panel["component_jitter_1"]["expected_gradient_effect"] == "neutral"
assert panel["anchored_component_jitter"]["expected_peak_effect"] == "neutral"
assert panel["sink_retarget"]["expected_peak_effect"] == "improve"
```

- [ ] **Step 2: Run the focused prompt-panel test and verify it fails**

Run:
```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v \
  tests/optimizers/test_s2_staged_baseline.py::test_s2_staged_union_uses_clean_registry_while_llm_retains_assisted_pool
```

Expected:
- FAIL because `panel["component_jitter_1"]["expected_peak_effect"]` is still `"neutral"`

- [ ] **Step 3: Update the prompt effect metadata**

```python
# optimizers/operator_pool/state_builder.py
_OPERATOR_EFFECTS: dict[str, dict[str, str]] = {
    "vector_sbx_pm": {
        "expected_peak_effect": "neutral",
        "expected_gradient_effect": "neutral",
    },
    "component_jitter_1": {
        "expected_peak_effect": "improve",
        "expected_gradient_effect": "neutral",
    },
    "anchored_component_jitter": {
        "expected_peak_effect": "neutral",
        "expected_gradient_effect": "neutral",
    },
    # ... unchanged rows ...
    "local_refine": {
        "expected_peak_effect": "improve",
        "expected_gradient_effect": "neutral",
    },
}
```

- [ ] **Step 4: Re-run the prompt-panel test and make sure it passes**

Run:
```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v \
  tests/optimizers/test_s2_staged_baseline.py::test_s2_staged_union_uses_clean_registry_while_llm_retains_assisted_pool
```

Expected:
- PASS
- The test now confirms `component_jitter_1` is surfaced as `expected_peak_effect=improve`

- [ ] **Step 5: Commit the metadata change**

```bash
git add \
  optimizers/operator_pool/state_builder.py \
  tests/optimizers/test_s2_staged_baseline.py

git commit -m "fix(optimizers): classify component jitter as peak-improving"
```

---

### Task 3: Keep `component_jitter_1` visible when peak pressure is active

**Files:**
- Modify: `tests/optimizers/test_llm_policy_kernel.py:1836-2057`
- Modify: `tests/optimizers/test_llm_policy_kernel.py:3037-3119`
- Modify: `optimizers/operator_pool/policy_kernel.py:37-46`
- Modify: `optimizers/operator_pool/policy_kernel.py:143-158`
- Modify: `optimizers/operator_pool/policy_kernel.py:576-592`
- Modify: `optimizers/operator_pool/policy_kernel.py:919-941`

- [ ] **Step 1: Add a failing regression for peak-pressure cooldown escape**

```python
# tests/optimizers/test_llm_policy_kernel.py
def _post_feasible_preserve_peak_pressure_component_jitter_state() -> ControllerState:
    state = _post_feasible_preserve_plateau_sink_state()
    state.metadata["prompt_panels"]["regime_panel"]["objective_balance"] = {
        "balance_pressure": "high",
        "preferred_effect": "peak_improve",
        "stagnant_objectives": ["temperature_max"],
        "improving_objectives": ["gradient_rms"],
    }
    state.metadata["operator_summary"]["component_jitter_1"] = {
        "selection_count": 14,
        "recent_selection_count": 1,
        "proposal_count": 14,
        "feasible_regression_count": 8,
        "post_feasible_success_count": 3,
        "post_feasible_selection_count": 14,
        "post_feasible_thermal_infeasible_count": 8,
    }
    return state


def test_post_feasible_preserve_keeps_component_jitter_during_peak_pressure() -> None:
    policy_kernel = _policy_kernel_module()

    policy = policy_kernel.build_policy_snapshot(
        _post_feasible_preserve_peak_pressure_component_jitter_state(),
        (
            "vector_sbx_pm",
            "component_jitter_1",
            "anchored_component_jitter",
            "component_swap_2",
            "sink_shift",
            "sink_resize",
            "sink_retarget",
        ),
    )

    assert policy.phase == "post_feasible_preserve"
    assert "component_jitter_1" in policy.allowed_operator_ids
    assert "anchored_component_jitter" not in policy.allowed_operator_ids
    assert "post_feasible_stable_low_success_cooldown" in policy.reason_codes
    assert policy.candidate_annotations["component_jitter_1"]["stable_success_state"]["budget_status"] == "throttled"
```

The last assertion is intentionally written to fail before the code change; it should be updated to `"neutral"` after the implementation lands.

- [ ] **Step 2: Run the focused policy-kernel regression and verify it fails**

Run:
```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v \
  tests/optimizers/test_llm_policy_kernel.py::test_post_feasible_preserve_keeps_component_jitter_during_peak_pressure
```

Expected:
- FAIL because `component_jitter_1` is still throttled by stable low-success cooldown under peak pressure

- [ ] **Step 3: Extend the peak-balance lane and add the cooldown exemption**

```python
# optimizers/operator_pool/policy_kernel.py
_PEAK_BALANCE_ESCAPE_OPERATORS = frozenset(
    {
        "component_jitter_1",
        "hotspot_pull_toward_sink",
        "sink_resize",
        "sink_retarget",
        "slide_sink",
        "move_hottest_cluster_toward_sink",
        "repair_sink_budget",
    }
)
```

```python
# optimizers/operator_pool/policy_kernel.py
def _stable_low_success_peak_pressure_exempt(
    state: ControllerState,
    operator_id: str,
    annotation: dict[str, Any],
) -> bool:
    if str(operator_id) != "component_jitter_1":
        return False
    if str(annotation.get("role", "")) != "component_jitter":
        return False
    prompt_panels = state.metadata.get("prompt_panels")
    if not isinstance(prompt_panels, dict):
        return False
    regime_panel = prompt_panels.get("regime_panel")
    if not isinstance(regime_panel, dict):
        return False
    objective_balance = regime_panel.get("objective_balance")
    if not isinstance(objective_balance, dict):
        return False
    return (
        str(objective_balance.get("preferred_effect", "")).strip() == "peak_improve"
        and str(objective_balance.get("balance_pressure", "")).strip() in {"high", "medium"}
    )


def _post_feasible_stable_low_success_suppression(
    state: ControllerState,
    candidate_operator_ids: Sequence[str],
    candidate_annotations: dict[str, dict[str, Any]],
) -> tuple[str, ...]:
    throttled = tuple(
        operator_id
        for operator_id in candidate_operator_ids
        if str(
            dict(candidate_annotations.get(operator_id, {}))
            .get("stable_success_state", {})
            .get("budget_status", "")
        ) == "throttled"
        and not _stable_low_success_peak_pressure_exempt(
            state,
            operator_id,
            dict(candidate_annotations.get(operator_id, {})),
        )
    )
    if not throttled:
        return ()
    viable_alternatives = tuple(
        operator_id
        for operator_id in candidate_operator_ids
        if operator_id not in throttled
        and str(candidate_annotations.get(operator_id, {}).get("post_feasible_role", "")) != "risky_expand"
    )
    return throttled if viable_alternatives else ()
```

```python
# optimizers/operator_pool/policy_kernel.py
stable_low_success_suppressed = _post_feasible_stable_low_success_suppression(
    state,
    tuple(allowed_operator_ids),
    candidate_annotations,
)
```

- [ ] **Step 4: Update the regression assertion and re-run the focused policy tests**

```python
# tests/optimizers/test_llm_policy_kernel.py
assert policy.candidate_annotations["component_jitter_1"]["stable_success_state"]["budget_status"] == "neutral"
```

Run:
```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v \
  tests/optimizers/test_llm_policy_kernel.py::test_post_feasible_preserve_cools_sink_plateau_and_low_success_stable_routes \
  tests/optimizers/test_llm_policy_kernel.py::test_post_feasible_preserve_keeps_component_jitter_during_peak_pressure \
  tests/optimizers/test_llm_policy_kernel.py::test_post_feasible_preserve_keeps_peak_budget_fill_routes_during_plateau
```

Expected:
- PASS
- `anchored_component_jitter` is still throttled in the original plateau test
- `component_jitter_1` stays visible in the new peak-pressure regression

- [ ] **Step 5: Commit the peak-pressure policy fix**

```bash
git add \
  optimizers/operator_pool/policy_kernel.py \
  tests/optimizers/test_llm_policy_kernel.py

git commit -m "fix(optimizers): keep component jitter visible under peak pressure"
```

---

### Task 4: Update docs and run focused verification plus one live trace audit

**Files:**
- Modify: `README.md:10-37`
- Modify: `AGENTS.md:14-18`
- Verify: `tests/optimizers/test_operator_pool_contracts.py`
- Verify: `tests/optimizers/test_optimizer_io.py`
- Verify: `tests/optimizers/test_s2_staged_baseline.py`
- Verify: `tests/optimizers/test_llm_policy_kernel.py`

- [ ] **Step 1: Update the human-facing contract text**

```markdown
# README.md
- clean baselines use `minimal_canonicalization`; assisted `llm` runs use `projection_plus_local_restore`
- active optimizer modes:
  - `nsga2_raw`
  - `nsga2_union`
  - `nsga2_llm`
- `union` keeps the full clean primitive pool, including `anchored_component_jitter`
- `llm` uses the assisted framework pool plus the curated primitive subset without `anchored_component_jitter`
```

```markdown
# AGENTS.md
- The active optimizer ladder now uses explicit registry and legality-policy splits:
  - `raw`: native backbone + clean legality policy
  - `union`: primitive operator registry + random controller + clean legality policy
  - `llm`: curated primitive subset (without `anchored_component_jitter`) + assisted registry + assisted legality policy
```

- [ ] **Step 2: Run the full focused verification set for the changed controller contract**

Run:
```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v \
  tests/optimizers/test_operator_pool_contracts.py \
  tests/optimizers/test_optimizer_io.py \
  tests/optimizers/test_s2_staged_baseline.py \
  tests/optimizers/test_llm_policy_kernel.py
```

Expected:
- PASS
- No validation failures about `operator_control.operator_pool`
- No prompt-panel assertion failures about `component_jitter_1`
- No policy-kernel regressions around plateau cooldown and peak pressure

- [ ] **Step 3: Run one controlled S2 LLM smoke validation and confirm the trace shape changed as intended**

Run:
```bash
RUN_ID="$(date +%m%d_%H%M)__llm"
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/s2_staged_llm.yaml \
  --evaluation-workers 2 \
  --output-root "./scenario_runs/s2_staged/${RUN_ID}"
```

Then audit the trace:

```bash
python - <<'PY'
import json
import os
from pathlib import Path

run_root = max(Path("scenario_runs/s2_staged").glob("*__llm"), key=lambda p: p.stat().st_mtime)
print(f"run_root={run_root}")
operator_trace = run_root / "traces/operator_trace.jsonl"
request_trace = run_root / "traces/llm_request_trace.jsonl"

counts = {}
for line in operator_trace.read_text().splitlines():
    if not line.strip():
        continue
    row = json.loads(line)
    operator_id = row.get("operator_name")
    counts[operator_id] = counts.get(operator_id, 0) + 1

peak_pressure_requests = 0
late_jitter_visibility = 0
for line in request_trace.read_text().splitlines():
    if not line.strip():
        continue
    row = json.loads(line)
    payload = json.loads(row["user_prompt"])
    objective_balance = (
        payload.get("metadata", {})
        .get("prompt_panels", {})
        .get("regime_panel", {})
        .get("objective_balance", {})
    )
    if objective_balance.get("preferred_effect") == "peak_improve":
        peak_pressure_requests += 1
        if "component_jitter_1" in (row.get("candidate_operator_ids") or []):
            late_jitter_visibility += 1

print("anchored_component_jitter", counts.get("anchored_component_jitter", 0))
print("component_jitter_1", counts.get("component_jitter_1", 0))
print("peak_pressure_requests", peak_pressure_requests)
print("peak_pressure_requests_with_jitter_visible", late_jitter_visibility)
PY
```

Expected:
- `anchored_component_jitter 0`
- `component_jitter_1` is non-zero
- If the run ever enters `preferred_effect=peak_improve`, at least one such request should keep `component_jitter_1` in `candidate_operator_ids`

- [ ] **Step 4: Commit docs and verification updates**

```bash
git add \
  README.md \
  AGENTS.md

git commit -m "docs(optimizers): document curated llm primitive subset"
```

---

## Self-Review

- **Spec coverage:** This plan covers the three approved changes: remove `anchored_component_jitter` from the default LLM line only, mark `component_jitter_1` as a peak-improving primitive, and keep it visible under explicit peak pressure without weakening the exact-pool validation contract.
- **Placeholder scan:** No `TODO`, `TBD`, “similar to above”, or unnamed commands remain. Every code-touching step includes exact file paths, concrete code, and concrete pytest or CLI commands.
- **Type consistency:** New names stay consistent across files: `LLM_PRIMITIVE_OPERATOR_IDS` is referenced everywhere the plan touches the split pool, and `component_jitter_1` remains the only stable local primitive granted the peak-pressure cooldown exemption.
