# OpenAI-Compatible Provider Profile Switching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `run-llm <profile>` command that lets `msfenicsx` switch among multiple OpenAI-compatible providers such as `gpt`, `claude`, and `qwen` using one stable paper-facing LLM optimization spec.

**Architecture:** Keep provider credentials in repository-root `.env`, store provider identity in a narrow `profiles.yaml` registry, and map the selected profile into one unified runtime variable set: `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL`. Extend the OpenAI-compatible config layer so `model_env_var` works with the same precedence rules as `api_key_env_var` and `base_url_env_var`, then add a thin `run-llm` CLI path that temporarily overlays those unified variables and forwards execution into the existing optimization flow.

**Tech Stack:** Python 3.12, pytest, PyYAML, argparse, pathlib, existing `llm/openai_compatible` transport layer, existing optimizer CLI and validation stack

---

Spec reference:

- `docs/superpowers/specs/2026-04-15-openai-compatible-provider-profile-switching-design.md`

Primary implementation guardrails:

- Keep `scenarios/` paper-facing and provider-agnostic.
- Do not duplicate `s1_typical_llm.yaml` per provider.
- Preserve backward compatibility for legacy specs that still use literal `model`.
- Make all missing-profile and missing-credential failures explicit and local.
- Do not rewrite `.env` or mutate optimization spec files at runtime.

## File Structure

### OpenAI-Compatible Runtime Resolution

- Create: `llm/openai_compatible/env.py`
  Shared dotenv and environment resolution helpers for the OpenAI-compatible stack.
- Modify: `llm/openai_compatible/config.py`
  Add `model_env_var` support and switch to the shared env helper.

### Provider Profile Registry

- Create: `llm/openai_compatible/profiles.yaml`
  Hand-authored provider profile registry mapping profile ids to source env var names and default model ids.
- Create: `llm/openai_compatible/profile_loader.py`
  Load and validate provider profiles, then resolve them into the unified runtime overlay.

### Optimizer CLI And Validation

- Modify: `optimizers/cli.py`
  Add `run-llm` and refactor the shared optimize path so both commands use the same execution core.
- Modify: `optimizers/validation.py`
  Accept either literal `model` or `model_env_var` for LLM controller parameters.

### Paper-Facing Spec And Docs

- Modify: `scenarios/optimization/s1_typical_llm.yaml`
  Switch provider identity fields to `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL`.
- Modify: `README.md`
  Document the new provider-profile workflow and `.env` shape.

### Tests

- Modify: `tests/optimizers/test_llm_client.py`
  Cover model resolution precedence and missing-model failures.
- Create: `tests/optimizers/test_llm_profiles.py`
  Cover profile loading, dotenv fallback, and explicit failure cases.
- Modify: `tests/optimizers/test_optimizer_cli.py`
  Cover `run-llm`, environment overlay behavior, and non-LLM spec rejection.
- Modify: `tests/optimizers/test_optimizer_io.py`
  Assert that the active `s1_typical_llm` spec uses unified runtime env vars.

## Task 1: Add Shared Env Helpers And `model_env_var` Support

**Files:**
- Create: `llm/openai_compatible/env.py`
- Modify: `llm/openai_compatible/config.py`
- Modify: `optimizers/validation.py`
- Modify: `tests/optimizers/test_llm_client.py`
- Modify: `tests/optimizers/test_optimizer_io.py`

- [ ] **Step 1: Write the red tests for model resolution**

Add focused tests in `tests/optimizers/test_llm_client.py` that require:

```python
def test_config_resolves_model_from_model_env_var_before_literal(tmp_path: Path) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("LLM_MODEL=qwen3.6-plus\n", encoding="utf-8")
    config = OpenAICompatibleConfig.from_dict(
        {
            "provider": "openai-compatible",
            "model": "gpt-5.4",
            "model_env_var": "LLM_MODEL",
            "capability_profile": "chat_compatible_json",
            "performance_profile": "balanced",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 128,
        }
    )

    assert config.resolve_model(dotenv_path=dotenv_path) == "qwen3.6-plus"
```

```python
def test_config_raises_when_model_and_model_env_var_are_both_missing() -> None:
    config = OpenAICompatibleConfig.from_dict(
        {
            "provider": "openai-compatible",
            "model_env_var": "LLM_MODEL",
            "capability_profile": "chat_compatible_json",
            "performance_profile": "balanced",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 128,
        }
    )

    with pytest.raises(RuntimeError, match="Missing model"):
        config.resolve_model(environ={})
```

- [ ] **Step 2: Write the red validation test for `model_env_var`**

Add a focused validation test that requires an LLM spec with `model_env_var` and no literal `model` to deserialize successfully:

```python
def test_llm_validation_accepts_model_env_var_without_literal_model() -> None:
    payload = _optimization_spec_payload()
    payload["algorithm"]["mode"] = "union"
    payload["operator_control"] = {
        "controller": "llm",
        "operator_pool": ["native_sbx_pm"],
        "controller_parameters": {
            "provider": "openai-compatible",
            "model_env_var": "LLM_MODEL",
            "capability_profile": "chat_compatible_json",
            "performance_profile": "balanced",
            "api_key_env_var": "LLM_API_KEY",
            "base_url_env_var": "LLM_BASE_URL",
            "max_output_tokens": 256,
        },
    }

    spec = OptimizationSpec.from_dict(payload)
    assert spec.operator_control["controller_parameters"]["model_env_var"] == "LLM_MODEL"
```

- [ ] **Step 3: Run the focused tests to confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_client.py \
  tests/optimizers/test_optimizer_io.py -v
```

Expected:

- FAIL because `model_env_var` is not implemented yet and validation still requires literal `model`

- [ ] **Step 4: Implement the shared env helpers and config changes**

Implement:

- `llm/openai_compatible/env.py` with a reusable dotenv loader and helper that resolves a named env var from `environ` first, then `.env`
- `OpenAICompatibleConfig.model_env_var`
- `OpenAICompatibleConfig.resolve_model(...)`
- `OpenAICompatibleConfig.from_dict(...)` so literal `model` becomes optional
- `optimizers/validation.py` so `model` or `model_env_var` is accepted, with a clear failure if both are absent

Keep precedence strict:

- `model_env_var` wins when it resolves to a non-empty value
- otherwise literal `model` is used
- otherwise fail clearly

- [ ] **Step 5: Re-run the focused tests**

Run the same pytest command from Step 3.

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add \
  llm/openai_compatible/env.py \
  llm/openai_compatible/config.py \
  optimizers/validation.py \
  tests/optimizers/test_llm_client.py \
  tests/optimizers/test_optimizer_io.py
git commit -m "feat: add env-driven llm model resolution"
```

## Task 2: Add Provider Profile Registry And Loader

**Files:**
- Create: `llm/openai_compatible/profiles.yaml`
- Create: `llm/openai_compatible/profile_loader.py`
- Create: `tests/optimizers/test_llm_profiles.py`

- [ ] **Step 1: Write the red tests for provider profile loading**

Create `tests/optimizers/test_llm_profiles.py` with focused tests such as:

```python
def test_load_provider_profile_resolves_runtime_overlay_from_dotenv(tmp_path: Path) -> None:
    profiles_path = tmp_path / "profiles.yaml"
    profiles_path.write_text(
        "schema_version: '1.0'\nprofiles:\n  gpt:\n    source_api_key_env_var: GPT_PROXY_API_KEY\n    source_base_url_env_var: GPT_PROXY_BASE_URL\n    model: gpt-5.4\n",
        encoding="utf-8",
    )
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "GPT_PROXY_API_KEY=test-gpt-key\nGPT_PROXY_BASE_URL=https://gpt.example/v1\n",
        encoding="utf-8",
    )

    overlay = load_provider_profile_overlay("gpt", profiles_path=profiles_path, dotenv_path=dotenv_path)

    assert overlay == {
        "LLM_API_KEY": "test-gpt-key",
        "LLM_BASE_URL": "https://gpt.example/v1",
        "LLM_MODEL": "gpt-5.4",
    }
```

```python
def test_load_provider_profile_rejects_unknown_profile(tmp_path: Path) -> None:
    profiles_path = tmp_path / "profiles.yaml"
    profiles_path.write_text("schema_version: '1.0'\nprofiles: {}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Unknown LLM profile"):
        load_provider_profile_overlay("claude2", profiles_path=profiles_path)
```

```python
def test_load_provider_profile_requires_source_base_url(tmp_path: Path) -> None:
    profiles_path = tmp_path / "profiles.yaml"
    profiles_path.write_text(
        "schema_version: '1.0'\nprofiles:\n  qwen:\n    source_api_key_env_var: QWEN_PROXY_API_KEY\n    source_base_url_env_var: QWEN_PROXY_BASE_URL\n    model: qwen3.6-plus\n",
        encoding="utf-8",
    )
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("QWEN_PROXY_API_KEY=qwen-key\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Missing source base URL"):
        load_provider_profile_overlay("qwen", profiles_path=profiles_path, dotenv_path=dotenv_path)
```

- [ ] **Step 2: Run the new profile-loader tests to confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_profiles.py -v
```

Expected:

- FAIL because the registry and loader do not exist yet

- [ ] **Step 3: Implement the profile registry and loader**

Implement:

- `llm/openai_compatible/profiles.yaml` with at least `gpt`, `claude`, and `qwen`
- `load_provider_profile_overlay(...)` in `llm/openai_compatible/profile_loader.py`
- explicit validation for:
  - unknown profile ids
  - missing source API keys
  - missing source base URLs
  - empty or malformed registry payloads

Return only the unified runtime overlay:

```python
{
    "LLM_API_KEY": "...",
    "LLM_BASE_URL": "...",
    "LLM_MODEL": "...",
}
```

- [ ] **Step 4: Re-run the new profile-loader tests**

Run the same pytest command from Step 2.

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  llm/openai_compatible/profiles.yaml \
  llm/openai_compatible/profile_loader.py \
  tests/optimizers/test_llm_profiles.py
git commit -m "feat: add llm provider profile loader"
```

## Task 3: Add `run-llm` And Shared Optimize Execution

**Files:**
- Modify: `optimizers/cli.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`

- [ ] **Step 1: Write the red CLI tests for `run-llm`**

Add focused tests in `tests/optimizers/test_optimizer_cli.py` that require:

```python
def test_optimizer_cli_run_llm_routes_profile_overlay_into_union_execution(tmp_path: Path, monkeypatch) -> None:
    import optimizers.cli as cli_module

    spec_path = _write_small_llm_spec(tmp_path)
    captured: dict[str, str] = {}

    monkeypatch.setattr(
        cli_module,
        "load_provider_profile_overlay",
        lambda profile, **_: {
            "LLM_API_KEY": "switch-key",
            "LLM_BASE_URL": "https://switch.example/v1",
            "LLM_MODEL": "claude-opus-4-6",
        },
    )

    def _fake_run_union_optimization(*args, **kwargs):
        captured["LLM_API_KEY"] = os.environ["LLM_API_KEY"]
        captured["LLM_BASE_URL"] = os.environ["LLM_BASE_URL"]
        captured["LLM_MODEL"] = os.environ["LLM_MODEL"]
        return _fake_union_run(include_llm_sidecars=True)

    monkeypatch.setattr(cli_module, "run_union_optimization", _fake_run_union_optimization)

    exit_code = main(
        [
            "run-llm",
            "claude",
            "--optimization-spec",
            str(spec_path),
            "--output-root",
            str(tmp_path / "run"),
        ]
    )

    assert exit_code == 0
    assert captured["LLM_MODEL"] == "claude-opus-4-6"
```

```python
def test_optimizer_cli_run_llm_rejects_non_llm_specs(tmp_path: Path) -> None:
    spec_path = _write_small_raw_spec(tmp_path)

    with pytest.raises(ValueError, match=\"operator_control.controller='llm'\"):
        main(
            [
                "run-llm",
                "gpt",
                "--optimization-spec",
                str(spec_path),
                "--output-root",
                str(tmp_path / "run"),
            ]
        )
```

- [ ] **Step 2: Run the focused CLI tests to confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_optimizer_cli.py -k "run_llm" -v
```

Expected:

- FAIL because `run-llm` does not exist yet

- [ ] **Step 3: Refactor the CLI and implement `run-llm`**

Refactor `optimizers/cli.py` so:

- the existing `optimize-benchmark` path moves into a shared helper rather than being duplicated
- `run-llm <profile>` loads the optimization spec and rejects non-LLM specs
- `run-llm` resolves the profile overlay through `load_provider_profile_overlay(...)`
- `run-llm` temporarily overlays `os.environ` only for the current process while the existing optimize flow runs
- environment cleanup happens even if optimization raises

Keep the shared optimize behavior identical:

- same case generation
- same evaluation spec resolution
- same artifact writing
- same raw vs union dispatch rules

- [ ] **Step 4: Re-run the focused CLI tests**

Run the same pytest command from Step 2.

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  optimizers/cli.py \
  tests/optimizers/test_optimizer_cli.py
git commit -m "feat: add run-llm provider switching command"
```

## Task 4: Switch The Active LLM Spec To Unified Runtime Variables

**Files:**
- Modify: `scenarios/optimization/s1_typical_llm.yaml`
- Modify: `tests/optimizers/test_optimizer_io.py`

- [ ] **Step 1: Write the red spec assertions**

Update `tests/optimizers/test_optimizer_io.py` so the active LLM spec is required to use the unified runtime env vars:

```python
def test_llm_spec_uses_unified_runtime_provider_env_vars() -> None:
    spec = load_optimization_spec("scenarios/optimization/s1_typical_llm.yaml")

    assert spec.operator_control is not None
    params = spec.operator_control["controller_parameters"]
    assert params["provider"] == "openai-compatible"
    assert params["api_key_env_var"] == "LLM_API_KEY"
    assert params["base_url_env_var"] == "LLM_BASE_URL"
    assert params["model_env_var"] == "LLM_MODEL"
    assert "base_url" not in params
```

- [ ] **Step 2: Run the focused spec tests to confirm they fail**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_optimizer_io.py -k "llm_spec" -v
```

Expected:

- FAIL because the current spec still hardcodes `model` and `base_url`

- [ ] **Step 3: Update the active LLM spec**

Modify `scenarios/optimization/s1_typical_llm.yaml` so the controller parameters use:

```yaml
provider: openai-compatible
api_key_env_var: LLM_API_KEY
base_url_env_var: LLM_BASE_URL
model_env_var: LLM_MODEL
```

Keep these fields intact:

- `capability_profile`
- `performance_profile`
- `max_output_tokens`
- `temperature`
- `reasoning`
- `retry`
- `memory`
- `fallback_controller`

- [ ] **Step 4: Re-run the focused spec tests**

Run the same pytest command from Step 2.

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  scenarios/optimization/s1_typical_llm.yaml \
  tests/optimizers/test_optimizer_io.py
git commit -m "chore: switch active llm spec to runtime env vars"
```

## Task 5: Document The Workflow And Run Final Focused Verification

**Files:**
- Modify: `README.md`
- Verify: `llm/openai_compatible/config.py`
- Verify: `llm/openai_compatible/profile_loader.py`
- Verify: `optimizers/cli.py`
- Verify: `scenarios/optimization/s1_typical_llm.yaml`
- Verify: `tests/optimizers/test_llm_client.py`
- Verify: `tests/optimizers/test_llm_profiles.py`
- Verify: `tests/optimizers/test_optimizer_cli.py`
- Verify: `tests/optimizers/test_optimizer_io.py`

- [ ] **Step 1: Add the user-facing workflow docs**

Update `README.md` with:

- a `.env` example that stores multiple provider credentials
- the `run-llm <profile>` command form
- the fact that the active paper-facing spec stays provider-agnostic

Use concrete examples:

```env
GPT_PROXY_API_KEY=...
GPT_PROXY_BASE_URL=https://gpt.example/v1
CLAUDE_PROXY_API_KEY=...
CLAUDE_PROXY_BASE_URL=https://claude.example/v1
QWEN_PROXY_API_KEY=...
QWEN_PROXY_BASE_URL=https://qwen.example/v1
```

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli run-llm gpt \
  --optimization-spec scenarios/optimization/s1_typical_llm.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s1_typical/<run_id>
```

- [ ] **Step 2: Run the combined focused verification suite**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_llm_client.py \
  tests/optimizers/test_llm_profiles.py \
  tests/optimizers/test_optimizer_cli.py \
  tests/optimizers/test_optimizer_io.py -v
```

Expected:

- PASS

- [ ] **Step 3: Spot-check the new CLI help text**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli --help
```

Expected:

- output includes `run-llm`

- [ ] **Step 4: Commit**

```bash
git add \
  README.md \
  llm/openai_compatible/config.py \
  llm/openai_compatible/profile_loader.py \
  optimizers/cli.py \
  scenarios/optimization/s1_typical_llm.yaml \
  tests/optimizers/test_llm_client.py \
  tests/optimizers/test_llm_profiles.py \
  tests/optimizers/test_optimizer_cli.py \
  tests/optimizers/test_optimizer_io.py
git commit -m "docs: document llm provider profile workflow"
```

## Notes For Execution

- Keep commits small and task-scoped. Do not batch Tasks 1 to 5 into one large commit.
- Avoid touching the unrelated modified files currently present in the workspace.
- If the active workspace remains noisy, prefer executing this plan in an isolated git worktree before touching code files.
- Do not add provider-specific logic anywhere under `scenarios/` beyond the unified runtime env var names in the active LLM spec.
