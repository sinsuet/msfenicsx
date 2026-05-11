# AGENTS.md

This file gives Codex-style agents repository-specific guidance for `msfenicsx`.

## Writing Language

- Reports, plans, design documents, analysis notes, and other prose deliverables should be written in Simplified Chinese by default.
- Keep necessary technical terms, code identifiers, command names, file paths, schema keys, model/profile IDs, and quoted API fields in their original language when translating would reduce precision.
- This Chinese-first rule applies to future files under `docs/superpowers/specs/`, `docs/superpowers/plans/`, and similar planning/reporting artifacts unless the user explicitly asks for another language.

## Repository Status

- `main` already contains the clean rebuild baseline.
- The current active paper-facing mainline is `s4_aggressive10` through `s6_aggressive20`.
- The primary debugging template remains `s5_aggressive15`; use S4 for low-dimensional semantic ablation and S6 for scale checks.
- S4/S5/S6 use the shared `primitive_structured` operator substrate for `union` and `llm`; `union` is used only where the final experiment design requires semantic-controller ablation.
- The active paper-facing optimizer ladder is:
  - `nsga2_raw`
  - `nsga2_llm_deepseek_v4_flash`
- Additional algorithm-comparison inputs are raw-only unless a later design explicitly promotes them:
  - `spea2_raw`
  - `moead_raw`
- The active final experiment structure is:
  - Main: S4/S5/S6, 5 seeds, `raw` vs `llm_deepseek_v4_flash`
  - Semantic Ablation: S4, 5 seeds, `raw / union / llm`
  - Mechanism / Feedback-Off Diagnostic: S6 seed23, single-seed mechanism ablation / negative control, raw vs feedback-off DeepSeek; LLM source root `scenario_runs/s6_aggressive20/0510_1239__llm-deepseek_v4_flash/llm-deepseek-v4-flash/seeds/seed-23`
  - Model Sensitivity: S5 seed11, DeepSeek/Qwen/GPT-5.5/MiMo
  - Algorithm Baseline: S5, 5 seeds, NSGA-II/SPEA2/MOEA/D raw
- The active paper-facing seed policy is:
  - S4 main and S4 semantic ablation: seeds `11,13,17,19,23`; official archive `paper_database/s4_aggressive10/archives/0511_archive__raw_union_llm-deepseek_v4_flash_5seed`
  - S5 main: seeds `11,19,23,37,41`; official archive `paper_database/s5_aggressive15/archives/0511_archive__raw_llm-deepseek_v4_flash_top5`
  - S5 algorithm baseline: seeds `11,23,31,37,41`
  - S5 model sensitivity: seed `11`, with GPT-5.5 treated as a normal effective profile result
  - S6 main: seeds `11,13,19,21,23`; official archive `paper_database/s6_aggressive20/archives/0511_archive__raw_llm-deepseek_v4_flash_5seed`
  - S6 seed23 mechanism / feedback-off diagnostic is diagnostic-only and must not enter S6 main aggregate
- The active optimizer ladder uses a matched paper-facing substrate:
  - `raw`: native backbone + `projection_plus_local_restore`
  - `union`: `primitive_structured` registry + fixed stochastic operator-selection controller + `projection_plus_local_restore`
  - `llm`: same `primitive_structured` registry + LLM representation-layer controller + same `projection_plus_local_restore`
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

- `scenarios/templates/s4_aggressive10.yaml`
- `scenarios/evaluation/s4_aggressive10_eval.yaml`
- `scenarios/optimization/s4_aggressive10_raw.yaml`
- `scenarios/optimization/s4_aggressive10_union.yaml`
- `scenarios/optimization/s4_aggressive10_llm.yaml`
- `scenarios/optimization/profiles/s4_aggressive10_raw.yaml`
- `scenarios/optimization/profiles/s4_aggressive10_union.yaml`
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
- `scenarios/batches/s4_main_raw_llm_deepseek_budgeted.yaml`
- `scenarios/batches/s5_main_raw_llm_deepseek_budgeted.yaml`
- `scenarios/batches/s6_main_raw_llm_deepseek_budgeted.yaml`
- `scenarios/batches/s4_semantic_ablation_budgeted.yaml`
- `scenarios/batches/s5_model_sensitivity_seed11.yaml`
- `scenarios/batches/s5_algorithm_baseline_raw_budgeted.yaml`

The fixed benchmark decisions are:

- one operating case
- fixed named components:
  - S4: 10 components
  - S5: 15 components
  - S6: 20 components
- all components optimize `x/y` only
- no optimized rotation
- scenario-specific decision dimensions:
  - S4: 22 decision variables
  - S5: 32 decision variables
  - S6: 42 decision variables
- formal paper-facing expensive PDE evaluation budgets:
  - S4: `population_size=32`, `num_generations=16`, nominal budget `512`
  - S5: `population_size=40`, `num_generations=32`, nominal budget `1280`
  - S6: `population_size=56`, `num_generations=36`, nominal budget `2016`
- these budgets are intentionally budget-limited for expensive PDE-constrained optimization, not cheap benchmark convergence budgets
- within each experiment block, keep the same formal budget across compared methods
- objectives:
  - `summary.temperature_max`
  - `summary.temperature_gradient_rms`
- hard sink-budget constraint:
  - `case.total_radiator_span <= radiator_span_max`
- cheap constraints must run before PDE
- paper-facing S4/S5/S6 `raw`, `union`, `llm`, and raw-only algorithm-comparison specs use `projection_plus_local_restore`; do not restore or execute `llm_direct`
- paper-facing S4/S5/S6 `llm` specs use `semantic_ranked_pick` and default to `provider_profile: deepseek_v4_flash`

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
- When worktrees are needed for this repository, create them under the repo-root `.worktrees/` directory. Do not use `.claude/worktrees/`; keep the location shared with Claude and Codex for a single convention.
- Use the `msfenicsx` conda environment for Python, CLI, and tests.
- Prefer:
  - `conda run -n msfenicsx ...`
- Repository text artifacts should use UTF-8 without BOM.
- Treat terminal-side mojibake from the host bridge as environment noise unless the saved file itself is corrupted.

Preferred commands:

Notes on optimizer worker counts:

- `--evaluation-workers 2` in the single-leaf examples below is only for smoke checks, quick debugging, or deliberately conservative daytime reruns.
- Formal overnight S4/S5/S6 paper-facing runs should follow the unified runner resource policy: multi-leaf batches use `max_concurrent_leaves=4` and `leaf_evaluation_workers=32`; single-leaf formal LLM/profile runs should use `--evaluation-workers 32` unless the machine is already heavily loaded.

- `conda run -n msfenicsx pytest -v`
- `conda run -n msfenicsx python -m core.cli.main validate-scenario-template --template scenarios/templates/s5_aggressive15.yaml`
- `conda run -n msfenicsx python -m core.cli.main generate-case --template scenarios/templates/s5_aggressive15.yaml --seed 11 --output-root ./scenario_runs/generated_cases/s5_aggressive15/seed-11`
- `conda run -n msfenicsx python -m core.cli.main solve-case --case ./scenario_runs/generated_cases/s5_aggressive15/seed-11/s5_aggressive15-seed-0011.yaml --output-root ./scenario_runs`
- `conda run -n msfenicsx python -m evaluation.cli evaluate-case --case ./scenario_runs/s5_aggressive15/s5_aggressive15-seed-0011/case.yaml --solution ./scenario_runs/s5_aggressive15/s5_aggressive15-seed-0011/solution.yaml --spec scenarios/evaluation/s5_aggressive15_eval.yaml --output ./evaluation_report.yaml --bundle-root ./scenario_runs/s5_aggressive15/s5_aggressive15-seed-0011`
- `conda run -n msfenicsx python -m optimizers.cli run-benchmark --optimization-spec scenarios/optimization/s5_aggressive15_raw.yaml --mode raw --benchmark-seed 11 --algorithm-seed 1011 --population-size 2 --num-generations 1 --evaluation-workers 2 --scenario-runs-root ./scenario_runs`
- `conda run -n msfenicsx python -m optimizers.cli run-benchmark --optimization-spec scenarios/optimization/s5_aggressive15_union.yaml --mode union --benchmark-seed 11 --algorithm-seed 1011 --population-size 2 --num-generations 1 --evaluation-workers 2 --scenario-runs-root ./scenario_runs`
- `conda run -n msfenicsx python -m optimizers.cli run-benchmark --optimization-spec scenarios/optimization/s5_aggressive15_llm.yaml --mode llm --llm-profile deepseek_v4_flash --benchmark-seed 11 --algorithm-seed 1011 --population-size 5 --num-generations 2 --evaluation-workers 2 --scenario-runs-root ./scenario_runs`
- Raw-only algorithm comparisons should be run as `run-benchmark` raw leaves or batch methods; do not add `spea2` or `moead` as `union` or `llm` modes.
- `conda run -n msfenicsx python -m optimizers.cli run-benchmark --optimization-spec scenarios/optimization/s5_aggressive15_spea2_raw.yaml --mode raw --benchmark-seed 11 --algorithm-seed 1011 --population-size 40 --num-generations 32 --evaluation-workers 32 --scenario-runs-root ./scenario_runs`
- `conda run -n msfenicsx python -m optimizers.cli run-benchmark --optimization-spec scenarios/optimization/s5_aggressive15_moead_raw.yaml --mode raw --benchmark-seed 11 --algorithm-seed 1011 --population-size 40 --num-generations 32 --evaluation-workers 32 --scenario-runs-root ./scenario_runs`
- `conda run -n msfenicsx python -m optimizers.cli run-benchmark --batch-spec scenarios/batches/s4_main_raw_llm_deepseek_budgeted.yaml`
- `conda run -n msfenicsx python -m optimizers.cli run-benchmark --batch-spec scenarios/batches/s5_main_raw_llm_deepseek_budgeted.yaml`
- `conda run -n msfenicsx python -m optimizers.cli run-benchmark --batch-spec scenarios/batches/s6_main_raw_llm_deepseek_budgeted.yaml`
- `conda run -n msfenicsx python -m optimizers.cli run-benchmark --batch-spec scenarios/batches/s4_semantic_ablation_budgeted.yaml`
- `conda run -n msfenicsx python -m optimizers.cli run-benchmark --batch-spec scenarios/batches/s5_model_sensitivity_seed11.yaml`
- `conda run -n msfenicsx python -m optimizers.cli run-benchmark --batch-spec scenarios/batches/s5_algorithm_baseline_raw_budgeted.yaml`
- `run-benchmark` automatically renders leaf assets, runs LLM replay/controller diagnostics for LLM leaves, and writes available seed-aware comparisons under `comparisons/`.
- Budget overrides for single-leaf `run-benchmark`: `--population-size`, `--num-generations`
- `conda run -n msfenicsx python -m pip install "openai>=1.70"`

The active `nsga2_llm` route currently uses OpenAI-compatible model profiles:

- `run-benchmark --mode llm` defaults to the spec's `provider_profile` when `--llm-profile` is omitted; active S4-S6 LLM specs use `provider_profile: deepseek_v4_flash`
- switch models explicitly with `--llm-profile deepseek_v4_flash`, `--llm-profile qwen3_6_plus`, `--llm-profile kimi_k2_5`, `--llm-profile gpt`, or `--llm-profile mimo_v2_5`
- model profile declarations live in `llm/openai_compatible/profiles.yaml`
- bundled model registry maps:
  - `default -> DEEPSEEK_PROXY_API_KEY / DEEPSEEK_PROXY_BASE_URL -> deepseek-v4-flash` with `extra_body.thinking.type=disabled` and `max_output_tokens=1024`
  - `gpt -> GPT_PROXY_API_KEY / GPT_PROXY_BASE_URL -> gpt-5.4`
  - `qwen3_6_plus -> QWEN_PROXY_API_KEY / QWEN_PROXY_BASE_URL -> qwen3.6-plus`
  - `glm_5 -> QWEN_PROXY_API_KEY / QWEN_PROXY_BASE_URL -> glm-5`
  - `kimi_k2_5 -> QWEN_PROXY_API_KEY / QWEN_PROXY_BASE_URL -> kimi-k2.5`
  - `minimax_m2_5 -> QWEN_PROXY_API_KEY / QWEN_PROXY_BASE_URL -> MiniMax-M2.5`
  - `deepseek_v4_flash -> DEEPSEEK_PROXY_API_KEY / DEEPSEEK_PROXY_BASE_URL -> deepseek-v4-flash` with `extra_body.thinking.type=disabled` and `max_output_tokens=1024`
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

## Data And Artifact Rules

- Treat `scenario_template`, `thermal_case`, and `thermal_solution` as the active canonical contracts.
- `s5_aggressive15` is the primary fixed single-case debugging template and must not define `operating_case_profiles`.
- S4/S5/S6 are fixed single-case benchmarks; do not use multiple benchmark seeds to simulate multiple problem instances.
- Conservative daytime smoke/debug optimizer reruns may prefer `--evaluation-workers 2` or lower, including future `llm` runs; do not apply this to formal overnight budgeted S4/S5/S6 runs.
- Formal overnight budgeted batches should use the batch resource policy (`max_concurrent_leaves=4`, `leaf_evaluation_workers=32` by default). Formal single-leaf LLM/profile runs should normally use `--evaluation-workers 32`.
- Keep evaluation criteria in standalone `evaluation_spec` files instead of adding optimizer metadata to `thermal_case`.
- Keep optimizer search settings and design-variable bounds in standalone `optimization_spec` files.
- Repository-wide backbone defaults belong in `optimizers/algorithm_config.py`.
- Benchmark-specific tuning belongs in `scenarios/optimization/profiles/` and `algorithm.parameters`.
- Active runtime outputs should go to `scenario_runs/`, not source folders.
- Single solved-case bundles written by `solve-case` should keep `fields/*.npz` + `summaries/field_view.json` and render `figures/layout.png`, `figures/temperature_field.png`, and `figures/gradient_field.png`.
- Active optimizer runs should write under `scenario_runs/<scenario_id>/<run_id>/`.
- Optimizer runs are not complete until `run-benchmark` automatic postprocess has written seed assets and the final `run_index.csv` status is `completed`.
- When 2+ concrete run roots are part of the same campaign or explicit `--compare-with` context, rely on the `run-benchmark` campaign-owned `comparisons/` bundle before final reporting.
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
- Legacy standalone comparison internals may remain importable for reuse, but active user-facing comparison output should be produced by `run-benchmark` under `comparisons/`.
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
- Central rendered assets live beside traces (written by `run-benchmark` postprocess):
  - `analytics/*.csv`
  - `figures/*.png`
  - `figures/pdf/*.pdf`
  - run-level figure set includes `pareto_front`, `hypervolume_progress`, `objective_progress`, `temperature_trace`, `gradient_trace`, `constraint_violation_progress`, `layout_initial`, `layout_final`, `layout_evolution`, `temperature_field_<repr>`, `gradient_field_<repr>`, `operator_phase_heatmap`
  - `layout_evolution` is a best-so-far spatial-milestone replay; preserved frame PNGs live under `figures/layout_evolution_frames/step-<n>` or `step_<NNN>.png`-style names rather than per-generation `gen_*`
  - layout figures are clean publication panels with internal component labels, explicit sink ribbon, and a compact right-side metadata strip
  - field figures keep mandatory top titles, explicit sink rendering, internal white label chips, and aligned colorbar composition
- Rendering must replay the recorded evaluated geometry from the run contract rather than silently applying full repair to clean baseline traces.
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
- Describe `nsga2_union` as the semantic-controller ablation baseline: it uses the same shared primitive operator substrate, NSGA-II backbone, repair path, cheap screening, and PDE budget as `nsga2_llm`, but uses a fixed stochastic operator policy without semantic task reasoning, LLM ranking, memory/reflection, or policy guidance. Describe `nsga2_llm` as adding those representation-layer semantic-control mechanisms over the same candidate support.
- If something is not validated yet, label it as a hypothesis rather than a confirmed result.
- Keep infeasible cases, failed solves, regressions, and anomalies visible in analysis.
- Failure reasons and dominant violations are valid evidence and should remain visible in artifacts when relevant.
- Cheap local `controller_trace` diagnostics are valid pre-live evidence before any new live rerun.
- For reruns within the same experiment family (for example a budget sweep, a raw/union/llm ladder, or a raw-only algorithm baseline), include the rendered comparison bundle for the closest prior baseline before final reporting so the user does not need to request a second pass.

## Documentation Expectations

- For major contract or workflow changes, update:
  - `README.md`
  - `AGENTS.md` when repository guidance changes
  - `CLAUDE.md` to keep it in sync
- Keep active docs aligned with implemented reality.
- Treat `CLAUDE.md` as authoritative repository guidance for Claude Code sessions.

## Useful References

- `README.md`
- `AGENTS.md`
- `CLAUDE.md`
- `docs/superpowers/specs/2026-03-26-msfenicsx-clean-rebuild-design.md`
- `docs/superpowers/plans/2026-03-26-msfenicsx-clean-rebuild-phase1.md`
- `scenarios/templates/s4_aggressive10.yaml`
- `scenarios/evaluation/s4_aggressive10_eval.yaml`
- `scenarios/optimization/s4_aggressive10_raw.yaml`
- `scenarios/optimization/s4_aggressive10_union.yaml`
- `scenarios/optimization/s4_aggressive10_llm.yaml`
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
- `scenarios/batches/s4_main_raw_llm_deepseek_budgeted.yaml`
- `scenarios/batches/s5_main_raw_llm_deepseek_budgeted.yaml`
- `scenarios/batches/s6_main_raw_llm_deepseek_budgeted.yaml`
- `scenarios/batches/s4_semantic_ablation_budgeted.yaml`
- `scenarios/batches/s5_model_sensitivity_seed11.yaml`
- `scenarios/batches/s5_algorithm_baseline_raw_budgeted.yaml`
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
