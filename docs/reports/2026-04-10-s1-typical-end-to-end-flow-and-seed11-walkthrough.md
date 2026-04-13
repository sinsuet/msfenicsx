# `s1_typical` 端到端流程详解与 `seed-11` 真实运行讲解

## 1. 文档目的

这份文档完整解释当前主线 benchmark `s1_typical` 的真实工作流，覆盖以下问题：

- 从最开始的模板 `scenario_template` 到生成出的 `base_case`，中间到底发生了什么。
- `base_case` 为什么通常是可行的。
- optimizer 产生的候选解为什么可能不可行，以及不可行会在哪一层被拦下。
- `nsga2_raw`、`nsga2_union`、`nsga2_llm` 三条路线在当前仓库中的关系是什么。
- 评价指标各自代表什么物理含义。
- 我们最近真实跑过的 `raw + union` 套件里，拿一个具体 seed 把全过程讲透。

本文基于 2026-04-10 当前仓库实现和真实运行产物，不是抽象设计稿。

> 2026-04-12 integrity update:
> 当前 `s1_typical` 的 paper-facing raw/union 语义已经锁定为单 `benchmark_seed` 单案例 benchmark；
> `first_feasible_eval` / `optimizer_feasible_rate` 采用 optimizer-only 口径；
> `layout_*` 从候选几何重算，不再沿用 baseline provenance。

## 2. 当前 benchmark 的身份

当前 paper-facing 主线只有 `s1_typical`，它的固定 benchmark 设定是：

- 单 operating case。
- 15 个命名组件。
- 只优化每个组件的 `x/y`，不优化旋转角。
- 总决策维度是 32。
- 目标固定为：
  - `summary.temperature_max`
  - `summary.temperature_gradient_rms`
- 硬约束固定为：
  - `case.total_radiator_span <= 0.48`
  - `component.c01-001.temperature_max <= 356 K`
  - `component.c08-001.temperature_max <= 352 K`
  - `components.max_temperature_spread <= 95 K`
- 官方 sink 模型仍然是单个 top-edge `line_sink`。
- 当前有效比较路线只有：
  - `nsga2_raw`
  - `nsga2_union`
  - `nsga2_llm`

这意味着当前 benchmark 研究的问题，不是“先生成一个全新的布局家族再筛选”，而是：

> 在同一个固定 benchmark 实例上，用不同 optimizer/controller 去做单案例热布局优化。

## 3. 核心对象先讲清楚

当前主线对象流是：

`scenario_template -> thermal_case -> thermal_solution -> evaluation_report -> optimization_result`

它们分别是什么：

| 对象 | 来源 | 含义 |
| --- | --- | --- |
| `scenario_template` | 手写 YAML | 问题定义模板，描述面板、组件族、散热边界、材料、载荷规则、生成规则 |
| `thermal_case` | 生成器输出 | 一个具体实例，组件已经摆好了，载荷和边界条件也已经具体化 |
| `thermal_solution` | FEniCSx 求解器输出 | 对这个具体 case 的稳态温度场求解结果 |
| `evaluation_report` | 评估引擎输出 | 从 `case + solution + evaluation_spec` 提取目标值、约束值、派生信号 |
| `optimization_result` | optimizer 输出 | 整次优化的历史、Pareto 集、代表解、聚合统计 |

当前主线里的三个最重要 YAML 是：

- `scenarios/templates/s1_typical.yaml`
- `scenarios/evaluation/s1_typical_eval.yaml`
- `scenarios/optimization/s1_typical_{raw,union,llm}.yaml`

## 4. 从模板到 `base_case`：生成阶段到底做了什么

### 4.1 模板里定义了什么

`scenarios/templates/s1_typical.yaml` 定义了：

- 面板尺寸：`width=1.0`, `height=0.8`
- 主布局区域 `main-deck`：
  - `x in [0.07, 0.93]`
  - `y in [0.06, 0.69]`
- 顶部 keep-out：`top-edge-harness-strip`
- 15 个组件族的形状、尺寸、语义标签、摆放提示、clearance
- 单个 top-edge `line_sink`
- 每个组件的 `total_power`
- 每个组件的 `source_area_ratio`
- 材料参数
- 物理参数：
  - `ambient_temperature = 292 K`
  - `background_boundary_cooling.transfer_coefficient = 0.15`
  - `background_boundary_cooling.emissivity = 0.08`
- 网格和 nonlinear solver 配置
- 生成策略 `legacy_aligned_dense_core_v1`

### 4.2 生成流程

生成入口在 `core/generator/pipeline.py` 的 `generate_case(...)`。

流程按顺序是：

1. 读入模板。
2. 用给定 seed 对模板参数采样。
3. 调用 `place_components(...)` 给 15 个组件放位置。
4. 生成边界散热特征，也就是 `line_sink`。
5. 计算一组生成期布局指标。
6. 组装成 canonical `thermal_case`。
7. 做 case contract 检查。

### 4.3 组件怎么被放进去

组件布局的核心在 `core/generator/layout_engine.py`。

它不是纯随机撒点，而是会利用：

- `placement_hint`
- `layout_tags`
- `adjacency_group`
- `clearance`
- keep-out 区域
- 生成策略里的区域分区

当前 `s1_typical` 使用的区域语义包括：

- `active_deck`
- `dense_core`
- `top_sink_band`
- `left_io_edge`
- `right_service_edge`

也就是说，像 power module 会更偏向 top band，IO 类会更偏向边缘，support 类更偏向底部或服务边。

### 4.4 clearance 在生成阶段怎么起作用

当前生成器不是只检查“有没有几何重叠”，而是检查最小间隙：

- `component_within_domain(...)`
- `component_respects_keep_out_regions(...)`
- `components_violate_clearance(...)`

`components_violate_clearance(...)` 用的是两组件实际几何距离减去所需 clearance gap，因此：

- 重叠一定非法
- 没重叠但间隙不够也非法

这也是为什么现在说“clearance 真正启用了”，不是纸面参数。

### 4.5 `source_area_ratio` 的真实含义

每个组件都有：

- `total_power`
- `source_area_ratio`

这两个量一起决定热源的空间分布。

在 `core/solver/case_to_geometry.py` 里，组件几何多边形会被按面积比缩成一个 `source_polygon`：

- 如果 `source_area_ratio = 1.0`，就是整个组件都均匀发热。
- 如果 `source_area_ratio < 1.0`，就是总功率被集中施加在组件内部更小的一块区域上。

因此：

> `source_area_ratio` 越小，局部体热源密度越大，热点通常越尖。

这也是为什么“所有组件都产生废热”不等于“所有组件热源分布都一样”。

### 4.6 `component_area_ratio` 的口径

`component_area_ratio` 在 `core/generator/layout_metrics.py` 里定义为：

> 总组件面积 / 布局域面积

这里的分母是 placement region，也就是 `main-deck`，不是整板 `panel_area=0.8`。

这点非常重要。当前 `seed-11` baseline 的：

- `layout_component_area_ratio = 0.4448693203070379`

它的含义是：

> 组件总面积占主布局域面积约 44.49%

而不是占整板 44.49%。

## 5. `base_case` 为什么通常可行

### 5.1 生成器目标就是先生成一个合法实例

当前 `s1_typical` 主线不是从一个故意非法的初始布局开始，而是先生成一个合法、可求解、可评估的 benchmark 实例，这个实例就是 `base_case`。

生成阶段已经尽量保证：

- 组件在板内
- 不碰 keep-out
- 没有 clearance 冲突
- `line_sink` 自身合法

所以 `base_case` 通常在几何层面就是合法的。

### 5.2 `seed-11` 的 baseline 真实证据

本次对照用的 baseline 验证产物在：

- `scenario_runs/v3_validate/s1_typical/s1_typical-seed-0011/evaluation_report.yaml`

真实结果：

- `case_id = s1_typical-seed-0011`
- `feasible = true`
- `summary.temperature_max = 311.1627103171753 K`
- `summary.temperature_gradient_rms = 16.952788118884403`
- `case.total_radiator_span = 0.38`
- `hotspot_component_id = c10-001`
- `active_heat_source_count = 15`

因此，至少对 `seed-11` 来说：

> `base_case` 是一个真实可行的 benchmark 实例，而不是 optimizer 在第 0 步还需要先修复的坏案例。

## 6. 从 `thermal_case` 到物理场：求解器到底解的是什么

### 6.1 几何解释

`core/solver/case_to_geometry.py` 会把 `thermal_case` 解释成 solver 输入：

- 面板材料导热率
- 组件材料导热率
- 每个组件的真实几何 polygon
- 每个组件的 `source_polygon`
- `line_sink`
- ambient/background cooling 参数

### 6.2 当前物理模型

`core/solver/physics_builder.py` 里构造的是一个 2D 稳态导热问题，边界上叠加两类冷却：

1. 官方主冷源：`line_sink`
2. 弱背景冷却：非 sink 外边界上的 ambient/background cooling

更具体一点：

- 域内有导热项 `k * grad(T)`
- 域内有热源项 `source`
- sink 边界上有：
  - 线性换热项 `h * (T - T_sink)`
  - 辐射风格的四次项 `emissivity * sigma * (T^4 - T_sink^4)`
- 其余边界上有较弱的 ambient/background cooling：
  - `background_h * (T - T_ambient)`
  - `background_emissivity * sigma * (T^4 - T_ambient^4)`

所以这里的物理含义可以直接说成：

> top-edge `line_sink` 是主散热通道，其他外边界只提供很弱的背景散热。

### 6.3 `sink` 到底是什么意思

在当前 benchmark 里，`sink` 指的就是边界上的散热窗口 `line_sink`。

它不是一个“组件”，也不是内部冷板，而是：

- 面板某条边上的一个区间
- 当前官方模型固定在 top edge
- 用归一化坐标 `start/end in [0, 1]` 描述位置

对 `seed-11` baseline 来说：

- `sink_start = 0.31`
- `sink_end = 0.69`
- 由于面板宽度就是 1.0，所以也等价于顶边 `x in [0.31, 0.69]`

模板里这个 sink 的固定参数是：

- `sink_temperature = 286 K`
- `transfer_coefficient = 10`

### 6.4 `hotspot` 到底是什么意思

当前实现里其实有两个相关但不完全相同的“热点”概念：

1. `hotspot_component_id`
2. `field_view.temperature.hotspot`

它们分别表示：

- `hotspot_component_id`
  - 来自 evaluation `derived_signals`
  - 含义是“哪个组件的 `temperature_max` 最高”
- `field_view.temperature.hotspot`
  - 来自 `summaries/field_view.json`
  - 含义是“导出到规则网格后的最高温点坐标和数值”

通常两者会落在同一热点组件附近，但它们不是同一个字段，也不保证数值定义完全相同。

### 6.5 网格、求解器与导出

当前模板使用：

- 网格：`48 x 40`
- nonlinear solver：`SNES`

求解完成后会得到：

- `thermal_solution`
- 每个组件的温度摘要
- 场的规则网格导出

规则网格导出目前是：

- 温度场 `81 x 101`
- 梯度模长场 `81 x 101`

这就是代表解 `pages/index.html` 和 `summaries/field_view.json` 的来源。

## 7. 评估阶段：目标、约束和指标分别是什么意思

评估入口在 `evaluation/engine.py`，使用规约文件：

- `scenarios/evaluation/s1_typical_eval.yaml`

### 7.1 两个优化目标

当前固定优化目标是：

1. `summary.temperature_max`
2. `summary.temperature_gradient_rms`

它们的含义分别是：

- `summary.temperature_max`
  - 整个求解域上的最高温度
  - 越低越好
- `summary.temperature_gradient_rms`
  - 在 `core/solver/gradient_metrics.py` 中定义为  
    `sqrt((1 / |Omega|) * integral_Omega |grad(T)|^2 dx)`
  - 它衡量的是整体温度梯度强度
  - 越低通常表示场更平滑、局部热应力风险更低

### 7.2 当前硬约束

当前评估规约定义了 4 个硬约束：

1. `case.total_radiator_span <= 0.48`
2. `component.c01-001.temperature_max <= 356`
3. `component.c08-001.temperature_max <= 352`
4. `components.max_temperature_spread <= 95`

其中：

- `case.total_radiator_span`
  - 所有 `line_sink` 长度之和
  - 当前只有一个 sink，所以就是 `end - start`
- `component.c01-001.temperature_max`
  - 组件 `c01-001` 内的最高温度
- `component.c08-001.temperature_max`
  - 组件 `c08-001` 内的最高温度
- `components.max_temperature_spread`
  - 各组件平均温度的最大值减最小值
  - 它不是整个面板场的 max-min

### 7.3 评估报告里常见字段怎么读

| 字段 | 含义 |
| --- | --- |
| `feasible` | 所有硬约束都满足 |
| `metric_values` | 所有被目标/约束需要的原始数值 |
| `objective_summary` | 目标值，给 optimizer 用 |
| `constraint_reports` | 每个约束的 `actual/limit/margin/satisfied` |
| `violations` | 不满足的约束列表 |
| `derived_signals` | 附加解释性信号，不直接参与优化 |

### 7.4 `constraint_values` 为什么有负数

在 `optimizers/problem.py` 里，optimizer history 记录的 `constraint_values` 是 violation form：

- 对 `<=` 约束，记录的是 `actual - limit`

因此：

- 小于 0：满足约束，而且离上界还有余量
- 等于 0：卡在边界
- 大于 0：违反约束

例如 baseline 的 radiator budget 是：

- 实际 `0.38`
- 上限 `0.48`
- 记录值 `0.38 - 0.48 = -0.10`

### 7.5 指标词典

下面是最常用指标的物理或工程解释：

| 指标 | 含义 |
| --- | --- |
| `case.component_count` | 组件数量，当前应为 15 |
| `case.panel_area` | 面板面积，当前为 `1.0 * 0.8 = 0.8` |
| `case.total_power` | 全部组件总功耗，当前 `114 W` |
| `case.power_density` | 总功耗 / 面板面积，当前数值为 `142.5` |
| `case.total_radiator_span` | 散热窗口总长度 |
| `summary.temperature_min` | 整场最低温 |
| `summary.temperature_mean` | 整场平均温 |
| `summary.temperature_max` | 整场峰值温度 |
| `summary.temperature_span` | 整场 max-min |
| `summary.temperature_gradient_rms` | 整场梯度能量强度的 RMS |
| `solver.iterations` | SNES 迭代次数 |
| `component.<id>.temperature_max` | 单个组件内最高温度 |
| `components.max_temperature_spread` | 各组件平均温度的最大差 |
| `hotspot_component_id` | 最高组件热点属于哪个组件 |
| `hotspot_temperature_max` | 最热点组件的最高温 |
| `layout_component_area_ratio` | 组件总面积 / 布局域面积 |
| `layout_bbox_fill_ratio` | 组件总面积 / 组件整体包围盒面积 |
| `layout_nearest_neighbor_gap_mean` | 各组件到最近邻的平均间距 |
| `layout_centroid_dispersion` | 组件质心相对整体中心的平均离散程度 |
| `layout_largest_dense_core_void_ratio` | dense core 内最大空洞占比 |
| `active_heat_source_count` | 功率大于 0 的热源数，当前应为 15 |

### 7.6 一个很重要的实现细节

当前主线已经把 `layout_*` 修正为候选级真实几何指标。

具体说：

- 生成阶段会把 `placement_region` / `active_deck` / `dense_core` 写入 `provenance.layout_context`
- repair 会在候选几何合法化之后刷新 `provenance.layout_metrics`
- `evaluation/metrics.py` 和 representative case page 会优先用 `layout_context` 从候选几何重算 `layout_*`

因此当前 raw/union 主线里的：

- `layout_component_area_ratio`
- `layout_bbox_fill_ratio`
- `layout_nearest_neighbor_gap_mean`
- `layout_centroid_dispersion`
- `layout_largest_dense_core_void_ratio`

描述的是当前候选 case 本身，而不是生成期 baseline 的静态 provenance。

只有旧工件在缺少 `layout_context` 时，才会回退到保存下来的 `provenance.layout_metrics`。

## 8. 优化阶段：从 `base_case` 到 NSGA-II 历史

### 8.1 决策变量是什么

`s1_typical_raw.yaml`、`s1_typical_union.yaml`、`s1_typical_llm.yaml` 三个 optimization spec 的设计变量一致：

- 15 个组件，每个组件 2 个变量：`x/y`
- 1 个 sink 的 `start/end`

总计：

- `15 * 2 + 2 = 32` 维

这也是当前 benchmark 固定的 32D。

### 8.2 `baseline` 是什么

优化问题初始化时，`optimizers/drivers/raw_driver.py` 和 `union_driver.py` 都会先调用：

- `problem.evaluate_baseline()`

也就是把 `base_case` 本身先评估一次，并记入 history。

因此：

- `evaluation_index = 1` 是 baseline
- 它既是对照点，也是工件里保留的 reference entry

但当前主线已经把 progress 口径改成 optimizer-only：

- baseline 继续保留在 `baseline_candidates` / `history` 里作为参考点
- `first_feasible_eval`
- `optimizer_feasible_rate`（以及兼容别名 `feasible_rate`）
- controller 的 pre/post-feasible phase split

都只看 `source=optimizer` 的评估条目。

### 8.3 为什么总评估次数是 513

当前 `raw/union/llm` spec 都是：

- `population_size = 32`
- `num_generations = 16`

当前实现里还额外把 baseline 放进 history，所以总数是：

- `1 + 32 * 16 = 513`

也就是说：

- `1` 次 baseline
- `512` 次 optimizer 候选评估

### 8.4 每个 optimizer 候选会经历哪些步骤

每一个候选向量在 `optimizers/problem.py` 中按下面顺序处理：

1. 从 32 维向量恢复出 case payload。
2. 调用 `repair_case_payload_from_vector(...)` 做修复。
3. 调用 `evaluate_cheap_constraints(...)` 做便宜约束筛查。
4. 如果 cheap constraints 不通过：
   - 跳过 PDE solve
   - 直接给罚值 `1e12`
   - 记录 `failure_reason = cheap_constraint_violation`
5. 如果 cheap constraints 通过：
   - 转成 `ThermalCase`
   - 跑 FEniCSx solve
   - 生成 `evaluation_report`
   - 根据是否违反硬约束设置 `feasible`

这里还有一个很容易忽略的实现事实：

- `optimization_result.json` 里的 `decision_vector`
  - 是 optimizer 原始提出的向量
- 实际被评估、被求解的 case
  - 是 repair 之后的 case

所以有些记录会出现这种现象：

- `decision_vector` 里的 `sink_start/sink_end` 看起来反了，或者长度超预算
- 但最终 `evaluation_report` 里的 `case.total_radiator_span` 仍然合法

这不是数据错乱，而是 repair 在中间把原始候选修正成了真正被评估的候选。

### 8.5 repair 具体修什么

repair 在 `optimizers/repair.py`，主要做 4 类事：

1. 把所有设计变量夹回各自上下界。
2. 把 sink 投影成合法区间。
3. 如果 sink 长度超预算，投影回预算内。
4. 对组件对做局部几何恢复：
   - 消除重叠
   - 恢复 clearance
   - 尝试局部重定位

所以 optimizer 并不是“向量一出来就直接求解”，而是会先经过一个几何合法化层。

### 8.6 cheap constraints 具体查什么

cheap constraints 在 `optimizers/cheap_constraints.py`，当前会检查：

- 组件是否出界
- 组件之间是否违反 clearance
- `line_sink` 自身是否合法
- `case.total_radiator_span` 是否超上限

只要这里不过，就不会进 PDE。

这层的作用很重要，因为：

> 绝大多数明显非法候选，会在 PDE 之前被便宜地拦住。

### 8.7 最终 `feasible` 不是只看 cheap constraints

cheap constraints 通过，不代表最终一定 `feasible`。

原因是最终还要过真实评估约束：

- radiator span
- 组件峰值温度上限
- 组件温差 spread 上限

所以可行性有 4 层概念：

1. 生成器生成的 baseline 几何是否合法。
2. repair 后候选几何是否合法。
3. cheap constraints 是否通过。
4. solve 后评估约束是否全部满足。

## 9. `raw`、`union`、`llm` 三条路线的关系

### 9.1 `raw`

`raw` 是 plain NSGA-II 主干：

- 同一个 `base_case`
- 同一个 32D 编码
- 同一个目标
- 同一个约束
- 同一个 repair
- 同一个 cheap constraints
- 同一个 PDE solve

区别仅在于 offspring proposal 方式：

- 直接用原生 NSGA-II 的 `SBX + PM`

### 9.2 `union`

`union` 和 `raw` 优化的是同一个问题。

不同点在于 offspring proposal 不是只用原生 `SBX + PM`，而是从共享 operator pool 里选动作，包括：

- `native_sbx_pm`
- `global_explore`
- `local_refine`
- `move_hottest_cluster_toward_sink`
- `spread_hottest_cluster`
- `smooth_high_gradient_band`
- `reduce_local_congestion`
- `repair_sink_budget`
- `slide_sink`
- `rebalance_layout`

本次正式 run 里 `union` 的 controller 是：

- `random_uniform`

也就是从这些动作里均匀随机选，不是 LLM。

### 9.3 `llm`

`llm` 路线和 `union` 的 operator pool、问题定义、预算都相同。

唯一真正变化的是 controller：

- `controller = llm`
- 当前 spec 配置模型为 `GPT-5.4`

所以当前主线对外应该表述成：

> `raw` 是原生 backbone，`union` 和 `llm` 使用同一个 mixed operator registry，只是 controller 不同。

## 10. `first_feasible_eval` 应该怎么理解

当前主线里：

- baseline 仍然先作为 `evaluation_index=1` 写入 history
- baseline 也通常是可行的

但 `first_feasible_eval` 的官方口径已经修正为：

> 第一个 `source=optimizer` 且 `feasible=true` 的 evaluation index

因此它不再等于“history 里第一个可行条目”，而是明确表示 optimizer 自己第一次进入可行域的时刻。

对本文展开讲解的 `seed-11 raw/union` 路径，这个值应理解为：

- `3`

因为：

- `1` 是 baseline reference
- `2` 是第一个 optimizer 候选，但不可行
- `3` 才是第一个 optimizer 可行候选

## 11. `seed-11` 真实 run 讲解

### 11.1 使用的真实运行目录

这次完整对照使用的正式 run root 是：

- `scenario_runs/s1_typical/0412_1816__raw_union`

它的 manifest 记录：

- `run_id = 0412_1816__raw_union`
- `mode_ids = [raw, union]`
- `benchmark_seeds = [11]`

本文只展开讲 `seed-11`。

### 11.2 `seed-11` baseline

baseline 可参考：

- `scenario_runs/v3_validate/s1_typical/s1_typical-seed-0011/evaluation_report.yaml`

关键数值：

| 指标 | baseline |
| --- | --- |
| `feasible` | `true` |
| `summary.temperature_max` | `311.1627103171753 K` |
| `summary.temperature_gradient_rms` | `16.952788118884403` |
| `case.total_radiator_span` | `0.38` |
| `components.max_temperature_spread` | `2.767155433093933 K` |
| `hotspot_component_id` | `c10-001` |
| `layout_component_area_ratio` | `0.4448693203070379` |
| `layout_bbox_fill_ratio` | `0.48070874866625074` |
| `ambient_temperature` | `292 K` |
| `background_boundary_transfer_coefficient` | `0.15` |
| `active_heat_source_count` | `15` |

这说明 seed-11 的 benchmark 实例一开始就是一个合法、可求解、可评估的单案例。

## 12. `seed-11 raw`：真实发生了什么

`raw` 路径：

- `scenario_runs/s1_typical/0412_1816__raw_union/raw/seeds/seed-11`

### 12.1 聚合统计

| 指标 | raw seed-11 |
| --- | --- |
| `num_evaluations` | `513` |
| `optimizer_feasible_rate` | `0.763671875` |
| `first_feasible_eval` | `3` |
| `pareto_size` | `5` |

### 12.2 前三个 evaluation 最能说明问题

#### `evaluation_index = 1`

- `source = baseline`
- `feasible = true`
- 目标值就是上面的 baseline 值

#### `evaluation_index = 2`

- `source = optimizer`
- `feasible = false`
- `failure_reason = cheap_constraint_violation`
- `solver_skipped = true`
- `cheap_constraint_issues = ['component_outside_domain:c11-001']`

这说明 optimizer 第一个真正候选并不自动可行，cheap constraints 会把明显非法解直接拦下。

#### `evaluation_index = 3`

- 第一个 optimizer 可行候选
- `summary.temperature_max = 325.0461651569875`
- `summary.temperature_gradient_rms = 15.85545793367526`
- `hotspot_component_id = c02-001`

这个点很典型：

- 虽然可行
- 但比 baseline 更热
- 梯度略有下降

也就是说，“先找到可行”不等于“立刻更优”。

### 12.3 raw 里不可行候选主要死在哪里

对 `seed-11 raw`，不可行主要来自两类情况：

1. cheap geometry 失败
2. 极少数 post-solve 约束边界数值失败

具体看：

- `cheap_constraint_violation`: `113` 次
- solve 后但最终 `feasible=false` 且没有 `failure_reason`: `8` 次

cheap violation 最常见的原因是：

- `component_outside_domain:c11-001`：`63` 次
- `component_outside_domain:c12-001`：`40` 次
- `component_outside_domain:c13-001`：`7` 次

这很符合几何直觉，因为：

- `c11`
- `c12`
- `c13`

都是长条/胶囊类组件，在广范围 `x/y` 搜索里更容易被推到边界外。

另外 raw 里那 8 个“solve 后仍不满足”的点，主要是 radiator span 数值卡边界，例如：

- `actual = 0.48000000000000004`
- `limit = 0.48`

也就是几何上几乎就在边界上，但最终评估按严格比较被记成不满足。

### 12.4 raw 的代表解

#### `min-peak-temperature`

- `evaluation_index = 497`
- `summary.temperature_max = 304.4342415107047`
- `summary.temperature_gradient_rms = 11.734470818243384`
- `hotspot_component_id = c07-001`
- field hotspot = `(0.14, 0.22, 304.4342)`
- sink = `[0.25963348654962415, 0.7396334865496241]`

相对 baseline：

- 峰值温度下降 `6.7285 K`
- 降幅约 `2.16%`

这个点还把 sink span 用满到了：

- `case.total_radiator_span = 0.48`

说明对“压低峰值温度”这件事，拉满主散热窗口在这个 seed 上是有效的。

#### `min-temperature-gradient-rms`

- `evaluation_index = 438`
- `summary.temperature_max = 318.98023802729153`
- `summary.temperature_gradient_rms = 9.659754416176332`
- `hotspot_component_id = c01-001`
- field hotspot = `(0.39, 0.22, 318.9802)`
- sink = `[0.25977143096000826, 0.36163300945976307]`

相对 baseline：

- 梯度 RMS 下降 `7.2930`
- 降幅约 `43.02%`

但代价是：

- 峰值温度比 baseline 更高

这正是典型的 Pareto trade-off。

#### `knee-candidate`

在这个 raw seed 上，`knee-candidate` 与 `min-temperature-gradient-rms` 是同一个点：

- `evaluation_index = 438`

这意味着 raw 的 Pareto 集在该 seed 上比较小，而且“折中点”恰好被最低梯度点占据。

### 12.5 对 raw seed-11 的物理解读

如果只看这个 seed 的最终代表点，可以读出两件事：

1. `raw` 可以把峰值温度压得比 baseline 更低，也能把梯度显著抹平。
2. 它不是一步一步单调改进，而是会先撞到很多非法点，再逐渐找到更好的可行解。

## 13. `seed-11 union`：真实发生了什么

`union` 路径：

- `scenario_runs/s1_typical/0412_1816__raw_union/union/seeds/seed-11`

### 13.1 聚合统计

| 指标 | union seed-11 |
| --- | --- |
| `num_evaluations` | `513` |
| `optimizer_feasible_rate` | `0.822265625` |
| `first_feasible_eval` | `3` |
| `pareto_size` | `7` |

和 raw 相比，这个 seed 上 union 的特点是：

- 可行率更高
- Pareto front 更大

### 13.2 前三个 evaluation

union 的前 3 个 evaluation 与 raw 在这个 seed 上非常像：

- `1`：baseline，可行
- `2`：optimizer 候选，cheap constraint 失败
- `3`：第一个 optimizer 可行候选

其中 `evaluation_index=3` 的目标值也是：

- `summary.temperature_max = 325.0461651569875`
- `summary.temperature_gradient_rms = 15.85545793367526`

这说明在非常早期阶段，两条路线还没有明显分叉。

### 13.3 union 里不可行候选主要死在哪里

对 `seed-11 union`：

- 所有不可行都来自 `cheap_constraint_violation`

高频问题也是相似的：

- `component_outside_domain:c11-001`：`32` 次
- `component_outside_domain:c12-001`：`32` 次
- `component_outside_domain:c13-001`：`12` 次

所以这个 seed 上的主要“可行性难点”，依然是长条组件在大范围搜索中的边界/clearance 问题，而不是热约束本身太紧。

### 13.4 union controller 真实选了哪些动作

`controller_trace.json` 有 `510` 条记录。

出现最多的动作是：

| 操作符 | 次数 |
| --- | --- |
| `rebalance_layout` | `62` |
| `global_explore` | `60` |
| `reduce_local_congestion` | `53` |
| `slide_sink` | `53` |
| `move_hottest_cluster_toward_sink` | `51` |
| `spread_hottest_cluster` | `51` |
| `local_refine` | `48` |
| `native_sbx_pm` | `46` |
| `repair_sink_budget` | `45` |
| `smooth_high_gradient_band` | `41` |

这能看出当前 union 不是只做一类动作，而是在：

- 原生 genetic offspring
- 全局探索
- 局部整理
- 热团向 sink 靠拢
- 平滑高梯度区域
- 调 sink

这些动作之间来回切换。

### 13.5 union 的代表解

#### `min-peak-temperature`

- `evaluation_index = 476`
- `summary.temperature_max = 305.8793871745624`
- `summary.temperature_gradient_rms = 13.693903500133416`
- `hotspot_component_id = c08-001`
- field hotspot = `(0.68, 0.10, 305.8794)`
- sink = `[0.32764313472098755, 0.8104244960015772]`

相对 baseline：

- 峰值温度下降 `5.2833 K`
- 降幅约 `1.70%`

#### `min-temperature-gradient-rms`

- `evaluation_index = 372`
- `summary.temperature_max = 317.1112031309943`
- `summary.temperature_gradient_rms = 10.999479788598341`
- `hotspot_component_id = c07-001`
- field hotspot = `(0.66, 0.34, 317.1112)`
- sink = `[0.3212520806338922, 0.47125208063389223]`

相对 baseline：

- 梯度 RMS 下降 `5.9533`
- 降幅约 `35.12%`

#### `knee-candidate`

- `evaluation_index = 480`
- `summary.temperature_max = 307.2111475213214`
- `summary.temperature_gradient_rms = 12.372218268204263`
- `hotspot_component_id = c03-001`
- field hotspot = `(0.08, 0.10, 307.2111)`
- sink = `[0.2038505853701058, 0.5967901908838824]`

相对 baseline：

- 峰值温度下降 `3.9516 K`
- 降幅约 `1.27%`
- 梯度 RMS 下降 `4.5806`
- 降幅约 `27.02%`

这个点比 raw seed-11 的 knee 更“温和”：

- 峰值温度比 baseline 好
- 梯度也比 baseline 好
- 但两个目标都没走到该 seed 的最极端位置

### 13.6 对 union seed-11 的物理解读

如果只看这个 seed：

- union 比 raw 更容易持续产出可行解
- union 的 Pareto 集更大
- 但 raw 在这个 seed 上拿到了更强的单点极值

具体到这个 seed-11：

- raw 最佳峰值温度优于 union
- raw 最低梯度也优于 union
- union 的优势体现在可行率和 Pareto 点数量

这只是单 seed 事实，不应直接外推成“raw 一定比 union 强”或反过来。正式结论仍应看多 seed 汇总。

## 14. 对“我们现在到底在做什么实验”的一句话总结

当前 `s1_typical` 主线实验，严格说是：

> 对同一个已知可行的 benchmark 实例，比较不同 optimizer/controller 在固定预算下如何探索 32D 设计空间，并最终输出 Pareto 解集和代表解。

它不是：

> 从一个故意不可行的初始布局出发，看谁先找到第一个可行解。

这两个实验类都合理，但它们不是同一个 benchmark 问题。

## 15. 后续做 LLM 对比时，建议重点盯哪些指标

如果后面要拿 `nsga2_llm` 和 `raw/union` 做对比，建议优先关注：

- `first_feasible_eval`
  - 当前口径已经是 optimizer-only
- `optimizer_feasible_rate`
- `pareto_size`
- 代表解的两个目标值
- `controller_trace` / `llm_request_trace` 里的动作分布
- 失败原因分布
  - 几何失败多
  - 还是热约束失败多

其中最容易误读的是：

- `first_feasible_eval`

因为它现在虽然仍然使用全局 `evaluation_index` 编号，但 baseline 已经不再参与该指标的口径。

## 16. 建议如何读一个完整 seed 目录

无论是 raw 还是 union，一个 seed 目录最值得看的文件是：

- `optimization_result.json`
  - 全部 history、aggregate、Pareto、representatives
- `pareto_front.json`
  - 仅 Pareto 点
- `evaluation_events.jsonl`
  - 每次评估事件
- `generation_summary.jsonl`
  - 代际摘要
- `controller_trace.json`
  - 仅 union/llm 有
- `operator_trace.json`
  - 仅 union/llm 有
- `representatives/<id>/evaluation.yaml`
  - 单个代表解的最终评估
- `representatives/<id>/summaries/field_view.json`
  - 热场、热点、布局和 sink 可视化摘要
- `representatives/<id>/pages/index.html`
  - 页面化浏览入口

## 17. 一页结论

把整条链压缩成一句话就是：

1. `s1_typical` 先从模板生成一个已知合法、已知可求解的 `base_case`。
2. optimizer 以这个 `base_case` 为 benchmark 实例，在完整 32D 设计空间里搜索。
3. 每个候选先过 repair，再过 cheap constraints，再决定要不要做 PDE solve。
4. 最终只把满足热约束和 sink 预算的点记为 `feasible`。
5. `raw`、`union`、`llm` 比较的是同一个问题，差别主要在 offspring proposal/controller。
6. 本次真实 `seed-11` 里，baseline 确实可行，但 optimizer 的第一个候选并不可行；raw/union 的第一个 optimizer 可行点都是 `evaluation_index=3`，而这现在就是官方 `first_feasible_eval` 口径。
7. 本次 `seed-11` 上，raw 给出了更强的单点极值，union 给出了更高的可行率和更大的 Pareto 集。

如果后面还要继续做 paper 图、LLM 对比或指标重构，这份文档可以直接当作当前主线的“流程说明书”来用。
