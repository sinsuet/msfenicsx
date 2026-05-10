# EAAI Paper Writing Governance Design

> Status: writing-governance design for staged discussion and later parallel drafting.

## 1. Goal

为 `paper/els-cas-templates` 中的 EAAI 论文建立一套可分阶段确认、可并行执行、可保持全文一致性的写作机制。

这份 spec 不直接写论文正文，而是定义：

- 全文核心叙事和贡献口径；
- 每章先讨论再写作的 `chapter brief` 流程；
- 文献、图表、实验结果、术语和 claim 的统一 register；
- 九章论文如何拆成若干章节组计划；
- 什么时候可以并行写正文，什么时候必须先暂停确认。

## 2. Why This Is Needed

当前论文不是普通“按大纲填文字”的写作任务。贡献表述、baseline 口径、实验结果、文献定位和图表叙事高度耦合。仅靠一次性全局大纲会出现几个问题：

- Introduction 的贡献颗粒度可能和 Method 的机制细节不匹配；
- Related Work 可能因为方法边界没冻结而发散；
- Results 可能引用未统一 reference point 或 unmatched run root；
- 图表编号、caption claim 和正文叙事容易漂移；
- 并行对话写作会丢失上下文，导致术语和 claim 不一致。

因此采用“总体 spec + 章节组 plan + 逐章 brief + register 控制”的工作流。

## 3. Core Narrative

全文核心记忆句：

> The LLM routes thermal-design operators; it does not generate layouts.

论文不应被表述为“LLM 直接优化卫星热布局”或“新 metaheuristic”。准确定位是：

> LLM-guided constrained thermal-semantic operator selection for high-dimensional PDE-constrained satellite thermal layout optimization.

## 4. Contribution Policy

贡献列表放在 Introduction 结尾。Abstract 不逐条列贡献，只压缩成核心方法和应用验证。

推荐英文贡献段：

> This paper makes three contributions. First, we introduce **LLM-guided constrained thermal-semantic operator selection**, which reframes satellite thermal layout search as state-to-operator matching over physically meaningful thermal-design actions rather than direct coordinate perturbation or layout generation. Second, we formulate an **engineering-safe LLM-in-the-loop optimization paradigm**, where the language model is confined to semantic control while deterministic optimization and physics simulation retain authority over feasibility, selection, and validation. Third, we validate the paradigm on **high-dimensional PDE-constrained satellite thermal layout optimization**, showing that semantic operator control improves Pareto-front quality, thermal-gradient reduction, and feasible-search efficiency over native NSGA-II and an operator-matched non-semantic control baseline under matched expensive-evaluation budgets.

对应中文口径：

1. **提出一种 LLM 引导的受约束热语义算子选择机制。** 将卫星热布局搜索从低层坐标扰动提升为“热状态到热设计算子”的语义匹配问题；LLM 不直接生成布局，而是在固定热语义动作空间中选择合适设计动作。
2. **提出一种面向昂贵物理优化的工程安全 LLM-in-the-loop 搜索范式。** LLM 被限制在语义决策层，物理求解、合法性维护和多目标选择保留在确定性优化与仿真组件中，从而兼顾语义推理、工程可控性和可复现实验评估。
3. **在高维 PDE 约束的卫星热控布局优化中验证该范式的有效性。** 在散热资源受限、几十维连续布局变量、昂贵 PDE 热仿真评估的卫星板级组件布局任务中，与原生 NSGA-II 和算子匹配的非语义控制基线做同预算比较，展示 Pareto 前沿质量、温度梯度降低和可行搜索效率的改进。

不要把以下内容写成贡献点：

- `S4/S5/S6` benchmark 本身。它们是问题定义和验证载体。
- `raw -> union -> llm` 消融链。它是实验设计，不是单独创新。
- `guardrail / repair / cheap constraints / PDE solver` 细节清单。它们属于 Method 机制。
- manifest-backed artifacts。它们属于可复现性和机制分析支撑。

## 5. Paper Structure

主文九章：

1. Introduction
2. Related Work
3. Problem Formulation and Benchmark
4. Semantic Operator Control Method
5. Experimental Setup
6. Results
7. Mechanistic Analysis
8. Discussion and Limitations
9. Conclusion

Appendix：

- Artifact contracts and schemas
- Additional seed-level results
- Prompt/state projection examples with sensitive fields removed
- Solver and visualization details

## 6. Chapter Group Plans

九章不逐章单独建 plan，而按依赖关系拆成四个章节组：

| Plan | Scope | Why Grouped |
|---|---|---|
| Front Matter, Introduction, Related Work | Abstract/highlights, §1, §2 | 冻结故事线、贡献和文献定位；不能和 Method 脱节 |
| Problem and Method | §3, §4 | 冻结问题形式化、符号、方法名、operator taxonomy、算法伪代码 |
| Experiments, Results, Mechanistic Analysis | §5, §6, §7 | 冻结 baseline、budget、metric、artifact-backed evidence 和 trace 解释 |
| Discussion, Conclusion, Appendix, Integration | §8, §9, Appendix, final compile | 汇总限制、结论、补充材料和全文一致性 |

每个章节组 plan 的产物不是直接正文，而是：

- 对应章节的 `chapter brief`；
- register 更新；
- 用户确认后的正文写作入口。

## 7. Planning Artifacts

推荐在论文目录下维护写作控制文件：

```text
paper/els-cas-templates/planning/
  narrative_register.md
  terminology_register.md
  citation_register.md
  figure_table_register.md
  evidence_register.md
  chapter_briefs/
    01_introduction_brief.md
    02_related_work_brief.md
    03_problem_benchmark_brief.md
    04_method_brief.md
    05_experimental_setup_brief.md
    06_results_brief.md
    07_mechanistic_analysis_brief.md
    08_discussion_brief.md
    09_conclusion_brief.md
```

这些文件是正文并行写作时的共享上下文。`docs/superpowers/plans/` 中的计划负责指导创建和维护它们。

## 7.1 LaTeX Compile Hygiene

正式稿和 smoke check 的 LaTeX 编译都必须从 `paper/els-cas-templates` 执行，并把所有编译产物写入 `paper/els-cas-templates/compile/`。推荐命令：

```bash
cd paper/els-cas-templates
mkdir -p compile
latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=compile manuscript.tex
```

如果手动调用 `pdflatex` / `bibtex`，也必须使用 `-output-directory=compile`，并在需要时对 `compile/manuscript` 运行 `bibtex`。模板根目录和 `sections/` 目录只保留源码、CAS class/style、规划文件和人工维护资源；不要留下 `.aux`、`.log`、`.out`、`.fls`、`.fdb_latexmk`、`.synctex.gz` 或临时 PDF。

## 8. Register Responsibilities

### 8.1 `narrative_register.md`

记录：

- 核心记忆句；
- 三点贡献；
- Abstract 和 Introduction 的分工；
- 每章 reader takeaway；
- 禁止口径。

### 8.2 `terminology_register.md`

固定术语：

- `LLM-guided constrained thermal-semantic operator selection`
- `engineering-safe LLM-in-the-loop optimization paradigm`
- `high-dimensional PDE-constrained satellite thermal layout optimization`
- `operator-matched non-semantic control baseline`
- `NSGA-II + LLM Semantic Controller`
- `NSGA-II + Union Operators`

### 8.3 `citation_register.md`

每条文献必须登记：

- citation key；
- title/authors/year/venue；
- DOI/arXiv/publisher URL；
- target section；
- why cited；
- status: `candidate`, `verified`, `rejected`。

正文只能使用 `verified` citation。

### 8.4 `figure_table_register.md`

每个 figure/table 必须登记：

- ID；
- caption claim；
- target section；
- data source；
- generation script or source file；
- current status；
- owner plan。

正文 worker 不自行分配图表编号。

### 8.5 `evidence_register.md`

所有结果 claim 必须登记：

- claim text；
- artifact path；
- scenario；
- benchmark seed；
- algorithm seed；
- budget；
- metric；
- comparison scope；
- status: `single-seed`, `aggregate`, `diagnostic`, `hypothesis`。

`hypothesis` 不允许进入 Results 主结论。

## 9. Chapter Brief Protocol

每章正文开始前必须先形成并确认 `chapter brief`。

模板：

```markdown
# Chapter XX Brief: <title>

## 1. Role in the Paper
- 本章回答什么问题。
- 本章支撑哪一个 contribution / claim。
- 本章不能承担什么任务。

## 2. Reader Takeaway
- 读者读完本章必须记住的一句话。

## 3. Section Outline
- 小节标题。
- 每小节 3 到 5 个必须覆盖的论点。
- 每小节不超过 1 个主 claim。

## 4. Required Inputs
- 代码路径。
- artifact 路径。
- 需要核验的文献。
- 需要引用的 figure/table。

## 5. Outputs to Other Chapters
- 本章定义的术语。
- 后文会复用的符号。
- 后文会引用的 figure/table/result。

## 6. Open Decisions
- 需要用户确认的叙事选择。
- 需要等实验完成的结果槽位。

## 7. Quality Gate
- 写完后必须满足的检查项。
```

## 10. Execution Gates

### Gate A: Global Narrative Freeze

必须先确认：

- 三点贡献；
- Abstract/Introduction 分工；
- 方法名；
- baseline 名称；
- 禁止口径。

### Gate B: Chapter Brief Approval

每个章节组先产出 brief，用户确认后才能写正文。

### Gate C: Parallel Drafting

并行写作只允许在对应 brief 已确认后开始。

### Gate D: Integration Review

正文合并后检查：

- 贡献是否前后一致；
- 文献是否都已核验；
- 图表编号是否稳定；
- 数字是否都有 artifact path；
- separate run roots 的比较是否受控；
- failed runs 和 partial results 是否可见。

## 11. Current Source Anchors

当前应作为计划输入的本地文件：

- `paper/els-cas-templates/2026-05-09-eaai-paper-parallel-writing-spec-plan.md`
- `docs/ss.txt`
- `scenario_runs/compares/s5_seed11_raw_union-neutral_llm-deepseek/s5_seed11_semantic_ablation_report.md`
- `scenario_runs/compares/s5_seed11_raw_union-neutral_llm-deepseek/analytics/summary_rows.csv`
- `scenario_runs/compares/s5_seed11_raw_union-neutral_llm-deepseek/analytics/common_pde_cutoff.csv`
- `scenario_runs/compares/s5_seed11_raw_union-neutral_llm-deepseek/analytics/operator_distribution.csv`
- `README.md`

## 12. Non-Goals

- 本 spec 不直接写正文。
- 本 spec 不冻结最终实验数字。
- 本 spec 不决定最终投稿标题。
- 本 spec 不替代每章 brief 的细节讨论。
- 本 spec 不允许把未完成 S4/S5/S6 final experiment block 写成已验证主结论。
