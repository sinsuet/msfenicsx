# LLM Semantic Ranker Controller 设计

## 背景与诊断

本设计针对 `scenario_runs/s5_aggressive15/0430_1921__raw_union_llm` 暴露的新问题：`semantic_prior_sampler` 虽然把 LLM 从直接选择改成 semantic/operator prior，但最终 action 仍被概率采样机制显著稀释。

同一 S5、seed 11、20 x 10、GPT 链路的核心证据是：

- `raw`: PDE 156, cheap skipped 44, feasible rate 0.420, best `temperature_max` 326.750, best `temperature_gradient_rms` 20.813, hypervolume 0.000。
- `union`: PDE 160, cheap skipped 40, feasible rate 0.595, best `temperature_max` 323.614, best `temperature_gradient_rms` 16.521, hypervolume 265.708。
- `llm`: PDE 142, cheap skipped 58, feasible rate 0.450, best `temperature_max` 322.934, best `temperature_gradient_rms` 18.735, hypervolume 97.473。

这不是 LLM 完全失败：`llm` 找到了更低 peak temperature。但它在 feasible rate、gradient、hypervolume 上输给 `union`，说明当前控制器没有把语义判断稳定转化成多目标 Pareto 改善。

进一步 trace 诊断显示：

- `llm` decision count 173，fallback count 0，模型调用链路稳定。
- 9 个候选 operator 下，uniform probability 是 0.111；`semantic_prior_sampler` 的平均 `selected_probability` 约 0.125，median 约 0.117。
- sampler probability normalized entropy 平均约 0.978，接近均匀分布。
- LLM top-prior 最终被采样命中 34/173，约 19.7%；top-2 命中 58/173，约 33.5%。
- selected rank 平均约 4.05，median 为 4。
- operator-level `risk` 绝大多数是默认 0.5，`confidence` 也大量是默认 0.5，risk penalty 和 confidence 信号基本没有起作用。

因此当前根因不是“LLM 不会读 semantic_task_panel”，而是 prior-to-action 机制把 LLM 的判断变成了轻微偏置的 random。研究问题被误改成“弱 LLM 概率偏置是否优于 union random”，这与目标不一致。

## 对 `union` 的判断

`union` 看起来强，不是因为它有额外信息，而是因为它在 shared primitive operator substrate 上保持了广覆盖。S5 的 primitive operator pool 本身已经包含有效的结构化算子，随机 controller 在 20 x 10 小预算下天然获得了较好的探索宽度。

这不应被视为 baseline 做错或过强。论文边界要求 `union` 与 `llm` 使用同一候选支持集；如果削弱 `union`，比较会失去可信度。正确方向是提高 LLM action fidelity：让 LLM 的语义判断直接决定排序，并只用可解释的 deterministic constraints 防止重复垄断，而不是用高熵采样把判断平均掉。

## 目标

实现新的 LLM-only 选择策略：

```yaml
selection_strategy: semantic_ranked_pick
```

核心目标：

1. LLM 输出 candidate operators 的有序 ranking，而不是概率 prior。
2. controller 默认选择 LLM 排名最高、未被当前 saturation caps 禁止的 operator。
3. 当 top choice 被 generation / rolling cap 禁止时，按 LLM 排序扫描到下一个可用 operator。
4. 当 top choice 与 next choice 是低置信近似平局时，使用 deterministic lower-risk tie-break，而不是随机采样。
5. 完整 trace LLM ranking、selected rank、suppressed operators、override reason 和 ranker config，方便复盘 LLM 语义判断是否真正落成 action。

## 非目标

- 不修改 `raw` 路线。
- 不修改 `union` 路线。
- 不修改 `*_raw.yaml`、`*_union.yaml`。
- 不修改 `optimizers/drivers/raw_driver.py`、`optimizers/drivers/union_driver.py`、`optimizers/operator_pool/random_controller.py`。
- 不修改 primitive operator registry 和 operator definitions。
- 不重构现有 semantic task taxonomy。
- 不重构 `semantic_task_panel`、adaptive sink gate、summary 逻辑。
- 不新增 `llm_direct` 或 `uniform_prior_sampler` baseline。
- 不启动新的 GPT 20 x 10 live run；live run 只在用户后续明确要求时执行。
- 不把 S5、seed 11、某个 operator 名称写成特调规则。

## 选定方案

采用“方案二：LLM ranker + deterministic constrained pick”。

保留现有 `semantic_prior_sampler` 代码和测试，作为 legacy experiment path；新增 `semantic_ranked_pick` 路线，并把 active paper-facing LLM YAMLs 切到该路线。这样可以在不破坏已有实现的前提下，把论文主线恢复为“LLM 语义理解直接控制 operator choice”。

## 新 contract

新增 schema helper：

```python
build_operator_rank_advice_schema(candidate_operator_ids: Sequence[str]) -> dict[str, Any]
```

新增 client dataclasses：

```python
@dataclass(frozen=True, slots=True)
class RankedOperatorCandidate:
    operator_id: str
    semantic_task: str
    score: float
    risk: float
    confidence: float
    rationale: str


@dataclass(frozen=True, slots=True)
class OpenAICompatibleRankAdvice:
    ranked_operators: tuple[RankedOperatorCandidate, ...]
    phase: str
    rationale: str
    provider: str
    model: str
    capability_profile: str
    performance_profile: str
    raw_payload: dict[str, Any]
```

模型响应格式：

```json
{
  "phase": "post_feasible_expand",
  "rationale": "rank sink-aware expansion above local cleanup because peak stagnates and sink is misaligned",
  "ranked_operators": [
    {
      "operator_id": "sink_shift",
      "semantic_task": "sink_alignment",
      "score": 0.82,
      "risk": 0.22,
      "confidence": 0.74,
      "rationale": "align sink toward hotspot corridor"
    },
    {
      "operator_id": "component_block_translate_2_4",
      "semantic_task": "semantic_block_move",
      "score": 0.76,
      "risk": 0.38,
      "confidence": 0.61,
      "rationale": "broaden Pareto support with bounded block move"
    }
  ]
}
```

约束：

- `ranked_operators` 必须是非空数组。
- 每个 item 必须包含 `operator_id`、`semantic_task`、`score`、`risk`、`confidence`、`rationale`。
- `operator_id` 必须属于当前 `candidate_operator_ids`。
- `score`、`risk`、`confidence` clamp 到 `[0.0, 1.0]`。
- duplicate `operator_id` 只保留首次出现，并在 raw payload 中保留原始响应。
- 推荐模型 rank 覆盖所有候选；解析器允许部分覆盖，但 picker 会把未覆盖候选追加到末尾并在 trace 记录 `ranker_missing_operator_ids`。这避免一次轻微漏项直接触发 fallback，同时使漏项可见。
- picker 使用代码侧 `semantic_task_for_operator(operator_id)` 作为 cap 判断的 canonical task；模型返回的 `semantic_task` 用于 trace 和一致性诊断。

## Deterministic ranked picker

新增模块：

```text
optimizers/operator_pool/semantic_ranked_picker.py
```

输入：

- `candidate_operator_ids`
- `ranked_operators`
- `ControllerState`
- `SemanticRankedPickConfig`

输出：

- `selected_operator_id`
- `selected_rank`
- `ranked_operator_rows`
- `suppressed_operator_ids`
- `cap_reasons`
- `override_reason`
- `missing_operator_ids`
- `config`

默认配置：

```yaml
semantic_ranked_pick:
  max_rank_scan: 9
  generation_operator_cap_fraction: 0.35
  rolling_operator_cap_fraction: 0.40
  rolling_semantic_task_cap_fraction: 0.55
  rolling_window: 16
  near_tie_score_margin: 0.03
  low_confidence_threshold: 0.35
```

选择流程：

1. 将 LLM ranking 按响应顺序去重。
2. 把未出现在 ranking 中的 candidate operators 追加到队尾，`score=0.0`、`risk=1.0`、`confidence=0.0`，并记录 `missing_operator_ids`。
3. 读取 `generation_local_memory`，对当前 generation accepted count 达到 `ceil(target_offsprings * generation_operator_cap_fraction)` 的 operator 加 `generation_operator_cap`。
4. 读取 `recent_decisions` 的最近 `rolling_window`，对 rolling operator share 达到 `rolling_operator_cap_fraction` 的 operator 加 `rolling_operator_cap`。
5. 按 canonical semantic task 统计 rolling share，对达到 `rolling_semantic_task_cap_fraction` 的 task 加 `rolling_semantic_task_cap`。
6. 在前 `max_rank_scan` 个 ranked rows 内选择第一个未被 suppress 的 operator。
7. 如果第一名未被 suppress，但它与第二名满足近似平局条件：
   - `top.score - second.score <= near_tie_score_margin`，或
   - `top.confidence < low_confidence_threshold`
   则在同一近似平局窗口内选择 `risk` 最低者；若 risk 相同，选择 `confidence` 更高者；若仍相同，保留 LLM 原始排名。
8. 如果 caps suppress 了全部候选，释放 caps，选择原始 rank 1，并记录 `override_reason="all_candidates_suppressed_release"`。

这个 picker 没有 `uniform_mix`、没有 probability floor、没有 RNG sampling。它保留最低限度的 anti-collapse 约束，但不把 LLM choice 平均化。

## Controller 集成

`LLMOperatorController` 支持第三种策略：

```python
{"direct_operator", "semantic_prior_sampler", "semantic_ranked_pick"}
```

当 `selection_strategy == "semantic_ranked_pick"` 时：

1. 使用 rank-specific system prompt。
2. 调用 `client.request_operator_rank_advice(...)`。
3. 调用 `pick_operator_from_semantic_ranking(...)`。
4. 把结果写入 response trace 和 `ControllerDecision.metadata`。

rank-specific prompt 的核心要求：

```text
Return an ordered ranking of candidate operators, not probabilities and not a final design vector.
Rank by semantic task fit, operator evidence, objective balance, feasibility risk, recent saturation, and confidence.
The controller will pick the highest ranked operator that is not saturated by deterministic caps.
Use score/risk/confidence explicitly; do not leave risk or confidence implicit.
Return JSON only.
```

旧 `direct_operator` 和 `semantic_prior_sampler` 分支保留，避免破坏已有测试与历史 trace replay。

## Trace contract

`llm_response_trace.jsonl` 和 `ControllerDecision.metadata` 新增字段：

- `selection_strategy: "semantic_ranked_pick"`
- `llm_ranked_operators`
- `selected_rank`
- `ranker_suppressed_operator_ids`
- `ranker_cap_reasons`
- `ranker_override_reason`
- `ranker_missing_operator_ids`
- `ranker_config`

`controller_trace.jsonl` 的基础字段不变，仍记录最终 `operator_selected`、prompt ref、response ref 和 latency。

## Active YAML 切换

只修改 active LLM specs：

- `scenarios/optimization/s1_typical_llm.yaml`
- `scenarios/optimization/s2_staged_llm.yaml`
- `scenarios/optimization/s3_scale20_llm.yaml`
- `scenarios/optimization/s4_dense25_llm.yaml`
- `scenarios/optimization/s5_aggressive15_llm.yaml`

示例配置：

```yaml
selection_strategy: semantic_ranked_pick
semantic_ranked_pick:
  max_rank_scan: 9
  generation_operator_cap_fraction: 0.35
  rolling_operator_cap_fraction: 0.40
  rolling_semantic_task_cap_fraction: 0.55
  rolling_window: 16
  near_tie_score_margin: 0.03
  low_confidence_threshold: 0.35
```

不修改任何 `*_raw.yaml` 或 `*_union.yaml`。

## 测试策略

使用 TDD 顺序：

1. schema/client tests 先失败，再实现 rank advice parser。
2. ranked picker tests 先失败，再实现 deterministic constrained pick。
3. controller integration tests 先失败，再接入 `selection_strategy == "semantic_ranked_pick"`。
4. trace contract tests 先失败，再补齐 ranker trace metadata。
5. YAML/spec tests 先失败，再切 active LLM configs。
6. 最后跑 focused LLM tests、ladder contract tests、raw/union diff check、`git diff --check`。

## 验收标准

- active LLM specs 使用 `semantic_ranked_pick`。
- `raw` 和 `union` specs、drivers、random controller 没有 diff。
- 新 client parser 能解析 rank advice，拒绝 unknown operator，拒绝缺失 `risk` 或 `confidence` 的 ranked item。
- picker 在无 caps 时选择 rank 1。
- picker 在 rank 1 被 generation 或 rolling cap 禁止时选择下一个可用 rank，并记录 selected rank 和 cap reason。
- picker 在低置信近似平局时 deterministic 选择 lower-risk operator。
- picker 不使用 RNG，不输出 sampler probabilities。
- trace 中可直接看到 LLM ranking 与最终 selected rank。
- 所有 focused tests 通过。

## 预期研究影响

新路线不会承诺一定超过 `union`。它承诺恢复清晰实验问题：

> 在相同 primitive operator support、相同 evaluation budget、相同 legality policy 下，LLM 对热布局状态的语义排序是否比 random uniform operator selection 更有效？

如果新路线仍输给 `union`，结论会更有解释力：不是 sampler 稀释造成的假阴性，而是 LLM 排序本身、prompt evidence、operator taxonomy 或 small-budget exploration tradeoff 需要进一步研究。
