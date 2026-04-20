# Satellite Paper AAAI-26 Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bootstrap a clean `paper/` workspace for the satellite thermal-control paper using the official AAAI-26 template as the initial formatting reference, with aligned Chinese and English drafts.

**Architecture:** Keep the durable writing contract in versioned docs, but implement the actual manuscript scaffold inside the git-ignored `paper/latex/` workspace. Use one shared bibliography file, parallel `sections/zh` and `sections/en` trees, a vendored AAAI-26 template reference under `paper/latex/vendor/`, and separate Chinese/English entry files that preserve the same section structure while allowing Chinese XeLaTeX authoring convenience.

**Tech Stack:** LaTeX (`latexmk`, `xelatex`, `pdflatex`, `biber`, `bibtex`), AAAI-26 official author kit files, a shared `.bib` file with `biblatex/biber` for the Chinese draft and AAAI-compatible `natbib/BibTeX` for the English draft, local `paper/` workspace under WSL.

**Spec:** [docs/superpowers/specs/2026-04-20-satellite-paper-writing-aaai-design.md](../specs/2026-04-20-satellite-paper-writing-aaai-design.md)

---

### Task 1: Vendor AAAI-26 Template And Establish The Paper Tree

**Files:**
- Create: `paper/latex/vendor/aaai26/`
- Create: `paper/latex/sections/zh/`
- Create: `paper/latex/sections/en/`
- Create: `paper/latex/figures/`
- Create: `paper/latex/tables/`
- Create: `paper/latex/build/`
- Create: `paper/latex/refs.bib`

- [ ] **Step 1: Verify the official AAAI-26 kit location before writing files**

Run:

```bash
curl -L --max-time 30 https://aaai.org | grep -oiE 'aaai-26|template' | sort -u
```

Expected:
- output contains `aaai-26`
- output contains `template` or `Template`

- [ ] **Step 2: Create the clean manuscript directory structure**

Run:

```bash
mkdir -p \
  /home/hymn/msfenicsx/paper/latex/vendor/aaai26 \
  /home/hymn/msfenicsx/paper/latex/sections/zh \
  /home/hymn/msfenicsx/paper/latex/sections/en \
  /home/hymn/msfenicsx/paper/latex/figures \
  /home/hymn/msfenicsx/paper/latex/tables \
  /home/hymn/msfenicsx/paper/latex/build
```

Expected:
- all target directories exist under `paper/latex/`

- [ ] **Step 3: Create the shared bibliography seed file**

```bibtex
% paper/latex/refs.bib
@comment{Shared bibliography for both Chinese and English drafts.}
```

- [ ] **Step 4: Verify the directory tree is clean and complete**

Run:

```bash
ls -la /home/hymn/msfenicsx/paper/latex && find /home/hymn/msfenicsx/paper/latex -maxdepth 2 -type d | sort
```

Expected:
- `vendor/aaai26`
- `sections/zh`
- `sections/en`
- `figures`
- `tables`
- `build`
- `refs.bib`

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/plans/2026-04-20-satellite-paper-aaai26-bootstrap.md
git commit -m "docs: add AAAI-26 paper bootstrap plan"
```

### Task 2: Create Parallel Chinese And English Entry Files

**Files:**
- Create: `paper/latex/main_zh.tex`
- Create: `paper/latex/main_en.tex`
- Create: `paper/latex/sections/zh/00_abstract.tex`
- Create: `paper/latex/sections/zh/01_introduction.tex`
- Create: `paper/latex/sections/zh/02_related_work.tex`
- Create: `paper/latex/sections/zh/03_problem_formulation.tex`
- Create: `paper/latex/sections/zh/04_method.tex`
- Create: `paper/latex/sections/zh/05_collapse_and_recovery.tex`
- Create: `paper/latex/sections/zh/06_experiments.tex`
- Create: `paper/latex/sections/zh/07_analysis_and_discussion.tex`
- Create: `paper/latex/sections/zh/08_limitations.tex`
- Create: `paper/latex/sections/zh/09_conclusion.tex`
- Create: `paper/latex/sections/en/00_abstract.tex`
- Create: `paper/latex/sections/en/01_introduction.tex`
- Create: `paper/latex/sections/en/02_related_work.tex`
- Create: `paper/latex/sections/en/03_problem_formulation.tex`
- Create: `paper/latex/sections/en/04_method.tex`
- Create: `paper/latex/sections/en/05_collapse_and_recovery.tex`
- Create: `paper/latex/sections/en/06_experiments.tex`
- Create: `paper/latex/sections/en/07_analysis_and_discussion.tex`
- Create: `paper/latex/sections/en/08_limitations.tex`
- Create: `paper/latex/sections/en/09_conclusion.tex`

- [ ] **Step 1: Write the Chinese entry file with XeLaTeX-capable article scaffold**

```tex
% paper/latex/main_zh.tex
\documentclass[11pt]{ctexart}
\usepackage[a4paper,margin=1in]{geometry}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{amsmath,amssymb}
\usepackage{hyperref}
\usepackage[backend=biber,style=numeric,sorting=nyt]{biblatex}
\addbibresource{refs.bib}

\title{面向卫星热控布局多目标优化的 LLM 在线控制器：公平比较、崩塌模式与分层恢复}
\author{}
\date{}

\begin{document}
\maketitle
\input{sections/zh/00_abstract}
\input{sections/zh/01_introduction}
\input{sections/zh/02_related_work}
\input{sections/zh/03_problem_formulation}
\input{sections/zh/04_method}
\input{sections/zh/05_collapse_and_recovery}
\input{sections/zh/06_experiments}
\input{sections/zh/07_analysis_and_discussion}
\input{sections/zh/08_limitations}
\input{sections/zh/09_conclusion}
\printbibliography
\end{document}
```

- [ ] **Step 2: Write the English entry file aligned to the AAAI-facing section structure**

```tex
% paper/latex/main_en.tex
\documentclass[letterpaper]{article}
\usepackage{aaai26}
\usepackage{times}
\usepackage{helvet}
\usepackage{courier}
\usepackage[hyphens]{url}
\usepackage{graphicx}
\urlstyle{rm}
\def\UrlFont{\rm}
\usepackage{natbib}
\usepackage{caption}
\usepackage{booktabs}
\usepackage{amsmath,amssymb}
\frenchspacing

\title{LLM Inline Control for Satellite Thermal-Control Layout Optimization: Fair Attribution, Collapse Modes, and Layered Recovery}
\author{}
\affiliations{}

\begin{document}
\maketitle
\input{sections/en/00_abstract}
\input{sections/en/01_introduction}
\input{sections/en/02_related_work}
\input{sections/en/03_problem_formulation}
\input{sections/en/04_method}
\input{sections/en/05_collapse_and_recovery}
\input{sections/en/06_experiments}
\input{sections/en/07_analysis_and_discussion}
\input{sections/en/08_limitations}
\input{sections/en/09_conclusion}
\bibliography{refs}
\end{document}
```

- [ ] **Step 3: Create the shared section placeholders for both languages**

```tex
% paper/latex/sections/zh/00_abstract.tex
\begin{abstract}
中文摘要待在后续任务中填充；当前先固定双语稿件结构与引用入口。
\end{abstract}
```

```tex
% paper/latex/sections/zh/01_introduction.tex
\section{引言}

% Satellite thermal-control framing draft goes here.
```

```tex
% paper/latex/sections/zh/02_related_work.tex
\section{相关工作}
```

```tex
% paper/latex/sections/zh/03_problem_formulation.tex
\section{问题定义：高代价评估下的卫星热控布局多目标优化}
```

```tex
% paper/latex/sections/zh/04_method.tex
\section{方法：固定优化边界下的 LLM 在线控制}
```

```tex
% paper/latex/sections/zh/05_collapse_and_recovery.tex
\section{崩塌模式与分层恢复框架}
```

```tex
% paper/latex/sections/zh/06_experiments.tex
\section{实验}
```

```tex
% paper/latex/sections/zh/07_analysis_and_discussion.tex
\section{分析与讨论}
```

```tex
% paper/latex/sections/zh/08_limitations.tex
\section{局限性}
```

```tex
% paper/latex/sections/zh/09_conclusion.tex
\section{结论}
```

```tex
% paper/latex/sections/en/00_abstract.tex
\begin{abstract}
English abstract placeholder aligned with the Chinese source draft.
\end{abstract}
```

```tex
% paper/latex/sections/en/01_introduction.tex
\section{Introduction}
```

```tex
% paper/latex/sections/en/02_related_work.tex
\section{Related Work}
```

```tex
% paper/latex/sections/en/03_problem_formulation.tex
\section{Problem Formulation: Satellite Thermal-Control Layout Optimization under Expensive Evaluation}
```

```tex
% paper/latex/sections/en/04_method.tex
\section{Method: Fixed-Boundary Inline LLM Controller}
```

```tex
% paper/latex/sections/en/05_collapse_and_recovery.tex
\section{Collapse Modes and Layered Recovery}
```

```tex
% paper/latex/sections/en/06_experiments.tex
\section{Experiments}
```

```tex
% paper/latex/sections/en/07_analysis_and_discussion.tex
\section{Analysis and Discussion}
```

```tex
% paper/latex/sections/en/08_limitations.tex
\section{Limitations}
```

```tex
% paper/latex/sections/en/09_conclusion.tex
\section{Conclusion}
```

- [ ] **Step 4: Verify the parallel section trees are symmetric**

Run:

```bash
find /home/hymn/msfenicsx/paper/latex/sections -maxdepth 2 -type f | sort
```

Expected:
- both `sections/zh/` and `sections/en/` contain the same numbered section files `00` through `09`

- [ ] **Step 5: Commit**

```bash
git add /home/hymn/msfenicsx/paper/latex/main_zh.tex /home/hymn/msfenicsx/paper/latex/main_en.tex /home/hymn/msfenicsx/paper/latex/sections /home/hymn/msfenicsx/paper/latex/refs.bib
git commit -m "docs: scaffold bilingual paper manuscript"
```

### Task 3: Populate The Initial Chinese Core Draft And English Alignment Placeholders

**Files:**
- Modify: `paper/latex/sections/zh/00_abstract.tex`
- Modify: `paper/latex/sections/zh/01_introduction.tex`
- Modify: `paper/latex/sections/zh/03_problem_formulation.tex`
- Modify: `paper/latex/sections/en/00_abstract.tex`
- Modify: `paper/latex/sections/en/01_introduction.tex`
- Modify: `paper/latex/sections/en/03_problem_formulation.tex`

- [ ] **Step 1: Write the Chinese abstract draft**

```tex
\begin{abstract}
卫星热控布局设计需要在有限板面空间和有限散热资源下协调多个发热部组件的位置与散热边界，同时兼顾峰值温度安全、温度分布均匀性与工程可行性。这类任务通常依赖高代价数值求解进行评估，因此在有限预算下提升多目标搜索效率，是一个具有明确工程背景的科学优化问题。近年来，大语言模型（LLM）被逐步引入优化流程，但多数工作将其用作离线启发式顾问或候选生成器，往往同时改变表示、先验、预算或搜索空间，使性能提升难以被公平归因。本文将 LLM 定位为固定优化边界下的在线控制器，在共享表示、共享语义算子池、共享 repair/evaluation pipeline 与共享评估预算的前提下，构建 raw、union 与 llm 三类可比较方法，并进一步提出面向控制崩塌模式的分层恢复框架。实验以规范化卫星热控 benchmark 为基础，使用最终性能、进度轨迹、里程碑事件与控制 trace 四层证据链评估方法行为。结果表明，该框架能够在预算匹配条件下稳定改善多目标搜索质量，并使 LLM 驱动优化过程具备更强的可归因性与可审计性。
\end{abstract}
```

- [ ] **Step 2: Write the Chinese introduction draft skeleton with the agreed framing**

```tex
\section{引言}

卫星热控布局设计需要在有限安装空间内布置多个发热部组件，并合理配置散热边界与散热资源，使系统同时满足峰值温度、热分布均匀性及关键器件安全阈值等要求。由于性能评估通常依赖数值求解或仿真计算，该类问题具有高代价、多约束、多目标的典型特征。如何在有限评估预算下提升搜索效率，是一个重要且现实的科学优化问题。

近年来，LLM 被逐步引入优化任务，但大多数工作要么将其作为离线启发式顾问，用于初始化或参数推荐；要么将其作为候选生成器，直接生成设计方案。这类方法往往同时引入额外先验、改变搜索空间或放宽比较边界，从而难以回答“性能提升是否来自控制能力本身”这一核心问题。

本文不将 LLM 视为设计生成器，而是将其视为固定优化边界下的在线控制器。我们在共享表示、共享语义算子池、共享 repair/evaluation pipeline 与共享预算的条件下，仅改变控制决策机制，构造 raw、union 与 llm 三类可比较方法。基于这一设定，本文进一步将控制器失败形式化为若干结构性崩塌模式，并提出一个面向这些崩塌模式的分层恢复框架。

本文的主要贡献包括：\textbf{(1)} 提出面向卫星热控布局多目标优化的公平比较框架；\textbf{(2)} 总结 LLM 控制器在高代价优化闭环中的结构性崩塌模式；\textbf{(3)} 提出与这些崩塌模式对应的分层恢复机制；\textbf{(4)} 构建 summary、timeline、milestone 与 trace 四层可审计实验资产。
```

- [ ] **Step 3: Write the Chinese problem-formulation draft skeleton**

```tex
\section{问题定义：高代价评估下的卫星热控布局多目标优化}

本文考虑一个规范化的卫星面板热控布局任务：多个发热部组件在有限平面区域内布局，散热带或散热边界可在预算约束下调整。优化目标包括最小化峰值温度与最小化温度梯度 RMS，约束包括散热资源预算、关键部组件温限、热分布约束以及几何合法性与可实施性约束。

在本文平台中，`s1_typical` 与 `s2_staged` 分别承担主 benchmark 与过程级分析 benchmark 的角色。它们不是完整工业卫星全系统复刻，而是保留关键工程张力的规范化卫星热控布局 benchmark。
```

- [ ] **Step 4: Write aligned English placeholders that reflect the same claims, but can remain lighter**

```tex
\begin{abstract}
This draft uses the AAAI-26 structure as the initial submission-facing reference. The English abstract remains aligned with the Chinese source draft and will be expanded after the Chinese core text stabilizes.
\end{abstract}
```

```tex
\section{Introduction}

Satellite thermal-control layout design requires placing multiple heat-generating components within limited panel area and limited heat-rejection resources while satisfying peak-temperature, thermal-uniformity, and feasibility constraints under expensive simulation-backed evaluation.

This paper studies LLMs not as direct design generators, but as inline controllers under a fixed optimization boundary with shared representation, shared operator pool, shared repair/evaluation pipeline, and shared evaluation budget.
```

```tex
\section{Problem Formulation: Satellite Thermal-Control Layout Optimization under Expensive Evaluation}

We study a canonicalized satellite thermal-control layout benchmark with continuous placement variables, constrained heat-rejection resources, and simulation-backed multi-objective evaluation.
```

- [ ] **Step 5: Verify the core draft files contain the agreed satellite-first framing**

Run:

```bash
grep -R "satellite\|卫星\|thermal-control\|热控" /home/hymn/msfenicsx/paper/latex/sections/zh /home/hymn/msfenicsx/paper/latex/sections/en
```

Expected:
- matches appear in the Chinese abstract/introduction/problem file
- matches appear in the aligned English abstract/introduction/problem file

- [ ] **Step 6: Commit**

```bash
git add /home/hymn/msfenicsx/paper/latex/sections/zh/00_abstract.tex /home/hymn/msfenicsx/paper/latex/sections/zh/01_introduction.tex /home/hymn/msfenicsx/paper/latex/sections/zh/03_problem_formulation.tex /home/hymn/msfenicsx/paper/latex/sections/en/00_abstract.tex /home/hymn/msfenicsx/paper/latex/sections/en/01_introduction.tex /home/hymn/msfenicsx/paper/latex/sections/en/03_problem_formulation.tex
git commit -m "docs: add initial bilingual paper draft skeleton"
```

### Task 4: Compile And Verify The Chinese And English Entry Files

**Files:**
- Modify: `paper/latex/main_zh.tex`
- Modify: `paper/latex/main_en.tex`
- Modify: `paper/latex/refs.bib`
- Test: `paper/latex/build/`

- [ ] **Step 1: Add one harmless bibliography seed entry so both flows can exercise citation tooling**

```bibtex
@misc{msfenicsx_internal_platform,
  title        = {msfenicsx Internal Platform Notes},
  author       = {Project Team},
  year         = {2026},
  note         = {Internal working reference for manuscript bootstrap}
}
```

- [ ] **Step 2: Add one citation call in each draft to force bibliography resolution**

```tex
% Append to paper/latex/sections/zh/01_introduction.tex
本文平台与实验叙事围绕统一的研究主线持续演化~\cite{msfenicsx_internal_platform}。
```

```tex
% Append to paper/latex/sections/en/01_introduction.tex
The manuscript scaffold is anchored to a single evolving project narrative~\cite{msfenicsx_internal_platform}.
```

- [ ] **Step 3: Run the Chinese build with latexmk and biber support**

Run:

```bash
cd /home/hymn/msfenicsx/paper/latex && latexmk -xelatex -interaction=nonstopmode -outdir=build main_zh.tex
```

Expected:
- exit code 0
- `paper/latex/build/main_zh.pdf` exists
- bibliography resolves without fatal errors

- [ ] **Step 4: Run the English build against the AAAI-26 template reference**

Run:

```bash
cd /home/hymn/msfenicsx/paper/latex && latexmk -pdf -interaction=nonstopmode -outdir=build main_en.tex
```

Expected:
- exit code 0 if `aaai26.sty` is present and the entry file matches the vendored template
- `paper/latex/build/main_en.pdf` exists

- [ ] **Step 5: Verify the build outputs and log cleanliness**

Run:

```bash
ls -la /home/hymn/msfenicsx/paper/latex/build && grep -E "(Fatal error|Undefined control sequence|Emergency stop)" /home/hymn/msfenicsx/paper/latex/build/*.log || true
```

Expected:
- both `main_zh.pdf` and `main_en.pdf` exist
- no fatal log markers are printed

- [ ] **Step 6: Commit**

```bash
git add /home/hymn/msfenicsx/paper/latex
git commit -m "docs: verify bilingual AAAI-26 paper scaffold builds"
```

## Self-Review

- **Spec coverage:** This plan covers the full spec contract: clean `paper/` structure, AAAI-based bootstrap, shared bibliography, Chinese-first/English-aligned dual entry files, and build verification.
- **Placeholder scan:** The only remaining placeholders are intentional manuscript placeholders inside early English sections and late Chinese sections, which are allowed because this plan is only for the initial scaffold and explicitly targets section skeleton creation rather than the full finished paper.
- **Type consistency:** File names, section numbering, bibliography file names, and build directory names are consistent across all tasks.

Plan complete and saved to `docs/superpowers/plans/2026-04-20-satellite-paper-aaai26-bootstrap.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
