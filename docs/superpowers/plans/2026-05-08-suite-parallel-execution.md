# 实现计划：run-benchmark-suite 并行执行

## Spec 引用

`docs/superpowers/specs/2026-05-08-suite-parallel-execution-design.md`

## 实施任务

### Task 1：新增 suite_parallel.py — leaf 展开与并行调度

新建 `optimizers/suite_parallel.py`，核心内容：

```python
# 展开所有 (mode, seed) 为 leaf 列表
def expand_leaves(
    spec_by_mode: dict[str, tuple[Path, OptimizationSpec]],
    selected_modes: list[str],
    effective_seeds: list[int],
) -> list[SuiteLeaf]:

# 单个 leaf 执行（线程安全，传入所有需要的参数，不读共享状态）
def run_leaf(
    leaf: SuiteLeaf,
    *,
    evaluation_workers: int | None,
    llm_profile: str,
    trace_output_root: Path,
) -> LeafResult:

# ThreadPoolExecutor 并行调度
def run_leaves_parallel(
    leaves: list[SuiteLeaf],
    *,
    max_concurrent: int,
    evaluation_workers: int | None,
    llm_profile: str,
    run_index_path: Path,
) -> list[LeafResult]:
```

- `SuiteLeaf` 是一个 dataclass，包含 mode, seed, spec_path, optimization_spec, evaluation_spec_path
- `LeafResult` 包含 mode, seed, status, wall_seconds, failure_reason
- 每个 leaf 内部：`generate_benchmark_case` → `_dispatch_run` → `write_optimization_artifacts` → `write_run_manifest`
- 全部 leaf 完成后写 `run_index.csv`

**线程安全处理：**
- `os.environ` 操作不是线程安全的。用 `_env_lock = threading.Lock()` 串行化所有 LLM profile overlay 写入
- 实际瓶颈在 PDE solve（CPU bound），LLM 请求等待只是 I/O，串行化 overlay 不影响整体并行度
- `_dispatch_run` 内部的 `ProcessPoolExecutor` 使用 `fork` context，每个 leaf 有独立的子进程池，互不干扰

### Task 2：修改 run_suite.py — 集成并行路径

修改 `run_benchmark_suite()`：

1. 新增参数：`parallel: bool`, `max_concurrent_leaves: int`, `leaf_evaluation_workers: int | None`, `continue_on_failure: bool`
2. 并行路径：
   ```
   if parallel:
       leaves = expand_leaves(spec_by_mode, selected_modes, effective_seeds)
       results = run_leaves_parallel(leaves, ...)
       # 对每个 mode root 做 render
       for mode in selected_modes:
           render_assets(mode_root)
       build_suite_comparisons(run_root)
       return run_root
   ```
3. 串行路径保持完全不变（early return 到现有逻辑）

### Task 3：修改 cli.py — 新增 CLI 参数

`suite_parser` 新增：

```python
suite_parser.add_argument("--parallel", action="store_true")
suite_parser.add_argument("--max-concurrent-leaves", type=_positive_int, default=20)
suite_parser.add_argument("--leaf-evaluation-workers", type=_positive_int, default=None)
suite_parser.add_argument("--continue-on-failure", action="store_true", default=True)
```

dispatch 传参到 `run_benchmark_suite()`。

### Task 4：测试

新建 `tests/optimizers/test_suite_parallel.py`：

1. `test_expand_leaves_basic` — 验证 3 modes × 3 seeds = 9 leaves
2. `test_expand_leaves_single_seed` — 验证 3 modes × 1 seed = 3 leaves
3. `test_run_index_csv_fields` — 验证 CSV 字段完整
4. `test_parallel_leaf_failure_does_not_block` — mock 一个 leaf 失败，验证其他 leaf 完成
5. `test_leaf_output_layout_compatible_with_render_assets` — 验证输出目录结构

## 验收标准

1. 串行模式下，`run-benchmark-suite` 行为与改动前 bit-for-bit 一致
2. `--parallel` 模式下，所有 leaf 并行执行，总 wall time 显著低于串行
3. 产出 `run_index.csv`，每个 leaf 有 completed/failed 状态
4. 某个 leaf 失败不阻塞其他 leaf（默认 continue_on_failure=True）
5. 并行执行后 `render_assets` 和 `build_suite_comparisons` 正常工作
6. 通过 `conda run -n msfenicsx pytest -v tests/optimizers/test_suite_parallel.py`

## 推荐的默认使用命令

**S5 full ladder, MIMO LLM, 5 seeds, 并行：**
```bash
conda run -n msfenicsx python -m optimizers.cli run-benchmark-suite \
  --optimization-spec scenarios/optimization/s5_aggressive15_raw.yaml \
  --optimization-spec scenarios/optimization/s5_aggressive15_union.yaml \
  --optimization-spec scenarios/optimization/s5_aggressive15_llm.yaml \
  --mode raw --mode union --mode llm \
  --llm-profile mimo_v2_5 \
  --benchmark-seed 11 --benchmark-seed 23 --benchmark-seed 31 \
  --benchmark-seed 37 --benchmark-seed 41 \
  --population-size 40 --num-generations 32 \
  --parallel --max-concurrent-leaves 20 \
  --leaf-evaluation-workers 1 \
  --scenario-runs-root ./scenario_runs
```

**S6, MIMO, 5 seeds：**
```bash
conda run -n msfenicsx python -m optimizers.cli run-benchmark-suite \
  --optimization-spec scenarios/optimization/s6_aggressive20_raw.yaml \
  --optimization-spec scenarios/optimization/s6_aggressive20_union.yaml \
  --optimization-spec scenarios/optimization/s6_aggressive20_llm.yaml \
  --mode raw --mode union --mode llm \
  --llm-profile mimo_v2_5 \
  --benchmark-seed 13 --benchmark-seed 19 --benchmark-seed 11 \
  --benchmark-seed 21 --benchmark-seed 23 \
  --population-size 56 --num-generations 36 \
  --parallel --max-concurrent-leaves 20 \
  --leaf-evaluation-workers 1 \
  --scenario-runs-root ./scenario_runs
```

**Historical S7 raw+union only (无 LLM)，5 seeds，已被 S4/S5/S6 final matrix 取代：**
```bash
conda run -n msfenicsx python -m optimizers.cli run-benchmark-suite \
  --optimization-spec scenarios/optimization/s7_aggressive25_raw.yaml \
  --optimization-spec scenarios/optimization/s7_aggressive25_union.yaml \
  --mode raw --mode union \
  --benchmark-seed 11 --benchmark-seed 13 --benchmark-seed 17 \
  --benchmark-seed 19 --benchmark-seed 23 \
  --population-size 64 --num-generations 40 \
  --parallel --max-concurrent-leaves 20 \
  --leaf-evaluation-workers 1 \
  --scenario-runs-root ./scenario_runs
```

**Historical S7 LLM only (Qwen), 1 seed，已被 S4/S5/S6 final matrix 取代：**
```bash
conda run -n msfenicsx python -m optimizers.cli run-benchmark-suite \
  --optimization-spec scenarios/optimization/s7_aggressive25_llm.yaml \
  --mode llm \
  --llm-profile qwen3_6_plus \
  --benchmark-seed 11 \
  --population-size 64 --num-generations 40 \
  --parallel --max-concurrent-leaves 1 \
  --leaf-evaluation-workers 1 \
  --scenario-runs-root ./scenario_runs
```

## 资源预算估算

| 场景 | leaves | 每 leaf 时间 (est) | 串行总时间 | 并行 (20 leaves) |
|------|--------|-------------------|-----------|-----------------|
| S5 raw+union+llm ×5 seeds | 15 | ~30 min | ~7.5 h | ~1.5 h |
| S6 raw+union+llm ×5 seeds | 15 | ~50 min | ~12.5 h | ~2.5 h |
| S7 raw+union ×5 seeds | 10 | ~80 min | ~13.3 h | ~4 h | historical, superseded |
| S7 llm ×1 seed | 1 | ~80 min | ~80 min | ~80 min | historical, superseded |

并行模式下总 CPU 利用率：20 leaves × 2 processes = 40 进程，接近 44 核上限。
