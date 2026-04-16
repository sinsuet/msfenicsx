# 报告四：`20x10` 代表性对比实验

Date: 2026-04-16

## 1. 实验目的

本报告用一组代表性的 `20x10` 对比实验回答三个问题：

1. `raw / union / llm` 在同一预算下最终分别得到什么结果
2. 三条路线在布局、温度场和梯度场上有什么直观差别
3. LLM 的优势到底体现在哪里

这里的重点不是泛泛比较平均值，而是给出具体且可核查的对比证据。

## 2. 实验设置

| 项目 | 设置 |
| --- | --- |
| benchmark | `s1_typical` |
| evaluation spec | `s1_typical_eval` |
| `benchmark_seed` | `11` |
| `algorithm.seed` | `7` |
| `population_size` | `20` |
| `num_generations` | `10` |
| 总 evaluations | `201` |

### 2.1 这组 `20x10` 实验到底在优化什么

这里的 `20x10` 只表示搜索预算，不改变 benchmark 本身的物理定义。当前比较始终是在同一个固定问题上完成：

- 面板是 `1.0 x 0.8` 的二维矩形域
- 15 个组件的形状、尺寸、材料身份固定
- 可优化的是 15 个组件的 `x/y` 位置以及顶部单段散热窗口的 `start/end`
- 因此总决策变量仍然是 `15 * 2 + 2 = 32`

也就是说，这里不是在优化组件功率、材料参数或环境温度，而是在固定热载荷和固定边界物理下，比较谁更会用同样的评估预算把布局和散热窗口调到更好的位置。

### 2.2 十五个热源的具体功率设定

`s1_typical` 不是“只有少数几个热点”的简化例子，而是 15 个组件全部带废热，总热功率为 `114.0 W`。各组件热源设定如下：

| 组件 | 角色 | `total_power` | `source_area_ratio` |
| --- | --- | ---: | ---: |
| `c01` | `logic_board_01` | `8.5 W` | `0.28` |
| `c02` | `power_module_01` | `14.0 W` | `0.12` |
| `c03` | `logic_board_02` | `8.0 W` | `0.30` |
| `c04` | `power_module_02` | `13.0 W` | `0.13` |
| `c05` | `service_board_01` | `6.5 W` | `0.34` |
| `c06` | `power_module_03` | `12.5 W` | `0.14` |
| `c07` | `logic_board_03` | `7.0 W` | `0.32` |
| `c08` | `io_board_01` | `6.5 W` | `0.30` |
| `c09` | `io_board_02` | `6.0 W` | `0.30` |
| `c10` | `battery_module` | `5.5 W` | `0.24` |
| `c11` | `edge_connector_left` | `4.5 W` | `0.40` |
| `c12` | `sink_side_bus` | `11.0 W` | `0.18` |
| `c13` | `harness_capsule` | `4.0 W` | `0.42` |
| `c14` | `rounded_sensor_pack_01` | `3.5 W` | `0.48` |
| `c15` | `rounded_sensor_pack_02` | `3.5 W` | `0.46` |

这里要特别说明，`source_area_ratio` 不是另一个“权重”，而是热源在组件内部真正占据的面积比例。相同总功率下：

- `source_area_ratio` 越小，热源越集中，局部热源密度越高
- `source_area_ratio` 越大，热源越分散，热点通常更平缓

因此，`c02 / c04 / c06 / c12` 不只是功率大，而且热源更集中，所以它们通常会主导最强热点与高梯度带的形成。

### 2.3 散热边界、环境温度和背景辐射

当前求解的不是纯绝热板，而是“顶部主散热窗口 + 其余外边界弱背景散热”共同作用的稳态导热问题。这里最容易混淆的是：背景散热到底作用在哪、强度有多大、和顶部主散热窗口是什么关系。

先按求解器口径把整个外边界分成两类：

- `Γ_sink`：顶部被选中的那一段 `line_sink`
- `Γ_bg`：除 `Γ_sink` 之外的所有外边界

这意味着 `Γ_bg` 实际上包括：

- 顶边里不属于散热窗口的其余部分
- 左边界
- 右边界
- 底边

也就是说，背景散热不是组件内部额外加的一圈小散热器，也不是第二个可优化散热窗口，它只是“非主散热窗口外边界与环境之间的微弱热交换”。

对应到边界热流表达式，可以把它写成：

```text
Γ_sink: q_out = h_sink * (T - T_sink) + ε_sink * σ * (T^4 - T_sink^4)
Γ_bg:   q_out = h_bg   * (T - T_amb ) + ε_bg   * σ * (T^4 - T_amb^4)
```

其中：

- `Γ_sink` 是主散热窗口，负责主要热量抽取
- `Γ_bg` 是弱环境耦合，避免其余边界被理想化成完全绝热
- 这里的 `T_amb` 同时也是背景辐射项使用的参考温度
- 当前实现里没有单独的 `background_radiation_temperature`

关键物理设定如下：

| 项目 | 当前设定 | 说明 |
| --- | --- | --- |
| 主散热窗口 | top-edge `line_sink` | 顶边单段主散热通道 |
| sink span family | `0.31` 到 `0.69` | 模板允许的窗口跨度范围 |
| hard budget | `case.total_radiator_span <= 0.48` | 优化阶段必须满足的散热窗口预算 |
| sink temperature | `286 K` | 主冷源温度 |
| sink transfer coefficient | `10.0` | 主散热窗口线性换热强度 |
| ambient temperature | `292 K` | 外部环境温度 |
| background radiation reference temperature | `292 K` | 当前与 `ambient temperature` 相同，背景辐射直接参考 `T_amb` |
| background transfer coefficient | `0.15` | 非 sink 边界上的弱背景换热 |
| background emissivity | `0.08` | 非 sink 边界上的弱背景辐射项 |
| sink emissivity | `0.78` | 当前未给 sink 单独 emissivity，默认继承 panel substrate |
| Stefan-Boltzmann constant | `5.670374419e-8` | 辐射四次项中的 `σ` |
| panel substrate | `conductivity = 3.0`, `emissivity = 0.78` | 面板基底材料 |
| electronics housing | `conductivity = 12.0`, `emissivity = 0.82` | 组件材料 |

这里可以再说得更直白一点：

- 背景换热项看的是 `T - 292 K`
- 背景辐射项看的是 `T^4 - (292 K)^4`
- 它们共享同一个环境参考温度 `292 K`

所以当前模型里，“环境温度”和“背景辐射参考温度”并不是两个独立旋钮，而是同一个 `ambient_temperature = 292 K` 同时进入了背景对流项和背景辐射项。

从这个表里可以直接看出，背景散热比主散热窗口弱很多：

- 线性换热系数只有 `0.15`，而主散热窗口是 `10.0`
- 仅看线性项系数，背景散热只有主散热窗口的 `1.5%`
- 背景辐射 emissivity 只有 `0.08`，而主散热窗口默认是 `0.78`
- 同时环境温度 `292 K` 也高于主冷源 `286 K`，所以背景边界的温差驱动力更小

如果拿一个代表性的边界温度 `T = 310 K` 做直觉比较，只看线性项就有：

- 主散热窗口：`10.0 * (310 - 286) = 240`
- 背景散热：`0.15 * (310 - 292) = 2.7`

也就是说，在线性部分上，背景散热大约只有主散热窗口的 `1/89`。再考虑到背景辐射 emissivity 更低，它在整体上仍然只是一个明显更弱的泄热通道。

因此，这组实验里的背景散热具有以下性质：

- 它不是和顶部 `line_sink` 平级的第二主散热器
- 它的作用是给非 sink 外边界提供“弱但非零”的环境耦合
- 它防止其余边界被理想化成完全绝热，从而让温度场更接近真实工程中的缓慢泄热
- 真正决定布局优化方向的主散热抓手，仍然是顶部那一段可移动的 `line_sink`

所以这组实验里可以直接把散热问题理解成：

> 顶边窗口负责“强散热”，其余外边界只负责“弱环境泄热”；背景散热存在，但远不足以替代主散热窗口。

### 2.4 “梯度优化”在这里的严格定义

这里说的“梯度优化”不是对 32 个布局变量做 gradient descent，也不是对候选解求解析梯度，而是把温度场空间梯度强度作为第二个优化目标。

官方目标定义是：

`summary.temperature_gradient_rms = sqrt((1 / |Omega|) * integral_Omega |grad(T_h)|^2 dx)`

它的含义是：

- 度量整个面板上温度变化有多陡
- 数值越低，说明温度场越平滑，高梯度带越少
- 通常意味着局部热应力风险和冷热分区撕裂感更低

因此，报告里的梯度场图展示的是 `|grad(T)|` 的空间分布，而表格里的 `grad_rms` 是这张场图对应的全局 RMS 汇总值。换句话说，本实验优化的是“压低最热点 + 抹平整场温差”，而不是只盯着一个局部最冷点。

对应的证据路径为：

| 模式 | 路径 |
| --- | --- |
| `raw` | `0415_2352__raw_union/raw/seeds/seed-11` |
| `union` | `0415_2352__raw_union/union/seeds/seed-11` |
| `llm` | `0416_0110__llm` |

## 3. 结论先行

这组实验的核心结论是：

> 在相同 `20x10` 总预算下，`llm` 的 knee 代表解同时优于 raw 和 union 的最终 knee 代表解，而且它在第 108 次评估时就已经达到 raw / union 最终 knee 所在的平衡质量区域。

也就是说，本次 LLM 优势的正确表述不是“总预算更小”，而是：

> 在相同总预算内，LLM 更早把昂贵评估用到了有效方向上，因此减少了达到同等效果所需的昂贵仿真次数。

## 4. 从初始状态到三种最终布局

### 4.1 初始布局

![Initial Layout](beamer/2026-04-16-s1-typical-progress-report/assets/baseline/initial-layout.png)

### 4.2 `raw / union / llm` 的最终 knee 布局

![Raw Knee Layout](beamer/2026-04-16-s1-typical-progress-report/assets/layouts/raw-knee-layout.png)

![Union Knee Layout](beamer/2026-04-16-s1-typical-progress-report/assets/layouts/union-knee-layout.png)

![LLM Knee Layout](beamer/2026-04-16-s1-typical-progress-report/assets/layouts/llm-knee-layout.png)

从布局上可以直观看到：

- 三条路线都明显改变了初始热点组织方式
- 三条路线都把布局调整成更贴合顶部散热窗口的形态
- 但 `llm` 的最终 knee 方案更接近“既压低热点，又不把整体梯度留得太高”的平衡结构

## 5. 三种最终温度场与梯度场

### 5.1 温度场对比

![Temperature Fields](beamer/2026-04-16-s1-typical-progress-report/assets/fields/comparison-temperature-fields.png)

### 5.2 梯度场对比

![Gradient Fields](beamer/2026-04-16-s1-typical-progress-report/assets/fields/comparison-gradient-fields.png)

这两张图要表达的重点是：

- `raw` 和 `union` 已经显著优于初始状态
- `llm` 的 balanced knee 方案不仅没有牺牲峰值温度，反而把温度场和梯度场都进一步压低
- 因为三路图使用同一色标，所以这里看到的差别是可以直接比较的

## 6. 关键数值对比

### 6.1 初始状态 vs 最终 knee

| 方案 | `T_max` | `grad_rms` | radiator span |
| --- | ---: | ---: | ---: |
| 初始状态 | `311.163` | `16.953` | `0.380` |
| raw knee | `306.520` | `12.597` | `0.480` |
| union knee | `306.459` | `12.807` | `0.480` |
| llm knee | `305.095` | `11.939` | `0.479` |

如果以初始状态为参考，`llm knee` 的改善幅度是：

- 峰值温度下降 `6.068`
- 梯度 RMS 下降 `5.014`

并且它在两个目标上都同时优于 raw 和 union 的最终 knee。

### 6.2 从初始状态实际下降了多少

如果关注“到底降了多少”，那么比起只看最终数值差，更合适的是直接看三条路线相对初始状态的实际下降幅度。

#### 6.2.1 峰值温度

| 方案 | 最终 `T_max` | 相对初始下降 | 相对 raw 下降幅度 |
| --- | ---: | ---: | ---: |
| raw | `306.520` | `4.642` | `1.00x` |
| union | `306.459` | `4.703` | `1.01x` |
| llm | `305.095` | `6.068` | `1.31x` |

这意味着：

- `llm` 的峰值温度下降幅度不是只比 `raw`“再低一点”，而是达到了 `1.31x raw`
- 换成更直观的话说，就是 `llm` 比 `raw` 多实现了约 `30.7%` 的温度下降幅度

#### 6.2.2 梯度 RMS

| 方案 | 最终 `grad_rms` | 相对初始下降 | 相对 raw 下降幅度 |
| --- | ---: | ---: | ---: |
| raw | `12.597` | `4.356` | `1.00x` |
| union | `12.807` | `4.146` | `0.95x` |
| llm | `11.939` | `5.014` | `1.15x` |

这意味着：

- `llm` 的梯度下降幅度达到了 `1.15x raw`
- 也就是相对 `raw`，它多实现了约 `15.1%` 的梯度下降幅度

因此，这一结果可表述为：

> 从同一个初始状态出发，`llm final knee` 在峰值温度上实现了 `1.31x raw` 的下降幅度，在梯度 RMS 上实现了 `1.15x raw` 的下降幅度。

### 6.3 各自最强方向

| 方案 | 代表点 | `T_max` | `grad_rms` |
| --- | --- | ---: | ---: |
| raw | `min-peak-temperature` | `306.315` | `13.276` |
| union | `min-peak-temperature` | `305.688` | `13.691` |
| llm | `min-temperature-gradient-rms` | `317.440` | `10.690` |

这张表说明：

- `union` 当前最强的单点优势仍然是峰值温度极值
- `llm` 当前最强的单点优势仍然是梯度极值
- 但在 balanced 代表点上，这次 `0416_0110__llm` 已经给出了更好的综合结果

## 7. 下降曲线：谁更早达到有效区域

### 7.1 峰值温度 best-so-far

![Best Peak vs Eval](beamer/2026-04-16-s1-typical-progress-report/assets/charts/best-peak-vs-eval.png)

### 7.2 梯度 RMS best-so-far

![Best Gradient vs Eval](beamer/2026-04-16-s1-typical-progress-report/assets/charts/best-gradient-vs-eval.png)

这两条曲线的关键节点是第 108 次评估：

- `llm` 在 `eval = 108` 时已经达到 `305.431 / 12.597`
- 这已经优于 raw 最终 knee 的 `306.520 / 12.597`
- 也已经优于 union 最终 knee 的 `306.459 / 12.807`

所以，如果把“达到 raw / union 最终 knee 质量”作为目标，那么：

| 目标质量 | 基线所需 eval | `llm` 所需 eval | `llm / baseline` | 节省 eval |
| --- | ---: | ---: | ---: | ---: |
| raw 最终 knee 质量 | `175` | `108` | `61.71%` | `67` (`38.29%`) |
| union 最终 knee 质量 | `161` | `108` | `67.08%` | `53` (`32.92%`) |

这就是本次汇报中“减少昂贵仿真”的最直接证据。

另外，收敛图前段里 `raw` 看起来像“断掉”的视觉现象，并不是缺数据，而是 early `best-so-far` 曲线发生了重合：

- `raw` 与 `union` 在前 `20` 次评估上完全相同
- `raw` 与 `llm` 在前 `42` 次评估上完全相同

因此，前段 `raw` 线条之所以不明显，是因为它被重合曲线覆盖，而不是实验没有跑出来。

## 8. 为什么这个结果能体现 LLM 价值

这里要特别避免把结论说得太虚。当前能明确说的是：

### 8.1 不是因为 LLM 有额外动作特权

`union` 和 `llm` 使用同一套动作池，所以 LLM 的优势不能归因于“它有更多操作权限”。

### 8.2 是因为 LLM 更早进入了有效决策区间

从真实 trace 看，`llm` 在 `eval = 108` 时通过一次具体的 `local_refine` 选择，把解推进到 raw / union 最终 knee 所在区域。

这说明它的价值主要体现在：

- 更快识别当前 phase
- 更快识别哪些动作更可能改善当前瓶颈
- 更快把评估预算转化成有效 frontier 改善

### 8.3 当前 strongest claim 是 balanced quality earlier

因此，当前最稳妥且最有说服力的表述是：

> 在相同 `20x10` 总预算下，LLM 已经展示出更早达到同等或更优 balanced 结果的能力，从而降低了达到该结果所需的昂贵 PDE 评估数。

## 9. 这组实验还没有声称什么

本次结果并不意味着：

- LLM 在所有代表点上都全面最优
- LLM 的总预算已经可以缩到更小并保持同样结论
- 后续 objective-balance 工作已经完成

本次结果只支持一个更准确的阶段性结论：

> 当前 `0416_0110__llm` 已经证明 LLM controller 不仅能工作，而且能在 balanced knee 区域优于 raw / union，并更早达到这种结果。

## 10. 本报告的结论

本报告的核心结论是：

> 同样是 `s1_typical`、同样是 `20x10`、同样是 201 次总评估，LLM 已经在第 108 次评估时达到 raw / union 最终 knee 区域，并最终给出更好的 balanced knee 解，这就是它当前最有说服力的工程价值。
