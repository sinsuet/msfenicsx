# Restore GPT Default LLM Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore GPT as the default OpenAI-compatible LLM route, add an explicit `gpt` profile, preserve existing explicit non-GPT profiles, and remove documentation ambiguity across the LLM scenario call chain.

**Architecture:** Keep all s1-s4 LLM scenario specs provider-neutral by continuing to resolve `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL`. The provider registry in `llm/openai_compatible/profiles.yaml` owns default and explicit profile identity; CLI paths continue to overlay the selected profile into the unified runtime variables.

**Tech Stack:** Python, PyYAML, pytest, OpenAI-compatible runtime config, Markdown repository docs.

---

### Task 1: Add failing tests for GPT default and explicit profile support

**Files:**
- Modify: `tests/optimizers/test_llm_profiles.py`
- Modify: `tests/optimizers/test_optimizer_cli.py`
- Modify: `tests/optimizers/test_run_suite.py`

- [ ] Update `test_bundled_profiles_support_default_profile_via_qwen_coding_plan_env` into a GPT default test:

```python
def test_bundled_profiles_support_default_profile_via_gpt_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GPT_PROXY_API_KEY", "bundled-gpt-key")
    monkeypatch.setenv("GPT_PROXY_BASE_URL", "https://gpt.example/v1")

    overlay = load_provider_profile_overlay("default")

    assert overlay == {
        "LLM_API_KEY": "bundled-gpt-key",
        "LLM_BASE_URL": "https://gpt.example/v1",
        "LLM_MODEL": "gpt-5.4",
    }
```

- [ ] Add an explicit GPT profile assertion:

```python
def test_bundled_gpt_profile_uses_gpt_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GPT_PROXY_API_KEY", "bundled-gpt-key")
    monkeypatch.setenv("GPT_PROXY_BASE_URL", "https://gpt.example/v1")

    overlay = load_provider_profile_overlay("gpt")

    assert overlay == {
        "LLM_API_KEY": "bundled-gpt-key",
        "LLM_BASE_URL": "https://gpt.example/v1",
        "LLM_MODEL": "gpt-5.4",
    }
```

- [ ] Change legacy rejection parametrization so `gpt` is no longer rejected:

```python
@pytest.mark.parametrize("profile_id", ["claude", "qwen"])
def test_bundled_profiles_reject_legacy_provider_style_profile_ids(profile_id: str) -> None:
    with pytest.raises(ValueError, match="Unknown LLM profile"):
        load_provider_profile_overlay(profile_id)
```

- [ ] Update CLI/suite default overlay tests to expect `gpt-5.4` where the fake default profile represents the bundled default.

- [ ] Run the focused tests and verify they fail before production changes:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_llm_profiles.py tests/optimizers/test_optimizer_cli.py::test_optimizer_cli_optimize_benchmark_llm_uses_default_profile_overlay_when_runtime_env_missing tests/optimizers/test_optimizer_cli.py::test_optimizer_cli_run_llm_uses_default_profile_when_omitted tests/optimizers/test_run_suite.py::test_run_benchmark_suite_llm_mode_uses_default_profile_overlay_when_runtime_env_missing
```

Expected: profile tests fail because bundled `default` still points to qwen and `gpt` is unknown.

### Task 2: Restore GPT in the bundled provider registry

**Files:**
- Modify: `llm/openai_compatible/profiles.yaml`

- [ ] Replace the `default` mapping with GPT route values and add explicit `gpt`:

```yaml
  default:
    source_api_key_env_var: GPT_PROXY_API_KEY
    source_base_url_env_var: GPT_PROXY_BASE_URL
    model: gpt-5.4
  gpt:
    source_api_key_env_var: GPT_PROXY_API_KEY
    source_base_url_env_var: GPT_PROXY_BASE_URL
    model: gpt-5.4
```

- [ ] Keep `qwen3_6_plus`, `glm_5`, `minimax_m2_5`, `deepseek_v4_flash`, and `gemma4` unchanged.

- [ ] Re-run the focused tests from Task 1; expected: pass.

### Task 3: Add a scenario call-chain consistency test for s1-s4

**Files:**
- Modify: `tests/optimizers/test_llm_profiles.py`

- [ ] Add a test that loads all four LLM specs and asserts they remain provider-neutral and use the same runtime env names:

```python
@pytest.mark.parametrize(
    "spec_path",
    [
        Path("scenarios/optimization/s1_typical_llm.yaml"),
        Path("scenarios/optimization/s2_staged_llm.yaml"),
        Path("scenarios/optimization/s3_scale20_llm.yaml"),
        Path("scenarios/optimization/s4_dense25_llm.yaml"),
    ],
)
def test_paper_facing_llm_specs_use_unified_runtime_provider_env(spec_path: Path) -> None:
    payload = yaml.safe_load(spec_path.read_text(encoding="utf-8"))

    params = payload["operator_control"]["controller_parameters"]

    assert params["provider"] == "openai-compatible"
    assert params["api_key_env_var"] == "LLM_API_KEY"
    assert params["base_url_env_var"] == "LLM_BASE_URL"
    assert params["model_env_var"] == "LLM_MODEL"
```

- [ ] Run it before changing docs; expected: pass, confirming no scenario YAML rewrite is needed.

### Task 4: Update runtime documentation to remove ambiguity

**Files:**
- Modify: `.env.example`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`

- [ ] Add GPT credential placeholders to `.env.example`:

```env
GPT_PROXY_API_KEY=
GPT_PROXY_BASE_URL=https://rust.cat/v1
```

- [ ] Update README LLM section so it says:
  - `default -> GPT_PROXY_* -> gpt-5.4`
  - `gpt -> GPT_PROXY_* -> gpt-5.4`
  - s1-s4 LLM specs all resolve through `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`
  - explicit switches use `run-llm gpt`, `run-llm qwen3_6_plus`, `run-llm glm_5`, `run-llm minimax_m2_5`, `run-llm deepseek_v4_flash`, or `run-llm gemma4`

- [ ] Update `AGENTS.md` and `CLAUDE.md` to match README wording and prevent Codex/Claude sessions from assuming qwen is default.

- [ ] Run focused profile tests again; expected: pass including `.env.example` assertions.

### Task 5: Code review the related call chain and report evidence

**Files to inspect:**
- `optimizers/cli.py`
- `optimizers/run_suite.py`
- `llm/openai_compatible/profile_loader.py`
- `llm/openai_compatible/config.py`
- `scenarios/optimization/s1_typical_llm.yaml`
- `scenarios/optimization/s2_staged_llm.yaml`
- `scenarios/optimization/s3_scale20_llm.yaml`
- `scenarios/optimization/s4_dense25_llm.yaml`

- [ ] Verify `run-llm` still overlays the selected profile into `LLM_*` before `_run_optimize_benchmark`.
- [ ] Verify direct `optimize-benchmark` and suite LLM mode auto-fill missing `LLM_*` from `default` only when env is missing.
- [ ] Verify s1-s4 LLM specs do not hardcode provider-specific env vars.
- [ ] Report the focused test command and result.
