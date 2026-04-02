# 四篇中文进度报告与后续 Beamer 写作设计

Date: 2026-04-01

> Status: user-approved reporting design for the current paper-facing `NSGA-II` thermal optimization mainline.
>
> This design defines how to write four Chinese reports first, then compress them into a later LaTeX Beamer deck without changing the evidence contract.

## 1. 目标

围绕仓库当前已经实现并已有运行证据支撑的主线，先写四篇中文报告，再将四篇报告收束为一套汇报型 Beamer。

本轮写作的目标不是重新定义研究方向，而是把当前已经形成的主线叙事写清楚：

1. 问题是什么
2. 平台怎么组织
3. `raw / union / llm-union` 的比较框架为什么成立
4. 当前 `LLM-union` 方法到底做了什么
5. 我们最有代表性的实验应该怎么讲，哪些结果可以说，哪些结果只能作为阶段性观察

## 2. 当前主线与证据边界

四篇报告必须全部围绕当前 paper-facing 主线展开，不引入已经退役的旧路线，不混用平台探索线和论文主线。

当前主线固定为：

- benchmark template:
  - `scenarios/templates/panel_four_component_hot_cold_benchmark.yaml`
- evaluation spec:
  - `scenarios/evaluation/panel_four_component_hot_cold_baseline.yaml`
- paper-facing raw baseline:
  - `scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml`
- paper-facing hybrid-union design:
  - `docs/superpowers/specs/2026-03-28-nsga2-hybrid-union-controller-design.md`
- paper-facing openai-compatible `LLM` design:
  - `docs/superpowers/specs/2026-03-28-openai-union-llm-controller-design.md`

必须遵守的写作边界：

1. `raw / union / llm-union` 的比较必须明确为同一 benchmark、同一 8 维设计变量、同一 repair、同一热求解与评估流程、同一预算下的 proposal/control 差异比较。
2. 不能把 action-space expansion 说成 decision-space expansion。
3. 不能把某一条 seed 上的成功写成“统一框架已经全面优于其他方法”。
4. 对于尚未多 seed 完整稳定验证的 controller 修复，只能写成阶段性证据、机制观察或可迁移 kernel 假设。

## 3. 总体叙事顺序

建议四篇报告按下面的逻辑顺序写：

1. 先定义问题和建模对象，让听众知道我们到底在优化什么。
2. 再给出主线架构，让听众知道为什么会有 `raw / union / llm-union` 三条线。
3. 再单独展开 `LLM-union` 的状态、决策、提示、回退与 trace 机制。
4. 最后用一次代表性实验把整条链路从输入、决策到结果讲通，并补充多方法对照指标。

这套顺序最适合后续转成 Beamer，因为它天然对应：

- 问题页
- 方法页
- 机制页
- 结果页

## 4. 交付物定义

本轮中文材料固定为四篇报告：

1. 《主线问题定义与热优化建模》
2. 《主线 raw / union / llm-union 架构总体思路》
3. 《当前 LLM-union 优化架构方法与细节》
4. 《代表性实验全流程复盘与方法对比》

后续 Beamer 不单独重新设计叙事，而是直接由这四篇报告压缩重组。

## 5. 第一篇报告设计

### 5.1 目标

把当前主线 benchmark 的问题定义写到足够细，让读者在不看代码的情况下也能明白：

- 几何域是什么
- 组件是什么
- 组件有哪些属性
- 热工况是什么
- 优化变量是什么
- 多目标与约束是什么
- 建模链条怎么串起来

### 5.2 必写内容

第一篇必须包含以下部分：

1. 研究背景与问题动机
2. 面板二维导热场景定义
3. 主线 benchmark 的几何域与区域约束
4. 组件生成规则与组件属性
5. 顶部 radiator 边界特征定义
6. 热工况定义：
   - hot case
   - cold case
7. 设计变量编码：
   - `processor_x`
   - `processor_y`
   - `rf_power_amp_x`
   - `rf_power_amp_y`
   - `battery_pack_x`
   - `battery_pack_y`
   - `radiator_start`
   - `radiator_end`
8. 多目标定义
9. 约束定义
10. `scenario_template -> thermal_case -> thermal_solution -> evaluation_report -> optimization_result` 建模链
11. 为什么这是一个昂贵约束多目标 multicase 优化问题

### 5.3 必须落表的信息

第一篇至少做四张表：

1. 面板与区域约束表
2. 四类组件属性表
3. hot / cold 工况参数表
4. 目标与约束汇总表

### 5.4 关键源文件

- `scenarios/templates/panel_four_component_hot_cold_benchmark.yaml`
- `scenarios/evaluation/panel_four_component_hot_cold_baseline.yaml`
- `scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml`
- `README.md`

## 6. 第二篇报告设计

### 6.1 目标

把当前主线上的三条架构线写清楚：

- `raw`
- `union-uniform`
- `llm-union`

第二篇是“总架构篇”，重点不是 prompt 细节，而是：

- 三条线共用什么
- 三条线只改什么
- 为什么这个比较是公平的

### 6.2 必写内容

第二篇必须包含以下部分：

1. 主线研究问题与方法梯子
2. `raw` 的定义：
   - 纯 `NSGA-II`
   - 原生 `SBX + PM`
3. `union-uniform` 的定义：
   - 同一 `NSGA-II` 骨架
   - 混合 action registry
   - `random_uniform` 控制器
4. `llm-union` 的定义：
   - 同一 `NSGA-II` 骨架
   - 同一 mixed action registry
   - `llm` 控制器
5. 三条线共享的部分：
   - benchmark source
   - evaluation spec
   - 设计变量编码
   - repair
   - 热求解与评价
   - survival semantics
   - artifact contract
6. 三条线不同的部分：
   - proposal layer
   - controller layer
7. 从 `raw_driver` 到 `union_driver` 的运行链条对比
8. 为什么这套比较能隔离：
   - action-space expansion 的贡献
   - controller intelligence 的贡献

### 6.3 必须落图的信息

第二篇至少做两张图：

1. `raw / union / llm-union` 三线统一框图
2. proposal-time control 插入点示意图

### 6.4 关键源文件

- `docs/superpowers/specs/2026-03-28-nsga2-hybrid-union-controller-design.md`
- `optimizers/drivers/raw_driver.py`
- `optimizers/drivers/union_driver.py`
- `optimizers/algorithm_config.py`
- `README.md`

## 7. 第三篇报告设计

### 7.1 目标

完整展开当前 `LLM-union` 的方法和实现细节，使这一篇既可以作为内部技术说明，也可以直接为论文方法章节和 Beamer 方法页供稿。

### 7.2 方法主线

第三篇要把 `LLM-union` 写成：

- 一个固定 action registry 上的 `LLM`-guided operator hyper-heuristic
- 一个放在 proposal layer 的 controller
- 一个不改动 decision encoding、repair、evaluation 和 survival 的策略层

### 7.3 必写内容

第三篇必须包含以下部分：

1. `LLM-union` 的方法定位
2. 固定混合 action registry：
   - `native_sbx_pm`
   - `sbx_pm_global`
   - `local_refine`
   - `hot_pair_to_sink`
   - `hot_pair_separate`
   - `battery_to_warm_zone`
   - `radiator_align_hot_pair`
   - `radiator_expand`
   - `radiator_contract`
3. controller state 的构成：
   - `run_state`
   - `parent_state`
   - `archive_state`
   - `domain_regime`
   - `progress_state`
   - `recent_decisions`
   - `operator_summary`
4. phase-aware policy kernel：
   - `cold_start`
   - `prefeasible_progress`
   - `prefeasible_convert`
   - `post_feasible_*`
5. candidate shaping 与 suppress / reset 逻辑
6. prompt projection 与 compact state 投影
7. OpenAI-compatible client 边界：
   - provider
   - model
   - capability profile
   - structured JSON output
8. repository-side validation：
   - schema validity
   - semantic validity
9. fallback 机制：
   - `random_uniform`
10. trace 机制：
   - `controller_trace.json`
   - `operator_trace.json`
   - `llm_request_trace.jsonl`
   - `llm_response_trace.jsonl`
   - `llm_metrics.json`
11. 当前 guardrail 的作用边界与阶段性定位

### 7.4 方法篇中的关键实现锚点

- `optimizers/operator_pool/llm_controller.py`
- `optimizers/operator_pool/state_builder.py`
- `optimizers/operator_pool/policy_kernel.py`
- `optimizers/operator_pool/prompt_projection.py`
- `optimizers/operator_pool/operators.py`
- `llm/openai_compatible/client.py`

## 8. 第四篇报告设计

### 8.1 目标

第四篇不是泛泛的“结果汇总”，而是一次完整实验的全流程复盘：

- 输入是什么
- 控制器怎么选 action
- 搜索怎么进入可行域
- Pareto 解怎么形成
- 三种方法在同预算下分别表现如何

### 8.2 主案例选择

第四篇正文主案例推荐采用 `seed-23` 的同预算对照，因为它最适合说明当前 `LLM` controller 的方法价值。

推荐主案例文件：

- raw:
  - `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-raw-multiseed/seed-23-real-test/optimization_result.json`
- union-uniform:
  - `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-uniform-multiseed/seed-23-real-test/optimization_result.json`
- llm:
  - `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-window-guardrail-multiseed/seed-23-real-test/optimization_result.json`

推荐原因：

1. 三条线都是 `129` evaluations 的同预算结果。
2. `seed-23` 上 `LLM` 相比 `raw` 与 `union-uniform` 在“进入可行域速度”和“可行解占比”上更适合讲清方法价值。
3. 这个案例非常适合汇报式叙事，因为 raw 和 uniform 都不是完全失败，比较更有解释力。

### 8.3 `seed-23` 主案例的当前已核对指标

- raw:
  - `feasible_rate = 0.0930`
  - `first_feasible_eval = 78`
  - `pareto_size = 5`
- union-uniform:
  - `feasible_rate = 0.0078`
  - `first_feasible_eval = 127`
  - `pareto_size = 1`
- `GPT-5.4 window-guardrail llm`:
  - `feasible_rate = 0.1473`
  - `first_feasible_eval = 42`
  - `pareto_size = 4`

因此，第四篇正文适合把 `seed-23` 写成：

- `raw` 能做出可行解，但进入可行域较晚
- `union-uniform` 在该 seed 上显著退化
- `LLM` 在同 action space 下恢复并加速了可行性进入

### 8.4 作为补充的“当前最好绝对结果”快照

第四篇末尾应补一个短节，说明当前 paper-facing 三线中绝对最强的一次不是 `seed-23 llm`，而是 `seed-17 union-uniform`。

建议补充的对照文件：

- raw:
  - `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-raw-multiseed/seed-17-real-test/optimization_result.json`
- union-uniform:
  - `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-uniform-multiseed/seed-17-real-test/optimization_result.json`
- llm current best checked:
  - `scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full/2026-04-01-kernel-validation-seed17/optimization_result.json`

当前已核对指标：

- raw:
  - `feasible_rate = 0.1318`
  - `first_feasible_eval = 70`
  - `pareto_size = 9`
- union-uniform:
  - `feasible_rate = 0.2248`
  - `first_feasible_eval = 34`
  - `pareto_size = 22`
- `GPT-5.4 full kernel-validation llm`:
  - `feasible_rate = 0.2016`
  - `first_feasible_eval = 39`
  - `pareto_size = 13`

这一节的定位应当是：

- 给出当前最好绝对结果的快照
- 保持诚实
- 说明 `LLM` 目前已有强正向结果，但还不能写成“稳定全面优于 uniform”

### 8.5 第四篇必须包含的内容

1. 实验配置与预算
2. 三方法共用条件与唯一差异
3. baseline 候选与初始不可行状态
4. 早期搜索阶段
5. 首次进入可行域的代际与 evaluation index
6. 可行解积累与 Pareto 形成过程
7. 代表解提取：
   - `min_hot_pa_peak`
   - `max_cold_battery_min`
   - `min_radiator_resource`
   - `knee_candidate`
8. 主案例中的 controller / operator trace 解释
9. 三方法表格对照
10. 当前最好绝对结果快照
11. 当前结论、未完成验证与下一步工作

### 8.6 第四篇建议使用的代表解材料

`seed-23 llm` 已核对代表解中至少可以重点讲：

- `knee_candidate`:
  - evaluation index `73`
- `min_hot_pa_peak`:
  - evaluation index `126`

这两个代表解已经能支撑：

- 三目标值
- 四项约束 margin
- hot / cold 两工况的关键温度指标
- radiator span 与布局变量

## 9. 四篇报告的统一写作规则

四篇报告必须共享同一套口径：

1. 所有结果都写清楚 template、benchmark seed、algorithm seed、evaluation budget 和 artifact path。
2. 所有比较都优先使用：
   - `feasible_rate`
   - `first_feasible_eval`
   - `pareto_size`
   - 代表解目标值
   - 关键约束 margin
3. 对尚未完成多 seed 完整验证的 controller 改进，统一使用：
   - “阶段性证据”
   - “机制观察”
   - “可迁移 kernel 假设”
4. 不把单 seed 现象写成一般结论。

## 10. 从四篇报告到 Beamer 的压缩映射

后续 Beamer 建议压缩为 14 到 18 页，映射关系如下：

1. 封面与任务背景
2. 问题定义总览
3. benchmark 几何域、组件、工况
4. 多目标与约束
5. `raw / union / llm-union` 总架构
6. 公平比较原则
7. `LLM-union` state 与 action registry
8. policy kernel / prompt / fallback 机制
9. 主案例实验设置
10. 主案例可行性进入对比
11. 主案例 Pareto 与代表解对比
12. trace 机制与 operator 行为解释
13. 当前最好绝对结果快照
14. 阶段性结论与下一步工作

## 11. 推荐执行顺序

后续实际写作顺序固定为：

1. 先写第一篇
2. 再写第二篇
3. 再写第三篇
4. 最后写第四篇
5. 四篇完成后再做 Beamer

原因是：

- 第一篇提供名词和建模基础
- 第二篇提供总框架
- 第三篇提供方法细节
- 第四篇最后写时，最容易统一各篇口径

## 12. 本设计的完成标准

当且仅当满足以下条件时，本设计算可执行：

1. 四篇报告的题目、目标、章节和证据来源全部明确。
2. 第四篇主案例与补充快照案例都已经指定。
3. `raw / union / llm-union` 的公平比较边界已经写死。
4. 后续 Beamer 的页级映射已经确定。

本设计完成后，下一步直接进入第一篇中文报告正文起草。
