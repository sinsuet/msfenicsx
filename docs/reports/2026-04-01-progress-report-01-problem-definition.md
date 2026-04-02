# 报告一：主线问题定义与热优化建模

Date: 2026-04-01

## 1. 报告目的

本报告用于把 `msfenicsx` 当前论文主线中的“问题到底是什么”讲清楚，并把主线场景的建模对象、参数、约束、多目标定义和从模板到优化的完整建模链条固定下来，作为后续三篇方法与实验报告以及 LaTeX Beamer 汇报的基础材料。

本报告只讨论当前 paper-facing 主线：

- 主线 benchmark template：
  - `scenarios/templates/panel_four_component_hot_cold_benchmark.yaml`
- 主线 multicase evaluation spec：
  - `scenarios/evaluation/panel_four_component_hot_cold_baseline.yaml`
- 主线 classical raw baseline：
  - `scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml`

## 2. 一句话问题定义

我们要解决的问题是：

在一个二维矩形卫星面板上，给定四个具有不同热角色的器件和一个顶部 radiator 边界散热段，在共享几何布局、但 hot/cold 两个工况不同的前提下，联合优化关键器件位置与 radiator 区间，使系统同时满足热约束，并在 hot 工况高热器件峰值温度、cold 工况电池最低温度以及 radiator 资源占用三者之间取得更优 Pareto 折中。

这不是单工况、单目标，也不是一个便宜的解析优化问题，而是一个：

- 几何合法性受约束的问题
- 物理求解开销昂贵的问题
- 需要 hot/cold 双工况同时成立的问题
- 具有显式 Pareto trade-off 的多目标问题

## 3. 规范对象与主线数据流

当前平台的规范对象流固定为：

```text
scenario_template
  -> thermal_case
  -> thermal_solution
  -> evaluation_report
  -> optimization_result
```

对应含义如下：

| 对象 | 作用 | 主字段 |
| --- | --- | --- |
| `scenario_template` | 定义几何域、组件族、边界特征族、材料、工况模板、mesh 和 solver 缺省设置 | `component_families`、`boundary_feature_families`、`operating_case_profiles` |
| `thermal_case` | 由模板实例化出的单个工况热问题输入 | `components`、`boundary_features`、`loads`、`physics` |
| `thermal_solution` | FEniCSx 求解后的数值结果 | `solver_diagnostics`、`summary_metrics`、`component_summaries` |
| `evaluation_report` | 按 evaluation spec 从 case + solution 提取目标与约束 | `objective_summary`、`constraint_reports` |
| `optimization_result` | 对一批候选设计完成多目标搜索后的总结工件 | `pareto_front`、`representative_candidates`、`aggregate_metrics` |

对当前主线而言，真正进入优化器的不是单个 `thermal_case`，而是“共享布局 + hot/cold 成对 operating cases”的 multicase 评价链：

```text
scenario_template
  -> sampled layout
  -> hot thermal_case + cold thermal_case
  -> hot thermal_solution + cold thermal_solution
  -> multicase evaluation_report
  -> Pareto optimization
```

## 4. 主线 benchmark 场景定义

### 4.1 面板域与空间约束

主线场景是一个二维矩形面板，所有组件都布局在同一个 `panel_xy` 平面内。

| 项目 | 数值/定义 | 说明 |
| --- | --- | --- |
| 面板宽度 | `1.0` | 归一化后的长度尺度 |
| 面板高度 | `0.8` | 归一化后的高度尺度 |
| 坐标系 | `panel_xy` | 所有组件 `pose.x / pose.y` 都在该平面中定义 |
| 主放置区 | `x∈[0.05, 0.95], y∈[0.05, 0.72]` | 组件默认只能在主甲板区域中布局 |
| 禁布区 | 顶部线束带 `x∈[0.0,1.0], y∈[0.74,0.80]` | 用来阻止组件贴到顶部边缘，与上边界散热结构形成区分 |

这意味着：

1. 面板顶部并不是完全可放置的自由空间。
2. 组件不能越界。
3. 组件不能进入 keep-out 区。
4. 组件之间不能重叠。

这些几何合法性约束不是“汇报里的人为规定”，而是会被 `layout_engine` 和 `case_contracts` 真正检查的运行时约束。

### 4.2 组件族定义

当前主线 benchmark 固定包含四类组件，每类正好一个实例，因此这是一个“四组件、固定角色、可变布局”的主线问题。

| 组件族 | 角色 | 数量 | 形状 | 几何参数范围 | 材料 | 热标签 |
| --- | --- | --- | --- | --- | --- | --- |
| `processor` | 处理器 | 1 | 矩形 | `width∈[0.14,0.18]`, `height∈[0.09,0.12]` | `electronics_housing` | `processor` |
| `rf_power_amp` | 射频功放 | 1 | 矩形 | `width∈[0.12,0.16]`, `height∈[0.08,0.11]` | `electronics_housing` | `rf_power_amp` |
| `obc` | 星载计算机 | 1 | 矩形 | `width∈[0.10,0.14]`, `height∈[0.07,0.10]` | `electronics_housing` | `obc` |
| `battery_pack` | 电池包 | 1 | 矩形 | `width∈[0.14,0.18]`, `height∈[0.10,0.13]` | `battery_insulated_housing` | `battery_pack` |

四个角色在热设计中的含义并不相同：

- `processor` 和 `rf_power_amp` 是 hot 工况下的主要热压力来源。
- `battery_pack` 是 cold 工况下最敏感的生存部件。
- `obc` 既提供背景热耦合，也避免场景退化成“只有两个热点 + 一个 radiator”的过度简化问题。

### 4.3 边界散热特征定义

除了组件之外，主线 benchmark 还包含一个顶部 radiator 型边界特征族。

| 项目 | 数值/定义 | 说明 |
| --- | --- | --- |
| 特征族 ID | `radiator-top` | 顶部边界散热段 |
| 类型 | `line_sink` | 沿边界线段定义 sink 条件 |
| 所在边 | `top` | 面板上边界 |
| 缺省 span | `start=0.25`, `end=0.75` | 模板族定义的初始可实例化区段 |
| 缺省 sink temperature | `286.0` | 模板级缺省值 |
| 缺省 transfer coefficient | `10.0` | 模板级缺省值 |

这里的 `start` 和 `end` 是沿边界归一化坐标定义的无量纲区间。对于 `top` 边界，它们最终会乘以 panel width 映射到真实边界位置。

### 4.4 材料参数

当前主线场景使用三类材料参数：

| 材料 ID | 导热系数 | 发射率 | 作用对象 |
| --- | --- | --- | --- |
| `panel_substrate` | `25.0` | `0.78` | 面板基底 |
| `electronics_housing` | `160.0` | `0.82` | processor / rf_power_amp / obc |
| `battery_insulated_housing` | `45.0` | `0.88` | battery_pack |

这些参数使问题至少具有以下物理区分：

- 面板基底的导热能力明显低于电子壳体；
- 电池包材料导热性能低于普通电子壳体，强化了 cold 工况下的保温敏感性；
- 发射率差异会影响 boundary sink 作用下的温度分布。

## 5. 双工况 operating cases 定义

主线 benchmark 不是把 hot 和 cold 当作两个完全无关的问题，而是：

- 共享同一个布局
- 共享同一组组件几何
- 共享同一个 radiator 边界特征实例
- 只在工况参数、载荷和边界覆盖值上不同

### 5.1 Hot 工况

| 项目 | 数值 |
| --- | --- |
| 环境温度 | `315.0` |
| processor 功率 | `96.0` |
| rf_power_amp 功率 | `80.0` |
| obc 功率 | `20.0` |
| battery_pack 功率 | `4.0` |
| radiator sink temperature | `305.0` |
| radiator transfer coefficient | `4.0` |

hot 工况的物理含义是：

- 环境更热
- 边界 sink 更弱
- 高功耗器件发热更大
- 系统更容易触发 hot-side 温度上限和组件间温差约束

### 5.2 Cold 工况

| 项目 | 数值 |
| --- | --- |
| 环境温度 | `255.0` |
| processor 功率 | `32.0` |
| rf_power_amp 功率 | `24.0` |
| obc 功率 | `8.0` |
| battery_pack 功率 | `1.0` |
| radiator sink temperature | `248.0` |
| radiator transfer coefficient | `10.0` |

cold 工况的物理含义是：

- 环境更冷
- 边界 sink 更强
- 整体内热源显著减弱
- battery 更容易跌破最低允许温度

### 5.3 双工况耦合的意义

这两个工况的耦合构成了整个问题的核心张力：

- 把热点更靠近 radiator，通常有利于 hot 工况；
- 但同样的散热资源加强，往往会降低 cold 工况下 battery 的最低温度；
- 更大的 radiator span 可能帮助热器件降温，却会增加资源占用并削弱 cold 生存性。

所以这是一个天然的冲突性 Pareto 问题，而不是简单的“找一个最冷的布局”。

## 6. 从模板到可求解 `thermal_case`

### 6.1 参数采样

模板实例化首先通过 `sample_template_parameters` 完成：

- 对每个组件族采样几何尺寸；
- 构造材料字典；
- 生成边界特征族的可实例化参数；
- 记录 mesh、solver、generation 相关配置。

当前主线里，组件的 `width / height` 会按给定区间采样；组件数量固定为 1；边界特征族先形成一个可实例化的 `line_sink` 对象，后续再由 operating case 覆写工况相关参数，再由优化变量调整其区间位置。

### 6.2 组件布局

组件布局由 `place_components` 完成，布局时必须同时满足：

1. 组件完全位于 `panel_domain` 内；
2. 组件完全位于允许放置区域内；
3. 组件不落入 keep-out 区；
4. 任意两个组件不重叠；
5. 若多次尝试仍不合法，则布局生成失败。

因此，布局合法性不是优化后才检查，而是在 case 生成阶段和 repair 后都会被维护。

### 6.3 边界特征综合

边界特征由 `synthesize_boundary_features` 综合为带 `feature_id` 的实例，例如：

- `radiator-top-001`

后续 hot/cold 两个工况会对这个同名特征施加不同的：

- `sink_temperature`
- `transfer_coefficient`

### 6.4 operating case 构造

`build_operating_case` 会把共享布局转换成单个工况下的 `thermal_case`，其主要字段如下：

| 字段 | 作用 |
| --- | --- |
| `components` | 组件位置、几何、材料、热标签 |
| `boundary_features` | 边界散热段及其工况参数 |
| `loads` | 每个组件在该工况下的总功率 |
| `physics` | 环境温度和 Stefan-Boltzmann 常数 |
| `mesh_profile` | 网格配置 |
| `solver_profile` | 非线性求解器配置 |
| `provenance` | 来源模板、生成 seed 和工况 ID |

## 7. 主线 8 维设计变量编码

当前论文主线并没有直接把所有组件和所有物理参数都暴露给优化器，而是固定为 8 维设计变量：

| 变量 | 路径 | 下界 | 上界 | 物理意义 |
| --- | --- | --- | --- | --- |
| `processor_x` | `components[0].pose.x` | `0.12` | `0.88` | 处理器中心 x 位置 |
| `processor_y` | `components[0].pose.y` | `0.12` | `0.66` | 处理器中心 y 位置 |
| `rf_power_amp_x` | `components[1].pose.x` | `0.12` | `0.88` | 功放中心 x 位置 |
| `rf_power_amp_y` | `components[1].pose.y` | `0.12` | `0.66` | 功放中心 y 位置 |
| `battery_pack_x` | `components[3].pose.x` | `0.12` | `0.88` | 电池中心 x 位置 |
| `battery_pack_y` | `components[3].pose.y` | `0.12` | `0.66` | 电池中心 y 位置 |
| `radiator_start` | `boundary_features[0].start` | `0.05` | `0.70` | radiator 左端点 |
| `radiator_end` | `boundary_features[0].end` | `0.20` | `0.95` | radiator 右端点 |

几个设计选择值得强调：

1. `obc` 在第一阶段 benchmark 中保持固定，不进入优化变量。
2. 三个可移动组件共同决定热源布局。
3. radiator 通过区间起止点建模，而不是中心/宽度建模，这更贴合当前 case schema。
4. 变量上下界比 placement region 更保守，这是为了给组件尺寸、repair 和几何合法性留出缓冲。

## 8. 多目标优化问题定义

当前主线优化是一个三目标问题：

### 8.1 目标函数

| 目标 ID | 所属工况 | 指标 | 优化方向 | 含义 |
| --- | --- | --- | --- | --- |
| `minimize_hot_pa_peak` | hot | `component.rf_power_amp.temperature_max` | 最小化 | 降低 hot 工况下功放峰值温度 |
| `maximize_cold_battery_min` | cold | `component.battery_pack.temperature_min` | 最大化 | 提高 cold 工况下电池最低温度 |
| `minimize_radiator_resource` | hot | `case.total_radiator_span` | 最小化 | 尽量减少 radiator 资源占用 |

因此，数学上可以写成：

```text
min f1(x) = T_hot_max(rf_power_amp)
max f2(x) = T_cold_min(battery_pack)
min f3(x) = radiator_span(x)
```

其中 `x` 是 8 维设计变量向量。

需要注意：

- 科学定义里第二个目标是“最大化电池最低温度”；
- 在优化器内部做 Pareto 比较时，会把 maximize 目标转换成等价的 minimization 形式；
- 但汇报和论文写作时，应始终保留其原始工程意义，即“尽量让 cold battery 不要太冷”。

### 8.2 约束条件

当前主线使用 4 个热约束：

| 约束 ID | 工况 | 指标 | 关系 | 阈值 | 工程含义 |
| --- | --- | --- | --- | --- | --- |
| `hot_pa_limit` | hot | `component.rf_power_amp.temperature_max` | `<=` | `355.0` | hot 功放温度不能过高 |
| `hot_processor_limit` | hot | `component.processor.temperature_max` | `<=` | `350.0` | hot 处理器温度不能过高 |
| `cold_battery_floor` | cold | `component.battery_pack.temperature_min` | `>=` | `259.5` | cold 电池最低温度不能过低 |
| `hot_component_spread_limit` | hot | `components.max_temperature_spread` | `<=` | `1.0` | hot 工况下组件间平均温度差不能过大 |

其中：

- `components.max_temperature_spread` 的定义不是“最大温度减最小温度”，而是“各组件平均温度中的最大值减最小值”；
- 该约束用于抑制局部器件之间过大的热不均匀性；
- 所有约束必须同时满足，候选解才被视为 feasible。

### 8.3 几何合法性约束

除了显式热约束外，还存在隐式几何合法性约束：

1. 组件不能越出面板；
2. 组件不能重叠；
3. 组件不能进入 keep-out 区；
4. `radiator_start < radiator_end` 且需满足最小有效 span；
5. repair 后的 case 必须通过运行时 geometry contract。

这些约束决定了问题不仅是 thermal-constrained，也是 geometry-constrained。

## 9. 物理与数值模型

### 9.1 热传导模型

当前求解器采用二维稳态导热模型，并在 radiator 边界段上施加线性换热项和辐射型非线性 sink 项。

可以用如下形式理解：

```text
-∇·(k(x) ∇T) = q(x)    in panel domain
```

其中：

- `k(x)` 是空间变化的导热系数场；
- 面板基底和各器件区域可具有不同材料参数；
- `q(x)` 是由组件总功率除以组件面积得到的面热源密度。

在 line sink 边界段上，残量中额外加入：

```text
h (T - T_sink) + εσ (T^4 - T_sink^4)
```

这意味着 radiator 并不是单纯的常温 Dirichlet 边界，而是一个带线性换热与非线性辐射项的散热边界。

### 9.2 材料与源项映射

求解阶段会把 `thermal_case` 映射成数值场：

- 导热系数场由 `panel_material_ref` 和各组件 `material_ref` 决定；
- 热源场由 `loads.total_power / component.area` 决定；
- radiator 边界段由 `feature_id` 和 `start/end/edge` 定位；
- 环境温度用作初值和物理参数之一。

### 9.3 网格与求解器

主线 benchmark 当前使用：

| 项目 | 数值 |
| --- | --- |
| `mesh_profile.nx` | `48` |
| `mesh_profile.ny` | `40` |
| 有限元空间 | `Lagrange, degree=1` |
| 非线性求解器 | `SNES` |
| 绝对容差 | `1e-8` |
| 相对容差 | `1e-8` |
| 最大迭代数 | `50` |

因此，每一次候选设计的 evaluation 都会触发两次真实的 FEniCSx 非线性求解：

- 一次 hot
- 一次 cold

### 9.4 `thermal_solution` 中保存什么

求解完成后，`thermal_solution` 至少保存：

- `solver_diagnostics`：
  - 是否收敛
  - 迭代次数
  - 求解器名称
- `field_records`：
  - 温度场自由度信息
- `summary_metrics`：
  - `temperature_min`
  - `temperature_mean`
  - `temperature_max`
- `component_summaries`：
  - 每个组件的 `temperature_min / mean / max`

这使得后续 evaluation 可以只依赖 `case + solution`，而不需要重新求解。

## 10. 从 `thermal_solution` 到 multicase `evaluation_report`

### 10.1 指标解析命名空间

当前 evaluation 层支持的指标命名空间主要有：

| 命名空间 | 例子 | 来源 |
| --- | --- | --- |
| `summary.*` | `summary.temperature_max` | 全场汇总指标 |
| `solver.*` | `solver.iterations` | 求解器诊断 |
| `component.<role_or_id>.*` | `component.rf_power_amp.temperature_max` | 组件级统计 |
| `components.*` | `components.max_temperature_spread` | 跨组件派生统计 |
| `case.*` | `case.total_radiator_span` | 从 `thermal_case` 派生的几何/载荷指标 |

### 10.2 单工况评价

单工况评价会把：

- `thermal_case`
- `thermal_solution`
- `evaluation_spec`

组合成一个 `EvaluationReport`，输出：

- `metric_values`
- `objective_summary`
- `constraint_reports`
- `violations`
- `derived_signals`

### 10.3 双工况聚合

multicase engine 会进一步把 hot/cold 两个单工况报告聚合成一个 `MultiCaseEvaluationReport`，并形成：

- 总体 `feasible`
- hot/cold 的分工况 `case_reports`
- 跨工况 `objective_summary`
- 跨工况 `constraint_reports`
- `worst_case_signals`

只有当四个约束全部满足时，该候选设计才被认定为 feasible。

## 11. 为什么这是一个昂贵的约束多目标 multicase 优化问题

这个问题之所以难，不仅因为目标多，还因为每次评估都贵。

### 11.1 昂贵性

一次候选设计评估至少包含：

1. 将 8 维设计变量写回 case；
2. 进行 bounds 和几何 repair；
3. 构造 hot `thermal_case`；
4. 构造 cold `thermal_case`；
5. 求解 hot PDE；
6. 求解 cold PDE；
7. 抽取组件和全局温度指标；
8. 聚合为 multicase 约束与目标值。

例如当前标准预算 `population_size=16, num_generations=8` 对应单次 run 的 `129` 次候选评估；由于每次评估都要求解 hot/cold 两个工况，因此大致对应 `258` 次真实热求解。

### 11.2 多目标冲突性

三个目标之间天然冲突：

- 减小 `hot_pa_peak` 往往要求热点更靠近 radiator 或扩大 radiator span；
- 提高 `cold_battery_min` 往往要求减少 cold 工况下的散热强度或让 battery 更靠近热区；
- 减少 `radiator_resource` 则要求尽可能缩短 radiator span。

这三者不存在一个显然的单点最优解，而是形成 Pareto 前沿。

### 11.3 约束耦合性

约束之间也并不独立：

- 为了降低功放峰值温度而移动热点，可能破坏 processor 的热上限；
- 为了把 battery 拉暖，可能增大 hot 侧 spread；
- 为了减小 radiator span，可能让 hot 工况重新越界。

因此，候选设计能否可行取决于多种机制是否同时协同成立。

## 12. `seed=11` 实例化对象示例

为了让抽象定义更具体，下面给出一个 `seed=11` 的实例化 `thermal_case / thermal_solution / evaluation_report` 结构示例。

说明：

- 这里使用的是已有代表性可行布局工件中的实例；
- 它用于展示“主线对象长什么样”和“评价结果如何落地”；
- 它不是在说 `seed=11` 只有这一种布局。

### 12.1 `thermal_case` 示例

在该实例中，hot case 的组件实例为：

| 组件 ID | 角色 | `(x,y)` | `width × height` | 材料 |
| --- | --- | --- | --- | --- |
| `processor-001` | processor | `(0.85819, 0.49014)` | `0.17463 × 0.115706` | `electronics_housing` |
| `rf_power_amp-001` | rf_power_amp | `(0.39910, 0.34391)` | `0.138073 × 0.105651` | `electronics_housing` |
| `obc-001` | obc | `(0.250057, 0.391962)` | `0.107386 × 0.085357` | `electronics_housing` |
| `battery_pack-001` | battery_pack | `(0.864338, 0.377640)` | `0.143765 × 0.109102` | `battery_insulated_housing` |

该实例中的 radiator 为：

| 特征 ID | 边 | `start` | `end` | `sink_temperature` | `transfer_coefficient` |
| --- | --- | --- | --- | --- | --- |
| `radiator-top-001` | top | `0.3115657` | `0.7969202` | hot:`305.0`, cold:`248.0` | hot:`4.0`, cold:`10.0` |

### 12.2 `thermal_solution` 示例

同一个实例中，hot 解的求解器输出显示：

- `converged = true`
- `iterations = 4`
- `num_dofs = 2009`
- `summary.temperature_min = 345.0956`
- `summary.temperature_mean = 348.7690`
- `summary.temperature_max = 349.6019`

这说明主线对象不是抽象打分器，而是真正经过 PDE 求解得到的温度场及其派生指标。

### 12.3 multicase `evaluation_report` 示例

该 `seed=11` 示例的 multicase evaluation 结果为可行：

| 指标 | 数值 |
| --- | --- |
| `minimize_hot_pa_peak` | `349.6019` |
| `maximize_cold_battery_min` | `259.6203` |
| `minimize_radiator_resource` | `0.48535` |
| `hot_pa_limit` margin | `5.3981` |
| `hot_processor_limit` margin | `0.4090` |
| `hot_component_spread_limit` margin | `0.7481` |
| `cold_battery_floor` margin | `0.1203` |

这个例子很重要，因为它说明：

1. 当前主线 benchmark 不是“天生不可行”的；
2. 三个目标和四个约束都能被真实地数值化；
3. `case -> solution -> evaluation` 这一链条已经能够稳定产出可解释的工程结果。

## 13. 把整个问题写成优化语句

综合以上定义，当前主线优化问题可以表述为：

给定 8 维设计变量向量

```text
x = [processor_x, processor_y, rf_power_amp_x, rf_power_amp_y,
     battery_pack_x, battery_pack_y, radiator_start, radiator_end]
```

在满足几何合法性与热约束的前提下，联合优化：

```text
minimize   f1(x) = T_hot_max(rf_power_amp)
maximize   f2(x) = T_cold_min(battery_pack)
minimize   f3(x) = span(radiator)
```

subject to

```text
T_hot_max(rf_power_amp) <= 355.0
T_hot_max(processor)   <= 350.0
T_cold_min(battery)    >= 259.5
DeltaT_hot_components  <= 1.0
geometry(x) is legal
```

其中每一次 `f(x)` 与约束值的计算，都不是闭式函数，而是由：

- case materialization
- FEniCSx steady conduction solve
- metric extraction
- multicase aggregation

共同给出的昂贵评价结果。

## 14. 本报告的结论

本报告固定了当前主线的问题定义，可以归纳为四点：

1. 当前主线不是简单布局问题，而是一个“共享布局、双工况、带热约束的 8 维多目标热优化问题”。
2. 主线 benchmark 的关键对象已经稳定：四类组件、一个顶部 radiator 边界段、hot/cold 两个 operating cases、三目标、四约束。
3. 平台中的 `scenario_template -> thermal_case -> thermal_solution -> evaluation_report` 链条已经足以完整表达这个问题。
4. 后续所有 `raw / union / llm-union` 的方法比较，都应被理解为在这个问题定义之上的 proposal/control 差异比较，而不是更换问题本身。

后续第二篇报告将进一步说明：在这个固定问题上，`raw`、`union-uniform` 与 `llm-union` 三条方法线分别改动了什么，以及为什么这种比较是公平的。
