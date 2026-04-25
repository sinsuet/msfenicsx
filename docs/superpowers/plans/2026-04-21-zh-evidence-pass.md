# 中文主稿实验主线补全 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 围绕 `scenario_runs/s2_staged/0421_0207__llm` 与 `scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair`，把中文主稿中的问题定义、方法、实验三章补成一条完整的当前证据主线，并为 4 张框架图加入 LaTeX 占位。

**Architecture:** 先用问题定义公式把 fixed-boundary 比较对象钉死，再用方法层公式把 inline control 闭环与 layered recovery 的介入位置形式化，最后把 compare report 与单 run 资产按“横向比较证据 + 单运行机制证据”两层结构接入实验章。框架图本轮只放占位，不引入新图片资产；所有新增公式、图位和表位都必须能被正文直接引用。

**Tech Stack:** LaTeX (`ctexart`, `graphicx`, `amsmath`, `booktabs`, `biblatex`), existing PNG/PDF/TEX artifacts under `scenario_runs/`, Chinese draft entrypoint `paper/latex/main_zh.tex`

---

## File Map

**Modify:**
- `paper/latex/sections/zh/03_problem_formulation.tex` — 增补设计变量、目标、约束与 fixed optimization boundary 的正式公式和解释。
- `paper/latex/sections/zh/04_method.tex` — 增补状态摘要、控制决策、统一闭环与 layered recovery 介入位置的最小充分形式化，并加入 2 张框架图占位。
- `paper/latex/sections/zh/05_collapse_and_recovery.tex` — 只做术语、图题引用、层次名称的对齐性轻改，并加入 taxonomy↔recovery 图占位。
- `paper/latex/sections/zh/06_experiments.tex` — 接入 compare report 图表、单 run 机制图，并加入运行资产证据地图占位。

**Read During Implementation:**
- `scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair/figures/summary_overview.png`
- `scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair/figures/progress_dashboard.png`
- `scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair/figures/temperature_field_comparison.png`
- `scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair/figures/gradient_field_comparison.png`
- `scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair/tables/summary_table.tex`
- `scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair/tables/mode_metrics.tex`
- `scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair/tables/pairwise_deltas.tex`
- `scenario_runs/s2_staged/0421_0207__llm/figures/objective_progress.png`
- `scenario_runs/s2_staged/0421_0207__llm/figures/operator_phase_heatmap.png`
- `scenario_runs/s2_staged/0421_0207__llm/figures/pareto_front.png`
- `scenario_runs/s2_staged/0421_0207__llm/figures/layout_initial.png`
- `scenario_runs/s2_staged/0421_0207__llm/figures/layout_final.png`
- `scenario_runs/s2_staged/0421_0207__llm/figures/temperature_field_min-peak-temperature.png`
- `scenario_runs/s2_staged/0421_0207__llm/figures/gradient_field_min-peak-temperature.png`

**Verify:**
- `paper/latex/main_zh.tex` — 用 XeLaTeX 编译整篇中文稿，确认新增公式、图位、表位不会引入新的 LaTeX 语法错误。

---

### Task 1: 盘点实验资产并锁定正文引用顺序

**Files:**
- Modify: `paper/latex/sections/zh/06_experiments.tex`
- Read: `scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair/tables/summary_table.tex`
- Read: `scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair/tables/mode_metrics.tex`
- Read: `scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair/tables/pairwise_deltas.tex`

- [ ] **Step 1: 读取 compare report 表格与关键图文件名，确定实验章顺序**

读取后，把实验章顺序固定为：

```tex
\section{实验}

\subsection{实验设置与证据来源}
...

\subsection{跨模式总览比较}
...

\subsection{过程进展与阶段差异}
...

\subsection{代表布局与温度场/梯度场对比}
...

\subsection{llm 单运行机制证据}
...
```

- [ ] **Step 2: 先把实验章骨架改成固定小节结构**

把 `paper/latex/sections/zh/06_experiments.tex` 先改成下面这种最小骨架，再往里填内容：

```tex
\section{实验}

\subsection{实验设置与证据来源}
本文当前实验主线围绕两类运行资产展开：其一是 compare report，负责提供 raw、union 与 llm recover repair 的横向比较证据；其二是 llm 单运行资产，负责提供 collapse/recovery 的过程级机制证据。

\subsection{跨模式总览比较}

\subsection{过程进展与阶段差异}

\subsection{代表布局与温度场/梯度场对比}

\subsection{llm 单运行机制证据}
```

- [ ] **Step 3: 编译一次中文稿，确认实验章骨架本身不报错**

Run:
```bash
cd "/home/hymn/msfenicsx/paper/latex" && /home/hymn/miniconda3/bin/conda run -n msfenicsx latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir=build-zh main_zh.tex
```

Expected: `build-zh/main_zh.pdf` 生成成功；允许继续出现已有的 `refs.bib` / `biber` 警告，但不能出现新的 TeX 语法错误。

- [ ] **Step 4: Commit**

```bash
git add paper/latex/sections/zh/06_experiments.tex
git commit -m "docs: scaffold zh experiments evidence sections"
```

### Task 2: 在问题定义章加入正式公式与固定边界定义

**Files:**
- Modify: `paper/latex/sections/zh/03_problem_formulation.tex`
- Verify: `paper/latex/main_zh.tex`

- [ ] **Step 1: 先写一个失败标准，明确本章必须出现的 4 类公式对象**

把下面 4 个对象当成“未实现前视为缺失”的清单：

```tex
% 必须补齐的对象
% 1) 设计变量向量 x
% 2) 双目标 f_1(x), f_2(x)
% 3) 约束集合 g_k(x) \le 0
% 4) 固定优化边界 B 与 mode-specific controller \pi_m
```

- [ ] **Step 2: 在问题定义中加入最小充分公式块**

把现有正文扩成包含如下结构的段落与公式：

```tex
设设计变量记为
\begin{equation}
\mathbf{x} = [\mathbf{x}_{\mathrm{layout}},\; \mathbf{x}_{\mathrm{sink}}] \in \mathcal{X},
\end{equation}
其中 $\mathbf{x}_{\mathrm{layout}}$ 表示组件布局变量，$\mathbf{x}_{\mathrm{sink}}$ 表示散热边界变量。

本文考虑如下双目标优化问题：
\begin{equation}
\min_{\mathbf{x} \in \mathcal{X}} \; \mathbf{f}(\mathbf{x}) = \bigl(f_1(\mathbf{x}), f_2(\mathbf{x})\bigr),
\end{equation}
其中
\begin{equation}
f_1(\mathbf{x}) = T_{\max}(\mathbf{x}), \qquad
f_2(\mathbf{x}) = G_{\mathrm{rms}}(\mathbf{x}).
\end{equation}

可行性由几何合法性、散热资源预算与数值评估链共同决定，可统一写为
\begin{equation}
g_k(\mathbf{x}) \le 0, \qquad k = 1,\dots,K.
\end{equation}
```

- [ ] **Step 3: 用一个固定边界定义段把 raw / union / llm 的公平比较写正式**

在同一章紧接着加入如下定义风格的内容：

```tex
进一步地，定义共享优化边界为
\begin{equation}
\mathcal{B} = (\mathcal{X}, \mathcal{A}, \mathcal{R}, \mathcal{C}, \mathcal{E}, T),
\end{equation}
其中 $\mathcal{A}$ 为共享动作集合，$\mathcal{R}$ 为 repair 机制，$\mathcal{C}$ 为廉价约束过滤，$\mathcal{E}$ 为高代价数值评估过程，$T$ 为评估预算。
在 raw、union 与 llm 三种模式中，$\mathcal{B}$ 保持不变；模式差异仅体现为控制映射
\begin{equation}
\pi_m : s_t \mapsto u_t, \qquad m \in \{\mathrm{raw},\mathrm{union},\mathrm{llm}\}.
\end{equation}
```

- [ ] **Step 4: 让新增公式与现有叙事连起来，而不是独立悬空**

在公式前后补两句解释性正文，至少包含下面这类句子：

```tex
上述写法的目的不是引入更自由的生成式设计空间，而是把本文研究对象限定为固定编码下的在线控制问题。
因此，后文关于 collapse taxonomy、layered recovery 与 attribution boundary 的讨论，都建立在共享边界 $\mathcal{B}$ 不变这一前提上。
```

- [ ] **Step 5: 编译中文稿确认公式环境无误**

Run:
```bash
cd "/home/hymn/msfenicsx/paper/latex" && /home/hymn/miniconda3/bin/conda run -n msfenicsx latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir=build-zh main_zh.tex
```

Expected: 新增 `equation` 环境正常；不存在 `Missing $ inserted`、`Undefined control sequence`、`Extra }, or forgotten $` 一类新错误。

- [ ] **Step 6: Commit**

```bash
git add paper/latex/sections/zh/03_problem_formulation.tex
git commit -m "docs: formalize zh problem formulation"
```

### Task 3: 在方法章加入控制闭环公式和两张框架图占位

**Files:**
- Modify: `paper/latex/sections/zh/04_method.tex`
- Verify: `paper/latex/main_zh.tex`

- [ ] **Step 1: 先加入固定边界框架图占位块**

在 `\section{方法：固定优化边界下的 inline LLM control}` 后的前两段附近加入占位图：

```tex
\begin{figure}[t]
    \centering
    \fbox{\parbox{0.92\linewidth}{
        \centering
        Placeholder: 固定优化边界与三种模式对比图\\
        Shared problem / shared operator pool / shared repair-evaluation pipeline / different control layers
    }}
    \caption{固定优化边界下 raw、union 与 llm 三种模式的比较关系。三者共享问题表示、动作集合与评估闭环，仅控制层不同。}
    \label{fig:fixed-boundary-modes}
\end{figure}
```

- [ ] **Step 2: 补状态摘要、控制决策与统一闭环的最小充分公式**

把方法章扩成包含下面这组核心公式：

```tex
在第 $t$ 轮迭代中，控制层读取压缩状态摘要 $s_t$，并输出控制决策
\begin{equation}
u_t = \pi_m(s_t),
\end{equation}
其中 $\pi_m$ 表示模式 $m$ 下的控制映射，$u_t$ 表示对动作族与搜索重点的调度偏好。

在统一边界下，一轮优化闭环可写为
\begin{equation}
(\mathbf{x}'_t, \hat{\mathbf{x}}_t, y_t, s_{t+1}) = \Phi(\mathbf{x}_t, s_t, u_t),
\end{equation}
其中候选生成、repair、廉价约束过滤与高代价评估都被吸收在统一映射 $\Phi$ 中。
```

- [ ] **Step 3: 再加入 inline control 闭环流程图占位块**

在上述公式后的流程说明段落附近加入：

```tex
\begin{figure}[t]
    \centering
    \fbox{\parbox{0.92\linewidth}{
        \centering
        Placeholder: inline control 闭环流程图\\
        state summary $\rightarrow$ controller decision $\rightarrow$ candidate generation $\rightarrow$ repair $\rightarrow$ cheap constraints $\rightarrow$ expensive evaluation $\rightarrow$ state write-back
    }}
    \caption{固定优化边界下的一轮 inline control 闭环。LLM 读取压缩状态并输出调度偏好，但候选生成、修复与评估仍由共享优化系统完成。}
    \label{fig:inline-control-loop}
\end{figure}
```

- [ ] **Step 4: 用克制形式把 layered recovery 写成介入映射，而不是实现细节表**

补一小段带公式的 recovery 描述：

```tex
在此基础上，layered recovery 可视为对决策上下文或控制输出的定向校正，即
\begin{equation}
\tilde{u}_t = \mathcal{R}_{\ell}(s_t, u_t, h_t),
\end{equation}
其中 $\mathcal{R}_{\ell}$ 表示第 $\ell$ 层恢复机制，$h_t$ 表示被显式召回的历史轨迹信息。不同 recovery layer 作用于语义解释、空间上下文、目标意图、历史检索或后期动作抑制等不同位置。
```

- [ ] **Step 5: 编译中文稿确认图位与公式共存正常**

Run:
```bash
cd "/home/hymn/msfenicsx/paper/latex" && /home/hymn/miniconda3/bin/conda run -n msfenicsx latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir=build-zh main_zh.tex
```

Expected: 占位图正常出现；不因 `\fbox`、`\parbox`、数学环境或图题中的英文术语引入新错误。

- [ ] **Step 6: Commit**

```bash
git add paper/latex/sections/zh/04_method.tex
git commit -m "docs: formalize zh inline control method"
```

### Task 4: 对齐 collapse/recovery 章节并加入 taxonomy 对应图占位

**Files:**
- Modify: `paper/latex/sections/zh/05_collapse_and_recovery.tex`
- Verify: `paper/latex/main_zh.tex`

- [ ] **Step 1: 在章节开头后加入 taxonomy↔recovery 对应图占位**

插入如下占位块：

```tex
\begin{figure}[t]
    \centering
    \fbox{\parbox{0.92\linewidth}{
        \centering
        Placeholder: collapse taxonomy 与 layered recovery 对应图\\
        semantic misalignment / spatial blindness / objective-intent drift / history-retrieval failure / late-stage saturation
        $\leftrightarrow$
        semantic / spatial / intent / retrieval / saturation recovery
    }}
    \caption{collapse taxonomy 与 layered recovery 的对应关系。每一层恢复都针对特定失稳类型，并在不同介入位置恢复相应控制能力。}
    \label{fig:taxonomy-recovery-map}
\end{figure}
```

- [ ] **Step 2: 统一章节术语，使其与方法章公式中的变量和实验章图题一致**

检查并必要时替换为一致写法：

```tex
state summary
controller decision
collapse taxonomy
layered recovery
semantic-layer recovery
spatial-layer recovery
intent-layer recovery
retrieval-layer recovery
saturation-layer recovery
```

目标不是全部英文统一，而是同一概念不要出现多种中文/英文混称。

- [ ] **Step 3: 在本章末尾补一句与实验章的桥接句**

加入类似下面的句子：

```tex
基于上述 taxonomy 与 recovery mapping，后续实验部分将分别从跨模式比较资产与 llm 单运行资产中检验：这些 collapse 是否可被识别，以及 recovery 是否在机制相关层面留下可检查证据。
```

- [ ] **Step 4: 编译中文稿确认新增图位与桥接句正常**

Run:
```bash
cd "/home/hymn/msfenicsx/paper/latex" && /home/hymn/miniconda3/bin/conda run -n msfenicsx latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir=build-zh main_zh.tex
```

Expected: 章节可正常编译；taxonomy 图位不与前后段落发生致命排版问题。

- [ ] **Step 5: Commit**

```bash
git add paper/latex/sections/zh/05_collapse_and_recovery.tex
git commit -m "docs: align zh collapse recovery section"
```

### Task 5: 在实验章接入 compare report 图表与表格

**Files:**
- Modify: `paper/latex/sections/zh/06_experiments.tex`
- Read: `scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair/figures/summary_overview.png`
- Read: `scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair/figures/progress_dashboard.png`
- Read: `scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair/figures/temperature_field_comparison.png`
- Read: `scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair/figures/gradient_field_comparison.png`

- [ ] **Step 1: 在实验章开头加入“运行资产证据地图图”占位**

在 `\subsection{实验设置与证据来源}` 下加入：

```tex
\begin{figure}[t]
    \centering
    \fbox{\parbox{0.92\linewidth}{
        \centering
        Placeholder: 运行资产证据地图图\\
        compare report figures/tables + single run analytics/figures/traces $\rightarrow$ experimental claims
    }}
    \caption{本文实验结论所依赖的运行资产证据地图。compare report 提供跨模式比较证据，llm 单运行资产提供过程级机制证据。}
    \label{fig:evidence-map}
\end{figure}
```

- [ ] **Step 2: 接入 compare report 的总览图和总览表**

在 `\subsection{跨模式总览比较}` 中插入如下结构：

```tex
\begin{figure}[t]
    \centering
    \includegraphics[width=0.95\linewidth]{../../scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair/figures/summary_overview.png}
    \caption{`s2_staged` 当前主比较中的总览结果。该图用于快速展示 raw、union 与 llm recover repair 在代表指标上的整体差异。}
    \label{fig:s2-compare-summary}
\end{figure}

\begin{table}[t]
    \centering
    \input{../../scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair/tables/summary_table.tex}
    \caption{当前主比较中的汇总表。}
    \label{tab:s2-compare-summary}
\end{table}
```

- [ ] **Step 3: 接入 progress dashboard 与 mode_metrics/pairwise_deltas 表**

在 `\subsection{过程进展与阶段差异}` 中插入：

```tex
\begin{figure}[t]
    \centering
    \includegraphics[width=0.95\linewidth]{../../scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair/figures/progress_dashboard.png}
    \caption{三种模式在当前比较中的过程进展与阶段差异。}
    \label{fig:s2-progress-dashboard}
\end{figure}

\begin{table}[t]
    \centering
    \input{../../scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair/tables/mode_metrics.tex}
    \caption{三种模式的主要指标对比。}
    \label{tab:s2-mode-metrics}
\end{table}

\begin{table}[t]
    \centering
    \input{../../scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair/tables/pairwise_deltas.tex}
    \caption{模式两两比较的差值摘要。}
    \label{tab:s2-pairwise-deltas}
\end{table}
```

- [ ] **Step 4: 接入温度场与梯度场对比图，并写明它们只承担当前证据层**

在 `\subsection{代表布局与温度场/梯度场对比}` 中插入：

```tex
\begin{figure}[t]
    \centering
    \includegraphics[width=0.95\linewidth]{../../scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair/figures/temperature_field_comparison.png}
    \caption{当前主比较中的代表温度场对比。}
    \label{fig:s2-temperature-comparison}
\end{figure}

\begin{figure}[t]
    \centering
    \includegraphics[width=0.95\linewidth]{../../scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair/figures/gradient_field_comparison.png}
    \caption{当前主比较中的代表梯度场对比。}
    \label{fig:s2-gradient-comparison}
\end{figure}
```

并在图前后写出下面这种限制性表述：

```tex
这些图像证据用于说明不同控制模式在代表布局与物理场形态上的可见差异，但在当前版本中，它们仍服务于“当前证据层”的比较，而不承担最终大规模 comparative closure 的任务。
```

- [ ] **Step 5: 编译中文稿验证外部图表路径全部可解析**

Run:
```bash
cd "/home/hymn/msfenicsx/paper/latex" && /home/hymn/miniconda3/bin/conda run -n msfenicsx latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir=build-zh main_zh.tex
```

Expected: 所有 compare report 图表路径都能找到；不存在 `File ... not found` 的新错误。

- [ ] **Step 6: Commit**

```bash
git add paper/latex/sections/zh/06_experiments.tex
git commit -m "docs: add zh compare report evidence"
```

### Task 6: 在实验章接入 llm 单运行机制图并完成正文叙事

**Files:**
- Modify: `paper/latex/sections/zh/06_experiments.tex`
- Read: `scenario_runs/s2_staged/0421_0207__llm/figures/objective_progress.png`
- Read: `scenario_runs/s2_staged/0421_0207__llm/figures/operator_phase_heatmap.png`
- Read: `scenario_runs/s2_staged/0421_0207__llm/figures/pareto_front.png`
- Read: `scenario_runs/s2_staged/0421_0207__llm/figures/layout_initial.png`
- Read: `scenario_runs/s2_staged/0421_0207__llm/figures/layout_final.png`
- Read: `scenario_runs/s2_staged/0421_0207__llm/figures/temperature_field_min-peak-temperature.png`
- Read: `scenario_runs/s2_staged/0421_0207__llm/figures/gradient_field_min-peak-temperature.png`

- [ ] **Step 1: 在 llm 单运行机制小节加入目标进展图与 operator heatmap 图**

插入以下结构：

```tex
\begin{figure}[t]
    \centering
    \includegraphics[width=0.95\linewidth]{../../scenario_runs/s2_staged/0421_0207__llm/figures/objective_progress.png}
    \caption{`0421_0207__llm` 单运行中的目标进展曲线。}
    \label{fig:llm-objective-progress}
\end{figure}

\begin{figure}[t]
    \centering
    \includegraphics[width=0.95\linewidth]{../../scenario_runs/s2_staged/0421_0207__llm/figures/operator_phase_heatmap.png}
    \caption{`0421_0207__llm` 单运行中的 operator-phase heatmap。该图用于观察阶段切换与动作偏好变化。}
    \label{fig:llm-operator-phase-heatmap}
\end{figure}
```

- [ ] **Step 2: 加入单运行代表点图，说明布局和物理场如何支撑机制解释**

在同一小节继续插入：

```tex
\begin{figure}[t]
    \centering
    \includegraphics[width=0.48\linewidth]{../../scenario_runs/s2_staged/0421_0207__llm/figures/layout_initial.png}
    \hfill
    \includegraphics[width=0.48\linewidth]{../../scenario_runs/s2_staged/0421_0207__llm/figures/layout_final.png}
    \caption{`0421_0207__llm` 单运行中的初始布局与最终代表布局。}
    \label{fig:llm-layout-evolution-static}
\end{figure}

\begin{figure}[t]
    \centering
    \includegraphics[width=0.48\linewidth]{../../scenario_runs/s2_staged/0421_0207__llm/figures/temperature_field_min-peak-temperature.png}
    \hfill
    \includegraphics[width=0.48\linewidth]{../../scenario_runs/s2_staged/0421_0207__llm/figures/gradient_field_min-peak-temperature.png}
    \caption{`0421_0207__llm` 代表点的温度场与梯度场。}
    \label{fig:llm-representative-fields}
\end{figure}
```

- [ ] **Step 3: 把实验章正文补成“两层证据”叙事，而不是纯图录**

至少补入下面这类正文句子：

```tex
上述 compare report 资产用于回答“在当前比较边界下，不同模式表现出了哪些可见差异”；而 `0421_0207__llm` 单运行资产用于回答“在 llm 控制过程内部，这些差异如何沿时间、动作偏好与代表布局演化被观察到”。
因此，本文实验章有意把横向比较证据与单运行机制证据分开组织，以避免将结果比较与机制解释混写为同一种证据。
```

- [ ] **Step 4: 在实验章末尾加一个桥接段，把结果引回 collapse/recovery 术语**

补一个结尾段，风格参考：

```tex
综合上述证据，可以把当前结果理解为两层结论：第一，固定边界下的跨模式比较已经展示出可见差异；第二，llm 单运行资产进一步提供了 collapse 识别与 recovery 分析所需的过程级证据。也就是说，本文当前版本更接近于建立一个可审计的机制主线，而不是提前给出最终的大规模比较闭环。
```

- [ ] **Step 5: 编译中文稿确认所有单运行图片路径和双图排版都正常**

Run:
```bash
cd "/home/hymn/msfenicsx/paper/latex" && /home/hymn/miniconda3/bin/conda run -n msfenicsx latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir=build-zh main_zh.tex
```

Expected: 单运行图全部可解析；双图并排不引发新的语法错误；允许继续存在已有参考文献警告。

- [ ] **Step 6: Commit**

```bash
git add paper/latex/sections/zh/06_experiments.tex
git commit -m "docs: add zh llm mechanism evidence"
```

### Task 7: 做中文稿整体验证并收口措辞

**Files:**
- Modify: `paper/latex/sections/zh/03_problem_formulation.tex`
- Modify: `paper/latex/sections/zh/04_method.tex`
- Modify: `paper/latex/sections/zh/05_collapse_and_recovery.tex`
- Modify: `paper/latex/sections/zh/06_experiments.tex`
- Verify: `paper/latex/main_zh.tex`

- [ ] **Step 1: 快速审读 4 个改动章节，删除会让当前版本过度承诺的句子**

重点删改以下类型的措辞：

```tex
稳定胜出
最终证明
全面优于
普遍成立
大规模闭环已经完成
```

替换成当前稿件更准确的表达，例如：

```tex
当前比较显示
当前证据表明
在本轮运行资产下可观察到
当前版本更强调机制主线
```

- [ ] **Step 2: 编译中文稿做最终验证**

Run:
```bash
cd "/home/hymn/msfenicsx/paper/latex" && /home/hymn/miniconda3/bin/conda run -n msfenicsx latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir=build-zh main_zh.tex
```

Expected: `build-zh/main_zh.pdf` 正常生成；不出现新的 LaTeX 致命错误。已有 `refs.bib` 路径/Biber 警告可以保留为已知问题，但要在交付说明中明确它们不是本轮新增。

- [ ] **Step 3: 记录验证结果，准备给用户的交付摘要**

摘要至少要覆盖：

```text
1. 哪四个中文章节被补强
2. 哪几组 compare report / 单 run 图表已接入
3. 哪 4 张框架图已占位
4. 中文编译是否通过
5. 还剩哪些后续工作（正式框架图替换、英文同步、参考文献路径修复）
```

- [ ] **Step 4: Commit**

```bash
git add paper/latex/sections/zh/03_problem_formulation.tex paper/latex/sections/zh/04_method.tex paper/latex/sections/zh/05_collapse_and_recovery.tex paper/latex/sections/zh/06_experiments.tex
git commit -m "docs: complete zh evidence pass for current runs"
```

## Self-Review Checklist

- Spec coverage:
  - `03_problem_formulation` 的 4 类公式对象由 Task 2 覆盖。
  - `04_method` 的状态/控制/闭环/recovery 形式化与 2 张框架图由 Task 3 覆盖。
  - `05_collapse_and_recovery` 的对齐性轻改与 taxonomy 图位由 Task 4 覆盖。
  - `06_experiments` 的 compare report 接入、单运行机制证据接入、证据地图图位与正文叙事由 Task 1、Task 5、Task 6 覆盖。
  - 最终编译验证与措辞收口由 Task 7 覆盖。

- Placeholder scan:
  - 无 `TODO` / `TBD` / “以后补”式步骤。
  - 所有修改步骤都给出具体 LaTeX 片段、路径与编译命令。

- Type consistency:
  - 统一使用 `s_t` 表示状态摘要，`u_t` 表示控制输出，`\pi_m` 表示模式控制映射，`\mathcal{R}_{\ell}` 表示恢复层映射。
  - 统一使用 compare report + 单 run 两层证据结构，不在后续任务改名。
