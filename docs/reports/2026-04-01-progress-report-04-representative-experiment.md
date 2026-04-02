# 报告四：代表性实验全流程复盘与方法对比

Date: 2026-04-01

## 1. 报告目的

本报告不是泛泛地罗列几组指标，而是围绕一个最适合汇报当前阶段方法价值的主案例，把整条链路讲清楚：

- 三种方法如何在同一 benchmark 上运行
- 它们在相同预算下何时进入可行域
- 最终形成了怎样的 Pareto 结果
- `LLM` controller 的行为与 `union-uniform` 有什么机制差异
- 当前最好绝对结果落在什么位置

按照前面设计文档，本报告采用：

- `seed-23` 作为正文主案例
- `seed-17` 作为“当前最好绝对结果”补充快照

## 2. 为什么主案例选 `seed-23`

选择 `seed-23` 的原因不是它给出了当前全库绝对最好的单次结果，而是它最能说明当前 `LLM-union` 的方法价值。

在 `seed-23` 上：

- `raw` 能进入可行域，但进入较晚；
- `union-uniform` 明显退化；
- `llm-union` 在同预算下显著更早进入可行域，并积累更多 feasible 候选。

也就是说，这个 seed 最适合回答：

在 action space 不变时，`LLM` controller 是否真的在起作用？

如果只讲当前绝对最好结果，听众容易把结论误读为“uniform 仍然最好”；而 `seed-23` 更适合解释 controller 的方法意义与阶段性正向证据。

## 3. 主案例实验设置

### 3.1 共享问题定义

三种方法都运行在同一个主线 benchmark 上：

- template：
  - `panel-four-component-hot-cold-benchmark`
- benchmark seed：
  - `23`
- 设计变量：
  - 相同 8 维编码
- 评价：
  - 相同 hot/cold multicase evaluation spec
- 预算：
  - `population_size = 16`
  - `num_generations = 8`
  - 总 candidate evaluations = `129`

由于每个 candidate 都要跑：

- 1 次 hot solve
- 1 次 cold solve

所以主案例三条线都对应 `258` 次热求解量级的昂贵评价。

### 3.2 三种方法的唯一差异

主案例中三种方法只在 proposal/control 层不同：

| 方法 | proposal 机制 | controller |
| --- | --- | --- |
| `raw` | 原生 `SBX + PM` | 无 controller |
| `union-uniform` | fixed mixed action registry | `random_uniform` |
| `llm-union` | fixed mixed action registry | `GPT-5.4` controller |

因此，这个对照不是在比三种不同问题，也不是在比三种不同物理模型，而是在比：

- 原生 proposal
- 扩展 action space 但随机调度
- 扩展 action space 且状态驱动调度

## 4. 主案例总结果对比

### 4.1 聚合指标对比

`seed-23` 主案例在相同 `129` evaluations 下的总指标如下：

| 方法 | feasible rate | feasible 个数 | first feasible eval | pareto size |
| --- | --- | --- | --- | --- |
| `raw` | `0.0930` | `12` | `78` | `5` |
| `union-uniform` | `0.0078` | `1` | `127` | `1` |
| `llm-union` | `0.1473` | `19` | `42` | `4` |

从这张表可以直接看出三点：

1. `raw` 能在这个 seed 上稳定找到可行解，但进入可行域较晚；
2. `union-uniform` 虽然拥有更大的 action space，但在这个 seed 上明显退化，几乎直到 run 末尾才找到唯一一个可行点；
3. `llm-union` 在同一 action space 下，把 first feasible evaluation 从 `127` 拉回到 `42`，并把 feasible 候选数从 `1` 提高到 `19`。

### 4.2 从汇报角度该怎么解读

这组结果最适合支撑的不是“`LLM` 已经全面最优”，而是：

- 扩大 action space 本身并不保证收益；
- 如果调度不好，甚至会显著破坏可行性进入；
- 在同一 action space 上，状态驱动 controller 确实可能把无效的随机扩展，重新变成有效的搜索机制。

## 5. 主案例全流程复盘

### 5.1 第一步：问题实例化

三条线都从同一个 `seed-23` benchmark layout source 出发，构造：

- 一个 hot case
- 一个 cold case

并共享：

- 同一组组件几何
- 同一类边界散热特征
- 同一 repair
- 同一 multicase evaluation

### 5.2 第二步：初始化与 baseline

所有 run 都会先评估 baseline candidate，再进入进化循环。

从优化器角度看，真正有 controller 参与的是初始化后的 proposal 决策阶段，因此：

- `raw` 只有 candidate evaluation 历史，没有 controller trace；
- `union-uniform` 与 `llm-union` 从第一个 proposal decision 起就开始写 `controller_trace` 与 `operator_trace`。

### 5.3 第三步：可行域进入时间

主案例中三种方法进入可行域的时间差异非常大：

| 方法 | first feasible eval |
| --- | --- |
| `raw` | `78` |
| `union-uniform` | `127` |
| `llm-union` | `42` |

这意味着：

- `raw` 需要较长时间才能把几何布局与热耦合同时调整到满足约束；
- `union-uniform` 在这个 seed 上几乎把大部分预算耗在无效 proposal 上；
- `llm-union` 则在不到一半预算的位置就已经跨过第一可行门槛。

从实验叙事上说，`42` 这个数字是正文里最重要的节点之一。

### 5.4 第四步：可行解积累

进入可行域之后，三种方法形成了不同的可行解积累速度：

- `raw`：
  - 最终积累 `12` 个 feasible 候选；
- `union-uniform`：
  - 最终只积累 `1` 个 feasible 候选；
- `llm-union`：
  - 最终积累 `19` 个 feasible 候选。

这说明主案例中的 `LLM` 收益不只体现在“更早找到第一个可行解”，也体现在“后续可行解持续积累能力更强”。

### 5.5 第五步：Pareto 前沿形成

主案例最终的 Pareto front 大小分别为：

- `raw = 5`
- `union-uniform = 1`
- `llm-union = 4`

需要谨慎解读：

- `llm-union` 在这个 seed 上并没有把 Pareto size 做到最大；
- 但它在 first feasible 速度和 feasible rate 上是三者中最强的；
- `union-uniform` 的唯一 Pareto 点更像“最后侥幸跨过可行门槛”的结果，而不是稳定形成了前沿。

因此在主案例上，更适合强调的是：

- feasibility conversion 和 feasibility accumulation

而不是只看最终 Pareto 个数。

## 6. 主案例代表解对比

为了公平展示三种方法的最终 trade-off，本报告使用：

- `raw`：
  - `knee_candidate`
- `union-uniform`：
  - 其唯一可行代表点，记作 `min_hot_pa_peak`
- `llm-union`：
  - `knee_candidate`

### 6.1 代表解三目标对比

| 方法 | 代表点 | eval index | hot PA peak | cold battery min | radiator resource |
| --- | --- | --- | --- | --- | --- |
| `raw` | `knee_candidate` | `123` | `349.9727` | `259.5846` | `0.4935` |
| `union-uniform` | `min_hot_pa_peak` | `127` | `349.7289` | `259.5480` | `0.4809` |
| `llm-union` | `knee_candidate` | `73` | `349.5924` | `259.5597` | `0.4932` |

这张表非常有意思：

1. `llm-union` 在主案例中给出了三者中最低的 hot PA peak；
2. `raw` 的 knee 点在 cold battery min 上略优于 `llm-union`；
3. `union-uniform` 的唯一可行点在 radiator resource 上最省，但这是以极差的 feasible rate 和极晚的 first feasible 为代价的。

因此，主案例最合理的结论不是“谁所有目标都赢”，而是：

- `llm-union` 更像是一个更快把搜索推进到“高质量可行区”的 controller；
- `union-uniform` 虽然偶尔能碰到一个较省 radiator 的点，但整体搜索过程非常不稳定；
- `raw` 依然是很强的 classical anchor。

### 6.2 代表解约束 margin 对比

| 方法 | hot PA margin | hot processor margin | hot spread margin | cold battery margin |
| --- | --- | --- | --- | --- |
| `raw` | `5.0273` | `0.3149` | `0.5693` | `0.0846` |
| `union-uniform` | `5.2711` | `0.2329` | `0.8538` | `0.0480` |
| `llm-union` | `5.4076` | `0.5490` | `0.6755` | `0.0597` |

这张表说明：

- `llm-union` 的代表点并不是“侥幸擦边可行”，而是在 hot 侧约束上留出了较好的安全余量；
- `raw` 的 knee 点在 cold battery margin 上更宽一些；
- `union-uniform` 的唯一点虽然可行，但 cold battery margin 其实偏紧。

因此，如果从工程可解释性看，主案例中的 `llm-union` 代表点是一个相当合理的折中点。

## 7. 主案例的机制观察

### 7.1 `union-uniform` 的 operator 分布

`seed-23 union-uniform` 的 operator 使用分布较为平均：

| operator | count |
| --- | --- |
| `radiator_align_hot_pair` | `19` |
| `battery_to_warm_zone` | `18` |
| `hot_pair_separate` | `15` |
| `sbx_pm_global` | `12` |
| `radiator_expand` | `11` |
| `hot_pair_to_sink` | `10` |
| `radiator_contract` | `10` |
| `native_sbx_pm` | `9` |
| `local_refine` | `8` |

这很符合 `random_uniform` 的设计初衷，但问题也很明显：

- 它没有形成针对该 seed 当前 regime 的偏置；
- 因而大部分动作只是被“平均尝试”，却没有被“条件化调度”。

### 7.2 `llm-union` 的 operator 分布

`seed-23 llm-union` 的 operator 使用则明显更有偏向性：

| operator | count |
| --- | --- |
| `battery_to_warm_zone` | `44` |
| `hot_pair_separate` | `27` |
| `radiator_align_hot_pair` | `18` |
| `native_sbx_pm` | `8` |
| `hot_pair_to_sink` | `5` |
| `radiator_expand` | `4` |
| `local_refine` | `3` |
| `radiator_contract` | `2` |
| `sbx_pm_global` | `1` |

这说明至少在 `seed-23` 这个主案例里，`LLM` controller 并没有“均匀地乱用动作”，而是更集中地使用：

- `battery_to_warm_zone`
- `hot_pair_separate`
- `radiator_align_hot_pair`

从热设计直觉看，这三类动作恰好分别对应：

- 提升 cold battery 生存性；
- 缓解高热器件耦合；
- 调整 radiator 与热点的相对关系。

### 7.3 主案例早期决策序列

从 `controller_trace.json` 的前 10 个 decision 看，`llm-union` 一开始就表现出明显偏置：

- `battery_to_warm_zone`：`6` 次
- `native_sbx_pm`：`2` 次
- `hot_pair_to_sink`：`2` 次

这说明主案例的 `LLM` controller 在早期并没有平均探索，而是较快把注意力集中到：

- 让 battery 变暖
- 让热点靠近 sink

这一机制观察与它更快进入可行域是相互一致的。

### 7.4 LLM runtime 稳定性

在 `seed-23 llm-union` 主案例中：

- `request_count = 112`
- `response_count = 112`
- `fallback_count = 0`
- `elapsed_seconds_total = 828.05`
- `elapsed_seconds_avg = 7.39`

这意味着主案例中的 controller 调用并没有出现 provider 级失败或 fallback，对“这是一条真实可运行的 live path”这一点形成了直接证据。

## 8. 当前最好绝对结果快照：`seed-17`

为了保持诚实，本报告不能只讲 `seed-23` 的方法亮点，还必须补充当前最好绝对结果所在的位置。

### 8.1 `seed-17` 总指标

当前 paper-facing 三线中，`seed-17` 的结果如下：

| 方法 | feasible rate | feasible 个数 | first feasible eval | pareto size |
| --- | --- | --- | --- | --- |
| `raw` | `0.1318` | `17` | `70` | `9` |
| `union-uniform` | `0.2248` | `29` | `34` | `22` |
| `llm-union` | `0.2016` | `26` | `39` | `13` |

这说明：

- 当前最好绝对结果确实仍然是 `seed-17 union-uniform`；
- 但 `llm-union` 在 `seed-17` 上也已经达到了非常强的水平，明显优于 `raw`，并且接近 `uniform`；
- 因此更准确的说法应当是：
  - 当前 `LLM` 路线已经出现强正向 seed，
  - 但跨 seed 的稳定领先还在继续验证。

### 8.2 `seed-17` 代表解对比

仍以各自代表性 knee 点为主，`seed-17` 的代表解三目标如下：

| 方法 | eval index | hot PA peak | cold battery min | radiator resource |
| --- | --- | --- | --- | --- |
| `raw` | `70` | `350.0432` | `259.7454` | `0.4749` |
| `union-uniform` | `55` | `350.2816` | `259.8132` | `0.4677` |
| `llm-union` | `101` | `349.8565` | `259.6969` | `0.4646` |

这张表显示：

- `llm-union` 在 `seed-17` 的 knee 点上给出了三者中最低的 radiator resource 和更低的 hot PA peak；
- `union-uniform` 在 cold battery min 上最好，且整体 Pareto 规模最大；
- `raw` 则整体落在后面。

因此，`seed-17` 最适合在汇报中被表述为：

- 当前最好绝对结果快照
- 同时也是 `LLM` 已经接近强 uniform baseline 的证据

### 8.3 `seed-17` 的机制补充

`seed-17 llm-union` 的 operator 分布与 `seed-23` 不同，更偏向：

- `native_sbx_pm`：`38`
- `battery_to_warm_zone`：`23`
- `radiator_align_hot_pair`：`15`

而 `seed-17 union-uniform` 仍然较均匀分布在 9 个动作之间。

这说明当前 controller 已经不是固定偏向某一个动作名字，而是会在不同 seed 下呈现不同的动作组合；但它是否已经形成足够稳定、足够可迁移的 kernel，还需要继续验证。

## 9. 这次代表性复盘真正说明了什么

综合 `seed-23` 主案例与 `seed-17` 补充快照，可以得到一个比较稳健的阶段性结论。

### 9.1 可以确认的

可以确认的是：

1. 当前 `LLM-union` 已经不是只会生成 trace 的 demo，而是真正能在 live route 上跑出多条可行、可解释结果的 controller。
2. 在 `seed-23` 主案例中，`LLM` controller 相比 `union-uniform` 显著改善了 first feasible speed 和 feasible rate。
3. 在 `seed-17` 上，`LLM-union` 已经接近当前最强的 `union-uniform`，并明显强于 `raw`。

### 9.2 还不能直接声称的

目前还不能直接声称：

1. `LLM-union` 在所有 seed 上都优于 `union-uniform`；
2. 当前 controller kernel 已经稳定完成；
3. 当前机制观察已经能无条件推广到所有 future scenarios 和 all backbones。

更稳妥的表达应当是：

- 当前已经获得明确的正向 seed-level evidence；
- controller kernel 的跨 seed 稳定性与跨场景可迁移性仍在继续做机制验证。

## 10. 本报告的结论

本报告通过 `seed-23` 主案例和 `seed-17` 最好结果快照，固定了当前阶段最适合用于汇报的实验叙事：

1. `seed-23` 最适合说明 `LLM` controller 的方法价值，因为它清楚显示了 `LLM` 在同一 action space 下把一个退化的 `union-uniform` 搜索重新拉回到了高效的可行性搜索轨道。
2. `seed-17` 最适合作为“当前最好绝对结果”补充，因为它表明最强 `uniform` 仍然存在，同时也表明 `LLM` 已经非常接近这一强基线。
3. 当前最合理的汇报结论不是“`LLM` 全面获胜”，而是：
   - `LLM` controller 已经显示出明确的方法有效性，
   - 但其稳定领先仍需继续用更多 seed 和更多 controller diagnostics 去验证。

到这里，四篇中文报告的逻辑链已经闭合：

- 第一篇定义问题；
- 第二篇定义比较架构；
- 第三篇解释 `LLM-union` 方法；
- 第四篇给出代表性实验复盘与结果对照。
