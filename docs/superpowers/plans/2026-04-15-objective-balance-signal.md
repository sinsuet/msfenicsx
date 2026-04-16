# Objective Balance Signal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-objective stagnation detection and prompt-layer balance signals so the LLM controller stops over-selecting grad_rms operators when T_max is stagnant.

**Architecture:** Four coordinated changes across domain_state (stagnation detection + regime panel), llm_controller (decision_axes + system_prompt), and state_builder (applicability boost). All changes are prompt-layer soft signals — no policy_kernel hard filters change.

**Tech Stack:** Python, pytest, numpy. All work in the `codex/l2-llm-controller-recovery` branch worktree at `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery`.

**Spec:** `docs/superpowers/specs/2026-04-15-objective-balance-signal-design.md`

**Run prefix:** `conda run -n msfenicsx`

**Working directory:** `/home/hymn/msfenicsx/.worktrees/codex-l2-llm-controller-recovery`

---

### Task 1: Per-objective stagnation detection in domain_state.py

**Files:**
- Modify: `optimizers/operator_pool/domain_state.py:574-719` (`build_progress_state`)
- Test: `tests/optimizers/test_llm_controller_state.py`

- [ ] **Step 1: Write the failing test for objective_stagnation — stagnant case**

Add to `tests/optimizers/test_llm_controller_state.py`:

```python
def test_objective_stagnation_detects_tmax_stagnation():
    """When T_max is flat across 8 feasible evals but grad_rms improves, temperature_max is stagnant."""
    from optimizers.operator_pool.domain_state import build_progress_state

    history = []
    vec = _vector()
    # First feasible at eval 10
    history.append(_record(
        10, vec, feasible=True,
        peak_temperature=310.0, temperature_gradient_rms=15.0,
        c01_temperature_violation=0.0, panel_spread_violation=0.0,
    ))
    # Evals 11-18: T_max stuck at 310, grad_rms improving
    for i in range(11, 19):
        history.append(_record(
            i, vec, feasible=True,
            peak_temperature=310.0, temperature_gradient_rms=15.0 - 0.3 * (i - 10),
            c01_temperature_violation=0.0, panel_spread_violation=0.0,
        ))

    progress = build_progress_state(history=history)

    stagnation = progress["objective_stagnation"]
    assert stagnation["temperature_max"]["stagnant"] is True
    assert stagnation["temperature_max"]["evaluations_since_improvement"] >= 6
    assert stagnation["gradient_rms"]["stagnant"] is False
```

- [ ] **Step 2: Write the failing test for objective_stagnation — no stagnation case**

```python
def test_objective_stagnation_no_stagnation_when_both_improve():
    """When both objectives improve recently, neither is stagnant."""
    from optimizers.operator_pool.domain_state import build_progress_state

    history = []
    vec = _vector()
    for i in range(10, 18):
        history.append(_record(
            i, vec, feasible=True,
            peak_temperature=310.0 - 0.5 * (i - 10),
            temperature_gradient_rms=15.0 - 0.3 * (i - 10),
            c01_temperature_violation=0.0, panel_spread_violation=0.0,
        ))

    progress = build_progress_state(history=history)

    stagnation = progress["objective_stagnation"]
    assert stagnation["temperature_max"]["stagnant"] is False
    assert stagnation["gradient_rms"]["stagnant"] is False
```

- [ ] **Step 3: Write the failing test for objective_stagnation — prefeasible has empty stagnation**

```python
def test_objective_stagnation_empty_when_no_feasible():
    """Before any feasible solution, objective_stagnation should have no entries."""
    from optimizers.operator_pool.domain_state import build_progress_state

    history = []
    vec = _vector()
    for i in range(1, 6):
        history.append(_record(
            i, vec, feasible=False,
            peak_temperature=320.0, temperature_gradient_rms=20.0,
            c01_temperature_violation=5.0, panel_spread_violation=0.0,
        ))

    progress = build_progress_state(history=history)

    stagnation = progress["objective_stagnation"]
    assert stagnation["temperature_max"]["stagnant"] is False
    assert stagnation["gradient_rms"]["stagnant"] is False
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_llm_controller_state.py -v -k "objective_stagnation"`
Expected: FAIL (KeyError on `objective_stagnation`)

- [ ] **Step 5: Implement per-objective stagnation detection**

In `optimizers/operator_pool/domain_state.py`, add the constant after `_EXPAND_SATURATION_THRESHOLD = 24` (line 13):

```python
_OBJECTIVE_STAGNATION_THRESHOLD = 6
```

At the end of `build_progress_state` (before the final `return` at line ~700), add the stagnation computation and include it in the returned dict:

```python
    # Per-objective stagnation detection
    objective_stagnation = _build_objective_stagnation(ordered_history, first_feasible_eval, latest_completed_eval)
```

Add a new helper function after `build_progress_state`:

```python
def _build_objective_stagnation(
    ordered_history: list[Mapping[str, Any]],
    first_feasible_eval: int | None,
    latest_completed_eval: int,
) -> dict[str, dict[str, Any]]:
    """Track per-objective stagnation across feasible evaluations."""
    objective_keys = {
        "temperature_max": "summary.temperature_max",
        "gradient_rms": "summary.temperature_gradient_rms",
    }
    result: dict[str, dict[str, Any]] = {}
    for short_key, metric_key in objective_keys.items():
        best_value: float | None = None
        last_improvement_eval: int | None = None
        for row in ordered_history:
            if not bool(row.get("feasible", False)):
                continue
            if str(row.get("source", "")).strip().lower() == "baseline":
                continue
            eval_index = int(row.get("evaluation_index", 0))
            value = _metric_from_record(row, metric_key)
            if value is None:
                continue
            if best_value is None or value < best_value:
                best_value = value
                last_improvement_eval = eval_index
        if best_value is None or last_improvement_eval is None:
            result[short_key] = {
                "best_value": None,
                "evaluations_since_improvement": None,
                "stagnant": False,
            }
        else:
            evals_since = max(0, latest_completed_eval - last_improvement_eval)
            result[short_key] = {
                "best_value": float(best_value),
                "evaluations_since_improvement": int(evals_since),
                "stagnant": evals_since >= _OBJECTIVE_STAGNATION_THRESHOLD,
            }
    return result
```

Add `"objective_stagnation": objective_stagnation` to the returned dict of `build_progress_state`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_llm_controller_state.py -v -k "objective_stagnation"`
Expected: 3 PASSED

- [ ] **Step 7: Run full optimizer test suite for regressions**

Run: `conda run -n msfenicsx pytest tests/optimizers/ -v`
Expected: All pass (160/160)

- [ ] **Step 8: Commit**

```bash
git add optimizers/operator_pool/domain_state.py tests/optimizers/test_llm_controller_state.py
git commit -m "feat: add per-objective stagnation detection to build_progress_state"
```

---

### Task 2: Objective balance sub-panel in regime_panel

**Files:**
- Modify: `optimizers/operator_pool/domain_state.py:870-935` (`build_prompt_regime_panel`)
- Test: `tests/optimizers/test_llm_controller_state.py`

- [ ] **Step 1: Write the failing test — high balance pressure**

```python
def test_regime_panel_objective_balance_high_pressure():
    """When T_max stagnant and grad_rms improving, balance_pressure is high with peak_improve."""
    from optimizers.operator_pool.domain_state import build_prompt_regime_panel

    run_state = {
        "first_feasible_eval": 10,
        "evaluations_used": 50,
        "peak_temperature": 307.0,
        "temperature_gradient_rms": 10.0,
    }
    progress_state = {
        "recent_no_progress_count": 0,
        "recent_frontier_stagnation_count": 2,
        "post_feasible_mode": "expand",
        "stable_preservation_streak": 0,
        "new_dominant_violation_family": False,
        "recent_dominant_violation_family": None,
        "recent_dominant_violation_persistence_count": 0,
        "expand_saturation_count": 0,
        "objective_stagnation": {
            "temperature_max": {"best_value": 307.0, "evaluations_since_improvement": 15, "stagnant": True},
            "gradient_rms": {"best_value": 10.0, "evaluations_since_improvement": 2, "stagnant": False},
        },
    }
    archive_state = {
        "recent_feasible_regression_count": 0,
        "recent_feasible_preservation_count": 2,
    }
    domain_regime = {"phase": "feasible_refine"}

    panel = build_prompt_regime_panel(
        run_state=run_state,
        progress_state=progress_state,
        archive_state=archive_state,
        domain_regime=domain_regime,
    )

    balance = panel["objective_balance"]
    assert balance["balance_pressure"] == "high"
    assert balance["preferred_effect"] == "peak_improve"
    assert "temperature_max" in balance["stagnant_objectives"]
    assert "gradient_rms" in balance["improving_objectives"]
```

- [ ] **Step 2: Write the failing test — low balance pressure**

```python
def test_regime_panel_objective_balance_low_when_no_stagnation():
    """When no stagnation, balance_pressure is low."""
    from optimizers.operator_pool.domain_state import build_prompt_regime_panel

    run_state = {
        "first_feasible_eval": 10,
        "evaluations_used": 50,
        "peak_temperature": 307.0,
        "temperature_gradient_rms": 10.0,
    }
    progress_state = {
        "recent_no_progress_count": 0,
        "recent_frontier_stagnation_count": 2,
        "post_feasible_mode": "expand",
        "stable_preservation_streak": 0,
        "new_dominant_violation_family": False,
        "recent_dominant_violation_family": None,
        "recent_dominant_violation_persistence_count": 0,
        "expand_saturation_count": 0,
        "objective_stagnation": {
            "temperature_max": {"best_value": 305.0, "evaluations_since_improvement": 1, "stagnant": False},
            "gradient_rms": {"best_value": 10.0, "evaluations_since_improvement": 2, "stagnant": False},
        },
    }
    archive_state = {
        "recent_feasible_regression_count": 0,
        "recent_feasible_preservation_count": 2,
    }
    domain_regime = {"phase": "feasible_refine"}

    panel = build_prompt_regime_panel(
        run_state=run_state,
        progress_state=progress_state,
        archive_state=archive_state,
        domain_regime=domain_regime,
    )

    balance = panel["objective_balance"]
    assert balance["balance_pressure"] == "low"
    assert balance["preferred_effect"] is None
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_llm_controller_state.py -v -k "objective_balance"`
Expected: FAIL (KeyError on `objective_balance`)

- [ ] **Step 4: Implement objective_balance sub-panel**

In `build_prompt_regime_panel`, before the final `return regime_panel`, add:

```python
    objective_stagnation = progress_state.get("objective_stagnation", {})
    regime_panel["objective_balance"] = _build_objective_balance(objective_stagnation)
```

Add helper after `build_prompt_regime_panel`:

```python
def _build_objective_balance(
    objective_stagnation: Mapping[str, Any],
) -> dict[str, Any]:
    """Derive balance pressure and preferred effect from per-objective stagnation."""
    tmax_stagnant = bool(
        isinstance(objective_stagnation.get("temperature_max"), Mapping)
        and objective_stagnation["temperature_max"].get("stagnant", False)
    )
    grad_stagnant = bool(
        isinstance(objective_stagnation.get("gradient_rms"), Mapping)
        and objective_stagnation["gradient_rms"].get("stagnant", False)
    )
    stagnant_objectives = []
    improving_objectives = []
    if tmax_stagnant:
        stagnant_objectives.append("temperature_max")
    else:
        improving_objectives.append("temperature_max")
    if grad_stagnant:
        stagnant_objectives.append("gradient_rms")
    else:
        improving_objectives.append("gradient_rms")

    if tmax_stagnant and not grad_stagnant:
        balance_pressure = "high"
        preferred_effect = "peak_improve"
    elif grad_stagnant and not tmax_stagnant:
        balance_pressure = "high"
        preferred_effect = "gradient_improve"
    elif tmax_stagnant and grad_stagnant:
        balance_pressure = "medium"
        preferred_effect = "balanced"
    else:
        balance_pressure = "low"
        preferred_effect = None

    return {
        "stagnant_objectives": stagnant_objectives,
        "improving_objectives": improving_objectives,
        "balance_pressure": balance_pressure,
        "preferred_effect": preferred_effect,
    }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_llm_controller_state.py -v -k "objective_balance"`
Expected: 2 PASSED

- [ ] **Step 6: Run full optimizer test suite**

Run: `conda run -n msfenicsx pytest tests/optimizers/ -v`
Expected: All pass

- [ ] **Step 7: Commit**

```bash
git add optimizers/operator_pool/domain_state.py tests/optimizers/test_llm_controller_state.py
git commit -m "feat: add objective_balance sub-panel to regime_panel"
```

---

### Task 3: Applicability boost in state_builder.py

**Files:**
- Modify: `optimizers/operator_pool/state_builder.py:85-140` (`_build_prompt_operator_panel`)
- Modify: `optimizers/operator_pool/state_builder.py:159-260` (`_build_operator_applicability_row`)
- Test: `tests/optimizers/test_llm_controller_state.py`

- [ ] **Step 1: Write the failing test — slide_sink boosted under peak_improve**

```python
def test_applicability_boost_slide_sink_under_peak_improve():
    """slide_sink applicability should be boosted when objective_balance says peak_improve."""
    from optimizers.operator_pool.state_builder import _build_operator_applicability_row

    spatial_panel = {
        "hotspot_to_sink_offset": 0.05,
        "hotspot_inside_sink_window": True,
        "hottest_cluster_compactness": 0.15,
        "nearest_neighbor_gap_min": 0.15,
        "sink_budget_bucket": "available",
    }
    regime_panel = {
        "phase": "post_feasible_expand",
        "frontier_pressure": "high",
        "preservation_pressure": "medium",
    }
    # Without boost: slide_sink inside sink window + small offset → applicability_score=0 → "low"
    row_no_boost = _build_operator_applicability_row(
        "slide_sink", spatial_panel=spatial_panel, regime_panel=regime_panel,
    )
    assert row_no_boost["applicability"] == "low"

    # With peak_improve boost: +1 → "medium"
    objective_balance = {"preferred_effect": "peak_improve", "balance_pressure": "high"}
    row_boosted = _build_operator_applicability_row(
        "slide_sink", spatial_panel=spatial_panel, regime_panel=regime_panel,
        objective_balance=objective_balance,
    )
    assert row_boosted["applicability"] == "medium"
```

- [ ] **Step 2: Write the failing test — no boost when balance_pressure is low**

```python
def test_applicability_no_boost_when_balance_low():
    """No applicability boost when balance_pressure is low."""
    from optimizers.operator_pool.state_builder import _build_operator_applicability_row

    spatial_panel = {
        "hotspot_to_sink_offset": 0.05,
        "hotspot_inside_sink_window": True,
        "hottest_cluster_compactness": 0.15,
        "nearest_neighbor_gap_min": 0.15,
        "sink_budget_bucket": "available",
    }
    regime_panel = {
        "phase": "post_feasible_expand",
        "frontier_pressure": "high",
        "preservation_pressure": "medium",
    }
    objective_balance = {"preferred_effect": None, "balance_pressure": "low"}
    row = _build_operator_applicability_row(
        "slide_sink", spatial_panel=spatial_panel, regime_panel=regime_panel,
        objective_balance=objective_balance,
    )
    assert row["applicability"] == "low"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_llm_controller_state.py -v -k "applicability_boost or applicability_no_boost"`
Expected: FAIL (TypeError — unexpected keyword argument `objective_balance`)

- [ ] **Step 4: Implement the applicability boost**

Modify `_build_operator_applicability_row` signature at line 159:

```python
def _build_operator_applicability_row(
    operator_id: str,
    *,
    spatial_panel: Mapping[str, Any],
    regime_panel: Mapping[str, Any],
    objective_balance: Mapping[str, Any] | None = None,
) -> dict[str, str]:
```

After the existing per-operator scoring block (after the `elif operator_id == "native_sbx_pm":` block, around line 253), before the final `return`, add:

```python
    # Objective balance applicability boost
    if isinstance(objective_balance, Mapping):
        ob_pressure = str(objective_balance.get("balance_pressure", "low"))
        ob_effect = str(objective_balance.get("preferred_effect") or "")
        if ob_pressure in ("high", "medium") and ob_effect:
            if ob_effect == "peak_improve" and operator_id in (
                "slide_sink", "move_hottest_cluster_toward_sink", "local_refine",
            ):
                applicability_score += 1
            elif ob_effect == "peak_improve" and operator_id == "spread_hottest_cluster" and compact_cluster:
                applicability_score += 1
            elif ob_effect == "gradient_improve" and operator_id in (
                "smooth_high_gradient_band", "spread_hottest_cluster", "reduce_local_congestion",
            ):
                applicability_score += 1
```

Modify `_build_prompt_operator_panel` to pass `objective_balance` through. At line 85, the function already receives `regime_panel`. Extract the balance and pass it:

```python
    objective_balance = dict(regime_panel.get("objective_balance", {})) if isinstance(regime_panel.get("objective_balance"), Mapping) else None
```

Then in the per-operator loop, change the call:

```python
        operator_panel[normalized_operator_id].update(
            _build_operator_applicability_row(
                normalized_operator_id,
                spatial_panel=spatial_panel,
                regime_panel=regime_panel,
                objective_balance=objective_balance,
            )
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_llm_controller_state.py -v -k "applicability_boost or applicability_no_boost"`
Expected: 2 PASSED

- [ ] **Step 6: Run full optimizer test suite**

Run: `conda run -n msfenicsx pytest tests/optimizers/ -v`
Expected: All pass

- [ ] **Step 7: Commit**

```bash
git add optimizers/operator_pool/state_builder.py tests/optimizers/test_llm_controller_state.py
git commit -m "feat: add objective balance applicability boost to operator selection"
```

---

### Task 4: decision_axes + system_prompt guidance in llm_controller.py

**Files:**
- Modify: `optimizers/operator_pool/llm_controller.py:458-524` (`_build_decision_axes`)
- Modify: `optimizers/operator_pool/llm_controller.py:336-395` (`_build_system_prompt`)
- Test: `tests/optimizers/test_llm_controller.py`

- [ ] **Step 1: Write the failing test — decision_axes includes objective_balance fields**

Add to `tests/optimizers/test_llm_controller.py`:

```python
def test_decision_axes_objective_balance_fields():
    """decision_axes should include objective_balance_pressure and preferred_effect from regime_panel."""
    from optimizers.operator_pool.llm_controller import LLMOperatorController

    metadata = {
        "prompt_panels": {
            "regime_panel": {
                "phase": "post_feasible_expand",
                "preservation_pressure": "medium",
                "frontier_pressure": "high",
                "objective_balance": {
                    "stagnant_objectives": ["temperature_max"],
                    "improving_objectives": ["gradient_rms"],
                    "balance_pressure": "high",
                    "preferred_effect": "peak_improve",
                },
            },
            "operator_panel": {
                "slide_sink": {
                    "applicability": "high",
                    "expected_peak_effect": "improve",
                    "expected_gradient_effect": "neutral",
                    "expected_feasibility_risk": "low",
                    "recent_regression_risk": "low",
                },
                "native_sbx_pm": {
                    "applicability": "medium",
                    "expected_peak_effect": "neutral",
                    "expected_gradient_effect": "neutral",
                    "expected_feasibility_risk": "low",
                    "recent_regression_risk": "low",
                },
            },
            "spatial_panel": {"hotspot_inside_sink_window": False},
        },
    }

    axes = LLMOperatorController._build_decision_axes(metadata)

    assert axes["objective_balance_pressure"] == "high"
    assert axes["preferred_effect"] == "peak_improve"
    assert "slide_sink" in axes["peak_improve_candidates"]
```

- [ ] **Step 2: Write the failing test — system_prompt contains balance guidance**

```python
def test_system_prompt_objective_balance_guidance():
    """system_prompt should mention objective balance alert when balance_pressure is high."""
    from optimizers.operator_pool.llm_controller import LLMOperatorController
    from optimizers.operator_pool.policy_kernel import PolicySnapshot

    policy_snapshot = PolicySnapshot(
        phase="post_feasible_expand",
        allowed_operator_ids=("native_sbx_pm", "slide_sink"),
        suppressed_operator_ids=(),
        reset_active=False,
        reason_codes=(),
        candidate_annotations={},
    )
    state = _make_minimal_llm_state(objective_balance={
        "balance_pressure": "high",
        "preferred_effect": "peak_improve",
        "stagnant_objectives": ["temperature_max"],
        "improving_objectives": ["gradient_rms"],
    })

    controller = LLMOperatorController(controller_parameters={"model": "test", "api_key": "test"})
    prompt = controller._build_system_prompt(
        state,
        ("native_sbx_pm", "slide_sink"),
        policy_snapshot=policy_snapshot,
        guardrail=None,
    )

    assert "Objective balance alert" in prompt
    assert "temperature_max" in prompt
```

Also add this helper if not already present:

```python
def _make_minimal_llm_state(*, objective_balance=None):
    from optimizers.operator_pool.state import ControllerState
    metadata = {
        "run_state": {"first_feasible_eval": 10},
        "prompt_panels": {
            "regime_panel": {
                "phase": "post_feasible_expand",
                "preservation_pressure": "medium",
                "frontier_pressure": "high",
            },
            "operator_panel": {},
            "spatial_panel": {},
        },
    }
    if objective_balance is not None:
        metadata["prompt_panels"]["regime_panel"]["objective_balance"] = objective_balance
    return ControllerState(
        family="genetic",
        backbone="nsga2",
        generation_index=5,
        evaluation_index=80,
        parent_count=2,
        vector_size=32,
        metadata=metadata,
    )
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_llm_controller.py -v -k "objective_balance"`
Expected: FAIL

- [ ] **Step 4: Implement decision_axes objective balance fields**

In `_build_decision_axes` (line 458), after the existing `route_family_candidates` block (around line 512), before the final `return`, add:

```python
        objective_balance = regime_panel.get("objective_balance", {}) if isinstance(regime_panel, dict) else {}
        objective_balance_pressure = str(objective_balance.get("balance_pressure", "low"))
        preferred_effect = objective_balance.get("preferred_effect")
        peak_improve_candidates: list[str] = []
        gradient_improve_candidates: list[str] = []
        if objective_balance_pressure in ("high", "medium") and isinstance(operator_panel, dict):
            for op_id, op_row in operator_panel.items():
                if not isinstance(op_row, dict):
                    continue
                if str(op_row.get("expected_peak_effect", "")) == "improve":
                    peak_improve_candidates.append(str(op_id))
                if str(op_row.get("expected_gradient_effect", "")) == "improve":
                    gradient_improve_candidates.append(str(op_id))
```

Add these keys to the returned dict:

```python
            "objective_balance_pressure": objective_balance_pressure,
            "preferred_effect": preferred_effect,
            "peak_improve_candidates": peak_improve_candidates,
            "gradient_improve_candidates": gradient_improve_candidates,
```

- [ ] **Step 5: Implement system_prompt objective balance guidance**

In `_build_system_prompt` (line 336), after the `route_family_guidance` block (around line 384) and before the guardrail block, add:

```python
        objective_balance_guidance = self._build_objective_balance_guidance(state, candidate_operator_ids)
        if objective_balance_guidance:
            prompt = f"{prompt} {objective_balance_guidance}"
```

Add a new static method:

```python
    @staticmethod
    def _build_objective_balance_guidance(
        state: ControllerState,
        candidate_operator_ids: Sequence[str],
    ) -> str:
        prompt_panels = state.metadata.get("prompt_panels")
        if not isinstance(prompt_panels, Mapping):
            return ""
        regime_panel = prompt_panels.get("regime_panel")
        if not isinstance(regime_panel, Mapping):
            return ""
        objective_balance = regime_panel.get("objective_balance")
        if not isinstance(objective_balance, Mapping):
            return ""
        pressure = str(objective_balance.get("balance_pressure", "low"))
        if pressure not in ("high", "medium"):
            return ""
        preferred_effect = str(objective_balance.get("preferred_effect") or "")
        stagnant = list(objective_balance.get("stagnant_objectives", []))
        improving = list(objective_balance.get("improving_objectives", []))

        operator_panel = prompt_panels.get("operator_panel", {})
        if not isinstance(operator_panel, Mapping):
            operator_panel = {}
        effect_key = "expected_peak_effect" if preferred_effect == "peak_improve" else "expected_gradient_effect"
        candidates = [
            str(op_id) for op_id in candidate_operator_ids
            if isinstance(operator_panel.get(op_id), Mapping)
            and str(dict(operator_panel[op_id]).get(effect_key, "")) == "improve"
        ]

        if preferred_effect == "peak_improve":
            candidate_text = f" (especially {', '.join(candidates)})" if candidates else ""
            return (
                f"Objective balance alert: temperature_max has stagnated while gradient_rms continues improving. "
                f"Prefer operators with expected_peak_effect=improve{candidate_text} "
                f"over operators that only improve gradient. "
                f"A bounded T_max-focused trial is justified even if it slightly risks gradient_rms."
            )
        if preferred_effect == "gradient_improve":
            candidate_text = f" (especially {', '.join(candidates)})" if candidates else ""
            return (
                f"Objective balance alert: gradient_rms has stagnated while temperature_max continues improving. "
                f"Prefer operators with expected_gradient_effect=improve{candidate_text} "
                f"over operators that only improve peak temperature."
            )
        if preferred_effect == "balanced":
            return (
                "Both objectives have stagnated. Diversify operator selection to break out of the current basin."
            )
        return ""
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `conda run -n msfenicsx pytest tests/optimizers/test_llm_controller.py -v -k "objective_balance"`
Expected: 2 PASSED

- [ ] **Step 7: Run full optimizer test suite**

Run: `conda run -n msfenicsx pytest tests/optimizers/ -v`
Expected: All pass

- [ ] **Step 8: Commit**

```bash
git add optimizers/operator_pool/llm_controller.py tests/optimizers/test_llm_controller.py
git commit -m "feat: add objective balance signal to decision_axes and system_prompt"
```

---

### Task 5: Full regression + integration verification

**Files:** None (verification only)

- [ ] **Step 1: Run full test suite**

Run: `conda run -n msfenicsx pytest -v`
Expected: All pass

- [ ] **Step 2: Run optimizer tests specifically**

Run: `conda run -n msfenicsx pytest tests/optimizers/ -v`
Expected: All pass (should be 160+ tests)

- [ ] **Step 3: Commit spec and plan docs**

```bash
git add docs/superpowers/specs/2026-04-15-objective-balance-signal-design.md docs/superpowers/plans/2026-04-15-objective-balance-signal.md
git commit -m "docs: add objective balance signal spec and implementation plan"
```
