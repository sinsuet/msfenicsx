# S5/S6 Main Results And Paper Database Relocation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按最终论文口径重建并同步 `paper_database/`：S5 main 只使用 top5 seeds，S6 main 使用完成的 five-seed raw-vs-DeepSeek archive，S6 seed23 机制诊断使用三方 raw / normal LLM / feedback-off LLM scope，所有 paper-facing archive、comparison、指标表、DuckDB、图和论文文档统一迁出 `scenario_runs/`。

**Architecture:** 原始 optimizer runs 仍保留在 `scenario_runs/` 作为 source-of-truth；`paper_database/` 是唯一 paper-facing evidence root。每个场景在 `paper_database/<scenario_id>/archives/` 下有官方 archive，所有 comparison bundle 从这些 archive 重新生成。`paper_database/paper_experiment_db/` 是当前论文指标、claim evidence 和图表索引的统一入口。

**Tech Stack:** Python, YAML/CSV/JSON artifact manipulation, existing `optimizers.benchmark_runner.comparisons.plan_campaign_comparisons`, DuckDB, focused pytest, Markdown/LaTeX documentation.

---

## Final Contract

### Official Main Blocks

| Block | Scenario | Methods | Official seeds | Budget | Official archive |
|---|---|---|---|---:|---|
| `main_s4` | `s4_aggressive10` | `raw`, `llm-deepseek-v4-flash` | `11,13,17,19,23` | 512 | `paper_database/s4_aggressive10/archives/0511_archive__raw_union_llm-deepseek_v4_flash_5seed` |
| `main_s5` | `s5_aggressive15` | `raw`, `llm-deepseek-v4-flash` | `23,37,19,11,41` | 1280 | `paper_database/s5_aggressive15/archives/0511_archive__raw_llm-deepseek_v4_flash_top5` |
| `main_s6` | `s6_aggressive20` | `raw`, `llm-deepseek-v4-flash` | `13,19,11,21,23` | 2016 | `paper_database/s6_aggressive20/archives/0511_archive__raw_llm-deepseek_v4_flash_5seed` |

### Diagnostic / Context Blocks

| Block | Scenario | Role | Official seeds | Official archive or root |
|---|---|---|---:|---|
| `semantic_ablation_s4` | `s4_aggressive10` | raw/union/LLM semantic-controller ablation | `11,13,17,19,23` | same S4 archive |
| `mechanism_ablation_s6_seed23` | `s6_aggressive20` | raw / normal LLM / feedback-off LLM mechanism diagnostic | `23` | `paper_database/paper_experiment_db/figures/s6_seed23_mechanism_ablation/` |
| `feedback_off_diagnostic_s6_seed23` | `s6_aggressive20` | feedback-off source archive, diagnostic only | `23` | `paper_database/s6_aggressive20/archives/0511_archive__feedback_off_deepseek_seed23_diagnostic` |
| `model_sensitivity_s5_seed11` | `s5_aggressive15` | model sensitivity diagnostic | `11` | `paper_database/s5_aggressive15/archives/0511_archive__model_compare_seed11` |
| `algorithm_baseline_s5` | `s5_aggressive15` | raw-only algorithm baseline | `11,23,31,37,41` | `paper_database/s5_aggressive15/archives/0511_archive__algorithm_compare_raw` |

### Source Maps

S5 top5 main sources:

| Seed | raw source | LLM source |
|---:|---|---|
| 23 | `paper_database/s5_aggressive15/archives/0511_archive__raw_llm-deepseek_v4_flash_top5/raw/seeds/seed-23` | `paper_database/s5_aggressive15/archives/0511_archive__raw_llm-deepseek_v4_flash_top5/llm-deepseek-v4-flash/seeds/seed-23` |
| 37 | `paper_database/s5_aggressive15/archives/0511_archive__raw_llm-deepseek_v4_flash_top5/raw/seeds/seed-37` | `paper_database/s5_aggressive15/archives/0511_archive__raw_llm-deepseek_v4_flash_top5/llm-deepseek-v4-flash/seeds/seed-37` |
| 19 | `paper_database/s5_aggressive15/archives/0511_archive__raw_llm-deepseek_v4_flash_top5/raw/seeds/seed-19` | `paper_database/s5_aggressive15/archives/0511_archive__raw_llm-deepseek_v4_flash_top5/llm-deepseek-v4-flash/seeds/seed-19` |
| 11 | `paper_database/s5_aggressive15/archives/0511_archive__raw_llm-deepseek_v4_flash_top5/raw/seeds/seed-11` | `paper_database/s5_aggressive15/archives/0511_archive__raw_llm-deepseek_v4_flash_top5/llm-deepseek-v4-flash/seeds/seed-11` |
| 41 | `paper_database/s5_aggressive15/archives/0511_archive__raw_llm-deepseek_v4_flash_top5/raw/seeds/seed-41` | `paper_database/s5_aggressive15/archives/0511_archive__raw_llm-deepseek_v4_flash_top5/llm-deepseek-v4-flash/seeds/seed-41` |

S6 main sources:

| Seed | raw source | LLM source |
|---:|---|---|
| 13 | `paper_database/s6_aggressive20/archives/0511_archive__raw_llm-deepseek_v4_flash_5seed/raw/seeds/seed-13` | `paper_database/s6_aggressive20/archives/0511_archive__raw_llm-deepseek_v4_flash_5seed/llm-deepseek-v4-flash/seeds/seed-13` |
| 19 | `paper_database/s6_aggressive20/archives/0511_archive__raw_llm-deepseek_v4_flash_5seed/raw/seeds/seed-19` | `paper_database/s6_aggressive20/archives/0511_archive__raw_llm-deepseek_v4_flash_5seed/llm-deepseek-v4-flash/seeds/seed-19` |
| 11 | `paper_database/s6_aggressive20/archives/0511_archive__raw_llm-deepseek_v4_flash_5seed/raw/seeds/seed-11` | `paper_database/s6_aggressive20/archives/0511_archive__raw_llm-deepseek_v4_flash_5seed/llm-deepseek-v4-flash/seeds/seed-11` |
| 21 | `paper_database/s6_aggressive20/archives/0511_archive__raw_llm-deepseek_v4_flash_5seed/raw/seeds/seed-21` | `paper_database/s6_aggressive20/archives/0511_archive__raw_llm-deepseek_v4_flash_5seed/llm-deepseek-v4-flash/seeds/seed-21` |
| 23 | `paper_database/s6_aggressive20/archives/0511_archive__raw_llm-deepseek_v4_flash_5seed/raw/seeds/seed-23` | `paper_database/s6_aggressive20/archives/0511_archive__raw_llm-deepseek_v4_flash_5seed/llm-deepseek-v4-flash/seeds/seed-23` |

Note: S6 seed23 mechanism / feedback-off diagnostic uses the same benchmark seed but is diagnostic-only and must not enter `main_s6`.

## Tasks

### Task 1: Archive Everything Under `paper_database/`

- [x] Create `paper_database/<scenario_id>/archives/` for S4, S5, and S6.
- [x] Stage S4 official raw/union/LLM archive under `paper_database/s4_aggressive10/archives/`.
- [x] Build S5 top5 main archive with method directories `raw` and `llm-deepseek-v4-flash`.
- [x] Build S6 main archive with method directories `raw` and `llm-deepseek-v4-flash`.
- [x] Copy S5 model-sensitivity and algorithm-baseline archives into `paper_database/s5_aggressive15/archives/`.
- [x] Copy S6 feedback-off diagnostic archive into `paper_database/s6_aggressive20/archives/`.
- [x] Write or refresh `archive_provenance.yaml` and `run_index.csv` for assembled archives.

### Task 2: Regenerate Comparisons

- [x] Run `optimizers.benchmark_runner.comparisons.plan_campaign_comparisons` for S4 official archive.
- [x] Run it for S5 top5 main archive.
- [x] Run it for S6 main archive.
- [x] Run comparison export for S5 algorithm-baseline archive.
- [x] Verify S5 main aggregate contains exactly seeds `11,19,23,37,41`.
- [x] Verify S6 main aggregate contains exactly seeds `11,13,19,21,23`.
- [x] Verify S6 seed23 mechanism diagnostic is single-seed and excluded from `main_s6`.

### Task 3: Refresh Paper Experiment DB

- [x] Update `paper_database/paper_experiment_db/manifest.yaml` so all `database.*`, `current_root`, `comparison_root`, claim paths, and representative diagnostic paths point to `paper_database/...`.
- [x] Regenerate:
  - `paper_database/paper_experiment_db/tables/seed_metrics.csv`
  - `paper_database/paper_experiment_db/tables/aggregate_metrics.csv`
  - `paper_database/paper_experiment_db/tables/pairwise_deltas.csv`
  - `paper_database/paper_experiment_db/tables/common_pde_cutoff.csv`
  - `paper_database/paper_experiment_db/tables/model_sensitivity_metrics.csv`
  - `paper_database/paper_experiment_db/tables/claim_evidence.csv`
  - `paper_database/paper_experiment_db/tables/completeness_matrix.csv`
  - `paper_database/paper_experiment_db/tables/artifact_index.csv`
  - `paper_database/paper_experiment_db/msfenicsx_experiments.duckdb`
- [x] Replace old representative diagnostic figure references with `paper_database/paper_experiment_db/figures/s6_seed23_mechanism_ablation/`.

### Task 4: Sync Specs, Docs, Plans, And Paper

- [x] Update batch specs:
  - `scenarios/batches/s5_main_raw_llm_deepseek_budgeted.yaml` -> seeds `23,37,19,11,41`
  - `scenarios/batches/s6_main_raw_llm_deepseek_budgeted.yaml` -> seeds `13,19,11,21,23`
- [x] Update repository guidance in `README.md`, `AGENTS.md`, and `CLAUDE.md`.
- [x] Update Stage A docs and this plan to reference `paper_database/` and current S6 seed23 mechanism diagnostic.
- [x] Update paper planning registers:
  - `paper/msgalaxy/planning/evidence_register.md`
  - `paper/msgalaxy/planning/narrative_register.md`
  - `paper/msgalaxy/planning/figure_table_register.md`
  - chapter briefs under `paper/msgalaxy/planning/chapter_briefs/`
- [x] Update actual LaTeX:
  - `00_abstract_highlights.tex`
  - `01_introduction.tex`
  - `05_experimental_setup.tex`
  - `06_results.tex`
  - `07_mechanistic_analysis.tex`
  - `08_discussion.tex`
  - `09_conclusion.tex`
  - `appendix_b_additional_results.tex`

### Task 5: Verification

- [x] Run `conda run -n msfenicsx pytest -v tests/optimizers/test_benchmark_runner_comparisons.py`.
- [x] Query DuckDB / CSV and verify:
  - `main_s4` raw/LLM seed_count `5`
  - `main_s5` raw/LLM seed_count `5`
  - `main_s6` raw/LLM seed_count `5`
  - `mechanism_ablation_s6_seed23` is diagnostic/single-seed and not part of `main_s6`
- [x] Search docs and paper for stale active old representative diagnostic case, obsolete S5 seed-cohort wording, and incomplete-main wording.
- [x] Verify all complete claim evidence paths exist under `paper_database/`.

## Self-Review

- Spec coverage: corrected S5 top5 policy, completed S6 main archive, S6 seed23 mechanism / feedback-off diagnostic, `paper_database/` relocation, archive rebuild, comparison regeneration, DB refresh, docs sync, and LaTeX sync are all represented.
- Placeholder scan: no source paths are omitted for the official S5/S6 main archives.
- Type/path consistency: official archives live under `paper_database/<scenario_id>/archives/`; generated DB lives under `paper_database/paper_experiment_db/`.
- Evidence boundary: seed23 mechanism / feedback-off diagnostic remains diagnostic-only and excluded from S6 main aggregate.
