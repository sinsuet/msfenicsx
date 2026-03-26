# 当前单案例可优化变量注册表设计

## 1. 目标

把当前单案例的“允许改哪些变量、每个变量的边界和步长是什么”从散落规则升级成一个统一的变量注册表。

这样做的原因是：

- LLM 现在还缺少明确的可操作空间说明
- validator 目前更多是前缀级允许，而不是变量级允许
- 后续想做变量优先级、联动规则、提案质量分析，都需要统一元数据

## 2. 首版范围

当前单案例首版先开放这 6 个变量：

- `materials.spreader_material.conductivity`
- `materials.base_material.conductivity`
- `components.2.width`
- `components.2.height`
- `components.2.x0`
- `heat_sources.0.value`

## 3. 每个变量需要描述的信息

- `path`
- `label`
- `description`
- `category`
- `min_value`
- `max_value`
- `step_rule`
- `priority`

## 4. 接入位置

- `src/optimization/variable_registry.py`
  - 统一维护允许变量及元数据
- `src/validation/proposals.py`
  - 改为按注册表判断某个 path 是否允许修改
- `src/llm_adapters/dashscope_qwen.py`
  - prompt 里显式列出允许变量、边界和步长

## 5. 预期效果

- 模型不再只知道“能改 materials/components/mesh”，而是知道当前案例真正允许动哪些变量
- validator 能更精准地拒绝未注册或越界的改动
- 后续可以基于同一注册表做变量优先级和多变量协同策略
