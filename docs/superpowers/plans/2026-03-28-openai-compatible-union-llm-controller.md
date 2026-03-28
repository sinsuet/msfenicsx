# OpenAI-Compatible Union-LLM Controller Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the first paper-facing `L1` union-`LLM` controller for `NSGA-II`, using an OpenAI-compatible API surface, a fixed hybrid-union action registry, structured controller state, reflective memory, and traceable performance profiles without changing repair, evaluation, or native survival semantics.

**Architecture:** Keep the existing `P0` and `P1` ladder intact. Extend the union controller contract so `llm` runs on the same action registry as `random_uniform`, but route model I/O through a dedicated OpenAI-compatible client boundary under `llm/`, not through optimizer core code. Preserve `NSGA-II` parent selection and survival, enrich the controller state with engineering-regime summaries and operator statistics, and write `LLM`-specific sidecars so mechanism analysis remains reproducible.

**Tech Stack:** Python 3.12, PyYAML, NumPy, `pymoo`, pytest, OpenAI Python SDK, FEniCSx (`dolfinx`, `ufl`, `mpi4py`, `petsc4py`)

---

Spec references:

- `docs/superpowers/specs/2026-03-28-nsga2-hybrid-union-controller-design.md`
- `docs/superpowers/specs/2026-03-28-openai-union-llm-controller-design.md`

Analysis references:

- `docs/reports/R68_msfenicsx_nsga2_union_mechanism_analysis_20260328.md`
- `docs/reports/R69_msfenicsx_llm_controller_literature_and_novelty_report_20260328.md`

Status context:

- pure `NSGA-II` remains the active paper-facing classical baseline
- `P1-union-uniform-nsga2` is implemented and mechanism-analyzed
- the next implementation step is `L1-union-llm-nsga2`
- the first runtime target remains `NSGA-II`
- the controller framework must stay backbone-pluggable even though only `NSGA-II` is wired now
- the API ecosystem is OpenAI-compatible, with official OpenAI as the first validated reference implementation

## File Structure

### Spec And Config Layer

- Modify: `optimizers/validation.py`
  Validate `operator_control.controller_parameters` for `controller=llm`, including provider metadata, capability profile, performance profile, token budget, and fallback controller rules.
- Modify: `optimizers/models.py`
  Keep `OptimizationSpec` round-trippable while preserving nested `controller_parameters`.
- Modify: `optimizers/io.py`
  Continue loading and saving specs/results cleanly with the richer `L1` payloads.
- Modify: `scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1.yaml`
  Replace the placeholder `llm` controller block with a real `controller_parameters` baseline fixture.
- Modify: `tests/optimizers/test_optimizer_io.py`

### LLM Client Boundary

- Modify: `pyproject.toml`
  Add the OpenAI Python SDK dependency.
- Modify: `llm/__init__.py`
  Expose the new client boundary cleanly.
- Create: `llm/openai_compatible/__init__.py`
- Create: `llm/openai_compatible/config.py`
  Provider config, capability profiles, performance profiles, and environment-variable resolution.
- Create: `llm/openai_compatible/schemas.py`
  Structured-output request and response schema helpers.
- Create: `llm/openai_compatible/client.py`
  OpenAI-compatible transport wrapper with `responses_native` and `chat_compatible_json` capability handling.
- Create: `tests/optimizers/test_llm_client.py`

### Controller Decision And Memory Layer

- Create: `optimizers/operator_pool/decisions.py`
  Structured controller decision and reflection-update contracts.
- Modify: `optimizers/operator_pool/state.py`
  Expand the controller-facing state shape beyond the current thin metadata shell.
- Create: `optimizers/operator_pool/state_builder.py`
  Build domain-grounded state payloads from the population, optimization history, controller trace, and operator trace.
- Create: `optimizers/operator_pool/reflection.py`
  Aggregate per-operator statistics, regime tags, and short-term versus long-term memory summaries.
- Create: `optimizers/operator_pool/llm_controller.py`
  Implement the `llm` controller using the OpenAI-compatible client boundary.
- Modify: `optimizers/operator_pool/controllers.py`
  Build controllers from `controller_id + controller_parameters`, not just `controller_id`.
- Modify: `optimizers/operator_pool/random_controller.py`
  Return the shared controller-decision contract so traces can stay uniform.
- Modify: `optimizers/operator_pool/trace.py`
  Add optional rationale, provider, model, profile, retry, and fallback metadata fields without contaminating the optimization result contract.
- Create: `tests/optimizers/test_llm_controller_state.py`
- Create: `tests/optimizers/test_llm_controller.py`

### NSGA-II Union Integration Layer

- Modify: `optimizers/adapters/genetic_family.py`
  Build enriched controller state, call the `LLM` controller, preserve the exact all-native fast path, and attach per-decision metadata for later outcome joins.
- Modify: `optimizers/drivers/union_driver.py`
  Carry `LLM` request/response/reflection sidecars in the run object when present.
- Modify: `optimizers/artifacts.py`
  Write `LLM` sidecars and metrics manifests alongside controller and operator traces.
- Modify: `optimizers/cli.py`
  Keep CLI surface minimal, but ensure `L1` specs flow through artifact writing unchanged.
- Modify: `tests/optimizers/test_operator_pool_adapters.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`

### Documentation

- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/reports/R69_msfenicsx_llm_controller_literature_and_novelty_report_20260328.md`
  Add a short “implemented contract” note once the code exists.

## Task 1: Add The `L1` Controller Config Contract

**Files:**
- Modify: `optimizers/validation.py`
- Modify: `optimizers/models.py`
- Modify: `optimizers/io.py`
- Modify: `scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1.yaml`
- Modify: `tests/optimizers/test_optimizer_io.py`

- [ ] **Step 1: Write the failing contract tests**

Add tests that require:

```python
def test_llm_union_spec_requires_controller_parameters():
    payload = load_optimization_spec(
        "scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1.yaml"
    ).to_dict()
    payload["operator_control"].pop("controller_parameters")
    with pytest.raises(OptimizationValidationError):
        OptimizationSpec.from_dict(payload)
```

```python
def test_llm_union_spec_round_trips_openai_compatible_runtime_profile():
    spec = load_optimization_spec(
        "scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1.yaml"
    )
    params = spec.operator_control["controller_parameters"]
    assert params["provider"] == "openai"
    assert params["capability_profile"] == "responses_native"
    assert params["performance_profile"] == "balanced"
    assert params["model"]
    assert params["max_output_tokens"] > 0
```

- [ ] **Step 2: Run the IO tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_optimizer_io.py -v
```

Expected:

- FAIL because `controller_parameters` are not yet validated or required

- [ ] **Step 3: Implement the minimal config contract**

Implement the minimum rules:

- `operator_control.controller_parameters` is required when `controller == "llm"`
- the block requires:
  - `provider`
  - `model`
  - `capability_profile`
  - `performance_profile`
  - `api_key_env_var`
  - `max_output_tokens`
- `fallback_controller` defaults to `random_uniform` if omitted, but must validate when present
- for non-OpenAI-compatible providers, require either `base_url` or `base_url_env_var`
- keep `random_uniform` specs backward-compatible

- [ ] **Step 4: Update the active `L1` scenario spec**

Add a real baseline fixture such as:

```yaml
operator_control:
  controller: llm
  operator_pool:
    - native_sbx_pm
    - sbx_pm_global
    - local_refine
    - hot_pair_to_sink
    - hot_pair_separate
    - battery_to_warm_zone
    - radiator_align_hot_pair
    - radiator_expand
    - radiator_contract
  controller_parameters:
    provider: openai
    capability_profile: responses_native
    performance_profile: balanced
    model: gpt-5.4
    api_key_env_var: OPENAI_API_KEY
    max_output_tokens: 1024
    temperature: 0.2
    reasoning:
      effort: medium
    retry:
      max_attempts: 2
      timeout_seconds: 45
    memory:
      recent_window: 32
      reflection_interval: 1
    fallback_controller: random_uniform
```

- [ ] **Step 5: Re-run the IO tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_optimizer_io.py -v
```

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add \
  optimizers/validation.py \
  optimizers/models.py \
  optimizers/io.py \
  scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1.yaml \
  tests/optimizers/test_optimizer_io.py
git commit -m "feat: add llm controller config contract"
```

## Task 2: Add OpenAI-Compatible Client Profiles And Structured Output Transport

**Files:**
- Modify: `pyproject.toml`
- Modify: `llm/__init__.py`
- Create: `llm/openai_compatible/__init__.py`
- Create: `llm/openai_compatible/config.py`
- Create: `llm/openai_compatible/schemas.py`
- Create: `llm/openai_compatible/client.py`
- Create: `tests/optimizers/test_llm_client.py`

- [ ] **Step 1: Write the failing client tests**

Add tests that require:

```python
def test_responses_native_client_builds_structured_request(monkeypatch):
    ...
```

```python
def test_chat_compatible_json_client_normalizes_openai_compatible_json_payload(monkeypatch):
    ...
```

```python
def test_client_rejects_operator_ids_outside_requested_registry(monkeypatch):
    ...
```

- [ ] **Step 2: Run the client tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_client.py -v
```

Expected:

- FAIL because the OpenAI-compatible client boundary does not yet exist

- [ ] **Step 3: Add the SDK dependency**

Update `pyproject.toml` with an OpenAI SDK dependency, for example:

```toml
"openai>=1.70",
```

- [ ] **Step 4: Implement the client boundary**

Implement:

- one config loader that resolves:
  - `provider`
  - `base_url`
  - `api_key_env_var`
  - `capability_profile`
  - `performance_profile`
- one transport wrapper that:
  - uses the official OpenAI client
  - supports `base_url` override for compatible endpoints
  - sends structured requests for `responses_native`
  - falls back to repository-side JSON parsing for `chat_compatible_json`
- one schema helper that returns the strict decision-batch schema and validates parsed payloads

- [ ] **Step 5: Re-run the client tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_client.py -v
```

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add \
  pyproject.toml \
  llm/__init__.py \
  llm/openai_compatible/__init__.py \
  llm/openai_compatible/config.py \
  llm/openai_compatible/schemas.py \
  llm/openai_compatible/client.py \
  tests/optimizers/test_llm_client.py
git commit -m "feat: add openai-compatible llm client boundary"
```

## Task 3: Add Rich Controller State And Reflective Memory

**Files:**
- Create: `optimizers/operator_pool/decisions.py`
- Modify: `optimizers/operator_pool/state.py`
- Create: `optimizers/operator_pool/state_builder.py`
- Create: `optimizers/operator_pool/reflection.py`
- Modify: `optimizers/operator_pool/trace.py`
- Create: `tests/optimizers/test_llm_controller_state.py`

- [ ] **Step 1: Write the failing state and memory tests**

Add tests that require:

```python
def test_state_builder_extracts_domain_regime_and_parent_summary():
    ...
```

```python
def test_reflection_memory_aggregates_operator_credit_by_regime():
    ...
```

```python
def test_controller_decision_round_trips_rationale_and_profile_metadata():
    ...
```

- [ ] **Step 2: Run the state tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller_state.py -v
```

Expected:

- FAIL because the richer state, decision, and reflection contracts do not yet exist

- [ ] **Step 3: Implement the richer state contract**

Expand the state layer so it can represent:

- run block:
  - generation index
  - decision index
  - evaluations used and remaining
  - current feasible rate
  - phase label
- parent block:
  - parent vectors
  - dominant parent violations
  - feasibility summaries if available
- archive block:
  - best near-feasible summary
  - best feasible summary
  - Pareto representative summary
- operator-statistics block:
  - usage counts
  - feasible-entry counts
  - feasible-preservation counts
  - average violation deltas
- reflection-memory block:
  - compact helpful-pattern summary
  - compact harmful-pattern summary
- domain-regime block:
  - e.g. `far_infeasible`, `near_feasible`, `hot_dominant`, `cold_dominant`, `geometry_dominant`

- [ ] **Step 4: Keep the trace contracts aligned**

Make sure traces can store:

- `selected_operator_id`
- `phase_label`
- `brief_rationale`
- `provider`
- `model_id`
- `capability_profile`
- `performance_profile`
- `fallback_used`

- [ ] **Step 5: Re-run the state tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller_state.py -v
```

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add \
  optimizers/operator_pool/decisions.py \
  optimizers/operator_pool/state.py \
  optimizers/operator_pool/state_builder.py \
  optimizers/operator_pool/reflection.py \
  optimizers/operator_pool/trace.py \
  tests/optimizers/test_llm_controller_state.py
git commit -m "feat: add llm controller state and memory contracts"
```

## Task 4: Implement The `LLM` Controller And Fallback Logic

**Files:**
- Create: `optimizers/operator_pool/llm_controller.py`
- Modify: `optimizers/operator_pool/controllers.py`
- Modify: `optimizers/operator_pool/random_controller.py`
- Create: `tests/optimizers/test_llm_controller.py`

- [ ] **Step 1: Write the failing controller tests**

Add tests that require:

```python
def test_llm_controller_returns_schema_valid_operator_decision(monkeypatch):
    ...
```

```python
def test_llm_controller_retries_invalid_payload_then_falls_back(monkeypatch):
    ...
```

```python
def test_random_uniform_controller_still_emits_shared_decision_contract():
    ...
```

- [ ] **Step 2: Run the controller tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller.py -v
```

Expected:

- FAIL because `llm` is still `NotImplemented`

- [ ] **Step 3: Implement the controller factory change**

Update the controller factory so:

- `build_controller(...)` accepts controller parameters and optional injected dependencies
- controllers return a structured decision object instead of only a raw operator id
- `random_uniform` continues to work unchanged at the behavior level

- [ ] **Step 4: Implement the `LLM` controller**

Implement the minimum viable `L1` controller:

- single-decision calls first, not batch mode
- structured request built from the richer controller state
- strict semantic validation of the selected operator id
- one retry for semantically invalid but parseable outputs
- fallback to `random_uniform` after policy-defined failure
- compact rationale preserved for traceability

- [ ] **Step 5: Re-run the controller tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_controller.py -v
```

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add \
  optimizers/operator_pool/llm_controller.py \
  optimizers/operator_pool/controllers.py \
  optimizers/operator_pool/random_controller.py \
  tests/optimizers/test_llm_controller.py
git commit -m "feat: implement llm operator controller"
```

## Task 5: Integrate The `LLM` Controller Into The NSGA-II Union Path

**Files:**
- Modify: `optimizers/adapters/genetic_family.py`
- Modify: `optimizers/drivers/union_driver.py`
- Modify: `optimizers/artifacts.py`
- Modify: `optimizers/cli.py`
- Modify: `tests/optimizers/test_operator_pool_adapters.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`

- [ ] **Step 1: Write the failing integration tests**

Add tests that require:

```python
def test_nsga2_union_llm_run_preserves_union_contract_with_mock_llm(monkeypatch):
    ...
```

```python
def test_llm_union_cli_writes_llm_sidecars_and_manifest_entries(tmp_path, monkeypatch):
    ...
```

```python
def test_llm_union_trace_rows_include_rationale_and_profile_metadata(monkeypatch):
    ...
```

- [ ] **Step 2: Run the adapter and CLI tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_operator_pool_adapters.py \
  tests/optimizers/test_optimizer_cli.py -v
```

Expected:

- FAIL because the `LLM` controller cannot yet run through the union adapter and artifact path

- [ ] **Step 3: Integrate the richer state builder into the mating path**

In `optimizers/adapters/genetic_family.py`:

- build controller state from:
  - current parents
  - `problem.history`
  - current trace buffers
  - resolved controller configuration
- preserve:
  - native selection
  - native survival
  - exact all-native fast path
- attach decision metadata so later outcomes can be joined by `evaluation_index` and `decision_index`

- [ ] **Step 4: Add `LLM` sidecars to run artifacts**

Write sidecars such as:

- `llm_request_trace.jsonl`
- `llm_response_trace.jsonl`
- `llm_reflection_trace.jsonl`
- `llm_metrics.json`

And add manifest entries only when the run actually contains them.

- [ ] **Step 5: Re-run the adapter and CLI tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_operator_pool_adapters.py \
  tests/optimizers/test_optimizer_cli.py -v
```

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add \
  optimizers/adapters/genetic_family.py \
  optimizers/drivers/union_driver.py \
  optimizers/artifacts.py \
  optimizers/cli.py \
  tests/optimizers/test_operator_pool_adapters.py \
  tests/optimizers/test_optimizer_cli.py
git commit -m "feat: wire llm controller into nsga2 union runtime"
```

## Task 6: Add Performance Profiles And Reporting Metadata

**Files:**
- Modify: `llm/openai_compatible/config.py`
- Modify: `llm/openai_compatible/client.py`
- Modify: `optimizers/operator_pool/llm_controller.py`
- Modify: `optimizers/artifacts.py`
- Modify: `tests/optimizers/test_llm_client.py`
- Modify: `tests/optimizers/test_llm_controller.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`

- [ ] **Step 1: Write the failing performance-profile tests**

Add tests that require:

```python
def test_performance_profile_controls_reasoning_and_token_budget():
    ...
```

```python
def test_artifacts_record_profile_reasoning_and_token_metadata(tmp_path, monkeypatch):
    ...
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_client.py \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_optimizer_cli.py -v
```

Expected:

- FAIL because `performance_profile`, reasoning settings, and token-budget metadata are not yet consistently plumbed through

- [ ] **Step 3: Implement runtime performance profiles**

Add named runtime profiles such as:

- `fast`
- `balanced`
- `high_reasoning`

Each profile should resolve:

- `capability_profile`
- `model`
- reasoning effort when supported
- `max_output_tokens`
- timeout
- retry budget

- [ ] **Step 4: Log the runtime knobs**

Ensure traces and metrics record:

- provider
- capability profile
- performance profile
- model id
- reasoning effort if used
- configured `max_output_tokens`
- retry counts
- latency and token usage

- [ ] **Step 5: Re-run the focused tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_client.py \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_optimizer_cli.py -v
```

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add \
  llm/openai_compatible/config.py \
  llm/openai_compatible/client.py \
  optimizers/operator_pool/llm_controller.py \
  optimizers/artifacts.py \
  tests/optimizers/test_llm_client.py \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_optimizer_cli.py
git commit -m "feat: add llm runtime performance profiles"
```

## Task 7: Sync Docs And Run Verification

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/reports/R69_msfenicsx_llm_controller_literature_and_novelty_report_20260328.md`

- [ ] **Step 1: Update the active documentation**

Document the implemented truths:

- `P0` remains pure native `NSGA-II`
- `P1` remains union-uniform on the fixed action registry
- `L1` is the same union registry under an `LLM` controller
- the first reference implementation uses the official OpenAI API
- compatible providers such as Qwen, GLM, and MiniMax are supported only through the same OpenAI-compatible contract
- model comparison and performance profiles are internal `L1` experiment factors

- [ ] **Step 2: Run the focused optimizer and controller tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_optimizer_io.py \
  tests/optimizers/test_llm_client.py \
  tests/optimizers/test_llm_controller_state.py \
  tests/optimizers/test_llm_controller.py \
  tests/optimizers/test_operator_pool_adapters.py \
  tests/optimizers/test_optimizer_cli.py -v
```

Expected:

- PASS

- [ ] **Step 3: Run the full optimizer suite**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers -v
```

Expected:

- PASS

- [ ] **Step 4: Run one offline `L1` smoke with a mocked client path**

Run a smoke path that uses the test-injected fake client or monkeypatched controller transport so the end-to-end artifact contract is exercised without live credentials.

Expected:

- bundle written successfully
- `controller_trace.json`
- `operator_trace.json`
- `llm_metrics.json`
- any present `llm_*_trace.jsonl` files

- [ ] **Step 5: Run one live API smoke only if credentials are configured**

Run only if the required environment variables are present, for example:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/panel_four_component_hot_cold_nsga2_union_llm_l1.yaml \
  --output-root ./scenario_runs/optimizations/nsga2_union_llm_l1_smoke
```

Expected:

- `L1` bundle written successfully
- trace and metrics sidecars present

If credentials are absent, record that the live smoke was not run.

- [ ] **Step 6: Run `git diff --check`**

Run:

```bash
cd /home/hymn/msfenicsx
git diff --check
```

Expected:

- clean

- [ ] **Step 7: Commit**

```bash
git add \
  README.md \
  AGENTS.md \
  docs/reports/R69_msfenicsx_llm_controller_literature_and_novelty_report_20260328.md
git commit -m "docs: sync llm controller runtime and experiment guidance"
```
