# CLAUDE.md

This file gives Claude Code repository-specific guidance for `msfenicsx`.

## Repository Status

- `main` already contains the clean rebuild baseline.
- The primary paper-facing mainline is `s1_typical`.
- A harder companion benchmark `s2_hard` is active per `docs/superpowers/specs/2026-04-17-s2-hard-design.md`; it shares the semantic shared operator registry and the same `raw / union / llm` ladder as `s1_typical`.
- The active paper-facing optimizer ladder is:
  - `nsga2_raw`
  - `nsga2_union`
  - `nsga2_llm`
- The current controller line uses the semantic shared operator registry implemented for `s1_typical`.
- The active platform is organized around:
  - `core/`
  - `evaluation/`
  - `optimizers/`
  - `llm/`
  - `visualization/`
  - `scenarios/`
  - `tests/`
  - `docs/`

## Current Platform Identity

`msfenicsx` is a clean research platform for:

- 2D thermal dataset generation
- steady conduction with nonlinear radiation-style sink boundaries
- canonical case generation and official FEniCSx baseline solving
- single-case thermal layout optimization

The active canonical object flow is:

`scenario_template -> thermal_case -> thermal_solution -> scenario_runs/ bundle`

The active derived evaluation flow is:

`thermal_case + thermal_solution + evaluation_spec -> evaluation_report`

The active optimizer mainline is:

`s1_typical case -> repair -> cheap constraints -> solve -> single-case evaluation_report -> Pareto search -> manifest-backed optimization bundle + representative solutions`

The implemented paper-facing inputs are:

- `scenarios/templates/s1_typical.yaml`
- `scenarios/evaluation/s1_typical_eval.yaml`
- `scenarios/optimization/s1_typical_raw.yaml`
- `scenarios/optimization/s1_typical_union.yaml`
- `scenarios/optimization/s1_typical_llm.yaml`
- `scenarios/templates/s2_hard.yaml`
- `scenarios/evaluation/s2_hard_eval.yaml`
- `scenarios/optimization/s2_hard_raw.yaml`
- `scenarios/optimization/s2_hard_union.yaml`
- `scenarios/optimization/s2_hard_llm.yaml`
- `scenarios/optimization/profiles/s2_hard_raw.yaml`
- `scenarios/optimization/profiles/s2_hard_union.yaml`

The fixed benchmark decisions are:

- one operating case
- fifteen named components
- all fifteen optimize `x/y` only
- no optimized rotation
- 32 decision variables
- objectives:
  - `summary.temperature_max`
  - `summary.temperature_gradient_rms`
- hard sink-budget constraint:
  - `case.total_radiator_span <= radiator_span_max`
- cheap constraints must run before PDE
- repair must use projection plus local legality restoration

## Architectural Expectations

- Keep `core/` as the kernel for:
  - schema
  - geometry
  - generator
  - solver
  - artifact I/O
  - contracts
  - CLI
- Keep `evaluation/`, `optimizers/`, `llm/`, and `visualization/` as separate top-level layers that consume `core/`.
- Do not add business logic to `scenarios/`; it is for hand-authored inputs.

## Environment And Execution

- Canonical execution context is WSL2 Ubuntu.
- Even if the workspace is opened through `\\wsl$\Ubuntu\home\hymn\msfenicsx`, treat the repo as Linux-first and use `/home/hymn/msfenicsx`.
- Use the `msfenicsx` conda environment for Python, CLI, and tests.
- Prefer: `/home/hymn/miniconda3/bin/conda run -n msfenicsx ...`
- Repository text artifacts should use UTF-8 without BOM.
- Treat terminal-side mojibake from the host bridge as environment noise unless the saved file itself is corrupted.

### Outbound Network / Proxy

- A local mihomo proxy is already provisioned in this WSL instance and managed as a systemd user service.
  - Mixed HTTP+SOCKS endpoint: `http://127.0.0.1:7890`
  - RESTful control: `http://127.0.0.1:9090`
  - Service name: `mihomo.service` (via `systemctl --user`)
  - Status check: `systemctl --user is-active mihomo`
  - Subscription refresh: `~/.local/bin/mihomo-update-sub.sh`
- Default behavior is direct networking. Do not enable shell proxy environment variables for normal repository work.
- Claude's `Bash` calls are non-interactive shells, so `~/.bashrc` proxy toggle helpers (`proxy_on` / `proxy_off`) do not apply automatically. Bash subcommands must opt in explicitly.
- Only add proxy settings inline for explicit outbound tasks such as network search, web lookup, GitHub / Google / `raw.githubusercontent.com` access, or other clearly blocked external resources, for example:
  - `curl -x http://127.0.0.1:7890 https://raw.githubusercontent.com/...`
  - `http_proxy=http://127.0.0.1:7890 https_proxy=http://127.0.0.1:7890 all_proxy=socks5://127.0.0.1:7890 git clone https://github.com/...`
  - `HTTPS_PROXY=http://127.0.0.1:7890 pip install <pkg-from-pypi.org>`
- Do not route through the proxy for:
  - normal local development, tests, solver runs, and artifact rendering
  - loopback / `127.0.0.1` / `localhost`
  - domestic mirrors already configured in the environment (Tsinghua, Aliyun, USTC, etc.)
  - conda/pip/apt operations that already use a domestic mirror
  - normal LLM provider requests that use the configured base URLs in `.env`
- Before a proxy-dependent command, quickly verify the service is up (`ss -ltn | grep 7890` or `systemctl --user is-active mihomo`). If the proxy is unreachable, fall back to a direct attempt and flag the degraded state instead of silently retrying.
- Do not hardcode proxy credentials or endpoints into repository files; the `127.0.0.1:7890` endpoint is a local-only development convenience and must not leak into scenario YAMLs, optimizer specs, solver defaults, or committed agent settings.

### Preferred Commands

Run tests:
```bash
conda run -n msfenicsx pytest -v
```

Run specific test file:
```bash
conda run -n msfenicsx pytest -v tests/optimizers/test_llm_controller.py
```

Validate template:
```bash
conda run -n msfenicsx python -m core.cli.main validate-scenario-template --template scenarios/templates/s1_typical.yaml
```

Generate case:
```bash
conda run -n msfenicsx python -m core.cli.main generate-case --template scenarios/templates/s1_typical.yaml --seed 11 --output-root ./scenario_runs/generated_cases/s1_typical/seed-11
```

Solve case:
```bash
conda run -n msfenicsx python -m core.cli.main solve-case --case ./scenario_runs/generated_cases/s1_typical/seed-11/s1_typical-seed-0011.yaml --output-root ./scenario_runs
```

Evaluate case:
```bash
conda run -n msfenicsx python -m evaluation.cli evaluate-case --case ./scenario_runs/s1_typical/s1_typical-seed-0011/case.yaml --solution ./scenario_runs/s1_typical/s1_typical-seed-0011/solution.yaml --spec scenarios/evaluation/s1_typical_eval.yaml --output ./evaluation_report.yaml --bundle-root ./scenario_runs/s1_typical/s1_typical-seed-0011
```

Optimize (raw/union/llm):
```bash
conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s1_typical_raw.yaml --evaluation-workers 2 --output-root ./scenario_runs/s1_typical/raw-smoke
conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s1_typical_union.yaml --evaluation-workers 2 --output-root ./scenario_runs/s1_typical/union-smoke
conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s1_typical_llm.yaml --evaluation-workers 2 --output-root ./scenario_runs/s1_typical/llm-smoke
```

Run benchmark suite:
```bash
conda run -n msfenicsx python -m optimizers.cli run-benchmark-suite --optimization-spec scenarios/optimization/s1_typical_raw.yaml --optimization-spec scenarios/optimization/s1_typical_union.yaml --optimization-spec scenarios/optimization/s1_typical_llm.yaml --mode raw --mode union --mode llm --benchmark-seed 11 --evaluation-workers 2 --scenario-runs-root ./scenario_runs
```

Render assets (analytics CSV + figures PNG) from an existing run:
```bash
conda run -n msfenicsx python -m optimizers.cli render-assets --run ./scenario_runs/s1_typical/<run_id> [--hires]
```

Compare multiple runs:
```bash
conda run -n msfenicsx python -m optimizers.cli compare-runs --run ./scenario_runs/s1_typical/<run_a> --run ./scenario_runs/s1_typical/<run_b> --output ./compare.json
```

Smoke harness (10×5 budget local check across modes):
```bash
bash scripts/smoke_render_assets.sh
```

Override algorithm budget / skip auto-render (works on `optimize-benchmark` and `run-llm`):
```bash
conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s1_typical_raw.yaml --output-root ./scenario_runs/s1_typical/raw-smoke --population-size 10 --num-generations 5 --skip-render
```

Install LLM dependency:
```bash
conda run -n msfenicsx python -m pip install "openai>=1.70"
```

### LLM Configuration

The active `nsga2_llm` route uses OpenAI-compatible provider profiles:

- `conda run -n msfenicsx python -m optimizers.cli run-llm` defaults to the bundled `default` profile, which points to GPT
- switch providers explicitly with `run-llm claude ...` or `run-llm qwen ...`
- provider profile declarations live in `llm/openai_compatible/profiles.yaml`
- bundled default models are:
  - `gpt -> gpt-5.4`
  - `claude -> claude-sonnet-4-6`
  - `qwen -> qwen3.6-plus`
- the active `scenarios/optimization/s1_typical_llm.yaml` resolves runtime provider identity through:
  - `LLM_API_KEY`
  - `LLM_BASE_URL`
  - `LLM_MODEL`
- repository-root `/home/hymn/msfenicsx/.env` should keep the raw provider credentials:
  - `GPT_PROXY_API_KEY`
  - `GPT_PROXY_BASE_URL=https://rust.cat/v1`
  - `CLAUDE_PROXY_API_KEY`
  - `CLAUDE_PROXY_BASE_URL=https://apiproxy.work/v1`
  - `QWEN_PROXY_API_KEY`
  - `QWEN_PROXY_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`

## Engineering Guardrails

- Read the exact source before editing and preserve precise edit context.
- If a write looks risky because of locking, permissions, or unclear ownership, stop and notify first.
- Never hardcode API keys, tokens, or private credentials.
- Do not silently change important runtime or solver defaults without documenting the change.
- Fix root causes with physically and architecturally defensible changes instead of fake passes or invalid shortcuts.
- Do not repair controller behavior by hardcoding benchmark seeds, scenario IDs, or operator names as one-off policy exceptions.
- Prefer portable optimizer-layer policy mechanisms over benchmark-specific prompt hacks.
- Run the **focused** tests relevant to your change (specific file or subdirectory under `tests/`) before claiming completion. Escalate to the full `conda run -n msfenicsx pytest -v` only when you are genuinely uncertain about cross-module impact — e.g. editing shared contracts in `core/`, shared registries in `optimizers/`, or when focused tests pass but behavior still looks suspicious.
- When modifying optimizer or controller logic, run the specific test file first. Only run the full suite if the change clearly reaches beyond that file's scope or if you cannot convince yourself the blast radius is contained.

## Data And Artifact Rules

- Treat `scenario_template`, `thermal_case`, and `thermal_solution` as the active canonical contracts.
- `s1_typical` is single-case only and must not define `operating_case_profiles`.
- `s1_typical` is a fixed single-case benchmark; do not use multiple benchmark seeds to simulate multiple problem instances.
- Conservative daytime optimizer reruns should prefer `--evaluation-workers 2` or lower, including future `llm` runs.
- Keep evaluation criteria in standalone `evaluation_spec` files instead of adding optimizer metadata to `thermal_case`.
- Keep optimizer search settings and design-variable bounds in standalone `optimization_spec` files.
- Repository-wide backbone defaults belong in `optimizers/algorithm_config.py`.
- Benchmark-specific tuning belongs in `scenarios/optimization/profiles/` and `algorithm.parameters`.
- Active runtime outputs should go to `scenario_runs/`, not source folders.
- Active optimizer runs should write under `scenario_runs/s1_typical/<run_id>/`.
- The canonical paper-facing run layout is:
  - `scenario_runs/s1_typical/<MMDD_HHMM>__<mode_slug>/`
- `mode_slug` must use the stable order: `raw`, `union`, `llm`.
- Mixed-mode runs keep sibling mode directories plus optional `comparison/`.
- Representative solved-case bundles live under:
  - `<mode>/seeds/seed-<n>/representatives/<representative_id>/`
- Representative bundles must preserve:
  - `fields/*.npz`
  - `summaries/field_view.json`
  - `pages/` (reserved directory for downstream rendering; empty by default)
- Run-root dual-write policy for trace artifacts (logging/viz refactor):
  - Flat JSON at run root: `controller_trace.json`, `operator_trace.json`, `llm_metrics.json`
  - Spec-§3.1 JSONL sidecars under `traces/`:
    - `traces/evaluation_events.jsonl`
    - `traces/generation_summary.jsonl`
    - `traces/controller_trace.jsonl`
    - `traces/operator_trace.jsonl`
    - `traces/llm_request_trace.jsonl`
    - `traces/llm_response_trace.jsonl`
    - `traces/llm_reflection_trace.jsonl`
  - Operator trace rows follow §4.3 schema: `decision_id, generation, operator_name, parents, offspring, params_digest, wall_ms`
  - Per-seed `run.yaml` manifest captures mode, seeds, spec paths, population/generation size, wall-clock seconds
- Central rendered assets live beside traces (written by `render-assets`):
  - `analytics/*.csv`
  - `figures/*.png` (hi-res PDF variants when `--hires`)
- Remove temporary scripts, debug files, caches, and one-off intermediate outputs after validation when they are not intended repository state.
- Do not manually edit generated artifacts to change conclusions.

## Testing Expectations

- Maintained tests belong under `tests/`.
- Add or update focused tests for new behavior.
- Run fresh relevant verification before claiming completion.

Current maintained test areas:

- `tests/schema/`
- `tests/geometry/`
- `tests/generator/`
- `tests/solver/`
- `tests/io/`
- `tests/cli/`
- `tests/evaluation/`
- `tests/optimizers/`
- `tests/visualization/`

## Evidence And Reporting Expectations

- Scientific or performance claims must identify the relevant template, case, solver profile, seed, and runtime path or artifact bundle.
- For optimization claims, identify whether evidence comes from one representative point or the Pareto set.
- Keep the decision encoding, evaluation spec, repair, and expensive-evaluation budget matched across comparisons unless a document explicitly defines a different experiment class.
- Describe `nsga2_union` and `nsga2_llm` as using the same mixed action registry with only the controller changed.
- If something is not validated yet, label it as a hypothesis rather than a confirmed result.
- Keep infeasible cases, failed solves, regressions, and anomalies visible in analysis.
- Failure reasons and dominant violations are valid evidence and should remain visible in artifacts when relevant.
- Cheap local `controller_trace` diagnostics are valid pre-live evidence before any new live rerun.

## Documentation Expectations

- For major contract or workflow changes, update:
  - `README.md`
  - relevant docs under `docs/`
  - `CLAUDE.md` when repository guidance changes
  - `AGENTS.md` to keep it in sync
- Keep active docs aligned with implemented reality.
- Treat `CLAUDE.md` as authoritative repository guidance for Claude Code sessions.
- Treat `AGENTS.md` as authoritative repository guidance for Codex sessions.

## Useful References

- `README.md`
- `AGENTS.md`
- `CLAUDE.md`
- `docs/superpowers/specs/2026-03-26-msfenicsx-clean-rebuild-design.md`
- `docs/superpowers/plans/2026-03-26-msfenicsx-clean-rebuild-phase1.md`
- `docs/superpowers/specs/2026-04-02-s1-typical-mainline-reset-design.md`
- `docs/superpowers/plans/2026-04-02-s1-typical-mainline-reset.md`
- `scenarios/templates/s1_typical.yaml`
- `scenarios/evaluation/s1_typical_eval.yaml`
- `scenarios/optimization/s1_typical_raw.yaml`
- `scenarios/optimization/s1_typical_union.yaml`
- `scenarios/optimization/s1_typical_llm.yaml`
- `scenarios/optimization/profiles/s1_typical_raw.yaml`
- `scenarios/optimization/profiles/s1_typical_union.yaml`
- `optimizers/algorithm_config.py`
- `optimizers/drivers/raw_driver.py`
- `optimizers/drivers/union_driver.py`
- `optimizers/problem.py`
- `optimizers/repair.py`
- `optimizers/cheap_constraints.py`
- `optimizers/operator_pool/operators.py`
- `optimizers/operator_pool/domain_state.py`
- `optimizers/artifacts.py`
- `optimizers/render_assets.py`
- `optimizers/compare_runs.py`
- `optimizers/run_manifest.py`
- `optimizers/analytics/` (decisions, loaders, pareto, rollups)
- `optimizers/traces/` (jsonl_writer, operator_trace, correlation, prompt_store)
- `visualization/figures/` (pareto, temperature_field, gradient_field, hypervolume, layout_evolution, operator_heatmap)
- `visualization/style/baseline.py`
- `scripts/smoke_render_assets.sh`
- `llm/openai_compatible/client.py`
- `llm/openai_compatible/profiles.yaml`
- `tests/optimizers/test_raw_driver_matrix.py`
- `tests/optimizers/test_repair.py`
- `tests/optimizers/test_representative_layout.py`
- `tests/optimizers/test_multi_seed_layout.py`
- `tests/visualization/test_render_assets_fixtures.py`
