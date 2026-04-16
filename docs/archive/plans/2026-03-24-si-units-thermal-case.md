# SI Units Thermal Case Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把当前二维热案例升级成带 SI 单位语义的教学模型，并把温度约束从抽象阈值改成工程化阈值。

**Architecture:** 先扩展 state schema 与 baseline 状态文件，再让求解与可视化链路读取并展示单位信息，最后更新学习笔记与回归测试，确保闭环优化仍可运行。

**Tech Stack:** Python, FEniCSx, gmsh, matplotlib, plotly, pytest, PyYAML

---

### Task 1: 扩展状态模型并更新 baseline

**Files:**
- Modify: `/home/hymn/msfenicsx/src/thermal_state/schema.py`
- Modify: `/home/hymn/msfenicsx/src/thermal_state/load_save.py`
- Modify: `/home/hymn/msfenicsx/states/baseline_multicomponent.yaml`
- Modify: `/home/hymn/msfenicsx/tests/test_state_schema.py`

- [ ] **Step 1: 写失败测试**

```python
def test_baseline_state_includes_si_units_and_reference_conditions():
    state = load_state(ROOT / "states" / "baseline_multicomponent.yaml")
    assert state.units["temperature"] == "degC"
    assert state.reference_conditions["ambient_temperature"] == 25.0
    assert state.constraints[0].value == 85.0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd ~/msfenicsx && /home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/test_state_schema.py::test_baseline_state_includes_si_units_and_reference_conditions -q`

- [ ] **Step 3: 最小实现**

为 `ThermalDesignState` 增加 `units` 和 `reference_conditions`，并在 load/save 中读写。

- [ ] **Step 4: 更新 baseline**

把边界温度改成 `25.0`，把芯片最高温约束改成 `85.0`，补上单位字段。

- [ ] **Step 5: 重新运行测试确认通过**

### Task 2: 让求解结果与可视化显示单位语义

**Files:**
- Modify: `/home/hymn/msfenicsx/src/compiler/physics_builder.py`
- Modify: `/home/hymn/msfenicsx/src/compiler/single_run.py`
- Modify: `/home/hymn/msfenicsx/src/msfenicsx_viz.py`
- Create or Modify: `/home/hymn/msfenicsx/tests/test_single_run_pipeline.py`

- [ ] **Step 1: 写失败测试**

```python
def test_single_run_reports_temperature_unit_in_metrics_or_outputs(tmp_path):
    result = run_case_from_state_file(ROOT / "states" / "baseline_multicomponent.yaml", output_root=tmp_path)
    assert result["metrics"]["units"]["temperature"] == "degC"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd ~/msfenicsx && /home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/test_single_run_pipeline.py::test_single_run_reports_temperature_unit_in_metrics_or_outputs -q`

- [ ] **Step 3: 最小实现**

让 `physics_builder.py` 从 state 边界条件中读取 Dirichlet 温度值，并让 `single_run.py` 的 metrics 带上 `units` 与 `reference_conditions`。

- [ ] **Step 4: 更新可视化标签**

色条、坐标轴、summary 文本与 overview 页面加入单位说明。

- [ ] **Step 5: 重新运行测试确认通过**

### Task 3: 更新教学笔记并做回归验证

**Files:**
- Modify: `/home/hymn/msfenicsx/notes/03_llm_optimization_workflow.md`
- Create: `/home/hymn/msfenicsx/notes/04_si_units_case.md`
- Modify: `/home/hymn/msfenicsx/tests/test_evaluator.py`

- [ ] **Step 1: 写失败测试**

```python
def test_baseline_constraint_uses_engineering_temperature_limit():
    state = load_state(ROOT / "states" / "baseline_multicomponent.yaml")
    assert state.constraints[0].name == "chip_max_temperature"
    assert state.constraints[0].value == 85.0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd ~/msfenicsx && /home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/test_state_schema.py::test_baseline_constraint_uses_engineering_temperature_limit -q`

- [ ] **Step 3: 更新文档**

解释：
- 原先的 `0.2` 是抽象教学阈值
- 新版 `85 degC` 是工程化教学阈值
- 当前热源仍是等效体热源

- [ ] **Step 4: 跑关键回归**

Run:
- `cd ~/msfenicsx && /home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/test_state_schema.py tests/test_single_run_pipeline.py tests/test_evaluator.py -q`
- `cd ~/msfenicsx && /home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests -q`

- [ ] **Step 5: 真实示例验证**

Run:
- `cd ~/msfenicsx && /home/hymn/miniconda3/bin/conda run -n msfenicsx python examples/02_multicomponent_steady_heat.py`
- `cd ~/msfenicsx && /home/hymn/miniconda3/bin/conda run -n msfenicsx python examples/03_optimize_multicomponent_case.py --real-llm --max-iters 1`
