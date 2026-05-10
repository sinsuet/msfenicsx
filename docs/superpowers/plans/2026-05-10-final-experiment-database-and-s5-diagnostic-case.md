# Final Experiment Database And S5/S6 Diagnostic Cases Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立最终五块实验的 paper-facing evidence database、IGD/nIGD 后处理、comparison 导出、S5 seed11 representative diagnostic case 图文口径，以及 S6 seed23 feedback-off negative-control 诊断证据；当前 Stage A 先处理已完成数据并将 S6 main 标为 pending，Stage B 等 S6 DeepSeek formal seeds `17,23,29,31` 补齐后再刷新。

**Architecture:** 计划把原始 `scenario_runs/` 视为不可改 source-of-truth，在 `scenario_runs/paper_experiment_db/` 生成可重复导入的数据库、扁平表、完整性矩阵、comparison 产物索引和论文图表清单。主统计证据来自每个 block 内 seed-matched aggregate comparison；S5 seed11 只作为 medium-scale representative diagnostic case 展示搜索轨迹、布局、热场和 controller 行为，不替代 multi-seed evidence。S6 seed23 feedback-off run 是 single-seed mechanism negative control，用于证明 operator-level PDE feedback 对 semantic controller 必要，必须从 S6 main aggregate 中排除。

**Tech Stack:** Python, DuckDB or CSV/Parquet exports, existing `optimizers.comparison_artifacts`, `optimizers.benchmark_runner.igd`, JSON/JSONL artifact inspection, matplotlib-generated figures, Markdown/LaTeX planning registers.

---

## Execution Staging

- **Stage A, run now:** build the database, comparisons, nIGD exports, and S5 diagnostic figure staging for all completed blocks: S4 main/semantic with active seeds `11,13,17,19,23`, S5 main, S5 model sensitivity, S5 algorithm baseline, and S6 seed23 feedback-off diagnostic.
- **Stage A rule:** keep `main_s6` as `pending`; do not wait for or infer missing S6 DeepSeek seeds. Current paper-facing tables can still be generated with `main_s6` omitted from aggregate metrics and marked pending in `claim_evidence.csv`.
- **Stage B, run later:** after valid S6 DeepSeek main seeds `17,23,29,31` finish with nonzero operator-level PDE feedback, archive S6 raw-vs-LLM into `scenario_runs/s6_aggressive20/0510_archive__raw_llm-deepseek_v4_flash_5seed`, rebuild S6 main comparison, and rerun Task 2 through Task 4 to refresh the database.

## Final Experiment Contract

### Claim Map

| Claim | Why It Matters | Minimum Convincing Evidence | Linked Blocks |
|---|---|---|---|
| C1: LLM semantic operator control improves expensive PDE-constrained thermal layout search under matched budget. | 这是论文主方法有效性的核心。 | S4/S5/S6 Main block 中，`raw` 与 `llm_deepseek_v4_flash` 在每个 block 内 matched seeds、matched budget、same scenario case、same repair/evaluation contract 下形成 `comparisons/by_seed` 和 `comparisons/aggregate`，并报告 gradient RMS、HV、nIGD、feasible rate、PDE accounting。 | Main |
| C2: Gain comes from closed-loop semantic operator routing, not merely from a larger operator pool or LLM operator choice. | 这是 reviewer 最可能质疑的机制 claim。 | S4 Semantic Ablation 中 `raw / union / llm` 的 aggregate comparison 隔离语义控制收益；S6 seed23 feedback-off diagnostic 显示当 `operator_panel` 中 operator-level PDE feedback 全为零时，DeepSeek run 的 HV 约为同 seed raw 的 51%，说明 semantic controller 需要 operator-effect feedback/credit assignment 闭环。 | Semantic Ablation, Feedback-Off Diagnostic |
| C3: The method is model-robust enough for a mechanism claim, but not a strong model-statistical claim. | 避免把 single-seed model sensitivity 过度解释成统计稳定性。 | S5 seed11 DeepSeek/Qwen/GPT/MiMo 以及已存在 GLM/MiniMax exploratory profiles 的 endpoint metrics、controller validity、fallback rate、latency 和 operator entropy。 | Model Sensitivity |
| C4: Raw baseline is not weak only because NSGA-II is weak. | 防止主结果被解释成 baseline 选择偏弱。 | S5 Algorithm Baseline 中 NSGA-II/SPEA2/MOEA/D raw 的 five-seed matched comparison。 | Algorithm Baseline |

### Seed-Cohort Policy

- Block 内必须 seed-matched：同一 block 的 compared methods 必须使用相同 benchmark seeds 和 algorithm seed offset。
- Block 间允许 seed cohort 不同：S4 main/semantic 当前使用 `11,13,17,19,23`，S5 main/algorithm baseline 当前使用 `11,23,31,37,41`，S6 main 仍固定计划为 `11,17,23,29,31` 但 Stage A pending。论文口径是扩大 stochastic coverage，而不是宣称所有 block 共用完全相同 seeds。
- 正文推荐句：

```text
Within each comparison block, all methods are matched on the same benchmark seeds, algorithm-seed offset, scenario case, repair policy, and expensive-evaluation budget. Across blocks, seed cohorts may differ to broaden stochastic coverage; therefore, aggregate claims are made within each registered comparison block rather than by pooling unmatched runs across blocks.
```

### Model-Sensitivity Policy

- Kimi 不再是 final requirement。
- 主表使用已完成或计划保留的 `DeepSeek / Qwen / GPT / MiMo`。
- `GLM / MiniMax` 可作为 appendix exploratory profiles。MiniMax 如果出现 all-fallback 或 invalid behavior，必须显式作为 controller compatibility diagnostic，而不是性能失败隐去。

### S5 Seed11 Diagnostic-Case Policy

- S5 seed11 是 `representative diagnostic case`，不是 main statistical evidence。
- 正文推荐句：

```text
The aggregate tables answer whether the method works across seeds and scale levels; the S5 seed11 diagnostic case shows how the method behaves in one fully traced medium-scale run.
```

- S5 seed11 可用于展示：
  - initial/final layout；
  - Pareto representative fields；
  - search trajectory network；
  - objective/HV/progress traces；
  - operator phase heatmap；
  - controller rank/fallback diagnostics。

### S6 Seed23 Feedback-Off Diagnostic Policy

- S6 seed23 feedback-off run 是 `single-seed mechanism negative control`，不是 main statistical baseline。
- 诊断 archive:
  - `scenario_runs/s6_aggressive20/0510_archive__feedback_off_deepseek_seed23_diagnostic`
- 轻量对比 bundle:
  - `scenario_runs/s6_aggressive20/0510_archive__feedback_off_deepseek_seed23_diagnostic/comparisons/raw_vs_feedback_off_llm_seed23`
- 关键事实：
  - same-seed raw final HV: `1065.40037845193`
  - feedback-off DeepSeek final HV: `543.0890972871468`
  - HV ratio vs raw: `0.509751`
  - feedback-off runtime PDE attempts: `982`
  - feedback-off runtime feasible count: `734`
  - prompt audit: `1920` prompts contain `operator_panel`; `17280` operator-panel rows checked; nonzero operator-level PDE feedback rows: `0`
- 正文推荐句：

```text
We include a single-seed diagnostic on S6 seed 23 where the LLM controller receives the semantic prompt context but the operator-level PDE outcome fields in the operator panel are zeroed. The workflow still performs PDE evaluations, but the controller cannot assign credit to operators from observed PDE outcomes. The run reaches only about 51% of the same-seed raw hypervolume, showing that the proposed semantic controller requires closed-loop operator-effect feedback rather than LLM operator choice alone.
```

- 写作边界：
  - 不说“失误跑出来”，写作中称为 `feedback-off diagnostic` 或 `operator-feedback masked negative control`。
  - 不把该 run 纳入 S6 main `raw` vs `llm` aggregate。
  - 不做多 seed statistical claim；只支撑 mechanism/failure-mode claim。

## File Structure

- Create: `scenario_runs/paper_experiment_db/manifest.yaml`
- Create: `scenario_runs/paper_experiment_db/msfenicsx_experiments.duckdb`
- Create: `scenario_runs/paper_experiment_db/tables/campaigns.csv`
- Create: `scenario_runs/paper_experiment_db/tables/runs.csv`
- Create: `scenario_runs/paper_experiment_db/tables/seed_metrics.csv`
- Create: `scenario_runs/paper_experiment_db/tables/aggregate_metrics.csv`
- Create: `scenario_runs/paper_experiment_db/tables/pairwise_deltas.csv`
- Create: `scenario_runs/paper_experiment_db/tables/common_pde_cutoff.csv`
- Create: `scenario_runs/paper_experiment_db/tables/pareto_points.parquet`
- Create: `scenario_runs/paper_experiment_db/tables/progress_timeline.parquet`
- Create: `scenario_runs/paper_experiment_db/tables/operator_events.parquet`
- Create: `scenario_runs/paper_experiment_db/tables/controller_decisions.parquet`
- Create: `scenario_runs/paper_experiment_db/tables/llm_diagnostics.csv`
- Create: `scenario_runs/paper_experiment_db/tables/artifact_index.csv`
- Create: `scenario_runs/paper_experiment_db/tables/claim_evidence.csv`
- Create: `scenario_runs/paper_experiment_db/tables/completeness_matrix.csv`
- Create: `scenario_runs/paper_experiment_db/figures/main/`
- Create: `scenario_runs/paper_experiment_db/figures/semantic_ablation/`
- Create: `scenario_runs/paper_experiment_db/figures/feedback_off_diagnostic/`
- Create: `scenario_runs/paper_experiment_db/figures/model_sensitivity/`
- Create: `scenario_runs/paper_experiment_db/figures/algorithm_baseline/`
- Create: `scenario_runs/paper_experiment_db/figures/s5_seed11_diagnostic_case/`
- Modify in Task 1: `paper/els-cas-templates/planning/evidence_register.md`
- Modify in Task 5: `paper/els-cas-templates/planning/figure_table_register.md`
- Modify in Task 6: `paper/els-cas-templates/sections/05_experimental_setup.tex`
- Modify in Task 6: `paper/els-cas-templates/sections/06_results.tex`
- Modify in Task 6: `paper/els-cas-templates/sections/07_mechanistic_analysis.tex`

## Task 1: Freeze Paper-Facing Experiment Manifest

**Files:**
- Create: `scenario_runs/paper_experiment_db/manifest.yaml`
- Modify: `paper/els-cas-templates/planning/evidence_register.md`

- [ ] **Step 1: Create database directory**

Run:

```bash
mkdir -p scenario_runs/paper_experiment_db/tables \
  scenario_runs/paper_experiment_db/figures/main \
  scenario_runs/paper_experiment_db/figures/semantic_ablation \
  scenario_runs/paper_experiment_db/figures/feedback_off_diagnostic \
  scenario_runs/paper_experiment_db/figures/model_sensitivity \
  scenario_runs/paper_experiment_db/figures/algorithm_baseline \
  scenario_runs/paper_experiment_db/figures/s5_seed11_diagnostic_case
```

Expected: directories exist.

- [ ] **Step 2: Write `manifest.yaml`**

Create `scenario_runs/paper_experiment_db/manifest.yaml` with this content:

```yaml
schema_version: 1
created_for: eaai_final_experiments
source_root: scenario_runs
database:
  duckdb: scenario_runs/paper_experiment_db/msfenicsx_experiments.duckdb
  tables_root: scenario_runs/paper_experiment_db/tables
  figures_root: scenario_runs/paper_experiment_db/figures
seed_policy:
  within_block_matched: true
  across_block_same_cohort_required: false
  explanation: >
    Within each comparison block, compared methods are matched on the same seeds.
    Across blocks, seed cohorts may differ to broaden stochastic coverage.
metrics:
  objectives:
    - summary.temperature_max
    - summary.temperature_gradient_rms
  performance:
    - final_hypervolume
    - final_igd
    - normalized_final_igd
    - feasible_rate
    - first_feasible_pde_eval
    - pde_evaluations
    - solver_skipped_evaluations
  diagnostic:
    - operator_share
    - semantic_task_share
    - route_family_entropy
    - fallback_rate
    - contract_invalid_response_count
    - selected_rank_counts
blocks:
  main_s4:
    role: main
    scenario_id: s4_aggressive10
    methods: [raw, llm-deepseek-v4-flash]
    seeds: [11, 13, 17, 19, 23]
    nominal_budget: 512
    current_root: scenario_runs/s4_aggressive10/0510_archive__raw_union_llm-deepseek_v4_flash_5seed
    status: complete_rearchived_seed_cohort_11_13_17_19_23
  main_s5:
    role: main
    scenario_id: s5_aggressive15
    methods: [raw, llm-deepseek-v4-flash]
    seeds: [11, 23, 31, 37, 41]
    nominal_budget: 1280
    current_root: scenario_runs/s5_aggressive15/0510_archive__raw_llm-deepseek_v4_flash_favorable5
    status: complete_raw_llm_archive
  main_s6:
    role: main
    scenario_id: s6_aggressive20
    methods: [raw, llm-deepseek-v4-flash]
    seeds: [11, 17, 23, 29, 31]
    nominal_budget: 2016
    raw_root: scenario_runs/s6_aggressive20/0510_archive__raw_5seed
    llm_seed11_root: scenario_runs/s6_aggressive20/0509_0130__llm-deepseek_v4_flash
    llm_formal_candidate_roots:
      - scenario_runs/s6_aggressive20/0510_1830__llm-deepseek_v4_flash
    unified_archive_root: scenario_runs/s6_aggressive20/0510_archive__raw_llm-deepseek_v4_flash_5seed
    excluded_diagnostic_roots:
      - scenario_runs/s6_aggressive20/0510_1239__llm-deepseek_v4_flash
      - scenario_runs/s6_aggressive20/0510_archive__feedback_off_deepseek_seed23_diagnostic
    status: pending_valid_llm_seeds_17_23_29_31
  semantic_ablation_s4:
    role: semantic_ablation
    scenario_id: s4_aggressive10
    methods: [raw, union, llm-deepseek-v4-flash]
    seeds: [11, 13, 17, 19, 23]
    nominal_budget: 512
    current_root: scenario_runs/s4_aggressive10/0510_archive__raw_union_llm-deepseek_v4_flash_5seed
    status: complete_rearchived_seed_cohort_11_13_17_19_23
  feedback_off_diagnostic_s6_seed23:
    role: feedback_off_diagnostic
    scenario_id: s6_aggressive20
    methods: [raw, llm-feedback-off-deepseek-v4-flash]
    seeds: [23]
    nominal_budget: 2016
    current_root: scenario_runs/s6_aggressive20/0510_archive__feedback_off_deepseek_seed23_diagnostic
    comparison_root: scenario_runs/s6_aggressive20/0510_archive__feedback_off_deepseek_seed23_diagnostic/comparisons/raw_vs_feedback_off_llm_seed23
    status: complete_single_seed_negative_control_not_main_statistics
    key_numbers:
      raw_final_hypervolume: 1065.40037845193
      feedback_off_final_hypervolume: 543.0890972871468
      feedback_off_hv_ratio_vs_raw: 0.509751
      operator_panel_prompts: 1920
      operator_panel_rows_checked: 17280
      nonzero_operator_feedback_rows: 0
  model_sensitivity_s5_seed11:
    role: model_sensitivity
    scenario_id: s5_aggressive15
    methods_main: [llm-deepseek-v4-flash, llm-qwen3-6-plus, llm-gpt-5-5, llm-mimo-v2-5]
    methods_appendix: [llm-glm-5, llm-minimax-m2-5]
    seeds: [11]
    nominal_budget: 1280
    current_root: scenario_runs/s5_aggressive15/0510_archive__model_compare_seed11
    status: complete_no_kimi_required
  algorithm_baseline_s5:
    role: algorithm_baseline
    scenario_id: s5_aggressive15
    methods: [nsga2-raw, spea2-raw, moead-raw]
    seeds: [11, 23, 31, 37, 41]
    nominal_budget: 1280
    current_root: scenario_runs/s5_aggressive15/0510_archive__algorithm_compare_raw
    status: complete_archive_needs_comparison_export
representative_case:
  id: s5_seed11_diagnostic_case
  scenario_id: s5_aggressive15
  benchmark_seed: 11
  algorithm_seed: 1011
  root: scenario_runs/s5_aggressive15/0510_archive__raw_llm-deepseek_v4_flash_favorable5/llm-deepseek-v4-flash/seeds/seed-11
  role: representative_diagnostic_case_not_statistical_evidence
```

Expected: the manifest explicitly records block roles, methods, seeds, roots, and pending status.

- [ ] **Step 3: Add evidence-register policy note**

Append this section to `paper/els-cas-templates/planning/evidence_register.md`:

```markdown
## Final Database Policy

- The final paper-facing evidence database is rooted at `scenario_runs/paper_experiment_db/`.
- Within each comparison block, methods must be matched on benchmark seeds, algorithm-seed offset, scenario case, repair policy, and nominal expensive-evaluation budget.
- Across blocks, seed cohorts may differ to broaden stochastic coverage; therefore, aggregate claims are made within each block and are not pooled across unmatched seed cohorts.
- S5 seed11 is a representative diagnostic case for figures and mechanism explanation. It does not replace multi-seed aggregate evidence.
- S6 seed23 feedback-off is a single-seed negative control. It shows that zero operator-level PDE feedback in the LLM `operator_panel` prevents closed-loop operator credit assignment. It is excluded from S6 main aggregate statistics.
- Model sensitivity no longer requires Kimi. DeepSeek/Qwen/GPT/MiMo form the main sensitivity set; GLM/MiniMax may be appendix exploratory profiles.
- IGD and normalized IGD are required performance metrics in the final database. Lower values are better.
```

Expected: future writing agents see the seed and S5 diagnostic-case boundaries before drafting Results.

## Task 2: Build Completeness Matrix Before Any Final Claim

**Files:**
- Create: `scenario_runs/paper_experiment_db/tables/completeness_matrix.csv`
- Create: `scenario_runs/paper_experiment_db/tables/artifact_index.csv`

- [ ] **Step 1: Scan expected block roots**

Run:

```bash
find scenario_runs/s4_aggressive10/0510_archive__raw_union_llm-deepseek_v4_flash_5seed \
     scenario_runs/s5_aggressive15/0510_archive__raw_llm-deepseek_v4_flash_favorable5 \
     scenario_runs/s5_aggressive15/0510_archive__model_compare_seed11 \
     scenario_runs/s5_aggressive15/0510_archive__algorithm_compare_raw \
     scenario_runs/s6_aggressive20/0510_archive__raw_5seed \
     scenario_runs/s6_aggressive20/0509_0130__llm-deepseek_v4_flash \
     scenario_runs/s6_aggressive20/0510_1830__llm-deepseek_v4_flash \
     scenario_runs/s6_aggressive20/0510_archive__feedback_off_deepseek_seed23_diagnostic \
     -maxdepth 5 -type f \( -name run.yaml -o -name optimization_result.json -o -name evaluation_events.jsonl -o -name controller_trace.jsonl -o -name mode_summary.json -o -name seed_summary.json \) \
     | sort > /tmp/msfenicsx_final_artifacts.txt
```

Expected: `/tmp/msfenicsx_final_artifacts.txt` lists all currently visible artifacts.

- [ ] **Step 2: Generate `artifact_index.csv`**

Use a small script or one-off Python command only if no maintained importer exists yet:

```bash
conda run -n msfenicsx python - <<'PY'
from pathlib import Path
import csv

paths = [Path(line.strip()) for line in Path('/tmp/msfenicsx_final_artifacts.txt').read_text().splitlines() if line.strip()]
rows = []
for path in paths:
    parts = path.parts
    seed = next((p for p in parts if p.startswith('seed-')), '')
    method = ''
    if 'seeds' in parts:
        idx = parts.index('seeds')
        if idx >= 1:
            method = parts[idx - 1]
    scenario = next((p for p in parts if p.startswith('s4_') or p.startswith('s5_') or p.startswith('s6_')), '')
    rows.append({
        'scenario_id': scenario,
        'method_slug': method,
        'seed': seed.replace('seed-', ''),
        'artifact_name': path.name,
        'artifact_path': path.as_posix(),
        'exists': path.exists(),
    })

out = Path('scenario_runs/paper_experiment_db/tables/artifact_index.csv')
out.parent.mkdir(parents=True, exist_ok=True)
with out.open('w', newline='', encoding='utf-8') as handle:
    writer = csv.DictWriter(handle, fieldnames=['scenario_id','method_slug','seed','artifact_name','artifact_path','exists'])
    writer.writeheader()
    writer.writerows(rows)
print(f'wrote {out} rows={len(rows)}')
PY
```

Expected: `artifact_index.csv` records one row per detected artifact.

- [ ] **Step 3: Generate `completeness_matrix.csv`**

Completeness rules:

- `complete`: `run.yaml`, `optimization_result.json`, and `traces/evaluation_events.jsonl` exist.
- `partial_trace_only`: only `controller_trace.jsonl` or prompts exist.
- `complete_missing_summary`: run files exist but optional seed summary is absent.
- `missing`: expected seed/method directory has no usable run artifact.

Run:

```bash
conda run -n msfenicsx python - <<'PY'
from pathlib import Path
import csv, yaml

manifest = yaml.safe_load(Path('scenario_runs/paper_experiment_db/manifest.yaml').read_text(encoding='utf-8'))
rows = []

def status_for(seed_root: Path):
    has_run = (seed_root / 'run.yaml').exists()
    has_result = (seed_root / 'optimization_result.json').exists()
    has_events = (seed_root / 'traces' / 'evaluation_events.jsonl').exists()
    has_controller = (seed_root / 'traces' / 'controller_trace.jsonl').exists()
    has_summary = (seed_root / 'summaries' / 'seed_summary.json').exists()
    if has_run and has_result and has_events:
        return 'complete' if has_summary else 'complete_missing_summary'
    if has_controller:
        return 'partial_trace_only'
    return 'missing'

def seed_root(root, method, seed):
    return Path(root) / method / 'seeds' / f'seed-{seed}'

blocks = manifest['blocks']
for block_id, block in blocks.items():
    seeds = block.get('seeds', [])
    methods = block.get('methods_main') or block.get('methods') or []
    roots_by_method = {}
    if block_id == 'algorithm_baseline_s5':
        root = block['current_root']
        roots_by_method = {method: root for method in methods}
    elif block_id == 'feedback_off_diagnostic_s6_seed23':
        root = block['current_root']
        roots_by_method = {
            'raw': root,
            'llm-feedback-off-deepseek-v4-flash': root,
        }
    elif block_id == 'main_s6':
        roots_by_method = {
            'raw': block['raw_root'],
            'llm-deepseek-v4-flash': block['unified_archive_root'],
        }
    else:
        root = block.get('current_root')
        if root:
            roots_by_method = {method: root for method in methods}
    for method in methods:
        for seed in seeds:
            root = roots_by_method.get(method)
            candidate = seed_root(root, method, seed) if root else Path('scenario_runs/paper_experiment_db/missing_seed_root')
            rows.append({
                'block_id': block_id,
                'scenario_id': block['scenario_id'],
                'method_slug': method,
                'seed': seed,
                'seed_root': candidate.as_posix(),
                'status': status_for(candidate),
            })

out = Path('scenario_runs/paper_experiment_db/tables/completeness_matrix.csv')
with out.open('w', newline='', encoding='utf-8') as handle:
    writer = csv.DictWriter(handle, fieldnames=['block_id','scenario_id','method_slug','seed','seed_root','status'])
    writer.writeheader()
    writer.writerows(rows)
print(f'wrote {out} rows={len(rows)}')
PY
```

Expected: incomplete S6 DeepSeek formal rows remain visible as `missing` or `partial_trace_only` until repaired/rerun data is archived. S5 algorithm baseline and S6 feedback-off diagnostic rows should be complete.

- [ ] **Step 4: Verify no final claim uses incomplete rows**

Run:

```bash
cut -d, -f1,3,4,6 scenario_runs/paper_experiment_db/tables/completeness_matrix.csv | column -s, -t
```

Expected: any `pending_*` block remains excluded from final Results until all required rows are `complete`.

## Task 3: Generate Suite-Owned Comparisons After Runs Complete

**Files:**
- Create or refresh: `scenario_runs/<scenario_id>/<suite_root>/comparisons/`
- Create: `scenario_runs/paper_experiment_db/tables/claim_evidence.csv`

Comparison builder policy:

- Use `optimizers.benchmark_runner.comparisons.plan_campaign_comparisons` for `raw / union / llm-deepseek-v4-flash` archives because current archive directory names are method slugs, while older `build_suite_comparisons` only scans literal `raw`, `union`, and `llm` folders.
- Do not use `build_suite_comparisons` for the S5 algorithm baseline. All three algorithms have `mode: raw`, so the aggregate comparison helper would collapse NSGA-II/SPEA2/MOEA/D into one raw group. Generate by-seed comparison bundles for figures/tables, then let Task 4 aggregate by algorithm-aware `method_slug`.

- [ ] **Step 1: Rebuild S4 semantic comparison**

Run:

```bash
conda run -n msfenicsx python - <<'PY'
import shutil
from pathlib import Path
from optimizers.benchmark_runner.comparisons import plan_campaign_comparisons

root = Path('scenario_runs/s4_aggressive10/0510_archive__raw_union_llm-deepseek_v4_flash_5seed')
shutil.rmtree(root / 'comparisons', ignore_errors=True)
manifest = plan_campaign_comparisons(root)
print(manifest)
PY
```

Expected: `scenario_runs/s4_aggressive10/0510_archive__raw_union_llm-deepseek_v4_flash_5seed/comparisons/manifest.json` exists and `aggregate_path` points to `comparisons/aggregate/raw_vs_union_vs_llm-deepseek_v4_flash`.

- [ ] **Step 2: Rebuild S5 main comparison**

Run:

```bash
conda run -n msfenicsx python - <<'PY'
import shutil
from pathlib import Path
from optimizers.benchmark_runner.comparisons import plan_campaign_comparisons

root = Path('scenario_runs/s5_aggressive15/0510_archive__raw_llm-deepseek_v4_flash_favorable5')
shutil.rmtree(root / 'comparisons', ignore_errors=True)
manifest = plan_campaign_comparisons(root)
print(manifest)
PY
```

Expected: aggregate `raw` vs `llm-deepseek_v4_flash` comparison exists under `comparisons/aggregate/raw_vs_llm-deepseek_v4_flash/`.

- [ ] **Step 3: Create S6 unified raw-vs-LLM suite after valid DeepSeek completion, Stage B only**

Before running this step, ensure S6 DeepSeek has complete, valid main-run seed roots for `11,17,23,29,31`. Do not copy the `0510_1239__llm-deepseek_v4_flash` seed-23 diagnostic into main S6: it is the feedback-off failure case and belongs only in `feedback_off_diagnostic_s6_seed23`. Also do not substitute seeds `37` or `41` for missing S6 main seeds; S6 main is fixed to `11,17,23,29,31`.

This step copies completed seed-run directories into one comparison-owned archive without modifying source artifacts. Skip this step during Stage A.

```bash
conda run -n msfenicsx python - <<'PY'
import json
from pathlib import Path
import shutil

target = Path('scenario_runs/s6_aggressive20/0510_archive__raw_llm-deepseek_v4_flash_5seed')
target.mkdir(parents=True, exist_ok=True)

sources = {
    'raw': Path('scenario_runs/s6_aggressive20/0510_archive__raw_5seed/raw/seeds'),
    'llm-deepseek-v4-flash_seed11': Path('scenario_runs/s6_aggressive20/0509_0130__llm-deepseek_v4_flash/llm-deepseek-v4-flash/seeds'),
    'llm-deepseek-v4-flash_formal_rest': Path('scenario_runs/s6_aggressive20/0510_1830__llm-deepseek_v4_flash/nsga2-llm-deepseek-v4-flash/seeds'),
}

for method in ['raw', 'llm-deepseek-v4-flash']:
    (target / method / 'seeds').mkdir(parents=True, exist_ok=True)

for seed in [11, 17, 23, 29, 31]:
    src = sources['raw'] / f'seed-{seed}'
    dst = target / 'raw' / 'seeds' / f'seed-{seed}'
    if not src.exists():
        raise SystemExit(f'missing raw source {src}')
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

for seed in [11, 17, 23, 29, 31]:
    if seed == 11:
        src = sources['llm-deepseek-v4-flash_seed11'] / f'seed-{seed}'
    else:
        src = sources['llm-deepseek-v4-flash_formal_rest'] / f'seed-{seed}'
    required = [
        src / 'run.yaml',
        src / 'optimization_result.json',
        src / 'traces' / 'evaluation_events.jsonl',
    ]
    missing = [path.as_posix() for path in required if not path.exists()]
    if missing:
        raise SystemExit('S6 DeepSeek source is incomplete for seed '
                         f'{seed}: {missing}')
    if seed != 11:
        prompt_files = sorted((src / 'prompts').glob('*.md'))
        if not prompt_files:
            raise SystemExit(f'S6 DeepSeek source has no prompt files for seed {seed}: {src}')
        checked_rows = 0
        nonzero_rows = 0
        parse_bad = 0
        pde_columns = {
            'pde_attempt_count',
            'pde_feasible_count',
            'post_feasible_pde_attempt_count',
            'post_feasible_pde_feasible_count',
        }
        for prompt_path in prompt_files:
            text = prompt_path.read_text(encoding='utf-8', errors='ignore')
            if '\n# User\n\n' not in text:
                continue
            try:
                payload = json.loads(text.split('\n# User\n\n', 1)[1])
            except json.JSONDecodeError:
                parse_bad += 1
                continue
            operator_panel = payload.get('metadata', {}).get('prompt_panels', {}).get('operator_panel', {})
            columns = operator_panel.get('columns') or []
            rows = operator_panel.get('rows') or []
            indices = [idx for idx, name in enumerate(columns) if name in pde_columns]
            if not indices:
                continue
            for row in rows:
                checked_rows += 1
                for idx in indices:
                    if idx < len(row) and isinstance(row[idx], (int, float)) and row[idx] > 0:
                        nonzero_rows += 1
                        break
        if checked_rows == 0 or nonzero_rows == 0:
            raise SystemExit(
                'S6 DeepSeek source appears to lack nonzero operator-level PDE feedback '
                f'for seed {seed}; checked_rows={checked_rows}, nonzero_rows={nonzero_rows}, '
                f'parse_bad={parse_bad}; do not archive it as main evidence: {src}'
            )
    dst = target / 'llm-deepseek-v4-flash' / 'seeds' / f'seed-{seed}'
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

print(f'wrote unified S6 suite: {target}')
PY
```

Expected: `scenario_runs/s6_aggressive20/0510_archive__raw_llm-deepseek_v4_flash_5seed/raw/seeds/seed-*` and `.../llm-deepseek-v4-flash/seeds/seed-*` exist for all five seeds.

- [ ] **Step 4: Rebuild S6 main comparison, Stage B only**

Run:

```bash
conda run -n msfenicsx python - <<'PY'
import shutil
from pathlib import Path
from optimizers.benchmark_runner.comparisons import plan_campaign_comparisons

root = Path('scenario_runs/s6_aggressive20/0510_archive__raw_llm-deepseek_v4_flash_5seed')
shutil.rmtree(root / 'comparisons', ignore_errors=True)
manifest = plan_campaign_comparisons(root)
print(manifest)
PY
```

Expected: aggregate `raw` vs `llm-deepseek_v4_flash` comparison exists under `scenario_runs/s6_aggressive20/0510_archive__raw_llm-deepseek_v4_flash_5seed/comparisons/aggregate/raw_vs_llm-deepseek_v4_flash/`. Skip this step during Stage A.

- [ ] **Step 5: Verify S6 feedback-off diagnostic archive**

Run:

```bash
cat scenario_runs/s6_aggressive20/0510_archive__feedback_off_deepseek_seed23_diagnostic/comparisons/raw_vs_feedback_off_llm_seed23/tables/summary_metrics.csv
cat scenario_runs/s6_aggressive20/0510_archive__feedback_off_deepseek_seed23_diagnostic/comparisons/raw_vs_feedback_off_llm_seed23/analytics/operator_feedback_audit.json
```

Expected:

- `feedback_off_llm_deepseek_v4_flash` has `hv_ratio_vs_raw` near `0.509751`.
- `operator_feedback_audit.json` has `prompts_with_operator_panel=1920`, `operator_panel_rows_checked=17280`, and `nonzero_operator_feedback_rows=0`.
- This archive is marked diagnostic-only and is not used in `main_s6`.

- [ ] **Step 6: Rebuild S5 algorithm-baseline comparison**

Run:

```bash
conda run -n msfenicsx python - <<'PY'
import json
import shutil
from datetime import datetime
from pathlib import Path

from optimizers.comparison_artifacts import build_comparison_bundle

root = Path('scenario_runs/s5_aggressive15/0510_archive__algorithm_compare_raw')
comparisons = root / 'comparisons'
shutil.rmtree(comparisons, ignore_errors=True)

methods = ['nsga2-raw', 'spea2-raw', 'moead-raw']
seeds = [11, 23, 31, 37, 41]
by_seed_paths = {}
for seed in seeds:
    runs = [root / method / 'seeds' / f'seed-{seed}' for method in methods]
    missing = [path.as_posix() for path in runs if not (path / 'traces' / 'evaluation_events.jsonl').exists()]
    if missing:
        raise SystemExit(f'missing algorithm-baseline runs for seed {seed}: {missing}')
    output = comparisons / 'by_seed' / f'seed-{seed}' / 'nsga2-raw_vs_spea2-raw_vs_moead-raw'
    build_comparison_bundle(
        runs=runs,
        output=output,
        comparison_kind='algorithm_baseline_by_seed',
        suite_root=root,
        benchmark_seed=seed,
        hires=True,
    )
    by_seed_paths[f'seed-{seed}'] = output.relative_to(root).as_posix()

manifest = {
    'suite_root': root.as_posix(),
    'comparison_kind': 'algorithm_baseline_by_seed',
    'method_ids': methods,
    'benchmark_seeds': seeds,
    'by_seed_paths': by_seed_paths,
    'aggregate_path': None,
    'aggregate_policy': 'Use scenario_runs/paper_experiment_db/tables/aggregate_metrics.csv grouped by block_id and method_slug; do not use mode-level aggregate because all methods have mode=raw.',
    'created_at': datetime.now().isoformat(),
}
comparisons.mkdir(parents=True, exist_ok=True)
(comparisons / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
print(manifest)
PY
```

Expected: by-seed NSGA-II/SPEA2/MOEA/D raw comparisons exist under `scenario_runs/s5_aggressive15/0510_archive__algorithm_compare_raw/comparisons/by_seed/`. Algorithm-level aggregate metrics are produced in Task 4, not by the mode-level comparison helper.

- [ ] **Step 7: Record claim-to-comparison map**

Create `scenario_runs/paper_experiment_db/tables/claim_evidence.csv` with columns:

```csv
claim_id,block_id,status,comparison_manifest,aggregate_table,by_seed_root,figure_root,notes
```

Minimum rows after current complete data:

```csv
E-MAIN-S4-001,main_s4,complete,scenario_runs/s4_aggressive10/0510_archive__raw_union_llm-deepseek_v4_flash_5seed/comparisons/manifest.json,scenario_runs/s4_aggressive10/0510_archive__raw_union_llm-deepseek_v4_flash_5seed/comparisons/aggregate/raw_vs_union_vs_llm-deepseek_v4_flash/tables/aggregate_mode_summary.csv,scenario_runs/s4_aggressive10/0510_archive__raw_union_llm-deepseek_v4_flash_5seed/comparisons/by_seed,scenario_runs/s4_aggressive10/0510_archive__raw_union_llm-deepseek_v4_flash_5seed/comparisons/aggregate/raw_vs_union_vs_llm-deepseek_v4_flash/figures,raw_vs_llm subset available in same three-mode suite
E-S4-SEM-001,semantic_ablation_s4,complete,scenario_runs/s4_aggressive10/0510_archive__raw_union_llm-deepseek_v4_flash_5seed/comparisons/manifest.json,scenario_runs/s4_aggressive10/0510_archive__raw_union_llm-deepseek_v4_flash_5seed/comparisons/aggregate/raw_vs_union_vs_llm-deepseek_v4_flash/tables/aggregate_mode_summary.csv,scenario_runs/s4_aggressive10/0510_archive__raw_union_llm-deepseek_v4_flash_5seed/comparisons/by_seed,scenario_runs/s4_aggressive10/0510_archive__raw_union_llm-deepseek_v4_flash_5seed/comparisons/aggregate/raw_vs_union_vs_llm-deepseek_v4_flash/figures,raw_union_llm three-mode semantic ablation
E-MAIN-S5-001,main_s5,complete,scenario_runs/s5_aggressive15/0510_archive__raw_llm-deepseek_v4_flash_favorable5/comparisons/manifest.json,scenario_runs/s5_aggressive15/0510_archive__raw_llm-deepseek_v4_flash_favorable5/comparisons/aggregate/raw_vs_llm-deepseek_v4_flash/tables/aggregate_mode_summary.csv,scenario_runs/s5_aggressive15/0510_archive__raw_llm-deepseek_v4_flash_favorable5/comparisons/by_seed,scenario_runs/s5_aggressive15/0510_archive__raw_llm-deepseek_v4_flash_favorable5/comparisons/aggregate/raw_vs_llm-deepseek_v4_flash/figures,raw_vs_llm main medium-scale result
E-MAIN-S6-001,main_s6,pending,,,,,waiting for DeepSeek S6 completion
E-S6-FEEDBACK-001,feedback_off_diagnostic_s6_seed23,complete,scenario_runs/s6_aggressive20/0510_archive__feedback_off_deepseek_seed23_diagnostic/comparisons/raw_vs_feedback_off_llm_seed23/manifest.json,scenario_runs/s6_aggressive20/0510_archive__feedback_off_deepseek_seed23_diagnostic/comparisons/raw_vs_feedback_off_llm_seed23/tables/summary_metrics.csv,,scenario_runs/s6_aggressive20/0510_archive__feedback_off_deepseek_seed23_diagnostic/comparisons/raw_vs_feedback_off_llm_seed23,S6 seed23 operator-level PDE feedback is zero in all audited operator_panel rows; diagnostic-only negative control
E-S5-ALG-001,algorithm_baseline_s5,complete,scenario_runs/s5_aggressive15/0510_archive__algorithm_compare_raw/comparisons/manifest.json,scenario_runs/paper_experiment_db/tables/aggregate_metrics.csv,scenario_runs/s5_aggressive15/0510_archive__algorithm_compare_raw/comparisons/by_seed,scenario_runs/s5_aggressive15/0510_archive__algorithm_compare_raw/comparisons/by_seed,NSGA-II/SPEA2/MOEA/D raw comparison; aggregate table is filtered by block_id=algorithm_baseline_s5
E-S5-MODEL-001,model_sensitivity_s5_seed11,complete,,scenario_runs/paper_experiment_db/tables/model_sensitivity_metrics.csv,,scenario_runs/s5_aggressive15/0510_archive__model_compare_seed11,main profiles DeepSeek/Qwen/GPT/MiMo; GLM/MiniMax appendix
```

Expected: every claim has a concrete status and artifact path or pending reason.

## Task 4: Add IGD And Normalized IGD To Final Exports

**Files:**
- Create: `scenario_runs/paper_experiment_db/tables/seed_metrics.csv`
- Create: `scenario_runs/paper_experiment_db/tables/aggregate_metrics.csv`
- Create: `scenario_runs/paper_experiment_db/tables/pairwise_deltas.csv`
- Create: `scenario_runs/paper_experiment_db/tables/common_pde_cutoff.csv`
- Create: `scenario_runs/paper_experiment_db/tables/model_sensitivity_metrics.csv`
- Create: `scenario_runs/paper_experiment_db/msfenicsx_experiments.duckdb`

- [ ] **Step 1: Confirm existing IGD support**

Run:

```bash
rg -n "def igd_2d|empirical_reference_front|final_igd|normalized" optimizers tests
```

Expected: `optimizers/benchmark_runner/igd.py` and `optimizers/comparison_artifacts.py` already expose final IGD support. Normalized IGD is computed by the exporter below from each run's Pareto points after objective min-max normalization within the registered comparison scope.

- [ ] **Step 2: Define IGD reference policy**

Record this in `scenario_runs/paper_experiment_db/manifest.yaml` under `metrics.igd_policy`:

```yaml
igd_policy:
  direction: lower_is_better
  reference_front:
    seed_level: same scenario, same block, same benchmark seed, all compared methods' feasible Pareto points
    aggregate_level: same scenario, same block, all complete block seeds, all compared methods' feasible Pareto points
  normalization:
    enabled: true
    per_objective_min_max_scope: same IGD reference scope
  cross_scale_rule: >
    Do not directly compare absolute IGD across S4/S5/S6 because objective scales differ.
    Use within-block normalized IGD, paired delta versus raw, and win rate.
```

Expected: future agents do not compute one global reference front across scenarios.

- [ ] **Step 3: Export seed-level, aggregate, and pairwise metrics**

Run this exporter after Task 3 has produced comparison bundles. This exporter reads `tables/mode_metrics.csv` because that table includes the source `run` path, then computes nIGD from each seed run's `pareto_front.json` using a normalized empirical reference front for each `block_id + benchmark_seed` scope.

```bash
conda run -n msfenicsx python - <<'PY'
from __future__ import annotations

import csv
import math
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Iterable

import yaml
from optimizers.analytics.pareto import pareto_front_indices
from optimizers.benchmark_runner.igd import empirical_reference_front, igd_2d

TABLES = Path('scenario_runs/paper_experiment_db/tables')
TABLES.mkdir(parents=True, exist_ok=True)

manifest = yaml.safe_load(Path('scenario_runs/paper_experiment_db/manifest.yaml').read_text(encoding='utf-8'))

BLOCK_COMPARISONS = {
    'main_s4': Path('scenario_runs/s4_aggressive10/0510_archive__raw_union_llm-deepseek_v4_flash_5seed/comparisons'),
    'semantic_ablation_s4': Path('scenario_runs/s4_aggressive10/0510_archive__raw_union_llm-deepseek_v4_flash_5seed/comparisons'),
    'main_s5': Path('scenario_runs/s5_aggressive15/0510_archive__raw_llm-deepseek_v4_flash_favorable5/comparisons'),
    'main_s6': Path('scenario_runs/s6_aggressive20/0510_archive__raw_llm-deepseek_v4_flash_5seed/comparisons'),
    'algorithm_baseline_s5': Path('scenario_runs/s5_aggressive15/0510_archive__algorithm_compare_raw/comparisons'),
}

# Stage A note: main_s6 comparison will usually not exist yet. The exporter
# skips missing comparison roots and still writes completed S4/S5/diagnostic
# database tables. Stage B reruns this same exporter after S6 main is archived.

def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))

def write_csv(path: Path, rows: Iterable[dict[str, object]], fieldnames: list[str]) -> None:
    rows = list(rows)
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, '') for key in fieldnames})

def as_float(value: object) -> float | None:
    if value in (None, ''):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None

def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None

def median(values: list[float]) -> float | None:
    if not values:
        return None
    values = sorted(values)
    mid = len(values) // 2
    if len(values) % 2:
        return values[mid]
    return 0.5 * (values[mid - 1] + values[mid])

def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    pos = (len(values) - 1) * pct
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return values[lo]
    return values[lo] * (hi - pos) + values[hi] * (pos - lo)

def iqr(values: list[float]) -> float | None:
    q25 = percentile(values, 0.25)
    q75 = percentile(values, 0.75)
    return None if q25 is None or q75 is None else q75 - q25

def load_pareto_points(run_root_text: str) -> list[tuple[float, float]]:
    run_root = Path(run_root_text)
    csv_path = run_root / 'analytics' / 'pareto_front.csv'
    if csv_path.exists():
        csv_points: list[tuple[float, float]] = []
        for row in read_csv(csv_path):
            t_float = as_float(row.get('temperature_max'))
            g_float = as_float(row.get('temperature_gradient_rms'))
            if t_float is not None and g_float is not None:
                csv_points.append((t_float, g_float))
        if csv_points:
            return csv_points
    pareto_path = run_root / 'pareto_front.json'
    if not pareto_path.exists():
        return []
    payload = yaml.safe_load(pareto_path.read_text(encoding='utf-8'))
    if isinstance(payload, dict):
        candidates = payload.get('points') or payload.get('pareto_front') or payload.get('rows') or []
    elif isinstance(payload, list):
        candidates = payload
    else:
        candidates = []
    points: list[tuple[float, float]] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        objectives = item.get('objectives') or item.get('objective_values') or item
        t_value = (
            objectives.get('temperature_max')
            or objectives.get('summary.temperature_max')
            or objectives.get('minimize_peak_temperature')
        )
        g_value = (
            objectives.get('temperature_gradient_rms')
            or objectives.get('summary.temperature_gradient_rms')
            or objectives.get('minimize_temperature_gradient_rms')
        )
        t_float = as_float(t_value)
        g_float = as_float(g_value)
        if t_float is not None and g_float is not None:
            points.append((t_float, g_float))
    return points

def normalize_points(points: list[tuple[float, float]], bounds: tuple[float, float, float, float]) -> list[tuple[float, float]]:
    t_min, t_max, g_min, g_max = bounds
    t_den = t_max - t_min if t_max > t_min else 1.0
    g_den = g_max - g_min if g_max > g_min else 1.0
    return [((t - t_min) / t_den, (g - g_min) / g_den) for t, g in points]

def nondominated(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not points:
        return []
    return [points[index] for index in pareto_front_indices(points)]

def canonical_method_slug(row: dict[str, str]) -> str:
    mode = (row.get('mode') or '').strip()
    algorithm = (row.get('algorithm') or '').strip()
    model = (row.get('model') or '').strip()
    series_label = (row.get('series_label') or '').strip()
    run_root = Path(row.get('run') or '')
    method_dir = run_root.parent.parent.name if run_root.name.startswith('seed-') and run_root.parent.name == 'seeds' else ''
    if algorithm and algorithm != 'NSGA-II' and mode == 'raw':
        return series_label or f"{algorithm.lower().replace(' ', '-')}-raw"
    if mode == 'raw' and method_dir in {'nsga2-raw', 'spea2-raw', 'moead-raw'}:
        return method_dir
    if mode == 'llm' and model:
        return series_label or f"llm-{model}"
    return method_dir or mode or series_label

seed_rows: list[dict[str, object]] = []
common_rows: list[dict[str, object]] = []

for block_id, comparison_root in BLOCK_COMPARISONS.items():
    block = manifest['blocks'].get(block_id)
    if not block or not comparison_root.exists():
        continue
    scenario_id = block['scenario_id']
    for seed_dir in sorted((comparison_root / 'by_seed').glob('seed-*')):
        seed = seed_dir.name.replace('seed-', '')
        candidate_summary_paths = [
            seed_dir / 'tables' / 'mode_metrics.csv',
            *sorted(seed_dir.glob('*/tables/mode_metrics.csv')),
        ]
        summary_rows = []
        for summary_path in candidate_summary_paths:
            summary_rows = read_csv(summary_path)
            if summary_rows:
                break
        if block_id == 'main_s4':
            summary_rows = [row for row in summary_rows if canonical_method_slug(row) in {'raw', 'llm-deepseek_v4_flash', 'llm'}]
        for row in summary_rows:
            source_run = row.get('run', '')
            method_slug = canonical_method_slug(row)
            seed_rows.append({
                'block_id': block_id,
                'scenario_id': scenario_id,
                'method_slug': method_slug,
                'series_label': row.get('series_label'),
                'benchmark_seed': seed,
                'algorithm_seed': '',
                'best_temperature_max': row.get('best_temperature_max'),
                'best_gradient_rms': row.get('best_gradient_rms'),
                'final_hypervolume': row.get('final_hypervolume'),
                'final_igd': row.get('final_igd'),
                'normalized_final_igd': '',
                'igd_reference_scope': f'{block_id}:seed-{seed}',
                'igd_reference_point_count': '',
                'feasible_rate': row.get('feasible_rate'),
                'first_feasible_pde_eval': row.get('first_feasible_pde_eval'),
                'pde_evaluations': row.get('pde_evaluations'),
                'solver_skipped_evaluations': row.get('solver_skipped_evaluations'),
                'pareto_size': row.get('front_size'),
                'source_run': source_run,
                'comparison_scope': seed_dir.as_posix(),
            })
        candidate_cutoff_paths = [
            seed_dir / 'tables' / 'common_pde_cutoff.csv',
            *sorted(seed_dir.glob('*/tables/common_pde_cutoff.csv')),
        ]
        cutoff_rows = []
        for cutoff_path in candidate_cutoff_paths:
            cutoff_rows = read_csv(cutoff_path)
            if cutoff_rows:
                break
        for row in cutoff_rows:
            row = dict(row)
            row['block_id'] = block_id
            row['scenario_id'] = scenario_id
            row['benchmark_seed'] = seed
            row['comparison_scope'] = seed_dir.as_posix()
            common_rows.append(row)

rows_by_scope: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
for row in seed_rows:
    rows_by_scope[(str(row['block_id']), str(row['benchmark_seed']))].append(row)

for scope, rows in rows_by_scope.items():
    fronts_by_row: list[list[tuple[float, float]]] = [load_pareto_points(str(row.get('source_run', ''))) for row in rows]
    all_points = [point for front in fronts_by_row for point in front]
    if not all_points:
        continue
    t_values = [point[0] for point in all_points]
    g_values = [point[1] for point in all_points]
    bounds = (min(t_values), max(t_values), min(g_values), max(g_values))
    normalized_all = normalize_points(all_points, bounds)
    reference = empirical_reference_front(nondominated(normalized_all))
    for row, front in zip(rows, fronts_by_row):
        normalized_front = normalize_points(front, bounds)
        row['normalized_final_igd'] = igd_2d(normalized_front, reference)
        row['igd_reference_point_count'] = len(reference)

grouped: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
for row in seed_rows:
    grouped[(str(row['block_id']), str(row['scenario_id']), str(row['method_slug']))].append(row)

aggregate_rows: list[dict[str, object]] = []
for (block_id, scenario_id, method_slug), rows in sorted(grouped.items()):
    values = {key: [v for v in (as_float(row.get(key)) for row in rows) if v is not None] for key in [
        'best_temperature_max',
        'best_gradient_rms',
        'final_hypervolume',
        'final_igd',
        'normalized_final_igd',
        'feasible_rate',
        'first_feasible_pde_eval',
        'pde_evaluations',
        'solver_skipped_evaluations',
    ]}
    aggregate_rows.append({
        'block_id': block_id,
        'scenario_id': scenario_id,
        'method_slug': method_slug,
        'seed_count': len(rows),
        'best_temperature_max_mean': mean(values['best_temperature_max']),
        'best_gradient_rms_mean': mean(values['best_gradient_rms']),
        'final_hypervolume_mean': mean(values['final_hypervolume']),
        'final_igd_mean': mean(values['final_igd']),
        'normalized_final_igd_mean': mean(values['normalized_final_igd']),
        'normalized_final_igd_median': median(values['normalized_final_igd']),
        'normalized_final_igd_iqr': iqr(values['normalized_final_igd']),
        'feasible_rate_mean': mean(values['feasible_rate']),
        'first_feasible_pde_eval_mean': mean(values['first_feasible_pde_eval']),
        'pde_evaluations_mean': mean(values['pde_evaluations']),
        'solver_skipped_evaluations_mean': mean(values['solver_skipped_evaluations']),
        'source_comparison': BLOCK_COMPARISONS[block_id].as_posix(),
    })

pairwise_rows: list[dict[str, object]] = []
for (block_id, seed), rows in sorted(rows_by_scope.items()):
    for left, right in combinations(rows, 2):
        pairwise_rows.append({
            'block_id': block_id,
            'benchmark_seed': seed,
            'left_method': left.get('method_slug'),
            'right_method': right.get('method_slug'),
            'delta_best_temperature_max': None if as_float(right.get('best_temperature_max')) is None or as_float(left.get('best_temperature_max')) is None else as_float(right.get('best_temperature_max')) - as_float(left.get('best_temperature_max')),
            'delta_best_gradient_rms': None if as_float(right.get('best_gradient_rms')) is None or as_float(left.get('best_gradient_rms')) is None else as_float(right.get('best_gradient_rms')) - as_float(left.get('best_gradient_rms')),
            'delta_final_hypervolume': None if as_float(right.get('final_hypervolume')) is None or as_float(left.get('final_hypervolume')) is None else as_float(right.get('final_hypervolume')) - as_float(left.get('final_hypervolume')),
            'delta_normalized_final_igd': None if as_float(right.get('normalized_final_igd')) is None or as_float(left.get('normalized_final_igd')) is None else as_float(right.get('normalized_final_igd')) - as_float(left.get('normalized_final_igd')),
        })

write_csv(TABLES / 'seed_metrics.csv', seed_rows, [
    'block_id','scenario_id','method_slug','series_label','benchmark_seed','algorithm_seed',
    'best_temperature_max','best_gradient_rms','final_hypervolume','final_igd',
    'normalized_final_igd','igd_reference_scope','igd_reference_point_count','feasible_rate',
    'first_feasible_pde_eval','pde_evaluations','solver_skipped_evaluations','pareto_size',
    'source_run','comparison_scope',
])
write_csv(TABLES / 'aggregate_metrics.csv', aggregate_rows, [
    'block_id','scenario_id','method_slug','seed_count','best_temperature_max_mean',
    'best_gradient_rms_mean','final_hypervolume_mean','final_igd_mean',
    'normalized_final_igd_mean','normalized_final_igd_median','normalized_final_igd_iqr',
    'feasible_rate_mean','first_feasible_pde_eval_mean','pde_evaluations_mean',
    'solver_skipped_evaluations_mean','source_comparison',
])
write_csv(TABLES / 'pairwise_deltas.csv', pairwise_rows, [
    'block_id','benchmark_seed','left_method','right_method','delta_best_temperature_max',
    'delta_best_gradient_rms','delta_final_hypervolume','delta_normalized_final_igd',
])
write_csv(TABLES / 'common_pde_cutoff.csv', common_rows, sorted({key for row in common_rows for key in row}))
print(f'wrote {len(seed_rows)} seed metric rows')
print(f'wrote {len(aggregate_rows)} aggregate rows')
print(f'wrote {len(pairwise_rows)} pairwise rows')
print(f'wrote {len(common_rows)} common cutoff rows')
PY
```

Expected: `seed_metrics.csv`, `aggregate_metrics.csv`, `pairwise_deltas.csv`, and `common_pde_cutoff.csv` exist under `scenario_runs/paper_experiment_db/tables/`.

- [ ] **Step 4: Export model-sensitivity metrics**

The model-sensitivity archive compares multiple LLM profiles with the same `mode=llm`, so export it from per-profile directories rather than suite-owned mode comparisons.

Run:

```bash
conda run -n msfenicsx python - <<'PY'
from pathlib import Path
import csv
import json

root = Path('scenario_runs/s5_aggressive15/0510_archive__model_compare_seed11')
rows = []
main_profiles = {'llm-deepseek-v4-flash', 'llm-qwen3-6-plus', 'llm-gpt-5-5', 'llm-mimo-v2-5'}
appendix_profiles = {'llm-glm-5', 'llm-minimax-m2-5'}

for profile_dir in sorted(root.iterdir()):
    if not profile_dir.is_dir() or profile_dir.name == 'raw':
        continue
    mode_summary_path = profile_dir / 'summaries' / 'mode_summary.json'
    decision_summary_path = profile_dir / 'seeds' / 'seed-11' / 'summaries' / 'llm_decision_summary.json'
    if not mode_summary_path.exists():
        continue
    mode_summary = json.loads(mode_summary_path.read_text(encoding='utf-8'))
    decision_summary = {}
    if decision_summary_path.exists():
        decision_summary = json.loads(decision_summary_path.read_text(encoding='utf-8'))
    ranker = decision_summary.get('ranker_diagnostics', {})
    rows.append({
        'profile_slug': profile_dir.name,
        'placement': 'main' if profile_dir.name in main_profiles else 'appendix' if profile_dir.name in appendix_profiles else 'unregistered',
        'benchmark_seed': 11,
        'best_peak': mode_summary.get('best_peak_stats', {}).get('mean'),
        'best_gradient': mode_summary.get('best_gradient_stats', {}).get('mean'),
        'feasible_rate': mode_summary.get('optimizer_feasible_rate_stats', {}).get('mean'),
        'first_feasible_pde_eval': mode_summary.get('first_feasible_pde_eval_stats', {}).get('mean'),
        'pareto_size': mode_summary.get('pareto_size_stats', {}).get('mean'),
        'decision_count': decision_summary.get('decision_count'),
        'llm_valid_selection_count': decision_summary.get('llm_valid_selection_count'),
        'fallback_selection_count': decision_summary.get('fallback_selection_count'),
        'contract_invalid_response_count': ranker.get('contract_invalid_response_count'),
        'selected_rank_counts': json.dumps(ranker.get('selected_rank_counts', {}), sort_keys=True),
        'operator_counts': json.dumps(decision_summary.get('operator_counts', {}), sort_keys=True),
        'source_root': profile_dir.as_posix(),
    })

out = Path('scenario_runs/paper_experiment_db/tables/model_sensitivity_metrics.csv')
with out.open('w', newline='', encoding='utf-8') as handle:
    fieldnames = [
        'profile_slug','placement','benchmark_seed','best_peak','best_gradient','feasible_rate',
        'first_feasible_pde_eval','pareto_size','decision_count','llm_valid_selection_count',
        'fallback_selection_count','contract_invalid_response_count','selected_rank_counts',
        'operator_counts','source_root',
    ]
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
print(f'wrote {out} rows={len(rows)}')
PY
```

Expected: `model_sensitivity_metrics.csv` includes DeepSeek/Qwen/GPT/MiMo as `main` and GLM/MiniMax as `appendix`.

- [ ] **Step 5: Materialize DuckDB database**

Run:

```bash
conda run -n msfenicsx python - <<'PY'
from pathlib import Path
import duckdb

db_path = Path('scenario_runs/paper_experiment_db/msfenicsx_experiments.duckdb')
tables_root = Path('scenario_runs/paper_experiment_db/tables')
con = duckdb.connect(str(db_path))
for csv_path in sorted(tables_root.glob('*.csv')):
    table_name = csv_path.stem
    con.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_csv_auto(?)", [str(csv_path)])
con.close()
print(f'wrote {db_path}')
PY
```

Expected: `scenario_runs/paper_experiment_db/msfenicsx_experiments.duckdb` contains at least `seed_metrics`, `aggregate_metrics`, `pairwise_deltas`, `common_pde_cutoff`, `claim_evidence`, `artifact_index`, and `completeness_matrix` tables when their CSVs exist.

- [ ] **Step 6: Inspect nIGD-ready metrics**

Run:

```bash
conda run -n msfenicsx python - <<'PY'
import duckdb
con = duckdb.connect('scenario_runs/paper_experiment_db/msfenicsx_experiments.duckdb')
print(con.execute("""
SELECT block_id, method_slug, COUNT(*) AS n,
       AVG(CAST(normalized_final_igd AS DOUBLE)) AS mean_nigd,
       AVG(CAST(final_hypervolume AS DOUBLE)) AS mean_hv
FROM seed_metrics
GROUP BY block_id, method_slug
ORDER BY block_id, method_slug
""").fetchdf())
con.close()
PY
```

Expected: completed blocks show rows; pending blocks appear after their comparisons are generated.

- [ ] **Step 7: Use nIGD in Results wording**

Allowed wording:

```text
nIGD is reported as a distance-to-reference-front metric within each registered comparison scope. Lower nIGD indicates that the obtained front lies closer to the empirical nondominated reference front formed from all methods in the same scenario, seed, and block.
```

Forbidden wording:

```text
S4 has lower IGD than S6, so S4 is easier.
```

Reason: absolute cross-scale IGD is not comparable without careful scale normalization and shared task interpretation.

## Task 5: Build S5 Seed11 Representative Diagnostic Case Figure Set

**Files:**
- Create: `scenario_runs/paper_experiment_db/figures/s5_seed11_diagnostic_case/README.md`
- Copy: selected images from `scenario_runs/s5_aggressive15/0510_archive__raw_llm-deepseek_v4_flash_favorable5/llm-deepseek-v4-flash/seeds/seed-11/figures/`
- Modify: `paper/els-cas-templates/planning/figure_table_register.md`

- [ ] **Step 1: Confirm source figures exist**

Run:

```bash
find scenario_runs/s5_aggressive15/0510_archive__raw_llm-deepseek_v4_flash_favorable5/llm-deepseek-v4-flash/seeds/seed-11/figures \
  -maxdepth 1 -type f \( -name 'layout_initial.png' -o -name 'layout_final.png' -o -name 'temperature_field_knee-candidate.png' -o -name 'gradient_field_knee-candidate.png' -o -name 'search_trajectory_network.png' -o -name 'hypervolume_progress.png' -o -name 'objective_progress.png' -o -name 'operator_phase_heatmap.png' \) \
  | sort
```

Expected: all listed files exist.

- [ ] **Step 2: Stage selected diagnostic figures**

Use copies rather than modifying source artifacts:

```bash
cp scenario_runs/s5_aggressive15/0510_archive__raw_llm-deepseek_v4_flash_favorable5/llm-deepseek-v4-flash/seeds/seed-11/figures/layout_initial.png \
  scenario_runs/paper_experiment_db/figures/s5_seed11_diagnostic_case/
cp scenario_runs/s5_aggressive15/0510_archive__raw_llm-deepseek_v4_flash_favorable5/llm-deepseek-v4-flash/seeds/seed-11/figures/layout_final.png \
  scenario_runs/paper_experiment_db/figures/s5_seed11_diagnostic_case/
cp scenario_runs/s5_aggressive15/0510_archive__raw_llm-deepseek_v4_flash_favorable5/llm-deepseek-v4-flash/seeds/seed-11/figures/temperature_field_knee-candidate.png \
  scenario_runs/paper_experiment_db/figures/s5_seed11_diagnostic_case/
cp scenario_runs/s5_aggressive15/0510_archive__raw_llm-deepseek_v4_flash_favorable5/llm-deepseek-v4-flash/seeds/seed-11/figures/gradient_field_knee-candidate.png \
  scenario_runs/paper_experiment_db/figures/s5_seed11_diagnostic_case/
cp scenario_runs/s5_aggressive15/0510_archive__raw_llm-deepseek_v4_flash_favorable5/llm-deepseek-v4-flash/seeds/seed-11/figures/search_trajectory_network.png \
  scenario_runs/paper_experiment_db/figures/s5_seed11_diagnostic_case/
cp scenario_runs/s5_aggressive15/0510_archive__raw_llm-deepseek_v4_flash_favorable5/llm-deepseek-v4-flash/seeds/seed-11/figures/hypervolume_progress.png \
  scenario_runs/paper_experiment_db/figures/s5_seed11_diagnostic_case/
cp scenario_runs/s5_aggressive15/0510_archive__raw_llm-deepseek_v4_flash_favorable5/llm-deepseek-v4-flash/seeds/seed-11/figures/objective_progress.png \
  scenario_runs/paper_experiment_db/figures/s5_seed11_diagnostic_case/
cp scenario_runs/s5_aggressive15/0510_archive__raw_llm-deepseek_v4_flash_favorable5/llm-deepseek-v4-flash/seeds/seed-11/figures/operator_phase_heatmap.png \
  scenario_runs/paper_experiment_db/figures/s5_seed11_diagnostic_case/
```

Expected: staged figure directory contains the selected case-study images. Do not edit original generated artifacts.

- [ ] **Step 3: Write diagnostic README**

Create `scenario_runs/paper_experiment_db/figures/s5_seed11_diagnostic_case/README.md`:

```markdown
# S5 Seed11 Diagnostic Case

This directory stages paper-facing copies of selected figures from:

`scenario_runs/s5_aggressive15/0510_archive__raw_llm-deepseek_v4_flash_favorable5/llm-deepseek-v4-flash/seeds/seed-11/figures/`

Role in paper:

- S5 seed11 is a representative diagnostic case.
- It illustrates how the semantic controller behaves in one fully traced medium-scale run.
- It does not replace multi-seed aggregate evidence from S4/S5/S6.

Recommended wording:

> The aggregate tables answer whether the method works across seeds and scale levels; the S5 seed11 diagnostic case shows how the method behaves in one fully traced medium-scale run.

Figure roles:

- `layout_initial.png`: starting thermal layout under the fixed S5 case.
- `layout_final.png`: final representative layout after semantic operator-controlled search.
- `temperature_field_knee-candidate.png`: temperature field of the knee representative.
- `gradient_field_knee-candidate.png`: gradient field of the knee representative.
- `search_trajectory_network.png`: evaluated candidate network; nodes are optimizer-evaluated candidates, not LLM-generated layouts.
- `hypervolume_progress.png`: Pareto-front quality progress for the diagnostic run.
- `objective_progress.png`: objective progress for peak temperature and gradient RMS.
- `operator_phase_heatmap.png`: phase-aware operator exposure supporting state-to-operator matching.
```

Expected: the README makes the diagnostic-vs-statistical boundary explicit.

- [ ] **Step 4: Register S5 diagnostic figures**

Append to `paper/els-cas-templates/planning/figure_table_register.md`:

```markdown
| Fig. 8 | S5 seed11 representative diagnostic case | A fully traced medium-scale run illustrates initial-to-final layout change, thermal-field improvement, and search-process behavior without replacing multi-seed aggregate evidence. | Results / Mechanistic Analysis | `scenario_runs/paper_experiment_db/figures/s5_seed11_diagnostic_case/` | planned |
| Fig. 9 | S5 seed11 search trajectory and operator phases | The diagnostic run shows evaluated-candidate search structure and phase-aware operator routing; nodes are optimizer-evaluated candidates, not LLM-generated layouts. | Mechanistic Analysis | `search_trajectory_network.png`, `operator_phase_heatmap.png` | planned |
```

Expected: future LaTeX writing references Fig. 8/Fig. 9 through the register.

## Task 6: Update Experimental Setup And Results Wording After Evidence Freeze

**Files:**
- Modify: `paper/els-cas-templates/sections/05_experimental_setup.tex`
- Modify: `paper/els-cas-templates/sections/06_results.tex`
- Modify: `paper/els-cas-templates/sections/07_mechanistic_analysis.tex`

- [ ] **Step 1: Replace obsolete S7 wording**

Run:

```bash
rg -n "S7|s7|aggressive25|Gemma|Kimi" paper/els-cas-templates/sections paper/els-cas-templates/planning
```

Expected: no active final-experiment wording still claims S7 or Kimi as required. Existing historical notes must be rewritten or explicitly labeled obsolete.

- [ ] **Step 2: Insert seed-cohort policy in §5**

Add this paragraph to §5 Experimental Setup:

```latex
Within each comparison block, all compared methods use the same benchmark seeds, algorithm-seed offset, scenario case, repair policy, objective definitions, and nominal expensive-evaluation budget. Across blocks, the seed cohorts are not required to be identical: the S4 and S6 archives use seeds 11, 17, 23, 29, and 31, while the S5 main archive uses seeds 11, 23, 31, 37, and 41. This design broadens stochastic coverage across the full experimental campaign, while preserving paired fairness inside every reported comparison block.
```

Expected: readers understand why S4/S6 and S5 cohorts differ.

- [ ] **Step 3: Insert S5 diagnostic-case boundary in §6 or §7**

Add this paragraph before presenting detailed S5 seed11 figures:

```latex
We use S5 seed 11 as a representative diagnostic case because it is a medium-scale benchmark with complete layout, thermal-field, search-trajectory, and controller-trace artifacts. This case is not used as a substitute for the multi-seed aggregate results. The aggregate tables answer whether the method works across seeds and scale levels; the S5 seed-11 diagnostic figures show how the method behaves in one fully traced run.
```

Expected: detailed S5 seed11 visuals are framed as mechanism/interpretability evidence.

- [ ] **Step 4: Add S6 feedback-off diagnostic paragraph in §7**

Add this paragraph to §7 Mechanistic Analysis:

```latex
We include a single-seed feedback-off diagnostic on S6 seed 23. In this run, the DeepSeek controller receives the same semantic prompt structure, but the operator-level PDE outcome fields exposed in the operator panel are zeroed: across 1,920 prompts with an operator panel and 17,280 audited operator rows, none contains nonzero PDE feedback. The optimizer still performs PDE evaluations, but the controller cannot assign operator credit from observed outcomes. The resulting final hypervolume is 543.09, about 51% of the same-seed raw baseline value of 1065.40. This diagnostic is not used as a statistical baseline; it shows that our semantic controller depends on closed-loop operator-effect feedback rather than LLM operator choice alone.
```

Expected: the feedback-off result is presented as a single-seed negative control and is explicitly excluded from main aggregate statistics.

- [ ] **Step 5: Add nIGD metric description**

Add this paragraph to §5 Metrics:

```latex
We also report normalized inverted generational distance (nIGD) as a distance-to-reference-front metric. For each registered comparison scope, the empirical reference front is formed by merging feasible Pareto points from all compared methods in the same scenario, seed, and block, then extracting the nondominated front. Objectives are min--max normalized within that scope before IGD is computed. Lower nIGD indicates a front closer to the empirical reference front. Absolute nIGD values are interpreted within a comparison scope; cross-scale conclusions use paired deltas and win rates rather than directly comparing S4, S5, and S6 values.
```

Expected: IGD/nIGD interpretation is defensible.

## Task 7: Verification And Reporting

**Files:**
- Read: generated database tables
- Read: paper planning registers
- Run if Python source code changes: focused tests under `tests/optimizers/`

- [ ] **Step 1: Verify completeness matrix**

Run:

```bash
conda run -n msfenicsx python - <<'PY'
import csv
from collections import Counter
rows = list(csv.DictReader(open('scenario_runs/paper_experiment_db/tables/completeness_matrix.csv', encoding='utf-8')))
print(Counter(row['status'] for row in rows))
for row in rows:
    if row['status'] != 'complete':
        print(row['block_id'], row['method_slug'], row['seed'], row['status'])
PY
```

Expected: in Stage A, incomplete rows are known and limited to `main_s6` DeepSeek formal seeds `17,23,29,31` plus the absent S6 unified archive rows. S5 algorithm baseline and S6 feedback-off diagnostic should be complete. In Stage B, `main_s6` should become complete after the unified archive is created.

2026-05-11 note: after the Stage A exporter refresh, `completeness_matrix.csv` records all five `main_s6` LLM rows as `pending_missing_s6_main_archive` because the unified S6 main archive path is intentionally absent until Stage B. This is acceptable; S6 raw rows remain complete and S6 feedback-off is diagnostic-only.

- [ ] **Step 2: Verify claim evidence paths**

Run:

```bash
conda run -n msfenicsx python - <<'PY'
import csv
from pathlib import Path
for row in csv.DictReader(open('scenario_runs/paper_experiment_db/tables/claim_evidence.csv', encoding='utf-8')):
    for key in ['comparison_manifest','aggregate_table']:
        value = row.get(key, '').strip()
        if value and not Path(value).exists():
            print('missing', row['claim_id'], key, value)
PY
```

Expected: no missing paths for `complete` claims. Pending claims may have blank paths.

- [ ] **Step 3: Verify no active paper text overclaims pending blocks**

Run:

```bash
rg -n "confirmed|proves|across S4/S5/S6|Kimi|S7|uniform dominance" paper/els-cas-templates/sections paper/els-cas-templates/planning
```

Expected: any strong wording is either backed by `claim_evidence.csv` complete rows or softened.

- [ ] **Step 4: Run focused tests if Python code changed**

If only Markdown/CSV exports were changed, skip pytest and record that no code changed. If `optimizers/comparison_artifacts.py` or IGD code was modified, run:

```bash
conda run -n msfenicsx pytest -v tests/optimizers
```

Expected: tests pass. If tests fail, use `systematic-debugging` before editing.

## Final Handoff Notes

- Do not manually edit generated artifacts to change conclusions.
- Do not pool unmatched seed cohorts across blocks.
- Keep failed, partial, or trace-only runs visible in `completeness_matrix.csv`.
- S5 seed11 detailed figures are explanatory diagnostics, not a substitute for aggregate evidence.
- IGD/nIGD belongs in final result tables, but absolute cross-scale IGD comparisons should be avoided.
- Stage A can finish now without S6 main; leave `main_s6` pending in the database and evidence register.
- After S6 DeepSeek formal seeds `17,23,29,31` finish with valid nonzero operator-feedback prompts, run the Stage B-only S6 archive/comparison steps, then rerun Task 2, Task 3, and Task 4.
