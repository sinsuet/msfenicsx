# S4 Seed Cohort Rearchive And Paper Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 paper-facing S4 main/semantic cohort 从旧 `11,17,23,29,31` 冻结切换为 `11,13,17,19,23`，并同步 archive、comparison、paper experiment DB、论文计划、正文和仓库状态文档。

**Architecture:** 不手改原始 seed-run 结论，不把旧 artifact 静默删除。保留旧 S4 archive 为 superseded 审计目录，在原 official archive 路径重建新的 5-seed suite。Comparison planner 先规范化 `nsga2_llm:*` 与 `llm:*` 的 method identity，避免来自不同 batch 的 LLM seed 被拆成两个方法。所有论文结果表和叙述只从重建后的 suite-owned `comparisons/` 和 `paper_database/paper_experiment_db/` 导出。

**2026-05-11 status:** This S4-specific plan has been executed and superseded by `docs/superpowers/plans/2026-05-11-s5-s6-main-results-paper-sync.md` for whole Stage A reporting. Keep this file as an audit plan for the S4 cohort change only.

**Tech Stack:** Python, YAML/CSV/JSON artifact manipulation, existing `optimizers.benchmark_runner.comparisons.plan_campaign_comparisons`, DuckDB, pytest focused optimizer tests, Markdown/LaTeX documentation.

---

## Final S4 Cohort Contract

- S4 main and S4 semantic ablation paper-facing seeds: `[11, 13, 17, 19, 23]`
- Methods in S4 semantic archive: `raw`, `union`, `llm-deepseek-v4-flash`
- Methods used for S4 main subset: `raw`, `llm-deepseek-v4-flash`
- Formal S4 budget: `population_size=32`, `num_generations=16`, nominal budget `512`
- Algorithm seed offset: `1000`
- S6 main is handled by the later Stage A sync plan; do not use S6 feedback-off as main evidence.
- Do not restore or execute `llm_direct`.

## Source Mapping

| Seed | raw source | union source | LLM source |
|---:|---|---|---|
| 11 | `paper_database/s4_aggressive10/archives/0511_archive__raw_union_llm-deepseek_v4_flash_5seed/raw/seeds/seed-11` | `.../union/seeds/seed-11` | `.../llm-deepseek-v4-flash/seeds/seed-11` |
| 13 | `scenario_runs/s4_aggressive10/0510_2234__raw_union_llm-deepseek_v4_flash/raw/seeds/seed-13` | `.../union/seeds/seed-13` | `.../nsga2-llm-deepseek-v4-flash/seeds/seed-13` |
| 17 | `paper_database/s4_aggressive10/archives/0511_archive__raw_union_llm-deepseek_v4_flash_5seed/raw/seeds/seed-17` | `.../union/seeds/seed-17` | `.../llm-deepseek-v4-flash/seeds/seed-17` |
| 19 | `scenario_runs/s4_aggressive10/0510_2234__raw_union_llm-deepseek_v4_flash/raw/seeds/seed-19` | `.../union/seeds/seed-19` | `.../nsga2-llm-deepseek-v4-flash/seeds/seed-19` |
| 23 | `paper_database/s4_aggressive10/archives/0511_archive__raw_union_llm-deepseek_v4_flash_5seed/raw/seeds/seed-23` | `.../union/seeds/seed-23` | `.../llm-deepseek-v4-flash/seeds/seed-23` |

## Tasks

### Task 1: Comparison Method Canonicalization

**Files:**
- Modify: `optimizers/benchmark_runner/comparisons.py`
- Modify: `tests/optimizers/test_benchmark_runner_comparisons.py`

- [ ] Add a failing test proving `nsga2_llm:deepseek_v4_flash` and `llm:deepseek_v4_flash` canonicalize to `llm-deepseek_v4_flash`.
- [ ] Run the focused test and confirm it fails before implementation.
- [ ] Implement minimal method-id canonicalization in `comparisons.py`.
- [ ] Run focused comparison tests and confirm pass.

### Task 2: Rebuild Official S4 Archive

**Files:**
- Rename/source-preserve: `paper_database/s4_aggressive10/archives/0511_archive__raw_union_llm-deepseek_v4_flash_5seed`
- Create: `paper_database/s4_aggressive10/archives/0511_archive__raw_union_llm-deepseek_v4_flash_5seed`
- Create: `paper_database/s4_aggressive10/archives/0511_archive__raw_union_llm-deepseek_v4_flash_5seed/archive_provenance.yaml`
- Refresh: `paper_database/s4_aggressive10/archives/0511_archive__raw_union_llm-deepseek_v4_flash_5seed/run_index.csv`

- [ ] Move the existing official S4 archive to `...__superseded_20260511_seeds_11_17_23_29_31` if that backup path does not already exist.
- [ ] Copy only seeds `11,13,17,19,23` into the official archive path, with destination method directories `raw`, `union`, and `llm-deepseek-v4-flash`.
- [ ] Write `archive_provenance.yaml` recording source root per seed and method.
- [ ] Rebuild `run_index.csv` with output roots rewritten to the official archive path.

### Task 3: Rebuild S4 Comparisons

**Files:**
- Refresh: `paper_database/s4_aggressive10/archives/0511_archive__raw_union_llm-deepseek_v4_flash_5seed/comparisons/`

- [ ] Run `plan_campaign_comparisons` on the official S4 archive.
- [ ] Verify by-seed comparisons exist only for `11,13,17,19,23`.
- [ ] Verify aggregate comparison path is `comparisons/aggregate/raw_vs_union_vs_llm-deepseek_v4_flash`.

### Task 4: Refresh Paper Experiment DB

**Files:**
- Modify: `paper_database/paper_experiment_db/manifest.yaml`
- Refresh: `paper_database/paper_experiment_db/tables/*.csv`
- Refresh: `paper_database/paper_experiment_db/msfenicsx_experiments.duckdb`

- [ ] Update S4 seeds in the manifest to `[11,13,17,19,23]`.
- [ ] Regenerate completeness/artifact/claim evidence tables.
- [ ] Regenerate seed, aggregate, pairwise, common cutoff, model sensitivity tables.
- [ ] Re-materialize DuckDB from CSV tables.
- [ ] Verify S4 seed metrics contain only `11,13,17,19,23`.

### Task 5: Sync Paper And Repository Wording

**Files:**
- Modify: `scenarios/batches/s4_main_raw_llm_deepseek_budgeted.yaml`
- Modify: `scenarios/batches/s4_semantic_ablation_budgeted.yaml`
- Modify: `docs/superpowers/specs/2026-05-10-final-experiment-database-design.md`
- Modify: `docs/superpowers/plans/2026-05-10-final-experiment-database-and-s5-diagnostic-case.md`
- Modify: `docs/reports/2026-05-10-stage-a-igd-and-paper-assets.md`
- Modify: `paper/msgalaxy/planning/*.md`
- Modify: `paper/msgalaxy/planning/chapter_briefs/*.md`
- Modify: `paper/msgalaxy/sections/*.tex`
- Modify: `README.md`, `AGENTS.md`, `CLAUDE.md`

- [ ] Update active S4 seed policy to `[11,13,17,19,23]`.
- [ ] Remove obsolete active requirements for `llm_direct` and Kimi.
- [ ] Treat GPT-5.5 as a normal model-sensitivity result, not fallback.
- [ ] State S4/S5 aggregate-mean LLM superiority in this S4-specific pass; later Stage A sync promotes S6 main after its official archive is complete.
- [ ] State S6 seed23 mechanism / feedback-off diagnostic is diagnostic, not multi-seed evidence.

### Task 6: Final Verification

**Files:**
- Read generated tables, docs, and tests.

- [ ] Run focused optimizer tests.
- [ ] Verify S4 official archive and paper DB contain only the active S4 seeds.
- [ ] Verify complete claim evidence paths exist.
- [ ] Verify active wording no longer claims old S4 cohort, `llm_direct`, Kimi final requirement, or GPT fallback anomaly.
- [ ] Report generated tables, DuckDB status, nIGD status, and claim evidence status.
