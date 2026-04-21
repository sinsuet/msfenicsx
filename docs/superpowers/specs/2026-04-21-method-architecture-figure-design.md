# Satellite Paper Method Architecture Figure — Design

- **Date**: 2026-04-21
- **Scope**: add one paper-facing TikZ architecture figure for the Chinese method section, compile it with the existing LaTeX environment, and store all figure source/build artifacts under `paper/latex/build/tikzz/`.
- **Applies to**: `paper/latex/sections/zh/04_method.tex`, `paper/latex/main_zh.tex`, `paper/latex/build/tikzz/`
- **Primary source**: [paper/latex/sections/zh/04_method.tex](../../paper/latex/sections/zh/04_method.tex)

## 1. Goal

Create a publication-ready TikZ architecture figure for the method section that makes the paper's fairness claim legible at a glance: `raw`, `union`, and `llm` must be shown as sharing the same representation, operator set, repair/filter/evaluation pipeline, and optimization budget, while differing only at the controller layer.

The figure should visually follow the user's supplied reference style rather than a generic flowchart style. That means soft colored panel backgrounds, rounded white internal blocks, restrained academic colors, dark primary routing lines, and light accent arrows reserved for emphasis.

## 2. User-Approved Constraints

The following choices were explicitly approved during brainstorming:

- Diagram family: layered architecture figure, not a pure flowchart.
- Content emphasis: fair comparison first.
- Layout choice: **A1**.
- Output format: TikZ/PGF suitable for direct LaTeX inclusion.
- Visual reference: match the supplied figure's color language and paper-style composition.
- Build location: create a new `paper/latex/build/tikzz/` directory and keep all figure-related source/build outputs there.
- Compilation: use the repository's existing TeX environment.

## 3. Figure Semantics

### 3.1 Main claim

The figure must communicate the central claim from [paper/latex/sections/zh/04_method.tex:2-6](../../paper/latex/sections/zh/04_method.tex#L2-L6): the comparison keeps optimization boundaries fixed and changes only the controller's scheduling policy.

### 3.2 Required semantic blocks

The left-side main panel represents the shared optimization backbone with three stacked layers:

1. **Representation Layer**
   - 15 component `x/y` variables
   - sink boundary variables
2. **Shared Operator Layer**
   - semantic shared operator registry
   - candidate action families
3. **Shared Repair / Evaluation Layer**
   - geometry repair
   - cheap constraint filtering
   - expensive PDE evaluation

Below the main panel, three controller blocks must appear side-by-side:

- `raw`: baseline evolutionary scheduling
- `union`: shared-registry non-LLM scheduling
- `llm`: state-guided online semantic scheduling

The right-side secondary panel must summarize the fairness constraints:

- same representation
- same operator pool
- same repair / cheap filtering / evaluation
- same optimization budget
- controller only changes decision policy

### 3.3 Flow semantics

The primary flow is conceptual rather than literal solver code flow:

- controller blocks feed the shared operator layer
- operator layer feeds repair / evaluation
- repair / evaluation produces compressed state / progress signals back to the controller layer

This keeps the figure aligned with [paper/latex/sections/zh/04_method.tex:6](../../paper/latex/sections/zh/04_method.tex#L6), while preserving the layered architecture emphasis.

## 4. Visual Design Contract

### 4.1 Template family

Use a `paper-block-feedback`-style composition similar to the user-supplied reference image:

- one large soft blue main panel on the left
- one smaller soft orange explanatory panel on the right
- rounded white cards inside each panel
- dark gray/black primary edges
- sparse colored accents for emphasis only

### 4.2 Palette

Use restrained academic colors close to the approved reference:

- **main blue border**: `#3A86C8`
- **main blue fill**: `#EAF3FB`
- **accent orange border**: `#E67E22`
- **accent orange fill**: `#FDF1E3`
- **feedback purple**: `#8E44AD`
- **primary routing gray**: `#333333`
- **secondary dashed gray**: `#BDBDBD`

The `llm` controller may receive a slightly stronger border treatment than `raw` and `union`, but the figure must avoid implying that the action space itself differs.

### 4.3 Typography

The figure text should be English paper style even though the surrounding manuscript is Chinese, because the method section already uses English identifiers such as `raw`, `union`, `llm`, and layer names read more cleanly in a figure when kept concise.

Typography rules:

- serif or LaTeX-default text is acceptable
- sentence-case labels
- compact line breaks within blocks
- no oversized decorative text

### 4.4 Composition

The final figure should fit comfortably in a paper figure slot without looking crowded. Prefer a landscape standalone figure that can later be included as a PDF. The right panel is explanatory support, not a competing second architecture.

## 5. File And Build Contract

### 5.1 Source and artifact locations

Create and use:

```text
paper/latex/build/tikzz/
```

Expected files:

- `paper/latex/build/tikzz/method_architecture_a1.tex`
- `paper/latex/build/tikzz/method_architecture_a1.pdf`
- `paper/latex/build/tikzz/method_architecture_a1.log`
- `paper/latex/build/tikzz/method_architecture_a1.aux`
- other normal TeX byproducts in the same directory

If a PNG preview is easy to generate locally from the compiled PDF, it may be added, but PDF is the required deliverable.

### 5.2 Inclusion into the paper

`paper/latex/sections/zh/04_method.tex` should gain a `figure` environment that includes the compiled PDF via `\includegraphics`, rather than embedding the full TikZ directly inside the section. This keeps the manuscript source readable and follows the repository's current use of `graphicx` in [paper/latex/main_zh.tex:3](../../paper/latex/main_zh.tex#L3).

## 6. Compilation Strategy

The repository already shows:

- Chinese main paper built with `xelatex`
- standalone figure compilation support available via installed `standalone.cls` and `tikz.sty`

Therefore the figure should be compiled locally using the existing TeX environment, with a standalone TikZ document under `paper/latex/build/tikzz/`. The compiled PDF should then be included from `sections/zh/04_method.tex`.

## 7. Non-Goals

This work does not include:

- redesigning the whole paper template
- generating multiple alternative figure families in one pass
- adding new manuscript-wide TikZ macros unless necessary
- changing the method semantics beyond what the existing text already states
- drawing a detailed run-time trace asset panel for `summary / timeline / milestone / trace` in this figure

The current figure is a fairness-focused architecture summary, not a full evidence-chain figure.

## 8. Acceptance Criteria

The design is successful if all of the following are true:

1. The compiled figure clearly shows four conceptual levels with controller-level differentiation only.
2. A reader can immediately see that `raw`, `union`, and `llm` share the same backbone.
3. The visual tone is recognizably close to the user-provided reference image.
4. The figure compiles successfully in the repository's current TeX environment.
5. The Chinese method section can include the resulting PDF without breaking manuscript compilation.

## 9. Risks And Mitigations

### 9.1 Overcrowding risk

A fairness note, three shared layers, and three controller boxes can overcrowd the canvas.

**Mitigation:** keep each internal card concise, move fairness bullets into the right orange panel, and keep only one feedback arrow.

### 9.2 Style drift risk

A generic TikZ layout would satisfy semantics but miss the requested reference style.

**Mitigation:** explicitly encode panel fills, rounded white cards, restrained accent palette, and a top feedback arc into the TikZ source.

### 9.3 Build-fragility risk

Standalone TikZ figures can fail if compiled with the wrong engine or missing package assumptions.

**Mitigation:** compile locally with the existing environment, prefer a self-contained standalone `.tex`, and include the compiled PDF in the manuscript instead of raw TikZ.
