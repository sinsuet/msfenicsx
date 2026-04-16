# 报告二：`raw / union / llm` 主线架构与公平比较边界

Date: 2026-04-16

## 1. 本报告回答的问题

如果要把 `raw`、`union`、`llm` 放在同一页里比较，必须先回答一个问题：

> 三条路线到底共享了什么，又只在哪一层不同？

只有这件事讲清楚，后面的结论才有说服力。

## 2. 三条路线共享同一个物理问题

三条路线都共享以下输入与评价链：

- 同一个 benchmark：`scenarios/templates/s1_typical.yaml`
- 同一个 evaluation spec：`scenarios/evaluation/s1_typical_eval.yaml`
- 同一个 benchmark seed：`11`
- 同一个设计变量编码：15 个组件的 `x/y` 加 `sink_start / sink_end`
- 同一个 repair 语义
- 同一个 cheap constraints 过滤
- 同一个 PDE 求解路径
- 同一个多目标 survival 语义

因此，这不是三套完全不同的优化器，而是同一个优化主链上的三种 proposal/controller 方式。

## 3. 统一主链

可以把三条路线抽象成完全相同的主链：

```mermaid
flowchart LR
    A[Population] --> B[Proposal]
    B --> C[Repair]
    C --> D[Cheap Constraints]
    D --> E[PDE Solve]
    E --> F[Evaluation Report]
    F --> G[NSGA-II Survival]
```

真正发生差异的只有 `Proposal` 这一步。

## 4. 三条路线分别怎么做 Proposal

### 4.1 `raw`

`raw` 使用原生 `NSGA-II` 的 `SBX + PM` 机制直接产生后代候选。

### 4.2 `union`

`union` 把 proposal 扩展成“共享动作池 + 随机控制器”：

- 候选动作来自同一套 mixed operator registry
- controller 是 `random_uniform`
- 也就是说，它不是直接固定使用原生算子，而是在共享动作池里均匀采样

### 4.3 `llm`

`llm` 与 `union` 共享同一套动作池，但 controller 从随机采样改成了状态驱动的 LLM 选择：

- 候选动作还是那一组 operator
- repair、约束、求解、survival 都不变
- 唯一变化是“这一轮选哪个 operator”

因此，`union` 和 `llm` 的比较非常干净：

> 动作空间相同，只是 controller 不同。

## 5. 公平比较表

| 比较项 | raw | union | llm |
| --- | --- | --- | --- |
| benchmark | 相同 | 相同 | 相同 |
| design variables | 相同 | 相同 | 相同 |
| evaluation spec | 相同 | 相同 | 相同 |
| repair | 相同 | 相同 | 相同 |
| cheap constraints | 相同 | 相同 | 相同 |
| PDE solve | 相同 | 相同 | 相同 |
| NSGA-II survival | 相同 | 相同 | 相同 |
| operator registry | 原生 only | 共享 mixed registry | 共享 mixed registry |
| controller | 无额外 controller | `random_uniform` | `llm` |

这张表对应的核心结论是：

> `raw` 是原生基线，`union` 和 `llm` 是在相同 mixed action registry 上比较“随机控制”与“状态驱动控制”。

## 6. 为什么这组比较是可信的

### 6.1 不是换问题

三条路线没有改：

- benchmark
- 目标
- 约束
- 求解器
- 决策变量

所以结果差异不能被解释成“问题换了”。

### 6.2 不是换评价口径

三条路线最终都落到同一个 `evaluation_report` 上，因此：

- `T_max` 的定义相同
- `grad_rms` 的定义相同
- 可行性的定义相同

所以结果差异不能被解释成“打分规则换了”。

### 6.3 对 `union` 和 `llm` 来说，甚至动作空间也没换

`union` 和 `llm` 的关键对比不是“谁有更多操作权限”，而是“谁更会在同一个动作空间里做选择”。

这也是为什么后面的 LLM 优势能够被解释成 controller 价值，而不是额外工程特权。

## 7. 本次 `20x10` 对比的统一预算

本次代表性实验使用统一的 `20x10` 预算：

| 项目 | 数值 |
| --- | ---: |
| `population_size` | `20` |
| `num_generations` | `10` |
| 总 evaluations | `201` |
| `benchmark_seed` | `11` |
| `algorithm.seed` | `7` |

也就是说，这次汇报不是“谁多跑，谁少跑”的比较，而是：

> 在同一个预算里，谁更快把昂贵评估用在有效方向上。

## 8. 本报告结论

本报告的核心结论是：

> `raw / union / llm` 共享同一个 `s1_typical` 物理问题和评价链，真正被比较的是 proposal/controller 层如何把同样的预算转化成更好的候选。
