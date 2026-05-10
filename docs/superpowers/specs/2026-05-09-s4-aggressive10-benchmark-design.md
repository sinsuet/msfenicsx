# S4 Aggressive10 Benchmark Design

## 目标

新增 `s4_aggressive10` 作为 S4/S5/S6 paper-facing ladder 的低维场景。它降低主实验的低维校准压力，同时保留 `raw / union / llm` 语义控制对比所需的布局、sink 与热瓶颈结构。

## 场景契约

- 固定单 case，不定义 `operating_case_profiles`。
- 组件数量为 10，全部固定命名为 `c01` 到 `c10`。
- 决策变量为 22D：10 个组件的 `x/y` 加 `sink_start/sink_end`。
- panel 沿用 `width=1.0, height=0.8`，顶部保留 harness keep-out strip。
- 热物理、材料、mesh 与 S5 主线保持一致，降低新场景引入额外 solver 差异的风险。

## 热布局设计

S4 不是简单稀疏场景。组件面积目标约为 active placement region 的 `0.27-0.31`，总热载约 `101.5 W`。组件构成包含一个主核心、两个主电源、一个逻辑板、一个服务缓冲、一个 sink-coupled bus、两个 IO shoulder、一个下部热质量和一个低功耗传感器。

该结构保留三类优化压力：

- `primary-hot-cluster`：`c01/c02/c03/c04` 形成紧凑主热点。
- `sink-lane`：`c06` 作为长条 sink-coupled bus，对 sink 位置和长度敏感。
- `io/support`：边缘 IO 与下部 thermal mass 形成布局拥挤和梯度平衡压力。

## 评价与优化

评价目标沿用 S4/S5/S6：

- `summary.temperature_max`
- `summary.temperature_gradient_rms`

硬约束包括 `case.total_radiator_span <= 0.32`，以及 `c01/c02/c04/c06` 的峰值温度约束。温度阈值是初始设计值，后续需要通过 seed-11 solve/evaluate 与 32x16 benchmark 结果校准。

优化配置包括：

- `s4_aggressive10_raw.yaml`
- `s4_aggressive10_union.yaml`
- `s4_aggressive10_llm.yaml`

三者共享 `projection_plus_local_restore`、相同 22D 编码和 `population_size=32, num_generations=16`。`union` 和 `llm` 使用同一 `primitive_structured` operator pool；`llm` 初始运行指定 `deepseek_v4_flash` profile。

## 验证

新增 focused tests 覆盖 template contract、seed-11 generation、optimization specs、evaluation spec 和 profile resolution。执行前先观察 RED 失败，再生成配置并运行 focused tests。
