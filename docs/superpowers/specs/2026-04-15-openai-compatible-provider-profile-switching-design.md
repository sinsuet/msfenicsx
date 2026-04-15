# OpenAI-Compatible Provider Profile Switching Design

> Status: approved design for command-layer switching across multiple OpenAI-compatible providers.

## 1. Context

`msfenicsx` already has an active paper-facing `nsga2_llm` route for `s1_typical`, and that route is intentionally built around the existing OpenAI-compatible controller stack:

- `llm/openai_compatible/`
- `optimizers/operator_pool/llm_controller.py`
- `scenarios/optimization/s1_typical_llm.yaml`

The current implementation can already resolve:

- `api_key_env_var`
- `base_url_env_var`

from either process environment or the repository-root `.env`.

That is enough for a single provider, but it is not the most convenient setup for repeated comparative testing across multiple OpenAI-compatible backends such as:

- `gpt`
- `claude`
- `qwen`

The desired workflow is not to keep editing `.env` or duplicating optimization specs. The desired workflow is to keep all provider credentials in one place and switch providers at the command layer with one stable entrypoint.

## 2. Problem Statement

We want a provider-switching workflow that makes it easy to run the same `nsga2_llm` benchmark against multiple OpenAI-compatible backends while preserving the current paper-facing benchmark contract.

The workflow must satisfy all of the following:

- keep the existing `s1_typical` benchmark and artifact layout intact
- avoid provider-specific duplication of paper-facing optimization specs
- keep provider credentials in `.env` without manually rewriting the active variables each time
- support future addition of new OpenAI-compatible providers without forcing changes to core benchmark specs
- preserve reproducibility by making the selected provider profile explicit in the command being run

## 3. Design Goals

- Add one stable command-layer entrypoint for provider switching.
- Keep `.env` as a store of raw provider credentials rather than a mutable "current provider" file.
- Keep `scenarios/` free of provider-specific switching logic.
- Preserve backward compatibility for existing specs that still use a literal `model`.
- Make configuration failures obvious and local to the missing profile or missing credential.

## 4. Non-Goals

- Do not add Anthropic-native or other non-OpenAI transport support in this change.
- Do not create separate paper-facing specs such as `s1_typical_llm_gpt.yaml` or `s1_typical_llm_qwen.yaml`.
- Do not move benchmark policy, optimization budget, or controller behavior into provider profiles.
- Do not change artifact layout, trace semantics, or the active `scenario_runs/s1_typical/<run_id>/` conventions.
- Do not add business logic to `scenarios/`.

## 5. Design Options Considered

### Option A: Manually edit `.env` before each run

Store one active key and base URL in `.env`, then rewrite them when switching providers.

Pros:

- minimal implementation work

Cons:

- easy to make mistakes
- poor auditability
- does not scale cleanly to more providers
- creates friction for repeated comparative testing

Decision: reject.

### Option B: Maintain one optimization spec per provider

Add files such as:

- `s1_typical_llm_gpt.yaml`
- `s1_typical_llm_claude.yaml`
- `s1_typical_llm_qwen.yaml`

Pros:

- straightforward implementation

Cons:

- duplicates paper-facing configuration
- increases drift risk across specs
- mixes provider identity into scenario-facing assets

Decision: reject.

### Option C: Add command-layer profile switching with unified runtime variables

Store all raw credentials in `.env`, define provider profiles in one registry file, and add a thin CLI entrypoint that maps a selected profile onto a single runtime variable set before calling the existing optimization flow.

Pros:

- easiest day-to-day workflow
- scales cleanly as more OpenAI-compatible providers are added
- keeps benchmark specs stable
- makes the selected provider explicit in the command invocation

Cons:

- requires a small compatibility extension for environment-driven model selection
- adds one thin launcher path to the optimizer CLI

Decision: select this option.

## 6. Selected Design

### 6.1 Command-Layer Switching Is The Primary User Interface

Provider switching should happen through a new optimizer CLI subcommand:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli run-llm gpt \
  --optimization-spec scenarios/optimization/s1_typical_llm.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s1_typical/0415_1200__llm-gpt
```

Equivalent invocations for other providers should look the same:

```bash
... python -m optimizers.cli run-llm claude ...
... python -m optimizers.cli run-llm qwen ...
```

The only switching input is the selected profile id.

### 6.2 `.env` Stores Raw Provider Credentials Only

The repository-root `.env` should store the raw credentials and endpoints for every provider that may be used:

```env
GPT_PROXY_API_KEY=...
GPT_PROXY_BASE_URL=...

CLAUDE_PROXY_API_KEY=...
CLAUDE_PROXY_BASE_URL=...

QWEN_PROXY_API_KEY=...
QWEN_PROXY_BASE_URL=...
```

`.env` should not act as a mutable file that indicates the currently selected provider.

### 6.3 Runtime Resolution Uses One Unified Variable Set

The active optimization spec should resolve provider identity through one stable runtime interface:

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`

The `run-llm` subcommand should:

1. load the selected provider profile
2. resolve the profile's source credential variables from process environment or `.env`
3. create a process-local environment overlay for:
   - `LLM_API_KEY`
   - `LLM_BASE_URL`
   - `LLM_MODEL`
4. call the existing optimization flow without rewriting `.env` or editing the spec file

This keeps the launcher path thin and deterministic.

### 6.4 Provider Profiles Stay Narrow

Provider profiles should live in:

- `llm/openai_compatible/profiles.yaml`

The file should define only provider identity and transport selection data:

```yaml
schema_version: "1.0"
profiles:
  gpt:
    source_api_key_env_var: GPT_PROXY_API_KEY
    source_base_url_env_var: GPT_PROXY_BASE_URL
    model: gpt-5.4
  claude:
    source_api_key_env_var: CLAUDE_PROXY_API_KEY
    source_base_url_env_var: CLAUDE_PROXY_BASE_URL
    model: claude-sonnet-4
  qwen:
    source_api_key_env_var: QWEN_PROXY_API_KEY
    source_base_url_env_var: QWEN_PROXY_BASE_URL
    model: qwen-max
```

Profiles should not contain:

- optimization budget
- reasoning settings
- retry policy
- controller prompt policy
- benchmark-specific tuning

Those remain the responsibility of the optimization spec and related controller configuration.

### 6.5 The Active Spec Stays Paper-Facing And Provider-Agnostic

The paper-facing `s1_typical` LLM spec should stay focused on benchmark and controller configuration, not provider identity.

Its controller parameters should move toward a provider-agnostic runtime interface:

- `provider: openai-compatible`
- `api_key_env_var: LLM_API_KEY`
- `base_url_env_var: LLM_BASE_URL`
- `model_env_var: LLM_MODEL`

These fields should remain in the spec:

- `capability_profile`
- `performance_profile`
- `max_output_tokens`
- `temperature`
- `reasoning`
- `retry`
- `memory`
- `fallback_controller`

This keeps provider selection orthogonal to paper-facing experimental policy.

## 7. Concrete File-Level Changes

### `optimizers/cli.py`

Add a new `run-llm` subcommand that:

- accepts a required positional `profile`
- accepts the same operational arguments needed to run the current benchmark flow
- resolves provider profile inputs
- forwards execution into the existing optimization path

`run-llm` should reject non-LLM optimization specs with a direct error.

### `llm/openai_compatible/profiles.yaml`

Add a small registry of provider profiles.

The registry should be hand-authored, checked into the repository, and stable enough to support repeatable benchmark usage.

### `llm/openai_compatible/profile_loader.py`

Add a focused helper that:

- loads `profiles.yaml`
- validates the requested profile id
- resolves source credential variables from process environment or repository-root `.env`
- returns the unified runtime mapping for:
  - `LLM_API_KEY`
  - `LLM_BASE_URL`
  - `LLM_MODEL`

If helpful, the existing dotenv parsing helper may be extracted or shared so profile loading and client config resolution use the same precedence rules.

### `llm/openai_compatible/config.py`

Extend the config contract to support `model_env_var` in the same spirit as:

- `api_key_env_var`
- `base_url_env_var`

Resolution behavior should be:

- if `model_env_var` is set and resolves to a non-empty value, use it
- otherwise fall back to literal `model` if present
- if neither exists, fail clearly

### `optimizers/validation.py`

Update LLM controller validation so that:

- `api_key_env_var` remains required
- `model` or `model_env_var` must be present
- if `base_url_env_var` is used, it remains validated as text

This preserves legacy compatibility while supporting the new provider-switching path.

### `scenarios/optimization/s1_typical_llm.yaml`

Update the active paper-facing spec to use the unified runtime variable names for provider selection.

The spec should not be duplicated per provider.

## 8. Runtime Flow

The selected execution flow for `run-llm` is:

1. parse CLI arguments
2. load the optimization spec
3. verify that the spec uses `operator_control.controller: llm`
4. load the requested provider profile
5. resolve source key and base URL from environment or `.env`
6. assemble the unified runtime variable overlay
7. execute the existing optimization flow under that overlay

No generated artifacts should change shape as a result of this launcher path. The run should still emit normal optimizer artifacts under the user-supplied output root.

## 9. Error Handling

Failures should be immediate and explicit.

Representative error messages:

- `Unknown LLM profile 'claude2'. Available profiles: gpt, claude, qwen.`
- `Missing source API key env var 'CLAUDE_PROXY_API_KEY' for profile 'claude'.`
- `Missing source base URL env var 'QWEN_PROXY_BASE_URL' for profile 'qwen'.`
- `Optimization spec requires LLM model, but neither 'model' nor 'model_env_var' is configured.`
- `run-llm requires an optimization spec with operator_control.controller='llm'.`

The launcher should not silently fall back to a different provider profile or a different credential source.

## 10. Backward Compatibility

Existing specs that define a literal `model` should continue to work.

Backward-compatible rules:

- legacy specs may keep `model: ...`
- new specs may use `model_env_var: ...`
- if both exist, `model_env_var` wins

This allows the repository to add command-layer switching without breaking existing tests or older experimental assets that still use literal models.

## 11. Testing Plan

Add or update focused tests for the following behaviors:

### 11.1 Profile Loading

Create coverage that proves:

- the requested profile is loaded correctly
- source credential variables resolve from environment or `.env`
- the unified runtime mapping is correct

### 11.2 Missing Profile And Missing Credential Failures

Create coverage that proves:

- unknown profile ids fail clearly
- missing source API keys fail clearly
- missing source base URLs fail clearly

### 11.3 Model Resolution

Create coverage that proves:

- `model_env_var` resolves correctly
- `model_env_var` overrides literal `model`
- missing `model` plus missing `model_env_var` fails clearly

### 11.4 CLI Integration

Create coverage that proves:

- `run-llm` routes through the existing optimization workflow
- `run-llm` rejects non-LLM specs
- provider selection is applied without modifying the optimization spec file itself

Likely test touchpoints include:

- `tests/optimizers/test_optimizer_cli.py`
- `tests/optimizers/test_llm_client.py`
- a new focused test module for profile loading if that keeps responsibilities clearer

## 12. Migration Plan

Implementation should proceed in this order:

1. add `model_env_var` support in config resolution and validation
2. add provider-profile loading support
3. add the `run-llm` CLI entrypoint
4. update `scenarios/optimization/s1_typical_llm.yaml` to use unified runtime variable names
5. add focused tests
6. update relevant docs and usage examples

This keeps compatibility in place while the new command path is introduced.

## 13. Documentation Expectations

Implementation of this design should update:

- `README.md`
- relevant optimizer or LLM workflow docs under `docs/`

The documentation should make two usage patterns explicit:

- direct legacy spec execution for existing setups
- recommended provider-switching execution through `run-llm`

## 14. Success Criteria

This design is successful when:

- a user can keep multiple provider credentials in one `.env`
- a user can switch providers with `run-llm <profile>`
- the active paper-facing LLM spec no longer needs provider-specific duplication
- adding a new OpenAI-compatible backend requires only:
  - adding credentials to `.env`
  - adding one provider profile entry
- normal `nsga2_llm` artifacts and traces continue to use the existing benchmark layout
