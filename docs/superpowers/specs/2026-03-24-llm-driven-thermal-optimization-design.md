# 大模型驱动的二维热仿真闭环优化设计

## 1. 目标

构建一个可让大模型自动分析、修改、重跑并评估二维热仿真设计的闭环系统。

系统需要满足以下目标：

- 大模型可以修改参数、几何布局、材料分区、边界条件、网格策略和求解设置
- 系统能够自动判断当前设计是否满足约束
- 系统能够在不满足约束时继续迭代优化
- 每一轮决策都要保留完整记录
- 所有轮次都必须支持回滚和分支继续优化
- 每一轮都要有清晰的可视化输出，便于人和模型共同理解

当前模型路线：

- 大模型：`qwen3.5-plus`
- 服务提供方：`DashScope`

## 2. 总体思路

核心原则不是“让模型直接改 Python 脚本”，而是：

```text
模型修改结构化设计状态
-> 系统把状态编译成仿真任务
-> 运行 FEniCSx
-> 评估约束和目标
-> 记录决策
-> 决定下一轮修改
```

也就是：

```text
Design State -> Compiler/Runner -> Evaluator -> LLM Planner -> New Design State
```

这样做的优势是：

- 模型改动有边界
- 状态可重复运行
- 方便记录 diff
- 方便回滚
- 方便做多轮对比
- 以后可替换模型而不重写整个系统

## 3. 五层架构

### 3.1 Design State

这是系统唯一的设计事实来源。

建议每一轮设计都存成一个结构化文件，例如 `state.yaml`。它应完整描述当前仿真设计，而不是只保存局部参数。

推荐字段：

- `geometry`
- `components`
- `materials`
- `heat_sources`
- `boundary_conditions`
- `mesh`
- `solver`
- `constraints`
- `objectives`
- `metadata`

示意：

```yaml
geometry:
  type: multirect_2d

components:
  - name: base_plate
    x0: 0.0
    y0: 0.0
    width: 1.2
    height: 0.2
    material: base_material
  - name: chip
    x0: 0.45
    y0: 0.2
    width: 0.3
    height: 0.12
    material: chip_material

materials:
  base_material:
    conductivity: 12.0
  chip_material:
    conductivity: 45.0

heat_sources:
  - component: chip
    value: 60.0

boundary_conditions:
  - type: dirichlet
    location: left
    value: 0.0
  - type: dirichlet
    location: right
    value: 0.0
  - type: neumann
    location: others
    value: 0.0

mesh:
  nx: 36
  ny: 14

solver:
  kind: steady_heat
  linear_solver: lu

constraints:
  - name: chip_max_temperature
    op: "<="
    value: 0.20

objectives:
  - name: chip_max_temperature
    sense: minimize
```

### 3.2 Compiler + Runner

这一层把 `state.yaml` 编译成实际仿真任务。

推荐拆分为：

- `geometry_builder`
- `mesh_builder`
- `physics_builder`
- `solver_runner`

对应流程：

1. 读取状态
2. 构建几何与组件分区
3. 生成网格与标记
4. 生成材料、热源、边界条件和变分形式
5. 调用 FEniCSx 求解
6. 输出结果和派生指标

这一层应保持尽可能确定性。给定同一个状态，应尽量得到同样的几何、网格、求解设置和结果。

### 3.3 Evaluator

这一层负责判断设计是否满足要求。

它的输入不是自然语言，而是结构化仿真结果，例如：

- 整体温度最小值和最大值
- 各组件 `min/max/mean`
- 关键测点温度
- 几何尺寸
- 网格规模
- 约束相关派生量

输出建议为结构化评估报告：

```json
{
  "feasible": false,
  "violations": [
    {
      "name": "chip_max_temperature",
      "limit": 0.20,
      "actual": 0.2572,
      "margin": -0.0572,
      "severity": "high"
    }
  ],
  "objective_summary": {
    "chip_max_temperature": 0.2572
  },
  "priority_actions": [
    "increase spreader conductivity",
    "increase spreader width",
    "reduce heat concentration near chip"
  ]
}
```

这一层的本质是把“仿真结果”翻译成“下一轮优化任务”。

### 3.4 LLM Planner

这一层接 `Evaluator` 的报告和当前状态，生成下一轮修改建议。

当前接入方案：

- 模型：`qwen3.5-plus`
- API：`DashScope`

建议模型职责限定为：

- 解释当前设计为何不满足约束
- 选择下一轮优先改哪些变量
- 输出结构化修改方案

不建议一开始就让模型自由改脚本。应强制输出固定 schema，例如：

```json
{
  "decision_summary": "improve heat spreading above the chip",
  "changes": [
    {
      "path": "components.heat_spreader.width",
      "action": "set",
      "old": 0.70,
      "new": 0.90,
      "reason": "increase spreading area"
    },
    {
      "path": "materials.heat_spreader.conductivity",
      "action": "set",
      "old": 90.0,
      "new": 120.0,
      "reason": "lower thermal resistance"
    }
  ],
  "expected_effects": [
    "lower chip max temperature"
  ],
  "risk_notes": [
    "geometry width increases"
  ]
}
```

推荐提供统一适配层：

- `llm_adapters/dashscope_qwen.py`

职责：

- 组装 prompt
- 调用 DashScope
- 校验结构化响应
- 记录模型名、时间、token 和摘要

这样未来切换模型时，无需重写整个系统。

### 3.5 Trace + Compare + Rollback

这一层负责把整个闭环过程变成可追溯、可解释、可回退的工程系统。

每一轮至少记录：

- `state.yaml`
- `proposal.json`
- `evaluation.json`
- `decision.json`
- 仿真输出目录
- 可视化文件路径
- 父轮次编号
- 当前轮次编号

推荐目录结构：

```text
runs/
  run_0001/
    state.yaml
    proposal.json
    evaluation.json
    decision.json
    outputs/
      overview.html
      temperature.html
      summary.txt
  run_0002/
    ...
```

建议采用“不可变快照 + 当前指针”的回滚模式：

- 每一轮都是独立快照
- `current_run.txt` 指向当前采用的轮次
- 回滚就是把指针切回旧轮次
- 从旧轮次可以创建新分支继续优化

## 4. 建议目录结构

在当前项目里建议逐步扩展成：

```text
msfenicsx/
  examples/
  notes/
  outputs/
  runs/
  src/
    thermal_state/
      schema.py
      load_save.py
    compiler/
      geometry_builder.py
      mesh_builder.py
      physics_builder.py
      solver_runner.py
    evaluator/
      constraints.py
      objectives.py
      report.py
    llm_adapters/
      dashscope_qwen.py
    orchestration/
      optimize_loop.py
      rollback.py
      run_manager.py
    visualization/
      single_run_dashboard.py
      history_dashboard.py
```

## 5. 单轮闭环流程

一轮完整优化建议固定为：

1. 读取当前 `state.yaml`
2. 编译并运行仿真
3. 输出结果和可视化
4. 评估是否满足约束
5. 若满足约束，则标记为可行解
6. 若不满足约束，则调用 `qwen3.5-plus`
7. 生成结构化修改方案
8. 校验修改是否合法
9. 产出下一轮 `state.yaml`
10. 保存本轮所有记录

## 6. 多轮优化流程

多轮循环可以设计为：

```text
while not feasible and iter < max_iters:
    run_simulation()
    evaluate()
    if feasible:
        stop
    plan_changes_with_llm()
    validate_changes()
    create_next_state()
```

停止条件至少包括：

- 满足全部硬约束
- 达到最大轮次
- 连续多轮改进不足
- 模型连续提出非法修改
- 求解失败次数超过阈值

## 7. 可视化策略

### 7.1 单轮可视化

每一轮输出：

- `layout.png`
- `mesh.png`
- `subdomains.png`
- `temperature.png`
- `temperature.html`
- `overview.html`

其中 `overview.html` 应作为默认入口。

### 7.2 多轮可视化

建议后续增加：

- `history.html`

用于展示：

- 每轮改了什么
- 每轮关键指标曲线
- 哪轮开始满足约束
- 点击进入某轮 `overview.html`

## 8. 决策记录要求

为了让大模型后续“可解释、可复盘”，每轮必须保留：

- 约束违反情况
- 模型输入摘要
- 模型输出结构化提案
- 提案合法性检查结果
- 实际采用的修改
- 预期效果
- 实际效果

这样后面你不只是在看“结果”，而是在看“为什么这么改，以及改完有没有真正改善”。

## 9. 最小可行版本 MVP

建议分三阶段推进。

### 阶段 A：结构化状态 + 编译运行

目标：

- 把当前多组件例子从“硬编码脚本”改成“状态驱动”
- 能从 `state.yaml` 生成仿真并跑通

### 阶段 B：评估器 + 轮次记录

目标：

- 输出结构化评估报告
- 保存每轮目录
- 支持手工回滚

### 阶段 C：接入 DashScope + qwen3.5-plus 闭环优化

目标：

- 自动读评估报告
- 自动产生结构化修改建议
- 自动生成下一轮状态
- 自动重跑直到满足条件或停止

## 10. 当前项目与下一步建议

当前项目已经具备的基础：

- FEniCSx 稳态导热求解
- 多组件几何示例
- 单轮可视化输出
- HTML 总览页

最适合的下一步不是马上做全自动闭环，而是：

1. 先把当前多组件示例抽象成 `state.yaml`
2. 再做 `state -> run -> evaluation` 的确定性链路
3. 最后接入 DashScope 的 `qwen3.5-plus`

这样能最大程度降低复杂度，同时保留后续扩展到完整自动优化系统的空间。
