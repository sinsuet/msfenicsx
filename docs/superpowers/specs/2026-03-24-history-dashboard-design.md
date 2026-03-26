# 多轮优化历史工作台设计

## 1. 目标

在当前已经具备单轮 `overview.html` 的基础上，增加一个面向多轮闭环优化的 `history.html`。

它不只是“列出 run 目录”，而是一个可分析的历史工作台，回答三类问题：

- 每轮指标是怎么变化的
- 大模型每轮为什么这样改
- 哪一轮被 evaluator 或 validator 拦住了

## 2. 首版定位

首版采用“分析工作台型”而不是简单总览页。

核心结构为：

- 顶部摘要条
- 左侧趋势区
- 右侧轮次详情区
- 底部对比区

## 3. 页面结构

### 3.1 顶部摘要条

显示：

- 总轮次数
- 最新轮次编号
- 当前最佳 `chip_max_temperature`
- 最新状态
- 最新模型名
- token 用量摘要

### 3.2 左侧趋势区

至少包含：

- `chip_max_temperature` 折线
- `temperature_max` 折线
- 每轮状态条带
- 每轮约束/校验命中摘要

### 3.3 右侧详情区

点击某轮后显示：

- `evaluation.json`
- `proposal.json`
- `proposal_validation.json`
- `decision.json`
- 跳转到该轮 `overview.html`

### 3.4 底部对比区

展示当前选中轮与上一轮的关键差异：

- 改动字段
- 指标变化量
- 是否从 `invalid_proposal` 变成 `proposal_applied`

## 4. 数据来源

页面不直接扫描零散文件，而是读取统一汇总文件：

- `runs/history_summary.json`

该文件由单独的历史汇总器生成，避免页面自己解析大量 JSON 文件。

## 5. 文件结构

新增：

- `src/orchestration/history_report.py`
- `examples/04_build_history_dashboard.py`

修改：

- `src/msfenicsx_viz.py`

输出：

- `runs/history_summary.json`
- `runs/history.html`

## 6. `history_summary.json` 字段

每轮至少包含：

- `run_id`
- `status`
- `feasible`
- `chip_max_temperature`
- `temperature_max`
- `validation_valid`
- `validation_reasons`
- `decision_summary`
- `changes`
- `model_info`
- `overview_html`
- `temperature_html`

## 7. 首版范围控制

首版不做：

- 多轮温度场动画
- 场级 diff 可视化
- 自动实时刷新
- 浏览器内直接编辑状态

首版先采用“手动重建”模式：

```bash
python examples/04_build_history_dashboard.py
```

## 8. 错误处理

- 某轮文件缺失时，该轮仍显示，但标记为 `incomplete`
- 某字段缺失时显示 `N/A`
- 汇总器全量重建 `history_summary.json`

## 9. 验证目标

完成后至少要满足：

- 能扫描现有 `runs/run_xxxx/`
- 能生成 `runs/history_summary.json`
- 能生成 `runs/history.html`
- 页面中可见真实轮次，例如 `run_0009`、`run_0010`
- 能打开每轮 `overview.html`
