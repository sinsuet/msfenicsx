# Demo Workflow And Chinese Beamer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为当前单案例生成一套老师演示专用的 10 轮官方数据、中文汇总材料和 LaTeX Beamer 初稿。

**Architecture:** 先归档旧 run 数据并生成独立的官方 10 轮 demo runs，再从 run 目录自动提取每轮修改与效果，最后生成图表和中文 `ctexbeamer` 演示稿。所有演示内容都围绕同一个 SI 风格热案例，不扩展到新物理案例。

**Tech Stack:** Python, FEniCSx, DashScope API, pytest, matplotlib/plotly, JSON/YAML, LaTeX `ctexbeamer`

---

### Task 1: 构建独立的演示数据集目录和归档流程

**Files:**
- Modify: `/home/hymn/msfenicsx/examples/03_optimize_multicomponent_case.py`
- Create: `/home/hymn/msfenicsx/src/orchestration/demo_dataset.py`
- Create: `/home/hymn/msfenicsx/tests/test_demo_dataset.py`

- [ ] **Step 1: 写失败测试**

```python
def test_prepare_demo_dataset_archives_old_runs_and_creates_clean_target(tmp_path):
    ...
    assert (tmp_path / "runs_archive").exists()
    assert (tmp_path / "demo_runs" / "official_10_iter").exists()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd ~/msfenicsx && /home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/test_demo_dataset.py::test_prepare_demo_dataset_archives_old_runs_and_creates_clean_target -q`

- [ ] **Step 3: 最小实现**

提供一个演示数据集准备函数，职责包括：

- 归档旧 `runs/`
- 创建 `demo_runs/official_10_iter/`
- 允许把优化循环输出指向该目录

- [ ] **Step 4: 重新运行测试确认通过**

### Task 2: 生成 10 轮官方 run 数据并抽取每轮效果

**Files:**
- Create: `/home/hymn/msfenicsx/src/orchestration/demo_summary.py`
- Create: `/home/hymn/msfenicsx/examples/05_build_demo_summary.py`
- Create: `/home/hymn/msfenicsx/tests/test_demo_summary.py`

- [ ] **Step 1: 写失败测试**

```python
def test_demo_summary_links_run_n_proposal_to_run_n_plus_1_effect(tmp_path):
    ...
    assert summary["runs"][0]["chip_max_after"] == 88.7
    assert summary["runs"][0]["delta_chip_max"] < 0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd ~/msfenicsx && /home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/test_demo_summary.py::test_demo_summary_links_run_n_proposal_to_run_n_plus_1_effect -q`

- [ ] **Step 3: 最小实现**

生成：

- `demo_summary.json`
- `demo_summary.csv`
- `demo_summary.md`

每轮字段至少包含：

- `run_id`
- `iteration`
- `chip_max_before`
- `chip_max_after`
- `delta_chip_max`
- `changed_paths`
- `validation_status`
- `decision_summary`

- [ ] **Step 4: 重新运行测试确认通过**

### Task 3: 生成趋势图和代表性图表

**Files:**
- Create: `/home/hymn/msfenicsx/src/orchestration/demo_figures.py`
- Create: `/home/hymn/msfenicsx/examples/06_build_demo_figures.py`
- Create: `/home/hymn/msfenicsx/tests/test_demo_figures.py`

- [ ] **Step 1: 写失败测试**

```python
def test_demo_figures_builder_generates_trend_pngs(tmp_path):
    ...
    assert (figures_dir / "chip_max_trend.png").exists()
    assert (figures_dir / "delta_trend.png").exists()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd ~/msfenicsx && /home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/test_demo_figures.py::test_demo_figures_builder_generates_trend_pngs -q`

- [ ] **Step 3: 最小实现**

生成至少：

- `chip_max_trend.png`
- `delta_trend.png`
- `category_timeline.png`

- [ ] **Step 4: 重新运行测试确认通过**

### Task 4: 生成中文 Beamer 初稿

**Files:**
- Create: `/home/hymn/msfenicsx/slides/demo_workflow_beamer.tex`
- Create: `/home/hymn/msfenicsx/slides/assets/`
- Create: `/home/hymn/msfenicsx/examples/07_build_demo_beamer_inputs.py`
- Create: `/home/hymn/msfenicsx/tests/test_demo_beamer_inputs.py`

- [ ] **Step 1: 写失败测试**

```python
def test_demo_beamer_inputs_builder_exports_required_sections(tmp_path):
    ...
    assert "问题定义" in beamer_source
    assert "整体 workflow" in beamer_source
    assert "10轮总体趋势" in beamer_source
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd ~/msfenicsx && /home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/test_demo_beamer_inputs.py::test_demo_beamer_inputs_builder_exports_required_sections -q`

- [ ] **Step 3: 最小实现**

产出一份中文 `ctexbeamer` 草稿，正文结构固定为：

- 背景与目标
- 问题定义
- 约束合理性
- 初始不满足条件
- LLM 可修改参数
- workflow
- run 与 iteration 的区别
- 10 轮整体趋势
- 代表性轮次
- 结论与局限

- [ ] **Step 4: 重新运行测试确认通过**

### Task 5: 真实生成演示资产并做回归验证

**Files:**
- Modify: `/home/hymn/msfenicsx/notes/04_si_units_case.md`
- Create: `/home/hymn/msfenicsx/notes/05_demo_script.md`

- [ ] **Step 1: 生成官方 10 轮数据**

Run: `cd ~/msfenicsx && /home/hymn/miniconda3/bin/conda run -n msfenicsx python examples/03_optimize_multicomponent_case.py --real-llm --max-iters 10 --runs-root demo_runs/official_10_iter`

- [ ] **Step 2: 生成总表**

Run: `cd ~/msfenicsx && /home/hymn/miniconda3/bin/conda run -n msfenicsx python examples/05_build_demo_summary.py`

- [ ] **Step 3: 生成图表**

Run: `cd ~/msfenicsx && /home/hymn/miniconda3/bin/conda run -n msfenicsx python examples/06_build_demo_figures.py`

- [ ] **Step 4: 生成 Beamer 草稿**

Run: `cd ~/msfenicsx && /home/hymn/miniconda3/bin/conda run -n msfenicsx python examples/07_build_demo_beamer_inputs.py`

- [ ] **Step 5: 跑全量测试**

Run: `cd ~/msfenicsx && /home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests -q`

- [ ] **Step 6: 写演示脚本**

在 `notes/05_demo_script.md` 中固定老师演示顺序：

- 现场跑 1 轮
- 说明 run/iteration 区别
- 切到官方 10 轮结果
- 展示趋势图
- 切到 Beamer
