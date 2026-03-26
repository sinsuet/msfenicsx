# TikZ Paper Figures Design

> Status: approved design draft for a global Codex skill. The skill is not repository-specific and should be installable under the user's global Codex skills directory.

## 1. Goal

Design a global skill named `tikz-paper-figures` that can read explicitly specified materials, extract high-level scientific structure, and generate polished TikZ figures for research papers.

The initial product goal is:

- accept explicit files or directories as the source material
- infer whether the requested figure should be an architecture diagram or a flow diagram
- summarize the planned figure before drawing
- generate TikZ and compile it locally
- render reviewable outputs and automatically repair obvious layout defects

The skill should prioritize computer-science-style paper figures, especially:

- system architecture diagrams
- training and inference loop diagrams
- algorithm and optimization flow diagrams
- high-level module relationship figures

## 2. User-Approved Defaults

The following defaults were approved during design:

- Input scope is explicit-only. The skill only reads files or directories explicitly provided by the user.
- If a directory is provided, the skill recursively reads relevant files under that directory.
- The file-reading policy is broad. The skill may read common text formats and may call additional tools or adapters for formats such as PDF, PPT/PPTX, and DOC/DOCX.
- Diagram type is inferred by default.
- Abstraction level defaults to high-level overview.
- The skill must send a figure summary for confirmation before drawing.
- If source materials disagree, documentation has priority over code.
- The default figure language is English paper style.
- If the user explicitly requests Chinese, the skill should generate Chinese labels.
- Default deliverables are `.tex`, `.pdf`, and `.png`.
- After first render, the skill should automatically repair obvious overlap, crowding, and routing issues before presenting the result.

## 3. Scope

### 3.1 Phase 1 In Scope

Phase 1 covers:

- material-driven architecture diagram generation
- material-driven flow diagram generation
- explicit file and directory ingestion
- English-first scientific styling
- optional Chinese rendering when requested
- local LaTeX compilation
- PNG preview generation
- automatic layout quality checks
- one to two rounds of automatic repair

### 3.2 Phase 1 Out of Scope

Phase 1 does not require:

- arbitrary low-level schematic drawing
- publication-perfect domain-specific notation for every subfield
- automatic full-repository scanning without explicit user input
- direct generation of every possible TikZ figure family
- full semantic reverse-engineering of large codebases without user curation
- interactive browser-only drawing workflows

## 4. Primary Usage Patterns

The skill is designed around explicit-material prompts such as:

- "Use these Markdown files to generate a paper-style flow diagram."
- "Read `README.md`, `docs/design.md`, and `src/pipeline.py`, then draw a high-level architecture figure."
- "Use these folders and rebuild the method figure in TikZ."
- "Based on these docs and code files, create a scientific architecture diagram in English."
- "Reference this image style, but derive the content from these specified materials."

The skill should treat these requests as its main trigger family rather than a secondary feature.

## 5. Source Material Policy

### 5.1 Explicit Scope Rule

The skill must only read:

- explicitly named files
- explicitly named directories and their recursive contents

It must not silently expand to unrelated repository areas.

### 5.2 Material Priority Rule

When multiple sources disagree:

1. narrative documents and formal docs
2. slide or PDF descriptions
3. code and configuration for structural validation

This means documentation drives semantic framing, while code acts as a structural check and gap-filler.

### 5.3 File Adapter Model

Material ingestion should be adapter-based.

Expected adapters:

- plain text adapter for `md`, `txt`, `rst`, `json`, `yaml`, `yml`, `toml`
- code adapter for `py`, `tex`, and other readable source files
- PDF adapter using PDF-oriented extraction and rendering workflows
- slide adapter for `ppt` and `pptx`
- document adapter for `doc` and `docx`

Adapter design rule:

- prefer deterministic local extraction first
- preserve file provenance for every extracted claim
- fail clearly if a requested file cannot be meaningfully read

## 6. Figure Intent Classification

Before drawing, the skill should classify the requested figure into a supported intent.

Phase 1 intents:

- `architecture`
- `flow`

The classifier should inspect:

- sequencing language such as "then", "next", "validate", "loop", "stage"
- module and dependency language such as "component", "service", "encoder", "critic", "buffer"
- explicit training or optimization loop semantics
- source structure hints from headings, function names, section titles, and repeated terminology

If the intent is ambiguous, the summary sent to the user should state the chosen intent and allow correction before drawing.

## 7. Confirmation Gate

The skill must pause before drawing and send a compact figure summary for user confirmation.

The summary should include:

- inferred figure type
- abstraction level
- primary source files used
- six to ten main blocks or stages
- the most important connections or flow directions
- selected visual template family

Drawing starts only after user confirmation.

## 8. Core Architecture

The skill should use a semantic intermediate representation rather than direct prompt-to-TikZ generation.

### 8.1 Pipeline

1. Collect explicitly specified sources.
2. Run adapter-based extraction.
3. Build a normalized source digest.
4. Infer figure intent.
5. Build a figure summary for confirmation.
6. After confirmation, generate a structured figure specification.
7. Run layout planning against a template family.
8. Emit TikZ.
9. Compile locally.
10. Render PNG preview.
11. Run quality checks.
12. Apply automatic repair if needed.
13. Return final artifacts.

### 8.2 Required Intermediate Artifacts

#### `source_digest.json`

Purpose:

- record what was read
- preserve provenance
- justify figure intent and selected content

Suggested contents:

- source list
- adapter used per source
- extracted entities
- extracted relations
- ignored material notes
- document-priority resolution notes
- inferred figure intent

#### `figure.spec.json`

Purpose:

- store the semantic representation used to generate the final figure

Suggested contents:

- figure type
- language mode
- template family
- canvas profile
- groups or panels
- nodes
- edges
- labels and math content
- layout constraints
- style options

## 9. Template Families

Phase 1 should define three template families, but only the first one must be fully productionized in the first milestone.

### 9.1 `paper-block-feedback-v1`

Primary use:

- architecture figures
- training loops
- actor-critic style diagrams
- optimization or evaluation pipelines with feedback arcs

Visual language:

- soft panel backgrounds
- rounded boxes
- strong left-to-right primary flow
- optional long feedback arc above the figure
- dashed highlight modules for auxiliary or proposed blocks
- clean legend support

Primary visual references:

- [Observer/Estimator](https://texample.net/observer-estimator/)
- [Knowledge Base Exchange framework](https://texample.net/kb-exchange/)
- [System Combination](https://texample.net/system-combination/)

### 9.2 `paper-flow-maintainable-v1`

Primary use:

- methods flowcharts
- experimental workflows
- processing pipelines

Visual language:

- orthogonal routing
- stable row or column alignment
- restrained decision styling
- black-and-white legibility with optional accent colors

Primary visual references:

- [Flexible flow chart](https://texample.net/flexible-flow-chart/)
- [Data flow diagram](https://texample.net/data-flow-diagram/)

### 9.3 `paper-layered-network-v1`

Primary use:

- repeated-layer structures
- encoder-decoder style figures
- head and branch diagrams

Visual language:

- layered alignment
- repeated node patterns
- constrained inter-layer links

Primary visual reference:

- [Neural network](https://texample.net/neural-network/)

## 10. Layout Strategy

The skill should not allow the model to freely invent raw coordinates for the final figure.

Preferred layout model:

- semantic blocks first
- template-driven lane and grid planning second
- final TikZ coordinates generated from planned layout

Layout rules should include:

- left-to-right primary narrative unless the user asks otherwise
- bounded panel padding
- fixed minimum node spacing
- routed edges via preferred anchors
- orthogonal routing by default for flow diagrams
- curved routing only for important feedback or high-level semantic loops
- lane allocation for parallel edges where useful

The model may influence:

- grouping
- ordering
- semantic emphasis
- choice of optional feedback arcs

The model should not directly own:

- unrestricted coordinates for every node
- unrestricted edge geometry in the final pass

## 11. Language and LaTeX Engine Policy

Language behavior:

- default to English paper-style labels
- switch to Chinese labels only on explicit user request

Engine behavior:

- prefer `pdflatex` for English-only figures when the selected template does not require XeLaTeX-specific font handling
- prefer `xelatex` for Chinese output or mixed-language output

Compilation should use local tooling available in the user's environment.

Observed local tool availability during design:

- `latexmk`
- `pdflatex`
- `xelatex`
- `pdftoppm`
- `dvisvgm`

## 12. Deliverables

Default output artifacts:

- `figure.tex`
- `figure.pdf`
- `figure.png`

Internal or optional debugging artifacts:

- `source_digest.json`
- `figure.spec.json`
- `figure.qa.json`
- intermediate logs

The default user-facing return does not need to expose every internal artifact, but the skill should retain them when useful for debugging and repair.

## 13. Quality Assurance

Quality assurance is a core product feature, not a postscript.

### 13.1 Geometric Checks

The QA pass should detect at minimum:

- node box overlap
- label overlap
- text colliding with edges
- edges passing through boxes
- excessive edge crossings
- out-of-bounds elements
- panel crowding
- insufficient spacing between parallel routes

### 13.2 Compilation Checks

The QA pass should capture:

- LaTeX compilation failure
- undefined control sequences
- missing package or font issues
- overfull or underfull box warnings when they indicate visible layout defects

### 13.3 Render Checks

The QA pass should inspect rendered outputs for:

- unreadably small labels
- crowded corners
- visually tangled routing
- poor balance between left and right regions
- legend collisions
- panel hierarchy that is too weak to read

## 14. Automatic Repair Policy

If the first render fails QA, the skill should automatically repair before returning results.

Allowed automatic repair actions:

- increase local spacing
- reorder nodes within a layer
- change edge anchors
- reroute through a different lane
- split long labels
- enlarge panel padding
- simplify secondary edges if clutter is excessive

Repair sequence:

1. deterministic rule-based repair
2. regenerate and re-check
3. if still failing, one additional model-guided repair pass that edits semantic or layout constraints rather than hand-writing arbitrary coordinates

Default limit:

- one to two automatic repair rounds

## 15. Global Installation Design

This skill is intentionally global and not tied to the current repository.

Default installation target:

- `C:/Users/hymn/.codex/skills/tikz-paper-figures`

If a mirrored WSL Codex skill environment is also used, a corresponding Linux-side copy may be installed under:

- `/home/hymn/.codex/skills/tikz-paper-figures`

The skill should not depend on repository-local assets to function.

## 16. Proposed Skill Directory Layout

```text
tikz-paper-figures/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── scripts/
│   ├── build_figure.py
│   ├── collect_sources.py
│   ├── extract_materials.py
│   ├── infer_intent.py
│   ├── summarize_figure.py
│   ├── plan_layout.py
│   ├── emit_tikz.py
│   ├── compile_figure.py
│   ├── render_preview.py
│   ├── check_geometry.py
│   ├── check_rendered.py
│   └── repair_spec.py
├── references/
│   ├── spec-schema.md
│   ├── template-catalog.md
│   ├── layout-rules.md
│   └── texample-sources.md
└── assets/
    ├── templates/
    │   └── standalone_figure.tex
    ├── styles/
    │   ├── paper-block-feedback-v1.tex
    │   ├── paper-flow-maintainable-v1.tex
    │   └── paper-layered-network-v1.tex
    └── examples/
```

## 17. First Milestone

The first implementation milestone should intentionally stay narrow.

Required milestone behavior:

- install the global skill skeleton
- support explicit file and directory input
- support broad material ingestion with clear failure messages
- infer `architecture` versus `flow`
- send a figure summary for confirmation
- fully implement `paper-block-feedback-v1`
- generate `.tex`, `.pdf`, and `.png`
- run QA and auto-repair

Deferred to later milestones:

- fully productized `paper-flow-maintainable-v1`
- fully productized `paper-layered-network-v1`
- wider domain-specific template catalog
- deeper codebase graph extraction

## 18. Design Rationale

This design intentionally avoids direct prompt-to-TikZ generation as the main method.

Reasons:

- raw prompt-to-TikZ is fast but unstable
- material-driven figures need provenance and controllability
- scientific figures benefit from reusable style systems
- layout defects are easier to repair when semantics and coordinates are separated
- explicit figure summaries reduce wasted drawing cycles

The design therefore combines:

- document-driven semantic extraction
- template-constrained layout
- real local compilation
- rendered QA
- automatic repair

## 19. Completion Gate For Moving To Implementation

The design is ready for implementation planning once:

- the user confirms this written spec
- the global install target is accepted as the default location unless later overridden
- the first milestone is accepted as architecture and flow support with only `paper-block-feedback-v1` fully implemented

