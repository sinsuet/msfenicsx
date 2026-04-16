# 热仿真真实物理合法性约束设计

## 1. 目标

在当前 LLM 驱动的二维稳态热仿真闭环中增加一层“提案合法性校验”，避免模型提出明显不现实或几何非法的修改。

当前阶段采用通用型方案，不绑定具体材料族，而是用宽松但现实的工程包络限制：

- 材料导热率必须位于合理范围
- 几何尺寸必须为正
- 组件之间不能重叠
- 组件必须保留在当前装配包络内
- 网格参数必须在安全范围内
- 单轮修改幅度不能过大

## 2. 设计原则

- 不把这层逻辑混进仿真 evaluator
- validator 只负责判断“提案是否合法”，不负责判断“结果是否满足目标”
- 默认不自动裁剪非法值，而是拒绝并记录原因
- 所有拒绝都要写入 run 目录，方便复盘和后续让模型学习

## 3. 当前采用的通用包络

基于常见工程材料的公开数据点，当前先采用以下保守包络：

- `conductivity`: `0.1 <= k <= 500.0`
- `components.*.width`: `> 0`
- `components.*.height`: `> 0`
- `mesh.nx`: `2 <= nx <= 300`
- `mesh.ny`: `2 <= ny <= 300`

单轮修改幅度限制：

- 导热率最多 `2x`，最少 `0.5x`
- 尺寸改动最多 `±50%`
- 位置改动最多整体包络宽高的 `25%`

几何限制：

- 所有组件必须位于当前外包络内
- 任意两个矩形组件不能有正面积重叠

## 4. 模块边界

新增：

- `src/validation/bounds.py`
- `src/validation/geometry.py`
- `src/validation/proposals.py`

职责划分：

- `bounds.py`: 数值范围与单轮步长限制
- `geometry.py`: 包络、正尺寸、矩形重叠
- `proposals.py`: 允许修改字段、应用提案后校验、结构化返回

## 5. 在闭环中的位置

流程调整为：

```text
LLM proposal
-> validate proposal
-> if invalid: write proposal_validation.json and mark decision invalid_proposal
-> if valid: apply to next_state.yaml
-> next iteration
```

## 6. 输出格式

每轮新增：

- `proposal_validation.json`

至少包含：

- `valid`
- `reasons`
- `checked_changes`

如果提案非法：

- 不生成新的 `next_state.yaml`
- `decision.json` 记录 `status=invalid_proposal`
- 本轮保持当前 state 不变

## 7. 参考依据

当前 `0.1 ~ 500 W/mK` 不是某个标准直接给出的统一区间，而是基于常见工程材料公开数据点做的通用工程推断：

- 聚合物薄膜量级约 `0.2 ~ 0.5 W/mK`
- 氧化铝/氮化铝基板约 `24 ~ 170 W/mK`
- 硅约 `149 W/mK`
- 铜约 `400 W/mK`

这个范围足够宽，适合当前“教学型二维热设计 + LLM 自动探索”阶段。
