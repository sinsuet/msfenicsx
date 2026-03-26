# 多组件二维稳态导热与可视化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增一个带多组件几何、分区材料、热源和浏览器可查看 HTML 可视化的二维稳态导热入门示例。

**Architecture:** 使用 `gmsh` 在脚本内创建三矩形组件装配体，借助 `dolfinx` 读取网格和子区域标签，求解分区材料的稳态导热问题。可视化部分抽到独立模块中，统一输出布局图、网格图、分区图、温度场 PNG 和交互式 HTML。

**Tech Stack:** Python, FEniCSx, gmsh, matplotlib, plotly, pytest

---

### Task 1: 安装和验证新增依赖

**Files:**
- Modify: `/home/hymn/msfenicsx/notes/01_install_and_first_heat_problem.md`

- [ ] **Step 1: 安装依赖前写下需要验证的包**

目标包：

```text
gmsh
plotly
pytest
```

- [ ] **Step 2: 运行安装命令**

Run:

```bash
cd ~/msfenicsx
/home/hymn/miniconda3/bin/conda install -y -n msfenicsx --override-channels -c conda-forge gmsh plotly pytest
```

Expected: 安装成功，无求解冲突

- [ ] **Step 3: 运行导入验证**

Run:

```bash
cd ~/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -c "import gmsh, plotly, pytest; print('ok')"
```

Expected: 输出 `ok`

### Task 2: 先写失败测试，定义布局与汇总接口

**Files:**
- Create: `/home/hymn/msfenicsx/tests/test_multicomponent_viz.py`
- Create: `/home/hymn/msfenicsx/src/msfenicsx_viz.py`

- [ ] **Step 1: 写一个失败测试，约束组件布局定义**

```python
def test_default_component_layout_contains_expected_regions():
    layout = default_component_layout()
    assert [part.name for part in layout] == ["base_plate", "chip", "heat_spreader"]
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
cd ~/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/test_multicomponent_viz.py -q
```

Expected: FAIL，提示函数不存在

- [ ] **Step 3: 写最小实现让测试通过**

- [ ] **Step 4: 再补一个失败测试，约束组件级温度汇总**

```python
def test_component_summary_returns_min_max_mean():
    ...
```

- [ ] **Step 5: 运行测试确认失败，再补最小实现**

### Task 3: 实现多组件示例脚本

**Files:**
- Create: `/home/hymn/msfenicsx/examples/02_multicomponent_steady_heat.py`
- Modify: `/home/hymn/msfenicsx/src/msfenicsx_viz.py`

- [ ] **Step 1: 先写一个集成测试，要求示例运行后生成关键输出**

关键文件：

```text
layout.png
mesh.png
subdomains.png
temperature.png
temperature.html
solution.xdmf
summary.txt
```

- [ ] **Step 2: 运行测试确认失败**

- [ ] **Step 3: 用 `gmsh` 实现三矩形组件、物理组和边界组**

- [ ] **Step 4: 在 `dolfinx` 中实现分区材料、芯片热源和边界条件**

- [ ] **Step 5: 求解稳态温度场**

- [ ] **Step 6: 生成静态图和 HTML**

- [ ] **Step 7: 重新运行测试确认通过**

### Task 4: 更新笔记并做人工验证

**Files:**
- Create: `/home/hymn/msfenicsx/notes/02_multicomponent_heat_visualization.md`
- Modify: `/home/hymn/msfenicsx/outputs/README.md`

- [ ] **Step 1: 写学习笔记**

内容包括：

- 为什么引入组件分区
- 如何理解热源与材料
- 如何读布局图、网格图、分区图和温度场图
- 如何打开 HTML 结果

- [ ] **Step 2: 实际运行示例**

Run:

```bash
cd ~/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx python examples/02_multicomponent_steady_heat.py
```

Expected: 终端打印网格与温度摘要，并生成所有输出文件

- [ ] **Step 3: 人工检查输出文件**

检查：

- `layout.png` 组件位置正确
- `mesh.png` 网格合理
- `subdomains.png` 标签正确
- `temperature.png` 热源附近温度更高
- `temperature.html` 浏览器可打开

- [ ] **Step 4: 回归运行原始示例**

Run:

```bash
cd ~/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx python examples/01_steady_heat_rectangle.py
```

Expected: 原示例仍然可运行
