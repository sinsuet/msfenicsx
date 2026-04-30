# CLAUDE.md

This file gives Claude Code repository-specific guidance for `msfenicsx`.

## Writing Language

- Reports, plans, design documents, analysis notes, and other prose deliverables should be written in Simplified Chinese by default.
- Keep necessary technical terms, code identifiers, command names, file paths, schema keys, model/profile IDs, and quoted API fields in their original language when translating would reduce precision.
- This Chinese-first rule applies to future files under `docs/superpowers/specs/`, `docs/superpowers/plans/`, and similar planning/reporting artifacts unless the user explicitly asks for another language.

## Repository Status

- `main` already contains the clean rebuild baseline.
- The current active paper-facing mainline is `s5_aggressive15` through `s7_aggressive25`.
- The primary debugging template is `s5_aggressive15`; use it for controller-sensitive smoke work unless a scale or density check explicitly needs S6/S7.
- `s2_staged` is retained as a historical controller-sensitive companion benchmark, not the active mainline.
- S5/S6/S7 use the shared `primitive_structured` operator substrate for `union` and `llm` and share the same `raw / union / llm` ladder.
- The active paper-facing optimizer ladder is:
  - `nsga2_raw`
  - `nsga2_union`
  - `nsga2_llm`
- Additional algorithm-comparison inputs are raw-only unless a later design explicitly promotes them:
  - `spea2_raw`
  - `moead_raw`
- The current controller line uses `semantic_ranked_pick` for paper-facing S5/S6/S7 `llm` specs.
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

`paper-facing scenario case -> legality policy -> cheap constraints -> solve -> single-case evaluation_report -> Pareto search -> manifest-backed optimization bundle + representative solutions`

The implemented paper-facing inputs are:

- `scenarios/templates/s1_typical.yaml`
- `scenarios/evaluation/s1_typical_eval.yaml`
- `scenarios/optimization/s1_typical_raw.yaml`
- `scenarios/optimization/s1_typical_union.yaml`
- `scenarios/optimization/s1_typical_llm.yaml`
- `scenarios/templates/s2_staged.yaml`
- `scenarios/evaluation/s2_staged_eval.yaml`
- `scenarios/optimization/s2_staged_raw.yaml`
- `scenarios/optimization/s2_staged_union.yaml`
- `scenarios/optimization/s2_staged_llm.yaml`
- `scenarios/optimization/profiles/s2_staged_raw.yaml`
- `scenarios/optimization/profiles/s2_staged_union.yaml`
- `scenarios/templates/s3_scale20.yaml`
- `scenarios/evaluation/s3_scale20_eval.yaml`
- `scenarios/optimization/s3_scale20_raw.yaml`
- `scenarios/optimization/s3_scale20_union.yaml`
- `scenarios/optimization/s3_scale20_llm.yaml`
- `scenarios/optimization/profiles/s3_scale20_raw.yaml`
- `scenarios/optimization/profiles/s3_scale20_union.yaml`
- `scenarios/templates/s4_dense25.yaml`
- `scenarios/evaluation/s4_dense25_eval.yaml`
- `scenarios/optimization/s4_dense25_raw.yaml`
- `scenarios/optimization/s4_dense25_union.yaml`
- `scenarios/optimization/s4_dense25_llm.yaml`
- `scenarios/optimization/profiles/s4_dense25_raw.yaml`
- `scenarios/optimization/profiles/s4_dense25_union.yaml`
- `scenarios/templates/s5_aggressive15.yaml`
- `scenarios/evaluation/s5_aggressive15_eval.yaml`
- `scenarios/optimization/s5_aggressive15_raw.yaml`
- `scenarios/optimization/s5_aggressive15_union.yaml`
- `scenarios/optimization/s5_aggressive15_llm.yaml`
- `scenarios/optimization/s5_aggressive15_spea2_raw.yaml`
- `scenarios/optimization/s5_aggressive15_moead_raw.yaml`
- `scenarios/optimization/profiles/s5_aggressive15_raw.yaml`
- `scenarios/optimization/profiles/s5_aggressive15_union.yaml`
- `scenarios/optimization/profiles/s5_aggressive15_spea2_raw.yaml`
- `scenarios/optimization/profiles/s5_aggressive15_moead_raw.yaml`
- `scenarios/templates/s6_aggressive20.yaml`
- `scenarios/evaluation/s6_aggressive20_eval.yaml`
- `scenarios/optimization/s6_aggressive20_raw.yaml`
- `scenarios/optimization/s6_aggressive20_union.yaml`
- `scenarios/optimization/s6_aggressive20_llm.yaml`
- `scenarios/optimization/s6_aggressive20_spea2_raw.yaml`
- `scenarios/optimization/s6_aggressive20_moead_raw.yaml`
- `scenarios/optimization/profiles/s6_aggressive20_raw.yaml`
- `scenarios/optimization/profiles/s6_aggressive20_union.yaml`
- `scenarios/optimization/profiles/s6_aggressive20_spea2_raw.yaml`
- `scenarios/optimization/profiles/s6_aggressive20_moead_raw.yaml`
- `scenarios/templates/s7_aggressive25.yaml`
- `scenarios/evaluation/s7_aggressive25_eval.yaml`
- `scenarios/optimization/s7_aggressive25_raw.yaml`
- `scenarios/optimization/s7_aggressive25_union.yaml`
- `scenarios/optimization/s7_aggressive25_llm.yaml`
- `scenarios/optimization/s7_aggressive25_spea2_raw.yaml`
- `scenarios/optimization/s7_aggressive25_moead_raw.yaml`
- `scenarios/optimization/profiles/s7_aggressive25_raw.yaml`
- `scenarios/optimization/profiles/s7_aggressive25_union.yaml`
- `scenarios/optimization/profiles/s7_aggressive25_spea2_raw.yaml`
- `scenarios/optimization/profiles/s7_aggressive25_moead_raw.yaml`

The fixed benchmark decisions are:

- one operating case
- fixed named components:
  - S5: 15 components
  - S6: 20 components
  - S7: 25 components
- all components optimize `x/y` only
- no optimized rotation
- scenario-specific decision dimensions:
  - S5: 32 decision variables
  - S6: 42 decision variables
  - S7: 52 decision variables
- objectives:
  - `summary.temperature_max`
  - `summary.temperature_gradient_rms`
- hard sink-budget constraint:
  - `case.total_radiator_span <= radiator_span_max`
- cheap constraints must run before PDE
- paper-facing S5/S6/S7 `raw`, `union`, `llm`, and raw-only algorithm-comparison specs use `projection_plus_local_restore`
- paper-facing S5/S6/S7 `union` and `llm` runs both use the shared `primitive_structured` operator substrate
- paper-facing S5/S6/S7 `llm` specs use `semantic_ranked_pick` with the same controller parameters as the S5 debugging template

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
- When worktrees are needed for this repository, create them under the repo-root `.worktrees/` directory. Do not use `.claude/worktrees/`; keep the location shared with Codex for a single convention.
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
conda run -n msfenicsx python -m core.cli.main validate-scenario-template --template scenarios/templates/s5_aggressive15.yaml
```

Generate case:
```bash
conda run -n msfenicsx python -m core.cli.main generate-case --template scenarios/templates/s5_aggressive15.yaml --seed 11 --output-root ./scenario_runs/generated_cases/s5_aggressive15/seed-11
```

Solve case:
```bash
conda run -n msfenicsx python -m core.cli.main solve-case --case ./scenario_runs/generated_cases/s5_aggressive15/seed-11/s5_aggressive15-seed-0011.yaml --output-root ./scenario_runs
```

Evaluate case:
```bash
conda run -n msfenicsx python -m evaluation.cli evaluate-case --case ./scenario_runs/s5_aggressive15/s5_aggressive15-seed-0011/case.yaml --solution ./scenario_runs/s5_aggressive15/s5_aggressive15-seed-0011/solution.yaml --spec scenarios/evaluation/s5_aggressive15_eval.yaml --output ./evaluation_report.yaml --bundle-root ./scenario_runs/s5_aggressive15/s5_aggressive15-seed-0011
```

Optimize (raw/union/llm):
```bash
conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s5_aggressive15_raw.yaml --evaluation-workers 2 --output-root ./scenario_runs/s5_aggressive15/raw-smoke
conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s5_aggressive15_union.yaml --evaluation-workers 2 --output-root ./scenario_runs/s5_aggressive15/union-smoke
conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s5_aggressive15_llm.yaml --evaluation-workers 2 --output-root ./scenario_runs/s5_aggressive15/llm-smoke
```

Run benchmark suite:
```bash
conda run -n msfenicsx python -m optimizers.cli run-benchmark-suite --optimization-spec scenarios/optimization/s5_aggressive15_raw.yaml --optimization-spec scenarios/optimization/s5_aggressive15_union.yaml --optimization-spec scenarios/optimization/s5_aggressive15_llm.yaml --mode raw --mode union --mode llm --llm-profile default --benchmark-seed 11 --evaluation-workers 2 --scenario-runs-root ./scenario_runs
```

Run S5-S7 512eval matrix block:
```bash
conda run -n msfenicsx python -m optimizers.cli run-benchmark-matrix --matrix-root ./scenario_runs/matrix_512eval_s5_s7 --block-id M1_raw_backbone_512eval
```

Aggregate S5-S7 512eval matrix:
```bash
conda run -n msfenicsx python -m optimizers.cli aggregate-benchmark-matrix --run-index ./scenario_runs/matrix_512eval_s5_s7/run_index.csv --output-root ./scenario_runs/matrix_512eval_s5_s7/aggregate
```

Render assets (analytics CSV + figures PNG) from every completed optimizer run:
```bash
conda run -n msfenicsx python -m optimizers.cli render-assets --run ./scenario_runs/s5_aggressive15/<run_id> [--hires]
```

Compare multiple concrete run roots before reporting comparative results:
```bash
conda run -n msfenicsx python -m optimizers.cli compare-runs --run ./scenario_runs/s5_aggressive15/<run_a> --run ./scenario_runs/s5_aggressive15/<run_b> --output ./scenario_runs/compare_reports/<compare_id>
```

Smoke harness (10×5 budget local check across modes):
```bash
bash scripts/smoke_render_assets.sh
```

Override algorithm budget (works on `optimize-benchmark` and `run-llm`):
```bash
conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s5_aggressive15_raw.yaml --output-root ./scenario_runs/s5_aggressive15/raw-smoke --population-size 10 --num-generations 5
```

`--skip-render` is only for temporary debug runs. If it is used, immediately run `render-assets` on the produced run root before analysis or reporting.

Install LLM dependency:
```bash
conda run -n msfenicsx python -m pip install "openai>=1.70"
```

### LLM Configuration

The active `nsga2_llm` route uses OpenAI-compatible provider profiles:

- `conda run -n msfenicsx python -m optimizers.cli run-llm` defaults to the bundled `default` profile, which points to `gpt-5.4`
- `run-benchmark-suite` uses the same `default` profile for LLM mode unless `--llm-profile <profile>` is provided
- switch models explicitly with profile names such as `run-llm qwen3_6_plus ...`, `run-llm gpt ...`, `run-llm glm_5 ...`, `run-llm minimax_m2_5 ...`, or `run-llm deepseek_v4_flash ...`
- provider profile declarations live in `llm/openai_compatible/profiles.yaml`
- bundled model registry maps:
  - `default -> GPT_PROXY_* -> gpt-5.4`
  - `gpt -> GPT_PROXY_* -> gpt-5.4`
  - `qwen3_6_plus -> QWEN_PROXY_* -> qwen3.6-plus`
  - `glm_5 -> QWEN_PROXY_* -> glm-5`
  - `minimax_m2_5 -> QWEN_PROXY_* -> MiniMax-M2.5`
  - `deepseek_v4_flash -> DEEPSEEK_PROXY_* -> DeepSeek-V4-Flash`
  - `gemma4 -> GEMMA4_* -> gemma-4` as a placeholder until credentials and the exact model id are configured
- the active `scenarios/optimization/s5_aggressive15_llm.yaml` resolves runtime provider identity through:
  - `LLM_API_KEY`
  - `LLM_BASE_URL`
  - `LLM_MODEL`
- repository-root `/home/hymn/msfenicsx/.env` should keep the raw provider credentials:
  - `GPT_PROXY_API_KEY`
  - `GPT_PROXY_BASE_URL`
  - `QWEN_PROXY_API_KEY`
  - `QWEN_PROXY_BASE_URL=https://coding.dashscope.aliyuncs.com/v1`

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
- `s5_aggressive15` is the primary fixed single-case debugging template and must not define `operating_case_profiles`.
- S5/S6/S7 are fixed single-case benchmarks; do not use multiple benchmark seeds to simulate multiple problem instances.
- Conservative daytime optimizer reruns should prefer `--evaluation-workers 2` or lower, including future `llm` runs.
- Keep evaluation criteria in standalone `evaluation_spec` files instead of adding optimizer metadata to `thermal_case`.
- Keep optimizer search settings and design-variable bounds in standalone `optimization_spec` files.
- Repository-wide backbone defaults belong in `optimizers/algorithm_config.py`.
- Benchmark-specific tuning belongs in `scenarios/optimization/profiles/` and `algorithm.parameters`.
- Active runtime outputs should go to `scenario_runs/`, not source folders.
- Active optimizer runs should write under `scenario_runs/<scenario_id>/<run_id>/`.
- Optimizer runs are not complete until `render-assets` has been executed on the final run root. Do not use `--skip-render` for normal benchmark runs; if it is used temporarily, rerun `render-assets` before any analysis or reporting.
- When 2+ concrete run roots are part of the same comparison, also produce a `compare-runs` bundle under `scenario_runs/compare_reports/<compare_id>/` before final reporting.
- The canonical paper-facing run layout is:
  - `scenario_runs/<scenario_id>/<MMDD_HHMM>__<mode_slug>/`
- `mode_slug` must use the stable order: `raw`, `union`, `llm`.
- Mixed-mode runs keep sibling mode directories plus suite-owned `comparisons/` bundles or external `scenario_runs/compare_reports/<compare_id>/` bundles; never revive legacy `comparison/`.
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
- Keep the decision encoding, evaluation spec, repair/canonicalization path, legality policy, operator pool, and expensive-evaluation budget matched across paper-facing `union` / `llm` comparisons unless a document explicitly defines a different experiment class.
- Describe `nsga2_union` and `nsga2_llm` as using the same shared primitive operator substrate; `llm` differs only through its representation-layer controller state, reflection, memory, and soft policy guidance over the same candidate support.
- If something is not validated yet, label it as a hypothesis rather than a confirmed result.
- Keep infeasible cases, failed solves, regressions, and anomalies visible in analysis.
- Failure reasons and dominant violations are valid evidence and should remain visible in artifacts when relevant.
- Cheap local `controller_trace` diagnostics are valid pre-live evidence before any new live rerun.
- For reruns within the same experiment family (for example a budget sweep, a raw/union/llm ladder, or a raw-only algorithm baseline), include the rendered comparison bundle for the closest prior baseline before final reporting so the user does not need to request a second pass.

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
- `docs/superpowers/specs/2026-04-28-s5-aggressive-15-component-benchmark-design.md`
- `docs/superpowers/specs/2026-04-28-s6-aggressive-20-component-benchmark-design.md`
- `docs/superpowers/specs/2026-04-28-s7-aggressive-25-component-benchmark-design.md`
- `docs/superpowers/specs/2026-04-30-llm-semantic-ranker-controller-design.md`
- `docs/superpowers/plans/2026-04-29-s5-s7-512eval-benchmark-matrix.md`
- `scenarios/templates/s1_typical.yaml`
- `scenarios/evaluation/s1_typical_eval.yaml`
- `scenarios/optimization/s1_typical_raw.yaml`
- `scenarios/optimization/s1_typical_union.yaml`
- `scenarios/optimization/s1_typical_llm.yaml`
- `scenarios/optimization/profiles/s1_typical_raw.yaml`
- `scenarios/optimization/profiles/s1_typical_union.yaml`
- `scenarios/templates/s5_aggressive15.yaml`
- `scenarios/evaluation/s5_aggressive15_eval.yaml`
- `scenarios/optimization/s5_aggressive15_raw.yaml`
- `scenarios/optimization/s5_aggressive15_union.yaml`
- `scenarios/optimization/s5_aggressive15_llm.yaml`
- `scenarios/optimization/s5_aggressive15_spea2_raw.yaml`
- `scenarios/optimization/s5_aggressive15_moead_raw.yaml`
- `scenarios/optimization/profiles/s5_aggressive15_raw.yaml`
- `scenarios/optimization/profiles/s5_aggressive15_union.yaml`
- `scenarios/optimization/profiles/s5_aggressive15_spea2_raw.yaml`
- `scenarios/optimization/profiles/s5_aggressive15_moead_raw.yaml`
- `scenarios/templates/s6_aggressive20.yaml`
- `scenarios/evaluation/s6_aggressive20_eval.yaml`
- `scenarios/optimization/s6_aggressive20_raw.yaml`
- `scenarios/optimization/s6_aggressive20_union.yaml`
- `scenarios/optimization/s6_aggressive20_llm.yaml`
- `scenarios/optimization/s6_aggressive20_spea2_raw.yaml`
- `scenarios/optimization/s6_aggressive20_moead_raw.yaml`
- `scenarios/optimization/profiles/s6_aggressive20_raw.yaml`
- `scenarios/optimization/profiles/s6_aggressive20_union.yaml`
- `scenarios/optimization/profiles/s6_aggressive20_spea2_raw.yaml`
- `scenarios/optimization/profiles/s6_aggressive20_moead_raw.yaml`
- `scenarios/templates/s7_aggressive25.yaml`
- `scenarios/evaluation/s7_aggressive25_eval.yaml`
- `scenarios/optimization/s7_aggressive25_raw.yaml`
- `scenarios/optimization/s7_aggressive25_union.yaml`
- `scenarios/optimization/s7_aggressive25_llm.yaml`
- `scenarios/optimization/s7_aggressive25_spea2_raw.yaml`
- `scenarios/optimization/s7_aggressive25_moead_raw.yaml`
- `scenarios/optimization/profiles/s7_aggressive25_raw.yaml`
- `scenarios/optimization/profiles/s7_aggressive25_union.yaml`
- `scenarios/optimization/profiles/s7_aggressive25_spea2_raw.yaml`
- `scenarios/optimization/profiles/s7_aggressive25_moead_raw.yaml`
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
