# History Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为多轮 LLM 热仿真闭环生成一个可分析的 `history.html` 工作台，统一查看指标趋势、提案、校验与单轮入口。

**Architecture:** 增加独立的 `history_report` 汇总器，扫描 `runs/run_xxxx/` 并生成 `history_summary.json`。`msfenicsx_viz.py` 负责渲染历史工作台 HTML，示例入口脚本负责手动重建页面。

**Tech Stack:** Python, pytest, JSON, Plotly, HTML

---

### Task 1: 写失败测试，固定历史汇总格式

**Files:**
- Create: `/home/hymn/msfenicsx/tests/test_history_report.py`

- [ ] **Step 1: 写失败测试，要求能从伪造 run 目录提取关键字段**

```python
def test_collect_history_summary_reads_run_metadata(tmp_path):
    ...
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
cd ~/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/test_history_report.py -q
```

Expected: FAIL，提示 `history_report` 模块不存在

### Task 2: 实现历史汇总器

**Files:**
- Create: `/home/hymn/msfenicsx/src/orchestration/history_report.py`

- [ ] **Step 1: 实现 run 目录扫描**
- [ ] **Step 2: 实现关键字段提取**
- [ ] **Step 3: 实现 `history_summary.json` 写出**
- [ ] **Step 4: 运行测试确认通过**

### Task 3: 生成 `history.html`

**Files:**
- Modify: `/home/hymn/msfenicsx/src/msfenicsx_viz.py`
- Create: `/home/hymn/msfenicsx/examples/04_build_history_dashboard.py`
- Create: `/home/hymn/msfenicsx/tests/test_history_dashboard.py`

- [ ] **Step 1: 写失败测试，要求生成 `runs/history.html`**
- [ ] **Step 2: 运行测试确认失败**
- [ ] **Step 3: 在 `msfenicsx_viz.py` 增加历史工作台渲染函数**
- [ ] **Step 4: 增加重建脚本**
- [ ] **Step 5: 运行测试确认通过**

### Task 4: 接真实 run 数据做回归

**Files:**
- Modify: `/home/hymn/msfenicsx/notes/03_llm_optimization_workflow.md`

- [ ] **Step 1: 补充 `history.html` 使用说明**
- [ ] **Step 2: 运行全量测试**
- [ ] **Step 3: 执行 `python examples/04_build_history_dashboard.py`**
- [ ] **Step 4: 检查 `runs/history_summary.json` 和 `runs/history.html`**
