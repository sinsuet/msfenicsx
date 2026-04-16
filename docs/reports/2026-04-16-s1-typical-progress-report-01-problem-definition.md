# 报告一：`s1_typical` 问题定义

Date: 2026-04-16

## 1. 本次汇报要解决的核心问题

本次汇报聚焦当前唯一的 paper-facing 主线问题 `s1_typical`：

> 在一个二维矩形卫星面板上，给定 15 个固定命名组件和一个顶部单段散热窗口，在满足几何合法性与热约束的前提下，联合优化 15 个组件的 `x/y` 位置以及散热窗口区间，共 32 个决策变量，同时降低全局峰值温度 `summary.temperature_max` 与整体温度梯度 `summary.temperature_gradient_rms`。

这不是一个玩具布局问题，而是一个必须经过真实热场求解的双目标优化问题。

## 2. Benchmark 身份

本次汇报中的问题边界固定如下：

| 项目 | 当前定义 |
| --- | --- |
| benchmark | `s1_typical` |
| benchmark case | 单案例 |
| operating case | 单工况 |
| 组件数量 | 15 |
| 散热边界 | 顶部单段 `line_sink` |
| 决策变量数 | 32 |
| 优化目标数 | 2 |
| 对比路线 | `nsga2_raw` / `nsga2_union` / `nsga2_llm` |

这意味着本次比较不是在多个问题实例之间平均，而是在同一个固定 benchmark 上比较三种 proposal/controller 机制。

### 2.1 固定的物理对象是什么

这里的 benchmark 固定的不只是“有 15 个组件”这么简单，而是完整固定了问题对象：

- 面板是 `1.0 x 0.8` 的二维矩形域
- 15 个组件的形状、尺寸、材料身份固定
- 顶边只有一个单段 `line_sink` 作为主散热窗口
- 当前可优化的是 15 个组件的 `x/y` 位置以及 `sink_start / sink_end`
- 所以总决策变量始终是 `15 * 2 + 2 = 32`

也就是说，我们优化的是布局和散热窗口位置，而不是去改组件功率、材料导热率或者环境温度。

### 2.2 十五个热源的具体功率设定

`s1_typical` 也不是“只有一两个热点”的简化问题，而是 15 个组件全部带废热，总热功率固定为 `114.0 W`。各组件热源设定如下：

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

这里的 `source_area_ratio` 不是另一个抽象权重，而是热源在组件内部实际占据的面积比例。相同总功率下：

- `source_area_ratio` 越小，热源越集中，局部热源密度越高
- `source_area_ratio` 越大，热源越分散，热点通常更平缓

因此，`c02 / c04 / c06 / c12` 既功率更高，又热源更集中，通常会主导最强热点和最明显的高梯度带。

## 3. 为什么这个问题已经不是简单示例

### 3.1 空间和热耦合都更复杂

当前布局里同时包含：

- 顶部高热或散热敏感模块
- 中部逻辑/计算模块
- 左右边缘接口模块
- 底部服务、缓冲和敏感模块

它们共用同一块面板和同一个顶部散热窗口，因此会同时面临：

- 空间拥挤与合法性恢复
- 热源间相互耦合
- 组件到散热窗口的相对对齐
- 峰值温度与整体温度梯度之间的真实 trade-off

### 3.2 主散热窗口和背景散热并存

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

关键参数如下：

| 项目 | 当前设定 | 说明 |
| --- | --- | --- |
| 主散热窗口 | top-edge `line_sink` | 顶边单段主散热通道 |
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

因此，这个 benchmark 里的背景散热具有以下性质：

- 它不是和顶部 `line_sink` 平级的第二主散热器
- 它的作用是给非 sink 外边界提供“弱但非零”的环境耦合
- 它防止其余边界被理想化成完全绝热，从而让温度场更接近真实工程中的缓慢泄热
- 真正决定布局优化方向的主散热抓手，仍然是顶部那一段可移动的 `line_sink`

因此，这个 benchmark 的热问题可概括为：

> 顶边窗口负责“强散热”，其余外边界只负责“弱环境泄热”；背景散热存在，但远不足以替代主散热窗口。

### 3.3 每一次评价都不便宜

当前主链不是“随机摆放后直接打分”，而是：

```text
candidate
  -> repair
  -> cheap constraints
  -> PDE solve
  -> evaluation_report
```

其中：

- `repair` 负责把候选投影回合法几何区域
- `cheap constraints` 先过滤明显不值得求解的候选
- 只有通过前两步的候选才会进入昂贵的 PDE 热场求解

所以本次汇报里说“减少评估”，本质上说的是减少达到目标质量所需的昂贵仿真次数。

## 4. 32 维设计变量到底是什么

当前编码固定为：

```text
15 * 2 + 2 = 32
```

具体包含：

- 15 个组件的 `x`
- 15 个组件的 `y`
- `sink_start`
- `sink_end`

当前主线不优化旋转，因此变量语义非常清楚：问题本质上是“组件平面布局 + 单段散热窗口位置/跨度联合优化”。

## 5. 目标和约束

### 5.1 两个优化目标

| objective | metric | 含义 |
| --- | --- | --- |
| 峰值温度最小化 | `summary.temperature_max` | 压低全局最热点 |
| 梯度 RMS 最小化 | `summary.temperature_gradient_rms` | 缓和整体温度梯度 |

这两个目标并不总是同步改善，因此需要用 Pareto 视角看结果。

这里要特别说明，报告里说的“梯度优化”不是对 32 个布局变量做 gradient descent，也不是去求候选解的解析梯度，而是把温度场空间梯度强度作为第二个优化目标。

其正式定义是：

`summary.temperature_gradient_rms = sqrt((1 / |Omega|) * integral_Omega |grad(T_h)|^2 dx)`

它衡量的是整个面板上温度变化有多陡：

- 数值越低，说明温度场越平滑
- 高梯度带越少，局部热应力风险通常越低
- 因而它和 `summary.temperature_max` 一起构成“压低最热点 + 抹平整场温差”的双目标问题

### 5.2 当前硬约束

| constraint | metric | limit |
| --- | --- | --- |
| radiator span budget | `case.total_radiator_span` | `<= 0.48` |
| c01 temperature limit | `component.c01-001.temperature_max` | `<= 356` |
| c08 temperature limit | `component.c08-001.temperature_max` | `<= 352` |
| panel spread limit | `components.max_temperature_spread` | `<= 95` |

因此，一个“好”的方案必须同时满足：

- 合法几何
- 合法散热窗口预算
- 合法关键组件温度
- 合法整板温差

## 6. 初始布局长什么样

下面给出当前 benchmark seed-11 的初始布局和初始热场，它们是三种优化路线共享的出发点。

### 6.1 初始布局

![Initial Layout](beamer/2026-04-16-s1-typical-progress-report/assets/baseline/initial-layout.png)

### 6.2 初始温度场

![Initial Temperature Field](beamer/2026-04-16-s1-typical-progress-report/assets/baseline/initial-temperature-field.png)

### 6.3 初始梯度场

![Initial Gradient Field](beamer/2026-04-16-s1-typical-progress-report/assets/baseline/initial-gradient-field.png)

这一初始状态对应的评价指标为：

| 指标 | 数值 |
| --- | ---: |
| `summary.temperature_max` | `311.163` |
| `summary.temperature_gradient_rms` | `16.953` |
| `case.total_radiator_span` | `0.380` |

这些数值也是后续比较“到底改善了多少”的共同参考点。

## 7. 本次问题定义的结论

本次汇报中的问题可概括为：

> 我们研究的不是“LLM 会不会摆布局”，而是“在同一个 15 组件、32 维、真实 PDE 评价的热布局问题上，谁能更有效地生成下一步候选，并用更少的昂贵仿真达到更好的双目标结果”。

后续三份报告就在这个固定问题定义上展开：

- 报告二解释三种路线为什么可以公平比较
- 报告三解释 LLM controller 实际做了什么
- 报告四给出代表性 `20x10` 对比结果
