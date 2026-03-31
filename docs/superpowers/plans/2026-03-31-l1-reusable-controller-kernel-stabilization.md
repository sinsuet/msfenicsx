# L1 Reusable Controller Kernel Stabilization Implementation Plan

Status update (2026-03-31):
- Tasks 1-5 have been implemented inline through the reusable policy kernel, generic progress/evidence state, controller integration, and cheap local trace diagnostics.
- Fresh verification passed with `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers -v` reporting `131 passed, 2 warnings`.
- A cheap real-artifact gate also passed with `/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli analyze-controller-trace --controller-trace scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-window-guardrail-multiseed/seed-17-real-test/controller_trace.json --output scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-window-guardrail-multiseed/seed-17-real-test/controller_trace_summary.json`.
- That historical `seed-17` artifact predates the new phase-tagged metadata, so the summary lands in the `unknown` bucket while still exposing `max_speculative_family_streak=40`; a fresh bounded rerun is still required for phase-attributed `prefeasible` diagnostics.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the current paper-facing `L1` `NSGA-II` union-`LLM` repairs into a reusable optimizer-layer controller-policy kernel that stabilizes pre-feasible search and post-feasible Pareto expansion without benchmark-specific, seed-specific, backbone-specific, or operator-name-specific special cases.

**Architecture:** Keep the validated OpenAI-compatible client boundary, union action registry, repair contract, expensive evaluation contract, budget framing, and native optimizer survival unchanged. Extract a pure controller-policy kernel that consumes compact generic progress and operator-evidence summaries, assigns generic search phases and evidence tiers, applies family-aware anti-collapse and progress-reset logic before the `LLM` call, and exposes cheap local diagnostics so most failures can be caught without rerunning full thermal optimizations.

**Tech Stack:** Python 3.12, pytest, NumPy, JSON/JSONL artifacts, existing OpenAI-compatible SDK boundary, `pymoo`, FEniCSx (`dolfinx`, `ufl`, `mpi4py`, `petsc4py`)

---

Spec references:

- `docs/superpowers/specs/2026-03-28-nsga2-hybrid-union-controller-design.md`
- `docs/superpowers/specs/2026-03-28-openai-union-llm-controller-design.md`

Current-plan references:

- `docs/superpowers/plans/2026-03-31-l1-domain-grounded-controller-state-completion.md`
- `docs/superpowers/plans/2026-03-31-l1-llm-stability-diagnostics-and-repair.md`

Evidence references:

- `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full/2026-03-31-real-test`
- `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full/2026-03-31-domain-grounded-calibrated-window-guardrail-seed11`
- `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-window-guardrail-multiseed/seed-17-real-test`
- `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-window-guardrail-multiseed/seed-23-real-test`
- `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-multiseed/seed-17-real-test`
- `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-multiseed/seed-23-real-test`

Planning guardrails:

- Do not solve the current instability by hardcoding `battery_to_warm_zone`, `hot_pair_separate`, current benchmark seeds, or the active thermal scenario into permanent controller logic.
- Domain summaries may stay benchmark-aware, but the controller-policy kernel itself must remain scenario-agnostic and portable to future multi-scenario and multi-backbone controller studies.
- Do not spend full live runs until deterministic tests and cheap trace diagnostics pass.
- Use the existing `L1` action registry and fairness contract unchanged.

Acceptance gates:

- deterministic policy tests cover both the current best-case and current failure-case controller traces
- the policy kernel can block speculative custom-family collapse without referencing concrete operator names in controller logic
- the local diagnostics utility can flag pre-feasible collapse and no-progress resets from saved trace artifacts without contacting any provider
- bounded live verification must pass on the historically unstable seed before any new full multi-seed rerun
- only then run the matched full `11/17/23` verification ladder

## File Structure

### Policy Kernel Layer

- Create: `optimizers/operator_pool/policy_kernel.py`
  Pure reusable logic for phase detection, evidence scoring, candidate tiering, family-aware anti-collapse, and progress-reset windows.
- Modify: `optimizers/operator_pool/operators.py`
  Add reusable operator metadata such as generic role, family, and exploration class without changing the proposal math.
- Modify: `optimizers/operator_pool/llm_controller.py`
  Delegate pre-LLM candidate shaping and phase policy messaging to the new kernel rather than embedding ad hoc rules inline.
- Create: `tests/optimizers/test_llm_policy_kernel.py`

### Generic Progress And Evidence Layer

- Modify: `optimizers/operator_pool/domain_state.py`
  Add compact, scenario-agnostic progress summaries such as recent no-progress counters and archive-improvement timing.
- Modify: `optimizers/operator_pool/reflection.py`
  Add reusable operator-family and evidence-tier summaries that do not assume one thermal scenario.
- Modify: `optimizers/operator_pool/state_builder.py`
  Build prompt-safe `progress_state`, `operator_family_summary`, and kernel-ready metadata blocks.
- Modify: `tests/optimizers/test_llm_controller_state.py`

### Integration And Prompt Layer

- Modify: `optimizers/operator_pool/trace.py`
  Keep enough controller metadata to explain phase gates, resets, and family-level filtering in later diagnostics.
- Modify: `tests/optimizers/test_llm_controller.py`
- Modify: `tests/optimizers/test_operator_pool_adapters.py`

### Cheap Diagnostics Layer

- Create: `optimizers/operator_pool/diagnostics.py`
  Local artifact analyzers for family collapse, speculative streaks, progress resets, and phase distribution.
- Modify: `optimizers/cli.py`
  Add a cheap trace-analysis command that does not call the provider or rerun expensive evaluations.
- Modify: `tests/optimizers/test_optimizer_cli.py`

### Documentation And Reporting

- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/reports/R69_msfenicsx_llm_controller_literature_and_novelty_report_20260328.md`
- Create: `docs/reports/R70_msfenicsx_l1_reusable_controller_kernel_validation_20260331.md`

## Task 1: Freeze The Failure Modes Into Deterministic Regression Tests

**Files:**
- Create: `tests/optimizers/test_llm_policy_kernel.py`
- Modify: `tests/optimizers/test_llm_controller.py`

- [ ] **Step 1: Write the failing policy-kernel tests**

Add tests that require:

```python
def test_policy_kernel_marks_cold_start_when_no_feasible_and_no_supported_evidence():
    state = _cold_start_state()
    policy = build_policy_snapshot(state, ("native_sbx_pm", "battery_to_warm_zone", "local_refine"))
    assert policy.phase == "cold_start"
    assert "native_sbx_pm" in policy.allowed_operator_ids
```

```python
def test_policy_kernel_blocks_zero_credit_custom_family_collapse():
    state = _seed17_like_prefeasible_collapse_state()
    policy = build_policy_snapshot(state, ("native_sbx_pm", "local_refine", "battery_to_warm_zone", "hot_pair_separate"))
    assert "battery_to_warm_zone" not in policy.allowed_operator_ids
    assert "hot_pair_separate" not in policy.allowed_operator_ids
```

```python
def test_policy_kernel_enters_forced_reset_after_speculative_no_progress_streak():
    state = _prefeasible_no_progress_reset_state()
    policy = build_policy_snapshot(state, ("native_sbx_pm", "sbx_pm_global", "local_refine", "hot_pair_to_sink"))
    assert policy.reset_active is True
    assert policy.allowed_operator_ids == ("native_sbx_pm", "sbx_pm_global", "local_refine")
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_llm_controller.py -v
```

Expected:

- FAIL because the reusable kernel and family-level collapse logic do not exist yet

- [ ] **Step 3: Commit the red tests**

```bash
git add \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_llm_controller.py
git commit -m "test: pin reusable llm policy kernel failure modes"
```

## Task 2: Add Generic Operator Metadata And A Pure Policy Kernel

**Files:**
- Modify: `optimizers/operator_pool/operators.py`
- Create: `optimizers/operator_pool/policy_kernel.py`
- Modify: `tests/optimizers/test_llm_policy_kernel.py`

- [ ] **Step 1: Extend operator metadata without changing proposal behavior**

Add generic metadata such as:

```python
@dataclass(frozen=True, slots=True)
class OperatorBehaviorProfile:
    operator_id: str
    family: str
    role: str
    exploration_class: str
```

Use portable labels like:

- `native_baseline`
- `global_explore`
- `local_refine`
- `speculative_custom`
- `pareto_expand`

Do not encode benchmark names, thermal labels, or seed-specific rules here.

- [ ] **Step 2: Implement the pure policy-kernel helpers**

Implement functions such as:

```python
def detect_search_phase(state: ControllerState) -> str: ...

def score_operator_evidence(state: ControllerState, operator_id: str) -> dict[str, object]: ...

def build_policy_snapshot(
    state: ControllerState,
    candidate_operator_ids: Sequence[str],
) -> PolicySnapshot: ...
```

`PolicySnapshot` should expose:

- `phase`
- `allowed_operator_ids`
- `suppressed_operator_ids`
- `reset_active`
- `reason_codes`
- `candidate_annotations`

- [ ] **Step 3: Run the focused kernel tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_policy_kernel.py -v
```

Expected:

- PASS

- [ ] **Step 4: Commit**

```bash
git add \
  optimizers/operator_pool/operators.py \
  optimizers/operator_pool/policy_kernel.py \
  tests/optimizers/test_llm_policy_kernel.py
git commit -m "feat: add reusable llm policy kernel"
```

## Task 3: Build Generic Progress And Evidence Summaries

**Files:**
- Modify: `optimizers/operator_pool/domain_state.py`
- Modify: `optimizers/operator_pool/reflection.py`
- Modify: `optimizers/operator_pool/state_builder.py`
- Modify: `tests/optimizers/test_llm_controller_state.py`

- [ ] **Step 1: Write the failing progress-state tests**

Add tests that require:

```python
def test_build_controller_state_includes_generic_progress_state():
    state = build_controller_state(...)
    assert state.metadata["progress_state"]["phase"] == "prefeasible_progress"
    assert state.metadata["progress_state"]["recent_no_progress_count"] >= 0
```

```python
def test_summarize_operator_history_includes_family_and_evidence_rollups():
    summary = summarize_operator_history(...)
    assert summary["battery_to_warm_zone"]["evidence_level"] in {"trusted", "supported", "speculative"}
    assert summary["battery_to_warm_zone"]["operator_family"] == "speculative_custom"
```

- [ ] **Step 2: Run the focused state tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller_state.py -v
```

Expected:

- FAIL because generic `progress_state` and family-aware evidence summaries are not available yet

- [ ] **Step 3: Implement the minimal generic summaries**

Add compact state blocks such as:

- `progress_state`
  - `phase`
  - `first_feasible_found`
  - `evaluations_since_first_feasible`
  - `recent_no_progress_count`
  - `recent_best_near_feasible_improvement`
  - `recent_best_feasible_improvement`
- `operator_family_summary`
  - recent selections by family
  - recent trusted versus speculative selections
- `operator_summary[*].evidence_level`
  - `trusted`
  - `supported`
  - `speculative`

Keep these summaries prompt-safe and fixed-size.

- [ ] **Step 4: Re-run the state tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller_state.py -v
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  optimizers/operator_pool/domain_state.py \
  optimizers/operator_pool/reflection.py \
  optimizers/operator_pool/state_builder.py \
  tests/optimizers/test_llm_controller_state.py
git commit -m "feat: add generic progress and evidence summaries"
```

## Task 4: Integrate The Policy Kernel Into The LLM Controller

**Files:**
- Modify: `optimizers/operator_pool/llm_controller.py`
- Modify: `optimizers/operator_pool/trace.py`
- Modify: `tests/optimizers/test_llm_controller.py`

- [ ] **Step 1: Write the failing integration tests**

Add tests that require:

```python
def test_llm_controller_prefeasible_policy_filters_speculative_custom_families():
    decision = controller.select_decision(_seed17_like_prefeasible_collapse_state(), ...)
    assert fake_client.last_kwargs["candidate_operator_ids"] == ("native_sbx_pm", "local_refine")
```

```python
def test_llm_controller_prompt_reports_phase_policy_not_operator_specific_patch():
    controller.select_decision(_prefeasible_reset_state(), ...)
    system_prompt = fake_client.last_kwargs["system_prompt"].lower()
    assert "prefeasible" in system_prompt
    assert "trusted evidence" in system_prompt
    assert "battery_to_warm_zone" not in system_prompt
```

```python
def test_llm_controller_trace_records_policy_reason_codes():
    decision = controller.select_decision(...)
    assert decision.metadata["guardrail_reason_codes"]
```

- [ ] **Step 2: Run the focused controller tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller.py -v
```

Expected:

- FAIL because the controller still owns the policy logic inline and does not expose generic reason codes

- [ ] **Step 3: Implement the minimal controller integration**

Implementation rules:

- shape candidates through `policy_kernel.build_policy_snapshot(...)` before contacting the provider
- serialize phase-aware and evidence-aware guidance into the prompt
- record suppression reasons and reset activation in request and response traces
- keep provider, fallback, repair, evaluation, and survival semantics unchanged

- [ ] **Step 4: Re-run the focused controller tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller.py -v
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  optimizers/operator_pool/llm_controller.py \
  optimizers/operator_pool/trace.py \
  tests/optimizers/test_llm_controller.py
git commit -m "feat: integrate reusable policy kernel into llm controller"
```

## Task 5: Add Cheap Local Diagnostics So Full Runs Are The Last Gate

**Files:**
- Create: `optimizers/operator_pool/diagnostics.py`
- Modify: `optimizers/cli.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`

- [ ] **Step 1: Write the failing diagnostics tests**

Add tests that require:

```python
def test_analyze_controller_trace_reports_speculative_family_collapse(tmp_path):
    summary = analyze_controller_trace(...)
    assert summary["prefeasible"]["max_speculative_family_streak"] >= 4
```

```python
def test_optimizer_cli_analyze_controller_trace_writes_summary_artifact(tmp_path):
    exit_code = main([...])
    assert exit_code == 0
    assert output_path.exists()
```

- [ ] **Step 2: Run the diagnostics tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_optimizer_cli.py -v
```

Expected:

- FAIL because the local diagnostics command does not exist yet

- [ ] **Step 3: Implement the local diagnostics path**

Add a provider-free analyzer that reports:

- phase distribution
- speculative-family streak lengths
- no-progress reset opportunities
- pre-feasible versus post-feasible operator-family mix
- guardrail trigger counts and reason codes

Expose it with a CLI such as:

```bash
python -m optimizers.cli analyze-controller-trace \
  --optimization-result <optimization_result.json> \
  --controller-trace <controller_trace.json> \
  --output <summary.json>
```

- [ ] **Step 4: Re-run the diagnostics tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_optimizer_cli.py -v
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  optimizers/operator_pool/diagnostics.py \
  optimizers/cli.py \
  tests/optimizers/test_optimizer_cli.py
git commit -m "feat: add local controller trace diagnostics"
```

## Task 6: Run The Cheap Verification Ladder Before Any New Full Multi-Seed Run

**Files:**
- No source edits required

- [ ] **Step 1: Run the focused reusable-kernel suite**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_policy_kernel.py \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_llm_controller_state.py \
  tests/optimizers/test_operator_pool_adapters.py \
  tests/optimizers/test_optimizer_cli.py -v
```

Expected:

- PASS

- [ ] **Step 2: Run local diagnostics on the known unstable and known improved artifacts**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli analyze-controller-trace \
  --optimization-result scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-window-guardrail-multiseed/seed-17-real-test/optimization_result.json \
  --controller-trace scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-window-guardrail-multiseed/seed-17-real-test/controller_trace.json \
  --output scenario_runs/optimizations/diagnostics/seed-17-window-guardrail-policy-summary.json
```

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli analyze-controller-trace \
  --optimization-result scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-window-guardrail-multiseed/seed-23-real-test/optimization_result.json \
  --controller-trace scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-window-guardrail-multiseed/seed-23-real-test/controller_trace.json \
  --output scenario_runs/optimizations/diagnostics/seed-23-window-guardrail-policy-summary.json
```

Expected:

- the existing bad trace shows collapse and reset opportunities
- the improved trace shows lower pre-feasible collapse pressure

- [ ] **Step 3: Run one bounded unstable-seed live verification**

Create a temporary seed-17 validation spec with the same action registry and controller path but a smaller generation count, then run:

```bash
/home/hymn/miniconda3/bin/conda run --no-capture-output -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec /tmp/panel_four_component_hot_cold_nsga2_union_llm_l1_gpt54_seed17_prefeasible_check.yaml \
  --output-root scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-prefeasible-check/seed-17
```

Expected:

- no early speculative custom-family monopoly
- native or local families remain visible in the pre-feasible prefix
- controller trace records family-aware suppression and reset reasons

- [ ] **Step 4: Only if Step 3 passes, schedule the full matched reruns**

Do not run the full `11/17/23` ladder until the bounded seed-17 check looks materially healthier than the currently saved failing artifact.

## Task 7: Run The Full Matched Validation Ladder And Write The Report

**Files:**
- Modify: `docs/reports/R69_msfenicsx_llm_controller_literature_and_novelty_report_20260328.md`
- Create: `docs/reports/R70_msfenicsx_l1_reusable_controller_kernel_validation_20260331.md`

- [ ] **Step 1: Run the matched full validation ladder**

Run:

```bash
/home/hymn/miniconda3/bin/conda run --no-capture-output -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1_gpt54_live.yaml \
  --output-root scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full/<new-seed11-run>
```

Then clone the spec to `/tmp` for seeds `17` and `23` as needed and run the same command, matching the existing `raw`, `union_uniform`, and older `L1` evidence paths.

- [ ] **Step 2: Build a three-seed comparison table**

Report at minimum:

- `feasible_rate`
- `first_feasible_eval`
- `pareto_size`
- `request_count`
- `fallback_count`
- `elapsed_seconds_avg`
- pre-feasible family mix
- guardrail and reset counts

- [ ] **Step 3: Update the report docs**

Document:

- what generalized controller-policy kernel was added
- what parts are generic optimizer-layer logic
- what parts remain optional domain-context blocks
- where the method improved and where it still failed
- whether it now beats `raw`, `union_uniform`, and the older compact `L1` on average

- [ ] **Step 4: Commit**

```bash
git add \
  docs/reports/R69_msfenicsx_llm_controller_literature_and_novelty_report_20260328.md \
  docs/reports/R70_msfenicsx_l1_reusable_controller_kernel_validation_20260331.md
git commit -m "docs: report reusable l1 controller kernel validation"
```

## Execution Notes

- Treat `seed 17` and `seed 23` as regression fixtures for controller behavior, not as permanent policy targets.
- If any step appears to require another benchmark-specific exception, stop and redesign the policy abstraction before adding code.
- Prefer adding new pure functions and pure tests before editing the provider-facing `LLM` transport path.
- Preserve the same paper-facing fairness contract: fixed action registry, fixed repair, fixed expensive evaluation loop, fixed survival, controller-only comparison.
