# S2 Staged Internal Group-Meeting Beamer Deck — Design

> Status: historical S2 presentation design; active paper-facing debugging has moved to `s5_aggressive15` in the S5-S7 family.

- **Date**: 2026-04-21
- **Scope**: design one Chinese Beamer deck for an 18–20 minute internal group meeting based on the historical `paper/latex/main_zh.tex` draft, with about 20 slides, mechanism-first narrative, and representative evidence from the historical `s2_staged` assets.
- **Applies to**: `paper/latex/`, `paper/latex/build/tikzz/`, `scenario_runs/compare_reports/s2_staged/`, `scenario_runs/s2_staged/`, `docs/superpowers/specs/`, `docs/superpowers/plans/`
- **Primary source**: [paper/latex/main_zh.tex](../../paper/latex/main_zh.tex), especially [paper/latex/sections/zh/04_method.tex](../../paper/latex/sections/zh/04_method.tex), [paper/latex/sections/zh/06_experiments.tex](../../paper/latex/sections/zh/06_experiments.tex), and [paper/latex/sections/zh/07_analysis_and_discussion.tex](../../paper/latex/sections/zh/07_analysis_and_discussion.tex)

## 1. Goal

Create a presentation-facing Beamer deck that translates the current Chinese paper draft into a concise, visually strong, internal-report version.

The deck must not simply compress the paper section-by-section. Instead, it should reorganize the material around the group-meeting question:

> under a fixed optimization boundary, what exactly is the current scientific claim about `raw`, `union`, and `llm`, what evidence already supports it, and what remains open?

The user-approved positioning is:

- **audience**: internal group meeting, already familiar with the project background
- **duration**: 18–20 minutes
- **narrative priority**: mechanism first, results as support
- **claim strength**: relatively aggressive wording for current progress, but not full comparative closure
- **style**: balanced; argument-led on key slides, figure-led on evidence slides

## 2. Presentation Strategy

### 2.1 The deck is not a paper dump

The Beamer deck must not mirror all nine paper sections mechanically. For a 20-slide internal talk, the correct unit is the **argument block**, not the manuscript section.

The talk should feel like a guided claim:

1. we fixed the optimization boundary,
2. we isolated the controller as the only changing factor,
3. we organized controller failure into collapse taxonomy and layered recovery,
4. the historical `s2_staged` evidence already showed visible mode differences,
5. the `llm` advantage is not just endpoint quality, but cross-stage objective focus and budget use.

### 2.2 Main speaking thesis

The hidden one-sentence thesis of the deck is:

> 在固定优化边界下，LLM 作为在线控制器已经显示出可见优势，而且这种优势可以被组织为 collapse taxonomy 与 layered recovery 的机制分析主线。

Every major block of the slides should either establish this sentence or defend it.

## 3. Narrative Contract

### 3.1 What the talk must emphasize

The main emphasis is:

- fairness by fixed optimization boundary
- inline controller framing rather than design generator framing
- collapse/recovery as mechanism language rather than after-the-fact storytelling
- current evidence chain from compare-report assets to single-run process assets
- strong but disciplined wording of current results

### 3.2 What the talk must explicitly avoid

The deck must avoid these failure modes:

- presenting the work as “LLM just beats everything”
- turning the talk into a long reheating of paper background the audience already knows
- showing dense paper tables with tiny text as the primary evidence format
- mixing compare-report summary evidence and single-run mechanism evidence without boundary
- overselling the current version as already-final comparative closure

## 4. Slide Count And Timing

The target is **20 main slides**.

Recommended time budget:

- opening and agenda: 1.5–2 minutes
- problem and boundary: 3 minutes
- method and mechanism: 6 minutes
- evidence and representative results: 6–7 minutes
- innovations, current conclusions, limitations, next step: 2.5–3 minutes

That pacing preserves the user-approved “机制优先，结果支撑” rhythm while still giving the audience enough visual evidence.

## 5. Deck Architecture

The deck should be implemented as five slide blocks:

1. **Opening**
2. **Problem and fixed boundary**
3. **Method and mechanism**
4. **Evidence and representative results**
5. **Innovations, current conclusions, limitations, next step**

This is a presentation structure, not a paper structure. It should remain stable even if the manuscript later adds or removes subsections.

## 6. Page-By-Page Design

### Slide 1 — Title

**Purpose:** establish the paper-facing title and internal-talk identity.

**Title suggestion:**

`面向卫星热控布局多目标优化的 LLM 在线控制器`

**Subtitle suggestion:**

`组会汇报：公平比较、崩塌模式与分层恢复`

**Layout:** title slide with title, speaker, group/date, and one short footer sentence.

**Footer sentence:**

`当前重点：固定优化边界下的机制主线与代表证据`

### Slide 2 — This talk answers three questions

**Purpose:** replace a generic outline with three explicit questions.

**Core content:**

1. 为什么必须先固定比较边界？
2. 在这个边界里，LLM controller 到底改变了什么？
3. 当前证据已经支持到什么程度？

**Layout:** one large statement at top, three numbered questions underneath.

**Key sentence on slide:**

`这次汇报不是复述整篇初稿，而是回答“当前主张是否已经被证据链撑住”。`

### Slide 3 — Why fixed optimization boundary first

**Purpose:** state why the work is not open-ended generation.

**Core content:**

- expensive, constrained, multi-objective setting
- fairness and attribution require fixed representation/action/evaluation budget
- otherwise controller effects are confounded with search-space and operator changes

**Layout:** left side short bullets, right side one highlighted takeaway box.

**Key sentence on slide:**

`如果比较边界不固定，就无法把收益归因到 controller decision 本身。`

### Slide 4 — Fair comparison object: raw / union / llm

**Purpose:** make the comparison boundary visually concrete.

**Primary visual:** reuse [paper/latex/build/tikzz/fixed_boundary_modes_a1.pdf](../../paper/latex/build/tikzz/fixed_boundary_modes_a1.pdf)

**Layout:** large figure with a short caption-like takeaway above or below.

**Key sentence on slide:**

`三者共享表示、动作池、repair/evaluation pipeline 与预算；只改控制层。`

### Slide 5 — Problem definition and controller-only variation

**Purpose:** connect the mathematical problem to the comparison object.

**Core content:**

- decision variables: layout + sink variables
- objectives: `T_max` and `G_rms`
- feasibility jointly determined by legality, sink budget, and expensive evaluation
- controller policy `π_m` is the only mode-specific mapping

**Layout:** not a full equation dump; keep one compact equation block plus three interpretation bullets.

**Key sentence on slide:**

`本文不是给 LLM 更大设计自由，而是在同一问题内观察控制行为如何改变搜索轨迹。`

### Slide 6 — Inline control loop

**Purpose:** explain where LLM sits in the optimization loop.

**Primary visual:** reuse [paper/latex/build/tikzz/inline_control_loop_a1.pdf](../../paper/latex/build/tikzz/inline_control_loop_a1.pdf)

**Layout:** one figure-dominant slide.

**Key sentence on slide:**

`LLM 读取压缩状态并输出调度偏好，但候选生成、修复和评估仍由共享优化系统完成。`

### Slide 7 — What changes and what stays fixed

**Purpose:** prevent audience misunderstanding after the loop figure.

**Core content:** two columns.

- left: **shared backbone**
  - representation
  - semantic operator registry
  - repair / cheap constraints / PDE
  - optimization budget
- right: **controller-specific behavior**
  - phase emphasis
  - action-family preference
  - history use
  - objective focus

**Layout:** two-column comparison cards.

**Key sentence on slide:**

`“LLM 更强”在本文里只能被理解为“控制更强”，不能被偷换成“系统更自由”。`

### Slide 8 — Why move from results to mechanism

**Purpose:** motivate collapse / recovery language.

**Core content:**

- endpoint numbers alone cannot explain controller stability
- repeated low-yield behavior is a trajectory problem, not a single-step mistake
- process assets make mechanism discussion auditable

**Layout:** top statement, bottom three short bullets.

**Key sentence on slide:**

`核心问题不是 LLM 偶尔能否更强，而是其失稳是否具有结构、能否被识别、能否被恢复。`

### Slide 9 — Collapse taxonomy

**Purpose:** present the five collapse modes as a scientific abstraction.

**Primary visual:** reuse [paper/latex/build/tikzz/taxonomy_recovery_map_a1.pdf](../../paper/latex/build/tikzz/taxonomy_recovery_map_a1.pdf), but visually crop/emphasize the left taxonomy side if needed.

**Core content to name aloud:**

- semantic misalignment
- spatial blindness
- objective-intent drift
- history-retrieval failure
- late-stage saturation

**Layout:** figure-dominant with one takeaway sentence.

**Key sentence on slide:**

`collapse 不是“某一步做坏了”，而是控制偏离被持续放大后形成的轨迹级退化。`

### Slide 10 — Layered recovery

**Purpose:** present recovery as organized intervention rather than ad hoc patching.

**Primary visual:** reuse the same taxonomy/recovery map, now emphasize the right side conceptually.

**Core content:**

- semantic-layer recovery
- spatial-layer recovery
- intent-layer recovery
- retrieval-layer recovery
- saturation-layer recovery

**Layout:** figure + one small mapping sentence.

**Key sentence on slide:**

`layered recovery 的价值不在于补丁技巧，而在于把恢复路径与崩塌来源一一对应。`

### Slide 11 — Evidence asset map

**Purpose:** define the evidence boundary before showing results.

**Primary visual:** reuse [paper/latex/build/tikzz/evidence_asset_map_a1.pdf](../../paper/latex/build/tikzz/evidence_asset_map_a1.pdf)

**Core content:**

- raw / union from `0420_2256`
- llm from `0421_0207`
- compare report `0421_0420` only summarizes cross-mode differences
- mechanism interpretation returns to llm single-run assets

**Key sentence on slide:**

`compare report 回答“差异是什么”，单运行资产回答“这些差异在过程里如何出现”。`

### Slide 12 — Cross-mode summary result

**Purpose:** establish the strongest current high-level result.

**Primary visual:** reuse `summary_overview.png` from [paper/latex/sections/zh/06_experiments.tex:18-23](../../paper/latex/sections/zh/06_experiments.tex#L18-L23)

**Core content:**

- llm currently achieves best `T_max`, best `G_rms`, highest feasible rate, highest final hypervolume
- raw still beats union on final representative quality
- union enters feasible region earlier

**Layout:** big summary figure + three one-line callouts.

**Key sentence on slide:**

`当前证据已经不是“有没有差异”，而是“差异表现为不同阶段的不同优势结构”。`

### Slide 13 — Progress dashboard and stage difference

**Purpose:** show that early feasibility and deep feasible-region optimization are different questions.

**Primary visual:** reuse `progress_dashboard.png` from [paper/latex/sections/zh/06_experiments.tex:43-48](../../paper/latex/sections/zh/06_experiments.tex#L43-L48)

**Core content:**

- union first feasible earliest
- raw slower to feasible but still locally resilient later
- llm shows stronger sustained progress after entering the feasible region

**Layout:** large dashboard figure + a short side column of stage interpretation.

**Key sentence on slide:**

`union 更早可行、raw 后期仍有韧性、llm 则更能跨阶段保持目标聚焦与预算效率。`

### Slide 14 — Representative final layouts

**Purpose:** move from curves to visible representative solutions.

**Primary visuals:** three layout figures from [paper/latex/sections/zh/06_experiments.tex:70-79](../../paper/latex/sections/zh/06_experiments.tex#L70-L79)

**Layout:** three equal-width panels labeled `raw`, `union`, `llm`.

**Key sentence on slide:**

`比较不是停留在表格排序上，而是已经落实到可见代表解层面。`

### Slide 15 — Temperature and gradient field comparison

**Purpose:** connect controller behavior to physical-field consequences.

**Primary visuals:** representative temperature and gradient fields from [paper/latex/sections/zh/06_experiments.tex:81-101](../../paper/latex/sections/zh/06_experiments.tex#L81-L101)

**Layout:** two-row grid.

- top row: three temperature fields
- bottom row: three gradient fields

**Key sentence on slide:**

`controller decision 的差异最终反映在热点分布、梯度集中区域与布局密度变化上。`

### Slide 16 — Single-run llm mechanism evidence

**Purpose:** show the process-level mechanism window for `0421_0207`.

**Primary visuals:** `objective_progress.png` and `operator_phase_heatmap.png` from [paper/latex/sections/zh/06_experiments.tex:109-121](../../paper/latex/sections/zh/06_experiments.tex#L109-L121)

**Layout:** two-panel slide.

**Key sentence on slide:**

`objective progress 给出时间上的性能推进，operator-phase heatmap 给出动作与阶段偏好的机制窗口。`

### Slide 17 — Why the evidence chain closes the mechanism story

**Purpose:** explicitly close the logic between compare report and single-run evidence.

**Core content:**

- compare report gives cross-mode result separation
- single-run assets give process visibility
- together they support collapse/recovery analysis rather than just endpoint ranking

**Layout:** one centered synthesis diagram or three-box chain written in Beamer blocks.

**Key sentence on slide:**

`本文当前最重要的进展，不只是 llm 数值更强，而是“结果差异 + 过程证据”已经能支撑机制化表述。`

### Slide 18 — Innovations of this version

**Purpose:** summarize novelty in presentation language rather than paper prose.

**Recommended three innovations:**

1. fixed-boundary fairness framing for inline LLM controller comparison
2. collapse taxonomy + layered recovery as mechanism language
3. trace-auditable evidence chain from compare report to single-run assets

**Layout:** three stacked innovation cards.

**Key sentence on slide:**

`这版工作的创新不只是新结果，而是把“LLM + 优化”的讨论从结果堆叠推进到机制归因。`

### Slide 19 — Current conclusion

**Purpose:** give the strongest allowed current wording.

**Core content:**

- visible mode differences are already established under fixed boundary
- current representative evidence favors llm most strongly on integrated outcome quality
- the more important point is stage-structured controller behavior

**Layout:** one bold top sentence + three disciplined subclaims.

**Key sentence on slide:**

`当前可以讲“llm 已显示明显领先信号”，但更准确的表达是“llm 在跨阶段控制上表现出更强的一致性与综合性”。`

### Slide 20 — Limitations and next step

**Purpose:** close strongly without weakening the deck.

**Core content:**

- historical evidence still centered on `s2_staged`
- current mechanism line is stronger than current large-scale closure
- next step: multi-seed / broader baseline / recovery intervention validation

**Layout:** left column limitations, right column next-step bullets, final footer line.

**Footer sentence:**

`下一步不是重写故事，而是沿着这条机制主线扩证据、做干预、补 closure。`

## 7. Visual Design Contract

### 7.1 Overall style

The Beamer deck should look like an internal research talk, not a conference poster and not a corporate template.

Rules:

- white or very light background
- restrained blue as main accent, matching the paper-facing TikZ palette
- orange only for emphasis, not as a second theme color everywhere
- Chinese main text with LaTeX-default math and English identifiers
- generous whitespace and large readable text

### 7.2 Layout discipline

- one main idea per slide
- no slide should contain both a dense table and multiple large figures
- raw paper tables should not be pasted as unreadable screenshots
- if numbers matter, convert them to 2–3 presentation-ready callouts instead of dense tabular blocks
- on figure slides, text should conclude, not compete with the figure

### 7.3 Figure usage policy

Allowed figure families:

- existing TikZ architecture figures under `paper/latex/build/tikzz/`
- existing compare-report figures under `scenario_runs/compare_reports/s2_staged/.../figures/`
- existing representative run figures under `scenario_runs/s2_staged/.../figures/`

Prefer curating stable copies into a Beamer-local figures directory rather than relying on deep relative paths forever.

## 8. File And Build Contract

### 8.1 Source layout

The implementation should create a dedicated Beamer source alongside the manuscript, not mix slide content into `main_zh.tex`.

Recommended structure:

```text
paper/latex/
├── main_beamer_zh.tex
├── sections/
│   └── beamer_zh/
│       ├── 00_title_and_questions.tex
│       ├── 01_boundary_and_problem.tex
│       ├── 02_method_and_mechanism.tex
│       ├── 03_evidence_and_results.tex
│       └── 04_conclusion_and_next.tex
├── figures/
│   └── beamer_internal/
└── build/
    └── beamer_zh/
```

### 8.2 Asset policy

The Beamer deck should use curated local copies for key assets that the slides depend on, especially:

- fixed-boundary modes figure
- inline control loop figure
- taxonomy/recovery map figure
- evidence asset map figure
- summary overview figure
- progress dashboard figure
- representative layout / temperature / gradient figures
- llm single-run objective progress and operator-phase heatmap

This keeps the slide build stable even if raw run directories are later reorganized.

### 8.3 Compilation

Use a Chinese-capable Beamer setup with `xelatex` or `latexmk -xelatex` and direct the output into:

```text
paper/latex/build/beamer_zh/
```

## 9. Non-Goals

This design does not include:

- writing the spoken presenter notes in full paragraph form
- building an English Beamer deck in parallel
- polishing every figure for external conference submission style
- adding new experiments just for the talk
- redesigning the scientific claims beyond the current paper-facing narrative

## 10. Acceptance Criteria

The design is successful if all of the following are true:

1. The deck compiles into one Chinese Beamer PDF with about 20 slides.
2. The talk can be delivered in 18–20 minutes without rushing the result section.
3. The opening makes the three main questions explicit.
4. The audience can clearly see that fixed-boundary fairness is the starting point.
5. Collapse taxonomy and layered recovery appear as the central mechanism contribution.
6. Cross-mode evidence and single-run evidence are separated but connected.
7. The conclusion is strong, but still stops short of claiming full comparative closure.

## 11. Risks And Mitigations

### 11.1 Risk: too much paper detail

A paper-derived slide deck can easily become overfull.

**Mitigation:** use argument blocks, not manuscript blocks; move dense tables out; keep each slide to one claim.

### 11.2 Risk: result slides overshadow the mechanism story

If too many figure slides appear without framing, the talk becomes a result showcase instead of a mechanism talk.

**Mitigation:** insert explicit synthesis slides before and after the evidence block, especially Slides 8, 11, and 17.

### 11.3 Risk: overclaiming current evidence

The assets were strong, but still concentrated on the then-present `s2_staged` line.

**Mitigation:** use strong wording on visible advantage, but reserve the final slide for the closure boundary and next-step expansion.
