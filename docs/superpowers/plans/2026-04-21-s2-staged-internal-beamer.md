# S2 Staged Internal Beamer Deck Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one Chinese Beamer deck for the current `s2_staged` internal group meeting, translating the mechanism-first paper narrative into a stable 18–20 minute slide deck with curated local assets.

**Architecture:** Keep the deck separate from the manuscript by adding a dedicated Beamer entry file, five section files organized by argument block, and one Beamer-local asset directory that stores curated copies of the figures the slides depend on. Compile with XeLaTeX into `paper/latex/build/beamer_zh/`, so the manuscript and talk can evolve independently while sharing the same scientific story.

**Tech Stack:** LaTeX Beamer, XeLaTeX / latexmk, existing TikZ-generated PDF figures under `paper/latex/build/tikzz/`, existing PNG evidence figures under `scenario_runs/compare_reports/s2_staged/` and `scenario_runs/s2_staged/`.

**Execution note:** `paper/` is a git-ignored workspace in this repository, so this plan uses verification checkpoints instead of git commits for slide-source progress inside `paper/`. Only the spec/plan documents under `docs/superpowers/` are versioned in git.

**Spec:** [docs/superpowers/specs/2026-04-21-s2-staged-internal-beamer-design.md](../specs/2026-04-21-s2-staged-internal-beamer-design.md)

---

## File Map

**Create:**
- `paper/latex/main_beamer_zh.tex` — Beamer entry file.
- `paper/latex/sections/beamer_zh/00_title_and_questions.tex` — Slides 1–2.
- `paper/latex/sections/beamer_zh/01_boundary_and_problem.tex` — Slides 3–5.
- `paper/latex/sections/beamer_zh/02_method_and_mechanism.tex` — Slides 6–10.
- `paper/latex/sections/beamer_zh/03_evidence_and_results.tex` — Slides 11–17.
- `paper/latex/sections/beamer_zh/04_conclusion_and_next.tex` — Slides 18–20.
- `paper/latex/figures/beamer_internal/README.txt` — Asset manifest for copied figures.

**Create or populate with copied assets:**
- `paper/latex/figures/beamer_internal/fixed_boundary_modes_a1.pdf`
- `paper/latex/figures/beamer_internal/inline_control_loop_a1.pdf`
- `paper/latex/figures/beamer_internal/taxonomy_recovery_map_a1.pdf`
- `paper/latex/figures/beamer_internal/evidence_asset_map_a1.pdf`
- `paper/latex/figures/beamer_internal/summary_overview.png`
- `paper/latex/figures/beamer_internal/progress_dashboard.png`
- `paper/latex/figures/beamer_internal/layout_raw.png`
- `paper/latex/figures/beamer_internal/layout_union.png`
- `paper/latex/figures/beamer_internal/layout_llm.png`
- `paper/latex/figures/beamer_internal/temp_raw.png`
- `paper/latex/figures/beamer_internal/temp_union.png`
- `paper/latex/figures/beamer_internal/temp_llm.png`
- `paper/latex/figures/beamer_internal/grad_raw.png`
- `paper/latex/figures/beamer_internal/grad_union.png`
- `paper/latex/figures/beamer_internal/grad_llm.png`
- `paper/latex/figures/beamer_internal/objective_progress.png`
- `paper/latex/figures/beamer_internal/operator_phase_heatmap.png`

**Verify:**
- `paper/latex/build/beamer_zh/main_beamer_zh.pdf`

---

### Task 1: Create the Beamer source tree and curated asset directory

**Files:**
- Create: `paper/latex/main_beamer_zh.tex`
- Create: `paper/latex/sections/beamer_zh/00_title_and_questions.tex`
- Create: `paper/latex/sections/beamer_zh/01_boundary_and_problem.tex`
- Create: `paper/latex/sections/beamer_zh/02_method_and_mechanism.tex`
- Create: `paper/latex/sections/beamer_zh/03_evidence_and_results.tex`
- Create: `paper/latex/sections/beamer_zh/04_conclusion_and_next.tex`
- Create: `paper/latex/figures/beamer_internal/README.txt`

- [ ] **Step 1: Create the missing directories before writing files**

Run:

```bash
mkdir -p \
  /home/hymn/msfenicsx/paper/latex/sections/beamer_zh \
  /home/hymn/msfenicsx/paper/latex/figures/beamer_internal \
  /home/hymn/msfenicsx/paper/latex/build/beamer_zh
```

Expected:
- all three directories exist
- no existing manuscript files are modified

- [ ] **Step 2: Seed the Beamer asset manifest file**

Create `paper/latex/figures/beamer_internal/README.txt` with this exact content:

```text
S2 staged internal Beamer asset manifest

This directory stores stable local copies of the figures used by main_beamer_zh.tex.
Do not point slides at deep scenario_runs paths once the copies are in place.

Expected assets:
- fixed_boundary_modes_a1.pdf
- inline_control_loop_a1.pdf
- taxonomy_recovery_map_a1.pdf
- evidence_asset_map_a1.pdf
- summary_overview.png
- progress_dashboard.png
- layout_raw.png
- layout_union.png
- layout_llm.png
- temp_raw.png
- temp_union.png
- temp_llm.png
- grad_raw.png
- grad_union.png
- grad_llm.png
- objective_progress.png
- operator_phase_heatmap.png
```

- [ ] **Step 3: Create placeholder section files so the entry file can compile incrementally**

Create these five files with this minimal content:

```tex
% paper/latex/sections/beamer_zh/00_title_and_questions.tex
\begin{frame}{占位：标题与问题}
  占位。
\end{frame}
```

```tex
% paper/latex/sections/beamer_zh/01_boundary_and_problem.tex
\begin{frame}{占位：比较边界}
  占位。
\end{frame}
```

```tex
% paper/latex/sections/beamer_zh/02_method_and_mechanism.tex
\begin{frame}{占位：方法与机制}
  占位。
\end{frame}
```

```tex
% paper/latex/sections/beamer_zh/03_evidence_and_results.tex
\begin{frame}{占位：证据与结果}
  占位。
\end{frame}
```

```tex
% paper/latex/sections/beamer_zh/04_conclusion_and_next.tex
\begin{frame}{占位：结论与下一步}
  占位。
\end{frame}
```

- [ ] **Step 4: Write the Beamer entry file with a compile-safe Chinese theme scaffold**

Create `paper/latex/main_beamer_zh.tex` with this exact content:

```tex
\documentclass[10pt,aspectratio=169]{beamer}
\usepackage[UTF8]{ctex}
\usetheme{default}
\usecolortheme{default}
\setbeamertemplate{navigation symbols}{}
\setbeamertemplate{footline}[frame number]
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{amsmath,amssymb}
\usepackage{tikz}
\usetikzlibrary{positioning,fit,calc}
\usepackage{hyperref}

\definecolor{MainBlue}{HTML}{3A86C8}
\definecolor{SoftBlue}{HTML}{EAF3FB}
\definecolor{AccentOrange}{HTML}{E67E22}
\definecolor{SoftOrange}{HTML}{FDF1E3}
\definecolor{RouteGray}{HTML}{333333}
\definecolor{SoftGreen}{HTML}{E8F5EC}

\setbeamercolor{title}{fg=MainBlue}
\setbeamercolor{frametitle}{fg=MainBlue}
\setbeamercolor{structure}{fg=MainBlue}
\setbeamercolor{normal text}{fg=RouteGray,bg=white}
\setbeamercolor{block title}{fg=white,bg=MainBlue}
\setbeamercolor{block body}{fg=RouteGray,bg=SoftBlue}
\setbeamerfont{title}{series=\bfseries,size=\LARGE}
\setbeamerfont{frametitle}{series=\bfseries,size=\large}

\title{面向卫星热控布局多目标优化的 LLM 在线控制器}
\subtitle{组会汇报：公平比较、崩塌模式与分层恢复}
\author{}
\institute{}
\date{2026-04-21}

\begin{document}

\input{sections/beamer_zh/00_title_and_questions}
\input{sections/beamer_zh/01_boundary_and_problem}
\input{sections/beamer_zh/02_method_and_mechanism}
\input{sections/beamer_zh/03_evidence_and_results}
\input{sections/beamer_zh/04_conclusion_and_next}

\end{document}
```

- [ ] **Step 5: Run a first compile to verify the scaffold builds before adding real content**

Run:

```bash
cd "/home/hymn/msfenicsx/paper/latex" && xelatex -interaction=nonstopmode -halt-on-error -output-directory build/beamer_zh main_beamer_zh.tex
```

Expected:
- `build/beamer_zh/main_beamer_zh.pdf` exists
- the PDF shows 5 placeholder frames

- [ ] **Step 6: Record a scaffold checkpoint**

Run:

```bash
ls -la /home/hymn/msfenicsx/paper/latex/main_beamer_zh.tex /home/hymn/msfenicsx/paper/latex/sections/beamer_zh /home/hymn/msfenicsx/paper/latex/figures/beamer_internal/README.txt
```

Expected:
- the entry file exists
- all five section files exist
- the asset manifest exists

### Task 2: Curate the figure assets into a Beamer-local directory

**Files:**
- Create: `paper/latex/figures/beamer_internal/fixed_boundary_modes_a1.pdf`
- Create: `paper/latex/figures/beamer_internal/inline_control_loop_a1.pdf`
- Create: `paper/latex/figures/beamer_internal/taxonomy_recovery_map_a1.pdf`
- Create: `paper/latex/figures/beamer_internal/evidence_asset_map_a1.pdf`
- Create: `paper/latex/figures/beamer_internal/summary_overview.png`
- Create: `paper/latex/figures/beamer_internal/progress_dashboard.png`
- Create: `paper/latex/figures/beamer_internal/layout_raw.png`
- Create: `paper/latex/figures/beamer_internal/layout_union.png`
- Create: `paper/latex/figures/beamer_internal/layout_llm.png`
- Create: `paper/latex/figures/beamer_internal/temp_raw.png`
- Create: `paper/latex/figures/beamer_internal/temp_union.png`
- Create: `paper/latex/figures/beamer_internal/temp_llm.png`
- Create: `paper/latex/figures/beamer_internal/grad_raw.png`
- Create: `paper/latex/figures/beamer_internal/grad_union.png`
- Create: `paper/latex/figures/beamer_internal/grad_llm.png`
- Create: `paper/latex/figures/beamer_internal/objective_progress.png`
- Create: `paper/latex/figures/beamer_internal/operator_phase_heatmap.png`

- [ ] **Step 1: Copy the stable paper-facing TikZ figures into the Beamer asset directory**

Run:

```bash
cp \
  /home/hymn/msfenicsx/paper/latex/build/tikzz/fixed_boundary_modes_a1.pdf \
  /home/hymn/msfenicsx/paper/latex/build/tikzz/inline_control_loop_a1.pdf \
  /home/hymn/msfenicsx/paper/latex/build/tikzz/taxonomy_recovery_map_a1.pdf \
  /home/hymn/msfenicsx/paper/latex/build/tikzz/evidence_asset_map_a1.pdf \
  /home/hymn/msfenicsx/paper/latex/figures/beamer_internal/
```

Expected:
- four PDF assets exist under `paper/latex/figures/beamer_internal/`

- [ ] **Step 2: Copy the cross-mode compare-report figures used by the slides**

Run:

```bash
cp \
  /home/hymn/msfenicsx/scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair/figures/summary_overview.png \
  /home/hymn/msfenicsx/paper/latex/figures/beamer_internal/summary_overview.png

cp \
  /home/hymn/msfenicsx/scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair/figures/progress_dashboard.png \
  /home/hymn/msfenicsx/paper/latex/figures/beamer_internal/progress_dashboard.png
```

Expected:
- `summary_overview.png`
- `progress_dashboard.png`

- [ ] **Step 3: Copy the representative raw / union / llm layout and field figures**

Run:

```bash
cp /home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm/raw/seeds/seed-11/figures/layout_final.png /home/hymn/msfenicsx/paper/latex/figures/beamer_internal/layout_raw.png
cp /home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm/union/seeds/seed-11/figures/layout_final.png /home/hymn/msfenicsx/paper/latex/figures/beamer_internal/layout_union.png
cp /home/hymn/msfenicsx/scenario_runs/s2_staged/0421_0207__llm/figures/layout_final.png /home/hymn/msfenicsx/paper/latex/figures/beamer_internal/layout_llm.png

cp /home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm/raw/seeds/seed-11/figures/temperature_field_knee-candidate.png /home/hymn/msfenicsx/paper/latex/figures/beamer_internal/temp_raw.png
cp /home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm/union/seeds/seed-11/figures/temperature_field_knee-candidate.png /home/hymn/msfenicsx/paper/latex/figures/beamer_internal/temp_union.png
cp /home/hymn/msfenicsx/scenario_runs/s2_staged/0421_0207__llm/figures/temperature_field_min-peak-temperature.png /home/hymn/msfenicsx/paper/latex/figures/beamer_internal/temp_llm.png

cp /home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm/raw/seeds/seed-11/figures/gradient_field_knee-candidate.png /home/hymn/msfenicsx/paper/latex/figures/beamer_internal/grad_raw.png
cp /home/hymn/msfenicsx/scenario_runs/s2_staged/0420_2256__raw_union_llm/union/seeds/seed-11/figures/gradient_field_knee-candidate.png /home/hymn/msfenicsx/paper/latex/figures/beamer_internal/grad_union.png
cp /home/hymn/msfenicsx/scenario_runs/s2_staged/0421_0207__llm/figures/gradient_field_min-peak-temperature.png /home/hymn/msfenicsx/paper/latex/figures/beamer_internal/grad_llm.png
```

Expected:
- `layout_raw.png`, `layout_union.png`, `layout_llm.png`
- `temp_raw.png`, `temp_union.png`, `temp_llm.png`
- `grad_raw.png`, `grad_union.png`, `grad_llm.png`

- [ ] **Step 4: Copy the llm single-run process evidence figures**

Run:

```bash
cp /home/hymn/msfenicsx/scenario_runs/s2_staged/0421_0207__llm/figures/objective_progress.png /home/hymn/msfenicsx/paper/latex/figures/beamer_internal/objective_progress.png
cp /home/hymn/msfenicsx/scenario_runs/s2_staged/0421_0207__llm/figures/operator_phase_heatmap.png /home/hymn/msfenicsx/paper/latex/figures/beamer_internal/operator_phase_heatmap.png
```

Expected:
- `objective_progress.png`
- `operator_phase_heatmap.png`

- [ ] **Step 5: Verify the curated asset directory contents before wiring them into slides**

Run:

```bash
ls -1 /home/hymn/msfenicsx/paper/latex/figures/beamer_internal
```

Expected output contains exactly these figure filenames:

```text
README.txt
fixed_boundary_modes_a1.pdf
inline_control_loop_a1.pdf
taxonomy_recovery_map_a1.pdf
evidence_asset_map_a1.pdf
summary_overview.png
progress_dashboard.png
layout_raw.png
layout_union.png
layout_llm.png
temp_raw.png
temp_union.png
temp_llm.png
grad_raw.png
grad_union.png
grad_llm.png
objective_progress.png
operator_phase_heatmap.png
```

- [ ] **Step 6: Record an asset-curation checkpoint**

Run:

```bash
ls -la /home/hymn/msfenicsx/paper/latex/figures/beamer_internal
```

Expected:
- all curated Beamer-local assets are present
- filenames match the manifest

### Task 3: Implement Slides 1–10 for opening, boundary, method, and mechanism

**Files:**
- Modify: `paper/latex/sections/beamer_zh/00_title_and_questions.tex`
- Modify: `paper/latex/sections/beamer_zh/01_boundary_and_problem.tex`
- Modify: `paper/latex/sections/beamer_zh/02_method_and_mechanism.tex`

- [ ] **Step 1: Replace the placeholder title file with Slides 1–2**

Overwrite `paper/latex/sections/beamer_zh/00_title_and_questions.tex` with this exact content:

```tex
\begin{frame}
  \titlepage
  \vspace{-0.5em}
  \begin{center}
    \small 当前重点：固定优化边界下的机制主线与代表证据
  \end{center}
\end{frame}

\begin{frame}{这次汇报回答三个问题}
  \begin{enumerate}
    \item 为什么必须先固定比较边界？
    \item 在这个边界里，LLM controller 到底改变了什么？
    \item 当前证据已经支持到什么程度？
  \end{enumerate}
  \vspace{0.8em}
  \begin{block}{一句话定位}
    这次汇报不是复述整篇初稿，而是回答“当前主张是否已经被证据链撑住”。
  \end{block}
\end{frame}
```

- [ ] **Step 2: Replace the boundary/problem section with Slides 3–5**

Overwrite `paper/latex/sections/beamer_zh/01_boundary_and_problem.tex` with this exact content:

```tex
\begin{frame}{为什么先固定优化边界}
  \begin{columns}[T]
    \column{0.58\textwidth}
    \begin{itemize}
      \item 卫星热控布局优化是高代价、受约束、多目标问题。
      \item 如果同时改变表示、动作集合和评估闭环，就无法把收益归因到 controller 本身。
      \item 本文关心的不是“更自由的生成器”，而是“同一问题内控制行为如何改变搜索轨迹”。
    \end{itemize}
    \column{0.38\textwidth}
    \begin{block}{核心判断}
      如果比较边界不固定，就无法把收益归因到 controller decision 本身。
    \end{block}
  \end{columns}
\end{frame}

\begin{frame}{公平比较对象：raw / union / llm}
  \centering
  \includegraphics[width=0.95\linewidth]{figures/beamer_internal/fixed_boundary_modes_a1.pdf}

  \vspace{0.4em}

  \small 三者共享表示、动作池、repair/evaluation pipeline 与预算；只改控制层。
\end{frame}

\begin{frame}{问题定义与 controller-only 变化}
  \begin{columns}[T]
    \column{0.48\textwidth}
    \[
      \min_{\mathbf{x} \in \mathcal{X}} \; \bigl(T_{\max}(\mathbf{x}),\; G_{\mathrm{rms}}(\mathbf{x})\bigr)
    \]
    \[
      g_k(\mathbf{x}) \le 0, \quad k=1,\dots,K
    \]
    \column{0.48\textwidth}
    \begin{itemize}
      \item 设计变量：layout + sink
      \item 目标：峰值温度与梯度 RMS
      \item 可行性：几何合法性 + 散热预算 + 高代价评估
      \item 模式差异只体现在控制映射 $\pi_m$
    \end{itemize}
  \end{columns}

  \vspace{0.5em}
  \begin{block}{解释}
    本文不是给 LLM 更大设计自由，而是在同一问题内观察控制行为如何改变搜索轨迹。
  \end{block}
\end{frame}
```

- [ ] **Step 3: Replace the method/mechanism section with Slides 6–10**

Overwrite `paper/latex/sections/beamer_zh/02_method_and_mechanism.tex` with this exact content:

```tex
\begin{frame}{inline control 闭环}
  \centering
  \includegraphics[width=0.95\linewidth]{figures/beamer_internal/inline_control_loop_a1.pdf}

  \vspace{0.4em}

  \small LLM 读取压缩状态并输出调度偏好，但候选生成、修复和评估仍由共享优化系统完成。
\end{frame}

\begin{frame}{哪些固定，哪些变化}
  \begin{columns}[T]
    \column{0.48\textwidth}
    \begin{block}{共享 backbone}
      \begin{itemize}
        \item 表示层
        \item 语义动作注册表
        \item repair / cheap constraints / PDE
        \item 优化预算
      \end{itemize}
    \end{block}
    \column{0.48\textwidth}
    \begin{block}{controller-specific behavior}
      \begin{itemize}
        \item 阶段侧重点
        \item 动作族偏好
        \item 历史利用方式
        \item 目标聚焦方式
      \end{itemize}
    \end{block}
  \end{columns}

  \vspace{0.4em}
  \begin{block}{要点}
    “LLM 更强”在本文里只能被理解为“控制更强”，不能被偷换成“系统更自由”。
  \end{block}
\end{frame}

\begin{frame}{为什么要从结果走向机制}
  \begin{itemize}
    \item 终点数值只能说明有差异，不能说明控制稳定性来自哪里。
    \item 持续低收益与重复动作不是单步错误，而是轨迹级退化。
    \item 过程资产让 collapse / recovery 的讨论变成可检查证据，而不是事后故事。
  \end{itemize}

  \vspace{0.8em}
  \begin{block}{核心问题}
    核心问题不是 LLM 偶尔能否更强，而是其失稳是否具有结构、能否被识别、能否被恢复。
  \end{block}
\end{frame}

\begin{frame}{collapse taxonomy}
  \centering
  \includegraphics[width=0.88\linewidth]{figures/beamer_internal/taxonomy_recovery_map_a1.pdf}

  \vspace{0.4em}

  \small collapse 不是“某一步做坏了”，而是控制偏离被持续放大后形成的轨迹级退化。
\end{frame}

\begin{frame}{layered recovery}
  \begin{columns}[T]
    \column{0.56\textwidth}
    \includegraphics[width=\linewidth]{figures/beamer_internal/taxonomy_recovery_map_a1.pdf}
    \column{0.40\textwidth}
    \begin{itemize}
      \item semantic-layer
      \item spatial-layer
      \item intent-layer
      \item retrieval-layer
      \item saturation-layer
    \end{itemize}
  \end{columns}

  \vspace{0.5em}

  \begin{block}{解释}
    layered recovery 的价值不在于补丁技巧，而在于把恢复路径与崩塌来源一一对应。
  \end{block}
\end{frame}
```

- [ ] **Step 4: Run a focused compile and verify the first half of the deck builds**

Run:

```bash
cd "/home/hymn/msfenicsx/paper/latex" && xelatex -interaction=nonstopmode -halt-on-error -output-directory build/beamer_zh main_beamer_zh.tex
```

Expected:
- PDF exists
- first 10 slides render without missing-asset errors

- [ ] **Step 5: Record a Slide 1–10 checkpoint**

Run:

```bash
ls -la \
  /home/hymn/msfenicsx/paper/latex/sections/beamer_zh/00_title_and_questions.tex \
  /home/hymn/msfenicsx/paper/latex/sections/beamer_zh/01_boundary_and_problem.tex \
  /home/hymn/msfenicsx/paper/latex/sections/beamer_zh/02_method_and_mechanism.tex
```

Expected:
- all three section files exist
- the files were updated from placeholder content

### Task 4: Implement Slides 11–17 for evidence and representative results

**Files:**
- Modify: `paper/latex/sections/beamer_zh/03_evidence_and_results.tex`

- [ ] **Step 1: Replace the evidence section placeholder with Slides 11–17**

Overwrite `paper/latex/sections/beamer_zh/03_evidence_and_results.tex` with this exact content:

```tex
\begin{frame}{证据资产图：结果证据与机制证据如何分工}
  \centering
  \includegraphics[width=0.92\linewidth]{figures/beamer_internal/evidence_asset_map_a1.pdf}

  \vspace{0.4em}

  \small compare report 回答“差异是什么”，单运行资产回答“这些差异在过程里如何出现”。
\end{frame}

\begin{frame}{跨模式总览结果}
  \includegraphics[width=0.98\linewidth]{figures/beamer_internal/summary_overview.png}

  \vspace{0.5em}
  \begin{itemize}
    \item llm 当前取得最佳 $T_{\max}$、最佳 $G_{\mathrm{rms}}$、最高 feasible rate 与最高 final hypervolume。
    \item raw 的最终代表质量仍优于 union。
    \item union 更早进入可行区。
  \end{itemize}
\end{frame}

\begin{frame}{过程推进与阶段差异}
  \begin{columns}[T]
    \column{0.66\textwidth}
    \includegraphics[width=\linewidth]{figures/beamer_internal/progress_dashboard.png}
    \column{0.30\textwidth}
    \begin{itemize}
      \item union：更早可行
      \item raw：后期局部精修仍有韧性
      \item llm：进入可行区后推进更稳
    \end{itemize}
  \end{columns}

  \vspace{0.4em}
  \begin{block}{阶段解释}
    union 更早可行、raw 后期仍有韧性、llm 则更能跨阶段保持目标聚焦与预算效率。
  \end{block}
\end{frame}

\begin{frame}{代表最终布局对比}
  \begin{columns}[T]
    \column{0.32\textwidth}
    \centering
    \includegraphics[width=\linewidth]{figures/beamer_internal/layout_raw.png}\\
    \small raw
    \column{0.32\textwidth}
    \centering
    \includegraphics[width=\linewidth]{figures/beamer_internal/layout_union.png}\\
    \small union
    \column{0.32\textwidth}
    \centering
    \includegraphics[width=\linewidth]{figures/beamer_internal/layout_llm.png}\\
    \small llm
  \end{columns}

  \vspace{0.5em}
  \begin{block}{要点}
    比较不是停留在表格排序上，而是已经落实到可见代表解层面。
  \end{block}
\end{frame}

\begin{frame}{温度场与梯度场对比}
  \begin{columns}[T]
    \column{0.32\textwidth}
    \includegraphics[width=\linewidth]{figures/beamer_internal/temp_raw.png}\\[-0.2em]
    \includegraphics[width=\linewidth]{figures/beamer_internal/grad_raw.png}
    \column{0.32\textwidth}
    \includegraphics[width=\linewidth]{figures/beamer_internal/temp_union.png}\\[-0.2em]
    \includegraphics[width=\linewidth]{figures/beamer_internal/grad_union.png}
    \column{0.32\textwidth}
    \includegraphics[width=\linewidth]{figures/beamer_internal/temp_llm.png}\\[-0.2em]
    \includegraphics[width=\linewidth]{figures/beamer_internal/grad_llm.png}
  \end{columns}

  \vspace{0.4em}
  \small controller decision 的差异最终反映在热点分布、梯度集中区域与布局密度变化上。
\end{frame}

\begin{frame}{llm 单运行机制证据}
  \begin{columns}[T]
    \column{0.48\textwidth}
    \includegraphics[width=\linewidth]{figures/beamer_internal/objective_progress.png}
    \column{0.48\textwidth}
    \includegraphics[width=\linewidth]{figures/beamer_internal/operator_phase_heatmap.png}
  \end{columns}

  \vspace{0.5em}
  \begin{block}{机制窗口}
    objective progress 给出时间上的性能推进，operator-phase heatmap 给出动作与阶段偏好的机制窗口。
  \end{block}
\end{frame}

\begin{frame}{为什么这条证据链能支撑机制主张}
  \begin{block}{compare report}
    负责把 raw / union / llm 的跨模式差异拉开，回答“差异是什么”。
  \end{block}

  \begin{block}{single-run assets}
    负责把 llm 控制过程变成可观测对象，回答“这些差异如何在过程里出现”。
  \end{block}

  \begin{alertblock}{综合判断}
    本文当前最重要的进展，不只是 llm 数值更强，而是“结果差异 + 过程证据”已经能支撑机制化表述。
  \end{alertblock}
\end{frame}
```

- [ ] **Step 2: Run a focused compile and verify the evidence slides build with all assets present**

Run:

```bash
cd "/home/hymn/msfenicsx/paper/latex" && xelatex -interaction=nonstopmode -halt-on-error -output-directory build/beamer_zh main_beamer_zh.tex
```

Expected:
- PDF exists
- Slides 11–17 show all figures without missing-image warnings

- [ ] **Step 3: Record a Slides 11–17 checkpoint**

Run:

```bash
ls -la /home/hymn/msfenicsx/paper/latex/sections/beamer_zh/03_evidence_and_results.tex
```

Expected:
- the evidence/results section file exists
- the file was updated from placeholder content

### Task 5: Implement Slides 18–20 for innovation, conclusion, and next step

**Files:**
- Modify: `paper/latex/sections/beamer_zh/04_conclusion_and_next.tex`

- [ ] **Step 1: Replace the conclusion placeholder with Slides 18–20**

Overwrite `paper/latex/sections/beamer_zh/04_conclusion_and_next.tex` with this exact content:

```tex
\begin{frame}{这版工作的三个创新点}
  \begin{block}{1. 固定边界公平比较}
    把 inline LLM controller 放回同一 optimization boundary 内讨论，而不是把表示、动作与先验同时混入。
  \end{block}
  \begin{block}{2. collapse taxonomy + layered recovery}
    把 controller failure 从“结果好坏”转写成可命名、可分析、可恢复的机制语言。
  \end{block}
  \begin{block}{3. 可审计证据链}
    从 compare report 到 single-run assets，形成结果比较与过程解释分工明确的证据结构。
  \end{block}
\end{frame}

\begin{frame}{当前结论应该怎么讲最准确}
  \begin{alertblock}{一句话结论}
    当前可以讲“llm 已显示明显领先信号”，但更准确的表达是“llm 在跨阶段控制上表现出更强的一致性与综合性”。
  \end{alertblock}

  \begin{itemize}
    \item 固定边界下的模式差异已经清晰可见。
    \item llm 当前在综合结果上最强，但 union 与 raw 仍各有阶段性优势。
    \item 更重要的是，当前结果已经能被 collapse / recovery 机制线解释。
  \end{itemize}
\end{frame}

\begin{frame}{局限性与下一步}
  \begin{columns}[T]
    \column{0.47\textwidth}
    \begin{block}{当前局限}
      \begin{itemize}
        \item 当前证据仍以 s2\_staged 为主。
        \item 现阶段机制线强于大规模 closure。
        \item recovery 的系统性干预验证还没有做完。
      \end{itemize}
    \end{block}
    \column{0.47\textwidth}
    \begin{block}{下一步}
      \begin{itemize}
        \item 扩展到 multi-seed / broader baselines
        \item 做 recovery intervention 验证
        \item 沿既有机制主线补 comparative closure
      \end{itemize}
    \end{block}
  \end{columns}

  \vspace{0.6em}
  \begin{center}
    \small 下一步不是重写故事，而是沿着这条机制主线扩证据、做干预、补 closure。
  \end{center}
\end{frame}
```

- [ ] **Step 2: Compile the full deck and verify the final slide count is about 20**

Run:

```bash
cd "/home/hymn/msfenicsx/paper/latex" && xelatex -interaction=nonstopmode -halt-on-error -output-directory build/beamer_zh main_beamer_zh.tex
```

Expected:
- PDF exists
- slide count is 20
- no frame title or body text overflows noticeably

- [ ] **Step 3: Record a Slides 18–20 checkpoint**

Run:

```bash
ls -la /home/hymn/msfenicsx/paper/latex/sections/beamer_zh/04_conclusion_and_next.tex
```

Expected:
- the conclusion section file exists
- the file was updated from placeholder content

### Task 6: Review the rendered deck and do one visual-cleanup pass

**Files:**
- Modify if needed: `paper/latex/main_beamer_zh.tex`
- Modify if needed: `paper/latex/sections/beamer_zh/*.tex`
- Verify: `paper/latex/build/beamer_zh/main_beamer_zh.pdf`

- [ ] **Step 1: Export slide images for quick visual inspection**

Run:

```bash
cd "/home/hymn/msfenicsx/paper/latex" && python /home/hymn/msfenicsx/scripts/pdf_to_images.py build/beamer_zh/main_beamer_zh.pdf build/beamer_zh/review/slide --dpi 150
```

Expected:
- one image per slide under `build/beamer_zh/review/`

- [ ] **Step 2: Inspect for these specific presentation issues**

Review checklist:

```text
- title and subtitle not overcrowded
- no figure extends beyond frame edges
- no slide contains unreadably small text
- taxonomy/recovery slide remains legible despite reuse of one figure
- temperature/gradient comparison slide is visually balanced
- final slide closes strongly without looking defensive
```

- [ ] **Step 3: Apply only layout-level fixes if inspection reveals crowding**

Allowed edits are limited to content-neutral layout changes such as:

```tex
\includegraphics[width=0.95\linewidth]{...}
\includegraphics[width=0.88\linewidth]{...}
\column{0.48\textwidth}
\small
\vspace{0.4em}
```

Do not rewrite the narrative at this step. Only fix presentation readability.

- [ ] **Step 4: Recompile after layout cleanup**

Run:

```bash
cd "/home/hymn/msfenicsx/paper/latex" && xelatex -interaction=nonstopmode -halt-on-error -output-directory build/beamer_zh main_beamer_zh.tex
```

Expected:
- PDF exists
- no new compile errors introduced

- [ ] **Step 5: Run a final smoke check on the output location**

Run:

```bash
ls -la /home/hymn/msfenicsx/paper/latex/build/beamer_zh/main_beamer_zh.pdf
```

Expected:
- file exists and has non-trivial size

- [ ] **Step 6: Record the final deck checkpoint**

Run:

```bash
ls -la \
  /home/hymn/msfenicsx/paper/latex/main_beamer_zh.tex \
  /home/hymn/msfenicsx/paper/latex/build/beamer_zh/main_beamer_zh.pdf
```

Expected:
- the Beamer source exists
- the compiled PDF exists and has non-trivial size

---

## Self-Review

### Spec coverage

- Opening questions from the spec map to Task 3, Step 1.
- Fixed-boundary fairness framing maps to Task 3, Steps 2–3.
- Collapse taxonomy and layered recovery slides map to Task 3, Step 3.
- Evidence boundary and result/mechanism separation map to Task 4, Step 1.
- Innovation / current conclusion / limitation framing maps to Task 5, Step 1.
- Local curated asset contract maps to Task 2.
- Build-output contract maps to Tasks 1, 3, 4, 5, and 6.

No major spec section is left without an implementation task.

### Placeholder scan

This plan contains no `TODO`, `TBD`, or “write tests later” placeholders. Each file path, command, and code block is explicit.

### Type and naming consistency

- Entry file name is consistently `main_beamer_zh.tex`.
- Section directory is consistently `sections/beamer_zh/`.
- Asset directory is consistently `figures/beamer_internal/`.
- Output directory is consistently `build/beamer_zh/`.
- All slide groups use the same filenames and figure references throughout.
