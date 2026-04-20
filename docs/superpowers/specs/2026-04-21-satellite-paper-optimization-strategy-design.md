# Satellite Paper Optimization Strategy — Design

- **Date**: 2026-04-21
- **Scope**: define the post-bootstrap writing strategy for the satellite thermal-control paper, including the stable paper spine, chapter responsibilities, claim-strength policy, literature-calibration workflow, and chapter-by-chapter optimization process.
- **Applies to**: `paper/latex/sections/zh/`, `paper/latex/sections/en/`, `paper/references/`, `docs/superpowers/specs/`.
- **Depends on**: the completed AAAI/双语 bootstrap scaffold defined in `docs/superpowers/plans/2026-04-20-satellite-paper-aaai26-bootstrap.md` and the paper-writing workspace contract defined in `docs/superpowers/specs/2026-04-20-satellite-paper-writing-aaai-design.md`.

## 1. Motivation

The bootstrap phase established a bilingual LaTeX workspace, but the manuscript itself is still only a rough scaffold. The current bottleneck is no longer formatting. It is narrative control:

1. the innovation claim is not yet sharp enough,
2. the background and motivation are not yet organized around the right scientific problem,
3. the method section risks collapsing into implementation detail,
4. the related-work section has not yet been turned into a precise novelty boundary, and
5. the experimental story is still incomplete and will expand substantially later.

This design defines how to optimize the paper *before* the full experiment matrix is finished. The immediate goal is to stabilize the writing spine so that later additions—more baselines, more models, more seeds, and more ablations—can strengthen the manuscript without forcing a wholesale rewrite.

## 2. Non-Goals

This phase does **not** attempt to:

- finalize the full experiment section,
- freeze the final title or venue-facing wording,
- perform a complete literature survey before any writing work continues,
- rewrite multiple sections in one undifferentiated pass,
- turn the paper into a pure application report or a pure decontextualized methods paper.

## 3. Paper Type And Stable Framing

The paper should be framed as:

**an application-driven problem paper, where satellite thermal-control layout optimization provides the high-cost constrained setting, while the central scientific contribution is the analysis and structured recovery of inline LLM control collapse.**

This is intentionally neither of the following:

- a pure application paper whose main message is “the method worked on a satellite problem”, or
- a pure generic methods paper detached from a realistic engineering setting.

The stable framing responsibilities are:

- **application setting** supplies realism, stakes, and difficulty,
- **method contribution** supplies publishable novelty,
- **evidence chain** supplies scientific credibility.

## 4. Core Paper Spine

### 4.1 One-sentence claim

The stable top-level claim for the current manuscript should be:

**Inline LLM control in expensive constrained black-box optimization is not merely a performance question; it is a stability problem with identifiable collapse modes and a recoverable intervention structure.**

This claim exists to keep the paper centered on mechanism rather than headline performance.

### 4.2 First reviewer memory

The first thing reviewers should remember is:

**the paper does not merely report that an inline LLM controller sometimes helps; it systematizes collapse taxonomy and layered recovery.**

Secondary memories may include:

- the attribution setting is made more auditable by fixed boundaries and shared optimization machinery,
- the satellite thermal-control case is a demanding engineering setting rather than decorative packaging.

### 4.3 Primary contribution structure

The manuscript should currently organize around three main contributions:

1. **Problem reframing**: reframe inline LLM control in expensive constrained optimization as a stability-and-failure-mechanism problem, not just a “can it improve performance?” question.
2. **Collapse taxonomy**: define a structured taxonomy of collapse modes for LLM-controlled black-box optimization.
3. **Layered recovery framework**: define a layered recovery framework organized by collapse type and intervention level, rather than by ad hoc patch accumulation.

The attribution/fairness setup should remain important, but for now it should support these three contributions rather than become an independent over-claimed contribution.

## 5. Claim-Strength Policy

The paper must explicitly use a **two-layer claim structure**.

### 5.1 Layer A: currently supportable claims

These are the claims the manuscript should already be willing to state clearly:

- inline LLM control exhibits recognizable collapse phenomena,
- these phenomena can be organized as a taxonomy rather than treated as random noise,
- layered recovery can be presented as a structured intervention framework,
- fixed-boundary and budget-matched settings improve attribution clarity.

### 5.2 Layer B: future-strengthened claims

These are stronger claims that may become central later, but should currently remain clearly bounded:

- superiority against a wider set of baselines and controller families,
- robustness across more models, more seeds, and more scenarios,
- systematic final-performance gains rather than only mechanism-level recovery,
- stronger generalization across broader families of LLM-controlled black-box optimization.

The immediate writing rule is:

**write Layer A as validated, write Layer B as future strengthening territory rather than current proof.**

## 6. Evidence Priority

The paper should organize evidence in the following order:

1. **mechanism evidence first** — collapse exists, can be characterized, and can be intervened upon,
2. **auditable attribution evidence second** — the setup makes controller influence more legible,
3. **performance evidence third** — useful, but not the primary narrative backbone at the current stage.

This ordering is important because the current experiment set is still partial. The paper should not be architected around a performance-first story that the present evidence cannot yet fully carry.

## 7. Chapter Responsibilities

### 7.1 Introduction

The introduction should:

- establish the setting of expensive constrained optimization with inline LLM control,
- foreground collapse as the central problem,
- position taxonomy plus layered recovery as the response,
- summarize contributions without sinking into implementation detail.

It should **not** become a long satellite-domain tutorial or a mini related-work section.

### 7.2 Related Work

Related work should primarily:

- identify the gap around collapse/recovery analysis for inline controllers,
- distinguish this work from LLM-as-generator, LLM-as-advisor, and loosely specified optimization agents,
- provide only the minimum background needed to justify the novelty boundary.

Its main function is **gap construction and boundary-setting**, not broad background accumulation.

### 7.3 Problem Formulation

Problem formulation should define:

- the satellite thermal-control layout optimization setting,
- the expensive constrained multi-objective nature of the task,
- the fixed optimization boundary,
- the insertion point and scope of inline controller decisions.

Its role is to establish the fairness and interpretability envelope for the later mechanism claims.

### 7.4 Method

Method should be organized around the following logic:

1. define the fixed-boundary inline-control setup,
2. explain why collapse—not just ordinary variance—is the central failure mode,
3. present the collapse taxonomy,
4. present the layered recovery framework motivated by that taxonomy.

The core internal formula is:

**fixed boundary → inline control induces structured collapse risk → collapse can be taxonomized → taxonomy motivates layered recovery**

Method must **not** read like an implementation manual.

### 7.5 Experiments

Experiments should answer:

- whether collapse phenomena actually occur,
- whether the taxonomy explains observed degradation,
- whether layered recovery helps in mechanism-relevant ways,
- what the current evidence supports now versus what later experiments will strengthen.

This section is not currently responsible for proving the final strongest comparative story.

### 7.6 Analysis And Discussion

This section should:

- connect mechanism evidence, attribution clarity, and application implications,
- carefully discuss generalization boundaries,
- cautiously extend the framing beyond the immediate task.

Discussion is where broader generalization claims may be introduced carefully; earlier sections should remain tighter.

## 8. Method-Narrative Guardrails

To avoid the paper degrading into a patch report, the method narrative must obey these rules:

1. **Do not lead with implementation detail.**
2. **Do not present recovery before collapse.**
3. **Do not let taxonomy become a flat list of observed symptoms.**
4. **Do not describe layered recovery as a sequence of pragmatic fixes.**
5. **Do describe each recovery layer by target failure, intervention location, and intended restored capability.**

The desired identity is:

**layered recovery is a framework organized by collapse structure, not an anecdotal stack of engineering patches.**

## 9. Literature Strategy

The literature workflow should be deliberately staged.

### 9.1 Immediate lightweight calibration

Before rewriting major sections, perform a lightweight calibration pass that answers:

- what buckets the key related work should fall into,
- what existing paper types the manuscript most risks resembling,
- which novelty phrases are likely too strong,
- which boundaries must be explicitly drawn.

This pass is a calibration tool, not a full exhaustive survey.

### 9.2 Later deep chapter-specific retrieval

After the spine is fixed, deeper literature work should happen **per chapter**, especially for:

- related work,
- introduction support citations,
- discussion-side generalization claims.

This staged approach prevents literature search from delaying spine stabilization while still ensuring the final claims are properly calibrated.

## 10. Execution Strategy

The writing process should be split into two scales.

### 10.1 Large-plan scale

First stabilize the global manuscript logic:

- one-sentence claim,
- contribution structure,
- two-layer claim policy,
- chapter responsibilities,
- method narrative formula,
- explicit “do not overclaim” boundaries.

### 10.2 Small-plan scale

Then optimize the paper one section at a time.

The recommended order is:

1. Introduction
2. Method
3. Related Work
4. Problem Formulation
5. Experiments
6. Analysis and Discussion
7. Conclusion / abstract refinement

Each chapter-specific optimization plan should define:

- the section’s single primary job,
- what must be deleted or weakened,
- what must be added,
- what claims must remain provisional,
- how the section hands off to adjacent sections.

The explicit collaboration rule is:

**do not ask for multi-section simultaneous rewriting when the goal is quality narrative optimization; use a single-chapter small plan each time.**

## 11. Evidence Growth Policy

The current experiment set is only a starting subset. The manuscript must therefore be designed to absorb later evidence growth without narrative collapse.

The paper should be prepared to expand later with:

- more optimization methods,
- more controller/model variants,
- more seeds,
- more ablations,
- broader comparative evidence.

Therefore:

- the current draft should avoid claiming final comparative closure,
- the structure should make it easy to enlarge the experiment section later,
- introduction, abstract, and conclusion wording should be upgradable rather than disposable.

## 12. Anti-Drift Rules

The manuscript must not drift into any of the following forms:

1. **performance-first report** — where mechanism becomes secondary,
2. **engineering patch log** — where recovery is just a list of fixes,
3. **thin novelty packaging** — where the application setting carries more weight than the actual method contribution,
4. **implementation-detail overload** — where the reader loses the paper’s scientific center.

The most important anti-drift rule is:

**do not let the paper read like an engineering repair diary.**

## 13. Immediate Deliverable From This Design

The immediate deliverable of this design is **not** a full rewritten paper.

It is a stable optimization-control document for the manuscript that provides:

- the paper spine,
- the chapter logic,
- the claim-strength policy,
- the literature-calibration workflow,
- the chapter-by-chapter optimization order.

Once this design is accepted, the next step is to write a detailed implementation plan and then execute the chapter-level optimization sequence.

## 14. Acceptance Criteria

This design is successful if, after approval:

1. the paper’s central scientific story no longer feels ambiguous,
2. later section work can proceed one chapter at a time without losing the main line,
3. incomplete experiments no longer force premature overclaiming,
4. the method section has a protected narrative identity,
5. later evidence additions can strengthen the paper without restructuring it from scratch.
