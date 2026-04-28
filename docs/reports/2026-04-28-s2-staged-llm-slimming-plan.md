# S2 staged LLM 链路低风险 slimming 方案

日期：2026-04-28

## 目标

降低 `s2_staged` 的 LLM 控制链路单次请求成本、prompt 体积、fallback 暴露面和小预算 smoke 的 wall time，同时保持 raw / union / llm 公平比较契约不变。

## 公平边界

本轮只改 representation-layer 行为：prompt projection、system prompt 表述和 LLM runtime 参数。不得改变：

- `primitive_clean` operator pool
- `minimal_canonicalization` legality policy
- expensive evaluation budget
- candidate support 完整性
- union / llm 共享 substrate

`policy_kernel` 继续作为 soft annotation / telemetry surface 使用，不恢复 hard filtering，不产生非空 suppression。

## 低风险改动

1. 在 prompt projection 层裁剪发送给模型的视图，而不改 `state_builder` 生成的完整诊断状态：
   - `run_panel` 移除大块 `objective_extremes`。
   - `generation_panel` 保留 accepted / dominant / streak / route-family 摘要，移除逐 operator counts。
   - `spatial_panel` 保留离散几何桶和关键标量，不传长文本。
   - `retrieval_panel` 将 positive matches 从 2 个降到 1 个，negative matches 仍保留 1 个。
   - `operator_panel` 移除长句 `spatial_match_reason`，保留 fit / applicability / risk / expected effect / evidence。

2. 压缩 controller system prompt：
   - 保留 JSON contract、candidate support、soft guidance、exact positive match、guardrail 语义。
   - 把 intent 和 operator 说明改成更短的机器可读映射，避免与 `metadata.intent_panel` / `metadata.prompt_panels.operator_panel` 重复。

3. 收紧 S2 LLM runtime 参数：
   - `max_output_tokens`: 96 -> 72。
   - `retry.timeout_seconds`: 45 -> 35。
   - `memory.recent_window`: 32 -> 16。
   - `retry.max_attempts` 先保留 2，继续保护 malformed JSON / schema invalid；timeout / HTTP error 仍直接 fallback。

## 暂不做的改动

- 不在本轮加入 per-generation cadence gate 或 cached-policy reuse。该方向节省最多，但会明显改变 controller 行为路径，需在 prompt/runtime trim 通过后单独验证。
- 不新增 GPT / Claude bundled provider profile。当前 `profiles.yaml` 和测试明确拒绝 legacy provider-style ids；GPT 链路若使用，先通过运行时 `LLM_*` 环境变量覆盖。

## 验证

先跑聚焦测试：

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_llm_controller.py
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_llm_controller_state.py
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_llm_policy_kernel.py
```

如 runtime profile 行为被触及，再补 `tests/optimizers/test_llm_profiles.py`。实验只在测试通过后从 S2 LLM 5×2 或 10×5 smoke 开始，输出到 `scenario_runs/s2_staged/`，并报告 scenario、template、spec、seed、预算、run path、prompt 大小、fallback 次数、平均响应时间和总 wall time。
