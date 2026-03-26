# Demo Workflow And Chinese Beamer Design

## Goal

围绕当前单一二维稳态导热案例，构建一套适合向老师演示的完整 workflow 材料。该材料需要同时满足三件事：

- 能现场展示系统真的会运行
- 能稳定讲清 10 轮 LLM 闭环优化过程
- 能最终沉淀为一份中文 LaTeX Beamer 汇报稿

## Context

当前仓库已经具备：

- SI 风格教学案例
- 状态驱动仿真
- LLM 结构化提案
- 提案合法性校验
- 每轮 run 目录记录
- 单轮和历史工作台

但当前 `runs/` 中混有不同阶段的实验记录，不适合直接作为老师演示的官方数据集。老师演示需要的是一套“可重复、可解释、可讲述”的标准化结果，而不是开发过程中的杂乱日志。

## Demo Strategy

采用“现场跑 1 到 2 轮 + 预先跑好的官方 10 轮结果”的混合演示方案。

原因：

- 现场完整跑 10 轮风险过高，受网络、模型随机性和时间限制影响
- 只展示预先结果会让老师怀疑系统并没有真的在运行
- 混合方案既能证明系统真的工作，也能稳定呈现完整 workflow

## Scope

包含：

- 归档旧 `runs/`
- 生成一套独立的官方 10 轮 demo runs
- 自动汇总每轮“修改内容 + 校验结果 + 下一轮效果”
- 生成适合展示的图表和总表
- 生成中文 LaTeX Beamer 初稿

不包含：

- 扩展到新物理案例
- 新增更复杂的热物理模型
- 支持多个不同课程项目的通用演示框架

## Data Layout

不直接复用当前 `runs/` 作为演示主数据集。

建议目录：

```text
demo_runs/
  official_10_iter/
    run_0001/
    run_0002/
    ...
    run_0010/
    demo_summary.json
    demo_summary.csv
    demo_summary.md
    figures/
      chip_max_trend.png
      delta_trend.png
      category_timeline.png
```

旧数据建议归档：

```text
runs_archive/
  2026-03-25-pre-demo/
```

这样：

- 当前开发数据不会丢
- 演示数据编号可以重新从 `run_0001` 开始
- 老师看到的目录结构更干净

## Core Narrative

整场演示的主线要固定，不随现场发挥漂移：

1. 定义一个二维稳态导热问题
2. 说明当前设计不满足芯片温度约束
3. 说明 LLM 不能改脚本，只能改有限个结构化参数
4. 每轮修改都必须先过合法性校验
5. 每轮结果都有温度场图、结构化评估和 run 记录
6. 在多轮后，策略会从单变量转向多变量联动
7. 即使没有完全达标，也能清楚解释为什么

## Important Explanation Rules

演示里必须明确解释 3 个容易混淆的点：

### 1. `run_xxxx` 不是循环轮次

`run_0001`、`run_0002` 这类目录编号是该数据集下的 run 顺序号。

真正的“这是本次 10 轮中的第几轮”要看：

- `decision.json` 中的 `iteration`

### 2. 每个 run 目录只对应一轮 iteration

不会在一个 run 目录里再套一个“子轮次”。

### 3. 某轮 proposal 的效果通常在下一轮 evaluation 里体现

也就是：

- `run_N/evaluation.json` 描述的是当前状态
- `run_N/proposal.json` 描述的是下一轮打算怎么改
- 该 proposal 的真实效果，需要看 `run_{N+1}/evaluation.json`

这是后续制作总表和 Beamer 时必须强调的逻辑。

## LLM Editable Variable Set

演示里要明确列出当前案例允许 LLM 修改的变量集合：

- `materials.spreader_material.conductivity`
- `materials.base_material.conductivity`
- `components.2.width`
- `components.2.height`
- `components.2.x0`
- `components.2.y0`
- `heat_sources.0.value`

并附上：

- 当前值
- 允许范围
- 类别（material / geometry / load）
- 优先级
- 推荐方向

## Per-Run Summary Format

需要自动生成一份“老师一眼能看懂”的每轮摘要。

每轮至少包含：

- `run_id`
- `iteration`
- `state_before`
- `chip_max_before`
- `constraint_limit`
- `llm_decision_summary`
- `changed_paths`
- `validation_status`
- `validation_reasons`
- `chip_max_after`
- `delta_chip_max`
- `change_categories`
- `strategy_note`

其中：

- `before` 从当前 run 读取
- `after` 从下一轮 run 的 evaluation 推导
- 最后一轮如果没有下一轮，则标记为 `pending_next_eval`

## Figures To Generate

用于 Beamer 和现场展示的图建议分两层：

### Per-run representative figures

- 布局图
- 温度场图
- overview 页面截图或导出图

### Aggregate figures

- `chip_max_temperature` 随轮次变化曲线
- 每轮改善量 `delta_chip_max` 曲线
- 修改类别时间线图
- 合法 / 非法提案分布图

## Beamer Structure

建议使用 `ctexbeamer`，正文 12 到 14 页，附录再放详细轮次页。

正文建议：

1. 标题页
2. 研究背景与目标
3. 问题定义
4. 物理建模与约束合理性
5. 初始状态为何不满足约束
6. LLM 可修改参数集合
7. 整体 workflow
8. run 编号与 iteration 的区别
9. 10 轮总体趋势
10. 代表性轮次一：材料调参
11. 代表性轮次二：非法提案与校验拒绝
12. 代表性轮次三：策略切换与多变量联动
13. 最终结果与分析
14. 局限性与后续工作

附录：

- `run_0001` 到 `run_0010` 逐轮记录

## Recommended Live Demo Flow

现场演示时建议只真实跑 1 轮：

1. 展示 baseline 状态与约束
2. 执行 1 轮真实 `examples/03_optimize_multicomponent_case.py`
3. 打开该轮 `proposal.json`、`evaluation.json` 和 overview 图
4. 切换到预先跑好的 10 轮官方数据集
5. 用总表和趋势图讲完整 workflow

这样最稳，也最容易回答老师提问。

## Risks

- 如果不隔离旧 `runs/`，编号和阶段混在一起，老师容易混淆
- 如果只展示 `proposal` 不展示 `after effect`，会显得 workflow 不完整
- 如果 10 轮中存在太多无效改动，汇报会显得算法能力不足
- 如果 Beamer 直接从原始 JSON 拼装而缺少人工叙述，老师会觉得材料机械

## Decision

以当前单案例为模板，构建一套独立的官方 10 轮演示数据集，并围绕该数据集生成总表、趋势图和中文 Beamer。现场只跑 1 到 2 轮，其余使用预先跑好的标准结果进行讲解。
