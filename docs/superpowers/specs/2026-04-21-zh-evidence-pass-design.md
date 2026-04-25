# 2026-04-21 中文主稿实验主线补全设计

## 1. 目标与边界

本轮工作的目标不是把整篇论文一次性补满，而是围绕当前最可信、最完整的一条证据主线，对中文主稿做一次“证据化补全 pass”。主线以 `scenario_runs/s2_staged/0421_0207__llm` 与 `scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair` 为核心运行资产，前者承担 llm 单运行内部的机制证据，后者承担 raw / union / llm recover repair 的横向比较证据。

本轮只优先落地中文主稿，英文不做同等深度的正文扩写，只保留后续同步空间。公式补到“问题定义 + 方法层”深度，即补全问题定义中的设计变量、目标、约束、固定边界，以及方法中的状态摘要、控制决策、统一闭环与 layered recovery 介入位置，但不把所有实验指标都做成完整数学体系。图表部分以已有运行产物为主，完整接入 compare report 中的图表和单 run 中关键的机制图；对于尚未生成的框架图，本轮先明确清单与 LaTeX 占位，等用户在其他对话生成后再插入正式图片。

## 2. 采用方案与理由

推荐并采用“中文实验主线驱动，问题定义和方法为它服务”的方案。也就是说，先围绕当前已有的最强证据资产把实验主线钉死，再反推问题定义需要哪些公式、方法需要哪些形式化表达，以及需要哪些框架图去支撑叙事。

不采用“先写满公式骨架再嵌结果”的路线，因为当前最重要的不是理论扩张，而是把已有 run 资产稳定转写进论文，避免先写出一套与现有证据对不齐的形式化体系。也不采用“先只做图位和框架位”的路线，因为当前缺口不仅是版面空位，而是现有证据如何被完整、克制且机制优先地讲清楚。

## 3. 章节级组织设计

本轮主改三个中文章节：`paper/latex/sections/zh/03_problem_formulation.tex`、`paper/latex/sections/zh/04_method.tex`、`paper/latex/sections/zh/06_experiments.tex`。必要时允许轻改 `paper/latex/sections/zh/05_collapse_and_recovery.tex`，使其与新增公式、框架图和实验引用保持一致。

`03_problem_formulation` 的职责是把任务写成可以被后文直接引用的正式对象。该章应明确定义设计变量向量、目标函数、约束集合，以及最关键的 fixed optimization boundary：raw、union、llm 在表示、动作集合、repair 机制、cheap constraints、数值求解流程与评估预算上共享，而仅在控制层不同。该章不展开控制器实现细节，只负责把“问题是什么、比较边界是什么”钉死。

`04_method` 的职责是说明 inline controller 如何被插入共享优化闭环，以及 layered recovery 如何作用。这里不写成实现手册，而是聚焦 state summary、controller decision、candidate generation、repair、cheap constraint filtering、expensive evaluation、state write-back 的统一闭环，再补 recovery 层如何介入语义层、空间层、意图层、检索层与饱和层。该章的 formalization 服务于“控制器是什么、如何工作、恢复在哪介入”。

`06_experiments` 是本轮主承载章节，负责把 compare report 与单 run 资产转化成一条完整的实验叙事链。其组织顺序应为：比较设置与证据来源说明、总览对比图表、进程类图表、代表布局与场图、机制解释与资产引用。实验章不能只是罗列图片，而要明确每组图表服务哪一类论点：哪些是效果比较证据，哪些是 collapse/recovery 机制证据。

`05_collapse_and_recovery` 若需轻改，重点是与新增框架图和实验引用对齐，例如让 taxonomy 名称、recovery layer 名称、实验章中的图题和术语保持完全一致。

## 4. 公式设计范围

### 4.1 问题定义公式

在 `03_problem_formulation` 中补四类核心公式。

第一类是设计变量向量，把组件布局变量与散热边界变量合并为统一决策向量，明确本文优化对象不是由 LLM 直接生成的自由结构，而是在固定编码下搜索的有限维设计变量。

第二类是目标函数，至少形式化写出峰值温度与温度梯度均方根两个目标，使后文所有温度场、梯度场和 Pareto 结果有统一定义来源。

第三类是约束集合，包含几何合法性、repair 后可行性、散热资源预算等核心约束，并明确 cheap constraints 与 expensive evaluation 在判定链条中的位置。

第四类是 fixed optimization boundary 的形式化描述。这里不必写成很重的公理化定义，但要明确写出三种模式共享的能力边界与不同的控制映射，使“公平比较 / attribution boundary”不再只是口头叙述。

### 4.2 方法层公式

在 `04_method` 中补控制回路的最小充分形式化。

首先定义状态摘要 `s_t`，它不是全量系统状态，而是提供给控制层的压缩决策上下文。其次定义控制决策 `u_t` 或动作偏好输出，表示控制器在时刻 `t` 对操作族、搜索重点或阶段侧重点的调度。然后用统一闭环表达一次迭代如何从状态到控制，到候选生成、repair、约束过滤、数值评估，再回写状态。

在此基础上，用克制的形式描述 layered recovery 的介入方式。例如把 recovery 视为作用在状态构造、意图强化、历史检索或动作抑制等位置的校正映射，而不是把每一层都展开成繁复子公式。目标是让方法更严谨，同时仍然紧贴后续图表与 taxonomy 解释。

本轮不对 hypervolume、多 seed 统计或所有实验指标做完整形式化；这些属于后续更大实验版的工作。

## 5. 图表与运行资产接入设计

### 5.1 横向比较证据

比较主线以 `scenario_runs/compare_reports/s2_staged/0421_0420__raw_union_old_vs_llm_recover_repair` 为中心。该目录下已有 `summary_overview.png`、`progress_dashboard.png`、`temperature_field_comparison.png`、`gradient_field_comparison.png`，以及 `tables/mode_metrics.tex`、`tables/pairwise_deltas.tex`、`tables/summary_table.tex`。这些资产应优先接入 `06_experiments`，并作为当前版本最直接的跨模式对比证据。

其中，总览类图表用于建立三种模式在当前比较中的整体差异，progress dashboard 用于展示阶段变化与过程差异，temperature/gradient field comparison 用于展示代表解在物理场上的可见差异，表格则用于给出可引用的数值摘要。实验文字必须明确这些图表服务于“当前可支持的证据层”，避免写成最终 comparative closure。

### 5.2 单运行机制证据

机制主线以 `scenario_runs/s2_staged/0421_0207__llm` 为中心。该目录已有 `analytics/progress_timeline.csv`、`analytics/hypervolume.csv`、`analytics/operator_phase_heatmap.csv`、`figures/objective_progress.png`、`figures/hypervolume_progress.png`、`figures/operator_phase_heatmap.png`、`figures/pareto_front.png`、`figures/layout_initial.png`、`figures/layout_final.png`、`figures/temperature_field_*.png`、`figures/gradient_field_*.png`，以及 `traces/` 与 `prompts/`。

这些资产不承担横向对比任务，而用于解释 llm 控制过程内部发生了什么。也就是说，它们服务于 collapse/recovery 的机制叙事：阶段切换、动作偏好、布局演化、代表点物理场差异，以及必要时引用 trace 说明控制决策并非不可审计。实验章需要明确区分“跨模式比较证据”和“单运行机制证据”，避免二者混写。

## 6. 框架图清单与占位设计

本轮先占位 4 张框架图。

第一张是“固定优化边界与三种模式对比图”。该图展示 shared problem / shared operator pool / shared repair-evaluation pipeline / different control layers，用于说明 raw、union、llm 的比较边界。建议放在 `04_method` 开头。

第二张是“inline control 闭环流程图”。该图展示 state summary、controller decision、candidate generation、repair、cheap constraints、expensive evaluation、state write-back 的时序关系，用于说明一轮控制如何运行。建议放在 `04_method` 的流程部分。

第三张是“collapse taxonomy ↔ layered recovery 对应图”。左侧为 collapse types，右侧为对应 recovery layers，中间用箭头连接，并标注 intervention location / restored capability。建议放在 `05_collapse_and_recovery`。

第四张是“运行资产证据地图图”。该图把 summary、timeline、milestone、trace 以及 compare report / single run 中的图表与表格连接到实验论点，说明论文如何从运行资产走到结论。建议放在 `06_experiments` 开头或开头之后。

可选的第五张是“实验主线证据串联图”，专门说明 compare report 与单 run 各自承担的证据职责。该图不是必须，只有在实验章出现信息拥挤时才考虑加入。

本轮实施中，这些图先用统一风格的 `figure` 占位块和明确 caption / label 落进 LaTeX，后续待用户生成正式图片后替换路径。

## 7. 本轮实施产出

本轮设计对应的实现应至少产生以下产出：

- 补全后的 `paper/latex/sections/zh/03_problem_formulation.tex`
- 补全后的 `paper/latex/sections/zh/04_method.tex`
- 补全后的 `paper/latex/sections/zh/06_experiments.tex`
- 必要时对 `paper/latex/sections/zh/05_collapse_and_recovery.tex` 的对齐性轻改
- 若干 compare report 现有图表的 LaTeX 插图与表格接入
- 4 张框架图的 LaTeX 占位及图题

本轮不要求英文同步完成，不要求新增真实实验 rerun，不要求补完整 related work 文献，也不要求补齐最终大规模统计结论。

## 8. 风险与控制

最大的风险是实验章被当前有限结果牵着走，重新滑回 performance-first 叙事。为避免这一点，实验章中的每组图表都必须明确其服务对象：是横向比较、过程差异、代表物理场，还是机制解释。另一个风险是公式过满、与当前资产脱节，因此所有新增公式都应能被后文图表或文字直接引用，不能为了“更学术”而独立膨胀。

第三个风险是框架图过多，导致与结果图争抢篇幅。因此本轮只占位 4 张必要框架图，并明确它们分别服务边界、流程、taxonomy/recovery、证据地图四种不同职责。

## 9. 后续规划接口

完成本轮后，下一步最自然的是为实验章单独写一个小计划，逐图逐表落正文和 caption，并把 compare report 与单 run 的具体图表顺序固定下来。再下一步是 related work 的真实文献补强，但仍维持 gap-first、boundary-setting 的写法。英文正文同步应放在中文主稿这一轮稳定之后进行。
