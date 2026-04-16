# LLM Consistency 10x15 Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the real-LLM optimization loop so a `10 groups x 15 rounds` comparison run can complete and produce a consistent Chinese summary of final performance and strategy differences.

**Architecture:** First harden DashScope response parsing and evidence capture at the adapter boundary, because the PDE solver is already functioning and the batch run is blocked by malformed or mixed-content LLM replies. Then resume only the interrupted comparison groups, regenerate per-group summaries/figures, and synthesize a final report focused on final chip-temperature improvement and cross-group strategy consistency.

**Tech Stack:** Python, pytest, DashScope-compatible chat completions API, FEniCSx workflow scripts, Markdown reporting.

---

### Task 1: Reproduce And Pin Down The Parser Failure

**Files:**
- Modify: `tests/test_dashscope_qwen.py`
- Inspect: `src/llm_adapters/dashscope_qwen.py`
- Inspect: `demo_runs/consistency_10x15_fullwindow_20260326/group_05`

- [ ] **Step 1: Write the failing test**

Create a parser-focused test that feeds a valid JSON proposal plus trailing commentary and asserts the adapter still extracts the first valid JSON object.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dashscope_qwen.py -q`
Expected: FAIL on the new parser case with a `JSONDecodeError` or equivalent parsing failure.

- [ ] **Step 3: Confirm evidence gap**

Inspect the interrupted `group_05` run directory and confirm the failing run contains `state.yaml` and `evaluation.json` but not `raw_response.json`, proving the adapter writes evidence too late.

### Task 2: Implement The Minimal Robust Parsing Fix

**Files:**
- Modify: `src/llm_adapters/dashscope_qwen.py`
- Test: `tests/test_dashscope_qwen.py`

- [ ] **Step 1: Write minimal implementation**

Update the adapter to:
1. strip fences,
2. decode the first JSON object even if extra text follows,
3. write `prompt.txt` and `raw_response.json` before proposal parsing so failures keep evidence.

- [ ] **Step 2: Run targeted tests**

Run:
- `pytest tests/test_dashscope_qwen.py -q`
- `pytest tests/test_optimize_cli.py -q`
- `pytest tests/test_optimize_loop.py -q`

Expected: PASS.

### Task 3: Resume The 10x15 Real-LLM Batch

**Files:**
- Modify if needed: `tmp/run_consistency_10x15_fullwindow.sh`
- Outputs: `demo_runs/consistency_10x15_fullwindow_20260326/group_05` through `group_10`

- [ ] **Step 1: Clean interrupted group**

Remove the partial `group_05` directory so the rerun keeps a clean 15-round record.

- [ ] **Step 2: Resume remaining groups**

Run the real-LLM optimizer for `group_05` through `group_10` with:
`--real-llm --max-iters 15 --max-invalid-proposals 15 --continue-when-feasible`

- [ ] **Step 3: Verify batch completeness**

Check that every `group_01` through `group_10` contains `run_0015`.

### Task 4: Build Comparison Artifacts And Final Report

**Files:**
- Run: `examples/05_build_demo_summary.py`
- Run: `examples/06_build_demo_figures.py`
- Create: `notes/10_llm_consistency_10group_15round_report.md`

- [ ] **Step 1: Rebuild summaries and figures**

Generate updated per-group summary artifacts for all ten groups.

- [ ] **Step 2: Extract final comparison signals**

Capture:
1. baseline chip temperature,
2. final chip temperature per group,
3. absolute/relative improvement,
4. main strategy sequence and breakthrough rounds,
5. whether strategies converge or diverge.

- [ ] **Step 3: Write Chinese report**

Produce a concise but evidence-backed Chinese report focused on final outcomes, strategy consistency, and whether independent 15-round LLM runs converge to similar solutions.
