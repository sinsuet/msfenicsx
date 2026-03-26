# Demo Workflow Beamer 10x15 Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update the Chinese Beamer deck so it keeps the existing physics and workflow teaching content, replaces the outdated single-run `official_10_iter` story with the new formal `10 groups x 15 rounds` experiment, and compiles cleanly with synchronized generator/test coverage.

**Architecture:** Keep the front half of the deck stable because the problem definition, PDE model, component modeling, and LLM workflow remain valid. Replace the outdated experiment section with a two-layer narrative: first a representative single-run walkthrough using a typical successful group, then a new multi-run consistency section driven by the fresh `10x15` aggregate assets and report. Update both the static slide source and the Beamer generator/test path so the repository has one coherent presentation contract.

**Tech Stack:** XeLaTeX/latexmk, static Beamer `.tex`, Python Beamer generator, pytest, existing PNG/CSV/JSON experiment artifacts.

---

## File Map

- Modify: `/home/hymn/msfenicsx/slides/demo_workflow_beamer.tex`
  - Main presentation source that currently still contains the old `official_10_iter` narrative.
- Modify: `/home/hymn/msfenicsx/src/orchestration/demo_beamer.py`
  - Generator that still emits the old “官方 10 轮总体趋势” structure.
- Modify: `/home/hymn/msfenicsx/examples/07_build_demo_beamer_inputs.py`
  - Only if generator arguments or defaults need to change.
- Modify: `/home/hymn/msfenicsx/tests/test_demo_beamer_inputs.py`
  - Update assertions so automated checks match the new slide structure.
- Read only: `/home/hymn/msfenicsx/notes/10_llm_consistency_10group_15round_report.md`
  - Primary narrative source of truth for the new experiment section.
- Read only: `/home/hymn/msfenicsx/demo_runs/consistency_10x15_fullwindow_20260326/consistency_10x15_group_comparison.csv`
  - Structured result table for exact numbers.
- Read only: `/home/hymn/msfenicsx/demo_runs/consistency_10x15_fullwindow_20260326/figures/consistency_10x15_trajectories.png`
- Read only: `/home/hymn/msfenicsx/demo_runs/consistency_10x15_fullwindow_20260326/figures/consistency_10x15_final_chip_max.png`
- Read only: `/home/hymn/msfenicsx/demo_runs/consistency_10x15_fullwindow_20260326/figures/consistency_10x15_first_base_k_round.png`
- Read only: `/home/hymn/msfenicsx/demo_runs/consistency_10x15_fullwindow_20260326/group_06/run_0001/outputs/figures/*.png`
  - Recommended representative baseline visuals.
- Read only: `/home/hymn/msfenicsx/demo_runs/consistency_10x15_fullwindow_20260326/group_06/run_0015/outputs/figures/*.png`
  - Recommended representative final visuals.

---

### Task 1: Lock The New Slide Contract In Tests And Generator

**Files:**
- Modify: `/home/hymn/msfenicsx/tests/test_demo_beamer_inputs.py`
- Modify: `/home/hymn/msfenicsx/src/orchestration/demo_beamer.py`
- Modify if needed: `/home/hymn/msfenicsx/examples/07_build_demo_beamer_inputs.py`
- Read: `/home/hymn/msfenicsx/notes/10_llm_consistency_10group_15round_report.md`

- [ ] **Step 1: Write the failing test**

Update `/home/hymn/msfenicsx/tests/test_demo_beamer_inputs.py` so it asserts the generated Beamer source includes the new experiment structure, for example:

```python
assert "代表性单跑" in beamer_source
assert "10组 15轮正式实验" in beamer_source
assert "第一次使用 base_k 的轮次" in beamer_source
assert "官方 10 轮总体趋势" not in beamer_source
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd ~/msfenicsx && source ~/miniconda3/etc/profile.d/conda.sh && conda activate msfenicsx && pytest tests/test_demo_beamer_inputs.py -q
```

Expected: FAIL because `/home/hymn/msfenicsx/src/orchestration/demo_beamer.py` still emits the old 10-run headings.

- [ ] **Step 3: Implement the minimal generator update**

Update `/home/hymn/msfenicsx/src/orchestration/demo_beamer.py` so it emits the new post-workflow structure:

- representative single-run section
- `10组 15轮正式实验` section
- trajectory / final distribution / first-`base_k` slides
- new conclusion wording based on the formal 10-group report

Recommended implementation choices:

- keep the front half of the generator stable
- stop hard-coding `run_0009` as the only turning point
- treat aggregate `10x15` figures as first-class inputs
- choose `group_06` as the default representative single run because it is a typical successful path rather than the most extreme best case

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd ~/msfenicsx && source ~/miniconda3/etc/profile.d/conda.sh && conda activate msfenicsx && pytest tests/test_demo_beamer_inputs.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_demo_beamer_inputs.py src/orchestration/demo_beamer.py examples/07_build_demo_beamer_inputs.py
git commit -m "feat: refresh beamer generator for 10x15 experiment"
```

---

### Task 2: Replace The Outdated Static Slide Section With The New Narrative

**Files:**
- Modify: `/home/hymn/msfenicsx/slides/demo_workflow_beamer.tex`
- Read: `/home/hymn/msfenicsx/notes/10_llm_consistency_10group_15round_report.md`
- Read: `/home/hymn/msfenicsx/demo_runs/consistency_10x15_fullwindow_20260326/consistency_10x15_group_comparison.csv`

- [ ] **Step 1: Identify the replacement range**

Treat the old block around `/home/hymn/msfenicsx/slides/demo_workflow_beamer.tex:235` through `/home/hymn/msfenicsx/slides/demo_workflow_beamer.tex:357` as the main replacement zone. Preserve the earlier physics/workflow slides unless a number/path must be updated.

- [ ] **Step 2: Rewrite the section outline**

In `/home/hymn/msfenicsx/slides/demo_workflow_beamer.tex`, replace the old `10轮官方数据` narrative with this recommended outline:

1. `代表性单跑：15轮温度轨迹`
2. `代表性单跑：关键轮次与策略切换`
3. `代表性单跑：初始与最终布局/温度场对比`
4. `10组 15轮正式实验：实验设置`
5. `10组 15轮正式实验：全组轨迹`
6. `10组 15轮正式实验：最终结果分布`
7. `10组 15轮正式实验：第一次使用 base_k 的轮次`
8. `结果分群与机制解释`
9. `更新后的结论与下一步`

- [ ] **Step 3: Update all numbers and claims**

Remove or rewrite all old claims that reference:

- `official_10_iter`
- “第 9 轮是唯一关键转折”
- “最终从 89.301 降到 58.613 就是最终结论”

Replace them with the new formal findings:

- `9 / 10` 组最终进入可行域
- final-result grouping at `43.16`, `58.58~58.61`, `68.85`, `89.20`
- key mechanism: early recognition and sufficient strengthening of `base_k`

- [ ] **Step 4: Keep the deck length under control**

When editing `/home/hymn/msfenicsx/slides/demo_workflow_beamer.tex`, target roughly `22–26` slides total. If content becomes crowded, compress detailed per-run tables before cutting the new cross-group findings.

- [ ] **Step 5: Commit**

```bash
git add slides/demo_workflow_beamer.tex
git commit -m "feat: rewrite beamer narrative around 10x15 experiment"
```

---

### Task 3: Rebase Visual Assets Onto The Formal 10x15 Dataset

**Files:**
- Modify: `/home/hymn/msfenicsx/slides/demo_workflow_beamer.tex`
- Read: `/home/hymn/msfenicsx/demo_runs/consistency_10x15_fullwindow_20260326/group_06/run_0001/outputs/figures/layout.png`
- Read: `/home/hymn/msfenicsx/demo_runs/consistency_10x15_fullwindow_20260326/group_06/run_0001/outputs/figures/mesh.png`
- Read: `/home/hymn/msfenicsx/demo_runs/consistency_10x15_fullwindow_20260326/group_06/run_0001/outputs/figures/subdomains.png`
- Read: `/home/hymn/msfenicsx/demo_runs/consistency_10x15_fullwindow_20260326/group_06/run_0001/outputs/figures/temperature.png`
- Read: `/home/hymn/msfenicsx/demo_runs/consistency_10x15_fullwindow_20260326/group_06/run_0015/outputs/figures/layout.png`
- Read: `/home/hymn/msfenicsx/demo_runs/consistency_10x15_fullwindow_20260326/group_06/run_0015/outputs/figures/temperature.png`
- Read: `/home/hymn/msfenicsx/demo_runs/consistency_10x15_fullwindow_20260326/figures/consistency_10x15_trajectories.png`
- Read: `/home/hymn/msfenicsx/demo_runs/consistency_10x15_fullwindow_20260326/figures/consistency_10x15_final_chip_max.png`
- Read: `/home/hymn/msfenicsx/demo_runs/consistency_10x15_fullwindow_20260326/figures/consistency_10x15_first_base_k_round.png`

- [ ] **Step 1: Replace baseline and final single-run images**

In `/home/hymn/msfenicsx/slides/demo_workflow_beamer.tex`, replace all old `official_10_iter` figure paths with formal `10x15` paths.

Recommended defaults:

- baseline visuals: `group_06/run_0001`
- representative final visuals: `group_06/run_0015`

- [ ] **Step 2: Insert the three aggregate comparison figures**

Add the following already-generated figures directly into the new multi-run section:

- `/home/hymn/msfenicsx/demo_runs/consistency_10x15_fullwindow_20260326/figures/consistency_10x15_trajectories.png`
- `/home/hymn/msfenicsx/demo_runs/consistency_10x15_fullwindow_20260326/figures/consistency_10x15_final_chip_max.png`
- `/home/hymn/msfenicsx/demo_runs/consistency_10x15_fullwindow_20260326/figures/consistency_10x15_first_base_k_round.png`

- [ ] **Step 3: Make captions support the argument**

Rewrite captions and bullets so each image answers a specific question:

- trajectory figure: “各组何时掉出平台期”
- final bar chart: “最终结果为什么是分群而不是单点收敛”
- first-`base_k` chart: “策略差异如何解释结果差异”

- [ ] **Step 4: Commit**

```bash
git add slides/demo_workflow_beamer.tex
git commit -m "feat: point beamer visuals to formal 10x15 assets"
```

---

### Task 4: Compile, Validate, And Tighten The Deck

**Files:**
- Run: `/home/hymn/msfenicsx/slides/build_beamer.sh`
- Inspect output: `/home/hymn/msfenicsx/slides/demo_workflow_beamer.pdf`
- Optionally regenerate: `/home/hymn/msfenicsx/examples/07_build_demo_beamer_inputs.py`

- [ ] **Step 1: Compile the deck**

Run:

```bash
cd ~/msfenicsx && bash slides/build_beamer.sh
```

Expected: `latexmk` exits successfully and updates `/home/hymn/msfenicsx/slides/demo_workflow_beamer.pdf`.

- [ ] **Step 2: Run the Python-side regression check**

Run:

```bash
cd ~/msfenicsx && source ~/miniconda3/etc/profile.d/conda.sh && conda activate msfenicsx && pytest tests/test_demo_beamer_inputs.py -q
```

Expected: PASS.

- [ ] **Step 3: Perform slide QA**

Open `/home/hymn/msfenicsx/slides/demo_workflow_beamer.pdf` and verify:

- no LaTeX overflow warnings turned into visible layout problems
- the new section transition from single-run to 10-group evidence is easy to follow
- all figure captions match the new numbers
- no page still references `official_10_iter` or the old 10-round-only conclusion

- [ ] **Step 4: Tighten wording if needed**

If any slide feels too dense, compress in this order:

1. shorten repeated explanatory bullets
2. merge small per-run tables
3. move non-essential numeric detail into speaker notes or backup material

- [ ] **Step 5: Commit**

```bash
git add slides/demo_workflow_beamer.tex slides/demo_workflow_beamer.pdf
git commit -m "feat: finalize beamer refresh with 10x15 results"
```

---

### Task 5: Keep The Verbal Story Consistent Across Slides And Notes

**Files:**
- Read: `/home/hymn/msfenicsx/notes/10_llm_consistency_10group_15round_report.md`
- Optionally modify: `/home/hymn/msfenicsx/notes/05_demo_script.md`
- Optionally modify: `/home/hymn/msfenicsx/notes/07_single_case_workflow_summary.md`

- [ ] **Step 1: Align spoken conclusions**

Ensure the deck’s final claims are consistent with the report:

- `9 / 10` groups feasible
- local strategy consistency is strong
- global best-result consistency is weaker
- `base_k` timing and magnitude explain most of the final variance

- [ ] **Step 2: Decide whether to refresh speaker notes**

If `/home/hymn/msfenicsx/notes/05_demo_script.md` is still used for rehearsal, update it so it references the new group-based story instead of the old single official run.

- [ ] **Step 3: Final verification pass**

Run:

```bash
cd ~/msfenicsx && grep -RIn "official_10_iter\\|官方 10 轮总体趋势\\|run_0009 把底板导热率从 12 提高到 24，直接把热点拉低到约 58.613" slides notes --include="*.tex" --include="*.md"
```

Expected: no stale references remain in the final presentation materials you still intend to use.

- [ ] **Step 4: Commit**

```bash
git add notes/05_demo_script.md notes/07_single_case_workflow_summary.md
git commit -m "docs: align presentation notes with 10x15 experiment"
```
