# Physics Legality Constraints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为真实 LLM 热仿真闭环增加通用型物理与几何合法性约束，阻止离谱提案直接落地。

**Architecture:** 新增独立的 `validation` 模块，负责检查 proposal 与应用后的 next state 是否满足数值边界、步长限制和几何合法性。`optimize_loop` 在应用提案前调用 validator，并把结果写入 run 目录。

**Tech Stack:** Python, pytest, PyYAML

---

### Task 1: 新增 proposal validator 的失败测试

**Files:**
- Create: `/home/hymn/msfenicsx/tests/test_proposal_validation.py`

- [ ] **Step 1: 写失败测试，覆盖合法提案与非法提案**

```python
def test_validate_proposal_rejects_conductivity_above_upper_bound():
    ...

def test_validate_proposal_rejects_overlapping_components():
    ...
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
cd ~/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/test_proposal_validation.py -q
```

Expected: FAIL，提示 `validation` 模块不存在

### Task 2: 实现 validation 模块

**Files:**
- Create: `/home/hymn/msfenicsx/src/validation/__init__.py`
- Create: `/home/hymn/msfenicsx/src/validation/bounds.py`
- Create: `/home/hymn/msfenicsx/src/validation/geometry.py`
- Create: `/home/hymn/msfenicsx/src/validation/proposals.py`

- [ ] **Step 1: 实现范围常量和步长限制**
- [ ] **Step 2: 实现矩形重叠与包络检查**
- [ ] **Step 3: 实现 `validate_proposal_against_state`**
- [ ] **Step 4: 运行测试确认通过**

### Task 3: 把 validator 接入 optimize loop

**Files:**
- Modify: `/home/hymn/msfenicsx/src/orchestration/optimize_loop.py`
- Modify: `/home/hymn/msfenicsx/tests/test_optimize_loop.py`

- [ ] **Step 1: 写失败测试，要求非法 proposal 会被拒绝并记录**
- [ ] **Step 2: 运行测试确认失败**
- [ ] **Step 3: 最小修改 loop，写出 `proposal_validation.json`**
- [ ] **Step 4: 重新运行测试确认通过**

### Task 4: 文档与真实回归

**Files:**
- Modify: `/home/hymn/msfenicsx/notes/03_llm_optimization_workflow.md`

- [ ] **Step 1: 补充真实合法性约束说明**
- [ ] **Step 2: 运行全量测试**
- [ ] **Step 3: 用真实 DashScope 跑 1 轮并检查 `proposal_validation.json`**
