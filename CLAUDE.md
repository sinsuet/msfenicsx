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
- formal paper-facing expensive PDE evaluation budgets:
  - S5: `population_size=40`, `num_generations=32`, nominal budget `1280`
  - S6: `population_size=56`, `num_generations=36`, nominal budget `2016`
  - S7: `population_size=64`, `num_generations=40`, nominal budget `2560`
- these budgets are intentionally budget-limited for expensive PDE-constrained optimization, not cheap benchmark convergence budgets
- within each scenario, keep the same formal budget across `raw`, `union`, `llm`, and raw-only algorithm-comparison runs
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
- Treat the repo as Linux-first; all paths in docs and scripts use relative form from the repo root.
- When worktrees are needed for this repository, create them under the repo-root `.worktrees/` directory. Do not use `.claude/worktrees/`; keep the location shared with Codex for a single convention.
- Use the `msfenicsx` conda environment for Python, CLI, and tests.
- Prefer: `conda run -n msfenicsx ...`
- Repository text artifacts should use UTF-8 without BOM.
- Treat terminal-side mojibake from the host bridge as environment noise unless the saved file itself is corrupted.

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

Optimize with unified benchmark runner:
```bash
# Smoke example only; use formal batch specs or --evaluation-workers 16 for overnight budgeted runs.
conda run -n msfenicsx python -m optimizers.cli run-benchmark \
  --optimization-spec scenarios/optimization/s5_aggressive15_raw.yaml \
  --mode raw \
  --benchmark-seed 11 \
  --algorithm-seed 1011 \
  --population-size 2 \
  --num-generations 1 \
  --evaluation-workers 2 \
  --scenario-runs-root ./scenario_runs

conda run -n msfenicsx python -m optimizers.cli run-benchmark \
  --batch-spec scenarios/batches/s5_raw_union_budgeted.yaml

conda run -n msfenicsx python -m optimizers.cli run-benchmark \
  --batch-spec scenarios/batches/s6_raw_union_budgeted.yaml

conda run -n msfenicsx python -m optimizers.cli run-benchmark \
  --batch-spec scenarios/batches/s5_s6_raw_union_budgeted.yaml
```

`run-benchmark` launches leaves as subprocesses, writes `run_index.csv`, automatically renders assets, runs LLM trace diagnostics, and creates available seed-aware `comparisons/`.

Worker-count policy:
- `--evaluation-workers 2` is for smoke checks, quick debugging, or deliberately conservative daytime reruns.
- Formal overnight S5/S6 raw+union batches use the batch resource policy (`max_concurrent_leaves=4`, `leaf_evaluation_workers=16`).
- Formal single-leaf LLM/profile runs should normally use `--evaluation-workers 16` unless the server is already heavily loaded.

Install LLM dependency:
```bash
conda run -n msfenicsx python -m pip install "openai>=1.70"
```

### LLM Configuration

The active `nsga2_llm` route uses OpenAI-compatible provider profiles:

- `run-benchmark --mode llm` defaults to the spec's `provider_profile` when `--llm-profile` is omitted; active S5-S7 LLM specs use `provider_profile: gemma4`
- switch models explicitly with `--llm-profile qwen3_6_plus`, `--llm-profile gpt`, `--llm-profile glm_5`, `--llm-profile minimax_m2_5`, `--llm-profile deepseek_v4_flash`, `--llm-profile gemma4`, or `--llm-profile mimo_v2_5`
- model profile declarations live in `llm/openai_compatible/profiles.yaml`
- bundled model registry maps:
  - `default -> GPT_PROXY_API_KEY / GPT_PROXY_BASE_URL -> gpt-5.4`
  - `gpt -> GPT_PROXY_API_KEY / GPT_PROXY_BASE_URL -> gpt-5.4`
  - `qwen3_6_plus -> QWEN_PROXY_API_KEY / QWEN_PROXY_BASE_URL -> qwen3.6-plus`
  - `glm_5 -> QWEN_PROXY_API_KEY / QWEN_PROXY_BASE_URL -> glm-5`
  - `minimax_m2_5 -> QWEN_PROXY_API_KEY / QWEN_PROXY_BASE_URL -> MiniMax-M2.5`
  - `deepseek_v4_flash -> DEEPSEEK_PROXY_API_KEY / DEEPSEEK_PROXY_BASE_URL -> deepseek-v4-flash` with `extra_body.thinking.type=disabled` and `max_output_tokens=1024`
  - `gemma4 -> GEMMA4_API_KEY / GEMMA4_BASE_URL -> gemma4:31b-it-q8_0` through the HPC Ollama/OpenAI-compatible endpoint with `max_output_tokens=2048`
  - `mimo_v2_5 -> MIMO_API_KEY / MIMO_BASE_URL -> mimo-v2.5` with `extra_body.chat_template_kwargs.enable_thinking=false` and `max_output_tokens=1024`
- the active `scenarios/optimization/s5_aggressive15_llm.yaml` resolves runtime provider identity through:
  - `LLM_API_KEY`
  - `LLM_BASE_URL`
  - `LLM_MODEL`
- repository-root `.env` should keep the raw provider credentials:
  - `GPT_PROXY_API_KEY`
  - `GPT_PROXY_BASE_URL`
  - `QWEN_PROXY_API_KEY`
  - `QWEN_PROXY_BASE_URL=https://coding.dashscope.aliyuncs.com/v1`
  - `DEEPSEEK_PROXY_API_KEY`
  - `DEEPSEEK_PROXY_BASE_URL=https://llmapi.paratera.com/v1`
  - `GEMMA4_API_KEY`
  - `GEMMA4_BASE_URL=http://10.40.1.22:11434/v1`
  - `MIMO_API_KEY`
  - `MIMO_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1`

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
- Conservative daytime smoke/debug optimizer reruns may prefer `--evaluation-workers 2` or lower, including future `llm` runs; do not apply this to formal overnight budgeted S5/S6/S7 runs.
- Formal overnight budgeted raw/union batches should use the batch resource policy (`max_concurrent_leaves=4`, `leaf_evaluation_workers=16` by default). Formal single-leaf LLM/profile runs should normally use `--evaluation-workers 16`.
- Keep evaluation criteria in standalone `evaluation_spec` files instead of adding optimizer metadata to `thermal_case`.
- Keep optimizer search settings and design-variable bounds in standalone `optimization_spec` files.
- Repository-wide backbone defaults belong in `optimizers/algorithm_config.py`.
- Benchmark-specific tuning belongs in `scenarios/optimization/profiles/` and `algorithm.parameters`.
- Active runtime outputs should go to `scenario_runs/`, not source folders.
- Active optimizer runs should write under `scenario_runs/<scenario_id>/<run_id>/`.
- Optimizer runs are not complete until `run-benchmark` automatic postprocess has written seed assets and the final `run_index.csv` status is `completed`.
- When 2+ concrete run roots are part of the same campaign or explicit compare context, use the `run-benchmark` campaign-owned `comparisons/` bundle before final reporting.
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
- Central rendered assets live beside traces (written by `run-benchmark` postprocess):
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
- `docs/superpowers/specs/2026-04-28-s5-aggressive-15-component-benchmark-design.md`
- `docs/superpowers/specs/2026-04-28-s6-aggressive-20-component-benchmark-design.md`
- `docs/superpowers/specs/2026-04-28-s7-aggressive-25-component-benchmark-design.md`
- `docs/superpowers/specs/2026-04-30-llm-semantic-ranker-controller-design.md`
- `docs/superpowers/plans/2026-04-29-s5-s7-512eval-benchmark-matrix.md`
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
