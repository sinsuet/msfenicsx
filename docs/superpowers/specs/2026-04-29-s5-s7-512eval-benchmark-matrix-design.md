# S5-S7 512-Evaluation Benchmark 矩阵设计

## 目标

本设计定义在 800 核服务器上验证论文主线 S5-S7 aggressive thermal-layout 场景的大规模 benchmark 矩阵。该 benchmark 拆分回答三个问题：

1. 与 SPEA2、MOEA/D 相比，NSGA-II 是否是合理的 raw backbone。
2. 在匹配 evaluation budget 下，NSGA-II 主线是否从 raw 到 union 到 LLM-guided control 逐步提升。
3. LLM controller 在六个 provider profile 上是否稳定。

本设计同时规定矩阵拆分、seed 语义、资源调度、失败处理，以及 matrix-level 可视化和统计报告口径。

## 固定预算和 Seed

每个正式 optimization run 使用同一个 nominal budget：

```text
population_size = 32
num_generations = 16
nominal_budget = 512 evaluations/run
```

benchmark 使用五个 unified replicate seeds。每个 replicate seed 同时定义一个 concrete thermal case 和一条 optimizer random stream，但 optimizer stream 使用确定性 offset 以避免两个 RNG 入口使用完全相同的整数：

```text
replicate_seeds = [11, 17, 23, 29, 31]
algorithm_seed_offset = 1000
benchmark_source.seed = replicate_seed
algorithm.seed = replicate_seed + algorithm_seed_offset
```

`benchmark_source.seed` 控制 scenario template 的参数采样和布局放置，用来生成不同的 concrete thermal case。`algorithm.seed` 控制该 case 上的 optimizer 随机性，通过 pymoo 的 `seed=` 传入，并进一步变成 `algorithm.random_state`。二者不再作为独立全因子维度展开，而是由同一个 replicate seed 成对派生。

因此每个 scenario-method cell 包含：

```text
5 benchmark replicates × 1 optimizer trajectory = 5 runs
```

这种口径把每个 seed 视为一个端到端独立 replicate，仍然支持同 seed 下 raw、union、LLM 和 raw backbone methods 的 paired comparison，但不再单独估计同一 case 上 optimizer 随机性的方差。

matrix runner 不能只依赖当前 `run-benchmark-suite` 的 seed 行为，因为该命令目前只暴露 `--benchmark-seed`。每个 leaf run 必须使用冻结的临时 optimization-spec snapshot，并在 snapshot 中写入选定的 `replicate_seed` 派生结果：`benchmark_source.seed`、`algorithm.seed`、population size、generation count、backbone/mode 和 LLM profile。

## 方法和 Run 数量

### Raw Backbone 基线

该 block 只比较 raw optimizer backbones：

```text
scenarios = [s5_aggressive15, s6_aggressive20, s7_aggressive25]
raw_backbones = [nsga2, spea2, moead]
replicate_seeds = [11, 17, 23, 29, 31]
algorithm.seed = replicate_seed + 1000
```

run 数量：

```text
3 scenarios × 3 raw backbones × 5 replicate seeds = 45 runs
```

S5/S6/S7 需要在现有 NSGA-II raw spec 旁边新增正式的 SPEA2 和 MOEA/D raw YAML 文件，不只依赖动态 backbone override。

### NSGA-II Union 主线

该 block 将 NSGA-II union 与共享的 NSGA-II raw 结果比较：

```text
3 scenarios × 1 union mode × 5 replicate seeds = 15 runs
```

NSGA-II raw 直接复用 raw backbone baseline 中的结果，不重复运行。

### NSGA-II LLM Profile 矩阵

LLM block 使用六个统一下划线命名的 profile IDs：

```text
gpt_5_4
qwen3_6_plus
glm_5
minimax_m2_5
deepseek_v4_flash
gemma4
```

run 数量：

```text
3 scenarios × 6 LLM profiles × 5 replicate seeds = 90 runs
```

共享 NSGA-II raw 后的正式 run 总数：

```text
NSGA-II raw      15
SPEA2 raw        15
MOEA/D raw       15
NSGA-II union    15
NSGA-II llm      90
-------------------
total           150 runs
```

总 nominal evaluations：

```text
150 × 512 = 76,800 evaluations
```

## 矩阵拆分

完整矩阵必须拆成更小、可控、可恢复的 blocks：

```text
M0_pilot_512eval                  不进入正式论文统计
M1_raw_backbone_512eval           45 runs
M2_nsga2_union_512eval            15 runs
M3a_llm_gpt_5_4_512eval           15 runs
M3b_llm_qwen3_6_plus_512eval      15 runs
M3c_llm_glm_5_512eval             15 runs
M3d_llm_minimax_m2_5_512eval      15 runs
M3e_llm_deepseek_v4_flash_512eval 15 runs
M3f_llm_gemma4_512eval            15 runs
M4_rerun_failed_512eval           dynamic
M5_aggregate_visualize_512eval    不运行 optimizer
```

M0 只用于验证和压力测试。它验证 spec snapshots、profile resolution、trace output、rendering、aggregation 和服务器资源表现。M0 结果不纳入正式论文统计。

M4 只补跑 failed、timed-out、missing-artifact 或 render-failed 的 leaf runs。原始失败 attempt 必须保留，补跑使用 `attempt=2`。自动补跑最多一次。

## Matrix Runner 要求

matrix runner 必须生成 `run_index.csv` 和每个 run 的 spec snapshot。最小 index 字段包括：

```text
matrix_id
block_id
scenario_id
method_id
algorithm_family
algorithm_backbone
mode
llm_profile
replicate_seed
benchmark_seed
algorithm_seed
population_size
num_generations
nominal_budget
optimization_spec_snapshot
evaluation_spec_path
template_path
run_root
attempt
status
failure_reason
started_at
finished_at
wall_seconds
actual_evaluations
feasible_count
render_status
trace_status
git_commit
git_dirty
spec_hash
template_hash
evaluation_spec_hash
environment_summary_hash
```

正式运行最好从 clean git working tree 开始，但本设计暂不把 clean 作为硬性要求。runner 必须始终记录 commit、dirty flag 和输入哈希。如果工作区是 dirty 状态，最终报告必须显式呈现。

## 资源和调度策略

benchmark 使用两层并行：

- `evaluation_workers`：单个 optimization run 内部用于 candidate evaluation 的 workers。
- `concurrent_runs`：scheduler 同时启动的独立 leaf runs 数量。

估算 worker 压力约为：

```text
estimated_workers = evaluation_workers × concurrent_runs
```

初始 caps：

```text
raw:
  evaluation_workers: 8
  concurrent_runs: 80
  estimated_workers: 640

union:
  evaluation_workers: 8
  concurrent_runs: 60
  estimated_workers: 480

external_llm_profile:
  evaluation_workers: 3
  concurrent_runs: 20
  estimated_workers: 60

gemma4:
  evaluation_workers: 3
  concurrent_runs: 4-8 initially
  may scale to 20 after pilot validation
```

raw cap 对 800 核服务器来说是高利用率且中等偏激进的设置。union cap 较均衡。external LLM cap 对 CPU 保守，但对 provider rate limit 可能仍偏激进。Gemma4 必须单独处理，因为本地 inference service 可能成为瓶颈，而不是 CPU。Gemma4 应从 4-8 concurrent runs 起步，只有在 latency、timeout rate、fallback count 和内存/GPU 压力稳定时才扩展到 20。

scheduler 必须执行全局 worker budget 控制。除非估算 worker 总数仍低于选定服务器预算，否则不能同时运行多个高 worker blocks。

M0 应包含资源 pilot：

```text
raw:    20×8 -> 40×8 -> 80×8
union:  20×8 -> 40×8 -> 60×8
LLM:    5×3  -> 10×3 -> 20×3
Gemma4: 2×3  -> 4×3  -> 8×3 -> 20×3, only if stable
```

每一步都应检查 CPU utilization、memory、disk IO wait、wall time、timeout rate、PDE failures、LLM retry/fallback counts 和 render failures。

## 失败处理和鲁棒性报告

失败 attempt 必须保留可见。补跑创建新的 attempt，不能覆盖失败输出目录。最终报告必须包含两种视角：

1. `success_only`：只统计成功 runs 的性能。
2. `failure_aware`：按 method/profile 报告 failure、timeout、infeasible、solver-failed 和 LLM-failed rates。

LLM diagnostics 必须尽可能包含质量和鲁棒性计数：

```text
request_count
retry_count
invalid_response_count
fallback_count
timeout_count
failure_count
```

token price 或 monetary cost 不作为该 benchmark 的主指标。

## 主指标和统计汇总

每个 run 的 primary outcomes：

```text
best feasible maximum temperature
best feasible temperature-gradient RMS
final Pareto hypervolume
feasible-run status/rate
```

每个 scenario-method/profile cell 在 5 runs 上报告：

```text
median [IQR]
mean ± std
best
worst
feasible_count / total_runs
feasible_rate
```

这 5 个样本是 matched replicate seeds。方法比较时直接在相同 replicate seed 上计算 paired differences；不再做 benchmark seed 内的 optimizer replicate 聚合。报告应强调 effect size、paired differences、win counts、average ranks 和 uncertainty intervals，而不是主要依赖 p-value，因为 replicate 数量只有 5 个。

推荐比较：

- Raw backbone：NSGA-II raw vs SPEA2 raw vs MOEA/D raw。
- NSGA-II ladder：NSGA-II raw vs NSGA-II union vs NSGA-II LLM。
- LLM profiles：六模型 leaderboard，以 final hypervolume 作为 primary rank，best feasible temperature 作为 secondary rank，feasible/failure rates 作为鲁棒性限定指标。

MOEA/D 可能因为 reference-direction 行为导致实际 population/evaluation 数量偏离 nominal 32×16 budget。这是允许的，但必须记录 `actual_evaluations`，并在分析中标记 budget deviation。

## Matrix-Level 可视化

per-run assets 保持不变：`render-assets` 仍然生成 run-local analytics、figures、traces 和 representatives。大矩阵额外增加 matrix-level figures 和 tables。

论文级 matrix figures 必须同时导出 PNG 和 PDF，并使用 colorblind-friendly palette。主统计图应显示 raw points + median/IQR，而不是只画 mean bar。

必须生成的 figure families：

1. 每个 primary outcome 的 distribution plots，每个 scenario-method/profile cell 显示 5 个 run points。
2. Paired-difference plots：在 matched replicate seed 上比较 union 和 LLM 相对 raw 的差异。
3. Rank heatmaps：展示 raw backbone methods 和 LLM profiles 在 S5/S6/S7 上的排名。
4. Failure/feasibility stacked bars：区分 success、infeasible、solver failure、LLM failure、timeout 和 missing artifacts。
5. Scenario-scaling plots：展示 S5 到 S7 的 median outcomes 和 ranks 变化。
6. LLM controller diagnostics：展示 request/retry/invalid/fallback 行为。

Representative layout 和 thermal-field exports 使用以下规则：

```text
For each scenario × method/profile, select the successful run with the best final hypervolume.
Within that run, select the Pareto knee point as the representative candidate.
```

该规则展示 best-observed Pareto quality，同时用确定性的非手工规则选择具体代表点。

## Comparison Bundles

matrix aggregator 负责完整统计比较。仓库级 `compare-runs` bundles 只为关键 representative runs 生成，不为所有 pairwise combination 生成。这样避免 pairwise 爆炸，同时保留论文示例所需的 concrete comparison artifacts。

## 后续实现范围

后续 implementation plan 应覆盖：

1. 新增 S5/S6/S7 SPEA2 和 MOEA/D raw optimization specs。
2. 新增或扩展 matrix runner，写入 per-leaf spec snapshots 和 `run_index.csv`。
3. 增加 resume 和 single-block execution filters。
4. 增加失败 run 的 `attempt=2` 补跑生成。
5. 增加 matrix aggregation tables，用于 outcomes、ranks、paired differences、failures 和 LLM diagnostics。
6. 增加 matrix-level figure rendering，输出 PNG/PDF 并使用 colorblind-safe styling。
7. 增加 representative-run selection 和关键 `compare-runs` bundle generation。
8. 增加 focused tests，覆盖 spec generation、replicate seed snapshotting、run-index creation、retry behavior 和 aggregation formulas。
