# 优化搜索轨迹网络可视化设计

## 目标

本设计把论文 `paper/references/2201.11726v3.pdf` 中的 Search Trajectory Network, STN 思路适配到 `msfenicsx` 的 paper-facing thermal-layout optimizer 流程。目标不是替代 Pareto front、hypervolume 或 objective trace，而是新增一个解释搜索动力学的图件：展示 raw、union、llm 在同一个高维决策空间中访问了哪些离散区域、不同目标偏好的代表轨迹是否共享路径，以及搜索是否反复回到同类布局。

首版范围只覆盖单个 concrete optimizer seed run 的后处理和渲染，并接入现有 `render-assets`。多 run 比较图暂不进入首版实现，但首版输出的 CSV 必须为后续 suite/compare-runs 复用保留稳定字段。

## 论文方法摘要

论文的 STN 方法把多目标优化每一代的 population 压缩为少量代表解：

1. 选定少量 decomposition vectors。
2. 对每一代 population 做 non-dominated sorting。
3. 从 rank 0 起补足候选集，再对每个 decomposition vector 用 scalar aggregation function 选代表解。
4. 把代表解的 high-dimensional decision vector 映射到离散 location。
5. 连续 generation 的 location 形成有向边，多个 decomposition vectors 的轨迹合并成一个 network。

论文图件中节点大小表达访问次数，边宽表达转移次数，颜色表达 decomposition vector，灰色表达多条轨迹共享 location，特殊 marker 标识起点和终点。

## 本平台适配

### 数据入口

STN 后处理读取 concrete run root 下的 `optimization_result.json`，使用其中的 `history`。该 history 保留：

- `generation`
- `source`
- `feasible`
- `decision_vector`
- `objective_values`
- `constraint_values`
- `solver_skipped`
- `failure_reason`

`traces/evaluation_events.jsonl` 不作为主入口，因为它不保存完整 decision vector。`operator_trace.jsonl` 可用于后续扩展 operator-aware STN，但首版不依赖它。

### 目标和权重

S5/S6/S7 paper-facing 优化目标固定为：

- `summary.temperature_max`
- `summary.temperature_gradient_rms`

运行产物中可能以 evaluation spec 的 `objective_id` 出现：

- `minimize_peak_temperature`
- `minimize_temperature_gradient_rms`

也可能以短名出现：

- `temperature_max`
- `temperature_gradient_rms`

STN analytics 必须兼容这些 key。首版固定使用五个二维权重方向：

```text
V1 = (1.00, 0.00)
V2 = (0.75, 0.25)
V3 = (0.50, 0.50)
V4 = (0.25, 0.75)
V5 = (0.00, 1.00)
```

这些方向分别表达偏 `temperature_max`、折中、偏 `temperature_gradient_rms` 的代表轨迹。

### 候选选择

每个 generation 内，先取有目标值且不是 baseline 的 optimizer records。候选选择流程：

1. 优先使用 feasible records。
2. 如果 feasible records 数量不足 5 个，用 infeasible records 按 total positive constraint violation 从小到大补足。
3. 如果一代里仍不足 1 个有效 record，则跳过该 generation。
4. 对候选集做 minimization 口径的 non-dominated sorting。
5. 从 rank 0 起累积，直到候选数至少为 5 或无更多 records。
6. 每个权重方向用 normalized weighted Tchebycheff score 选代表解；如果分数相同，选择较新的 `evaluation_index`。

normalized weighted Tchebycheff 使用当前 generation candidate set 的目标范围归一化，避免温度峰值和梯度 RMS 的数值尺度差异支配选择：

```text
score(x, w) = max_i w_i * abs((f_i(x) - ideal_i) / range_i)
```

当某个 `range_i` 接近 0 时使用 1.0 作为分母。

### Location 映射

location 使用 `decision_vector`，即已被 legality policy 接受的 evaluated decision vector。首版不使用 `proposal_decision_vector`，避免把未经 `projection_plus_local_restore` 的几何写入 paper-facing 图件。

location 计算步骤：

1. 按 decision vector key 的字典序取值，形成稳定高维向量。
2. 对每个维度做 `round(value / bin_width)` 的整数量化。
3. 用量化整数 tuple 计算稳定短 hash。

默认 `bin_width = 0.02`。该值与 S5/S6/S7 的坐标变量尺度匹配，能把接近布局聚合成同一 node，同时不把明显不同布局压成一个点。首版不把 `bin_width` 暴露为 CLI 参数，但必须在 `search_trajectory_metrics.csv` 中记录。

### 节点和边

`analytics/search_trajectory_nodes.csv` 字段：

```text
node_id
location_key
visit_count
vector_count
vectors
first_generation
last_generation
representative_evaluation_index
temperature_max
temperature_gradient_rms
feasible
pareto_member
status
```

`analytics/search_trajectory_edges.csv` 字段：

```text
source
target
vector_id
weight
first_generation
last_generation
```

`analytics/search_trajectory_metrics.csv` 至少包含一行 overall metrics 和每个 vector 的 metrics：

```text
scope
vector_id
bin_width
num_nodes
num_edges
shared_nodes
pareto_nodes
components
mean_in_degree
max_in_degree
mean_out_degree
max_out_degree
```

`pareto_member` 表示该 node 的代表 objective point 属于该 run 所有 feasible evaluated records 的最终 approximate Pareto set。若 run 没有 feasible records，则全部为 false。

### 图件

`figures/search_trajectory_network.png` 和 paired PDF 是首版主图。图件约束：

- 使用 Matplotlib，沿用 `visualization/style/baseline.py` 的 publication baseline。
- 使用 deterministic force-directed layout；不能依赖外部 `networkx` 或 `igraph` 包，因为当前 `pyproject.toml` 没有这些依赖。
- 节点大小随 `visit_count` 增大。
- 边宽随 `weight` 增大。
- 单一 vector node 使用该 vector 颜色。
- 多 vector shared node 使用 light gray。
- `pareto_member` node 使用红色描边或红色填充标识。
- 起点使用 square marker，终点使用 triangle marker。
- 无节点时不生成图，但 CSV 可以为空。

`figures/search_trajectory_nodes_by_vector.png` 是辅助图，显示每个 vector 访问的 unique node 数。该图对应论文 Figure 4 的简化适配。

## 接入点

`optimizers.render_assets.render_run_assets()` 在读取 `optimization_result.json` 后调用 STN analytics：

1. 构建 `SearchTrajectoryResult`。
2. 写出三个 CSV。
3. 如果存在 nodes 和 edges，渲染 network 图和 nodes-by-vector 图。

清理逻辑必须删除旧的 STN PNG/PDF/CSV，避免 stale artifacts。

## 非目标

首版不做以下内容：

- 不新增 optimizer runtime trace 字段。
- 不改变 `optimization_spec`、`evaluation_spec` 或 solver defaults。
- 不渲染 suite-level raw/union/llm 三联 STN。
- 不引入 `networkx`、`igraph`、UMAP、t-SNE 或其他新依赖。
- 不把 STN 指标用作优化性能结论的单独证据。

## 测试策略

测试覆盖三层：

1. `optimizers.analytics.search_trajectory`：用最小 synthetic history 验证候选选择、Tchebycheff 代表解、location 聚合、shared node、Pareto membership、metrics。
2. `visualization.figures.search_trajectory_network`：用最小 node/edge rows 验证 PNG 和 paired PDF 输出。
3. `optimizers.render_assets`：扩展现有 fixture，验证 `render_run_assets` 生成 STN CSV 和 figure，并清理 stale outputs。

focused verification 命令：

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_search_trajectory.py tests/visualization/test_search_trajectory_figure.py tests/visualization/test_render_assets_fixtures.py
```

## 风险和解释口径

STN 的 location 粒度会影响节点数和共享程度。因此所有 STN 图和表必须报告 `bin_width`。论文写作中应把 STN 描述为搜索行为解释工具，而不是性能显著性证明。性能结论仍以 Pareto front、hypervolume、objective trace、constraint violation 和 representative fields 为主。
