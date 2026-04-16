# SI Units Thermal Case Design

## Goal

把当前二维稳态导热教学案例从“抽象无量纲数值”升级为“带 SI 单位语义的教学模型”，让温度约束、边界条件、材料参数和热源解释更接近真实工程，同时保持当前 FEniCSx 入门体验和 LLM 闭环优化结构不变。

## Why This Change

当前 baseline 案例中的 `chip_max_temperature <= 0.2` 只是一个教学型阈值，不具备稳定的工程物理意义。对于后续让 LLM 做约束驱动设计与可解释决策，温度、材料和边界条件需要至少具有一致的物理语义，否则模型只能优化“数字游戏”，不能优化“热设计”。

## Scope

本次升级只做“工程化教学模型”而不做完整封装热设计模型。

包含：

- 为状态文件增加单位与参考工况字段
- 把边界温度改为真实环境/冷端温度
- 把芯片温度约束改成工程上更像真的值
- 更新可视化和文本输出中的单位说明
- 更新学习笔记，解释这是二维稳态、等效热源模型

不包含：

- 对流边界条件
- 界面热阻
- 瞬态热分析
- 多层封装/PCB 细化建模
- 严格由芯片功率和厚度反推体热源的完整校准

## Recommended Physical Framing

第一版采用以下教学型工程语义：

- 长度单位：`m`
- 温度单位：`degC`
- 导热率单位：`W/(m*K)`
- 热源单位：`W/m^3`
- 左右冷端边界温度：`25 degC`
- 芯片最高温约束：`85 degC`

解释方式：

- 当前模型是二维截面稳态导热模型
- 芯片热源使用等效体热源表示
- 材料导热率和边界温度使用工程常见单位
- 该模型适合教学和闭环优化，不等于完整器件认证模型

## Data Model Changes

`ThermalDesignState` 增加两个新顶层字段：

- `units`
- `reference_conditions`

建议结构：

```yaml
units:
  length: m
  temperature: degC
  conductivity: W/(m*K)
  heat_source: W/m^3

reference_conditions:
  ambient_temperature: 25.0
  cold_sink_temperature: 25.0
```

`baseline_multicomponent.yaml` 中：

- 左右 Dirichlet 边界改为 `25.0`
- `chip_max_temperature` 约束改为 `85.0`
- `metadata` 增加 case note，明确当前是 teaching-scale SI case

## Solver Changes

当前求解器本身已经支持一般线性稳态导热方程，不需要修改 UFL 形式，只需要：

- 从 state 中读取真实边界温度，而不是默认把冷端解释为 `0.0`
- 保持热源、导热率数值原样进入求解

换句话说，这次核心不是换 PDE，而是给现有 PDE 一组具有一致 SI 语义的输入。

## Visualization Changes

图和文本输出要开始显式显示单位，避免用户误把数值当成无量纲：

- 温度图色条标题显示 `Temperature (degC)`
- 布局图坐标轴显示 `x (m)`、`y (m)`
- summary 文本里显示：
  - `Temperature min/max (degC)`
  - `Conductivity (W/(m*K))` 在笔记中解释
- overview 页面增加简短说明：
  - current case uses SI-style teaching units

## Notes and Teaching Content

新增或更新学习笔记，明确说明：

1. 为什么原来的 `0.2` 约束不适合继续作为工程目标
2. 为什么 `85 degC` 更像芯片结温/热点控制指标
3. 为什么当前热源仍然是“等效体热源”，而不是严格封装功率映射
4. 这套模型适合做：
   - 参数影响分析
   - 约束优化
   - LLM 决策解释
5. 暂时不适合直接做：
   - 工艺签核
   - 真实产品热认证

## Testing Strategy

先写失败测试，再实现：

- state schema/load test:
  - baseline 含 `units` 与 `reference_conditions`
- solver pipeline test:
  - 边界温度不再默认是 `0.0`
- prompt/output-facing tests:
  - 可视化 summary 或 metrics 中带单位信息
- evaluator test:
  - `85.0` 约束下 baseline 初始状态应为不可行或可行，结果要和真实求解一致并可解释

## Risks

- 如果直接把原有热源数值解释成 `W/m^3`，温度水平可能显得偏低或偏高
- 如果只改约束不改说明文档，会造成“看起来更真实，实际上仍不透明”的问题
- 如果单位字段只存储不显示，用户仍然容易误解输出

## Decision

采用“SI 风格教学模型”作为下一阶段默认 baseline，并保留当前闭环优化框架不变。后续若需要更真实物理性，再在此基础上逐步加入对流、界面热阻和功率校准。
