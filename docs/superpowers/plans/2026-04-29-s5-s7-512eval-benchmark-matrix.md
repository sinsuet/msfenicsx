# S5-S7 512-Evaluation Benchmark 矩阵实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 S5-S7 512-evaluation 大规模 benchmark 矩阵所需的规格文件、matrix runner、失败补跑、统计聚合、可视化和代表 run 比较产物。

**Architecture:** 新增 `optimizers/matrix/` 作为矩阵层，专门负责任务展开、spec snapshot、run index、聚合、figure rendering 和 representative selection；现有 `optimizers.cli optimize-benchmark`、driver、artifact writer、render-assets 和 compare-runs 继续作为 leaf run 执行与产物生成层。场景 YAML 保持手写输入职责，新增 SPEA2/MOEA-D raw specs 只声明配置，不放业务逻辑。

**Tech Stack:** Python 3.12、PyYAML、pandas、numpy、matplotlib/seaborn、pymoo、pytest、现有 `msfenicsx` conda 环境。

---

## 文件结构

### 新增文件

- `scenarios/optimization/s5_aggressive15_spea2_raw.yaml`：S5 SPEA2 raw 正式规格。
- `scenarios/optimization/s5_aggressive15_moead_raw.yaml`：S5 MOEA/D raw 正式规格。
- `scenarios/optimization/s6_aggressive20_spea2_raw.yaml`：S6 SPEA2 raw 正式规格。
- `scenarios/optimization/s6_aggressive20_moead_raw.yaml`：S6 MOEA/D raw 正式规格。
- `scenarios/optimization/s7_aggressive25_spea2_raw.yaml`：S7 SPEA2 raw 正式规格。
- `scenarios/optimization/s7_aggressive25_moead_raw.yaml`：S7 MOEA/D raw 正式规格。
- `scenarios/optimization/profiles/s5_aggressive15_spea2_raw.yaml`：S5 SPEA2 raw profile。
- `scenarios/optimization/profiles/s5_aggressive15_moead_raw.yaml`：S5 MOEA/D raw profile。
- `scenarios/optimization/profiles/s6_aggressive20_spea2_raw.yaml`：S6 SPEA2 raw profile。
- `scenarios/optimization/profiles/s6_aggressive20_moead_raw.yaml`：S6 MOEA/D raw profile。
- `scenarios/optimization/profiles/s7_aggressive25_spea2_raw.yaml`：S7 SPEA2 raw profile。
- `scenarios/optimization/profiles/s7_aggressive25_moead_raw.yaml`：S7 MOEA/D raw profile。
- `optimizers/matrix/__init__.py`：矩阵层公开入口。
- `optimizers/matrix/models.py`：矩阵配置、leaf run、run index row 等 dataclass。
- `optimizers/matrix/config.py`：内置 S5-S7 512eval matrix 定义。
- `optimizers/matrix/spec_snapshots.py`：生成 per-leaf optimization spec snapshot。
- `optimizers/matrix/index.py`：读写 `run_index.csv`、状态更新、attempt 选择。
- `optimizers/matrix/leaf_executor.py`：封装单个 leaf run 的 `optimize-benchmark` 调用，避免 `optimizers.cli` 与 runner 互相 import。
- `optimizers/matrix/runner.py`：按 block 运行 leaf runs、按 block cap 控制外层并发、resume、失败补跑。
- `optimizers/matrix/aggregate.py`：汇总 outcomes、paired differences、rank、failure 和 LLM diagnostics。
- `optimizers/matrix/figures.py`：matrix-level PNG/PDF 图。
- `optimizers/matrix/representatives.py`：best-HV run + knee point 选择和关键 compare-runs bundle 规划。
- `tests/optimizers/test_matrix_specs.py`：S5-S7 SPEA2/MOEA-D specs 合约测试。
- `tests/optimizers/test_matrix_config.py`：矩阵定义和 run count 测试。
- `tests/optimizers/test_matrix_spec_snapshots.py`：seed/budget/profile snapshot 测试。
- `tests/optimizers/test_matrix_index.py`：run index 读写和 retry 测试。
- `tests/optimizers/test_matrix_aggregate.py`：统计汇总公式测试。
- `tests/optimizers/test_matrix_figures.py`：figure 输出文件和格式测试。
- `tests/optimizers/test_matrix_representatives.py`：representative selection 测试。

### 修改文件

- `llm/openai_compatible/profiles.yaml`：新增 `gpt_5_4` alias，保留 `default` 和 `gpt`。
- `optimizers/cli.py`：新增 matrix 相关 CLI 子命令。
- `CLAUDE.md`：已加入中文写作规则；后续实现若新增命令需同步 preferred commands。
- `AGENTS.md`：已加入中文写作规则；后续实现若新增命令需同步 preferred commands。

---

## Task 1：补齐 S5/S6/S7 SPEA2 和 MOEA/D raw specs

**Files:**
- Create: `scenarios/optimization/s5_aggressive15_spea2_raw.yaml`
- Create: `scenarios/optimization/s5_aggressive15_moead_raw.yaml`
- Create: `scenarios/optimization/s6_aggressive20_spea2_raw.yaml`
- Create: `scenarios/optimization/s6_aggressive20_moead_raw.yaml`
- Create: `scenarios/optimization/s7_aggressive25_spea2_raw.yaml`
- Create: `scenarios/optimization/s7_aggressive25_moead_raw.yaml`
- Create: `scenarios/optimization/profiles/s5_aggressive15_spea2_raw.yaml`
- Create: `scenarios/optimization/profiles/s5_aggressive15_moead_raw.yaml`
- Create: `scenarios/optimization/profiles/s6_aggressive20_spea2_raw.yaml`
- Create: `scenarios/optimization/profiles/s6_aggressive20_moead_raw.yaml`
- Create: `scenarios/optimization/profiles/s7_aggressive25_spea2_raw.yaml`
- Create: `scenarios/optimization/profiles/s7_aggressive25_moead_raw.yaml`
- Modify: `tests/optimizers/test_s5_aggressive15_specs.py`
- Modify: `tests/optimizers/test_s6_aggressive20_specs.py`
- Modify: `tests/optimizers/test_s7_aggressive25_specs.py`
- Test: `tests/optimizers/test_matrix_specs.py`

- [ ] **Step 1: 写失败测试，验证 S5/S6/S7 raw-only specs 存在且字段正确**

Create `tests/optimizers/test_matrix_specs.py`:

```python
from pathlib import Path

import pytest

from optimizers.io import load_optimization_spec


@pytest.mark.parametrize(
    ("scenario_id", "dimension"),
    [
        ("s5_aggressive15", 32),
        ("s6_aggressive20", 42),
        ("s7_aggressive25", 52),
    ],
)
@pytest.mark.parametrize(
    ("backbone", "family"),
    [
        ("spea2", "genetic"),
        ("moead", "decomposition"),
    ],
)
def test_s5_s7_raw_backbone_specs_exist_and_match_contract(scenario_id: str, dimension: int, backbone: str, family: str) -> None:
    spec_path = Path(f"scenarios/optimization/{scenario_id}_{backbone}_raw.yaml")
    profile_path = Path(f"scenarios/optimization/profiles/{scenario_id}_{backbone}_raw.yaml")

    assert spec_path.exists()
    assert profile_path.exists()

    spec = load_optimization_spec(spec_path)
    payload = spec.to_dict()

    assert payload["spec_meta"]["spec_id"] == f"{scenario_id}_{backbone}_raw"
    assert payload["benchmark_source"]["template_path"] == f"scenarios/templates/{scenario_id}.yaml"
    assert payload["benchmark_source"]["seed"] == 11
    assert len(payload["design_variables"]) == dimension
    assert payload["algorithm"]["family"] == family
    assert payload["algorithm"]["backbone"] == backbone
    assert payload["algorithm"]["mode"] == "raw"
    assert payload["algorithm"]["seed"] == 7
    assert payload["algorithm"]["profile_path"] == f"scenarios/optimization/profiles/{scenario_id}_{backbone}_raw.yaml"
    assert payload["evaluation_protocol"]["evaluation_spec_path"] == f"scenarios/evaluation/{scenario_id}_eval.yaml"
    assert "operator_control" not in payload
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_matrix_specs.py
```

Expected: FAIL，原因是新增 spec/profile 文件尚不存在。

- [ ] **Step 3: 创建 profile YAML**

每个 SPEA2 profile 使用下面结构，将 `scenario_id` 替换为对应场景：

```yaml
schema_version: "1.0"
profile_id: s5_aggressive15_spea2_raw
family: genetic
backbone: spea2
mode: raw
parameters:
  crossover:
    operator: sbx
    eta: 15
    prob: 0.9
  mutation:
    operator: pm
    eta: 20
```

每个 MOEA/D profile 使用下面结构，将 `scenario_id` 替换为对应场景：

```yaml
schema_version: "1.0"
profile_id: s5_aggressive15_moead_raw
family: decomposition
backbone: moead
mode: raw
parameters:
  reference_directions:
    scheme: energy
  neighbors:
    strategy: half_population
    min_size: 2
```

- [ ] **Step 4: 创建 raw optimization specs**

对每个场景，复制对应现有 NSGA-II raw spec 的 `benchmark_source`、`design_variables`、`evaluation_protocol` 和 scenario-specific bounds，只改 `spec_meta` 与 `algorithm`。

SPEA2 的 `algorithm` 段：

```yaml
algorithm:
  family: genetic
  backbone: spea2
  mode: raw
  population_size: 32
  num_generations: 16
  seed: 7
  profile_path: scenarios/optimization/profiles/s5_aggressive15_spea2_raw.yaml
```

MOEA/D 的 `algorithm` 段：

```yaml
algorithm:
  family: decomposition
  backbone: moead
  mode: raw
  population_size: 32
  num_generations: 16
  seed: 7
  profile_path: scenarios/optimization/profiles/s5_aggressive15_moead_raw.yaml
```

`spec_meta.spec_id` 必须分别为：

```text
s5_aggressive15_spea2_raw
s5_aggressive15_moead_raw
s6_aggressive20_spea2_raw
s6_aggressive20_moead_raw
s7_aggressive25_spea2_raw
s7_aggressive25_moead_raw
```

- [ ] **Step 5: 运行规格测试确认通过**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_matrix_specs.py
```

Expected: PASS。

---

## Task 2：补齐 `gpt_5_4` LLM profile alias

**Files:**
- Modify: `llm/openai_compatible/profiles.yaml`
- Test: `tests/optimizers/test_llm_client.py`

- [ ] **Step 1: 写失败测试，验证六个 matrix profile IDs 可解析**

在 `tests/optimizers/test_llm_client.py` 增加：

```python
def test_matrix_llm_profiles_include_gpt_5_4_alias(monkeypatch):
    from llm.openai_compatible.profile_loader import load_provider_profile_overlay

    monkeypatch.setenv("GPT_PROXY_API_KEY", "gpt-key")
    monkeypatch.setenv("GPT_PROXY_BASE_URL", "https://gpt.example/v1")
    monkeypatch.setenv("QWEN_PROXY_API_KEY", "qwen-key")
    monkeypatch.setenv("QWEN_PROXY_BASE_URL", "https://qwen.example/v1")
    monkeypatch.setenv("DEEPSEEK_PROXY_API_KEY", "deepseek-key")
    monkeypatch.setenv("DEEPSEEK_PROXY_BASE_URL", "https://deepseek.example/v1")
    monkeypatch.setenv("GEMMA4_API_KEY", "gemma-key")
    monkeypatch.setenv("GEMMA4_BASE_URL", "http://127.0.0.1:8000/v1")

    expected_models = {
        "gpt_5_4": "gpt-5.4",
        "qwen3_6_plus": "qwen3.6-plus",
        "glm_5": "glm-5",
        "minimax_m2_5": "MiniMax-M2.5",
        "deepseek_v4_flash": "DeepSeek-V4-Flash",
        "gemma4": "gemma-4",
    }

    for profile_id, model in expected_models.items():
        overlay = load_provider_profile_overlay(profile_id)
        assert overlay["LLM_MODEL"] == model
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_llm_client.py::test_matrix_llm_profiles_include_gpt_5_4_alias
```

Expected: FAIL，原因是 `gpt_5_4` profile 尚不存在。

- [ ] **Step 3: 修改 profiles.yaml**

在 `llm/openai_compatible/profiles.yaml` 的 `profiles:` 下增加：

```yaml
  gpt_5_4:
    source_api_key_env_var: GPT_PROXY_API_KEY
    source_base_url_env_var: GPT_PROXY_BASE_URL
    model: gpt-5.4
```

保留现有 `default` 和 `gpt`，二者继续指向 `GPT_PROXY_* -> gpt-5.4`。

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_llm_client.py::test_matrix_llm_profiles_include_gpt_5_4_alias
```

Expected: PASS。

---

## Task 3：定义矩阵配置模型和 S5-S7 512eval 内置矩阵

**Files:**
- Create: `optimizers/matrix/__init__.py`
- Create: `optimizers/matrix/models.py`
- Create: `optimizers/matrix/config.py`
- Test: `tests/optimizers/test_matrix_config.py`

- [ ] **Step 1: 写失败测试**

Create `tests/optimizers/test_matrix_config.py`:

```python
from optimizers.matrix.config import build_s5_s7_512eval_matrix


def test_s5_s7_matrix_counts_and_blocks() -> None:
    matrix = build_s5_s7_512eval_matrix()

    assert matrix.matrix_id == "s5_s7_512eval"
    assert matrix.population_size == 32
    assert matrix.num_generations == 16
    assert matrix.benchmark_seeds == (11, 17, 23)
    assert matrix.algorithm_seeds == (101, 102, 103)

    leaves = matrix.expand_leaves()
    assert len(leaves) == 270

    counts = {}
    for leaf in leaves:
        counts[leaf.block_id] = counts.get(leaf.block_id, 0) + 1

    assert counts == {
        "M1_raw_backbone_512eval": 81,
        "M2_nsga2_union_512eval": 27,
        "M3a_llm_gpt_5_4_512eval": 27,
        "M3b_llm_qwen3_6_plus_512eval": 27,
        "M3c_llm_glm_5_512eval": 27,
        "M3d_llm_minimax_m2_5_512eval": 27,
        "M3e_llm_deepseek_v4_flash_512eval": 27,
        "M3f_llm_gemma4_512eval": 27,
    }


def test_s5_s7_matrix_resource_caps() -> None:
    matrix = build_s5_s7_512eval_matrix()

    assert matrix.resource_caps["raw"].evaluation_workers == 8
    assert matrix.resource_caps["raw"].concurrent_runs == 80
    assert matrix.resource_caps["union"].evaluation_workers == 8
    assert matrix.resource_caps["union"].concurrent_runs == 60
    assert matrix.resource_caps["external_llm"].evaluation_workers == 3
    assert matrix.resource_caps["external_llm"].concurrent_runs == 20
    assert matrix.resource_caps["gemma4"].evaluation_workers == 3
    assert matrix.resource_caps["gemma4"].concurrent_runs == 8
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_matrix_config.py
```

Expected: FAIL，原因是 `optimizers.matrix` 尚不存在。

- [ ] **Step 3: 实现 dataclass 模型**

Create `optimizers/matrix/models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


ModeId = Literal["raw", "union", "llm"]


@dataclass(frozen=True, slots=True)
class ResourceCap:
    evaluation_workers: int
    concurrent_runs: int

    @property
    def estimated_workers(self) -> int:
        return int(self.evaluation_workers) * int(self.concurrent_runs)


@dataclass(frozen=True, slots=True)
class MatrixLeaf:
    matrix_id: str
    block_id: str
    scenario_id: str
    method_id: str
    algorithm_family: str
    algorithm_backbone: str
    mode: ModeId
    llm_profile: str | None
    benchmark_seed: int
    algorithm_seed: int
    population_size: int
    num_generations: int
    base_spec_path: Path

    @property
    def nominal_budget(self) -> int:
        return int(self.population_size) * int(self.num_generations)


@dataclass(frozen=True, slots=True)
class MatrixConfig:
    matrix_id: str
    scenarios: tuple[str, ...]
    benchmark_seeds: tuple[int, ...]
    algorithm_seeds: tuple[int, ...]
    population_size: int
    num_generations: int
    llm_profiles: tuple[str, ...]
    resource_caps: dict[str, ResourceCap]

    def expand_leaves(self) -> list[MatrixLeaf]:
        leaves: list[MatrixLeaf] = []
        for scenario_id in self.scenarios:
            for backbone, family in (("nsga2", "genetic"), ("spea2", "genetic"), ("moead", "decomposition")):
                for benchmark_seed in self.benchmark_seeds:
                    for algorithm_seed in self.algorithm_seeds:
                        leaves.append(
                            MatrixLeaf(
                                matrix_id=self.matrix_id,
                                block_id="M1_raw_backbone_512eval",
                                scenario_id=scenario_id,
                                method_id=f"{backbone}_raw",
                                algorithm_family=family,
                                algorithm_backbone=backbone,
                                mode="raw",
                                llm_profile=None,
                                benchmark_seed=benchmark_seed,
                                algorithm_seed=algorithm_seed,
                                population_size=self.population_size,
                                num_generations=self.num_generations,
                                base_spec_path=Path(f"scenarios/optimization/{scenario_id}_{backbone}_raw.yaml"),
                            )
                        )
            for benchmark_seed in self.benchmark_seeds:
                for algorithm_seed in self.algorithm_seeds:
                    leaves.append(
                        MatrixLeaf(
                            matrix_id=self.matrix_id,
                            block_id="M2_nsga2_union_512eval",
                            scenario_id=scenario_id,
                            method_id="nsga2_union",
                            algorithm_family="genetic",
                            algorithm_backbone="nsga2",
                            mode="union",
                            llm_profile=None,
                            benchmark_seed=benchmark_seed,
                            algorithm_seed=algorithm_seed,
                            population_size=self.population_size,
                            num_generations=self.num_generations,
                            base_spec_path=Path(f"scenarios/optimization/{scenario_id}_union.yaml"),
                        )
                    )
            for profile_index, llm_profile in enumerate(self.llm_profiles):
                block_letter = chr(ord("a") + profile_index)
                block_id = f"M3{block_letter}_llm_{llm_profile}_512eval"
                for benchmark_seed in self.benchmark_seeds:
                    for algorithm_seed in self.algorithm_seeds:
                        leaves.append(
                            MatrixLeaf(
                                matrix_id=self.matrix_id,
                                block_id=block_id,
                                scenario_id=scenario_id,
                                method_id=f"nsga2_llm_{llm_profile}",
                                algorithm_family="genetic",
                                algorithm_backbone="nsga2",
                                mode="llm",
                                llm_profile=llm_profile,
                                benchmark_seed=benchmark_seed,
                                algorithm_seed=algorithm_seed,
                                population_size=self.population_size,
                                num_generations=self.num_generations,
                                base_spec_path=Path(f"scenarios/optimization/{scenario_id}_llm.yaml"),
                            )
                        )
        return leaves
```

Create `optimizers/matrix/__init__.py`:

```python
from optimizers.matrix.config import build_s5_s7_512eval_matrix
from optimizers.matrix.models import MatrixConfig, MatrixLeaf, ResourceCap

__all__ = ["MatrixConfig", "MatrixLeaf", "ResourceCap", "build_s5_s7_512eval_matrix"]
```

- [ ] **Step 4: 实现内置配置**

Create `optimizers/matrix/config.py`:

```python
from __future__ import annotations

from optimizers.matrix.models import MatrixConfig, ResourceCap


def build_s5_s7_512eval_matrix() -> MatrixConfig:
    return MatrixConfig(
        matrix_id="s5_s7_512eval",
        scenarios=("s5_aggressive15", "s6_aggressive20", "s7_aggressive25"),
        benchmark_seeds=(11, 17, 23),
        algorithm_seeds=(101, 102, 103),
        population_size=32,
        num_generations=16,
        llm_profiles=(
            "gpt_5_4",
            "qwen3_6_plus",
            "glm_5",
            "minimax_m2_5",
            "deepseek_v4_flash",
            "gemma4",
        ),
        resource_caps={
            "raw": ResourceCap(evaluation_workers=8, concurrent_runs=80),
            "union": ResourceCap(evaluation_workers=8, concurrent_runs=60),
            "external_llm": ResourceCap(evaluation_workers=3, concurrent_runs=20),
            "gemma4": ResourceCap(evaluation_workers=3, concurrent_runs=8),
        },
    )
```

- [ ] **Step 5: 运行测试确认通过**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_matrix_config.py
```

Expected: PASS。

---

## Task 4：实现 per-leaf spec snapshot 生成

**Files:**
- Create: `optimizers/matrix/spec_snapshots.py`
- Test: `tests/optimizers/test_matrix_spec_snapshots.py`

- [ ] **Step 1: 写失败测试**

Create `tests/optimizers/test_matrix_spec_snapshots.py`:

```python
from pathlib import Path

import yaml

from optimizers.matrix.config import build_s5_s7_512eval_matrix
from optimizers.matrix.spec_snapshots import write_leaf_spec_snapshot


def test_write_leaf_spec_snapshot_overrides_seed_budget_and_profile(tmp_path: Path) -> None:
    matrix = build_s5_s7_512eval_matrix()
    leaf = next(item for item in matrix.expand_leaves() if item.method_id == "nsga2_llm_gpt_5_4" and item.scenario_id == "s5_aggressive15")

    snapshot = write_leaf_spec_snapshot(leaf, tmp_path)
    payload = yaml.safe_load(snapshot.read_text(encoding="utf-8"))

    assert snapshot.name == "s5_aggressive15__nsga2_llm_gpt_5_4__b11__a101.yaml"
    assert payload["benchmark_source"]["seed"] == 11
    assert payload["algorithm"]["seed"] == 101
    assert payload["algorithm"]["population_size"] == 32
    assert payload["algorithm"]["num_generations"] == 16
    assert payload["operator_control"]["controller"] == "llm"
    assert payload["operator_control"]["controller_parameters"]["provider_profile"] == "gpt_5_4"
    assert payload["spec_meta"]["spec_id"] == "s5_aggressive15_nsga2_llm_gpt_5_4_b11_a101"


def test_write_leaf_spec_snapshot_keeps_raw_without_operator_control(tmp_path: Path) -> None:
    matrix = build_s5_s7_512eval_matrix()
    leaf = next(item for item in matrix.expand_leaves() if item.method_id == "spea2_raw" and item.scenario_id == "s6_aggressive20")

    snapshot = write_leaf_spec_snapshot(leaf, tmp_path)
    payload = yaml.safe_load(snapshot.read_text(encoding="utf-8"))

    assert payload["algorithm"]["family"] == "genetic"
    assert payload["algorithm"]["backbone"] == "spea2"
    assert payload["algorithm"]["mode"] == "raw"
    assert payload["algorithm"]["seed"] == 101
    assert "operator_control" not in payload
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_matrix_spec_snapshots.py
```

Expected: FAIL。

- [ ] **Step 3: 实现 snapshot writer**

Create `optimizers/matrix/spec_snapshots.py`:

```python
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from optimizers.io import load_optimization_spec
from optimizers.matrix.models import MatrixLeaf


def write_leaf_spec_snapshot(leaf: MatrixLeaf, snapshot_root: str | Path) -> Path:
    payload = load_optimization_spec(leaf.base_spec_path).to_dict()
    snapshot_payload = _leaf_payload(leaf, payload)
    snapshot_dir = Path(snapshot_root) / leaf.block_id / "specs"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshot_dir / _snapshot_filename(leaf)
    snapshot_path.write_text(yaml.safe_dump(snapshot_payload, sort_keys=False), encoding="utf-8")
    return snapshot_path


def _leaf_payload(leaf: MatrixLeaf, payload: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(payload)
    result["spec_meta"]["spec_id"] = _snapshot_spec_id(leaf)
    result["benchmark_source"]["seed"] = int(leaf.benchmark_seed)
    result["algorithm"]["family"] = leaf.algorithm_family
    result["algorithm"]["backbone"] = leaf.algorithm_backbone
    result["algorithm"]["mode"] = "union" if leaf.mode == "llm" else leaf.mode
    result["algorithm"]["seed"] = int(leaf.algorithm_seed)
    result["algorithm"]["population_size"] = int(leaf.population_size)
    result["algorithm"]["num_generations"] = int(leaf.num_generations)
    if leaf.mode == "llm":
        operator_control = result.setdefault("operator_control", {})
        controller_parameters = operator_control.setdefault("controller_parameters", {})
        controller_parameters["provider_profile"] = str(leaf.llm_profile)
    else:
        result.pop("operator_control", None)
    return result


def _snapshot_filename(leaf: MatrixLeaf) -> str:
    return f"{leaf.scenario_id}__{leaf.method_id}__b{leaf.benchmark_seed}__a{leaf.algorithm_seed}.yaml"


def _snapshot_spec_id(leaf: MatrixLeaf) -> str:
    return f"{leaf.scenario_id}_{leaf.method_id}_b{leaf.benchmark_seed}_a{leaf.algorithm_seed}"
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_matrix_spec_snapshots.py
```

Expected: PASS。

---

## Task 5：实现 run index、状态和 retry attempt 管理

**Files:**
- Create: `optimizers/matrix/index.py`
- Test: `tests/optimizers/test_matrix_index.py`

- [ ] **Step 1: 写失败测试**

Create `tests/optimizers/test_matrix_index.py`:

```python
from pathlib import Path

from optimizers.matrix.config import build_s5_s7_512eval_matrix
from optimizers.matrix.index import build_initial_index_rows, failed_retry_rows, write_run_index, read_run_index


def test_run_index_round_trip(tmp_path: Path) -> None:
    matrix = build_s5_s7_512eval_matrix()
    rows = build_initial_index_rows(matrix.expand_leaves()[:2], matrix_root=tmp_path)
    index_path = write_run_index(tmp_path / "run_index.csv", rows)

    loaded = read_run_index(index_path)

    assert len(loaded) == 2
    assert loaded[0]["matrix_id"] == "s5_s7_512eval"
    assert loaded[0]["attempt"] == "1"
    assert loaded[0]["status"] == "pending"
    assert loaded[0]["nominal_budget"] == "512"


def test_failed_retry_rows_create_attempt_two_only_for_failed_statuses(tmp_path: Path) -> None:
    matrix = build_s5_s7_512eval_matrix()
    rows = build_initial_index_rows(matrix.expand_leaves()[:3], matrix_root=tmp_path)
    rows[0]["status"] = "completed"
    rows[1]["status"] = "failed"
    rows[2]["status"] = "render_failed"

    retries = failed_retry_rows(rows)

    assert [row["attempt"] for row in retries] == ["2", "2"]
    assert [row["status"] for row in retries] == ["pending", "pending"]
    assert [row["previous_attempt"] for row in retries] == ["1", "1"]
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_matrix_index.py
```

Expected: FAIL。

- [ ] **Step 3: 实现 index helpers**

Create `optimizers/matrix/index.py`:

```python
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from optimizers.matrix.models import MatrixLeaf

INDEX_COLUMNS = [
    "matrix_id",
    "block_id",
    "scenario_id",
    "method_id",
    "algorithm_family",
    "algorithm_backbone",
    "mode",
    "llm_profile",
    "benchmark_seed",
    "algorithm_seed",
    "population_size",
    "num_generations",
    "nominal_budget",
    "optimization_spec_snapshot",
    "evaluation_spec_path",
    "template_path",
    "run_root",
    "attempt",
    "previous_attempt",
    "status",
    "failure_reason",
    "started_at",
    "finished_at",
    "wall_seconds",
    "actual_evaluations",
    "feasible_count",
    "render_status",
    "trace_status",
    "git_commit",
    "git_dirty",
    "spec_hash",
    "template_hash",
    "evaluation_spec_hash",
    "environment_summary_hash",
]

FAILED_STATUSES = {"failed", "timeout", "missing_artifacts", "render_failed"}


def build_initial_index_rows(leaves: Iterable[MatrixLeaf], *, matrix_root: str | Path) -> list[dict[str, str]]:
    root = Path(matrix_root)
    rows: list[dict[str, str]] = []
    for leaf in leaves:
        run_root = root / leaf.block_id / leaf.scenario_id / leaf.method_id / f"b{leaf.benchmark_seed}" / f"a{leaf.algorithm_seed}" / "attempt-1"
        rows.append(_row_for_leaf(leaf, run_root=run_root, attempt=1, previous_attempt=""))
    return rows


def failed_retry_rows(rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    retries: list[dict[str, str]] = []
    for row in rows:
        if str(row.get("status", "")).strip() not in FAILED_STATUSES:
            continue
        if str(row.get("attempt", "1")) != "1":
            continue
        retry = dict(row)
        retry["attempt"] = "2"
        retry["previous_attempt"] = "1"
        retry["status"] = "pending"
        retry["failure_reason"] = ""
        retry["started_at"] = ""
        retry["finished_at"] = ""
        retry["wall_seconds"] = ""
        retry["actual_evaluations"] = ""
        retry["feasible_count"] = ""
        retry["render_status"] = ""
        retry["trace_status"] = ""
        retry["run_root"] = str(Path(row["run_root"]).parent / "attempt-2")
        retries.append(retry)
    return retries


def write_run_index(path: str | Path, rows: Iterable[dict[str, str]]) -> Path:
    index_path = Path(path)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=INDEX_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: str(row.get(column, "")) for column in INDEX_COLUMNS})
    return index_path


def read_run_index(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _row_for_leaf(leaf: MatrixLeaf, *, run_root: Path, attempt: int, previous_attempt: str) -> dict[str, str]:
    return {
        "matrix_id": leaf.matrix_id,
        "block_id": leaf.block_id,
        "scenario_id": leaf.scenario_id,
        "method_id": leaf.method_id,
        "algorithm_family": leaf.algorithm_family,
        "algorithm_backbone": leaf.algorithm_backbone,
        "mode": leaf.mode,
        "llm_profile": "" if leaf.llm_profile is None else leaf.llm_profile,
        "benchmark_seed": str(leaf.benchmark_seed),
        "algorithm_seed": str(leaf.algorithm_seed),
        "population_size": str(leaf.population_size),
        "num_generations": str(leaf.num_generations),
        "nominal_budget": str(leaf.nominal_budget),
        "optimization_spec_snapshot": "",
        "evaluation_spec_path": "",
        "template_path": "",
        "run_root": str(run_root),
        "attempt": str(attempt),
        "previous_attempt": previous_attempt,
        "status": "pending",
        "failure_reason": "",
        "started_at": "",
        "finished_at": "",
        "wall_seconds": "",
        "actual_evaluations": "",
        "feasible_count": "",
        "render_status": "",
        "trace_status": "",
        "git_commit": "",
        "git_dirty": "",
        "spec_hash": "",
        "template_hash": "",
        "evaluation_spec_hash": "",
        "environment_summary_hash": "",
    }
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_matrix_index.py
```

Expected: PASS。

---

## Task 6：实现 matrix runner 的单 block 执行、外层并发和 resume 骨架

**Files:**
- Create: `optimizers/matrix/leaf_executor.py`
- Create: `optimizers/matrix/runner.py`
- Modify: `optimizers/cli.py`
- Test: `tests/optimizers/test_matrix_runner.py`
- Test: `tests/optimizers/test_optimizer_cli.py`

- [ ] **Step 1: 写失败测试，使用 monkeypatch 避免真实 PDE/LLM 运行**

Create `tests/optimizers/test_matrix_runner.py`:

```python
from pathlib import Path

from optimizers.matrix.config import build_s5_s7_512eval_matrix
from optimizers.matrix.runner import run_matrix_block


def test_run_matrix_block_writes_index_and_invokes_selected_leaves(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_run_leaf(row, *, evaluation_workers: int) -> dict[str, str]:
        calls.append((row["block_id"], str(evaluation_workers)))
        updated = dict(row)
        updated["status"] = "completed"
        updated["actual_evaluations"] = "512"
        updated["feasible_count"] = "9"
        return updated

    monkeypatch.setattr("optimizers.matrix.runner._run_leaf", fake_run_leaf)

    matrix = build_s5_s7_512eval_matrix()
    index_path = run_matrix_block(
        matrix,
        matrix_root=tmp_path,
        block_id="M2_nsga2_union_512eval",
        max_leaves=2,
    )

    assert index_path == tmp_path / "run_index.csv"
    assert calls == [("M2_nsga2_union_512eval", "8"), ("M2_nsga2_union_512eval", "8")]
    text = index_path.read_text(encoding="utf-8")
    assert "completed" in text


def test_run_matrix_block_uses_block_concurrency_cap(tmp_path: Path, monkeypatch) -> None:
    captured = {}

    def fake_run_rows(rows, *, matrix, leaves_by_key, max_workers):
        captured["max_workers"] = max_workers
        return [dict(row, status="completed") for row in rows]

    monkeypatch.setattr("optimizers.matrix.runner._run_rows_concurrently", fake_run_rows)

    matrix = build_s5_s7_512eval_matrix()
    run_matrix_block(matrix, matrix_root=tmp_path, block_id="M1_raw_backbone_512eval", max_leaves=2)

    assert captured["max_workers"] == 80


def test_run_matrix_block_can_generate_attempt_two_for_failed_rows(tmp_path: Path, monkeypatch) -> None:
    from optimizers.matrix.index import build_initial_index_rows, write_run_index

    matrix = build_s5_s7_512eval_matrix()
    rows = build_initial_index_rows(matrix.expand_leaves()[:2], matrix_root=tmp_path)
    rows[0]["status"] = "failed"
    rows[1]["status"] = "completed"
    write_run_index(tmp_path / "run_index.csv", rows)

    monkeypatch.setattr("optimizers.matrix.runner._run_rows_concurrently", lambda rows, **kwargs: [dict(row, status="completed") for row in rows])

    run_matrix_block(matrix, matrix_root=tmp_path, block_id="M4_rerun_failed_512eval")

    text = (tmp_path / "run_index.csv").read_text(encoding="utf-8")
    assert "attempt-2" in text
    assert ",2,1,completed," in text
```

在 `tests/optimizers/test_optimizer_cli.py` 增加 CLI 转发测试：

```python
def test_optimizer_cli_run_benchmark_matrix_forwards_block(tmp_path, monkeypatch):
    import optimizers.cli as cli_module

    captured = {}

    def fake_run_matrix_block(matrix, *, matrix_root, block_id, max_leaves=None):
        captured["matrix_id"] = matrix.matrix_id
        captured["matrix_root"] = str(matrix_root)
        captured["block_id"] = block_id
        captured["max_leaves"] = max_leaves
        return tmp_path / "run_index.csv"

    monkeypatch.setattr(cli_module, "run_matrix_block", fake_run_matrix_block)

    result = cli_module.main(
        [
            "run-benchmark-matrix",
            "--matrix-root",
            str(tmp_path),
            "--block-id",
            "M2_nsga2_union_512eval",
            "--max-leaves",
            "2",
        ]
    )

    assert result == 0
    assert captured == {
        "matrix_id": "s5_s7_512eval",
        "matrix_root": str(tmp_path),
        "block_id": "M2_nsga2_union_512eval",
        "max_leaves": 2,
    }
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_matrix_runner.py tests/optimizers/test_optimizer_cli.py::test_optimizer_cli_run_benchmark_matrix_forwards_block
```

Expected: FAIL。

- [ ] **Step 3: 实现 leaf executor，避免 CLI import cycle**

Create `optimizers/matrix/leaf_executor.py`:

```python
from __future__ import annotations

from pathlib import Path

from llm.openai_compatible.profile_loader import load_provider_profile_overlay


def execute_leaf(row: dict[str, str], *, evaluation_workers: int) -> dict[str, str]:
    from optimizers.cli import _run_optimize_benchmark, _temporary_env_overlay

    spec_path = Path(row["optimization_spec_snapshot"])
    output_root = Path(row["run_root"])
    output_root.mkdir(parents=True, exist_ok=True)
    profile = row.get("llm_profile", "")
    if profile:
        overlay = load_provider_profile_overlay(profile)
        with _temporary_env_overlay(overlay):
            _run_optimize_benchmark(
                spec_path,
                output_root,
                evaluation_workers=evaluation_workers,
                skip_render=False,
            )
    else:
        _run_optimize_benchmark(
            spec_path,
            output_root,
            evaluation_workers=evaluation_workers,
            skip_render=False,
        )
    return {"status": "completed"}
```

- [ ] **Step 4: 实现 runner 骨架和外层并发 cap**

Create `optimizers/matrix/runner.py`:

```python
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Iterable

from optimizers.matrix.index import build_initial_index_rows, failed_retry_rows, read_run_index, write_run_index
from optimizers.matrix.leaf_executor import execute_leaf
from optimizers.matrix.models import MatrixConfig, MatrixLeaf
from optimizers.matrix.spec_snapshots import write_leaf_spec_snapshot


def run_matrix_block(
    matrix: MatrixConfig,
    *,
    matrix_root: str | Path,
    block_id: str,
    max_leaves: int | None = None,
) -> Path:
    root = Path(matrix_root)
    index_path = root / "run_index.csv"
    if block_id == "M4_rerun_failed_512eval":
        rows = failed_retry_rows(read_run_index(index_path))
        leaves = _leaves_for_retry_rows(matrix, rows)
    else:
        leaves = [leaf for leaf in matrix.expand_leaves() if leaf.block_id == block_id]
        if max_leaves is not None:
            leaves = leaves[: int(max_leaves)]
        rows = build_initial_index_rows(leaves, matrix_root=root)
    leaves_by_key = {_leaf_key(leaf): leaf for leaf in leaves}
    for row in rows:
        leaf = leaves_by_key[_row_key(row)]
        row["optimization_spec_snapshot"] = str(write_leaf_spec_snapshot(leaf, root))
    completed_rows = _run_rows_concurrently(
        rows,
        matrix=matrix,
        leaves_by_key=leaves_by_key,
        max_workers=_concurrent_runs_for_block(matrix, block_id),
    )
    if block_id == "M4_rerun_failed_512eval" and index_path.exists():
        all_rows = read_run_index(index_path) + completed_rows
    else:
        all_rows = completed_rows
    return write_run_index(index_path, all_rows)


def _run_rows_concurrently(
    rows: list[dict[str, str]],
    *,
    matrix: MatrixConfig,
    leaves_by_key: dict[tuple[str, str, str, str, str], MatrixLeaf],
    max_workers: int,
) -> list[dict[str, str]]:
    completed: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for row in rows:
            leaf = leaves_by_key[_row_key(row)]
            futures[executor.submit(_run_leaf_with_timing, row, matrix=matrix, leaf=leaf)] = row
        for future in as_completed(futures):
            completed.append(future.result())
    return completed


def _run_leaf_with_timing(row: dict[str, str], *, matrix: MatrixConfig, leaf: MatrixLeaf) -> dict[str, str]:
    updated = dict(row)
    updated["status"] = "running"
    updated["started_at"] = datetime.now().isoformat()
    started = time.monotonic()
    try:
        result = _run_leaf(updated, evaluation_workers=_evaluation_workers_for_leaf(matrix, leaf))
        updated.update(result)
        updated["status"] = result.get("status", "completed")
    except Exception as exc:
        updated["status"] = "failed"
        updated["failure_reason"] = str(exc)
    updated["finished_at"] = datetime.now().isoformat()
    updated["wall_seconds"] = f"{time.monotonic() - started:.6f}"
    return updated


def _run_leaf(row: dict[str, str], *, evaluation_workers: int) -> dict[str, str]:
    return execute_leaf(row, evaluation_workers=evaluation_workers)


def _evaluation_workers_for_leaf(matrix: MatrixConfig, leaf: MatrixLeaf) -> int:
    if leaf.mode == "raw":
        return matrix.resource_caps["raw"].evaluation_workers
    if leaf.mode == "union":
        return matrix.resource_caps["union"].evaluation_workers
    if leaf.llm_profile == "gemma4":
        return matrix.resource_caps["gemma4"].evaluation_workers
    return matrix.resource_caps["external_llm"].evaluation_workers


def _concurrent_runs_for_block(matrix: MatrixConfig, block_id: str) -> int:
    if block_id == "M1_raw_backbone_512eval":
        return matrix.resource_caps["raw"].concurrent_runs
    if block_id == "M2_nsga2_union_512eval":
        return matrix.resource_caps["union"].concurrent_runs
    if "gemma4" in block_id:
        return matrix.resource_caps["gemma4"].concurrent_runs
    if block_id.startswith("M3"):
        return matrix.resource_caps["external_llm"].concurrent_runs
    return 1


def _leaves_for_retry_rows(matrix: MatrixConfig, rows: Iterable[dict[str, str]]) -> list[MatrixLeaf]:
    leaves = {_leaf_key(leaf): leaf for leaf in matrix.expand_leaves()}
    return [leaves[_row_key(row)] for row in rows]


def _leaf_key(leaf: MatrixLeaf) -> tuple[str, str, str, str, str]:
    return (leaf.block_id, leaf.scenario_id, leaf.method_id, str(leaf.benchmark_seed), str(leaf.algorithm_seed))


def _row_key(row: dict[str, str]) -> tuple[str, str, str, str, str]:
    block_id = row["block_id"]
    if block_id == "M4_rerun_failed_512eval":
        block_id = _source_block_for_method(row["method_id"])
    return (block_id, row["scenario_id"], row["method_id"], row["benchmark_seed"], row["algorithm_seed"])


def _source_block_for_method(method_id: str) -> str:
    if method_id.endswith("_raw"):
        return "M1_raw_backbone_512eval"
    if method_id == "nsga2_union":
        return "M2_nsga2_union_512eval"
    if method_id.startswith("nsga2_llm_"):
        profile = method_id.removeprefix("nsga2_llm_")
        letters = {
            "gpt_5_4": "a",
            "qwen3_6_plus": "b",
            "glm_5": "c",
            "minimax_m2_5": "d",
            "deepseek_v4_flash": "e",
            "gemma4": "f",
        }
        return f"M3{letters[profile]}_llm_{profile}_512eval"
    raise ValueError(f"Unknown method_id: {method_id}")
```

- [ ] **Step 5: 增加 CLI 子命令**

Modify `optimizers/cli.py` imports:

```python
from optimizers.matrix.config import build_s5_s7_512eval_matrix
from optimizers.matrix.runner import run_matrix_block
```

在 `build_parser()` 增加：

```python
    matrix_parser = subparsers.add_parser("run-benchmark-matrix")
    matrix_parser.add_argument("--matrix-root", required=True)
    matrix_parser.add_argument("--block-id", required=True)
    matrix_parser.add_argument("--max-leaves", type=_positive_int, default=None)
```

在 `main()` 增加：

```python
    if args.command == "run-benchmark-matrix":
        run_matrix_block(
            build_s5_s7_512eval_matrix(),
            matrix_root=Path(args.matrix_root),
            block_id=args.block_id,
            max_leaves=args.max_leaves,
        )
        return 0
```

- [ ] **Step 6: 运行测试确认通过**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_matrix_runner.py tests/optimizers/test_optimizer_cli.py::test_optimizer_cli_run_benchmark_matrix_forwards_block
```

Expected: PASS。

---

## Task 7：实现 matrix aggregation 统计表

**Files:**
- Create: `optimizers/matrix/aggregate.py`
- Test: `tests/optimizers/test_matrix_aggregate.py`

- [ ] **Step 1: 写失败测试**

Create `tests/optimizers/test_matrix_aggregate.py`:

```python
from optimizers.matrix.aggregate import summarize_outcomes, paired_differences


def test_summarize_outcomes_reports_median_iqr_mean_std_and_feasible_rate() -> None:
    rows = [
        {"scenario_id": "s5", "method_id": "raw", "best_temperature_max": "10", "final_hypervolume": "0.1", "feasible": "true"},
        {"scenario_id": "s5", "method_id": "raw", "best_temperature_max": "12", "final_hypervolume": "0.2", "feasible": "true"},
        {"scenario_id": "s5", "method_id": "raw", "best_temperature_max": "14", "final_hypervolume": "0.3", "feasible": "false"},
    ]

    summary = summarize_outcomes(rows, metric="best_temperature_max")

    assert len(summary) == 1
    item = summary[0]
    assert item["scenario_id"] == "s5"
    assert item["method_id"] == "raw"
    assert item["n_runs"] == 3
    assert item["median"] == 12.0
    assert item["q1"] == 11.0
    assert item["q3"] == 13.0
    assert item["mean"] == 12.0
    assert round(item["std"], 6) == 2.0
    assert item["feasible_rate"] == 2 / 3


def test_paired_differences_aggregate_algorithm_seeds_within_benchmark_seed() -> None:
    rows = [
        {"scenario_id": "s5", "method_id": "raw", "benchmark_seed": "11", "algorithm_seed": "101", "best_temperature_max": "10"},
        {"scenario_id": "s5", "method_id": "raw", "benchmark_seed": "11", "algorithm_seed": "102", "best_temperature_max": "12"},
        {"scenario_id": "s5", "method_id": "union", "benchmark_seed": "11", "algorithm_seed": "101", "best_temperature_max": "8"},
        {"scenario_id": "s5", "method_id": "union", "benchmark_seed": "11", "algorithm_seed": "102", "best_temperature_max": "10"},
    ]

    diffs = paired_differences(rows, baseline_method="raw", candidate_method="union", metric="best_temperature_max")

    assert diffs == [
        {
            "scenario_id": "s5",
            "benchmark_seed": "11",
            "baseline_method": "raw",
            "candidate_method": "union",
            "baseline_mean": 11.0,
            "candidate_mean": 9.0,
            "difference": -2.0,
        }
    ]
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_matrix_aggregate.py
```

Expected: FAIL。

- [ ] **Step 3: 实现 aggregation helpers**

Create `optimizers/matrix/aggregate.py`:

```python
from __future__ import annotations

from collections import defaultdict
from statistics import mean, median, stdev
from typing import Iterable

import numpy as np


def summarize_outcomes(rows: Iterable[dict[str, str]], *, metric: str) -> list[dict[str, float | int | str]]:
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[(row["scenario_id"], row["method_id"])].append(row)
    summaries: list[dict[str, float | int | str]] = []
    for (scenario_id, method_id), group_rows in sorted(groups.items()):
        values = [float(row[metric]) for row in group_rows if str(row.get(metric, "")).strip()]
        feasible_values = [_is_true(row.get("feasible", "false")) for row in group_rows]
        if not values:
            continue
        summaries.append(
            {
                "scenario_id": scenario_id,
                "method_id": method_id,
                "metric": metric,
                "n_runs": len(group_rows),
                "median": float(median(values)),
                "q1": float(np.quantile(values, 0.25)),
                "q3": float(np.quantile(values, 0.75)),
                "mean": float(mean(values)),
                "std": float(stdev(values)) if len(values) >= 2 else 0.0,
                "best": float(min(values)),
                "worst": float(max(values)),
                "feasible_count": int(sum(feasible_values)),
                "feasible_rate": float(sum(feasible_values) / max(1, len(group_rows))),
            }
        )
    return summaries


def paired_differences(
    rows: Iterable[dict[str, str]],
    *,
    baseline_method: str,
    candidate_method: str,
    metric: str,
) -> list[dict[str, float | str]]:
    grouped: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for row in rows:
        if row["method_id"] not in {baseline_method, candidate_method}:
            continue
        value = str(row.get(metric, "")).strip()
        if not value:
            continue
        key = (row["scenario_id"], row["benchmark_seed"], row["method_id"])
        grouped[key].append(float(value))
    outputs: list[dict[str, float | str]] = []
    scenario_seed_pairs = sorted({(scenario_id, seed) for scenario_id, seed, _ in grouped})
    for scenario_id, benchmark_seed in scenario_seed_pairs:
        baseline_values = grouped.get((scenario_id, benchmark_seed, baseline_method), [])
        candidate_values = grouped.get((scenario_id, benchmark_seed, candidate_method), [])
        if not baseline_values or not candidate_values:
            continue
        baseline_mean = float(mean(baseline_values))
        candidate_mean = float(mean(candidate_values))
        outputs.append(
            {
                "scenario_id": scenario_id,
                "benchmark_seed": benchmark_seed,
                "baseline_method": baseline_method,
                "candidate_method": candidate_method,
                "baseline_mean": baseline_mean,
                "candidate_mean": candidate_mean,
                "difference": candidate_mean - baseline_mean,
            }
        )
    return outputs


def _is_true(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_matrix_aggregate.py
```

Expected: PASS。

---

## Task 8：实现 matrix-level PNG/PDF figures

**Files:**
- Create: `optimizers/matrix/figures.py`
- Test: `tests/optimizers/test_matrix_figures.py`

- [ ] **Step 1: 写失败测试**

Create `tests/optimizers/test_matrix_figures.py`:

```python
from pathlib import Path

from optimizers.matrix.figures import (
    render_distribution_figure,
    render_failure_stacked_bar,
    render_rank_heatmap,
)


def test_render_distribution_figure_writes_png_and_pdf(tmp_path: Path) -> None:
    rows = [
        {"scenario_id": "s5", "method_id": "raw", "best_temperature_max": "10"},
        {"scenario_id": "s5", "method_id": "raw", "best_temperature_max": "12"},
        {"scenario_id": "s5", "method_id": "union", "best_temperature_max": "9"},
        {"scenario_id": "s5", "method_id": "union", "best_temperature_max": "11"},
    ]

    outputs = render_distribution_figure(rows, metric="best_temperature_max", output_dir=tmp_path)

    assert outputs == [tmp_path / "best_temperature_max_distribution.png", tmp_path / "best_temperature_max_distribution.pdf"]
    assert outputs[0].exists()
    assert outputs[1].exists()


def test_render_rank_heatmap_writes_png_and_pdf(tmp_path: Path) -> None:
    rows = [
        {"scenario_id": "s5", "method_id": "raw", "rank": "2"},
        {"scenario_id": "s5", "method_id": "union", "rank": "1"},
        {"scenario_id": "s6", "method_id": "raw", "rank": "1"},
        {"scenario_id": "s6", "method_id": "union", "rank": "2"},
    ]

    outputs = render_rank_heatmap(rows, output_dir=tmp_path)

    assert outputs == [tmp_path / "rank_heatmap.png", tmp_path / "rank_heatmap.pdf"]
    assert all(path.exists() for path in outputs)


def test_render_failure_stacked_bar_writes_png_and_pdf(tmp_path: Path) -> None:
    rows = [
        {"method_id": "raw", "status": "completed"},
        {"method_id": "raw", "status": "failed"},
        {"method_id": "union", "status": "timeout"},
    ]

    outputs = render_failure_stacked_bar(rows, output_dir=tmp_path)

    assert outputs == [tmp_path / "failure_stacked_bar.png", tmp_path / "failure_stacked_bar.pdf"]
    assert all(path.exists() for path in outputs)
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_matrix_figures.py
```

Expected: FAIL。

- [ ] **Step 3: 实现 figure renderer**

Create `optimizers/matrix/figures.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


OKABE_ITO = ["#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7", "#000000"]


def render_distribution_figure(rows: Iterable[dict[str, str]], *, metric: str, output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(list(rows))
    frame[metric] = frame[metric].astype(float)

    _set_style()
    fig, ax = plt.subplots(figsize=(7.0, 3.5))
    sns.boxplot(data=frame, x="method_id", y=metric, hue="scenario_id", ax=ax, showfliers=False)
    sns.stripplot(data=frame, x="method_id", y=metric, hue="scenario_id", ax=ax, dodge=True, color="black", alpha=0.45, size=3, legend=False)
    ax.set_xlabel("Method")
    ax.set_ylabel(metric)
    return _save(fig, output_root, f"{metric}_distribution")


def render_rank_heatmap(rows: Iterable[dict[str, str]], *, output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(list(rows))
    frame["rank"] = frame["rank"].astype(float)
    pivot = frame.pivot(index="scenario_id", columns="method_id", values="rank")

    _set_style()
    fig, ax = plt.subplots(figsize=(6.5, 3.0))
    sns.heatmap(pivot, annot=True, fmt=".1f", cmap="viridis_r", cbar_kws={"label": "Rank"}, ax=ax)
    ax.set_xlabel("Method")
    ax.set_ylabel("Scenario")
    return _save(fig, output_root, "rank_heatmap")


def render_failure_stacked_bar(rows: Iterable[dict[str, str]], *, output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(list(rows))
    counts = frame.groupby(["method_id", "status"]).size().unstack(fill_value=0)

    _set_style()
    fig, ax = plt.subplots(figsize=(7.0, 3.5))
    counts.plot(kind="bar", stacked=True, color=OKABE_ITO[: len(counts.columns)], ax=ax)
    ax.set_xlabel("Method")
    ax.set_ylabel("Run count")
    return _save(fig, output_root, "failure_stacked_bar")


def _set_style() -> None:
    sns.set_theme(style="ticks", context="paper", font_scale=1.05)
    sns.set_palette(OKABE_ITO)


def _save(fig, output_root: Path, stem: str) -> list[Path]:
    sns.despine(fig=fig)
    fig.tight_layout()
    png_path = output_root / f"{stem}.png"
    pdf_path = output_root / f"{stem}.pdf"
    fig.savefig(png_path, dpi=300)
    fig.savefig(pdf_path)
    plt.close(fig)
    return [png_path, pdf_path]
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_matrix_figures.py
```

Expected: PASS。

---

## Task 9：实现 representative run 选择、Pareto knee 选择和关键 compare-runs 规划

**Files:**
- Create: `optimizers/matrix/representatives.py`
- Test: `tests/optimizers/test_matrix_representatives.py`

- [ ] **Step 1: 写失败测试**

Create `tests/optimizers/test_matrix_representatives.py`:

```python
from optimizers.matrix.representatives import plan_compare_bundles, select_best_hv_representatives, select_knee_point


def test_select_best_hv_representatives_picks_best_successful_run_per_cell() -> None:
    rows = [
        {"scenario_id": "s5", "method_id": "raw", "status": "completed", "final_hypervolume": "0.2", "run_root": "run-a"},
        {"scenario_id": "s5", "method_id": "raw", "status": "completed", "final_hypervolume": "0.5", "run_root": "run-b"},
        {"scenario_id": "s5", "method_id": "raw", "status": "failed", "final_hypervolume": "0.9", "run_root": "run-c"},
        {"scenario_id": "s5", "method_id": "union", "status": "completed", "final_hypervolume": "0.4", "run_root": "run-d"},
    ]

    selected = select_best_hv_representatives(rows)

    assert selected == [
        {"scenario_id": "s5", "method_id": "raw", "run_root": "run-b", "final_hypervolume": 0.5},
        {"scenario_id": "s5", "method_id": "union", "run_root": "run-d", "final_hypervolume": 0.4},
    ]


def test_select_knee_point_picks_point_nearest_ideal_after_minmax_scaling() -> None:
    points = [
        {"candidate_id": "a", "temperature_max": "100", "gradient_rms": "50"},
        {"candidate_id": "b", "temperature_max": "80", "gradient_rms": "80"},
        {"candidate_id": "c", "temperature_max": "60", "gradient_rms": "120"},
    ]

    assert select_knee_point(points) == "b"


def test_plan_compare_bundles_pairs_key_methods_within_scenario() -> None:
    representatives = [
        {"scenario_id": "s5", "method_id": "nsga2_raw", "run_root": "raw"},
        {"scenario_id": "s5", "method_id": "nsga2_union", "run_root": "union"},
        {"scenario_id": "s5", "method_id": "nsga2_llm_gpt_5_4", "run_root": "llm"},
    ]

    plans = plan_compare_bundles(representatives)

    assert plans == [
        {"scenario_id": "s5", "baseline_run": "raw", "candidate_run": "union", "compare_id": "s5__nsga2_raw__vs__nsga2_union"},
        {"scenario_id": "s5", "baseline_run": "union", "candidate_run": "llm", "compare_id": "s5__nsga2_union__vs__nsga2_llm_gpt_5_4"},
    ]
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_matrix_representatives.py
```

Expected: FAIL。

- [ ] **Step 3: 实现代表 run、knee point 和 compare bundle 规划**

Create `optimizers/matrix/representatives.py`:

```python
from __future__ import annotations

from collections import defaultdict
from math import sqrt
from typing import Iterable


def select_best_hv_representatives(rows: Iterable[dict[str, str]]) -> list[dict[str, float | str]]:
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("status") != "completed":
            continue
        if not str(row.get("final_hypervolume", "")).strip():
            continue
        groups[(row["scenario_id"], row["method_id"])].append(row)

    selected: list[dict[str, float | str]] = []
    for (scenario_id, method_id), group_rows in sorted(groups.items()):
        best = max(group_rows, key=lambda row: float(row["final_hypervolume"]))
        selected.append(
            {
                "scenario_id": scenario_id,
                "method_id": method_id,
                "run_root": best["run_root"],
                "final_hypervolume": float(best["final_hypervolume"]),
            }
        )
    return selected


def select_knee_point(points: Iterable[dict[str, str]]) -> str:
    candidates = list(points)
    temps = [float(point["temperature_max"]) for point in candidates]
    grads = [float(point["gradient_rms"]) for point in candidates]
    temp_min, temp_max = min(temps), max(temps)
    grad_min, grad_max = min(grads), max(grads)

    def score(point: dict[str, str]) -> float:
        temp = _scale(float(point["temperature_max"]), temp_min, temp_max)
        grad = _scale(float(point["gradient_rms"]), grad_min, grad_max)
        return sqrt(temp * temp + grad * grad)

    return str(min(candidates, key=score)["candidate_id"])


def plan_compare_bundles(representatives: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    by_scenario: dict[str, dict[str, str]] = defaultdict(dict)
    for row in representatives:
        by_scenario[row["scenario_id"]][row["method_id"]] = row["run_root"]
    plans: list[dict[str, str]] = []
    for scenario_id, methods in sorted(by_scenario.items()):
        pairs = [("nsga2_raw", "nsga2_union")]
        pairs.extend(("nsga2_union", method_id) for method_id in sorted(methods) if method_id.startswith("nsga2_llm_"))
        for baseline, candidate in pairs:
            if baseline not in methods or candidate not in methods:
                continue
            plans.append(
                {
                    "scenario_id": scenario_id,
                    "baseline_run": methods[baseline],
                    "candidate_run": methods[candidate],
                    "compare_id": f"{scenario_id}__{baseline}__vs__{candidate}",
                }
            )
    return plans


def _scale(value: float, minimum: float, maximum: float) -> float:
    if maximum == minimum:
        return 0.0
    return (value - minimum) / (maximum - minimum)
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_matrix_representatives.py
```

Expected: PASS。

---

## Task 10：增加 matrix aggregation CLI

**Files:**
- Modify: `optimizers/cli.py`
- Test: `tests/optimizers/test_optimizer_cli.py`

- [ ] **Step 1: 写失败测试**

在 `tests/optimizers/test_optimizer_cli.py` 增加：

```python
def test_optimizer_cli_aggregate_benchmark_matrix_forwards_paths(tmp_path, monkeypatch):
    import optimizers.cli as cli_module

    captured = {}

    def fake_aggregate_matrix(index_path, *, output_root):
        captured["index_path"] = str(index_path)
        captured["output_root"] = str(output_root)
        return [tmp_path / "summary.csv"]

    monkeypatch.setattr(cli_module, "aggregate_matrix", fake_aggregate_matrix)

    result = cli_module.main(
        [
            "aggregate-benchmark-matrix",
            "--run-index",
            str(tmp_path / "run_index.csv"),
            "--output-root",
            str(tmp_path / "aggregate"),
        ]
    )

    assert result == 0
    assert captured == {
        "index_path": str(tmp_path / "run_index.csv"),
        "output_root": str(tmp_path / "aggregate"),
    }
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_optimizer_cli.py::test_optimizer_cli_aggregate_benchmark_matrix_forwards_paths
```

Expected: FAIL。

- [ ] **Step 3: 在 aggregate.py 增加文件级聚合入口**

Append to `optimizers/matrix/aggregate.py`:

```python
from pathlib import Path
import csv


def aggregate_matrix(index_path: str | Path, *, output_root: str | Path) -> list[Path]:
    from optimizers.matrix.index import read_run_index

    rows = read_run_index(index_path)
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for metric in ("best_temperature_max", "best_gradient_rms", "final_hypervolume"):
        summary_rows = summarize_outcomes(rows, metric=metric)
        output = root / f"{metric}_summary.csv"
        _write_dict_rows(output, summary_rows)
        outputs.append(output)
    return outputs


def _write_dict_rows(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("\n", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
```

- [ ] **Step 4: 增加 CLI 子命令**

Modify `optimizers/cli.py` imports:

```python
from optimizers.matrix.aggregate import aggregate_matrix
```

在 `build_parser()` 增加：

```python
    matrix_aggregate_parser = subparsers.add_parser("aggregate-benchmark-matrix")
    matrix_aggregate_parser.add_argument("--run-index", required=True)
    matrix_aggregate_parser.add_argument("--output-root", required=True)
```

在 `main()` 增加：

```python
    if args.command == "aggregate-benchmark-matrix":
        aggregate_matrix(Path(args.run_index), output_root=Path(args.output_root))
        return 0
```

- [ ] **Step 5: 运行测试确认通过**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_optimizer_cli.py::test_optimizer_cli_aggregate_benchmark_matrix_forwards_paths
```

Expected: PASS。

---

## Task 11：同步 CLAUDE.md / AGENTS.md 命令说明

**Files:**
- Modify: `CLAUDE.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: 在两个文件中加入 matrix 命令说明**

在 preferred commands 或 optimizer 命令附近加入：

```markdown
Run S5-S7 512eval matrix block:
```bash
conda run -n msfenicsx python -m optimizers.cli run-benchmark-matrix --matrix-root ./scenario_runs/matrix_512eval_s5_s7 --block-id M1_raw_backbone_512eval
```

Aggregate S5-S7 512eval matrix:
```bash
conda run -n msfenicsx python -m optimizers.cli aggregate-benchmark-matrix --run-index ./scenario_runs/matrix_512eval_s5_s7/run_index.csv --output-root ./scenario_runs/matrix_512eval_s5_s7/aggregate
```
```

- [ ] **Step 2: 检查文档中保留中文写作规则**

Run:

```bash
grep -n "Writing Language\|Simplified Chinese\|run-benchmark-matrix\|aggregate-benchmark-matrix" CLAUDE.md AGENTS.md
```

Expected: 输出两个文件中的中文写作规则和 matrix 命令。

---

## Task 12：最终聚焦验证

**Files:**
- Test: `tests/optimizers/test_matrix_specs.py`
- Test: `tests/optimizers/test_matrix_config.py`
- Test: `tests/optimizers/test_matrix_spec_snapshots.py`
- Test: `tests/optimizers/test_matrix_index.py`
- Test: `tests/optimizers/test_matrix_runner.py`
- Test: `tests/optimizers/test_matrix_aggregate.py`
- Test: `tests/optimizers/test_matrix_figures.py`
- Test: `tests/optimizers/test_matrix_representatives.py`

- [ ] **Step 1: 运行所有新增矩阵聚焦测试**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_matrix_specs.py tests/optimizers/test_matrix_config.py tests/optimizers/test_matrix_spec_snapshots.py tests/optimizers/test_matrix_index.py tests/optimizers/test_matrix_runner.py tests/optimizers/test_matrix_aggregate.py tests/optimizers/test_matrix_figures.py tests/optimizers/test_matrix_representatives.py
```

Expected: PASS。

- [ ] **Step 2: 运行 CLI 相关聚焦测试**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_optimizer_cli.py::test_optimizer_cli_run_benchmark_matrix_forwards_block tests/optimizers/test_optimizer_cli.py::test_optimizer_cli_aggregate_benchmark_matrix_forwards_paths
```

Expected: PASS。

- [ ] **Step 3: 运行 LLM profile 聚焦测试**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v tests/optimizers/test_llm_client.py::test_matrix_llm_profiles_include_gpt_5_4_alias
```

Expected: PASS。

- [ ] **Step 4: 检查不运行全仓测试**

本计划只要求上述聚焦测试。若实现过程中修改了 shared optimizer contracts 或 artifact schema，再停下询问是否扩大验证范围。

---

## 执行备注

- 本计划不包含自动 commit 步骤；只有在用户明确要求提交时才创建 git commit。
- 大矩阵正式运行前应先执行 `M0_pilot_512eval` 的功能 pilot 和资源 pilot。
- 正式运行建议 clean git working tree，但 matrix runner 必须记录 `git_dirty`，不能假设一定 clean。
- Gemma4 初始并发按 4-8 concurrent runs 控制，资源稳定后才提升到 20。
