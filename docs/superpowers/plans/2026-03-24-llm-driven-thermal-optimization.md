# LLM-Driven Thermal Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把当前二维多组件热仿真例子升级成一个由结构化状态驱动、可评估约束、可记录轮次、可接入 DashScope `qwen3.5-plus` 的闭环优化系统 MVP。

**Architecture:** 先把现有 `02_multicomponent_steady_heat.py` 的硬编码布局和物理设置抽象成 `state.yaml` 与 schema，再搭建 `compiler/runner -> evaluator -> trace/rollback -> llm planner -> optimize loop` 的稳定流水线。所有 LLM 改动都通过结构化状态 diff 落地，不直接改求解脚本。

**Tech Stack:** Python, FEniCSx, gmsh, matplotlib, plotly, pytest, PyYAML, jsonschema or pydantic, DashScope API

---

### Task 1: 建立状态驱动骨架

**Files:**
- Create: `/home/hymn/msfenicsx/src/thermal_state/schema.py`
- Create: `/home/hymn/msfenicsx/src/thermal_state/load_save.py`
- Create: `/home/hymn/msfenicsx/states/baseline_multicomponent.yaml`
- Create: `/home/hymn/msfenicsx/tests/test_state_schema.py`

- [ ] **Step 1: 写失败测试，约束 baseline 状态可以被读取并校验**

```python
def test_baseline_state_loads_and_validates():
    state = load_state(Path("states/baseline_multicomponent.yaml"))
    assert state.geometry["type"] == "multirect_2d"
    assert [c.name for c in state.components] == ["base_plate", "chip", "heat_spreader"]
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
cd ~/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/test_state_schema.py -q
```

Expected: FAIL，提示 `load_state` 或 schema 模块不存在

- [ ] **Step 3: 创建最小 schema**

建议先用 `dataclasses` 或 `pydantic` 表达：

```python
@dataclass
class ComponentState:
    name: str
    x0: float
    y0: float
    width: float
    height: float
    material: str
```

- [ ] **Step 4: 创建 baseline YAML**

内容覆盖：

- 几何类型
- 3 个组件
- 材料导热率
- 热源
- 边界条件
- 网格参数
- 求解器
- 约束
- 目标

- [ ] **Step 5: 再次运行测试确认通过**

Run:

```bash
cd ~/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/test_state_schema.py -q
```

Expected: PASS

### Task 2: 把当前多组件示例重构为状态驱动的编译与运行器

**Files:**
- Create: `/home/hymn/msfenicsx/src/compiler/geometry_builder.py`
- Create: `/home/hymn/msfenicsx/src/compiler/mesh_builder.py`
- Create: `/home/hymn/msfenicsx/src/compiler/physics_builder.py`
- Create: `/home/hymn/msfenicsx/src/compiler/solver_runner.py`
- Create: `/home/hymn/msfenicsx/src/compiler/single_run.py`
- Modify: `/home/hymn/msfenicsx/examples/02_multicomponent_steady_heat.py`
- Modify: `/home/hymn/msfenicsx/src/msfenicsx_viz.py`
- Create: `/home/hymn/msfenicsx/tests/test_single_run_pipeline.py`

- [ ] **Step 1: 写失败测试，要求 state 驱动运行能生成现有可视化输出**

```python
def test_single_run_from_state_generates_outputs(tmp_path):
    result = run_case_from_state_file(
        Path("states/baseline_multicomponent.yaml"),
        output_root=tmp_path,
    )
    assert Path(result["overview_html"]).exists()
    assert Path(result["summary_txt"]).exists()
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
cd ~/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/test_single_run_pipeline.py -q
```

Expected: FAIL，提示 `run_case_from_state_file` 不存在

- [ ] **Step 3: 抽离几何构建**

把 `examples/02_multicomponent_steady_heat.py` 里的 Gmsh 布局逻辑迁移到：

- `geometry_builder.py`
- `mesh_builder.py`

输出：

- `mesh`
- `cell_tags`
- `facet_tags`

- [ ] **Step 4: 抽离物理构建**

在 `physics_builder.py` 中根据状态生成：

- DG0 材料场
- DG0 热源场
- Dirichlet / Neumann 边界条件
- UFL 变分形式

- [ ] **Step 5: 实现 `solver_runner.py`**

最小接口：

```python
def solve_steady_heat(state, mesh_bundle):
    ...
    return solution_bundle
```

- [ ] **Step 6: 实现 `single_run.py`**

最小接口：

```python
def run_case_from_state_file(state_path: Path, output_root: Path) -> dict[str, str]:
    ...
```

- [ ] **Step 7: 修改现有示例脚本**

让 `examples/02_multicomponent_steady_heat.py` 退化成一个轻量入口：

```python
from compiler.single_run import run_case_from_state_file
```

- [ ] **Step 8: 运行测试确认通过**

Run:

```bash
cd ~/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/test_single_run_pipeline.py -q
```

Expected: PASS

### Task 3: 建立约束评估器与结构化报告

**Files:**
- Create: `/home/hymn/msfenicsx/src/evaluator/constraints.py`
- Create: `/home/hymn/msfenicsx/src/evaluator/objectives.py`
- Create: `/home/hymn/msfenicsx/src/evaluator/report.py`
- Create: `/home/hymn/msfenicsx/tests/test_evaluator.py`

- [ ] **Step 1: 写失败测试，要求评估器能识别芯片最高温超过约束**

```python
def test_evaluator_reports_chip_temp_violation():
    evaluation = evaluate_case(
        state=state,
        metrics={"component_summary": {"chip": {"max": 0.2572}}},
    )
    assert evaluation["feasible"] is False
    assert evaluation["violations"][0]["name"] == "chip_max_temperature"
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
cd ~/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/test_evaluator.py -q
```

Expected: FAIL，提示 `evaluate_case` 不存在

- [ ] **Step 3: 实现指标提取**

至少包含：

- 整体温度极值
- 各组件 `min/max/mean`
- 网格规模

- [ ] **Step 4: 实现硬约束判断**

优先支持：

- `<=`
- `>=`
- 几何上界

- [ ] **Step 5: 生成结构化评估报告**

输出字段至少包含：

- `feasible`
- `violations`
- `objective_summary`
- `priority_actions`

- [ ] **Step 6: 重新运行测试确认通过**

### Task 4: 建立轮次记录、回滚和输出目录管理

**Files:**
- Create: `/home/hymn/msfenicsx/src/orchestration/run_manager.py`
- Create: `/home/hymn/msfenicsx/src/orchestration/rollback.py`
- Create: `/home/hymn/msfenicsx/tests/test_run_manager.py`

- [ ] **Step 1: 写失败测试，要求可以创建 `run_0001` 并写入状态快照**

```python
def test_run_manager_creates_incremental_run_directory(tmp_path):
    manager = RunManager(tmp_path)
    run_dir = manager.create_run_dir()
    assert run_dir.name == "run_0001"
```

- [ ] **Step 2: 运行测试确认失败**

- [ ] **Step 3: 实现 run 目录生成**

推荐结构：

```text
runs/run_0001/
  state.yaml
  proposal.json
  evaluation.json
  decision.json
  outputs/
```

- [ ] **Step 4: 实现当前指针文件**

文件：

- `/home/hymn/msfenicsx/runs/current_run.txt`

- [ ] **Step 5: 实现简单回滚接口**

```python
def rollback_to(run_id: str) -> None:
    ...
```

- [ ] **Step 6: 运行测试确认通过**

### Task 5: 接入 DashScope `qwen3.5-plus` 结构化提案器

**Files:**
- Create: `/home/hymn/msfenicsx/src/llm_adapters/dashscope_qwen.py`
- Create: `/home/hymn/msfenicsx/tests/test_dashscope_adapter.py`
- Create: `/home/hymn/msfenicsx/prompts/plan_changes_system.md`

- [ ] **Step 1: 写失败测试，要求适配器能把 evaluator 报告转成 prompt 并解析结构化响应**

```python
def test_dashscope_adapter_parses_structured_change_proposal():
    raw = '{"decision_summary": "...", "changes": []}'
    parsed = parse_change_proposal(raw)
    assert parsed["changes"] == []
```

- [ ] **Step 2: 运行测试确认失败**

- [ ] **Step 3: 实现结构化响应 schema 校验**

至少校验：

- `decision_summary`
- `changes`
- `expected_effects`
- `risk_notes`

- [ ] **Step 4: 实现 DashScope 客户端包装**

最小接口：

```python
def propose_next_changes(state, evaluation, history_summary) -> dict:
    ...
```

- [ ] **Step 5: 记录模型元信息**

至少记录：

- model name
- request timestamp
- token usage if available
- raw response path

- [ ] **Step 6: 运行测试确认通过**

### Task 6: 连接闭环优化 orchestrator

**Files:**
- Create: `/home/hymn/msfenicsx/src/orchestration/optimize_loop.py`
- Create: `/home/hymn/msfenicsx/examples/03_optimize_multicomponent_case.py`
- Create: `/home/hymn/msfenicsx/tests/test_optimize_loop.py`

- [ ] **Step 1: 写失败测试，要求一轮 loop 至少生成 run 目录、evaluation 和 proposal**

```python
def test_optimize_loop_runs_one_iteration(tmp_path):
    result = run_optimization_loop(
        state_path=Path("states/baseline_multicomponent.yaml"),
        runs_root=tmp_path,
        max_iters=1,
        dry_run_llm=True,
    )
    assert result["iterations"] == 1
```

- [ ] **Step 2: 运行测试确认失败**

- [ ] **Step 3: 实现单轮 loop**

顺序固定为：

1. 创建 run 目录
2. 保存当前 state
3. 执行仿真
4. 生成 evaluation
5. 若不可行则生成 proposal

- [ ] **Step 4: 实现多轮停止条件**

至少支持：

- `max_iters`
- `feasible == True`
- 连续非法提案

- [ ] **Step 5: 提供示例入口**

命令：

```bash
cd ~/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx python examples/03_optimize_multicomponent_case.py
```

- [ ] **Step 6: 运行测试确认通过**

### Task 7: 文档与人工验证

**Files:**
- Create: `/home/hymn/msfenicsx/notes/03_llm_optimization_workflow.md`
- Modify: `/home/hymn/msfenicsx/notes/02_multicomponent_heat_visualization.md`
- Modify: `/home/hymn/msfenicsx/outputs/README.md`

- [ ] **Step 1: 写工作流笔记**

覆盖内容：

- 结构化状态是什么
- 一轮优化发生了什么
- DashScope / `qwen3.5-plus` 在哪里接入
- 怎么查看 run 目录
- 怎么回滚

- [ ] **Step 2: 人工运行 baseline 单轮**

Run:

```bash
cd ~/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx python examples/02_multicomponent_steady_heat.py
```

Expected: 输出和现有可视化保持正常

- [ ] **Step 3: 人工运行优化 loop**

Run:

```bash
cd ~/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx python examples/03_optimize_multicomponent_case.py
```

Expected: 至少生成 `runs/run_0001/`，包含 `state.yaml`、`evaluation.json`、`proposal.json` 和 `outputs/`

- [ ] **Step 4: 总体验证**

Run:

```bash
cd ~/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests -q
```

Expected: 全部测试通过

- [ ] **Step 5: 回归检查旧例子**

Run:

```bash
cd ~/msfenicsx
/home/hymn/miniconda3/bin/conda run -n msfenicsx python examples/01_steady_heat_rectangle.py
```

Expected: 原始入门例子仍可运行

## Notes

- 当前阶段先做稳态二维案例 MVP，不提前引入瞬态、多物理场或复杂 CAD。
- DashScope 调用应通过环境变量读取密钥，不把密钥写进仓库。
- 按当前会话约束，未使用子代理做计划文档审阅；执行前可再进行一次人工审阅。
