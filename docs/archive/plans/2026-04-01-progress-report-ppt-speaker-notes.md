# Progress Report PPT Speaker Notes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate detailed Chinese speaker notes for the 35-slide progress-report PPT and inject them into a new `main_with_notes.pptx` without changing slide visuals.

**Architecture:** Keep the source of truth in a repository-local JSON notes file, then use a small OpenXML-level injector to add `notesMaster` and per-slide `notesSlide` parts to a copied `.pptx`. Verification will confirm note-part counts and extracted note text on representative pages before delivery.

**Tech Stack:** Python 3, ZIP/XML processing, PowerPoint OpenXML package structure

---

## Target File Map

- Create: `/home/hymn/msfenicsx/docs/reports/ppt_notes/2026-04-01-progress-report-notes/speaker_notes.json`
- Create: `/home/hymn/msfenicsx/docs/reports/ppt_notes/2026-04-01-progress-report-notes/inject_notes.py`
- Create: `/home/hymn/msfenicsx/docs/reports/ppt_notes/2026-04-01-progress-report-notes/extract_notes.py`
- Output: `C:\Users\hymn\Downloads\main_with_notes.pptx`

## Task 1: Prepare Notes Source

**Files:**
- Create: `/home/hymn/msfenicsx/docs/reports/ppt_notes/2026-04-01-progress-report-notes/speaker_notes.json`

- [ ] **Step 1: Freeze the 35-slide order**

Use the existing Beamer slide order and the converted PPT slide count to confirm there are exactly 35 note entries.

- [ ] **Step 2: Write detailed note text for every slide**

For each slide, include:

- slide number
- title
- recommended duration
- full speaker note text

- [ ] **Step 3: Keep backup-slide notes concise**

Backup slides should be phrased as optional Q&A answers rather than mandatory presentation script.

## Task 2: Implement Notes Injection

**Files:**
- Create: `/home/hymn/msfenicsx/docs/reports/ppt_notes/2026-04-01-progress-report-notes/inject_notes.py`

- [ ] **Step 1: Copy the source PPTX to a new output file**

Input:

- `C:\Users\hymn\Downloads\main.pptx`

Output:

- `C:\Users\hymn\Downloads\main_with_notes.pptx`

- [ ] **Step 2: Add the minimal notes master structure**

Write the required master parts, relationships, and content-type entries if they do not already exist.

- [ ] **Step 3: Add one notes slide per presentation slide**

Each notes slide must:

- link back to its slide
- link to the notes master
- contain the corresponding speaker note body

- [ ] **Step 4: Update slide relationships**

Attach each `notesSlide` to the matching `slideN.xml.rels`.

## Task 3: Implement Verification Helpers

**Files:**
- Create: `/home/hymn/msfenicsx/docs/reports/ppt_notes/2026-04-01-progress-report-notes/extract_notes.py`

- [ ] **Step 1: Count note parts in the output PPTX**

Expected: 35 notes slides.

- [ ] **Step 2: Extract representative notes text**

Check at least:

- slide 1
- slide 18
- slide 24
- slide 31
- one backup slide

- [ ] **Step 3: Confirm content matches the JSON source**

Use exact text extraction comparison on sampled pages.

## Task 4: Deliver

**Files:**
- Output: `C:\Users\hymn\Downloads\main_with_notes.pptx`

- [ ] **Step 1: Run the full injection flow**

Run the injector against the source PPTX.

- [ ] **Step 2: Run the verification helper**

Confirm note-part count and sampled note text.

- [ ] **Step 3: Report the output path and usage**

Tell the user where the new file is and that the notes should be visible in PowerPoint’s notes pane / presenter view.
