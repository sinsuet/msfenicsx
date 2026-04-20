# Satellite Thermal-Control Paper Writing with AAAI Template — Design

- **Date**: 2026-04-20
- **Scope**: define the paper-writing workflow, directory contract, bilingual draft strategy, and AAAI-template-based LaTeX bootstrap for the satellite thermal-control LLM-controller paper.
- **Applies to**: `paper/`, `paper/references/`, `paper/latex/`, `docs/superpowers/specs/`.
- **Depends on**: the already-agreed paper narrative: satellite thermal-control background, fixed-boundary inline controller framing, collapse taxonomy, layered recovery, and summary/timeline/milestone/trace evidence chain.

## 1. Motivation

We now have a stable paper-facing narrative, but writing directly into ad hoc files would create drift between:

1. the agreed scientific story,
2. the actual LaTeX structure,
3. the bibliography workflow, and
4. the bilingual drafting process.

This spec establishes a clean paper workspace under `paper/` and defines how we will draft the manuscript using an **AAAI official template as the initial formatting reference**, while writing **Chinese and English drafts in parallel**. The immediate goal is not submission packaging yet; it is to create a disciplined authoring scaffold that keeps the story, structure, and references aligned.

## 2. Non-Goals

- Finalizing the target venue choice at this step. AAAI is used as the initial template/example, not as an irreversible submission commitment.
- Producing the final camera-ready version.
- Deciding every citation before writing begins.
- Building a multi-template system (AAAI + NeurIPS + journal variants) in this phase.
- Creating a complex document build system beyond what is needed for a clean LaTeX authoring loop.

## 3. Authoring Principles

### 3.1 Application-first framing

The paper must be written as a **satellite thermal-control layout optimization** paper with a method contribution, not as a generic thermal toy problem paper.

The stable framing is:

- **Application**: satellite thermal-control layout optimization
- **Optimization class**: expensive, constrained, multi-objective simulation-driven design
- **Method**: LLM as inline controller under a fixed optimization boundary
- **Scientific contribution**: collapse taxonomy, layered recovery, and trace-auditable evaluation

### 3.2 Chinese-first, English-aligned drafting

The immediate drafting order is:

1. write a Chinese draft first,
2. keep the section structure aligned with the future English paper,
3. then produce the English draft against the same structure.

Rules:

- Chinese is the **thinking and content-authoring source draft**.
- English is the **submission-facing aligned draft**, not a separate independently evolving manuscript.
- Section ordering, subsection boundaries, figure/table intents, and contribution wording must stay aligned across languages.

### 3.3 Spec is the authoritative writing contract

Because `paper/` is intentionally git-ignored, the authoritative, versioned agreement about writing structure must live in this spec file under `docs/superpowers/specs/`.

The `paper/` tree is a working area; the spec remains the durable source of truth for workflow and layout decisions.

## 4. Directory Contract

The paper workspace root is:

```text
paper/
```

It is intentionally git-ignored.

### 4.1 Top-level layout

```text
paper/
├── references/
└── latex/
```

Rules:

- `paper/references/` stores writing-time bibliography assets and reading notes for the paper.
- `paper/latex/` stores the actual LaTeX manuscript workspace.
- No unrelated experiment outputs, scratch code, or downloaded archives should accumulate directly under `paper/`.

### 4.2 `references/` contract

`paper/references/` is for paper-facing literature assets only.

Allowed contents include:

- `.bib` files
- exported citation metadata
- paper PDFs if needed for local reading
- concise reading notes / categorization notes

This directory should support the related-work buckets already identified:

- satellite / aerospace thermal control and engineering optimization
- LLM as heuristic advisor
- LLM as inline controller
- LLM as generator / co-designer
- fairness, attribution, and auditability in hybrid optimization

### 4.3 `latex/` contract

`paper/latex/` is the manuscript build root.

The initial clean structure is:

```text
paper/latex/
├── main_zh.tex
├── main_en.tex
├── refs.bib
├── sections/
│   ├── zh/
│   └── en/
├── figures/
├── tables/
├── build/
└── vendor/
```

Rules:

- `main_zh.tex` is the Chinese draft entry.
- `main_en.tex` is the English draft entry.
- `sections/zh/` and `sections/en/` keep parallel section files.
- `refs.bib` is the working bibliography source used by both drafts.
- `figures/` contains paper-facing copied/curated figures, not raw run directories.
- `tables/` contains authored tables or exported paper-facing tables.
- `build/` is the LaTeX output directory for `.aux`, `.bbl`, `.pdf`, etc.
- `vendor/` stores the AAAI official template files, unmodified except where the template explicitly expects manuscript editing.

No generated build byproducts should spill into `paper/latex/` root once the build rules are established.

## 5. AAAI Template Strategy

### 5.1 Why AAAI first

AAAI is used as the initial authoring template because it provides:

- a strong conference-paper structural prior,
- a familiar AI-facing layout for sections, figures, and references,
- a concrete LaTeX target that prevents endless formatting drift while drafting.

This choice is a **bootstrap choice** for writing discipline, not a final venue lock.

### 5.2 Template usage rules

The paper scaffold must use the **official AAAI template as the formatting example**.

Rules:

- Preserve vendor files in `paper/latex/vendor/` as close to upstream as practical.
- Keep our manuscript logic in our own `main_zh.tex`, `main_en.tex`, and section files.
- Avoid scattering manuscript content into copied vendor sample text files.
- If template-specific hacks are needed, isolate them and document them.

### 5.3 Chinese drafting under AAAI example

The Chinese draft is for internal writing and idea stabilization, so it may use a XeLaTeX-based Chinese-capable setup while preserving the same section structure as the AAAI-facing English draft.

That means:

- Chinese draft prioritizes authoring convenience and readable Chinese typesetting.
- English draft prioritizes eventual AAAI-style submission compatibility.
- The two drafts share structure, citation keys, figure/table naming, and section semantics.

## 6. Manuscript Structure Contract

The paper structure to be instantiated in both Chinese and English drafts is:

1. Introduction
2. Related Work
3. Problem Formulation: Satellite Thermal-Control Layout Optimization under Expensive Evaluation
4. Method: Fixed-Boundary Inline LLM Controller
5. Collapse Modes and Layered Recovery
6. Experiments
7. Analysis and Discussion
8. Limitations
9. Conclusion

This structure must remain synchronized across `main_zh.tex` and `main_en.tex`.

## 7. Initial Drafting Deliverables

The first writing phase must produce:

### 7.1 Chinese draft deliverables

- title candidates
- Chinese abstract
- Introduction draft
- Problem Formulation draft
- a section skeleton for the remaining sections

### 7.2 English draft deliverables

- aligned English title candidates
- aligned English abstract draft
- aligned Introduction draft skeleton
- aligned section placeholders matching the Chinese structure

The English draft may initially lag in prose completeness, but it must not lag in structure.

## 8. Reference Workflow

### 8.1 Single shared bibliography

Use one working bibliography file:

```text
paper/latex/refs.bib
```

Both Chinese and English drafts cite from the same key space.

### 8.2 Citation-key stability

Once a citation key is used in either language draft, avoid renaming it unless necessary. Stable keys reduce cross-language drift.

### 8.3 Reading assets vs manuscript assets

Rules:

- raw reading materials and note collections belong in `paper/references/`
- manuscript-facing curated bibliography belongs in `paper/latex/refs.bib`

This separation keeps literature discovery and manuscript citation hygiene from collapsing into one messy directory.

## 9. Build and Cleanliness Contract

### 9.1 Build tools

The installed toolchain is expected to support:

- `latexmk`
- `xelatex`
- `pdflatex`
- `lualatex`
- `biber`

### 9.2 Build outputs

LaTeX-generated outputs should be directed into:

```text
paper/latex/build/
```

The working source tree should remain readable and uncluttered.

### 9.3 Clean workspace expectation

Even though `paper/` is git-ignored, maintain internal cleanliness:

- no duplicated draft files like `main_final_v2_reallyfinal.tex`
- no random download archives left in `latex/`
- no mixed bibliography experiments once the main flow is chosen

## 10. Immediate Next-Step Plan

After this spec is approved, the next writing implementation step should do the following in order:

1. bootstrap `paper/latex/` with an AAAI-template-based layout,
2. create parallel `main_zh.tex` and `main_en.tex`,
3. create mirrored section files under `sections/zh/` and `sections/en/`,
4. create `refs.bib`,
5. place an initial Chinese abstract + introduction + problem formulation draft,
6. place aligned English title/abstract/introduction placeholders,
7. verify the LaTeX toolchain by compiling both entry files.

## 11. Acceptance Criteria

This design is considered correctly implemented only if all of the following become true in the next phase:

- `paper/references/` and `paper/latex/` remain the only top-level paper subdirectories.
- `paper/latex/` contains a clean manuscript scaffold rather than an ad hoc pile of files.
- the AAAI template is present as the formatting reference.
- Chinese and English drafts exist simultaneously and share the same section structure.
- one shared bibliography file serves both drafts.
- build artifacts are kept out of the source root.
- the paper narrative remains satellite-thermal-control-first rather than generic thermal-optimization-only.

## 12. Risks and Guardrails

### 12.1 Template lock-in risk

Using AAAI first could create accidental venue lock-in. Guardrail: treat AAAI as the initial formatting reference only; keep content modular and venue-neutral where possible.

### 12.2 Chinese/English drift risk

Parallel bilingual drafts can diverge. Guardrail: mirror section boundaries and keep one shared citation/figure/table naming system.

### 12.3 Ignored workspace risk

Because `paper/` is git-ignored, writing work could become hard to track. Guardrail: keep the structural contract and major writing decisions in versioned specs under `docs/superpowers/specs/`.
