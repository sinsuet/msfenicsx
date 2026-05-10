# EAAI Paper Brief 计划恢复审计与继续执行记录

日期：2026-05-09

## 1. 本次恢复结论

上一个 session 在上下文压缩附近中断，但磁盘上已经保留了主要 `paper brief` 产物。当前状态不是“计划未开始”，而是：

1. `docs/superpowers/specs/2026-05-09-eaai-paper-writing-governance-design.md` 已生成。
2. 四个章节组 implementation plan 已生成：
   - `docs/superpowers/plans/2026-05-09-eaai-paper-frontmatter-intro-related-plan.md`
   - `docs/superpowers/plans/2026-05-09-eaai-paper-problem-method-plan.md`
   - `docs/superpowers/plans/2026-05-09-eaai-paper-experiments-results-analysis-plan.md`
   - `docs/superpowers/plans/2026-05-09-eaai-paper-discussion-conclusion-integration-plan.md`
3. `paper/els-cas-templates/planning/` 下的 registers 和 chapter briefs 已基本齐全。
4. `paper/els-cas-templates/sections/05_experimental_setup.tex`、`06_results.tex`、`07_mechanistic_analysis.tex` 已存在正文草稿，但它们是在 brief approval gate 之前生成的后续产物，应视为草稿而不是最终集成正文。

关键风险：仓库 `.gitignore` 当前忽略整个 `paper/` 目录。因此 `paper/els-cas-templates/planning/` 与 `sections/` 中的产物虽然存在于磁盘，但默认不会进入 git status / git diff。若需要版本化论文写作产物，需要后续单独调整 `.gitignore` 或使用显式 `git add -f` 策略。

## 2. 已恢复的 planning 产物

### 2.1 Global registers

已存在：

- `paper/els-cas-templates/planning/narrative_register.md`
- `paper/els-cas-templates/planning/terminology_register.md`
- `paper/els-cas-templates/planning/citation_register.md`
- `paper/els-cas-templates/planning/evidence_register.md`
- `paper/els-cas-templates/planning/figure_table_register.md`

其中 `narrative_register.md` 已冻结核心句：

> The LLM routes thermal-design operators; it does not generate layouts.

`evidence_register.md` 已明确 `single-seed`、`aggregate`、`diagnostic`、`pending`、`hypothesis` 五类证据状态，并把 S5 seed-11 legacy semantic ablation、S5 raw/union aggregate context、S6 seed-wise raw/union observations、以及 active S4/S5/S6 final-block pending status 分开。

### 2.2 Chapter briefs

已存在：

- `00_abstract_highlights_brief.md`
- `01_introduction_brief.md`
- `02_related_work_brief.md`
- `03_problem_benchmark_brief.md`
- `04_method_brief.md`
- `05_experimental_setup_brief.md`
- `06_results_brief.md`
- `07_mechanistic_analysis_brief.md`
- `08_discussion_brief.md`
- `09_conclusion_brief.md`
- `appendix_brief.md`

本次恢复过程中已修正 05-07 briefs 与 `figure_table_register.md` 的状态不一致问题：实验、结果和机制分析中的 Table 4-6、Fig. 4-7 已登记回 `figure_table_register.md`。

## 3. 当前证据状态

### 3.1 可以进入主文但必须标为 single-seed

S5 seed-11 三方 semantic ablation 是当前最干净的 LLM semantic-control 证据：

- comparison bundle: `scenario_runs/compares/s5_seed11_raw_union-neutral_llm-deepseek`
- scope: `NSGA-II` vs `NSGA-II + Union Operators` vs `NSGA-II + LLM Semantic Controller`
- scenario: `s5_aggressive15`
- benchmark seed / algorithm seed: `11 / 1011`
- formal S5 setting: `population_size=40`, `num_generations=32`, nominal budget `1280`

已核对的核心数字：

| Evidence ID | 结论边界 |
|---|---|
| `E-S5-SEM-001` | common PDE cutoff `907` 下，LLM gradient RMS `13.661` 低于 raw `16.383` 和 neutral union `14.730`；feasible rate 为 `0.847`。 |
| `E-S5-SEM-002` | endpoint final HV：raw `822.916`，neutral union `891.542`，LLM `962.906`；LLM vs raw 为 `+17.01%`。 |
| `E-S5-SEM-003` | endpoint 上 LLM 的 gradient RMS、HV、first feasible PDE、feasible rate 优于 neutral union，但 peak temperature 不优于 raw。 |

写作口径：只能写成 “In the S5 seed-11 semantic ablation...”，不能写成跨 seed、跨 S4/S5/S6 的最终统计结论。

### 3.2 可以作为 aggregate context，但不是 LLM aggregate

S5 raw/union five-seed suite 可作为 structured operator support 的 aggregate context：

- bundle: `scenario_runs/s5_aggressive15/0509_0130__raw_union/comparisons/aggregate/raw_vs_union`
- seeds: `11, 17, 23, 29, 31`
- claim: union 改善 mean gradient RMS 和 mean final HV，但 raw 有更低 mean peak temperature。

这不是 `raw vs neutral union vs LLM` aggregate evidence，不能替代 S5 seed-11 semantic ablation，也不能证明 LLM aggregate dominance。

### 3.3 只能作为 seed-wise / final-block pending

S6 raw/union 当前只有 by-seed observations：

- seed 11: union 改善 peak、gradient、feasible rate、HV 和 first feasible PDE。
- seeds 17 / 23 / 29: mixed。
- seed 31: failed。

因此 S6 raw/union 不能写成 aggregate conclusion。

active S4/S5/S6 final-block LLM scale-up 仍是 pending：

- Main block 需要 S4/S5/S6、5 seeds、raw vs DeepSeek LLM 的 suite-owned comparison bundles。
- Semantic Ablation、Mechanism Ablation、Model Sensitivity、Algorithm Baseline 均以 `evidence_register.md` 中的 final experiment block 为准。
- 历史 S6 LLM profile run status 和已退役 scale run status 只能作为仓库审计背景，不再作为论文 pending claim。

## 4. 已存在正文草稿的处理建议

`paper/els-cas-templates/sections/05_experimental_setup.tex`、`06_results.tex`、`07_mechanistic_analysis.tex` 已经存在，并且内容大体遵循 `evidence_register.md` 的保守口径。

但根据 governance spec，正文应在对应 chapter brief 经用户确认后再写。因此这三个文件当前应标记为：

- useful draft material；
- not yet approved manuscript text；
- not yet safe for final `manuscript.tex` integration。

下一步如果继续正文写作，应先让用户确认 00-09 briefs 和 appendix brief，再决定是否保留、重写或拆分这些草稿。

## 5. 本次继续实现已完成

本次 session 已完成：

1. 审计 git 状态，确认新增 docs plan/spec 文件未跟踪，`paper/` 产物被 `.gitignore` 忽略。
2. 审计 `paper/els-cas-templates/planning/` 中的 registers 和 chapter briefs。
3. 核对 S5 semantic ablation 的关键 CSV / PDF / JSON artifact 路径存在。
4. 核对核心数字与 `evidence_register.md` 口径一致。
5. 同步 `figure_table_register.md`，补入：
   - `Table 4`
   - `Table 5`
   - `Fig. 4`
   - `Fig. 5`
   - `Table 6`
   - `Fig. 6`
   - `Fig. 7`
6. 更新 `05_experimental_setup_brief.md`、`06_results_brief.md`、`07_mechanistic_analysis_brief.md`、`appendix_brief.md` 中的图表登记表头和状态说明。

## 6. 下一步执行顺序

推荐按以下顺序继续：

1. 先决定 `paper/` 产物是否需要纳入 git 跟踪。
2. 用户审阅并确认 00-09 chapter briefs、appendix brief 和五个 registers。
3. 若确认 brief，可进入正文阶段：
   - 优先补 `00_abstract_highlights.tex`、`01_introduction.tex`、`02_related_work.tex`、`03_problem_benchmark.tex`、`04_method.tex`。
   - 已存在的 `05-07` 正文草稿可作为候选输入，但必须重新过 evidence gate。
4. Related Work 正文写作前必须先把关键 citation 从 `candidate` / `screened` 升级到 `verified`，并写入 `references/bibtex/verified.bib`。
5. Results / Discussion / Conclusion 必须继续遵守 `evidence_register.md`，不能把 active final-block pending 条目写成 confirmed result。

## 7. 阻塞项

当前继续到正式论文正文的主要阻塞项是：

- `paper/` ignored：产物不进入正常 git diff。
- chapter brief 尚未显式经过用户 approval gate。
- citation register 仍无足够 `verified` 条目，Related Work 正文不能安全展开。
- S4/S5/S6 final main-block comparison bundle 未完成，不能支撑跨尺度 LLM dominance。
- 已存在 05-07 正文草稿需要重新按 brief/evidence gate 审查。
