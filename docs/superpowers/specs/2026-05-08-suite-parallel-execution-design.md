# 设计：run-benchmark-suite 并行执行

## 背景

当前 `run-benchmark-suite` 以嵌套 for 循环串行执行所有 (mode, seed) 组合。在 44 核服务器上，一次 S5 raw+union+llm × 5 seeds 的完整 suite 需要串行跑 15 个 leaf，总耗时数小时。

`run-benchmark-matrix` 已经实现了 `ThreadPoolExecutor` 并行调度和 `run_index.csv` 追踪，但其 leaf 定义是硬编码的 block 结构，不支持灵活的 suite 级组合。

本设计为 `run-benchmark-suite` 增加 opt-in 并行执行能力，同时保持默认串行行为不变。

## 设计目标

1. 在 suite 命令上新增 `--parallel` 和 `--max-concurrent-leaves` 参数
2. 并行模式下展开所有 (mode, seed) 为独立 leaf，用 ThreadPoolExecutor 并行执行
3. 产出 `run_index.csv` 追踪每个 leaf 的状态
4. 全部 leaf 完成后统一 render，避免 I/O 干扰
5. 任何 leaf 失败不阻塞其他 leaf
6. 保持现有输出布局和 render_assets/compare_runs 兼容

## 机器资源模型

- 44 核 CPU, 216GB RAM, 4×24GB GPU
- 每个 leaf 使用 `ProcessPoolExecutor` 做 PDE 求解：
  - `evaluation_workers=1` → 2 进程 (1 main + 1 worker)
  - `evaluation_workers=2` → 3 进程 (1 main + 2 workers)
- 并行模式默认 `evaluation_workers=1`，让并行来自 leaf 数量
- 建议 `max_concurrent_leaves`：
  - 保守: 20 (40 进程, ~90% CPU)
  - 推荐: 22 (44 进程, 100% CPU)
  - 激进: 30+ (会超售，PDE 内部并行退化)

## leaf 定义

每个 leaf = (scenario, mode, seed, llm_profile, population_size, num_generations)

展开后示例（S5 raw+union+llm, seeds=[11,17,23,29,31], llm_profile=mimo_v2_5）：
- 3 modes × 5 seeds = 15 leaves
- 其中 10 个 non-LLM leaves + 5 个 LLM leaves

## 并行执行流程

```
1. 加载 specs，校验，展开 leaves
2. 创建 run root，写 manifest.json
3. snapshot shared inputs
4. 展开 leaves: [(mode, seed, spec, eval_spec, ...), ...]
5. 用 ThreadPoolExecutor(max_workers=N) 并行执行所有 leaves:
   - 每个 leaf 写到 mode_root/seeds/seed-<n>/
   - 每个 leaf 写 run.yaml (含 wall_seconds)
   - 每个 leaf 完成后更新 run_index.csv 行状态
6. 全部完成后:
   - render_assets(mode_root) for each mode
   - build_suite_comparisons(run_root)
7. 写最终 run_index.csv
```

## 输出布局

保持与现有 suite 完全一致：

```
<scenario_runs_root>/
  <scenario_template_id>/
    <run_id>/
      manifest.json
      run_index.csv          ← 新增，并行模式才有
      shared/
      raw/
        seeds/seed-11/...
        seeds/seed-17/...
      union/
        seeds/seed-11/...
      llm/
        seeds/seed-11/...
      comparisons/
```

`render_assets` 已经能解析此布局（`resolve_render_targets` → `iter_mode_seed_roots`），无需修改。

## run_index.csv 字段

简化版，不采用 matrix 的 45 列，只保留 suite 需要的：

```
mode, seed, llm_profile, population_size, num_generations,
status, started_at, finished_at, wall_seconds,
output_root, failure_reason
```

status 值: `pending`, `running`, `completed`, `failed`

## CLI 参数变更

现有 `run-benchmark-suite` 新增参数：

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--parallel` | flag | off | 启用并行 leaf 执行 |
| `--max-concurrent-leaves` | int | 20 | 并行模式下最大并发 leaf 数 |
| `--leaf-evaluation-workers` | int | None | 每个 leaf 内部的 evaluation workers (None=1 when parallel, None=2 when serial) |
| `--continue-on-failure` | flag | on | 某个 leaf 失败继续执行其他 leaf |

串行模式下行为完全不变（新增参数被忽略）。

## 代码变更范围

| 文件 | 变更 |
|------|------|
| `optimizers/cli.py` | suite_parser 加 4 个新参数; dispatch 传新参数 |
| `optimizers/run_suite.py` | 新增 `_run_suite_parallel()` 函数; `run_benchmark_suite()` 加 `parallel`/`max_concurrent_leaves`/`leaf_evaluation_workers`/`continue_on_failure` 参数 |
| `optimizers/suite_parallel.py` | 新文件，封装 leaf 展开、ThreadPoolExecutor 调度、run_index.csv 写入 |
| `tests/optimizers/test_suite_parallel.py` | 新测试 |

## 不变更的部分

- `run-benchmark-matrix` 完全不动
- `render_assets` 不动
- `compare_runs` 不动
- 现有串行 suite 行为不动
- 输出布局不变

## LLM 策略

当前 GPT (nexahubai.com) 配额耗尽，plan 中暂时不包含 gpt_5_4。可用的 LLM provider：
- `mimo_v2_5` — 已验证正常
- `qwen3_6_plus` — 待验证
- 其他 profiles 看实际需求

用户可以手动传 `--llm-profile` 切换，充值后恢复 gpt_5_4。
