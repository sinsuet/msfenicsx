# R58 面向当前 MASS 主线的 LLM 策略层正式研究报告（2026-03-26）

## 1. 报告摘要

本报告面向 MsGalaxy 当前真实可运行的 `mass` 主线，目标不是讨论“LLM 能否替代优化器”，而是回答一个更贴近当前系统与论文发表的核心问题：

> 在不绕开 `pymoo + proxy/COMSOL` 可执行闭环的前提下，如何把 LLM 插入当前 MASS 流程，作为高层策略器去缓解混合搜索空间的割裂、算子组合爆炸、合同投影碎裂和高保真预算浪费，并形成一条可验证的论文叙事。

本报告的核心结论是：

1. 当前仓库的真实主线是 `mass`，默认稳定模式是 `position_only`，`operator_program / hybrid` 已接入主线但仍是 `experimental`。
2. 历史 `vop_maas` 文档可作为思想来源，但不能作为“当前已实现模式”来叙述。
3. 近三年高质量工程领域 LLM 文献普遍支持的不是“LLM 直接替代数值优化器”，而是“LLM 作为结构化设计语言生成器、工具调用器、工作流控制器或上层策略器”。
4. 因此，对 MsGalaxy 最合理、也最有论文说服力的方案，是构建一个 `LLM-guided policy layer over MASS`：
   - LLM 负责选择/裁剪搜索空间、生成算子先验、调度多保真仿真预算。
   - `pymoo` 继续作为唯一数值优化核心。
   - `proxy + COMSOL` 继续作为唯一物理真实性闭环。
5. 最稳健的论文主创新点应写成：

> **LLM-guided semantic operator policy for contract-safe hybrid satellite layout optimization under multi-fidelity physics feedback**

而不是：

- “LLM 直接替代 NSGA-II”
- “LLM 直接生成最终可行卫星布局”
- “LLM 普遍优于传统优化器”

## 2. 当前系统真实边界

本报告严格遵循当前仓库真相，不把历史草案或规划态能力误写成现状。

### 2.1 当前已实现真相

- 活跃主线是 `mass` 单栈场景运行时。
- 唯一稳定化场景仍是 `optical_remote_sensing_bus`。
- 默认稳定搜索空间是 `position_only`。
- `operator_program / hybrid` 已接入主线，且已有受控 real-chain evidence，但仍属 `experimental`。
- 当前真实可落地的关键入口与模块包括：
  - `workflow/scenario_runtime.py`
  - `optimization/modes/mass/pymoo_integration/search_space_factory.py`
  - `optimization/modes/mass/pymoo_integration/operator_problem_generator.py`
  - `optimization/modes/mass/pymoo_integration/operator_program_codec.py`
  - `optimization/modes/mass/meta_policy.py`
  - `optimization/modes/mass/trace_features.py`
  - `optimization/knowledge/mass/mass_rag_system.py`

### 2.2 当前不能误写的内容

- 不能把 `vop_maas` 描述为当前活跃运行模式。
- 不能把 `MP-OP-MaaS v3` 描述为已完成能力。
- 不能把 `operator_program / hybrid` 现有单场景证据表述成“稳定优于 baseline”的发表级结论。
- 不能把 LLM 写成直接输出最终坐标并绕开 `pymoo` 与硬约束合同。

### 2.3 与历史 `vop_maas` 资料的关系

历史资料可参考：

- `docs/archive/reports/R28_vop_maas_master_plan_20260307.md`
- `docs/archive/reports/R39_vop_maas_architecture_paper_plan_20260309.md`

这些文档对于“LLM 作为上层策略/算子控制器”的叙事仍有价值，但本报告的落脚点已经切换为：

> 在当前重构后的 `mass` 真实架构内实现 LLM 策略层，而不是恢复旧模式命名或旧入口。

## 3. 文献筛选标准

本报告将主文献集合限制为约 10 篇，筛选规则如下：

1. 发表时间限制在近三年，具体按 `2024-01-01` 到 `2026-03-26`。
2. 仅保留一区期刊或 A 类会议论文。
3. 必须与工程设计、CAD/CAE、布局设计、仿真驱动优化、多智能体工程工作流、或优化器/求解器协同中的 LLM 使用方式直接相关。
4. 必须能提供官方来源链接，优先采用出版社、会议官网或 DOI 页面。
5. 只把“与当前 MASS 问题同构或强相邻”的论文列为主文献；一般性 agent、纯 benchmark、纯代码生成论文不纳入主表。

说明：

- “Q1/A-tier” 采用工程与计算机领域常见评价口径进行筛选，具体分区标签可能因数据库和年度更新略有差异。
- 本报告对每篇文献均给出官方链接，便于后续人工复核。

## 4. 近三年主文献集合（10 篇）

| 编号 | 文献 | 年份/场景 | 期刊/会议质量 | 与本课题的直接关系 | 官方链接 |
| --- | --- | --- | --- | --- | --- |
| P1 | FloorPlan-LLaMa: Aligning Architects' Feedback and Domain Knowledge in Architectural Floor Plan Generation | 2025 | ACL 2025，A 类会议 | 说明 LLM 可吸收领域知识与人类反馈，生成受约束平面方案，支持“LLM 做上层语义生成而不是直接数值优化” | https://aclanthology.org/2025.acl-long.1127/ |
| P2 | LLM-based framework for automated and customized floor plan design | 2025 | Automation in Construction，Q1 | 与“从需求到设计方案”的工程生成流程高度相近，支持需求语义到布局先验的映射 | https://doi.org/10.1016/j.autcon.2025.106512 |
| P3 | EPlus-LLM: A large language model-based computing platform for automated building energy modeling | 2024 | Applied Energy，Q1 | 说明 LLM 可以把非结构化输入转成可执行仿真模型，直接支撑“LLM 插在建模/流程前端”的设计 | https://doi.org/10.1016/j.apenergy.2024.123822 |
| P4 | Multi-agent large language model framework for code-compliant automated design of reinforced concrete structures | 2025 | Automation in Construction，Q1 | 说明 LLM 多智能体可承担规范约束解析、结构方案生成与合规校核，支持“LLM 做规则控制器” | https://doi.org/10.1016/j.autcon.2025.106331 |
| P5 | Integrating large models with topology optimization for conceptual design realization | 2025 | Advanced Engineering Informatics，Q1 | 直接把大模型与拓扑优化耦合，最接近“LLM 不替代求解器，而是强化设计实现链”的路线 | https://doi.org/10.1016/j.aei.2025.103524 |
| P6 | An LLM-based knowledge and function-augmented approach for optimal design of remanufacturing process | 2025 | Advanced Engineering Informatics，Q1 | 说明 LLM 与函数调用/知识增强结合后，可以参与受约束工艺优化，支持“LLM 调用算子/工具”叙事 | https://doi.org/10.1016/j.aei.2025.103303 |
| P7 | DR-RAG: Domain-Rule-based Retrieval-Augmented Generation for aviation digital model design | 2025 | Advanced Engineering Informatics，Q1 | 强调领域规则、RAG 与工程数字模型设计结合，直接支持 MASS 中 `CGRAG-Mass + policy` 的思路 | https://doi.org/10.1016/j.aei.2025.103316 |
| P8 | AirfoilAgent: Airfoil aerodynamics optimization design via large language model multi-agent collaborations | 2026 | Advanced Engineering Informatics，Q1 | 与“LLM 协同优化器/仿真器做工程优化”高度相似，支持把 LLM 放到气动/物理优化前端控制层 | https://doi.org/10.1016/j.aei.2026.103822 |
| P9 | Large language model-driven dynamic communication strategy generation for multi-swarm particle swarm optimization | 2026 | Engineering Applications of Artificial Intelligence，Q1 | 直接证明 LLM 可作为优化算法中的高层动态策略器，支持“LLM 管搜索策略而非替代群体优化器” | https://doi.org/10.1016/j.engappai.2025.111178 |
| P10 | Three-dimensional facility layout optimization using large language model-driven A-star and non-dominated sorting genetic algorithm-II | 2026 | Expert Systems with Applications，Q1 | 与我们问题最接近之一，直接涉及三维布局优化、LLM 驱动搜索策略与 NSGA-II 协同 | https://doi.org/10.1016/j.eswa.2025.128191 |

## 5. 文献综合结论

### 5.1 文献共同指向的“正确用法”

这 10 篇文献的共同趋势非常明确：

1. LLM 更适合做设计语义解释器、结构化程序/策略生成器、规则与知识协调器、以及工作流控制器。
2. 在真实工程问题里，LLM 很少被写成“唯一数值优化核心”，而是与传统优化器、求解器、规则系统或 CAD/CAE 工具协同。
3. 高质量论文更倾向于让 LLM 输出：
   - DSL
   - design intent
   - operator/action plan
   - tool-call sequence
   - multi-agent workflow
   - fidelity scheduling strategy
4. 当问题涉及高维、混合离散-连续、强约束、昂贵仿真时，LLM 的最佳位置通常是“上层策略层”，不是“底层 evaluator”。

### 5.2 文献没有支持的叙事

当前文献并没有稳定支持以下强主张：

- LLM 普遍可以直接替代 NSGA-II、PSO、BO 等经典优化算法。
- LLM 直接输出最终工程几何/坐标并天然满足硬约束。
- LLM 在高代价仿真闭环里不需要受约束的结构化中间层。

因此，本项目论文叙事必须严格收敛到：

> LLM 负责上层语义策略与流程控制，传统优化器与物理仿真仍然负责执行与真实性判定。

### 5.3 对 MsGalaxy 最有用的三条外部启发

1. `P5 + P9 + P10` 支撑“LLM 做优化中的动态策略器”。
2. `P3 + P6 + P7` 支撑“LLM 通过知识增强和函数调用衔接工程工具链”。
3. `P1 + P2 + P4 + P8` 支撑“LLM 更擅长把需求/规则/专家经验转成结构化工程决策，而不是直接替代物理优化核心”。

## 6. 当前传统 MASS 流程的关键问题

这里的“传统方法”具体指当前不含 LLM 策略层的基线，包括：

- `position_only + NSGA-II`
- `hybrid/operator_program + static NSGA-II`
- `rule-based meta policy`

### 6.1 `position_only` 的表达力瓶颈

`position_only` 的优点是稳定，但它本质上只是在连续坐标空间里搜索，存在明显限制：

- 不能自然表达“成组移动”“热热点扩散”“重件回中”“视场推离”等高阶语义动作。
- 无法把“结构加固”“热连接调整”“任务 keep-out 修复”等离散工程动作内生进搜索变量。
- 对需求语义和工程先验基本没有显式利用。

因此，`position_only` 更像一个稳定但语义盲的坐标搜索器。

### 6.2 `operator_program / hybrid` 的异构搜索复杂性

当前 `hybrid` 与 `operator_program` 虽然补上了语义动作表达，但也引入了新的困难：

1. 搜索空间异构。
   - 连续位置变量与离散算子槽位混在一起。
   - 同一套交叉/变异机制并不天然适合语义动作基因。
2. 组合空间爆炸。
   - `action family × component subset × axis × magnitude × slot count`
   - 槽位一多，组合复杂度迅速膨胀。
3. 合同投影碎裂。
   - `PlacementContractGuard` 会把许多候选投影回合法区间。
   - 多个不同基因可能映射到同一实际设计状态。
   - 搜索地形因此出现严重 aliasing 与不连续。
4. 静态策略限制。
   - 当前优化器本身并不知道本轮主导违约究竟是热、重心、边界还是任务约束。
   - 也不知道当前更该尝试几何类动作、热类动作还是结构/电源类动作。
5. 多保真预算低效。
   - proxy 很便宜，但和 real COMSOL 存在 gap。
   - COMSOL 很贵，但当前缺少 value-of-information 驱动的 promotion 策略。

### 6.3 当前 rule-based meta policy 的边界

当前已有 `optimization/modes/mass/meta_policy.py`，但它仍是规则型调参器，不是语义策略器。其局限主要体现在：

- 只能基于固定规则修改 runtime knobs。
- 无法显式结合需求/BOM/semantic zones/历史案例知识去生成算子先验。
- 无法输出结构化的“下一阶段算子模板”和“重点组件子集”。
- 无法作为论文中的“智能策略层”形成强 attribution。

结论是：

> 当前系统真正缺少的不是更多算子，而是一个能利用需求语义、轨迹诊断、规则知识和预算状态来调度这些算子的上层策略器。

## 7. 当前代码中已经存在的真实插入点

下表列出当前仓库中与 LLM 策略层最直接相关的插入位置。

| 代码位置 | 当前职责 | 已有能力 | 建议的 LLM 插入方式 |
| --- | --- | --- | --- |
| `workflow/scenario_runtime.py` 中 `_run_optimizer` | 优化主入口，组装搜索空间并运行 `PymooNSGA2Runner` | 已完成 bundle 构建、初始种群、结果观测汇总 | 在优化前注入 `PolicyPack`，决定 `search_space_mode`、slot 数、初始算子先验与 seed program |
| `optimization/modes/mass/pymoo_integration/search_space_factory.py` | 选择 `position_only / operator_program / hybrid` | 已支持三种模式与元数据输出 | 让 LLM 生成 mode bias 与约束化 search-space pruning 策略 |
| `optimization/modes/mass/pymoo_integration/operator_problem_generator.py` | 构造 operator-program 搜索问题 | 已能生成 operator-program 初始种群 | 让 LLM 给出 `forced_slot_action_params`、组件作用域与 family prior |
| `optimization/modes/mass/pymoo_integration/operator_program_codec.py` | 将基因解码为 operator program，并经过合同投影 | 已支持 `decode_program`、`decode_with_trace`、contract-guard trace | 在解码前后统计“策略命中率”和“guard 浪费率”，形成在线策略反馈 |
| `optimization/modes/mass/trace_features.py` | 生成轨迹摘要特征 | 已有 `first_feasible_eval`、`comsol_calls_to_first_feasible`、`violation_focus` | 作为 LLM 在线策略输入摘要，不再把原始日志直接喂模型 |
| `optimization/modes/mass/meta_policy.py` | 规则型 runtime knob controller | 已能按 `trace_features` 调参 | 用作 LLM 策略层的 fallback / safety floor，而不是主智能控制器 |
| `optimization/knowledge/mass/mass_rag_system.py` | `CGRAG-Mass` 证据检索 | 已有 symbolic + semantic + rerank + phase router | 为 LLM 策略层提供案例、规则、失败模式与组件知识支持 |

当前关键代码事实包括：

- `workflow/scenario_runtime.py` 中 `_run_optimizer` 已是主线优化入口。
- `search_space_factory.py` 已真实支持三类搜索空间选择。
- `operator_program_codec.py` 已真实支持 `decode_program` 和 `decode_with_trace`，并保留 contract-guard 审计。
- `trace_features.py` 已真实输出 `first_feasible_eval` 与 `comsol_calls_to_first_feasible` 等论文友好指标。
- `mass_rag_system.py` 已是真实活跃的 `mass` 证据检索后端。

这意味着：

> 当前仓库并不缺少“可执行骨架”，缺的是把这些现有能力调度起来的 LLM 策略层。

## 8. 推荐的总体方案：在当前 MASS 内加入 LLM Policy Layer

### 8.1 总体原则

本报告推荐的体系结构不是“LLM 替代 MASS”，而是：

```text
requirements / BOM / semantic zones / archived cases
    -> LLM Policy Layer
    -> search-space policy + operator priors + fidelity policy
    -> pymoo (NSGA-II / NSGA-III / MOEA/D)
    -> proxy evaluator
    -> selective COMSOL promotion
    -> trace digest + knowledge retrieval
    -> LLM Policy Layer (next round)
```

其中：

- `pymoo` 继续是唯一数值搜索核心。
- `proxy + COMSOL` 继续是唯一物理真实性闭环。
- LLM 只负责“怎么搜、搜哪一块、先调用哪些算子、何时升高保真度”。

### 8.2 建议引入的 `PolicyPack`

建议引入一个结构化中间对象 `PolicyPack`，作为 LLM 输出与执行层之间的唯一合同。其字段建议包括：

- `policy_version`
- `search_space_mode_bias`
- `operator_family_prior`
- `component_scope_prior`
- `forced_slot_actions`
- `action_slot_budget`
- `seed_programs`
- `runtime_knob_overrides`
- `promotion_policy`
- `confidence`
- `rationale`
- `evidence_refs`

该对象的意义在于：

1. 避免 LLM 直接操纵最终坐标。
2. 让策略输出具备可审计、可对照、可消融的结构化形态。
3. 让系统可以做安全校验与 fallback。

### 8.3 三个核心插入阶段

#### 阶段 A：搜索前静态策略生成

输入：

- requirement
- BOM
- semantic zones
- scenario constraints
- archived successful/failed evidence

输出：

- 初始 `search_space_mode`
- 初始 `operator_family_prior`
- 初始 `forced_slot_actions`
- 初始 `seed_programs`
- 重点组件集合

目标：

- 在优化开始前先裁剪搜索空间。
- 把大量“明显不值得尝试”的算子组合排除掉。
- 用需求语义为 `operator_program / hybrid` 提供 warm-start。

#### 阶段 B：搜索中在线策略更新

输入：

- `trace_features`
- dominant violation breakdown
- contract-guard reasons
- feasible ratio trend
- operator usage history
- proxy-real gap

输出：

- 下一阶段 operator family 优先级
- 下一阶段组件焦点
- slot 预算调整
- search-space mode 偏置调整
- runtime knobs 的语义化调整建议

目标：

- 让系统从“静态搜索”升级成“trajectory-conditioned policy search”。
- 缓解混合搜索空间在不同阶段最优动作完全不同的问题。

#### 阶段 C：多保真 promotion 策略

输入：

- `first_feasible_eval`
- `comsol_calls_to_first_feasible`
- proxy top-k 候选
- online budget snapshot
- physics audit 摘要

输出：

- 哪些候选值得升格到 COMSOL
- 本轮是否继续 proxy-only 扩搜
- 是否需要 bounded relaxation 或 operator family 切换

目标：

- 减少无效 COMSOL 调用。
- 把高保真预算用在更有希望的候选上。

## 9. 为什么这个方案能正面解决当前问题

### 9.1 针对搜索空间爆炸

LLM 可以先根据需求语义、组件功能和历史案例，把不相关的算子族、组件对和槽位模板裁掉。这样做不是直接降维坐标，而是：

- 先做语义级 pruning
- 再把剩余空间交给 `pymoo`

因此更适合解决当前 `hybrid/operator_program` 的组合爆炸问题。

### 9.2 针对搜索空间割裂与投影 aliasing

当前的割裂主要来自：

- 坐标变量与算子变量语义不一致
- 合同投影把多个基因映到同一状态

LLM 无法消除 aliasing 本身，但可以减少“无意义进入 aliasing 区域”的概率。方法包括：

- 避开高 guard-hit family
- 优先选择更可能真正改变设计状态的 action template
- 在重心、热、边界等主导违规类型之间动态切换 operator family

### 9.3 针对静态策略问题

当前 rule-based meta policy 只能调参，不能理解：

- “为什么此时 `cg_recenter` 比 `hot_spread` 更有价值”
- “为什么该场景优先从 `position_only` 升到 `hybrid`，而不是一开始就用 `operator_program`”
- “为什么当前 COMSOL promotion 应优先考虑热风险低但结构风险边缘的候选”

LLM 则可以基于：

- 需求语义
- 案例知识
- 当前轨迹摘要
- 失败模式解释

形成显式策略判断。

### 9.4 针对多保真预算浪费

如果没有上层策略器，COMSOL promotion 容易出现两类浪费：

- 明显 proxy 仍不稳定的候选被过早送去高保真。
- 已经在局部模式坍缩的候选被反复高保真验证。

LLM 策略层若与 `trace_features + CGRAG-Mass + physics_audit` 联动，可以把高保真预算从“固定阈值触发”升级到“信息价值驱动”。

## 10. 推荐的论文主叙事

### 10.1 最佳叙事逻辑

本报告建议的论文叙事顺序如下：

1. 传统 `position_only` 搜索稳定但表达力不足，只能在坐标空间中试错。
2. 引入 `operator_program / hybrid` 后，系统获得更强语义动作表达，但同时出现混合空间爆炸、合同投影碎裂和多保真预算分配困难。
3. 问题不在于“算子数量不够”，而在于“缺乏能动态调度这些算子的上层策略层”。
4. 近三年高质量工程文献表明，LLM 的最优角色不是替代数值优化器，而是输出结构化策略、工具调用和工作流控制。
5. 因此，本文提出 `LLM-guided policy layer over MASS`：
   - LLM 决定搜索策略与保真度策略。
   - MOEA 继续执行数值搜索。
   - proxy/COMSOL 继续执行真实性评估。
6. 在 matched budget 对照下，该策略层可望改善：
   - `first_feasible_eval`
   - `comsol_calls_to_first_feasible`
   - `proxy_feasible_rate`
   - `real_feasible_rate`
   - `AOCC-CV`

### 10.2 推荐的主创新点写法

推荐收敛为以下三条贡献：

#### C1. 语义算子策略控制器

提出一个 `LLM-guided semantic operator policy`，让 LLM 输出结构化 `PolicyPack`，用于控制：

- search-space mode
- operator family prior
- component focus
- action slots
- promotion strategy

#### C2. 合同安全的混合搜索控制

在 `operator_program / hybrid + PlacementContractGuard` 已存在的执行骨架上，引入策略层，使得 LLM 的任何建议都必须通过：

- operator codec
- contract guard
- executable evaluator

从而保证“LLM 可用但不越权”。

#### C3. 面向真实仿真预算的多保真调度

把 LLM 从“需求解释器”升级成“多保真策略控制器”，直接优化：

- 可行解首次出现速度
- COMSOL 使用效率
- real-feasible 闭环表现

## 11. 实验设计与对照方案

### 11.1 基线设置

建议至少设置以下对照组：

- `B0`: `position_only + NSGA-II`
- `B1`: `hybrid + static search-space + NSGA-II`
- `B2`: `hybrid + rule-based meta policy`
- `B3`: `hybrid + static LLM prior`
- `B4`: `hybrid + online LLM policy`
- `B5`: `hybrid + online LLM policy + fidelity scheduler`

### 11.2 关键指标

当前仓库已经具备或易于补齐的优先指标包括：

- `proxy_feasible_rate`
- `real_feasible_rate`
- `first_feasible_eval`
- `comsol_calls_to_first_feasible`
- `AOCC-CV`
- `best_feasible_objective_curve`
- `contract_guard_hit_rate`
- `contract_guard_reason_distribution`
- operator family usage entropy
- proxy-real gap

### 11.3 公平对照约束

所有“LLM 优于传统方法”的结论必须满足：

- matched budget
- 相同场景
- 相同 BOM
- 相同 active constraints
- 相同种子集
- 相同 proxy/real fidelity 配置

建议最低统计门槛：

- `seed >= 5` 作为初步结论
- `seed >= 10` 更适合论文级对照

### 11.4 能够成立的稳健结论

最稳健、最容易发表的改进叙事不是“所有目标函数全面超越”，而是：

- 更快找到首个可行解
- 更少调用 COMSOL 才找到首个 real-feasible 候选
- 在同预算下获得更高 feasibility rate
- 在混合搜索空间下减少无效 guard projection

## 12. 实施路线图

### 12.1 Phase P0：静态先验版

目标：

- 只做搜索前 `PolicyPack`
- 不做在线控制

新增能力：

- `LLMPolicyPackService`
- `PolicyPackValidator`
- `PolicyPack -> search_space_factory` 适配层

可验证收益：

- 更优初始模式选择
- 更优 seed programs
- 更快 `first_feasible_eval`

### 12.2 Phase P1：在线策略版

目标：

- 基于 `trace_features` 做 generation-level 策略更新

新增能力：

- `TrajectoryDigestBuilder`
- `OnlinePolicyUpdateService`
- `PolicyDecisionLog`

可验证收益：

- 更低 AOCC-CV
- 更好的 operator family 使用效率
- 更低 contract-guard 浪费

### 12.3 Phase P2：多保真调度版

目标：

- 在 proxy/COMSOL 之间引入 LLM-guided promotion policy

新增能力：

- `FidelityPromotionPolicy`
- `PromotionCandidateDigest`
- `Policy + hard-threshold` 双重门控

可验证收益：

- 更低 `comsol_calls_to_first_feasible`
- 更高 real-feasible rate

## 13. 建议的实现位置

在不破坏当前主线的前提下，建议新增或扩展如下模块：

- `optimization/modes/mass/llm_policy_service.py`
  - 负责生成 `PolicyPack`
- `optimization/modes/mass/policy_pack.py`
  - 定义结构化策略合同
- `optimization/modes/mass/policy_digest.py`
  - 将 `trace_features`、违规分解、budget snapshot 压缩为 LLM 可消费摘要
- `optimization/modes/mass/fidelity_policy.py`
  - 负责 COMSOL promotion 策略
- `optimization/modes/mass/policy_observability.py`
  - 记录 policy inputs/outputs/confidence/evidence refs

并优先在下列真实主线位置接入：

- `workflow/scenario_runtime.py`
- `optimization/modes/mass/pymoo_integration/search_space_factory.py`
- `optimization/modes/mass/meta_policy.py`

## 14. 风险与边界

### 14.1 需要明确控制的风险

- LLM 输出策略可能不稳定，因此必须经过 `PolicyPackValidator` 与 hard guard。
- LLM 策略若过强，可能掩盖 baseline 数值优化器的真实表现，因此必须做清晰 ablation。
- LLM 可能过度利用历史案例，导致策略过拟合单场景，因此必须做跨 seed 与逐步扩场景验证。
- 如果直接把 LLM 接入最终坐标生成，将违反当前 `mass` 合同边界，也会显著削弱论文可信度。

### 14.2 当前不能提前宣称的结论

在没有完成 matched-budget 多 seed 对照前，不能宣称：

- `LLM + MASS` 已稳定优于 `position_only`
- `LLM + hybrid` 已经具备 release-grade 稳定性
- LLM 策略层对所有场景都有效

当前更诚实的说法应是：

> 当前 MASS 已具备可执行、可观测、可进入 real COMSOL 的混合搜索骨架，因此下一步最有研究价值的工作，是在这条真实骨架上加入 LLM 策略层，并以 first-feasible、COMSOL 预算效率和 matched-budget feasibility gain 作为核心验证指标。

## 15. 最终建议

综合当前仓库真相、历史 `vop_maas` 思路和近三年高质量文献，本报告给出以下最终建议：

1. 不恢复旧 `vop_maas` 模式名，而是在当前 `mass` 内实现 `LLM Policy Layer`。
2. 不把 LLM 定位成最终布局生成器，而把它定位成：
   - 搜索空间控制器
   - 算子策略生成器
   - 多保真调度器
3. 第一阶段先做 `static policy prior`，尽快拿到可发表的初步收益。
4. 第二阶段做 `online operator policy`，把它作为论文主创新点。
5. 第三阶段再做 `fidelity scheduler`，把 COMSOL 预算效率作为亮点。

最推荐的论文核心表述是：

> 传统坐标搜索在卫星布局问题中具有稳定但语义贫乏的特点；混合搜索空间虽然提升了动作表达力，却引入了搜索空间爆炸、合同投影碎裂与高保真预算分配困难。基于近三年工程领域高质量 LLM 文献的共同启示，最合理的路线不是用 LLM 替代数值优化器，而是在当前 MASS 可执行闭环之上构建一个 LLM-guided policy layer，让 LLM 负责搜索空间裁剪、算子策略生成和多保真调度，从而在合同安全与物理真实性不被破坏的前提下，提高 first-feasible 发现效率与 real-feasible 闭环效率。

## 16. 官方参考链接

- FloorPlan-LLaMa: Aligning Architects' Feedback and Domain Knowledge in Architectural Floor Plan Generation
  - https://aclanthology.org/2025.acl-long.1127/
- LLM-based framework for automated and customized floor plan design
  - https://doi.org/10.1016/j.autcon.2025.106512
- EPlus-LLM: A large language model-based computing platform for automated building energy modeling
  - https://doi.org/10.1016/j.apenergy.2024.123822
- Multi-agent large language model framework for code-compliant automated design of reinforced concrete structures
  - https://doi.org/10.1016/j.autcon.2025.106331
- Integrating large models with topology optimization for conceptual design realization
  - https://doi.org/10.1016/j.aei.2025.103524
- An LLM-based knowledge and function-augmented approach for optimal design of remanufacturing process
  - https://doi.org/10.1016/j.aei.2025.103303
- DR-RAG: Domain-Rule-based Retrieval-Augmented Generation for aviation digital model design
  - https://doi.org/10.1016/j.aei.2025.103316
- AirfoilAgent: Airfoil aerodynamics optimization design via large language model multi-agent collaborations
  - https://doi.org/10.1016/j.aei.2026.103822
- Large language model-driven dynamic communication strategy generation for multi-swarm particle swarm optimization
  - https://doi.org/10.1016/j.engappai.2025.111178
- Three-dimensional facility layout optimization using large language model-driven A-star and non-dominated sorting genetic algorithm-II
  - https://doi.org/10.1016/j.eswa.2025.128191
