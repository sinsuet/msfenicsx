# 报告二：主线 raw / union / llm-union 架构总体思路

Date: 2026-04-01

## 1. 报告目的

本报告用于回答两个问题：

1. 在当前主线 benchmark 上，我们到底搭建了什么样的优化架构？
2. 为什么 `raw`、`union-uniform` 与 `llm-union` 三条线的比较是公平的、可解释的？

第一篇报告已经固定了“问题定义”；本报告在此基础上固定“方法比较框架”。后续第三篇再进入 `LLM-union` 的具体实现细节，第四篇再进入实验与结果。

## 2. 当前主线的架构定位

当前仓库并不只有一条优化线，而是同时存在：

- 平台级的 multi-backbone raw / union runtime
- 论文主线的 `NSGA-II raw / union-uniform / union-llm`

但对于当前进度汇报，必须明确只围绕论文主线来讲：

- `raw`：
  - 纯 `NSGA-II`
- `union-uniform`：
  - `NSGA-II` + 混合 action space + `random_uniform` 控制器
- `llm-union`：
  - `NSGA-II` + 同一混合 action space + `llm` 控制器

也就是说，当前汇报并不是在讲“所有骨干算法的总平台”，而是在讲一个更聚焦、更论文化的主线研究梯子：

```text
P0: pure-native NSGA-II
P1: union-uniform NSGA-II
L1: union-llm NSGA-II
```

## 3. 顶层模块边界

当前仓库的主线平台分层是清晰的：

| 层 | 目录 | 负责什么 |
| --- | --- | --- |
| 核心层 | `core/` | schema、模板实例化、几何合法性、求解器、artifact I/O、CLI |
| 评价层 | `evaluation/` | 目标/约束 spec、指标提取、single-case / multicase report |
| 优化层 | `optimizers/` | design variable 编码、算法配置、raw/union drivers、repair、结果工件 |
| LLM 层 | `llm/` | OpenAI-compatible client 边界 |
| 可视化层 | `visualization/` | 实验汇总、dashboard、对比渲染 |

这套边界很关键，因为它意味着：

1. benchmark 与物理求解不会被 controller 逻辑污染；
2. `LLM` 不是直接进 `core/` 改动物理模型；
3. controller 只是优化层 proposal-time 决策的一部分；
4. 所有方法都消费同一套 `core` 和 `evaluation` 契约。

## 4. 三条主线的共同骨架

在当前 paper-facing 主线上，三条线共享以下内容：

### 4.1 共享 benchmark

三条线都使用同一个主线模板与评价规范：

- template：
  - `scenarios/templates/panel_four_component_hot_cold_benchmark.yaml`
- evaluation spec：
  - `scenarios/evaluation/panel_four_component_hot_cold_baseline.yaml`

### 4.2 共享设计变量编码

三条线都在同一 8 维决策空间上搜索：

- `processor_x`
- `processor_y`
- `rf_power_amp_x`
- `rf_power_amp_y`
- `battery_pack_x`
- `battery_pack_y`
- `radiator_start`
- `radiator_end`

因此：

- 决策空间没有变；
- `union` 线的变化不在 design encoding，而在 proposal/action space。

### 4.3 共享物理评价链

三条线都必须经过同一条昂贵评价链：

```text
decision vector
  -> repair
  -> hot/cold thermal_case
  -> hot/cold thermal_solution
  -> multicase evaluation_report
```

也就是说，三条线共享：

- 同一几何修复逻辑
- 同一 FEniCSx 热求解
- 同一 multicase 指标提取
- 同一可行性定义

### 4.4 共享 survival semantics

三条线都保持 `NSGA-II` 的生存机制和 Pareto ranking 语义。

这点尤其重要，因为它意味着：

- 不是拿 `NSGA-II` 去和一个完全不同的 optimizer 做黑盒对比；
- 而是在同一个 `NSGA-II` 骨架上比较不同 proposal 机制。

## 5. 三条主线分别改什么

### 5.1 `raw`

`raw` 是最干净的 classical baseline。

它的定义是：

- 算法骨架：`NSGA-II`
- mode：`raw`
- proposal 机制：原生 `SBX + PM`
- parent selection：原生 `NSGA-II`
- survival：原生 `NSGA-II`
- 不经过 controller action registry

可以把它理解为：

```text
same optimization problem
  + same NSGA-II
  + native variation only
```

### 5.2 `union-uniform`

`union-uniform` 仍然保留同一个 `NSGA-II` 骨架，但在 offspring proposal 阶段不再只使用原生 variation，而是让控制器从一个混合 action registry 中均匀随机选动作。

它的定义是：

- 算法骨架：`NSGA-II`
- mode：`union`
- controller：`random_uniform`
- action space：原生动作 + 共享 custom operators

所以它回答的是：

如果我们扩大 proposal vocabulary，但不引入智能调度，仅仅均匀随机使用这些动作，会发生什么？

### 5.3 `llm-union`

`llm-union` 与 `union-uniform` 共享同一个混合 action registry，只把 controller 从 `random_uniform` 换成 `llm`。

它的定义是：

- 算法骨架：`NSGA-II`
- mode：`union`
- controller：`llm`
- action space：与 `union-uniform` 完全相同

因此它回答的是：

在 action space 固定不变的前提下，引入一个基于状态摘要的 `LLM` controller，是否能更有效地调度动作，从而改善可行性进入、Pareto 质量或评价效率？

## 6. 从 `raw_driver` 到 `union_driver`

### 6.1 `raw` 运行链

`raw_driver` 的逻辑可以概括为：

```text
optimization spec
  -> resolve algorithm config
  -> load/generate benchmark cases
  -> build ThermalOptimizationProblem
  -> build raw backbone algorithm
  -> minimize()
  -> extract pareto front
  -> build representative candidates
  -> write optimization artifacts
```

在这条链里，变化只来自：

- 决策变量向量
- 原生 `NSGA-II` 的 mating / mutation

### 6.2 `union` 运行链

`union_driver` 的结构与 `raw_driver` 相似，但中间插入了 family-specific union adapter。

其逻辑可概括为：

```text
optimization spec
  -> resolve algorithm config
  -> load/generate benchmark cases
  -> build ThermalOptimizationProblem
  -> build family-specific union adapter
  -> controller chooses one operator
  -> operator proposes one offspring vector
  -> shared repair
  -> expensive evaluation
  -> native NSGA-II survival
  -> write optimization + trace artifacts
```

因此，`union` 不会改动物理模型，不会改动 multicase evaluation，也不会改动 NSGA-II 的 survival；它只在 proposal-time 插入控制器。

## 7. proposal-time 插入点

如果把整个 `NSGA-II` 主线流程画成简化链条，可以写成：

```text
population
  -> parent selection
  -> offspring proposal
  -> repair
  -> hot/cold solve
  -> multicase evaluation
  -> survival
  -> next generation
```

三条线唯一关键差异就在 `offspring proposal`：

- `raw`：
  - 直接用 native `SBX + PM`
- `union-uniform`：
  - 先选 action，再生成 proposal
- `llm-union`：
  - 先看 state，再选 action，再生成 proposal

也就是说，controller 的 authority 只在“选动作”这一层，而不在“直接输出最终设计”这一层。

## 8. 混合 action registry

当前论文主线的混合 action registry 固定为 9 个动作：

1. `native_sbx_pm`
2. `sbx_pm_global`
3. `local_refine`
4. `hot_pair_to_sink`
5. `hot_pair_separate`
6. `battery_to_warm_zone`
7. `radiator_align_hot_pair`
8. `radiator_expand`
9. `radiator_contract`

这个 registry 的意义是：

- `native_sbx_pm` 保留了原生 `NSGA-II` 的 proposal 语义；
- 其余动作提供领域化布局调整；
- `P1` 与 `L1` 共享这同一个 registry，避免 `LLM` 拥有额外特权动作。

因此：

- `P0 -> P1` 比较的是“只扩大 action space”；
- `P1 -> L1` 比较的是“在相同 action space 上改 controller intelligence”。

## 9. 为什么这是公平比较

当前主线比较框架成立，关键在于它严格隔离了变量来源。

### 9.1 `raw` vs `union-uniform`

`raw` 与 `union-uniform` 的差异仅在于：

- proposal 是否只来自 native action
- proposal 是否可以来自扩展的 mixed action registry

所以这个比较测的是：

- action-space expansion 本身有没有价值

### 9.2 `union-uniform` vs `llm-union`

`union-uniform` 与 `llm-union` 的差异仅在于：

- controller 是均匀随机
- 还是状态驱动的 `LLM`

所以这个比较测的是：

- controller intelligence 在固定 action space 上有没有价值

### 9.3 不能混淆的地方

当前汇报里必须反复强调：

1. 这不是把 `LLM` 直接拿来生设计向量；
2. 这不是把 `LLM` 接到求解器上改物理；
3. 这不是让 `LLM` 获得更多设计自由度；
4. 这也不是让 `LLM` 改写 survival rule。

因此，当前主线的结论空间更干净，也更适合论文叙事。

## 10. 工件与 trace 设计

当前主线不仅输出最终 `optimization_result.json`，还输出 controller 机制分析工件。

### 10.1 三条线共享的结果工件

每次 run 至少会输出：

- `optimization_result.json`
- `pareto_front.json`
- `manifest.json`

如果存在代表解，还会输出：

- `representatives/`
  - `cases/`
  - `solutions/`
  - `evaluation.yaml`

### 10.2 `union` 线额外机制工件

`union-uniform` 与 `llm-union` 还会输出：

- `controller_trace.json`
- `operator_trace.json`

### 10.3 `llm-union` 额外 LLM 工件

`llm-union` 进一步输出：

- `llm_request_trace.jsonl`
- `llm_response_trace.jsonl`
- `llm_metrics.json`

这意味着：

- `raw` 主要提供结果基线；
- `union-uniform` 提供 action-space 机制基线；
- `llm-union` 不仅提供结果，还提供 controller 机制证据。

## 11. 主线实验目录组织

当前实验系统采用 template-first 布局，官方 paper-facing mode 为：

- `nsga2_raw`
- `nsga2_union`
- `nsga2_llm`

规范实验目录形如：

```text
scenario_runs/<scenario_template_id>/experiments/<mode>__<timestamp>/
```

每个实验目录下再分为：

- `runs/seed-*/`
- `summaries/`
- `figures/`
- `dashboards/`
- `representatives/`
- `logs/`
- `spec_snapshot/`

这样的目录组织对汇报很有帮助，因为它天然支持：

- 单 seed 复盘
- 多 seed 汇总
- 图表与 summary 解耦

## 12. 为什么主线要先保持 `NSGA-II`

虽然仓库已经有 multi-backbone runtime，但当前论文主线坚持先用 `NSGA-II`，原因不是保守，而是为了隔离研究变量。

如果一开始就同时改变：

- backbone
- action space
- controller
- prompt/state 机制

那么最后很难回答性能变化究竟来自哪里。

当前主线选择 `NSGA-II` 的意义在于：

1. 给出 reviewer-friendly classical anchor；
2. 先把问题定义和 action-space 研究讲清楚；
3. 再把 `LLM` 限定为 controller 层；
4. 避免把“算法骨架变化”与“controller 智能变化”混在一起。

## 13. 当前主线的研究含义

从研究设计的角度看，当前三条线各自承担不同角色：

| 线 | 角色 | 回答的问题 |
| --- | --- | --- |
| `raw` | classical anchor | 纯原生 `NSGA-II` 在当前 benchmark 上能做到什么 |
| `union-uniform` | action-space baseline | 扩大 proposal vocabulary 但不智能调度，会发生什么 |
| `llm-union` | controller study line | 在相同 action space 上，状态驱动 controller 是否更有效 |

这使当前主线不是“我们做了一个大而全的平台”，而是一个层次非常清楚的研究故事：

1. 先固定问题；
2. 再扩大动作空间；
3. 最后在固定动作空间上比较调度策略。

## 14. 本报告的结论

本报告固定了当前主线的架构逻辑，可以归纳为四点：

1. 当前论文主线是一个围绕固定 benchmark 和固定 8 维设计变量展开的 `NSGA-II` 三阶梯架构，而不是多个优化平台故事的混合体。
2. `raw`、`union-uniform` 与 `llm-union` 共享 benchmark、repair、求解、evaluation 和 survival，只在 proposal/control 层形成差异。
3. `union` 线的核心不是改决策空间，而是引入固定 mixed action registry，并把 controller 插入 offspring proposal 阶段。
4. 这套设计使得 `P0 -> P1 -> L1` 的比较具有明确的公平性和机制可解释性。

后续第三篇报告将在这一总体架构之上，进一步详细展开 `llm-union` 当前的状态建模、policy kernel、prompt 投影、OpenAI-compatible 边界、fallback 和 trace 细节。
