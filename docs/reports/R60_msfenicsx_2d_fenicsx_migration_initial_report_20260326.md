# R60 面向二维 FEniCSx 热优化的 MsGalaxy 思路迁移初步研究报告（2026-03-26）

> Historical note on 2026-03-28: this migration report is retained as repository history and moved under `docs/reports/`. The earlier `docs/msgalaxy/` exploratory notes that fed into it were removed from the active repository because they no longer match the current `msfenicsx` mainline.

## 1. 任务背景

本报告的目标不是继续讨论 MsGalaxy 现有三维卫星布局主线本身，而是回答一个更贴近当前新项目推进的问题：

> 当问题从三维卫星组件排布切换为二维热布局，求解器从 `proxy + COMSOL` 切换为 `FEniCSx`，物理场暂时收敛为“仅热场”时，我们之前在 `msgalaxy` 里形成的 LLM 优化思路，哪些可以迁移，哪些必须重写，应该如何组织成一个可执行的二维研究路线。

当前我们关心的不是最终论文包装，而是先形成一份可供后续设计、实现和实验统一口径的初步研究文档。

本报告围绕三个明确候选路线展开：

1. `LLM direct`：由 LLM 直接基于结构化状态提出下一轮设计改动。
2. `Traditional optimizer`：引入传统优化器，例如 `pymoo`，优先考虑 `NSGA-II` 等算法。
3. `LLM + Traditional optimizer`：由 LLM 负责上层策略，传统优化器负责数值执行，`FEniCSx` 负责物理验真。

---

## 2. 当前两个项目的真实边界

### 2.1 `msgalaxy` 当前真实边界

从迁移期保留下来的 `msgalaxy` 研究结论来看，`msgalaxy` 当时的真实主线具有以下特征：

- 活跃主线是 `mass`。
- 默认稳定模式是 `position_only`。
- `operator_program / hybrid` 已接回主线，但仍是 `experimental`。
- 数值优化核心仍是 `pymoo`。
- 物理真实性闭环仍是 `proxy + COMSOL`。
- 最可信的 LLM 插入层不是“直接出最终布局”，而是“上层语义策略层”。

也就是说，`msgalaxy` 真正成熟的不是某个三维几何技巧本身，而是一条更重要的方法学边界：

> **LLM 不替代优化器，不替代物理求解器，而是在合同约束和真实性闭环之外层，负责搜索空间裁剪、算子策略控制和多保真调度。**

这是本次迁移里最值得保留的核心。

### 2.2 `msfenicsx` 当前真实边界

当前二维项目已经不是空白状态，而是已经具备了一个可运行的最小闭环雏形。现有仓库里已经存在：

- `states/baseline_multicomponent.yaml`
- `src/thermal_state/`
- `src/compiler/`
- `src/evaluator/`
- `src/llm_adapters/dashscope_qwen.py`
- `src/orchestration/optimize_loop.py`
- `src/validation/proposals.py`
- `src/optimization/variable_registry.py`

这意味着当前二维项目已经具备以下真实能力：

1. 使用结构化 `state.yaml` 描述二维热设计。
2. 将状态编译为 `FEniCSx` 热仿真并输出结构化指标。
3. 对结果做约束评估与目标汇总。
4. 使用 LLM 输出结构化 proposal。
5. 对 proposal 做白名单、范围、步长、几何合法性校验。
6. 按轮次保存 `state / evaluation / proposal / decision / outputs`。

因此，本项目当前并不是“先从 `msgalaxy` 搬一整套过来”，而是：

> **二维项目已经先走通了“LLM direct + FEniCSx” 这条最小闭环，而现在需要把 `msgalaxy` 里已经想清楚的方法论，反向迁移回来，帮助二维项目补齐传统优化器与策略层。**

---

## 3. 从迁移期研究结论可继承的稳定共识

`msgalaxy` 多份文档反复批判和收敛后，真正稳定的共识主要有六条，这六条都可以直接作为二维项目的上位原则：

1. 论文和方法都不应建立在“LLM 替代传统优化器”这一命题上。
2. 不应把“LLM 直接输出最终物理可行设计”当作最终主张。
3. 真正值得解决的问题，不是“算子够不够多”，而是“有没有上层策略层”。
4. LLM 最合理的位置是：
   - 搜索前先验生成；
   - 搜索中在线策略控制；
   - 多保真或预算调度。
5. 所有 LLM 输出都必须经过结构化合同和执行链校验。
6. 最可信的收益叙事应优先写成：
   - 更快进入可行域；
   - 更少浪费高代价仿真预算；
   - 更高可行率；
   - 更低无效试探与约束违规累计。

如果把这些原则翻译到二维热优化项目中，可以得到一句更贴切的话：

> **二维项目的最佳发展方向，不是继续强化“LLM 直接改状态”这一条单一路线，而是把它降级为一个基线或消融分支，同时逐步建立“传统优化器主执行 + LLM 上层策略”的完整架构。**

---

## 4. `msgalaxy -> 2D/FEniCSx` 可迁移性分析

### 4.1 可以直接迁移的方法骨架

以下能力可以直接迁移，而且应该成为二维项目后续架构设计的主骨架。

#### A. 结构化设计状态是唯一事实源

`msgalaxy` 的重要经验之一，是不要让 LLM 直接改脚本或绕过系统状态。在二维项目里，这一条已经被证明是正确方向：

- 设计状态放在 `state.yaml`
- 仿真由编译器和求解器负责
- LLM 只提出状态修改建议

这条路径可以继续保留，并且应作为后续接入传统优化器时的统一接口。

#### B. LLM 输出必须经过合同约束

在 `msgalaxy` 里，这表现为：

- `PolicyPack`
- allowlist
- contract guard
- proxy / real evaluator

在二维项目里，已经有一个轻量版雏形：

- 可编辑变量注册表
- proposal path allowlist
- 边界范围检查
- 步长限制
- 几何包络检查
- 组件重叠检查

这说明“LLM 可参与但不可越权”的治理方式完全可迁移。

#### C. 轨迹驱动的策略输入是有价值的

`msgalaxy` 文档里多次强调：

- 当前违规类型
- 历史算子轨迹
- 预算消耗
- guard hit 原因
- 阶段切换信号

这些信息应输入 LLM，而不是只给它当前一轮结果。

二维项目虽然没有完整的 `trace digest` 对象，但已经开始在 `optimize_loop.py` 中构造：

- `history_summary`
- `prior_invalid_feedback`
- `strategy_shift_hint`
- `objective_history`

这说明二维项目已经天然适合向“trajectory-conditioned policy”继续演化。

#### D. 分阶段推进而不是一步到位

`msgalaxy` 文档最稳的一点，是始终建议分阶段推进：

- 先静态先验
- 再在线策略
- 最后多保真调度

二维项目也应该沿用这个推进方式，而不是一上来同时追求：

- 传统优化器
- LLM 直接控制
- 多目标
- 多保真
- 复杂动作空间

分阶段是必要的。

### 4.2 需要重写后再迁移的部分

以下机制的思想可以迁移，但具体对象必须重写。

#### A. `position_only / operator_program / hybrid` 不能原样照搬

在 `msgalaxy` 中，这三个模式依附于三维卫星布局问题：

- `position_only` 本质是坐标搜索
- `operator_program` 本质是语义动作程序
- `hybrid` 是连续变量和动作变量混合搜索

迁移到二维项目后，建议重新定义为更贴近二维热设计的对象：

- `continuous_only`
  - 只优化连续设计变量
  - 如材料导热率、散热片宽高、位置等
- `operator_only`
  - 只优化离散动作族
  - 如“增强散热扩展”“向热源对齐”“减小热阻路径”
- `hybrid_2d`
  - 连续变量与动作模板混合

也就是说，模式思想可以保留，但名称、变量定义和语义必须重写。

#### B. `PlacementContractGuard` 需要改写成二维热设计合同

三维卫星布局问题的合同重点在：

- 挂载合法性
- 面向关系
- shell contact
- zone grammar

二维热设计问题更合理的合同应包括：

- 组件必须在设计域内
- 组件不得非法重叠
- 相邻或接触规则可显式定义
- 材料参数必须在物理合理范围
- 热源强度不得越界
- 局部几何变化需满足最小厚度、最小间隙、最大步长

因此可以迁移的不是原 guard 本身，而是“建立一个问题特定的 legality contract”的方法。

#### C. `proxy + COMSOL` 需要改写成二维版本的多保真链

当前新项目的求解器统一为 `FEniCSx`，这意味着 `msgalaxy` 中“proxy -> COMSOL promotion”这一多保真结构不能原样复制。

但它背后的方法论仍然成立：

- 并不是每个候选都值得用最贵的求解精度评估
- 需要有上层机制决定何时升格更高代价求解

对应到二维项目，可以考虑的二维版多保真链包括：

1. 粗网格 `FEniCSx` -> 细网格 `FEniCSx`
2. 简化边界条件 -> 完整边界条件
3. 简化几何热模型 -> 更细的多区域热模型

因此，“多保真调度”可以迁移，但应改写成 FEniCSx 内部不同精度等级，而不是 COMSOL。

### 4.3 不应直接迁移的部分

以下内容属于 `msgalaxy` 的三维卫星领域特定资产，不应直接迁入二维项目主叙事：

- `shell_contact_audit`
- `mount_face`
- `aperture`
- `SatelliteLikenessGate`
- STEP 导出链
- `.mph`
- COMSOL 语义接口
- 载荷、平台、shell 等卫星装配语义

这些内容至多可以提供“如何做工程合同与审计”的灵感，但不应成为二维项目当前文档的中心。

---

## 5. 三条候选路线的详细判断

### 5.1 路线 A：`LLM direct`

#### 定义

`LLM direct` 指的是：

- 当前状态进入仿真
- 系统生成评估报告
- LLM 直接输出下一轮结构化状态修改提案
- 系统校验后落地为 `next_state.yaml`

这也是当前二维项目已经实际跑通的路线。

#### 优势

1. 工程门槛低，现有仓库已具备基础设施。
2. 闭环非常清晰，便于快速验证“LLM 是否能读懂热结果并提出改动”。
3. 对教学演示、原型验证和生成案例很友好。
4. 容易积累：
   - proposal 轨迹
   - 失败原因
   - 变量偏好
   - 有效提案模式

#### 局限

1. 结果稳定性不够强，容易依赖模型当下的策略偏好。
2. 难以保证 matched-budget 下比成熟优化器更强。
3. 当变量变多、约束更复杂时，直接 proposal 的方差会快速变大。
4. 它更像“结构化启发式设计代理”，不像稳定的数值优化主引擎。

#### 在当前项目中的合理定位

这条路线不应被删除，但建议从“未来主方法”降级为：

- MVP 主线
- 快速探索基线
- 消融分支
- 用于收集高价值策略样本的先导系统

#### 还需要补的能力

- proposal 成功率统计
- invalid proposal 分类
- 变量类别切换分析
- 多轮收敛稳定性度量
- matched-budget 与传统优化器对照

---

### 5.2 路线 B：`Traditional optimizer`

#### 定义

这条路线指的是：

- 把二维热设计状态映射为优化变量向量
- 使用传统优化器进行搜索
- 每个候选都通过 `FEniCSx` 仿真与 evaluator 验真

如果只考虑“单一热目标 + 若干硬约束”，则并不一定必须一开始就用 `NSGA-II`。只有在引入多个目标后，`NSGA-II` 的多目标优势才会真正体现出来。

二维项目里更合理的起步方式可以是：

1. 先做 constrained single-objective baseline
2. 再扩展到 `pymoo`
3. 当第二目标明确后，再正式使用 `NSGA-II`

可能的第二目标包括：

- 芯片峰值温度最小化
- 材料代价最小化
- 改动幅度最小化
- 散热构件面积最小化
- 网格或求解开销代理最小化

#### 优势

1. 这是后续所有 LLM 结论最需要的对照基线。
2. 在连续变量空间里，传统优化器通常比直接 LLM proposal 更稳。
3. 更容易做 matched-budget 和多 seed 统计。
4. 一旦基线建立，后续 LLM 的收益才可被可信度量。

#### 局限

1. 需要先把问题表述得足够数值化。
2. 当变量具有强语义、强阶段性、强离散动作特征时，单纯数值搜索可能效率不足。
3. 如果一开始就做混合离散-连续、多目标、多保真，复杂度会显著上升。

#### 在当前项目中的合理定位

这条路线不是可选项，而是必须补齐的基础设施。理由很简单：

> **没有传统优化器基线，就无法客观判断“LLM direct”究竟是在真正优化，还是只是在少量变量里做碰运气式改动。**

---

### 5.3 路线 C：`LLM + Traditional optimizer`

#### 定义

这条路线不是“LLM 和优化器同时随意改状态”，而是：

- 传统优化器继续作为数值执行核心
- `FEniCSx` 继续作为物理真实性 evaluator
- LLM 只负责高层策略

更具体地说，LLM 可以负责输出：

- 变量族优先级
- 变量作用范围
- 初始 seed 建议
- 步长偏置
- 阶段切换建议
- 哪些候选值得升格到更高保真求解

#### 这条路线为什么最接近 `msgalaxy` 的可迁移精华

因为它完整保留了 `msgalaxy` 里最重要的边界：

1. LLM 不直接替代优化器。
2. LLM 不直接替代求解器。
3. LLM 负责策略，优化器负责执行，求解器负责验真。

这是最有方法论一致性的迁移方案。

#### 这条路线在二维项目里建议再拆成三层

#### C0. `static LLM prior`

LLM 在优化开始前生成：

- 变量优先级
- 初始 seed
- 初始步长偏好
- 不建议优先动的变量

这一步工程成本最低，也最容易最先得到可见收益。

#### C1. `online LLM policy`

LLM 根据运行轨迹动态调整：

- 变量类别切换
- 当前阶段应从材料转向几何还是反过来
- 是否采用更协调的多变量联动
- 哪类候选值得继续扩搜

这一步才是最接近 `msgalaxy` 文档主创新点的位置。

#### C2. `fidelity scheduler`

当二维项目后续形成了粗细两级求解链后，再让 LLM 决定：

- 哪些候选只值得粗评估
- 哪些候选值得细求解
- 哪些失败模式应先反思再继续

这一步应作为第三阶段，而不是第一阶段。

#### 这条路线的合理定位

这条路线应被视为当前二维项目最值得追求的主线方法。

---

## 6. 推荐的二维项目总体架构

为了让迁移不是停留在概念层，下面给出一个更贴近当前仓库的二维版架构建议。

### 6.1 总体数据流

建议把未来二维项目明确组织为：

```text
Design State
  -> Compiler / Runner (FEniCSx)
  -> Evaluator
  -> Optimizer Core
  -> LLM Policy Layer
  -> Safety Contract
  -> Next Candidate / Next State
  -> Trace / Compare / Branch
```

更具体一点：

```text
state.yaml
  -> geometry/material/load compiler
  -> FEniCSx solve
  -> thermal metrics + constraint report
  -> optimizer asks for candidate generation/update
  -> LLM provides strategy prior or policy update
  -> proposal/candidate validation
  -> next_state or next population
  -> run artifacts
```

### 6.2 建议保留的核心层

#### A. `DesignState`

继续使用 `state.yaml` 作为唯一事实源，不让任何外部模块直接越过状态层修改求解代码。

#### B. `ThermalCompilerRunner`

继续保留当前 `src/compiler/` 结构，保证“给定同一状态，得到尽可能确定的仿真结果”。

#### C. `Evaluator`

继续保留 `src/evaluator/`，但后续要补更多便于优化器和策略层读取的派生指标，例如：

- 热热点位置
- 温度梯度相关统计
- 组件间温差
- 目标改进幅度
- 候选求解耗时

#### D. `OptimizerCore`

新增一个真正的优化器层，用于封装：

- 参数编码与解码
- 候选生成
- 约束处理
- `pymoo` 接入

#### E. `LLMPolicyLayer`

新增一个明确的策略层对象，不直接输出最终状态，而是优先输出：

- policy prior
- category bias
- variable scope
- candidate shortlist rule
- promotion suggestion

#### F. `SafetyContract`

继续复用当前 proposal validation 思路，并逐步拓展为二维问题的统一合同层。

### 6.3 建议新增的中间对象

建议在二维项目中引入一个轻量版 `PolicyPack2D`，不要直接沿用 `msgalaxy` 的名字，但可以保留其结构思想。

建议字段包括：

- `policy_version`
- `variable_category_prior`
- `variable_scope_prior`
- `initial_seed_bias`
- `step_scale_bias`
- `joint_change_preference`
- `candidate_promotion_rule`
- `confidence`
- `rationale`
- `evidence_refs`

这个对象的意义在于：

1. 让 LLM 输出保持结构化。
2. 让策略层和执行层分离。
3. 便于做消融和可解释分析。
4. 避免把 LLM 直接绑定到某一种优化算法实现上。

---

## 7. 二维版变量与动作空间建议

为了让二维项目后续能从 `continuous-only` 自然过渡到 `hybrid_2d`，建议提前把变量和动作分开建模。

### 7.1 建议的连续变量分组

当前最适合先纳入传统优化器的连续变量包括：

- 材料类
  - `base_material.conductivity`
  - `spreader_material.conductivity`
- 几何尺寸类
  - `heat_spreader.width`
  - `heat_spreader.height`
- 几何位置类
  - `heat_spreader.x0`
  - `heat_spreader.y0`

当前不建议优先纳入主优化空间的变量包括：

- 热源强度
  - 更适合作为场景或鲁棒性分析参数，而不是核心设计改进杠杆
- 网格参数
  - 更适合作为求解精度控制变量，而不是主优化变量

### 7.2 建议的二维动作族

如果后续要引入二维版 `operator_program` 思路，建议先定义少量高价值动作族，而不是一开始就做复杂 DSL。

例如：

- `boost_spreading_material`
  - 提高散热扩展材料导热率
- `expand_spreader`
  - 增大散热扩展块宽度或厚度
- `reposition_spreader_toward_hotspot`
  - 向热源热点方向靠近，但保持合法间隙
- `improve_base_extraction`
  - 提高底板导热能力
- `coordinated_spreader_plus_base`
  - 联动调整扩展块和底板
- `local_refine_after_feasible`
  - 可行后做小步精修

这些动作族并不是要马上替代连续变量，而是为后续 `LLM + optimizer` 提供上层语义控制入口。

### 7.3 二维版模式建议

建议后续以如下定义替换三维项目中的旧模式名：

- `continuous_only`
  - 只对连续变量做数值优化
- `operator_guided`
  - 由 LLM 生成动作或策略，系统执行有限改动
- `hybrid_2d`
  - 连续变量搜索 + 动作族策略控制

这样命名更贴近当前二维问题，也更利于后续写文档和实验。

---

## 8. 建议的实验口径与最小实验矩阵

这里需要明确区分两件事：

1. 工程推进顺序
2. 论文或研究对照顺序

两者不必完全相同。

### 8.1 工程推进顺序

建议按下面顺序推进：

#### Phase E0：冻结当前 `LLM direct` 闭环

目标：

- 把当前已有链条稳定下来
- 固化日志口径
- 固化评估器输出
- 补 proposal 成功率与轨迹统计

#### Phase E1：补齐传统优化器基线

目标：

- 把当前连续变量映射成优化向量
- 先跑 constrained single-objective baseline
- 再接 `pymoo`

#### Phase E2：接入 `static LLM prior`

目标：

- 让 LLM 先只控制初始化前的变量优先级和 seed
- 不直接在线接管整个搜索过程

#### Phase E3：接入 `online LLM policy`

目标：

- 基于轨迹与违规模式调整变量类别和搜索阶段

#### Phase E4：接入二维版 `fidelity scheduler`

目标：

- 在形成粗细两级求解链后，再研究预算调度

### 8.2 研究对照矩阵

当需要形成对照实验时，建议至少保留以下几组：

- `B0`: `continuous_only + traditional optimizer`
- `B1`: `LLM direct`
- `B2`: `traditional optimizer + static LLM prior`
- `B3`: `traditional optimizer + online LLM policy`

如果后续有了两级求解链，再增加：

- `B4`: `traditional optimizer + online LLM policy + fidelity scheduler`

### 8.3 为什么不建议把 `LLM direct` 当主方法

因为它更适合作为：

- 对照分支
- 消融分支
- 先导探索系统

但从 `msgalaxy` 的经验和二维项目现有实验现象来看，它都不适合作为最终论文主命题。其最大价值在于：

- 快速找到有效变量
- 形成策略样本
- 验证 LLM 是否具备热设计语义理解能力

而不是替代传统优化器。

### 8.4 建议的指标体系

当前二维项目最建议优先统一的指标包括：

- `feasible_rate`
- `first_feasible_eval`
- `best_objective_value`
- `objective_improvement_ratio`
- `invalid_proposal_rate`
- `average_solver_calls_to_first_feasible`
- `wall_time_to_first_feasible`
- `category_switch_count`
- `variable_usage_distribution`

如果后续引入两级求解链，再增加：

- `high_fidelity_calls_to_first_feasible`
- `promotion_precision`
- `proxy_fine_gap`

### 8.5 统计和结论边界

后续若要形成可信结论，至少应满足：

- matched budget
- 相同初始状态
- 相同约束
- 相同变量集合
- 相同求解精度配置
- 多 seed 重复

否则只能算工程观察，不能算稳定方法结论。

---

## 9. 风险、边界与不应过度主张的内容

### 9.1 风险一：把二维问题写得过于像三维卫星问题

虽然本次迁移来自 `msgalaxy`，但当前二维项目本质上是：

- 二维热设计优化
- 教学/原型/方法验证导向

它并不是三维卫星布局主线的等价替身。因此不应把二维结果直接写成“三维卫星布局优化已经被验证”的旁证。

### 9.2 风险二：直接把 `NSGA-II` 当默认唯一选择

如果当前问题暂时只有单一主目标，那么强行使用 `NSGA-II` 并不会自动让方法更好。只有当第二目标被清晰定义后，`NSGA-II` 才具备天然优势。

因此应先区分：

- 这是“单目标约束优化”
还是
- 这是“真正多目标优化”

### 9.3 风险三：继续高估 `LLM direct`

当前二维项目已经说明 `LLM direct` 有用，但这不等于：

- 它能稳定替代优化器
- 它天然比传统搜索更强
- 它在变量扩展后仍保持稳定

因此应把它放在正确位置上。

### 9.4 风险四：过早引入复杂动作空间

如果在传统优化器基线尚未建立前，就同时引入：

- 动作 DSL
- 多目标
- 多保真
- 在线策略层

系统复杂度会显著上升，且很难定位收益来自哪里。

### 9.5 当前不应宣称的内容

在后续实验做扎实之前，不应宣称：

- LLM 已全面优于传统优化器
- 二维项目已经证明 `LLM + optimizer` 在统计上稳定领先
- 当前二维结果可直接代表三维卫星布局主线
- 当前已完成二维版 `msgalaxy` 全迁移

---

## 10. 最终建议

综合 `msgalaxy` 文档的稳定结论、当前二维项目的真实仓库状态，以及三条候选路线的可行性，本报告给出以下最终建议：

1. **迁移的核心不是迁移三维几何机制，而是迁移方法论边界。**
   - 保留“LLM 只做策略层，不替代优化器与求解器”的原则。

2. **当前二维项目可以继续保留 `LLM direct`，但应把它降级为基线或消融分支。**
   - 它适合原型验证，不适合最终主命题。

3. **应尽快补齐传统优化器基线。**
   - 先做连续变量单目标约束优化；
   - 再视目标定义扩展到 `pymoo / NSGA-II`。

4. **最值得追求的主线方法是 `LLM + Traditional optimizer`。**
   - 第一阶段：`static LLM prior`
   - 第二阶段：`online LLM policy`
   - 第三阶段：二维版 `fidelity scheduler`

5. **二维项目的推荐主叙事应写成：**

> 在二维热设计优化中，LLM 不直接替代数值优化器，也不替代 `FEniCSx` 物理求解器，而是作为一个受结构化合同约束的策略层，为传统优化器提供变量优先级、阶段切换和候选升格策略，从而提升进入可行域的效率与整体搜索质量。

---

## 11. 建议的下一步

如果下一步要把本报告继续往“可实施方案”推进，建议依次完成以下工作：

1. 冻结当前二维项目的 `LLM direct` 基线口径。
2. 明确当前问题究竟是单目标还是多目标，并据此决定 `NSGA-II` 的接入时机。
3. 为连续变量建立优化向量编码与解码层。
4. 接入一个最小传统优化器 baseline。
5. 设计二维版 `PolicyPack2D`。
6. 把 LLM 从“直接改状态”逐步抬升到“控制优化器怎么搜”。

到这一步之后，`msgalaxy` 里的核心思路才算真正被迁移并落在二维项目上。
