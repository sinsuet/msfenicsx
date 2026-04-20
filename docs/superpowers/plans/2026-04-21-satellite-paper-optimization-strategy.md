# Satellite Paper Optimization Strategy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize the manuscript spine for the satellite thermal-control paper so that later evidence growth can strengthen the paper without forcing a narrative rewrite.

**Architecture:** Execute the paper optimization in two layers. First, create a lightweight literature-calibration note that locks novelty boundaries and claim strength. Then rewrite one chapter at a time—Chinese source first, English alignment second—while preserving the paper spine defined in `docs/superpowers/specs/2026-04-21-satellite-paper-optimization-strategy-design.md`.

**Tech Stack:** LaTeX (`latexmk`, `xelatex`, `pdflatex`, `biber`, `bibtex`), AAAI-26 English template, Chinese XeLaTeX draft, shared bibliography `paper/latex/refs.bib`, paper workspace under `paper/latex/`.

---

## File Map

- `paper/references/2026-04-21-lightweight-calibration.md` — lightweight novelty-boundary memo used to calibrate the current writing pass before deep literature retrieval.
- `paper/latex/sections/zh/01_introduction.tex` — Chinese source introduction; the first narrative anchor for the paper spine.
- `paper/latex/sections/en/01_introduction.tex` — English-aligned introduction; structurally mirrors the Chinese source but may stay shorter in this pass.
- `paper/latex/sections/zh/02_related_work.tex` — Chinese related-work section focused on gap construction and boundary-setting.
- `paper/latex/sections/en/02_related_work.tex` — English-aligned related-work section.
- `paper/latex/sections/zh/03_problem_formulation.tex` — Chinese problem formulation establishing fixed optimization boundary and inline-controller scope.
- `paper/latex/sections/en/03_problem_formulation.tex` — English-aligned problem formulation.
- `paper/latex/sections/zh/04_method.tex` — Chinese fixed-boundary inline-control framework section.
- `paper/latex/sections/zh/05_collapse_and_recovery.tex` — Chinese collapse taxonomy and layered recovery section.
- `paper/latex/sections/en/04_method.tex` — English-aligned framework section.
- `paper/latex/sections/en/05_collapse_and_recovery.tex` — English-aligned collapse and recovery section.
- `paper/latex/sections/zh/00_abstract.tex` — Chinese abstract, revised only after the main spine sections are stabilized.
- `paper/latex/sections/en/00_abstract.tex` — English abstract, aligned to the same claim-strength policy.
- `paper/latex/sections/zh/06_experiments.tex` — Chinese experiments section constrained to mechanism-first current claims.
- `paper/latex/sections/en/06_experiments.tex` — English-aligned experiments section.
- `paper/latex/sections/zh/07_analysis_and_discussion.tex` — Chinese discussion section for cautious generalization.
- `paper/latex/sections/en/07_analysis_and_discussion.tex` — English-aligned discussion section.
- `paper/latex/sections/zh/08_limitations.tex` — Chinese limitations section.
- `paper/latex/sections/en/08_limitations.tex` — English-aligned limitations section.
- `paper/latex/sections/zh/09_conclusion.tex` — Chinese conclusion section.
- `paper/latex/sections/en/09_conclusion.tex` — English-aligned conclusion section.

### Task 1: Create the lightweight calibration memo

**Files:**
- Create: `paper/references/2026-04-21-lightweight-calibration.md`
- Read for context: `docs/superpowers/specs/2026-04-21-satellite-paper-optimization-strategy-design.md`
- Read for context: `paper/latex/sections/zh/01_introduction.tex`
- Read for context: `paper/latex/sections/zh/02_related_work.tex`

- [ ] **Step 1: Write the calibration memo with four locked sections**

```markdown
# Lightweight Calibration Memo

## 1. Current paper identity
- Application-driven problem paper.
- Central scientific contribution: collapse taxonomy + layered recovery for inline LLM control.
- Current evidence priority: mechanism first, attribution second, performance third.

## 2. Closest neighboring paper types to avoid collapsing into
- Performance-first hybrid optimizer report.
- Engineering patch diary.
- Application-packaged novelty claim where the engineering scene carries more weight than the method contribution.

## 3. Safe claims for the current draft
- Inline LLM control exhibits recognizable collapse phenomena in expensive constrained black-box optimization.
- These failures can be organized as a structured taxonomy rather than described as isolated bad runs.
- Layered recovery is presented as a framework aligned to collapse type and intervention level.
- Fixed-boundary and budget-matched comparison improves attribution clarity.

## 4. Claims to postpone until deeper experiments arrive
- Broad superiority against many baselines.
- Robustness across multiple models, many seeds, and multiple scenarios.
- Strong final-performance dominance as the headline claim.
- Strongly universal generalization across all LLM-controlled optimization settings.
```

- [ ] **Step 2: Add the chapter-level writing boundaries to the same memo**

```markdown
## 5. Chapter boundaries for the current rewrite pass
- Introduction: open with collapse problem, not domain tutorial.
- Related Work: construct gap and boundary, not broad survey.
- Problem Formulation: define task, fixed boundary, and controller insertion point.
- Method: present framework logic, not implementation detail.
- Collapse and Recovery: present taxonomy before interventions; each recovery layer must identify target failure, intervention location, and intended restored capability.
- Experiments: state what current evidence supports now; do not claim final comparative closure.
- Discussion: cautiously discuss what might generalize beyond the current task.
```

- [ ] **Step 3: Verify the memo exists and reads cleanly**

Run: `sed -n '1,220p' /home/hymn/msfenicsx/paper/references/2026-04-21-lightweight-calibration.md`

Expected:
- file opens without missing headings
- the memo contains the four safe claims and four deferred claims
- the memo includes chapter boundaries for Introduction, Related Work, Problem Formulation, Method, Collapse and Recovery, Experiments, and Discussion

### Task 2: Rewrite the Chinese introduction around the paper spine

**Files:**
- Modify: `paper/latex/sections/zh/01_introduction.tex`
- Read for context: `paper/references/2026-04-21-lightweight-calibration.md`
- Compile target: `paper/latex/main_zh.tex`

- [ ] **Step 1: Replace the current introduction with a four-paragraph structure**

```tex
\section{引言}

卫星热控布局优化属于一类高代价、受约束、多目标的黑盒优化问题。一次候选方案是否可接受，往往依赖数值求解或仿真评估，而有限评估预算又迫使搜索过程必须兼顾可行性、峰值温度与热分布均匀性等目标。在这类问题中，研究焦点不只是谁能偶然找到更好的解，更在于控制机制能否在昂贵评估闭环内保持稳定、可解释且可恢复的搜索行为。

近年来，LLM 被逐步引入优化任务，但大多数工作将其置于闭环之外：要么把它作为初始化或算子推荐的启发式顾问，要么把它作为候选生成器直接提出设计方案。这样的设置通常同时改变表示方式、先验来源、算子能力或比较边界，因此即便最终结果改善，也很难判断收益究竟来自控制能力本身，还是来自额外知识注入与搜索边界变化。对于高代价优化问题，这种归因不清会进一步掩盖一个更核心的问题：当 LLM 被放入在线控制位置之后，它何时会系统性失稳，又应如何恢复。

本文将 LLM 置于固定优化边界之内，把问题重写为一个在线控制稳定性问题。具体地，我们在共享表示、共享语义算子池、共享 repair/evaluation pipeline 与共享预算的条件下，仅改变控制决策机制，从而构造 raw、union 与 llm 三类可比较控制模式。在这一设置下，本文不把关注点放在“LLM 是否偶尔带来更好结果”这一单一性能问题上，而是聚焦于：高代价约束优化中的 inline LLM control 会呈现哪些可识别的崩塌模式，这些崩塌如何被组织为 taxonomy，以及如何基于这些崩塌构造 layered recovery framework。

本文的主要贡献包括：\textbf{(1)} 将高代价约束优化中的 inline LLM control 重构为一个稳定性与失效机制问题，而非仅是性能增强问题；\textbf{(2)} 提出面向 LLM-controlled black-box optimization 的崩塌模式 taxonomy，用于组织可识别的结构性失稳；\textbf{(3)} 提出与 taxonomy 对齐的 layered recovery framework，以干预层级而非工程补丁堆叠的方式恢复控制行为；\textbf{(4)} 在固定边界、预算匹配与可审计运行资产下讨论控制作用的归因边界，并为后续更大规模实验扩展保留统一叙事主线。
```

- [ ] **Step 2: Compile the Chinese draft to catch LaTeX breakage immediately**

Run: `cd /home/hymn/msfenicsx/paper/latex && latexmk -xelatex -interaction=nonstopmode -outdir=build/main_zh main_zh.tex`

Expected:
- build completes without a fatal error
- output file exists at `paper/latex/build/main_zh/main_zh.pdf`
- no missing-file error mentions `01_introduction.tex`

- [ ] **Step 3: Read the rendered introduction source and verify four properties**

Run: `sed -n '1,220p' /home/hymn/msfenicsx/paper/latex/sections/zh/01_introduction.tex`

Expected:
- paragraph 1 opens with the problem class, not a long satellite-domain tutorial
- paragraph 2 distinguishes inline control from generator/advisor settings
- paragraph 3 reframes the paper around collapse and recovery
- paragraph 4 states contributions without headline performance claims

### Task 3: Align the English introduction to the same spine

**Files:**
- Modify: `paper/latex/sections/en/01_introduction.tex`
- Read for context: `paper/latex/sections/zh/01_introduction.tex`
- Compile target: `paper/latex/main_en.tex`

- [ ] **Step 1: Replace the English introduction with a compressed aligned draft**

```tex
\section{Introduction}

Satellite thermal-control layout optimization is an expensive, constrained, multi-objective black-box optimization problem. Candidate quality must be judged through solver-backed evaluation, while limited evaluation budgets force the search process to balance feasibility, peak temperature, and thermal uniformity under tight resource constraints. In this setting, the key scientific question is not only whether a controller can occasionally improve the final objective values, but whether it can sustain stable, interpretable, and recoverable search behavior inside an expensive optimization loop.

Recent work has introduced LLMs into optimization in several ways, but most settings keep the model outside the inner control loop: as a heuristic advisor for initialization or operator preference, or as a generator that directly proposes candidate designs. Such choices often change representation, prior knowledge, operator availability, or the comparison boundary itself. As a result, even when performance improves, the gain cannot be cleanly attributed to control ability alone. For expensive optimization, this ambiguity also hides a more central problem: once an LLM is inserted into the online control position, when does it collapse, and how should that collapse be recovered?

This paper studies LLMs as inline controllers under a fixed optimization boundary. We hold representation, semantic operator pool, repair/evaluation pipeline, and evaluation budget constant, and vary only the control mechanism across raw, union, and llm modes. Under this setting, we shift the paper away from a purely performance-centric question and instead ask which collapse modes emerge in inline LLM control, how those failures can be organized into a taxonomy, and how a layered recovery framework can intervene on them.

Our contributions are fourfold: \textbf{(1)} we reframe inline LLM control in expensive constrained optimization as a stability-and-failure-mechanism problem rather than only a performance question; \textbf{(2)} we define a collapse taxonomy for LLM-controlled black-box optimization; \textbf{(3)} we present a layered recovery framework aligned to collapse type and intervention level; and \textbf{(4)} we discuss attribution boundaries under fixed comparison settings and auditable run assets while leaving stronger comparative claims to later large-scale experiments.
```

- [ ] **Step 2: Compile the English draft after the rewrite**

Run: `cd /home/hymn/msfenicsx/paper/latex && latexmk -pdf -interaction=nonstopmode -outdir=build/main_en main_en.tex`

Expected:
- build completes without a fatal error
- output file exists at `paper/latex/build/main_en/main_en.pdf`
- no missing-file error mentions `01_introduction.tex`

- [ ] **Step 3: Check the English introduction against the Chinese source**

Run: `diff -u /home/hymn/msfenicsx/paper/latex/sections/zh/01_introduction.tex /home/hymn/msfenicsx/paper/latex/sections/en/01_introduction.tex | sed -n '1,220p'`

Expected:
- the files differ in language and compression, not in section role
- both versions include the same four logical paragraphs
- neither version claims broad performance dominance

### Task 4: Rewrite the Chinese method and collapse/recovery sections as a framework narrative

**Files:**
- Modify: `paper/latex/sections/zh/04_method.tex`
- Modify: `paper/latex/sections/zh/05_collapse_and_recovery.tex`
- Read for context: `paper/references/2026-04-21-lightweight-calibration.md`
- Compile target: `paper/latex/main_zh.tex`

- [ ] **Step 1: Rewrite `04_method.tex` so it defines the fixed-boundary control setup and the logic that makes collapse central**

```tex
\section{方法：固定优化边界下的 inline LLM control}

本文的方法部分遵循一个严格边界：我们不改变问题定义，不改变表示方式，不改变候选动作集合，也不改变 repair/evaluation pipeline，而只改变控制层如何在既有优化能力上做在线调度。具体而言，表示层固定为布局变量与散热边界变量，算子层固定为共享的语义动作注册表，repair/evaluation 层固定为相同的几何修复、廉价约束检查与高代价数值评估闭环，控制层则分别对应 raw、union 与 llm 三种模式。由此，三者之间的差异被压缩到控制决策本身，而不是被混杂在搜索空间变化、外部先验注入或额外算子能力之中。

在这一设置中，LLM 的角色被限定为在线控制器而非设计生成器。每一轮优化仍遵循“控制决策—候选生成—repair—廉价约束过滤—高代价评估—状态回写”的统一闭环；LLM 读取的是压缩后的过程状态，而非直接生成最终几何布局。它输出的是对动作族与搜索侧重点的控制偏好，真正的候选产生、修复与评估仍由既有优化系统完成。因此，本文要研究的不是一个更大、更自由的生成系统，而是在固定优化边界内，控制机制如何影响搜索轨迹的稳定性。

正因为控制边界被固定，本文将 collapse 而不是普通随机波动视为核心失败模式。如果控制器只是偶发地产生坏建议，那么问题可以被视为局部噪声；但当动作偏好、阶段判断、目标侧重或历史检索在多轮交互中持续偏离，控制层就会把这种偏离放大为轨迹级退化，进而吞噬高代价评估预算。由此，inline LLM control 的关键问题不再只是“偶尔能否更强”，而是其失稳是否具有结构、能否被命名、以及是否存在与之对应的系统性恢复路径。

为使这种机制研究具备可审计性，本文在运行时保留 summary、timeline、milestone 与 trace 四层资产。它们分别服务于结果概览、阶段变化、关键事件与细粒度控制记录，为后续的 collapse 识别、恢复干预与归因讨论提供统一证据链。这样的方法设计使得后续 taxonomy 与 layered recovery 不是凭直觉命名，而是建立在固定边界与可检查运行资产上的机制分析。
```

- [ ] **Step 2: Rewrite `05_collapse_and_recovery.tex` so taxonomy comes before recovery and each layer states its target failure**

```tex
\section{崩塌模式 taxonomy 与 layered recovery framework}

当 LLM 被嵌入高代价优化闭环时，其失败方式并不只是“某一步建议不好”，而会表现为若干可识别的结构性崩塌。本文将这类崩塌组织为一个面向 inline LLM control 的 taxonomy。第一类是\textbf{语义失配}：控制器表面上调用了正确的动作语义，但其控制偏好与当前阶段真正需要解决的目标矛盾不一致。第二类是\textbf{空间感知缺失}：压缩状态不足以支撑控制器恢复关键几何关系，导致动作选择忽略布局密度、间距张力或散热边界位置。第三类是\textbf{目标意图漂移}：多目标权衡在持续决策中被逐步稀释，控制器把形式上合理的动作当成目标上有效的动作。第四类是\textbf{历史检索失效}：本应影响当前决策的关键失败案例、阶段信号或改进线索未能被正确带回控制窗口。第五类是\textbf{后期饱和重复}：搜索已进入局部稳定区后，控制器仍重复输出高频低收益偏好，持续消耗昂贵评估预算。

taxonomy 的作用不是列举现象，而是为恢复设计提供组织原则。本文据此提出 layered recovery framework，并按“目标失败—介入位置—预期恢复能力”的方式描述每一层干预。\textbf{语义层恢复}针对语义失配，在动作语义解释与阶段目标之间重新建立一致性，以恢复控制器对当前主矛盾的对齐能力。\textbf{空间层恢复}针对空间感知缺失，在状态摘要与布局张力表达之间补足几何上下文，以恢复控制器对空间约束的辨识能力。\textbf{意图层恢复}针对目标意图漂移，在多目标权重与阶段性优先级的表达中强化主次关系，以恢复控制器对优化目标的持续聚焦。\textbf{检索层恢复}针对历史检索失效，在决策窗口中显式带回关键轨迹事实，以恢复控制器对近期成败模式的利用能力。\textbf{饱和层恢复}针对后期饱和重复，通过抑制低收益高频动作并引导更稀疏的探索，恢复后期预算使用的有效性。

这样的 layered recovery 不是一串经验性补丁，而是由 collapse structure 组织起来的干预框架。它的价值不在于宣称某个单独技巧永远有效，而在于把 inline LLM control 的失稳问题转化为可定位、可解释、可逐层介入的机制问题。后续实验部分据此验证的，也不是“是否存在神秘增益”，而是 taxonomy 是否解释得动退化，recovery 是否能够在机制上改善控制行为。
```

- [ ] **Step 3: Compile the Chinese draft after both section rewrites**

Run: `cd /home/hymn/msfenicsx/paper/latex && latexmk -xelatex -interaction=nonstopmode -outdir=build/main_zh main_zh.tex`

Expected:
- build completes without a fatal error
- `04_method.tex` and `05_collapse_and_recovery.tex` are both included successfully
- resulting PDF exists at `paper/latex/build/main_zh/main_zh.pdf`

- [ ] **Step 4: Read both files and verify the framework logic**

Run: `sed -n '1,260p' /home/hymn/msfenicsx/paper/latex/sections/zh/04_method.tex && printf '\n---\n' && sed -n '1,280p' /home/hymn/msfenicsx/paper/latex/sections/zh/05_collapse_and_recovery.tex`

Expected:
- `04_method.tex` defines the fixed boundary before discussing collapse
- `05_collapse_and_recovery.tex` presents taxonomy before recovery
- each recovery layer names target failure, intervention location, and intended restored capability
- neither file reads like an implementation manual

### Task 5: Align the English method and collapse/recovery sections

**Files:**
- Modify: `paper/latex/sections/en/04_method.tex`
- Modify: `paper/latex/sections/en/05_collapse_and_recovery.tex`
- Read for context: `paper/latex/sections/zh/04_method.tex`
- Read for context: `paper/latex/sections/zh/05_collapse_and_recovery.tex`
- Compile target: `paper/latex/main_en.tex`

- [ ] **Step 1: Replace `sections/en/04_method.tex` with an English-aligned framework draft**

```tex
\section{Method: Fixed-Boundary Inline LLM Control}

Our method enforces a strict comparison boundary: we do not change the problem definition, the representation, the candidate action space, or the repair/evaluation pipeline. We only change how the control layer schedules the same underlying optimization capabilities. Concretely, the representation layer remains fixed to layout and heat-rejection variables, the operator layer remains fixed to a shared semantic action registry, the repair/evaluation layer remains fixed to the same geometry repair, cheap-constraint filtering, and expensive numerical evaluation loop, and the control layer varies across raw, union, and llm modes. This design compresses the difference among modes into control decisions rather than search-space changes or additional prior knowledge.

Under this setup, the LLM acts as an inline controller rather than a design generator. Each optimization round still follows a common loop of control decision, candidate generation, repair, cheap-constraint filtering, expensive evaluation, and state write-back. The LLM reads compressed process state rather than emitting final layouts directly; it outputs control preferences over action families and search emphasis, while candidate construction and evaluation remain inside the existing optimizer. The scientific question is therefore not how a freer generator behaves, but how a controller behaves when inserted into a fixed expensive optimization loop.

Because the boundary is fixed, collapse rather than ordinary stochastic variance becomes the central failure mode. If the controller only produced occasional bad suggestions, the issue would remain local noise. But once action preference, phase judgment, objective emphasis, or trajectory retrieval persistently drift, the control layer can amplify that drift into trajectory-level degradation and waste expensive evaluation budget. This motivates a mechanism-centered analysis of identifiable collapse modes and structured recovery paths.

To make that analysis auditable, we retain four classes of run assets: summary, timeline, milestone, and trace. They support result overview, phase evolution, key-event capture, and fine-grained control records, respectively. These assets provide the common evidence chain used later to discuss collapse identification, recovery intervention, and attribution boundaries.
```

- [ ] **Step 2: Replace `sections/en/05_collapse_and_recovery.tex` with an English-aligned taxonomy and recovery draft**

```tex
\section{Collapse Taxonomy and Layered Recovery}

When an LLM is embedded in an expensive optimization loop, failure is not merely a matter of one bad suggestion. Instead, it appears as structured forms of collapse that can be organized into a taxonomy for inline LLM control. The first class is \textbf{semantic misalignment}, where the controller invokes plausible action semantics but fails to align them with the phase-specific optimization need. The second class is \textbf{spatial blindness}, where compressed state is insufficient for recovering the geometric relations that matter for control. The third class is \textbf{objective-intent drift}, where multi-objective priorities are gradually diluted across repeated decisions. The fourth class is \textbf{history-retrieval failure}, where key trajectory evidence is not properly brought back into the current decision window. The fifth class is \textbf{late-stage saturation}, where the controller keeps repeating high-frequency, low-yield preferences after the search has entered a locally stable region.

The purpose of the taxonomy is not to name symptoms, but to organize intervention design. We therefore present a layered recovery framework in terms of target failure, intervention location, and intended restored capability. \textbf{Semantic-layer recovery} targets semantic misalignment by re-establishing consistency between action meaning and phase objective. \textbf{Spatial-layer recovery} targets spatial blindness by enriching the state summary with the geometric context needed for control. \textbf{Intent-layer recovery} targets objective-intent drift by reinforcing the priority structure of the optimization targets. \textbf{Retrieval-layer recovery} targets history-retrieval failure by explicitly bringing key trajectory facts back into the decision context. \textbf{Saturation-layer recovery} targets late-stage saturation by suppressing low-yield repetition and redirecting the controller toward sparser, better-focused exploration.

In this formulation, layered recovery is not an anecdotal patch stack. It is a collapse-structured intervention framework. The experimental question that follows is therefore not whether a single trick creates a mysterious gain, but whether the taxonomy explains degradation and whether recovery improves controller behavior in mechanism-relevant ways.
```

- [ ] **Step 3: Compile the English draft after both rewrites**

Run: `cd /home/hymn/msfenicsx/paper/latex && latexmk -pdf -interaction=nonstopmode -outdir=build/main_en main_en.tex`

Expected:
- build completes without a fatal error
- `04_method.tex` and `05_collapse_and_recovery.tex` are both included successfully
- resulting PDF exists at `paper/latex/build/main_en/main_en.pdf`

### Task 6: Rewrite related work and problem formulation as boundary-setting sections

**Files:**
- Modify: `paper/latex/sections/zh/02_related_work.tex`
- Modify: `paper/latex/sections/zh/03_problem_formulation.tex`
- Modify: `paper/latex/sections/en/02_related_work.tex`
- Modify: `paper/latex/sections/en/03_problem_formulation.tex`
- Compile targets: `paper/latex/main_zh.tex`, `paper/latex/main_en.tex`

- [ ] **Step 1: Replace the Chinese related-work section with a gap-first version**

```tex
\section{相关工作}

与本文最接近的研究可分为四条线索。第一类是卫星与航天热控设计中的仿真驱动优化工作，这类研究强调布局变量、热边界与安全约束之间的耦合，以及一次有效评估本身所具有的高代价特征。第二类是将 LLM 作为启发式顾问的工作：模型帮助推荐初始化、参数或算子偏好，但并不稳定地位于优化闭环的在线控制位置。第三类是将 LLM 作为候选生成器或设计协作者的工作：模型直接提出候选结构、局部修改或修复提案，同时也往往带来表示、先验或搜索边界的变化。第四类工作关注混合优化中的公平比较、可归因性与审计问题，讨论当模型参与搜索后，收益究竟来自控制能力、额外知识注入，还是比较边界变化。

现有工作提供了重要背景，但对于本文关注的问题仍存在明显缺口：当 LLM 被放入高代价优化闭环内部承担 inline controller 角色时，研究重点不应只停留在最终结果是否改善，还需要回答控制过程会以何种方式 collapse、这些 collapse 是否能够被系统组织、以及 recovery 是否能以结构化方式进行。尤其是在 fixed boundary 与 budget-matched 的比较设置下，失效分析与恢复框架本身比“单次结果是否更好”更接近本文想回答的科学问题。

因此，本文与已有工作的差异不只在于应用场景，也不只在于是否使用 LLM，而在于研究对象本身发生了变化：我们研究的是固定优化边界内的 inline control 失稳与恢复，而不是更宽松条件下的生成式辅助优化。基于这一定位，相关工作在本文中的作用主要是构造 novelty gap 与 boundary-setting，而不是展开一场覆盖面很广的背景综述。
```

- [ ] **Step 2: Replace the Chinese problem formulation with a boundary-first version**

```tex
\section{问题定义：固定优化边界下的卫星热控布局优化}

本文研究的任务是卫星热控布局多目标优化。设计变量包括发热部组件布局变量以及散热边界变量；优化目标关注峰值温度与热分布均匀性，同时受制于可行性、散热资源预算与几何合法性等约束。一次候选方案是否有效，必须经过 repair、廉价约束检查与高代价数值评估的串联闭环，因此该任务天然具有昂贵评估、约束耦合和多目标权衡的特征。

为研究 inline controller 的真实作用，本文采用固定优化边界。也就是说，表示、动作集合、repair 机制、廉价约束、数值求解流程与评估预算在不同模式之间保持一致；变化的仅是控制层如何根据当前状态调度相同的优化能力。raw 模式对应不带语义控制的基线搜索，union 模式对应共享语义算子池上的非 LLM 统一调度，llm 模式则在完全相同的能力边界内引入语言模型做在线控制决策。

在这个问题定义下，本文不把 LLM 看作直接输出设计的生成器，而把它视为一个对既有优化动作进行阶段化调度的控制器。由此，后续实验与分析可以更清楚地区分：哪些行为变化来自控制机制本身，哪些变化则本不应归因于控制器。这个固定边界也是本文后续 collapse taxonomy、layered recovery 与归因讨论能够成立的前提。
```

- [ ] **Step 3: Replace the English related-work and problem-formulation sections with aligned drafts**

```tex
% paper/latex/sections/en/02_related_work.tex
\section{Related Work}

The literature most relevant to this paper can be grouped into four threads. The first studies simulation-driven optimization for satellite and aerospace thermal-control design, where layout variables, heat-rejection resources, and safety constraints interact under expensive evaluation. The second uses LLMs as heuristic advisors for initialization, parameter hints, or operator preference, without placing the model in a stable online control position inside the optimization loop. The third uses LLMs as candidate generators or design collaborators, where the model directly proposes structures, local edits, or repairs and often changes representation, prior knowledge, or the search boundary itself. The fourth addresses fairness, attribution, and auditability in hybrid optimization, asking whether a gain should be attributed to control ability, additional knowledge injection, or altered comparison conditions.

These threads provide important background but leave the central gap of this paper only partially answered. Once an LLM is placed inside an expensive optimization loop as an inline controller, the scientific question is not only whether the final result improves, but how the control process collapses, whether those collapses can be organized systematically, and whether recovery can be defined as a structured framework. Under fixed-boundary and budget-matched comparison, failure analysis and recovery design become first-class research questions rather than side notes to performance.

Accordingly, the distinctive move of this paper is not merely to use an LLM in a satellite setting. It is to study instability and recovery for inline control under a fixed optimization boundary. Related work therefore serves mainly to construct the novelty gap and boundary of comparison, not to provide an exhaustive survey.
```

```tex
% paper/latex/sections/en/03_problem_formulation.tex
\section{Problem Formulation: Satellite Thermal-Control Layout Optimization under a Fixed Boundary}

We study multi-objective satellite thermal-control layout optimization. The design variables include component layout variables and heat-rejection boundary variables, while the optimization objectives track peak temperature and thermal uniformity under feasibility, geometry, and heat-rejection constraints. Candidate validity is determined through a common loop of repair, cheap-constraint filtering, and expensive numerical evaluation, making the task a naturally expensive constrained multi-objective problem.

To isolate the role of inline control, we enforce a fixed optimization boundary. Representation, action space, repair mechanism, cheap constraints, solver-backed evaluation, and evaluation budget are shared across modes; only the control layer changes how the same optimization capabilities are scheduled. The raw mode serves as a baseline search without semantic control, the union mode uses non-LLM unified scheduling over the same semantic operator pool, and the llm mode introduces language-model control decisions under the same capability boundary.

Under this problem definition, the LLM is not treated as a design generator. It is treated as a controller that schedules existing optimization actions over time. This fixed boundary is the condition that makes later claims about collapse taxonomy, layered recovery, and attribution boundaries meaningful.
```

- [ ] **Step 4: Compile both language drafts after the boundary-setting rewrites**

Run: `cd /home/hymn/msfenicsx/paper/latex && latexmk -xelatex -interaction=nonstopmode -outdir=build/main_zh main_zh.tex && latexmk -pdf -interaction=nonstopmode -outdir=build/main_en main_en.tex`

Expected:
- both builds complete without a fatal error
- both PDFs are regenerated successfully
- the new sections do not introduce missing-reference or missing-file errors

### Task 7: Constrain experiments, discussion, abstract, limitations, and conclusion to the current claim layer

**Files:**
- Modify: `paper/latex/sections/zh/00_abstract.tex`
- Modify: `paper/latex/sections/en/00_abstract.tex`
- Modify: `paper/latex/sections/zh/06_experiments.tex`
- Modify: `paper/latex/sections/en/06_experiments.tex`
- Modify: `paper/latex/sections/zh/07_analysis_and_discussion.tex`
- Modify: `paper/latex/sections/en/07_analysis_and_discussion.tex`
- Modify: `paper/latex/sections/zh/08_limitations.tex`
- Modify: `paper/latex/sections/en/08_limitations.tex`
- Modify: `paper/latex/sections/zh/09_conclusion.tex`
- Modify: `paper/latex/sections/en/09_conclusion.tex`
- Compile targets: `paper/latex/main_zh.tex`, `paper/latex/main_en.tex`

- [ ] **Step 1: Replace the Chinese abstract, experiments, discussion, limitations, and conclusion with current-claim constrained drafts**

```tex
% paper/latex/sections/zh/00_abstract.tex
\begin{abstract}
本文研究高代价、受约束、多目标黑盒优化中的 inline LLM control。与将 LLM 用作候选生成器或闭环外顾问的设置不同，本文在固定表示、共享语义算子池、共享 repair/evaluation pipeline 与预算匹配的条件下，仅改变控制层，从而把研究重点转向一个稳定性问题：控制器会以何种方式 collapse，以及这些 collapse 能否被结构化恢复。围绕这一问题，本文提出面向 inline LLM control 的崩塌模式 taxonomy 与 layered recovery framework，并在可审计运行资产上讨论其机制证据与归因边界。当前稿件首先强调机制可识别性与恢复结构，而将更强的比较性结论留待后续更大规模实验验证。
\end{abstract}
```

```tex
% paper/latex/sections/zh/06_experiments.tex
\section{实验}

本文当前实验部分的职责不是给出最终完整比较，而是验证三件事：其一，inline LLM control 的 collapse 是否能够在统一运行资产中被实际观察到；其二，taxonomy 是否能够解释这些退化现象；其三，layered recovery 是否能够在机制层面改善控制行为。基于这一目标，当前稿件以已完成的单案例运行作为机制证据起点，并把更多方法、更大模型集合、多 seed 统计与系统性消融留给后续扩展。

围绕这一证据目标，实验记录应优先展示 summary、timeline、milestone 与 trace 四层资产如何支持 collapse 识别与 recovery 讨论，而不是急于把尚未完成的大规模比较包装为终局结论。对于当前版本，性能结果可以作为补充信息出现，但不承担全文主叙事。
```

```tex
% paper/latex/sections/zh/07_analysis_and_discussion.tex
\section{分析与讨论}

本文当前分析重点在于：当控制边界被固定后，collapse taxonomy 与 layered recovery 是否为理解 inline LLM control 提供了更清晰的机制语言。如果答案是肯定的，那么这一框架的价值首先体现在可解释性、可归因性与后续实验扩展的组织能力上，而不只是短期性能数字。

从更一般的角度看，本文的讨论可以谨慎外推到更广义的 LLM-controlled black-box optimization：一旦语言模型被放入昂贵评估闭环，稳定性与恢复问题就可能比单次性能增益更具决定性意义。不过，这一外推仍需等待更多任务、更多模型与更多对照设置的支持，因此当前稿件只把它作为讨论方向，而不作为既定结论。
```

```tex
% paper/latex/sections/zh/08_limitations.tex
\section{局限性}

本文当前版本仍存在明显局限。首先，实验范围尚未覆盖更多方法、更多模型、更多 seed 与更系统的消融，因此稿件目前主要支撑机制层主张，而非最终比较优势。其次，collapse taxonomy 与 layered recovery 的更广泛可迁移性仍需在更多问题族中检验。最后，当前的证据链虽然增强了可审计性，但并不意味着已经穷尽所有可能影响控制行为的因素。
```

```tex
% paper/latex/sections/zh/09_conclusion.tex
\section{结论}

本文将高代价约束优化中的 inline LLM control 重构为一个稳定性与失效机制问题，而不只是性能增强问题。在固定优化边界下，我们提出 collapse taxonomy 与 layered recovery framework，用以组织控制失稳的识别与干预。当前稿件首先建立这一机制主线，并为后续更大规模比较实验保留统一而可升级的叙事结构。
```

- [ ] **Step 2: Replace the English abstract, experiments, discussion, limitations, and conclusion with aligned drafts**

```tex
% paper/latex/sections/en/00_abstract.tex
\begin{abstract}
We study inline LLM control in expensive, constrained, multi-objective black-box optimization. Unlike settings that use LLMs as candidate generators or heuristic advisors outside the loop, we keep representation, semantic operator pool, repair/evaluation pipeline, and evaluation budget fixed, and vary only the control layer. This shifts the scientific focus from raw performance to stability: how inline control collapses and whether those collapses admit structured recovery. We therefore present a collapse taxonomy and a layered recovery framework, and discuss their mechanism evidence and attribution boundary through auditable run assets. The current draft emphasizes identifiable mechanism and recovery structure, while leaving stronger comparative claims to later large-scale experiments.
\end{abstract}
```

```tex
% paper/latex/sections/en/06_experiments.tex
\section{Experiments}

The present role of the experiments section is not to deliver the final comparative story. It is to validate three claims: that collapse phenomena in inline LLM control can be observed in shared run assets, that the proposed taxonomy can explain those degradations, and that layered recovery can improve controller behavior in mechanism-relevant ways. The current manuscript therefore uses the completed single-case evidence as a starting point and leaves broader baseline coverage, larger model sets, multi-seed statistics, and fuller ablations to later expansion.

Accordingly, the experiments should prioritize showing how summary, timeline, milestone, and trace assets support collapse identification and recovery analysis. Performance outcomes may still appear, but they should not carry the main narrative burden in the current draft.
```

```tex
% paper/latex/sections/en/07_analysis_and_discussion.tex
\section{Analysis and Discussion}

The current analysis focuses on whether collapse taxonomy and layered recovery provide a clearer mechanism language for inline LLM control once the comparison boundary is fixed. If so, the immediate value of the framework lies in interpretability, attribution clarity, and its ability to organize later experiment growth rather than in short-term performance numbers alone.

More broadly, the framing may extend to other families of LLM-controlled black-box optimization in which expensive evaluation makes stability and recovery more decisive than isolated gains. However, that broader claim still requires support from more tasks, more models, and stronger comparative evidence, so the current draft presents it as a discussion direction rather than as a settled conclusion.
```

```tex
% paper/latex/sections/en/08_limitations.tex
\section{Limitations}

The current manuscript has clear limitations. The experiment set does not yet cover more methods, more models, more seeds, or a more systematic ablation matrix, so the present draft mainly supports mechanism-level claims rather than final comparative superiority. The portability of the collapse taxonomy and layered recovery framework also remains to be tested on broader problem families. Finally, although the evidence chain improves auditability, it does not eliminate every factor that may influence controller behavior.
```

```tex
% paper/latex/sections/en/09_conclusion.tex
\section{Conclusion}

This paper reframes inline LLM control in expensive constrained optimization as a stability-and-failure-mechanism problem rather than only a performance question. Under a fixed optimization boundary, we present a collapse taxonomy and a layered recovery framework for organizing instability identification and intervention. The current draft establishes that mechanism-centered narrative while preserving a structure that can absorb stronger comparative evidence later.
```

- [ ] **Step 3: Compile both language drafts for the final narrative-consistency pass**

Run: `cd /home/hymn/msfenicsx/paper/latex && latexmk -xelatex -interaction=nonstopmode -outdir=build/main_zh main_zh.tex && latexmk -pdf -interaction=nonstopmode -outdir=build/main_en main_en.tex`

Expected:
- both builds complete without a fatal error
- both PDFs exist in their build directories
- the abstract, experiments, discussion, limitations, and conclusion all reflect the current claim-strength policy

### Task 8: Run the final manuscript audit for this optimization pass

**Files:**
- Read: `paper/latex/sections/zh/01_introduction.tex`
- Read: `paper/latex/sections/zh/02_related_work.tex`
- Read: `paper/latex/sections/zh/03_problem_formulation.tex`
- Read: `paper/latex/sections/zh/04_method.tex`
- Read: `paper/latex/sections/zh/05_collapse_and_recovery.tex`
- Read: `paper/latex/sections/zh/06_experiments.tex`
- Read: `paper/latex/sections/zh/07_analysis_and_discussion.tex`
- Read: `paper/latex/sections/zh/08_limitations.tex`
- Read: `paper/latex/sections/zh/09_conclusion.tex`
- Read: `paper/latex/sections/en/01_introduction.tex`
- Read: `paper/latex/sections/en/02_related_work.tex`
- Read: `paper/latex/sections/en/03_problem_formulation.tex`
- Read: `paper/latex/sections/en/04_method.tex`
- Read: `paper/latex/sections/en/05_collapse_and_recovery.tex`
- Read: `paper/latex/sections/en/06_experiments.tex`
- Read: `paper/latex/sections/en/07_analysis_and_discussion.tex`
- Read: `paper/latex/sections/en/08_limitations.tex`
- Read: `paper/latex/sections/en/09_conclusion.tex`
- Create: `paper/references/2026-04-21-chapter-pass-summary.md`

- [ ] **Step 1: Check for the four forbidden drift patterns**

Run: `grep -RniE 'dominates|state-of-the-art|SOTA|best overall|universally|outperforms all' /home/hymn/msfenicsx/paper/latex/sections || true`

Expected:
- no headline-performance wording appears unless backed by the current evidence policy
- no universal claim appears in the current draft

- [ ] **Step 2: Check that the chapter roles are intact**

Run: `sed -n '1,220p' /home/hymn/msfenicsx/paper/latex/sections/zh/01_introduction.tex && printf '\n---\n' && sed -n '1,220p' /home/hymn/msfenicsx/paper/latex/sections/zh/02_related_work.tex && printf '\n---\n' && sed -n '1,260p' /home/hymn/msfenicsx/paper/latex/sections/zh/04_method.tex && printf '\n---\n' && sed -n '1,260p' /home/hymn/msfenicsx/paper/latex/sections/zh/05_collapse_and_recovery.tex`

Expected:
- Introduction opens with the problem and collapse
- Related Work constructs a gap rather than a broad survey
- Method defines the fixed boundary before discussing collapse
- Collapse and Recovery presents taxonomy before layered recovery

- [ ] **Step 3: Record completion in a single summary note for the next chapter pass**

Write to `paper/references/2026-04-21-chapter-pass-summary.md`:

```markdown
# Chapter Pass Summary

Completed in this pass:
- lightweight calibration memo
- Chinese and English introduction alignment
- Chinese and English method / collapse-recovery alignment
- Chinese and English related work / problem formulation alignment
- current-claim constrained abstract, experiments, discussion, limitations, and conclusion

Next recommended pass:
- deeper chapter-specific literature retrieval for `02_related_work`
- chapter-specific refinement for `06_experiments` after more evidence arrives
- title polishing only after the expanded experiment matrix exists
```

- [ ] **Step 4: Verify the summary note exists and is readable**

Run: `sed -n '1,220p' /home/hymn/msfenicsx/paper/references/2026-04-21-chapter-pass-summary.md`

Expected:
- file opens without errors
- file lists completed items for this pass
- file lists the next recommended pass items
