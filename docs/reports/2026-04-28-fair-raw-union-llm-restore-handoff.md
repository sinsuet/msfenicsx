# raw / union / llm 公平对比恢复交接记录

## 1. 这份文档的用途

这是一份给后续对话使用的交接文档，记录当前 worktree（`/home/hymn/msfenicsx/.worktree/fair-comparison-restore`）里围绕 `raw / union / llm` 公平对比恢复所做的工作。

你后面如果在另一个对话里继续这条线，可以直接从这里接着看：

- 问题背景是什么
- 这次具体规划了什么
- 实际改了什么
- 最后验证出来的效果是什么
- 下一步应该怎么继续优化

相关设计与计划文件：

- `/home/hymn/msfenicsx/docs/superpowers/specs/2026-04-27-fair-raw-union-llm-comparison-restore-design.md`
- `/home/hymn/msfenicsx/docs/superpowers/plans/2026-04-28-fair-raw-union-llm-comparison-restore.md`

## 2. 背景问题

这条线的起点是：之前为了重构算子和提升 `raw / union / llm` 效果，链路逐渐变复杂，导致原本应该“干净可比”的比较关系被破坏了。

最核心的漂移有两类：

1. **`llm` 线跨出了原本的对比契约**
   - 原先希望的是：`union` 和 `llm` 只有 controller 不同，其余都相同。
   - 后来 `llm` 逐渐带上了更多自己的硬机制，和 `union` 不再是同一套搜索底座。

2. **`raw` / `union` 的搜索行为偏斜**
   - `union` 的组件探索偏少，很多时候几乎都在动 sink。
   - 这意味着即使 `llm` 有优势，也很难解释清楚到底是 controller 优势，还是底座不公平。

所以这次工作的目标不是继续“堆效果”，而是先把比较契约恢复干净，再谈保留 `llm` 优势。

## 3. 这次的规划思路

这条线采用的是一个更严格的 B-shape 契约：

- `union` 和 `llm` 必须共享同一套搜索底座
  - decision encoding
  - operator pool
  - registry profile
  - repair / legality policy
  - cheap constraints
  - expensive evaluation budget
- `llm` 允许有自己的**表述层 / representation layer**
  - prompt projection
  - reflection
  - generation-local memory
  - recent decision summaries
  - soft policy guidance
- 但 `llm` **不能**通过硬裁剪 candidate set、硬移除 operator、或者不同的 legality policy 获得额外底座优势

所以整体路线分成两步：

1. **先恢复公平契约**：把 `union` 和 `llm` 重新对齐到同一底座。
2. **再做性能与稳定性优化**：在公平契约已经成立后，继续看 `llm` 链路怎么在不破坏公平性的前提下变快、变稳。

## 4. 这次实际做了什么

### 4.1 恢复 `union / llm` 的公平底座

已经完成的核心修复包括：

- `s1_typical` 和 `s2_staged` 的 `union / llm` 规格对齐
  - 相同的 operator pool
  - 相同的 legality policy
  - 相同的 evaluation spec
  - 相同的 cheap constraints / repair chain
- `policy_kernel` 从“门禁”改成“注释器”
  - 不再缩小 candidate support
  - 不再输出非空的 `suppressed_operator_ids`
  - 原本的筛选逻辑改成 `reason_codes` / annotation
- `llm_controller` 保留同一套 candidate support
  - 不再让模型拿到更小的候选集
  - guardrail 变成 soft advice，而不是硬移除 operator
- `prompt_projection` 做了压缩
  - 去掉了过大的 parent / retrieval 冗余信息
  - 合并重复的 per-operator 注释
  - 缩短 prompt 的总体长度，减少每轮 LLM 请求成本

### 4.2 provider / model 链路排查

在公平契约恢复后，又继续做了 provider 侧的链路实验，目的是判断到底是哪个 provider 链路更可用、更稳定。

主要试过三条：

- `qwen`
- `deepseek`
- `gpt`

同时还做了一个额外的小修正：

- 在 `s2_staged_llm.yaml` 里去掉了 qwen 的 reasoning 字段，验证默认路径是不是“关闭思考模式”

## 5. 做完之后的验证结果

### 5.1 公平契约恢复后的测试

公平契约恢复后，相关聚焦测试是通过的：

- `tests/optimizers/test_llm_profiles.py`：`8 passed`
- `policy_kernel` / `llm_controller` / prompt 投影相关测试：之前也已经跑通过
- 整体公平恢复阶段的验证结论是：契约已经回到“同底座、不同 controller”的状态

### 5.2 qwen 的实验结果

#### `llm-qwen-prompt-slim2-smoke`

- 规模：`4×2`
- 请求数：`2`
- fallback：`0`
- 平均延迟：`31.4s`
- 结论：能正常返回决策，但不算快

#### `llm-qwen-no-reasoning-10x5-baseline`

- 规模：`10×5`
- 请求数：`37`
- 有效响应：`11`
- fallback：`26`
- 平均延迟：`46.7s`
- 结论：qwen 能工作，但慢，而且大量请求最终还是 fallback

### 5.3 DeepSeek 的实验结果

#### `llm-deepseek-5x2-link-check`

- 先用 `deepseek-chat`
- 结果是：`401 Unauthorized`
- 6 次请求全部 fallback
- 结论：这个链路不是“慢”，而是鉴权不可用

#### `llm-deepseek-v4-flash-5x2-link-check`

- 改成 `DeepSeek-V4-Flash`
- 结果是：
  - 3 次 `429 Too Many Requests`
  - 3 次 JSON 截断 / 不完整
- 6 次请求全部 fallback
- 平均延迟约 `7.0s`
- 结论：这条链路能打到服务，但当前不可稳定产出有效 JSON

### 5.4 GPT 的实验结果

#### `llm-gpt-5x2-link-check`

- 模型：`gpt-5.4`
- 请求数：`3`
- 有效响应：`2`
- fallback：`1`
- 平均延迟：`16.9s`
- 失败点：`1` 次 timeout
- 结论：这三条 provider 里，GPT 是目前最接近“可继续测”的链路

## 6. 最终效果怎么看

这次工作真正达成的效果，不是“已经把 llm 彻底调到最好”，而是：

1. **先把公平对比契约恢复了**
   - `union` 和 `llm` 现在重新回到同一套搜索底座
   - `llm` 的优势如果存在，可以更清楚地解释为表述层 / controller 层能力

2. **把 prompt 压下来了，但没有把 provider 问题彻底消掉**
   - prompt 变短了
   - 但 qwen 依然慢
   - DeepSeek 依然不稳定
   - GPT 比较可用，但仍有 timeout

3. **当前真正的瓶颈已经变成“LLM 调用频率 + provider 稳定性”**
   - 不是公平契约本身
   - 也不是单纯 reasoning 字段的问题
   - 而是每个 generation 里请求太多、每次请求都太重、provider 行为差异太大

## 7. 后面最值得继续做的优化

如果后面要继续往下走，优先级我建议是：

1. **先把 GPT 作为当前最稳的 provider 继续测**
   - DeepSeek 目前不稳定
   - qwen 目前太慢且 fallback 多
   - GPT 是当前最适合继续排查的链路

2. **做低频 LLM 调用 / budgeted reuse**
   - 这能直接减少 `20×10` 场景里的调用次数
   - 也能减少超时和 provider 限流对整体运行的拖累
   - 这是目前最值得做的下一步

3. **继续压 prompt，但不要再牺牲公平契约**
   - 现在已经证明 prompt 压缩只能缓解一部分问题
   - 不能靠重新裁剪 candidate support 来换速度

4. **小规模验证后再回到大规模比较**
   - 先用 `5×2`、`4×2`、单次 probe 做稳定性验证
   - 再考虑回到更完整的 `10×5` 或 `20×10`

## 8. 交接建议

这条线下一步如果要继续，建议按下面顺序做：

1. 把这份报告作为新的对话起点
2. 继续在 GPT 链路上做低频调用和稳定性排查
3. 如果实现了新的优化，再重新跑一轮公平比较
4. 确认最终代码和文档都已经落到 `main`
5. 然后删除旧的 worktree，只保留最终主线

这份文档的目标就是：让你在新对话里不用重新回忆整个来龙去脉，直接接着做下一步。
