# AGENTS.md

This file gives Codex-style agents repository-specific guidance for `msfenicsx`.

## Repository Status

- `main` already contains the clean rebuild baseline.
- The active paper-facing mainlines are `s1_typical`, `s2_staged`, `s3_scale20`, and `s4_dense25`.
- `s2_staged` is the current controller-sensitive S2 companion benchmark. `s3_scale20` and `s4_dense25` are the 20-component scale and 25-component dense companions. They share the same `raw / union / llm` ladder as `s1_typical`.
- The active paper-facing optimizer ladder is:
  - `nsga2_raw`
  - `nsga2_union`
  - `nsga2_llm`
- Additional algorithm-comparison inputs are raw-only unless a later design explicitly promotes them:
  - `spea2_raw`
  - `cmopso_raw`
  - `moead_raw` backup
- The active optimizer ladder uses a matched paper-facing substrate:
  - `raw`: native backbone + clean legality policy
  - `union`: primitive operator registry + random controller + clean legality policy
  - `llm`: same primitive operator registry + LLM representation-layer controller + same clean legality policy
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
- `scenarios/optimization/s1_typical_spea2_raw.yaml`
- `scenarios/optimization/s1_typical_cmopso_raw.yaml`
- `scenarios/optimization/s1_typical_moead_raw.yaml`
- `scenarios/optimization/profiles/s1_typical_raw.yaml`
- `scenarios/optimization/profiles/s1_typical_union.yaml`
- `scenarios/optimization/profiles/s1_typical_spea2_raw.yaml`
- `scenarios/optimization/profiles/s1_typical_cmopso_raw.yaml`
- `scenarios/optimization/profiles/s1_typical_moead_raw.yaml`
- `scenarios/templates/s2_staged.yaml`
- `scenarios/evaluation/s2_staged_eval.yaml`
- `scenarios/optimization/s2_staged_raw.yaml`
- `scenarios/optimization/s2_staged_union.yaml`
- `scenarios/optimization/s2_staged_llm.yaml`
- `scenarios/optimization/s2_staged_spea2_raw.yaml`
- `scenarios/optimization/s2_staged_cmopso_raw.yaml`
- `scenarios/optimization/s2_staged_moead_raw.yaml`
- `scenarios/optimization/profiles/s2_staged_raw.yaml`
- `scenarios/optimization/profiles/s2_staged_union.yaml`
- `scenarios/optimization/profiles/s2_staged_spea2_raw.yaml`
- `scenarios/optimization/profiles/s2_staged_cmopso_raw.yaml`
- `scenarios/optimization/profiles/s2_staged_moead_raw.yaml`
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

The fixed benchmark decisions are:

- one operating case
- fixed named components:
  - S1/S2: 15 components
  - S3: 20 components
  - S4: 25 components
- all components optimize `x/y` only
- no optimized rotation
- scenario-specific decision dimensions:
  - S1/S2: 32 decision variables
  - S3: 42 decision variables
  - S4: 52 decision variables
- objectives:
  - `summary.temperature_max`
  - `summary.temperature_gradient_rms`
- hard sink-budget constraint:
  - `case.total_radiator_span <= radiator_span_max`
- cheap constraints must run before PDE
- paper-facing `union` and `llm` runs both use minimal canonicalization; `llm` may use reflection, memory, and soft policy guidance as representation-layer controller context over the same candidate support

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
- Even if the workspace is opened through `\\wsl$\\Ubuntu\\home\\hymn\\msfenicsx`, agents should treat the repo as Linux-first and use `/home/hymn/msfenicsx`.
- When worktrees are needed for this repository, create them under the repo-root `.worktree/` directory. Do not use `.claude/worktrees/`; keep the location shared with Claude and Codex for a single convention.
- Use the `msfenicsx` conda environment for Python, CLI, and tests.
- Prefer:
  - `/home/hymn/miniconda3/bin/conda run -n msfenicsx ...`
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
- Only add proxy settings inline for explicit outbound tasks such as network search, web lookup, GitHub / Google / `raw.githubusercontent.com` access, or other clearly blocked external resources.
- Do not route through the proxy for:
  - normal local development, tests, solver runs, and artifact rendering
  - loopback / `127.0.0.1` / `localhost`
  - domestic mirrors already configured in the environment (Tsinghua, Aliyun, USTC, etc.)
  - conda/pip/apt operations that already use a domestic mirror
  - normal LLM provider requests that use the configured base URLs in `.env`
- When a proxy is needed, prepend it on the specific command instead of enabling it globally, for example:
  - `curl -x http://127.0.0.1:7890 https://raw.githubusercontent.com/...`
  - `http_proxy=http://127.0.0.1:7890 https_proxy=http://127.0.0.1:7890 all_proxy=socks5://127.0.0.1:7890 git clone https://github.com/...`
  - `HTTPS_PROXY=http://127.0.0.1:7890 pip install <pkg-from-pypi.org>`
- Before a proxy-dependent command, quickly verify the service is up (`ss -ltn | grep 7890` or `systemctl --user is-active mihomo`). If the proxy is unreachable, fall back to a direct attempt and flag the degraded state instead of silently retrying.
- Do not hardcode proxy credentials or endpoints into repository files; the `127.0.0.1:7890` endpoint is a local-only development convenience and must not leak into scenario YAMLs, optimizer specs, solver defaults, or committed agent settings.

Preferred commands:

- `conda run -n msfenicsx pytest -v`
- `conda run -n msfenicsx python -m core.cli.main validate-scenario-template --template scenarios/templates/s1_typical.yaml`
- `conda run -n msfenicsx python -m core.cli.main generate-case --template scenarios/templates/s1_typical.yaml --seed 11 --output-root ./scenario_runs/generated_cases/s1_typical/seed-11`
- `conda run -n msfenicsx python -m core.cli.main solve-case --case ./scenario_runs/generated_cases/s1_typical/seed-11/s1_typical-seed-0011.yaml --output-root ./scenario_runs`
- `conda run -n msfenicsx python -m evaluation.cli evaluate-case --case ./scenario_runs/s1_typical/s1_typical-seed-0011/case.yaml --solution ./scenario_runs/s1_typical/s1_typical-seed-0011/solution.yaml --spec scenarios/evaluation/s1_typical_eval.yaml --output ./evaluation_report.yaml --bundle-root ./scenario_runs/s1_typical/s1_typical-seed-0011`
- `conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s1_typical_raw.yaml --evaluation-workers 2 --output-root ./scenario_runs/s1_typical/raw-smoke`
- `conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s1_typical_union.yaml --evaluation-workers 2 --output-root ./scenario_runs/s1_typical/union-smoke`
- `conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s1_typical_llm.yaml --evaluation-workers 2 --output-root ./scenario_runs/s1_typical/llm-smoke`
- Raw-only algorithm comparisons should be run as standalone raw roots, then compared with `compare-runs`; do not add `spea2/cmopso/moead` as `union` or `llm` suite modes unless a later design explicitly promotes them.
- `conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s1_typical_spea2_raw.yaml --evaluation-workers 2 --output-root ./scenario_runs/s1_typical/spea2-raw-smoke`
- `conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s1_typical_cmopso_raw.yaml --evaluation-workers 2 --output-root ./scenario_runs/s1_typical/cmopso-raw-smoke`
- `conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s1_typical_moead_raw.yaml --evaluation-workers 2 --output-root ./scenario_runs/s1_typical/moead-raw-smoke`
- `conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s2_staged_spea2_raw.yaml --evaluation-workers 2 --output-root ./scenario_runs/s2_staged/spea2-raw-smoke`
- `conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s2_staged_cmopso_raw.yaml --evaluation-workers 2 --output-root ./scenario_runs/s2_staged/cmopso-raw-smoke`
- `conda run -n msfenicsx python -m optimizers.cli optimize-benchmark --optimization-spec scenarios/optimization/s2_staged_moead_raw.yaml --evaluation-workers 2 --output-root ./scenario_runs/s2_staged/moead-raw-smoke`
- `conda run -n msfenicsx python -m optimizers.cli run-benchmark-suite --optimization-spec scenarios/optimization/s1_typical_raw.yaml --optimization-spec scenarios/optimization/s1_typical_union.yaml --optimization-spec scenarios/optimization/s1_typical_llm.yaml --mode raw --mode union --mode llm --benchmark-seed 11 --evaluation-workers 2 --scenario-runs-root ./scenario_runs` (auto-writes suite-owned `comparisons/` when 2+ modes participate)
- `conda run -n msfenicsx python -m optimizers.cli replay-llm-trace --optimization-spec scenarios/optimization/s1_typical_llm.yaml --request-trace ./scenario_runs/s1_typical/<run_id>/llm/seeds/seed-11/traces/llm_request_trace.jsonl --output ./scenario_runs/s1_typical/<run_id>/llm/reports/<summary>.json`
- `conda run -n msfenicsx python -m optimizers.cli analyze-controller-trace --controller-trace ./scenario_runs/s1_typical/<run_id>/llm/seeds/seed-11/traces/controller_trace.jsonl --output ./scenario_runs/s1_typical/<run_id>/llm/reports/<summary>.json`
- `conda run -n msfenicsx python -m optimizers.cli render-assets --run ./scenario_runs/s1_typical/<run_id> [--hires]` (accepts a suite root, a mode root, or a concrete single-mode seed run root)
- `conda run -n msfenicsx python -m optimizers.cli compare-runs --run ./scenario_runs/s1_typical/<run_a> --run ./scenario_runs/s1_typical/<run_b> --output ./scenario_runs/compare_reports/<compare_id>` (accepts only concrete single-mode run roots and must write outside source runs)
- `bash scripts/smoke_render_assets.sh` (10×5 local smoke harness covering raw/union/llm + render-assets + compare-runs)
- Budget / render overrides (work on `optimize-benchmark`, `run-llm`, and `run-benchmark-suite`): `--population-size`, `--num-generations`, `--skip-render`
- `conda run -n msfenicsx python -m pip install "openai>=1.70"`

The active `nsga2_llm` route currently uses OpenAI-compatible model profiles:

- `conda run -n msfenicsx python -m optimizers.cli run-llm` defaults to the bundled `default` profile, which points to `qwen3.6-plus`
- switch models explicitly with profile names such as `run-llm glm_5 ...`, `run-llm minimax_m2_5 ...`, or `run-llm deepseek_v4_flash ...`
- model profile declarations live in `llm/openai_compatible/profiles.yaml`
- bundled coding-plan route models share `QWEN_PROXY_API_KEY` and `QWEN_PROXY_BASE_URL`:
  - `qwen3_6_plus -> qwen3.6-plus`
  - `glm_5 -> glm-5`
  - `minimax_m2_5 -> MiniMax-M2.5`
- non-coding-plan profiles use model-named env pairs:
  - `deepseek_v4_flash -> DEEPSEEK_PROXY_API_KEY / DEEPSEEK_PROXY_BASE_URL -> DeepSeek-V4-Flash`
  - `gemma4 -> GEMMA4_API_KEY / GEMMA4_BASE_URL -> gemma-4` (placeholder until credentials and exact model id are configured)
- the active `scenarios/optimization/s1_typical_llm.yaml` resolves runtime provider identity through:
  - `LLM_API_KEY`
  - `LLM_BASE_URL`
  - `LLM_MODEL`
- repository-root `/home/hymn/msfenicsx/.env` should keep the raw provider credentials:
  - `QWEN_PROXY_API_KEY`
  - `QWEN_PROXY_BASE_URL=https://coding.dashscope.aliyuncs.com/v1`
  - `DEEPSEEK_PROXY_API_KEY`
  - `DEEPSEEK_PROXY_BASE_URL=https://llmapi.paratera.com/v1`
  - `GEMMA4_API_KEY`
  - `GEMMA4_BASE_URL`

## Engineering Guardrails

- Read the exact source before editing and preserve precise edit context.
- If a write looks risky because of locking, permissions, or unclear ownership, stop and notify first.
- Never hardcode API keys, tokens, or private credentials.
- Do not silently change important runtime or solver defaults without documenting the change.
- Fix root causes with physically and architecturally defensible changes instead of fake passes or invalid shortcuts.
- Do not repair controller behavior by hardcoding benchmark seeds, scenario IDs, or operator names as one-off policy exceptions.
- Prefer portable optimizer-layer policy mechanisms over benchmark-specific prompt hacks.

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
- Single solved-case bundles written by `solve-case` should keep `fields/*.npz` + `summaries/field_view.json` and render `figures/layout.png`, `figures/temperature_field.png`, and `figures/gradient_field.png`.
- Active optimizer runs should write under `scenario_runs/<scenario_id>/<run_id>/`.
- The canonical paper-facing run layout is:
  - `scenario_runs/<scenario_id>/<MMDD_HHMM>__<mode_slug>/`
- `mode_slug` must use the stable order:
  - `raw`
  - `union`
  - `llm`
- Suite-owned comparisons live only under:
  - single-seed suite: `<suite_root>/comparisons/`
  - multi-seed suite: `<suite_root>/comparisons/by_seed/seed-<n>/` and `<suite_root>/comparisons/aggregate/`
- `by_seed/seed-<n>/` means same benchmark seed across modes; `aggregate/` is the across-seeds rollup layer for those same modes.
- `aggregate/` may exist for any multi-seed suite with `N>=2`; keep the wording descriptive unless the bundle has `N>=3` seeds.
- Standalone `compare-runs` accepts only concrete single-mode run roots and must write an external bundle outside all source run roots.
- Never revive legacy `comparison/`.
- Representative solved-case bundles live under:
  - `<mode>/seeds/seed-<n>/representatives/<representative_id>/`
- Representative bundles must preserve:
  - `fields/*.npz`
  - top-level `case.yaml`
  - top-level `solution.yaml`
  - top-level `evaluation.yaml`
- Seed-run trace artifacts are JSONL-only under `traces/`:
  - `traces/evaluation_events.jsonl`
  - `traces/generation_summary.jsonl`
  - `traces/controller_trace.jsonl` (llm only)
  - `traces/operator_trace.jsonl`
  - `traces/llm_request_trace.jsonl` (llm only)
  - `traces/llm_response_trace.jsonl` (llm only)
  - Operator trace rows follow §4.3 schema: `decision_id, generation, operator_name, parents, offspring, params_digest, wall_ms`
  - Per-seed `run.yaml` manifest captures mode, seeds, spec paths, population/generation size, wall-clock seconds
- Central rendered assets live beside traces (written by `render-assets`):
  - `analytics/*.csv`
  - `figures/*.png`
  - `figures/pdf/*.pdf`
  - run-level figure set includes `pareto_front`, `hypervolume_progress`, `objective_progress`, `temperature_trace`, `gradient_trace`, `constraint_violation_progress`, `layout_initial`, `layout_final`, `layout_evolution`, `temperature_field_<repr>`, `gradient_field_<repr>`, `operator_phase_heatmap`
  - `layout_evolution` is a best-so-far spatial-milestone replay; preserved frame PNGs live under `figures/layout_evolution_frames/step-<n>` or `step_<NNN>.png`-style names rather than per-generation `gen_*`
  - layout figures are clean publication panels with internal component labels, explicit sink ribbon, and a compact right-side metadata strip
  - field figures keep mandatory top titles, explicit sink rendering, internal white label chips, and aligned colorbar composition
- `render-assets` must replay the recorded evaluated geometry from the run contract rather than silently applying full repair to clean baseline traces.
- Remove temporary scripts, debug files, caches, and one-off intermediate outputs after validation when they are not intended repository state.
- Do not manually edit generated artifacts to change conclusions.

## Testing Expectations

- Maintained tests belong under `tests/`.
- Add or update focused tests for new behavior.
- Run the **focused** tests relevant to your change (specific file or subdirectory under `tests/`) before claiming completion. Escalate to the full `conda run -n msfenicsx pytest -v` only when you are genuinely uncertain about cross-module impact — e.g. editing shared contracts in `core/`, shared registries in `optimizers/`, or when focused tests pass but behavior still looks suspicious.
- When modifying optimizer or controller logic, run the specific test file first. Only run the full suite if the change clearly reaches beyond that file's scope or if you cannot convince yourself the blast radius is contained.

Current maintained test areas are:

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

## Documentation Expectations

- For major contract or workflow changes, update:
  - `README.md`
  - relevant docs under `docs/`
  - `AGENTS.md` when repository guidance changes
- Keep active docs aligned with implemented reality.
- Treat `AGENTS.md` as the single authoritative repository guidance file.

## Useful References

- `README.md`
- `AGENTS.md`
- `docs/superpowers/specs/2026-03-26-msfenicsx-clean-rebuild-design.md`
- `docs/superpowers/plans/2026-03-26-msfenicsx-clean-rebuild-phase1.md`
- `docs/superpowers/specs/2026-04-02-s1-typical-mainline-reset-design.md`
- `docs/superpowers/plans/2026-04-02-s1-typical-mainline-reset.md`
- `docs/superpowers/specs/2026-04-27-s3-s4-scale-benchmarks-design.md`
- `docs/superpowers/plans/2026-04-27-s3-s4-scale-benchmarks.md`
- `scenarios/templates/s1_typical.yaml`
- `scenarios/evaluation/s1_typical_eval.yaml`
- `scenarios/optimization/s1_typical_raw.yaml`
- `scenarios/optimization/s1_typical_union.yaml`
- `scenarios/optimization/s1_typical_llm.yaml`
- `scenarios/optimization/profiles/s1_typical_raw.yaml`
- `scenarios/optimization/profiles/s1_typical_union.yaml`
- `scenarios/templates/s2_staged.yaml`
- `scenarios/evaluation/s2_staged_eval.yaml`
- `scenarios/optimization/s2_staged_raw.yaml`
- `scenarios/optimization/s2_staged_union.yaml`
- `scenarios/optimization/s2_staged_llm.yaml`
- `scenarios/optimization/s2_staged_spea2_raw.yaml`
- `scenarios/optimization/s2_staged_cmopso_raw.yaml`
- `scenarios/optimization/s2_staged_moead_raw.yaml`
- `scenarios/optimization/profiles/s2_staged_raw.yaml`
- `scenarios/optimization/profiles/s2_staged_union.yaml`
- `scenarios/optimization/profiles/s2_staged_spea2_raw.yaml`
- `scenarios/optimization/profiles/s2_staged_cmopso_raw.yaml`
- `scenarios/optimization/profiles/s2_staged_moead_raw.yaml`
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
