# S7/Gemma4 Retirement And S4-S6 Experiment Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 彻底退役 `s7_aggressive25` 与 `gemma4`，并把 active 论文实验口径统一到 S4/S5/S6 与 `deepseek_v4_flash` 默认模型。

**Architecture:** 删除 S7 场景、优化规格、batch 与测试入口，不保留兼容路径。LLM profile registry 与 S4/S5/S6 active LLM specs 统一使用 `deepseek_v4_flash`。README、AGENTS、CLAUDE 与论文计划改成最终五块实验矩阵，避免后续写作继续引用 S7 或 Gemma4。

**Tech Stack:** YAML, Markdown, pytest, repository scenario specs.

---

### Task 1: Delete S7 Runtime And Test Surface

**Files:**
- Delete: `scenarios/templates/s7_aggressive25.yaml`
- Delete: `scenarios/evaluation/s7_aggressive25_eval.yaml`
- Delete: `scenarios/optimization/s7_aggressive25_raw.yaml`
- Delete: `scenarios/optimization/s7_aggressive25_union.yaml`
- Delete: `scenarios/optimization/s7_aggressive25_llm.yaml`
- Delete: `scenarios/optimization/s7_aggressive25_spea2_raw.yaml`
- Delete: `scenarios/optimization/s7_aggressive25_moead_raw.yaml`
- Delete: `scenarios/optimization/profiles/s7_aggressive25_raw.yaml`
- Delete: `scenarios/optimization/profiles/s7_aggressive25_union.yaml`
- Delete: `scenarios/optimization/profiles/s7_aggressive25_spea2_raw.yaml`
- Delete: `scenarios/optimization/profiles/s7_aggressive25_moead_raw.yaml`
- Delete: `scenarios/batches/s7_union_only_budgeted.yaml`
- Delete: `tests/schema/test_s7_aggressive25_template.py`
- Delete: `tests/generator/test_s7_aggressive25_template.py`
- Delete: `tests/optimizers/test_s7_aggressive25_specs.py`

- [ ] Delete all listed S7 files.
- [ ] Run `rg -n "s7|S7|aggressive25" scenarios tests README.md AGENTS.md CLAUDE.md docs/superpowers docs/reports`.

### Task 2: Retire Gemma4 And Set DeepSeek Default

**Files:**
- Modify: `llm/openai_compatible/profiles.yaml`
- Modify: `.env.example`
- Modify: `scenarios/optimization/s5_aggressive15_llm.yaml`
- Modify: `scenarios/optimization/s6_aggressive20_llm.yaml`
- Modify: `tests/optimizers/test_llm_profiles.py`
- Modify: `tests/optimizers/test_llm_scenario_config_sync.py`

- [ ] Remove the `gemma4` profile and GEMMA4 env placeholders.
- [ ] Change S5/S6 LLM `provider_profile` to `deepseek_v4_flash`.
- [ ] Update LLM profile tests to cover `deepseek_v4_flash`, not `gemma4`.
- [ ] Update scenario sync tests to cover S4/S5/S6 DeepSeek defaults.

### Task 3: Sync Repository Guidance And Paper Plans

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: active paper planning files under `docs/superpowers/plans/2026-05-09-eaai-paper-*.md`
- Modify: active support specs under `docs/superpowers/specs/`
- Modify: active reports under `docs/reports/`

- [ ] Replace the old S5/S6/S7 mainline with S4/S5/S6.
- [ ] State the final experiment matrix:
  - Main: S4/S5/S6, 5 seeds, `raw` vs `llm_deepseek_v4_flash`
  - Semantic Ablation: S4, 5 seeds, `raw / union / llm`
  - Mechanism Ablation: S5, 5 seeds, `llm_direct` vs ours
  - Model Sensitivity: S5 seed11, DeepSeek/Qwen/Kimi/GPT/MiMo
  - Algorithm Baseline: S5, 5 seeds, NSGA-II/SPEA2/MOEA/D raw
- [ ] Remove Gemma4 from examples, profile lists, and resource guidance.

### Task 4: Verify Focused Contract Surface

**Files:**
- Test: `tests/optimizers/test_llm_profiles.py`
- Test: `tests/optimizers/test_llm_scenario_config_sync.py`
- Test: `tests/optimizers/test_raw_backbone_specs.py`
- Test: `tests/schema/test_s4_aggressive10_template.py`
- Test: `tests/generator/test_s4_aggressive10_generator.py`
- Test: `tests/optimizers/test_s4_aggressive10_specs.py`
- Test: `tests/optimizers/test_s5_aggressive15_specs.py`
- Test: `tests/optimizers/test_s6_aggressive20_specs.py`

- [ ] Run focused pytest command covering the changed scenario/model contracts.
- [ ] Run final `rg` checks for retired terms.
