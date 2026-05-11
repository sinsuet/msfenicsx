# 统一 Benchmark Runner 设计

## 背景

当前 optimizer 运行入口经历了多轮增量扩展，已经形成多个相互重叠的命令：

- `optimize-benchmark`
- `run-llm`
- `run-benchmark-suite`
- `run-benchmark-matrix`
- `aggregate-benchmark-matrix`
- `render-assets`
- `compare-runs`
- `replay-llm-trace`
- `analyze-controller-trace`

这些入口在日常使用上造成三个问题。

第一，运行语义不统一。旧的单 run、suite、matrix 各自维护 leaf 展开、seed、budget、profile、render 和 comparison 逻辑，很容易出现同一实验家族内 raw、union、llm 预算或 seed 口径不一致。

第二，当前 `run-benchmark-suite --parallel` 的实现路线不适合 FEniCSx/PETSc。它在父 Python 进程中导入 optimizer/FEniCSx 相关模块后，再用 multiprocessing `fork` 启动 leaf worker。PETSc、MPI、OpenMP、BLAS 和 FEniCSx 都不应在这种已初始化状态下 fork 进入多个子进程。实际表现是多个进程看似启动、CPU 被占用，但 leaf 迟迟不写入 seed artifacts，后续 raw/union/llm 与 render 都没有真正完成。之前服务器上疑似 “gli/render 卡住” 的现象应视为该 fork unsafe 调度的症状，而不是 rendering 本身的根因。

第三，旧 `matrix` 是针对旧服务器和旧实验拆分写的，现在 paper-facing 主线、预算、服务器资源和日常调参方式都已经变化。继续保留旧 matrix 代码和计划会污染代码库，并诱导后续运行走回不兼容的路径。

本设计用一个新的统一入口 `run-benchmark` 取代所有日常运行命令。它既支持单个 leaf，也支持 batch/campaign，并把 leaf 执行、实时日志、render、LLM trace 诊断、comparison、aggregate 和 IGD 统计纳入同一条正式运行链路。

## 目标

1. 提供唯一的日常 benchmark 入口：`run-benchmark`。
2. 支持单 leaf 运行，例如只跑 S5 seed-11 的 `llm:gpt`，也支持 batch/campaign 运行，例如 S5 raw+union 的 5 个 seeds。
3. 彻底废弃旧 `suite`、旧 `matrix`、旧单独 `run-llm` 和旧裸 `optimize-benchmark` 工作流，不做向后兼容。
4. 用 subprocess supervisor 启动 leaf，避免在导入 FEniCSx/PETSc 后 fork。
5. 在当前 2×Xeon Gold 6430、64 physical cores、128 logical threads、754 GiB RAM 服务器上充分但可控地利用 CPU 和内存。
6. 运行过程中持续写 JSONL 日志与进度摘要，不再只在最后写 artifacts。
7. 不再创建全局 `scenario_runs/logs/`。
8. 每个 leaf 结束时自动执行 render 与必要的 LLM 诊断；正常 run 不要求用户单独调用 `render-assets`、`replay-llm-trace` 或 `analyze-controller-trace`。
9. 对 raw/union 记录清晰 wall-clock 时间；对 llm 额外记录每个 LLM leaf 的总运行时间、每次 LLM 调用延迟、总 LLM 延迟、token 汇总和 provider/model 身份。
10. 在 comparison/aggregate 层增加 IGD 指标，和 hypervolume 等指标并列输出。
11. 允许后续补跑 LLM 单 seed 或单模型，并自动生成正确的 by-seed comparison，不污染未配齐 seed 的 aggregate。

## 非目标

- 不改变 S4/S5/S6 的 paper-facing 预算、目标函数、repair path、operator substrate 或 LLM controller policy。
- 不在本机调度模型 GPU 资源。LLM 通过远程 OpenAI-compatible endpoint 访问，本地只负责请求和日志。
- 不迁移旧 `scenario_runs/` artifacts。
- 不保留旧 command 的兼容 alias。删除就是删除，避免后续文档和脚本继续引用旧入口。
- 不把图片渲染改成边跑边生成。运行过程中需要日志即可；图片和 analytics 在 leaf 完成后自动生成。

## 新命令面

日常只暴露一个运行命令：

```bash
conda run -n msfenicsx python -m optimizers.cli run-benchmark [args]
```

该命令有两种使用形态。

### 单 leaf

单 leaf 面向日常 LLM 调参，也可用于 raw/union/spea2/moead smoke 或补跑。

```bash
conda run -n msfenicsx python -m optimizers.cli run-benchmark \
  --optimization-spec scenarios/optimization/s5_aggressive15_llm.yaml \
  --mode llm \
  --llm-profile gpt \
  --benchmark-seed 11 \
  --algorithm-seed 1011 \
  --population-size 40 \
  --num-generations 32 \
  --evaluation-workers 16 \
  --campaign-id s5_budgeted_main \
  --compare-with ./scenario_runs/s5_aggressive15/<raw_union_run_id> \
  --scenario-runs-root ./scenario_runs
```

`--mode` 支持：

- `raw`
- `union`
- `llm`

raw-only algorithm comparison 仍然通过 optimization spec 表达，例如 `s5_aggressive15_spea2_raw.yaml` 和 `s5_aggressive15_moead_raw.yaml`，method label 分别解析为 `spea2_raw` 和 `moead_raw`。它们不被提升成 `union` 或 `llm` 模式。

LLM profile 进入 method label。示例：

- `llm:gpt`
- `llm:qwen3_6_plus`
- `llm:deepseek_v4_flash`
- `llm:mimo_v2_5`

因此同一个 seed 下可以比较：

```text
raw vs union vs llm:gpt
raw vs union vs llm:gpt vs llm:qwen3_6_plus
```

### Batch/Campaign

batch 面向正式多 leaf 执行：

```bash
conda run -n msfenicsx python -m optimizers.cli run-benchmark \
  --batch-spec scenarios/batches/s5_raw_union_budgeted.yaml
```

batch spec 定义 campaign、scenario、methods、seeds、预算、资源参数和 comparison policy。示例语义：

```yaml
campaign_id: s5_budgeted_main
scenario_runs_root: ./scenario_runs
scenario_id: s5_aggressive15
methods:
  - method_id: nsga2_raw
    mode: raw
    optimization_spec: scenarios/optimization/s5_aggressive15_raw.yaml
  - method_id: nsga2_union
    mode: union
    optimization_spec: scenarios/optimization/s5_aggressive15_union.yaml
replicate_seeds: [11, 17, 23, 29, 31]
algorithm_seed_offset: 1000
population_size: 40
num_generations: 32
resource_policy:
  max_concurrent_leaves: 4
  leaf_evaluation_workers: 32
comparison_policy:
  by_seed: true
  aggregate: true
```

`batch-spec` 不是日常单 LLM 调参的强制入口。用户要跑一个 S5 seed-11 的 `llm:gpt` 时，直接用单 leaf 命令，不需要手写一个单 leaf batch YAML。

### Campaign identity

`campaign_id` 是实验家族的稳定逻辑 ID，不等同于时间戳 run root。第一次 batch 运行会创建一个新的 campaign root，并在 `campaign.yaml` 中记录 `campaign_id`。后续单 leaf 补跑如果同时提供 `--campaign-id` 和 `--compare-with`：

- leaf artifacts 写到新的 leaf run root 或指定的 active campaign append root，具体由实现计划决定；
- comparison context 必须读取 `--compare-with` 指向的既有 campaign root；
- 输出 comparison 可以写回既有 campaign 的 `comparisons/`，也可以写到新 leaf run root 的 `comparisons/linked/`，但必须在 manifest 中记录 source roots；
- 不允许只凭 `campaign_id` 在全局 `scenario_runs` 中模糊搜索并自动挑一个旧 run root。

这个规则的重点是避免同名 campaign 的历史 run 被误配。显式路径优先于字符串 ID。

## 命令删除策略

以下命令从日常 CLI 删除，不保留兼容入口：

- `optimize-benchmark`
- `run-llm`
- `run-benchmark-suite`
- `run-benchmark-matrix`
- `aggregate-benchmark-matrix`
- `render-assets`
- `compare-runs`
- `replay-llm-trace`
- `analyze-controller-trace`

实现上可以保留可复用的内部模块，例如 renderer、comparison builder、LLM replay/analyzer 函数，但它们不能作为用户日常 CLI 暴露。完整 run 的末尾必须自动调用这些内部能力。

旧 matrix 必须完全删除：

- 删除 `optimizers/matrix/`。
- 删除旧 matrix runner 和 aggregator tests。
- 删除旧 matrix specs/plans 作为 active guidance 的引用。
- 更新 README、AGENTS.md 和相关 docs，使 `run-benchmark` 成为唯一正式入口。

旧 `run-benchmark-suite` 并行设计也必须废弃。`docs/superpowers/specs/2026-05-08-suite-parallel-execution-design.md` 和对应 plan 只能作为历史记录存在，不得继续作为当前实现计划引用。

## 运行架构

### 总体结构

`run-benchmark` 分成四层：

1. CLI/spec loader：解析单 leaf args 或 batch YAML，生成标准 `CampaignSpec`。
2. campaign planner：展开 leaf、生成 run root、snapshot specs、写入 campaign manifest 和 `run_index.csv`。
3. subprocess supervisor：按资源策略启动独立 Python interpreter 执行 leaf。
4. post-run pipeline：每个 leaf 完成后自动 render、LLM trace 诊断；campaign 结束或补跑完成后自动 comparison/aggregate。

关键原则是：supervisor 进程不导入 FEniCSx/PETSc/dolfinx 相关模块。leaf 作为独立 Python 解释器启动，在子进程内部完成 FEniCSx 初始化、PDE evaluation worker pool 和 artifacts 写入。

### Leaf 启动方式

supervisor 使用 `subprocess.Popen` 启动 leaf，而不是 `ProcessPoolExecutor(fork)`。

每个 leaf 命令内部可以继续使用 `optimizers.problem.BenchmarkOptimizationProblem` 的 evaluation workers。leaf 内部 evaluation workers 已经使用 `get_context("spawn")`，该路径保留。

supervisor 为每个 leaf 设置环境：

```text
PYTHONUNBUFFERED=1
OMP_NUM_THREADS=1
MKL_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
NUMEXPR_NUM_THREADS=1
MPLBACKEND=Agg
CUDA_VISIBLE_DEVICES=
```

这些环境变量防止每个 PDE worker 再隐式启动多线程 BLAS/OpenMP，避免 4 个 leaf × 16 workers × BLAS threads 的超售。raw/union/llm 的 PDE 部分主要吃 CPU，本地 8 张 RTX 4090 不应被默认占用。

### 当前服务器资源策略

当前机器：

```text
CPU: 2 × Intel Xeon Gold 6430
physical cores: 64
logical threads: 128
RAM: ~754 GiB
GPU: 8 × RTX 4090, raw/union 不依赖本地 GPU
```

正式 S5/S6 raw+union 或 LLM batch 默认建议：

```text
max_concurrent_leaves = 4
leaf_evaluation_workers = 32
total PDE workers ~= 128
```

这样把主要 PDE worker 数量对齐到 128 logical threads（4 leaves × 32 workers）。PDE/FEniCSx 求解在 logical threads 上也能获得可观收益，充分利用可用并行度。内存按 754 GiB 估算足够支撑 4 个 formal-budget leaves 并行；如果实际观测到每个 leaf 峰值内存偏低，可以后续把 `max_concurrent_leaves` 调到 5 或 6，但这属于运行策略，不是默认实现。

保守调试：

```text
max_concurrent_leaves = 2
leaf_evaluation_workers = 8
```

单 leaf LLM 调参：

```text
max_concurrent_leaves = 1
evaluation_workers = 32
```

## 输出布局

新 runner 不创建 `scenario_runs/logs/`。所有运行日志和 trace 都写到对应 campaign 或 seed 目录下。

### Campaign root

```text
scenario_runs/<scenario_id>/<MMDD_HHMM>__<campaign_slug>/
├── campaign.yaml
├── run_index.csv
├── shared/
│   ├── input_hashes.json
│   └── environment.json
├── raw/
│   └── seeds/
│       ├── seed-11/
│       └── seed-17/
├── union/
│   └── seeds/
├── llm-gpt/
│   └── seeds/
├── comparisons/
│   ├── by_seed/
│   │   └── seed-11/
│   └── aggregate/
└── reports/
    └── campaign_summary.json
```

`mode_slug` 使用稳定顺序和可读标签：

- `raw`
- `union`
- `llm-<profile>`
- `spea2-raw`
- `moead-raw`

### Seed leaf root

```text
<method_slug>/seeds/seed-<n>/
├── run.yaml
├── optimization_result.json
├── pareto_front.json
├── traces/
│   ├── run_events.jsonl
│   ├── evaluation_events.jsonl
│   ├── generation_summary.jsonl
│   ├── operator_trace.jsonl
│   ├── controller_trace.jsonl
│   ├── llm_request_trace.jsonl
│   └── llm_response_trace.jsonl
├── summaries/
│   ├── runtime_summary.json
│   ├── llm_runtime_summary.json
│   ├── llm_replay_summary.json
│   └── controller_trace_summary.json
├── analytics/
├── figures/
│   └── pdf/
└── representatives/
```

raw/union 不写 LLM-only traces 和 summaries。`controller_trace.jsonl`、`llm_request_trace.jsonl`、`llm_response_trace.jsonl`、`llm_runtime_summary.json`、`llm_replay_summary.json` 和 `controller_trace_summary.json` 只在 LLM leaf 中出现。

## 实时日志与运行事件

`traces/run_events.jsonl` 是新 runner 的主进度日志，必须随运行持续 append 和 flush。每条记录至少包含：

```json
{
  "timestamp": "2026-05-08T22:00:00+08:00",
  "event": "generation_finished",
  "scenario_id": "s5_aggressive15",
  "method_id": "nsga2_union",
  "mode": "union",
  "llm_profile": null,
  "seed": 11,
  "generation": 7,
  "elapsed_seconds": 521.3,
  "message": "generation 7 finished",
  "metrics": {
    "evaluations_total": 320,
    "feasible_total": 41,
    "cheap_skips_total": 97,
    "pde_attempts_total": 223
  }
}
```

建议事件：

- `leaf_started`
- `spec_snapshot_written`
- `baseline_started`
- `baseline_finished`
- `generation_started`
- `evaluation_batch_started`
- `evaluation_batch_finished`
- `generation_finished`
- `render_started`
- `render_finished`
- `llm_replay_started`
- `llm_replay_finished`
- `controller_analysis_started`
- `controller_analysis_finished`
- `leaf_completed`
- `leaf_failed`

`generation_summary.jsonl` 继续保留 optimizer 代际统计，但需要边跑边写，而不是只在内存中积累到最后。`evaluation_events.jsonl` 和 `operator_trace.jsonl` 保持 JSONL streaming。

## Runtime summary

raw/union/spea2/moead 的 `summaries/runtime_summary.json` 至少包含：

```json
{
  "scenario_id": "s5_aggressive15",
  "method_id": "nsga2_raw",
  "mode": "raw",
  "seed": 11,
  "population_size": 40,
  "num_generations": 32,
  "nominal_budget": 1280,
  "run_wall_seconds": 12345.6,
  "optimizer_wall_seconds": 12001.2,
  "baseline_wall_seconds": 41.8,
  "postprocess_wall_seconds": 302.6,
  "render_wall_seconds": 287.4,
  "pde_wall_seconds_total": 98765.4,
  "evaluation_count": 1280,
  "pde_attempt_count": 902,
  "cheap_skip_count": 378,
  "feasible_count": 211,
  "failed_evaluation_count": 0
}
```

LLM leaf 除上述字段外，额外写 `summaries/llm_runtime_summary.json`：

```json
{
  "scenario_id": "s5_aggressive15",
  "method_id": "llm:gpt",
  "mode": "llm",
  "llm_profile": "gpt",
  "provider": "openai_compatible",
  "model": "gpt-5.4",
  "remote_endpoint_label": "GPT_PROXY_BASE_URL",
  "run_wall_seconds": 14000.0,
  "optimizer_wall_seconds": 13610.2,
  "llm_request_count": 96,
  "llm_response_count": 96,
  "llm_retry_count": 2,
  "llm_fallback_count": 1,
  "llm_latency_seconds_total": 812.4,
  "llm_latency_seconds_mean": 8.46,
  "llm_latency_seconds_median": 6.92,
  "llm_latency_seconds_p95": 21.4,
  "llm_latency_seconds_max": 37.8,
  "tokens_prompt_total": 123456,
  "tokens_completion_total": 18432,
  "tokens_total": 141888,
  "tokens_total_per_request_mean": 1478.0
}
```

该 summary 既单独存成 JSON，也作为最后一条 `run_events.jsonl` 事件写入，便于 `tail` 查看。

不记录 API key、完整 base URL secret、认证 header 或任何敏感凭据。`remote_endpoint_label` 只写 profile 中使用的环境变量名或非敏感 provider label。

## Comparison planner

Comparison 必须按 seed 分层，再做共同 seed 集合上的 aggregate。runner 不全局扫描整个 `scenario_runs` 做隐式匹配，只在同一个 campaign 内自动匹配；跨 run 补跑时必须通过 `--campaign-id` 或 `--compare-with` 明确加入比较上下文。

匹配条件：

- `scenario_id` 相同。
- `benchmark_seed` 相同。
- `population_size` 和 `num_generations` 相同。
- `evaluation_spec` hash 相同。
- template/spec 的 benchmark-relevant hash 兼容。
- objectives 相同。
- hard constraint 和 repair/canonicalization path 兼容。

### 示例：先跑 S5 raw+union 五个 seeds

运行 S5 raw+union seeds `[11, 23, 31, 37, 41]` 后，自动生成：

```text
comparisons/by_seed/seed-11/    raw vs union
comparisons/by_seed/seed-23/    raw vs union
comparisons/by_seed/seed-31/    raw vs union
comparisons/by_seed/seed-37/    raw vs union
comparisons/by_seed/seed-41/    raw vs union
comparisons/aggregate/          raw vs union over 5 seeds
```

### 示例：后续补跑 S5 seed-11 的 llm:gpt

后续单独运行：

```text
S5 seed-11 llm:gpt
```

并指定同一 `campaign_id` 或 `--compare-with` 上面的 raw+union campaign 后，runner 自动补生成：

```text
comparisons/by_seed/seed-11/    raw vs union vs llm:gpt
```

此时不会生成 `raw vs union vs llm:gpt over 5 seeds`，因为 `llm:gpt` 只有 seed-11。aggregate 只允许使用所有参与 method 的共同 seed 集合；共同 seed 数为 1 时，输出单 seed comparison，不输出冒充多 seed 的 aggregate。

### 示例：LLM 五个 seeds 补齐

如果之后补跑 `llm:gpt` 的 seed-17、23、29、31，则每补一个 seed 自动更新对应 by-seed comparison。五个 seeds 全部配齐后，自动生成：

```text
comparisons/aggregate/          raw vs union vs llm:gpt over 5 seeds
```

如果同一 campaign 还包含 `llm:qwen3_6_plus`，则 aggregate 按共同 seed 集合分别判断。`raw vs union vs llm:gpt` 和 `raw vs union vs llm:qwen3_6_plus` 可以拥有不同 seed 覆盖，不互相阻塞。

## IGD 指标

IGD 是 comparison/aggregate 层指标，不作为单个 run 自证指标。单个 leaf 没有独立 reference front，不能定义有意义的最终 IGD。

reference front 使用当前 comparison context 内所有参与 method、所有共同 seeds 的 feasible Pareto points 的 nondominated union，经同一 objective normalization 后得到 empirical reference front。

每个 method 输出：

- `final_hypervolume`
- `final_igd`
- `feasible_count`
- `evaluations_total`
- `best_temperature_max`
- `best_temperature_gradient_rms`
- 需要时输出 `igd_progress`，但正式表格至少包含 final IGD。

IGD 越小越好，hypervolume 越大越好。报告和 CSV 必须明确方向，避免读表时误解。

当 comparison context 中某个 method 没有任何 feasible Pareto point 时：

- `final_igd` 写为 null。
- `feasible_count=0`。
- failure/infeasible 状态必须保留在 summary 表中，不能静默删除该 method。

## Post-run pipeline

每个 leaf 成功结束后自动执行：

1. 写终态 artifacts：`optimization_result.json`、`pareto_front.json`、`run.yaml`、runtime summaries。
2. render 当前 seed leaf assets。
3. 如果是 LLM leaf，执行 LLM trace replay summary 和 controller trace analysis summary。
4. 更新 campaign `run_index.csv`。
5. 通知 comparison planner 检查该 seed 是否可以生成或刷新 by-seed comparison。

campaign 内所有 leaf 完成后自动执行：

1. 生成或刷新所有可用 `comparisons/by_seed/seed-*`。
2. 基于共同 seed 集合生成可用 `comparisons/aggregate/`。
3. 写 `reports/campaign_summary.json`。

若某个 leaf 失败：

- 失败状态写入 `run_index.csv`。
- `traces/run_events.jsonl` 写 `leaf_failed`。
- 其他 leaf 继续运行。
- comparison planner 跳过该失败 leaf，但 summary 中保留 failure 记录。

## 旧代码清理范围

实现计划必须包含以下清理。

删除或重写：

- `optimizers/run_suite.py`
- `optimizers/suite_parallel.py`
- `optimizers/matrix/`
- 旧 suite/matrix CLI parser 和 dispatch。
- 旧命令对应 tests。
- 旧 matrix active docs/plans 的当前引用。

保留为内部模块并改由 `run-benchmark` 调用：

- rendering 相关实现。
- comparison builder。
- LLM request/response trace 解析。
- controller trace analysis。

文档更新：

- `README.md`
- `AGENTS.md`
- 相关 `docs/` 中当前命令示例。
- smoke 脚本，改为覆盖 `run-benchmark` 单 leaf、小 batch、render 自动执行和 comparison 自动生成。

## 测试策略

实现必须先写 focused tests。

核心测试：

1. CLI 只暴露 `run-benchmark`，旧 run 命令不可用。
2. 单 leaf args 能生成标准 `CampaignSpec`。
3. batch spec 能展开 method × seed leaves，并派生 `algorithm_seed = benchmark_seed + 1000`。
4. subprocess supervisor 不使用 `fork` leaf pool，且 leaf env 包含线程限制变量。
5. `scenario_runs/logs/` 不会被创建。
6. seed root 下会 streaming 写 `run_events.jsonl`。
7. LLM summary 能从 request/response trace 计算 latency 和 token 汇总。
8. raw/union runtime summary 只要求 wall-clock 和 PDE/evaluation 统计，不要求 LLM 字段。
9. comparison planner 对 raw+union 五 seeds 生成五个 by-seed comparison 和一个 raw-vs-union aggregate。
10. 后续补跑单个 `llm:gpt seed-11` 只刷新 seed-11 的三模式 comparison，不生成三模式五 seed aggregate。
11. 五个 LLM seeds 补齐后生成三模式 aggregate。
12. IGD 使用 comparison context 的 empirical reference front，方向为越小越好。
13. 失败 leaf 不阻塞其他 leaf，且 comparison summary 保留 failure 状态。

运行测试优先使用：

```bash
conda run -n msfenicsx pytest -v tests/optimizers
```

如果实现触及 shared analytics、visualization 或 CLI contract，再补充：

```bash
conda run -n msfenicsx pytest -v tests/visualization tests/cli tests/optimizers
```

## 迁移后的正式用法

### S5 raw+union 五 seeds

```bash
conda run -n msfenicsx python -m optimizers.cli run-benchmark \
  --batch-spec scenarios/batches/s5_raw_union_budgeted.yaml
```

默认资源：

```text
max_concurrent_leaves=4
leaf_evaluation_workers=32
```

预期输出：

```text
scenario_runs/s5_aggressive15/<MMDD_HHMM>__raw_union/
```

并自动包含 raw-vs-union by-seed 与 aggregate comparison。

### S5 单 seed LLM GPT 补跑

```bash
conda run -n msfenicsx python -m optimizers.cli run-benchmark \
  --optimization-spec scenarios/optimization/s5_aggressive15_llm.yaml \
  --mode llm \
  --llm-profile gpt \
  --benchmark-seed 11 \
  --algorithm-seed 1011 \
  --population-size 40 \
  --num-generations 32 \
  --evaluation-workers 16 \
  --campaign-id s5_budgeted_main \
  --compare-with ./scenario_runs/s5_aggressive15/<MMDD_HHMM>__raw_union \
  --scenario-runs-root ./scenario_runs
```

预期自动输出：

```text
comparisons/by_seed/seed-11/    raw vs union vs llm:gpt
```

不会输出三模式五 seed aggregate，直到 `llm:gpt` 的五个 seeds 都配齐。

## 风险和处理

1. Leaf subprocess 失败但 supervisor 误判成功。  
   处理：leaf 必须写 terminal status marker；supervisor 同时检查 exit code 和必需 artifacts。

2. LLM trace token 字段在不同 provider 中名称不一致。  
   处理：解析层支持 OpenAI-compatible 常见 `usage.prompt_tokens`、`usage.completion_tokens`、`usage.total_tokens`，缺失时写 null，不编造 token。

3. Render 失败导致整个 leaf 被判失败。  
   处理：optimizer 成功但 render 失败时 leaf status 为 `completed_render_failed`，comparison 可使用 numeric artifacts，但 final campaign summary 必须暴露 render failure。

4. 单 leaf 补跑误配旧 raw/union。  
   处理：`--compare-with` 只接受明确 run root；comparison planner 仍校验 spec/eval/budget/hash，失败则拒绝合并。

5. 多 profile LLM aggregate seed 覆盖不一致。  
   处理：aggregate metadata 写清每个 method 的 included seeds 和 excluded/missing seeds；不同 method set 的 aggregate 分开命名。

## 验收标准

实现完成后，以下行为必须成立：

1. 用户不再需要调用 `render-assets`、`compare-runs`、`replay-llm-trace` 或 `analyze-controller-trace` 来完成一次正式 run。
2. `scenario_runs/logs/` 不再由 optimizer runner 创建。
3. S5 raw+union 五 seeds 可以用一个 batch command 并行运行，leaf 数并行，不是先 raw 全部跑完再 union。
4. S5 seed-11 单独 LLM profile 可以用一个短命令运行，并和已有 raw/union seed-11 自动生成三模式 comparison。
5. LLM 五 seeds 未配齐前，不会生成误导性的三模式五 seed aggregate。
6. LLM 日志最后可以直接看到总运行时间、LLM 请求数、延迟总和/均值/中位数/p95/max、token 总数。
7. raw/union 日志和 summary 至少能看到总 wall-clock 时间。
8. comparison 表包含 IGD，且方向标注为越小越好。
9. 代码库中没有旧 matrix active path，也没有旧 run command 的日常入口。
