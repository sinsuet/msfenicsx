# TikZ Paper Figures Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and globally install a `tikz-paper-figures` Codex skill that reads explicitly specified materials, infers whether the figure should be an architecture or flow diagram, sends a figure summary for confirmation, and then generates `.tex`, `.pdf`, and `.png` outputs with automatic layout QA and repair.

**Architecture:** The skill is implemented as a global skill under `C:/Users/hymn/.codex/skills/tikz-paper-figures` with an adapter-driven ingestion pipeline, a semantic `source_digest -> figure.spec` intermediate layer, a template-constrained TikZ emitter, and a compile-render-QA-repair loop. Phase 1 fully productizes `paper-block-feedback-v1` and supports both architecture and flow requests by sharing the same core semantic pipeline while deferring a fully separate flow template family to a later phase.

**Tech Stack:** Python 3.12, pytest, pathlib, json, PyYAML, `pypdf`, `python-pptx`, `python-docx`, `latexmk`, `pdflatex`, `xelatex`, `pdftoppm`, Codex skill validation scripts.

---

## File Structure

### Global Skill Root

- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/SKILL.md`
  Main skill instructions and trigger description.
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/agents/openai.yaml`
  UI metadata for the skill.
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/__init__.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/build_figure.py`
  End-to-end entrypoint from explicit materials to final artifacts.
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/collect_sources.py`
  Explicit file and recursive directory collection.
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/extract_materials.py`
  Adapter orchestration and `source_digest` assembly.
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/infer_intent.py`
  `architecture` versus `flow` classification.
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/summarize_figure.py`
  User-facing pre-draw summary generation.
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/plan_layout.py`
  Template-driven block and lane placement.
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/emit_tikz.py`
  `figure.spec` to TikZ emission.
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/compile_figure.py`
  `latexmk` orchestration and engine selection.
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/render_preview.py`
  PNG rendering from compiled output.
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/check_geometry.py`
  Geometric overlap and routing checks.
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/check_rendered.py`
  Render-level QA checks and report generation.
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/repair_spec.py`
  Rule-based repair and one model-guided repair handoff point.

### Adapter Layer

- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/adapters/__init__.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/adapters/base.py`
  Common adapter contract and extraction result schema.
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/adapters/text_adapter.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/adapters/code_adapter.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/adapters/pdf_adapter.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/adapters/pptx_adapter.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/adapters/docx_adapter.py`

### References And Assets

- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/references/spec-schema.md`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/references/template-catalog.md`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/references/layout-rules.md`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/references/texample-sources.md`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/assets/templates/standalone_figure.tex`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/assets/styles/paper-block-feedback-v1.tex`
- Create later: `C:/Users/hymn/.codex/skills/tikz-paper-figures/assets/styles/paper-flow-maintainable-v1.tex`
- Create later: `C:/Users/hymn/.codex/skills/tikz-paper-figures/assets/styles/paper-layered-network-v1.tex`

### Tests And Fixtures

- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/test_skill_structure.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/test_collect_sources.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/test_extract_materials.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/test_infer_intent.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/test_summarize_figure.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/test_emit_tikz.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/test_compile_pipeline.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/test_quality_checks.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/fixtures/architecture_project/README.md`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/fixtures/architecture_project/docs/overview.md`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/fixtures/architecture_project/src/pipeline.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/fixtures/flow_project/docs/method.md`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/fixtures/chinese_project/docs/overview.md`

### Design References

- Inspect: `/home/hymn/msfenicsx/docs/superpowers/specs/2026-03-26-tikz-paper-figures-design.md`
  Approved design specification.

## Task 1: Bootstrap The Global Skill Skeleton

**Files:**
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/SKILL.md`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/agents/openai.yaml`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/__init__.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/test_skill_structure.py`

- [ ] **Step 1: Run the official validator first to verify the skill is missing**

Run:

```bash
python C:/Users/hymn/.codex/skills/.system/skill-creator/scripts/quick_validate.py C:/Users/hymn/.codex/skills/tikz-paper-figures
```

Expected: FAIL because the skill has not been initialized yet.

- [ ] **Step 2: Initialize the skill skeleton with the official helper**

Run:

```bash
python C:/Users/hymn/.codex/skills/.system/skill-creator/scripts/init_skill.py tikz-paper-figures --path C:/Users/hymn/.codex/skills --resources scripts,references,assets
```

Expected: the folder `C:/Users/hymn/.codex/skills/tikz-paper-figures` is created with base skill files.

- [ ] **Step 3: Add the tests directory, package marker, and failing structure test**

Create:

- `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/`
- `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/__init__.py`

and write:

```python
from pathlib import Path


def test_skill_has_required_top_level_files():
    root = Path("C:/Users/hymn/.codex/skills/tikz-paper-figures")
    assert (root / "SKILL.md").exists()
    assert (root / "scripts").is_dir()
    metadata = (root / "agents" / "openai.yaml").read_text(encoding="utf-8")
    assert "$tikz-paper-figures" in metadata
```

- [ ] **Step 4: Run the structure test to verify it fails on incomplete metadata**

Run: `cd C:/Users/hymn/.codex/skills/tikz-paper-figures && pytest tests/test_skill_structure.py -v`
Expected: FAIL because `agents/openai.yaml` does not yet contain the finalized `$tikz-paper-figures` prompt metadata.

- [ ] **Step 5: Generate `agents/openai.yaml` with explicit UI metadata**

Run:

```bash
python C:/Users/hymn/.codex/skills/.system/skill-creator/scripts/generate_openai_yaml.py C:/Users/hymn/.codex/skills/tikz-paper-figures --interface display_name="TikZ Paper Figures" --interface short_description="Generate paper-style TikZ figures" --interface default_prompt="Use $tikz-paper-figures to generate a paper-style TikZ figure from explicitly specified materials."
```

Expected: `agents/openai.yaml` exists and references `$tikz-paper-figures` in `default_prompt`.

- [ ] **Step 6: Run structure validation**

Run:

```bash
cd C:/Users/hymn/.codex/skills/tikz-paper-figures
pytest tests/test_skill_structure.py -v
python C:/Users/hymn/.codex/skills/.system/skill-creator/scripts/quick_validate.py C:/Users/hymn/.codex/skills/tikz-paper-figures
```

Expected: both commands PASS.

## Task 2: Implement Explicit Source Collection

**Files:**
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/collect_sources.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/test_collect_sources.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/fixtures/architecture_project/README.md`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/fixtures/architecture_project/docs/overview.md`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/fixtures/architecture_project/src/pipeline.py`

- [ ] **Step 1: Write failing collection tests**

Cover these cases:

1. explicit file paths are preserved in order
2. explicit directories are scanned recursively
3. unrelated directories are not added automatically
4. broad readable extensions are kept while binary files are ignored

- [ ] **Step 2: Run the collection tests to verify they fail**

Run: `cd C:/Users/hymn/.codex/skills/tikz-paper-figures && pytest tests/test_collect_sources.py -v`
Expected: FAIL because `collect_sources.py` does not exist yet.

- [ ] **Step 3: Implement explicit-only source collection**

Implement:

- recursive directory walking
- stable deterministic ordering
- extension filtering for common readable formats
- clear error messages for missing paths

- [ ] **Step 4: Add a helper that records source provenance**

Expose a result structure that includes:

- normalized path
- source kind: file or directory expansion
- detected extension
- collection order

- [ ] **Step 5: Run the collection tests again**

Run: `cd C:/Users/hymn/.codex/skills/tikz-paper-figures && pytest tests/test_collect_sources.py -v`
Expected: PASS.

## Task 3: Implement Adapter-Based Material Extraction And Source Digest Assembly

**Files:**
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/extract_materials.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/adapters/base.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/adapters/text_adapter.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/adapters/code_adapter.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/adapters/pdf_adapter.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/adapters/pptx_adapter.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/adapters/docx_adapter.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/test_extract_materials.py`

- [ ] **Step 1: Write failing extraction tests**

Cover these behaviors:

1. Markdown and plain text are classified as documentation
2. code files are classified as code
3. document-derived evidence outranks code-derived evidence
4. unsupported or dependency-blocked formats fail with readable messages

- [ ] **Step 2: Run the extraction tests to verify they fail**

Run: `cd C:/Users/hymn/.codex/skills/tikz-paper-figures && pytest tests/test_extract_materials.py -v`
Expected: FAIL because the adapter registry is not implemented.

- [ ] **Step 3: Implement the base adapter contract**

Define a common extraction result that includes:

- source path
- adapter name
- material class
- extracted text or structured hints
- provenance snippets
- confidence notes

- [ ] **Step 4: Implement the text and code adapters**

Support at least:

- `md`
- `txt`
- `rst`
- `json`
- `yaml`
- `yml`
- `toml`
- `py`
- `tex`

- [ ] **Step 5: Implement the PDF, PPTX, and DOCX adapters**

Use:

- `pypdf` for PDF text extraction
- `python-pptx` for slide text extraction
- `python-docx` for DOCX extraction

If a dependency is unavailable, return a precise message naming the missing package and the blocked file.

- [ ] **Step 6: Assemble `source_digest` with document-priority conflict resolution**

Implement digest fields for:

- all sources read
- extracted entities
- extracted relations
- ignored material notes
- document-over-code resolution notes

- [ ] **Step 7: Run extraction tests again**

Run: `cd C:/Users/hymn/.codex/skills/tikz-paper-figures && pytest tests/test_extract_materials.py -v`
Expected: PASS.

## Task 4: Implement Figure Intent Inference And Pre-Draw Summary

**Files:**
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/infer_intent.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/summarize_figure.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/test_infer_intent.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/test_summarize_figure.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/fixtures/flow_project/docs/method.md`

- [ ] **Step 1: Write failing intent and summary tests**

Cover these behaviors:

1. a staged method document maps to `flow`
2. a module-centric design document maps to `architecture`
3. the summary includes figure type, abstraction level, primary sources, main blocks, main edges, and template family

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
cd C:/Users/hymn/.codex/skills/tikz-paper-figures
pytest tests/test_infer_intent.py -v
pytest tests/test_summarize_figure.py -v
```

Expected: FAIL because both scripts are missing.

- [ ] **Step 3: Implement `architecture` versus `flow` inference**

Use weighted cues from:

- headings
- repeated terms
- sequencing verbs
- module nouns
- loop and validation language

- [ ] **Step 4: Implement the confirmation summary renderer**

The summary output must include:

- inferred figure type
- abstraction level `high-level overview`
- six to ten blocks or stages
- high-level connections
- selected template family

- [ ] **Step 5: Re-run the tests**

Run:

```bash
cd C:/Users/hymn/.codex/skills/tikz-paper-figures
pytest tests/test_infer_intent.py -v
pytest tests/test_summarize_figure.py -v
```

Expected: PASS.

## Task 5: Implement Figure Spec Generation And The `paper-block-feedback-v1` Style System

**Files:**
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/references/spec-schema.md`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/references/template-catalog.md`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/references/layout-rules.md`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/references/texample-sources.md`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/assets/templates/standalone_figure.tex`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/assets/styles/paper-block-feedback-v1.tex`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/plan_layout.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/emit_tikz.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/test_emit_tikz.py`

- [ ] **Step 1: Write the failing TikZ emission test**

Cover these behaviors:

1. a simple architecture spec emits panel styles and rounded boxes
2. emitted TikZ references `paper-block-feedback-v1`
3. feedback edges can be emitted as top arcs when requested
4. flow intent can still emit a simplified orthogonal layout through the same style family in Phase 1

- [ ] **Step 2: Run the emission test to verify it fails**

Run: `cd C:/Users/hymn/.codex/skills/tikz-paper-figures && pytest tests/test_emit_tikz.py -v`
Expected: FAIL because no emitter or style assets exist yet.

- [ ] **Step 3: Write the style and template assets**

Implement:

- panel styles
- node styles
- auxiliary dashed module styles
- legend helpers
- language-neutral math-safe label helpers

- [ ] **Step 4: Define the `figure.spec` schema and layout rules**

The schema should cover:

- figure type
- language mode
- template family
- canvas profile
- panels
- nodes
- edges
- layout constraints

- [ ] **Step 5: Implement layout planning and TikZ emission**

Implement:

- left-to-right block placement
- panel padding
- anchor-based routing
- optional feedback arc placement
- simplified orthogonal mode for flow requests in Phase 1

- [ ] **Step 6: Re-run the emission test**

Run: `cd C:/Users/hymn/.codex/skills/tikz-paper-figures && pytest tests/test_emit_tikz.py -v`
Expected: PASS.

## Task 6: Implement Compilation, Language Switching, And PNG Preview Rendering

**Files:**
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/compile_figure.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/render_preview.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/test_compile_pipeline.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/fixtures/chinese_project/docs/overview.md`

- [ ] **Step 1: Write the failing compile pipeline tests**

Cover these behaviors:

1. English-only figures choose `pdflatex`
2. Chinese-requested figures choose `xelatex`
3. successful compilation produces `figure.pdf`
4. preview rendering produces `figure.png`

- [ ] **Step 2: Run the compile pipeline tests to verify they fail**

Run: `cd C:/Users/hymn/.codex/skills/tikz-paper-figures && pytest tests/test_compile_pipeline.py -v`
Expected: FAIL because compile and render helpers do not exist.

- [ ] **Step 3: Implement engine selection and `latexmk` invocation**

Implement:

- `pdflatex` for English-only output
- `xelatex` for Chinese or mixed-language output
- build logs captured to a predictable QA-friendly location

- [ ] **Step 4: Implement preview rendering with `pdftoppm`**

Render the first page of `figure.pdf` to `figure.png` with deterministic naming.

- [ ] **Step 5: Re-run the compile pipeline tests**

Run: `cd C:/Users/hymn/.codex/skills/tikz-paper-figures && pytest tests/test_compile_pipeline.py -v`
Expected: PASS.

## Task 7: Implement Layout QA And Automatic Repair

**Files:**
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/check_geometry.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/check_rendered.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/repair_spec.py`
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/test_quality_checks.py`

- [ ] **Step 1: Write the failing QA and repair tests**

Cover these behaviors:

1. overlapping nodes are detected
2. out-of-bounds elements are detected
3. an obviously crowded spec triggers a repair suggestion
4. one repair pass reduces the reported defect count

- [ ] **Step 2: Run the QA tests to verify they fail**

Run: `cd C:/Users/hymn/.codex/skills/tikz-paper-figures && pytest tests/test_quality_checks.py -v`
Expected: FAIL because the QA scripts do not exist.

- [ ] **Step 3: Implement deterministic geometry checks**

Implement checks for:

- box overlap
- label overlap
- edge-through-box cases
- out-of-bounds placement
- insufficient inter-lane spacing

- [ ] **Step 4: Implement render-level QA reporting**

At minimum record:

- compile warnings that are likely visible
- crowded-corner heuristics
- legend collision flags
- tangled-routing flags

- [ ] **Step 5: Implement rule-based repair**

Allow repair actions to:

- increase spacing
- change anchors
- reorder same-layer nodes
- enlarge panel padding
- split long labels

- [ ] **Step 6: Re-run QA tests**

Run: `cd C:/Users/hymn/.codex/skills/tikz-paper-figures && pytest tests/test_quality_checks.py -v`
Expected: PASS.

## Task 8: Wire The End-To-End Entry Script And Finalize The Skill Instructions

**Files:**
- Create: `C:/Users/hymn/.codex/skills/tikz-paper-figures/scripts/build_figure.py`
- Modify: `C:/Users/hymn/.codex/skills/tikz-paper-figures/SKILL.md`
- Modify: `C:/Users/hymn/.codex/skills/tikz-paper-figures/agents/openai.yaml`

- [ ] **Step 1: Write the failing end-to-end smoke expectation**

Define the expected CLI-style flow:

1. collect explicit inputs
2. extract materials
3. infer intent
4. produce summary
5. after confirmation, emit TikZ
6. compile and render
7. run QA and repair

- [ ] **Step 2: Implement `build_figure.py`**

Wire all earlier modules into a single end-to-end entrypoint that can be called from the skill.

- [ ] **Step 3: Rewrite `SKILL.md` to reflect the approved product behavior**

The skill instructions must explicitly state:

- explicit-only input policy
- recursive directory handling
- document-priority conflict policy
- summary-before-draw gate
- default English output and optional Chinese
- default artifacts `.tex`, `.pdf`, `.png`

- [ ] **Step 4: Refresh `agents/openai.yaml` if the UI text drifted**

Regenerate or patch the metadata so it matches the final skill behavior.

- [ ] **Step 5: Validate the skill definition**

Run:

```bash
python C:/Users/hymn/.codex/skills/.system/skill-creator/scripts/quick_validate.py C:/Users/hymn/.codex/skills/tikz-paper-figures
```

Expected: PASS.

## Task 9: Run End-To-End Smoke Tests And Mirror If Needed

**Files:**
- Inspect: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/fixtures/architecture_project/`
- Inspect: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/fixtures/flow_project/`
- Inspect: `C:/Users/hymn/.codex/skills/tikz-paper-figures/tests/fixtures/chinese_project/`

- [ ] **Step 1: Run the full local test suite**

Run:

```bash
cd C:/Users/hymn/.codex/skills/tikz-paper-figures
pytest tests -v
```

Expected: PASS.

- [ ] **Step 2: Run an architecture-figure smoke build**

Run:

```bash
cd C:/Users/hymn/.codex/skills/tikz-paper-figures
python scripts/build_figure.py --input tests/fixtures/architecture_project/README.md --input tests/fixtures/architecture_project/docs --input tests/fixtures/architecture_project/src/pipeline.py --confirm-summary yes --output-dir tmp/architecture_smoke
```

Expected:

- `tmp/architecture_smoke/figure.tex`
- `tmp/architecture_smoke/figure.pdf`
- `tmp/architecture_smoke/figure.png`

- [ ] **Step 3: Run a flow-figure smoke build**

Run:

```bash
cd C:/Users/hymn/.codex/skills/tikz-paper-figures
python scripts/build_figure.py --input tests/fixtures/flow_project/docs --confirm-summary yes --output-dir tmp/flow_smoke
```

Expected:

- `flow` is inferred
- all three output artifacts are produced

- [ ] **Step 4: Run a Chinese-language smoke build**

Run:

```bash
cd C:/Users/hymn/.codex/skills/tikz-paper-figures
python scripts/build_figure.py --input tests/fixtures/chinese_project/docs --language zh --confirm-summary yes --output-dir tmp/chinese_smoke
```

Expected:

- `xelatex` is selected
- all three output artifacts are produced

- [ ] **Step 5: Optionally mirror the finalized skill into the WSL-side skill directory**

If `/home/hymn/.codex/skills` is used by a separate Codex installation, copy the finalized directory there and rerun `quick_validate.py` against the mirrored path.

- [ ] **Step 6: Remove temporary smoke outputs that are not needed**

Delete only the ad hoc `tmp/*_smoke` outputs after validation, keeping the source skill files intact.

## Plan Review Checklist

Before executing this plan, verify:

- the approved spec still matches the intended first milestone
- the global install target `C:/Users/hymn/.codex/skills/tikz-paper-figures` is still the desired primary location
- the environment has `latexmk`, `pdflatex`, `xelatex`, and `pdftoppm`
- optional Python packages for PDF, PPTX, and DOCX extraction are available or installation is permitted

## Execution Notes

- This plan intentionally keeps Phase 1 narrow: both `architecture` and `flow` are supported, but only `paper-block-feedback-v1` is fully productized in the first milestone.
- If a fully distinct `paper-flow-maintainable-v1` style is required sooner, split it into a follow-up implementation plan rather than expanding the current scope mid-stream.
- If an agent is not allowed to launch subagents for plan review, perform a strict local review against the approved spec before starting Task 1.
