# Unified Benchmark Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用新的 `run-benchmark` 统一入口替代旧 optimizer run/suite/matrix 命令，支持安全并行 leaf、实时日志、自动 render/LLM 诊断、seed-aware comparison 和 IGD。

**Architecture:** 新增 `optimizers/benchmark_runner/` 包作为 orchestration 层；CLI 只暴露 `run-benchmark`，它把单 leaf args 或 batch YAML 解析为标准 campaign/leaves，再由 subprocess supervisor 启动独立 Python leaf 进程。底层 optimizer drivers、rendering、comparison 和 LLM trace modules 尽量复用，但旧 suite/matrix 入口和代码最终删除。

**Tech Stack:** Python dataclasses、argparse、subprocess、CSV/JSONL/YAML、现有 FEniCSx optimizer drivers、现有 render/comparison/LLM trace helpers、pytest。

---

## File Structure

新增文件：

- `optimizers/benchmark_runner/__init__.py`：导出新 runner 的小型公共 API。
- `optimizers/benchmark_runner/specs.py`：batch YAML / single leaf args 到 `CampaignSpec`、`BenchmarkLeaf` 的解析和校验。
- `optimizers/benchmark_runner/run_events.py`：append+flush 的 `run_events.jsonl` writer 和 summary 事件工具。
- `optimizers/benchmark_runner/leaf_entrypoint.py`：leaf 子进程入口，不由用户直接调用。
- `optimizers/benchmark_runner/supervisor.py`：subprocess 调度、资源 env、`run_index.csv` 状态更新。
- `optimizers/benchmark_runner/postprocess.py`：leaf 结束后的 runtime summary、render、LLM replay/analyze 汇总。
- `optimizers/benchmark_runner/comparisons.py`：campaign 内 by-seed 和 aggregate comparison planner。
- `optimizers/benchmark_runner/igd.py`：2D minimization IGD 和 empirical reference front。
- `scenarios/batches/s5_raw_union_budgeted.yaml`：S5 raw+union 五 seed 正式预算 batch。
- `scenarios/batches/s6_raw_union_budgeted.yaml`：S6 raw+union 五 seed 正式预算 batch。
- `scenarios/batches/s5_s6_raw_union_budgeted.yaml`：S5+S6 raw+union 正式预算组合 batch。
- `tests/optimizers/test_benchmark_runner_specs.py`：spec 展开和 seed/budget 校验。
- `tests/optimizers/test_benchmark_runner_supervisor.py`：subprocess supervisor 和 env 策略。
- `tests/optimizers/test_benchmark_runner_run_events.py`：JSONL streaming writer。
- `tests/optimizers/test_benchmark_runner_postprocess.py`：runtime/LLM summary 和 post-run 调用顺序。
- `tests/optimizers/test_benchmark_runner_comparisons.py`：by-seed/aggregate 比较语义。
- `tests/optimizers/test_benchmark_runner_igd.py`：IGD 指标。
- `tests/optimizers/test_benchmark_runner_cli.py`：新 CLI 命令面。

修改文件：

- `optimizers/cli.py`：删除旧 subcommands 和旧 matrix/suite 顶层导入，只保留 `run-benchmark`。
- `optimizers/artifacts.py`：seed bundle 增加 `summaries/`，避免 runtime summary 写到非标准位置。
- `optimizers/run_manifest.py`：允许写入 `method_id`、`llm_profile`、postprocess timing 和 status。
- `optimizers/llm_summary.py`：新增 seed-level latency/token summary helper。
- `optimizers/comparison_artifacts.py`：支持 `llm:<profile>` / `llm-<profile>` label、IGD summary 字段，以及 common-seed aggregate 的输入。
- `optimizers/analytics/pareto.py`：新增 2D objective normalization 和 IGD helper，或从 `benchmark_runner/igd.py` re-export。
- `README.md`：命令示例改为 `run-benchmark`。
- `AGENTS.md`：把 repository guidance 更新到新入口。

删除文件或目录：

- `optimizers/run_suite.py`
- `optimizers/suite_parallel.py`
- `optimizers/matrix/`
- `tests/optimizers/test_run_suite.py`
- `tests/optimizers/test_suite_parallel.py`
- `tests/optimizers/test_suite_comparisons.py`
- `tests/optimizers/test_matrix_config.py`
- `tests/optimizers/test_matrix_figures.py`
- `tests/optimizers/test_matrix_index.py`
- `tests/optimizers/test_matrix_representatives.py`
- `tests/optimizers/test_matrix_runner.py`
- `tests/optimizers/test_matrix_spec_snapshots.py`
- `tests/optimizers/test_matrix_aggregate.py`

---

### Task 1: Campaign Spec Models And Batch Loader

**Files:**
- Create: `optimizers/benchmark_runner/__init__.py`
- Create: `optimizers/benchmark_runner/specs.py`
- Create: `tests/optimizers/test_benchmark_runner_specs.py`

- [ ] **Step 1: Write failing tests for single-leaf args and batch YAML expansion**

Create `tests/optimizers/test_benchmark_runner_specs.py`:

```python
from pathlib import Path

import yaml

from optimizers.benchmark_runner.specs import (
    build_single_leaf_campaign,
    load_campaigns_from_batch_spec,
)


def test_single_leaf_llm_campaign_derives_method_and_paths(tmp_path: Path) -> None:
    campaign = build_single_leaf_campaign(
        optimization_spec=Path("scenarios/optimization/s5_aggressive15_llm.yaml"),
        mode="llm",
        llm_profile="gpt",
        benchmark_seed=11,
        algorithm_seed=1011,
        population_size=40,
        num_generations=32,
        evaluation_workers=16,
        scenario_runs_root=tmp_path / "scenario_runs",
        campaign_id="s5_budgeted_main",
        compare_with=[tmp_path / "scenario_runs/s5_aggressive15/0508_2300__raw_union"],
    )

    assert campaign.campaign_id == "s5_budgeted_main"
    assert campaign.scenario_runs_root == tmp_path / "scenario_runs"
    assert len(campaign.leaves) == 1
    leaf = campaign.leaves[0]
    assert leaf.method_id == "llm:gpt"
    assert leaf.method_slug == "llm-gpt"
    assert leaf.mode == "llm"
    assert leaf.llm_profile == "gpt"
    assert leaf.benchmark_seed == 11
    assert leaf.algorithm_seed == 1011
    assert leaf.population_size == 40
    assert leaf.num_generations == 32
    assert leaf.evaluation_workers == 16
    assert campaign.compare_with == (tmp_path / "scenario_runs/s5_aggressive15/0508_2300__raw_union",)


def test_batch_spec_expands_methods_by_replicate_seeds(tmp_path: Path) -> None:
    batch_path = tmp_path / "s5_raw_union.yaml"
    batch_path.write_text(
        yaml.safe_dump(
            {
                "campaign_id": "s5_budgeted_main",
                "scenario_runs_root": str(tmp_path / "scenario_runs"),
                "scenario_id": "s5_aggressive15",
                "methods": [
                    {
                        "method_id": "nsga2_raw",
                        "mode": "raw",
                        "optimization_spec": "scenarios/optimization/s5_aggressive15_raw.yaml",
                    },
                    {
                        "method_id": "nsga2_union",
                        "mode": "union",
                        "optimization_spec": "scenarios/optimization/s5_aggressive15_union.yaml",
                    },
                ],
                "replicate_seeds": [11, 17],
                "algorithm_seed_offset": 1000,
                "population_size": 40,
                "num_generations": 32,
                "resource_policy": {
                    "max_concurrent_leaves": 4,
                    "leaf_evaluation_workers": 16,
                },
                "comparison_policy": {"by_seed": True, "aggregate": True},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    campaigns = load_campaigns_from_batch_spec(batch_path)

    assert len(campaigns) == 1
    campaign = campaigns[0]
    assert campaign.scenario_id == "s5_aggressive15"
    assert campaign.resource_policy.max_concurrent_leaves == 4
    assert campaign.resource_policy.leaf_evaluation_workers == 16
    assert [(leaf.method_id, leaf.benchmark_seed, leaf.algorithm_seed) for leaf in campaign.leaves] == [
        ("nsga2_raw", 11, 1011),
        ("nsga2_raw", 17, 1017),
        ("nsga2_union", 11, 1011),
        ("nsga2_union", 17, 1017),
    ]


def test_multi_campaign_batch_wrapper(tmp_path: Path) -> None:
    batch_path = tmp_path / "s5_s6.yaml"
    batch_path.write_text(
        yaml.safe_dump(
            {
                "campaigns": [
                    {
                        "campaign_id": "s5_budgeted_main",
                        "scenario_runs_root": str(tmp_path / "scenario_runs"),
                        "scenario_id": "s5_aggressive15",
                        "methods": [
                            {
                                "method_id": "nsga2_raw",
                                "mode": "raw",
                                "optimization_spec": "scenarios/optimization/s5_aggressive15_raw.yaml",
                            }
                        ],
                        "replicate_seeds": [11],
                        "algorithm_seed_offset": 1000,
                        "population_size": 40,
                        "num_generations": 32,
                    },
                    {
                        "campaign_id": "s6_budgeted_main",
                        "scenario_runs_root": str(tmp_path / "scenario_runs"),
                        "scenario_id": "s6_aggressive20",
                        "methods": [
                            {
                                "method_id": "nsga2_union",
                                "mode": "union",
                                "optimization_spec": "scenarios/optimization/s6_aggressive20_union.yaml",
                            }
                        ],
                        "replicate_seeds": [17],
                        "algorithm_seed_offset": 1000,
                        "population_size": 56,
                        "num_generations": 36,
                    },
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    campaigns = load_campaigns_from_batch_spec(batch_path)

    assert [campaign.scenario_id for campaign in campaigns] == ["s5_aggressive15", "s6_aggressive20"]
    assert [campaign.leaves[0].algorithm_seed for campaign in campaigns] == [1011, 1017]
```

- [ ] **Step 2: Run the new spec tests and verify they fail**

Run:

```bash
conda run -n msfenicsx pytest -v tests/optimizers/test_benchmark_runner_specs.py
```

Expected: FAIL with `ModuleNotFoundError: No module named 'optimizers.benchmark_runner'`.

- [ ] **Step 3: Implement dataclasses and loader**

Create `optimizers/benchmark_runner/__init__.py`:

```python
"""Unified benchmark runner orchestration."""

from optimizers.benchmark_runner.specs import (
    BenchmarkLeaf,
    CampaignSpec,
    ComparisonPolicy,
    ResourcePolicy,
    build_single_leaf_campaign,
    load_campaigns_from_batch_spec,
)

__all__ = [
    "BenchmarkLeaf",
    "CampaignSpec",
    "ComparisonPolicy",
    "ResourcePolicy",
    "build_single_leaf_campaign",
    "load_campaigns_from_batch_spec",
]
```

Create `optimizers/benchmark_runner/specs.py`:

```python
"""Contracts and YAML loading for the unified benchmark runner."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


MODE_ORDER = ("raw", "union", "llm")
DEFAULT_REPLICATE_SEEDS = (11, 17, 23, 29, 31)


@dataclass(frozen=True)
class ResourcePolicy:
    max_concurrent_leaves: int = 4
    leaf_evaluation_workers: int = 16


@dataclass(frozen=True)
class ComparisonPolicy:
    by_seed: bool = True
    aggregate: bool = True


@dataclass(frozen=True)
class BenchmarkLeaf:
    scenario_id: str
    method_id: str
    method_slug: str
    mode: str
    optimization_spec: Path
    benchmark_seed: int
    algorithm_seed: int
    population_size: int
    num_generations: int
    evaluation_workers: int
    llm_profile: str | None = None


@dataclass(frozen=True)
class CampaignSpec:
    campaign_id: str
    scenario_id: str
    scenario_runs_root: Path
    leaves: tuple[BenchmarkLeaf, ...]
    resource_policy: ResourcePolicy = field(default_factory=ResourcePolicy)
    comparison_policy: ComparisonPolicy = field(default_factory=ComparisonPolicy)
    compare_with: tuple[Path, ...] = ()


def build_single_leaf_campaign(
    *,
    optimization_spec: Path,
    mode: str,
    llm_profile: str | None,
    benchmark_seed: int,
    algorithm_seed: int,
    population_size: int,
    num_generations: int,
    evaluation_workers: int,
    scenario_runs_root: Path,
    campaign_id: str | None,
    compare_with: list[Path] | tuple[Path, ...] = (),
) -> CampaignSpec:
    scenario_id = _scenario_id_from_spec_path(Path(optimization_spec))
    method_id = _method_id(mode=mode, llm_profile=llm_profile, explicit_method_id=None, optimization_spec=optimization_spec)
    method_slug = _method_slug(method_id)
    effective_campaign_id = campaign_id or f"{scenario_id}_{method_slug}_seed_{int(benchmark_seed)}"
    leaf = BenchmarkLeaf(
        scenario_id=scenario_id,
        method_id=method_id,
        method_slug=method_slug,
        mode=str(mode),
        optimization_spec=Path(optimization_spec),
        benchmark_seed=int(benchmark_seed),
        algorithm_seed=int(algorithm_seed),
        population_size=int(population_size),
        num_generations=int(num_generations),
        evaluation_workers=int(evaluation_workers),
        llm_profile=None if llm_profile is None else str(llm_profile),
    )
    return CampaignSpec(
        campaign_id=effective_campaign_id,
        scenario_id=scenario_id,
        scenario_runs_root=Path(scenario_runs_root),
        leaves=(leaf,),
        resource_policy=ResourcePolicy(max_concurrent_leaves=1, leaf_evaluation_workers=int(evaluation_workers)),
        compare_with=tuple(Path(path) for path in compare_with),
    )


def load_campaigns_from_batch_spec(path: str | Path) -> list[CampaignSpec]:
    batch_path = Path(path)
    payload = yaml.safe_load(batch_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Batch spec must be a mapping: {batch_path}")
    campaign_payloads = payload.get("campaigns")
    if campaign_payloads is None:
        campaign_payloads = [payload]
    if not isinstance(campaign_payloads, list) or not campaign_payloads:
        raise ValueError("Batch spec campaigns must be a non-empty list.")
    return [_campaign_from_payload(dict(item), base_path=batch_path) for item in campaign_payloads]


def _campaign_from_payload(payload: dict[str, Any], *, base_path: Path) -> CampaignSpec:
    campaign_id = str(payload["campaign_id"])
    scenario_id = str(payload["scenario_id"])
    scenario_runs_root = Path(payload.get("scenario_runs_root", "./scenario_runs"))
    replicate_seeds = [int(seed) for seed in payload.get("replicate_seeds", DEFAULT_REPLICATE_SEEDS)]
    seed_offset = int(payload.get("algorithm_seed_offset", 1000))
    population_size = int(payload["population_size"])
    num_generations = int(payload["num_generations"])
    resource_payload = dict(payload.get("resource_policy", {}))
    resource_policy = ResourcePolicy(
        max_concurrent_leaves=int(resource_payload.get("max_concurrent_leaves", 4)),
        leaf_evaluation_workers=int(resource_payload.get("leaf_evaluation_workers", 16)),
    )
    comparison_payload = dict(payload.get("comparison_policy", {}))
    comparison_policy = ComparisonPolicy(
        by_seed=bool(comparison_payload.get("by_seed", True)),
        aggregate=bool(comparison_payload.get("aggregate", True)),
    )
    leaves: list[BenchmarkLeaf] = []
    for method in payload.get("methods", []):
        method_payload = dict(method)
        mode = str(method_payload["mode"])
        optimization_spec = _resolve_spec_path(base_path, method_payload["optimization_spec"])
        llm_profile = method_payload.get("llm_profile")
        method_id = _method_id(
            mode=mode,
            llm_profile=None if llm_profile is None else str(llm_profile),
            explicit_method_id=method_payload.get("method_id"),
            optimization_spec=optimization_spec,
        )
        for seed in replicate_seeds:
            leaves.append(
                BenchmarkLeaf(
                    scenario_id=scenario_id,
                    method_id=method_id,
                    method_slug=_method_slug(method_id),
                    mode=mode,
                    optimization_spec=optimization_spec,
                    benchmark_seed=int(seed),
                    algorithm_seed=int(seed) + seed_offset,
                    population_size=population_size,
                    num_generations=num_generations,
                    evaluation_workers=resource_policy.leaf_evaluation_workers,
                    llm_profile=None if llm_profile is None else str(llm_profile),
                )
            )
    if not leaves:
        raise ValueError(f"Campaign {campaign_id} must define at least one leaf.")
    return CampaignSpec(
        campaign_id=campaign_id,
        scenario_id=scenario_id,
        scenario_runs_root=scenario_runs_root,
        leaves=tuple(leaves),
        resource_policy=resource_policy,
        comparison_policy=comparison_policy,
        compare_with=tuple(Path(path) for path in payload.get("compare_with", [])),
    )


def _resolve_spec_path(base_path: Path, raw_path: str | Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute() or path.exists():
        return path
    candidate = base_path.resolve().parent / path
    return candidate if candidate.exists() else path


def _scenario_id_from_spec_path(path: Path) -> str:
    name = path.stem
    for suffix in ("_spea2_raw", "_moead_raw", "_raw", "_union", "_llm"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _method_id(
    *,
    mode: str,
    llm_profile: str | None,
    explicit_method_id: Any,
    optimization_spec: Path,
) -> str:
    if explicit_method_id:
        return str(explicit_method_id)
    if mode == "llm":
        return f"llm:{llm_profile or 'default'}"
    stem = Path(optimization_spec).stem
    if stem.endswith("_spea2_raw"):
        return "spea2_raw"
    if stem.endswith("_moead_raw"):
        return "moead_raw"
    if mode == "raw":
        return "nsga2_raw"
    if mode == "union":
        return "nsga2_union"
    raise ValueError(f"Unsupported mode: {mode}")


def _method_slug(method_id: str) -> str:
    return method_id.replace(":", "-").replace("_", "-")
```

- [ ] **Step 4: Run spec tests and verify they pass**

Run:

```bash
conda run -n msfenicsx pytest -v tests/optimizers/test_benchmark_runner_specs.py
```

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

```bash
git add optimizers/benchmark_runner/__init__.py optimizers/benchmark_runner/specs.py tests/optimizers/test_benchmark_runner_specs.py
git commit -m "feat: add benchmark runner campaign specs"
```

---

### Task 2: Streaming Run Events

**Files:**
- Create: `optimizers/benchmark_runner/run_events.py`
- Create: `tests/optimizers/test_benchmark_runner_run_events.py`

- [ ] **Step 1: Write failing tests for append+flush JSONL run events**

Create `tests/optimizers/test_benchmark_runner_run_events.py`:

```python
import json
from pathlib import Path

from optimizers.benchmark_runner.run_events import RunEventWriter, append_summary_event


def test_run_event_writer_appends_jsonl_immediately(tmp_path: Path) -> None:
    path = tmp_path / "seed-11" / "traces" / "run_events.jsonl"

    with RunEventWriter(path) as writer:
        writer.write(
            "leaf_started",
            scenario_id="s5_aggressive15",
            method_id="nsga2_raw",
            mode="raw",
            llm_profile=None,
            seed=11,
            message="leaf started",
            metrics={"evaluations_total": 0},
        )
        assert path.exists()
        first_line = path.read_text(encoding="utf-8").strip()
        assert json.loads(first_line)["event"] == "leaf_started"

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["scenario_id"] == "s5_aggressive15"
    assert rows[0]["seed"] == 11
    assert rows[0]["metrics"] == {"evaluations_total": 0}


def test_append_summary_event_adds_terminal_payload(tmp_path: Path) -> None:
    path = tmp_path / "traces" / "run_events.jsonl"
    append_summary_event(
        path,
        event="llm_runtime_summary",
        scenario_id="s5_aggressive15",
        method_id="llm:gpt",
        mode="llm",
        llm_profile="gpt",
        seed=11,
        summary={"llm_request_count": 3, "tokens_total": 42},
    )

    row = json.loads(path.read_text(encoding="utf-8"))
    assert row["event"] == "llm_runtime_summary"
    assert row["metrics"]["llm_request_count"] == 3
    assert row["metrics"]["tokens_total"] == 42
```

- [ ] **Step 2: Run run-event tests and verify they fail**

Run:

```bash
conda run -n msfenicsx pytest -v tests/optimizers/test_benchmark_runner_run_events.py
```

Expected: FAIL with missing `RunEventWriter`.

- [ ] **Step 3: Implement run event writer**

Create `optimizers/benchmark_runner/run_events.py`:

```python
"""Streaming run event JSONL helpers."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO


class RunEventWriter:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._handle: TextIO | None = None
        self._started = time.monotonic()

    def __enter__(self) -> "RunEventWriter":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a", encoding="utf-8")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    def write(
        self,
        event: str,
        *,
        scenario_id: str,
        method_id: str,
        mode: str,
        llm_profile: str | None,
        seed: int,
        message: str = "",
        metrics: dict[str, Any] | None = None,
        generation: int | None = None,
    ) -> None:
        if self._handle is None:
            raise RuntimeError("RunEventWriter must be used as a context manager.")
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
            "event": str(event),
            "scenario_id": str(scenario_id),
            "method_id": str(method_id),
            "mode": str(mode),
            "llm_profile": llm_profile,
            "seed": int(seed),
            "elapsed_seconds": float(time.monotonic() - self._started),
            "message": str(message),
            "metrics": dict(metrics or {}),
        }
        if generation is not None:
            payload["generation"] = int(generation)
        self._handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")
        self._handle.flush()


def append_summary_event(
    path: str | Path,
    *,
    event: str,
    scenario_id: str,
    method_id: str,
    mode: str,
    llm_profile: str | None,
    seed: int,
    summary: dict[str, Any],
) -> None:
    with RunEventWriter(path) as writer:
        writer.write(
            event,
            scenario_id=scenario_id,
            method_id=method_id,
            mode=mode,
            llm_profile=llm_profile,
            seed=seed,
            message=event,
            metrics=dict(summary),
        )
```

- [ ] **Step 4: Run run-event tests and verify they pass**

Run:

```bash
conda run -n msfenicsx pytest -v tests/optimizers/test_benchmark_runner_run_events.py
```

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

```bash
git add optimizers/benchmark_runner/run_events.py tests/optimizers/test_benchmark_runner_run_events.py
git commit -m "feat: add benchmark run event logging"
```

---

### Task 3: Subprocess Supervisor

**Files:**
- Create: `optimizers/benchmark_runner/supervisor.py`
- Create: `tests/optimizers/test_benchmark_runner_supervisor.py`

- [ ] **Step 1: Write failing tests for safe env and run_index**

Create `tests/optimizers/test_benchmark_runner_supervisor.py`:

```python
import csv
from pathlib import Path

from optimizers.benchmark_runner.specs import BenchmarkLeaf, CampaignSpec, ResourcePolicy
from optimizers.benchmark_runner.supervisor import (
    LEAF_ENV_DEFAULTS,
    build_leaf_command,
    run_campaign_supervisor,
)


def _leaf() -> BenchmarkLeaf:
    return BenchmarkLeaf(
        scenario_id="s5_aggressive15",
        method_id="nsga2_raw",
        method_slug="nsga2-raw",
        mode="raw",
        optimization_spec=Path("scenarios/optimization/s5_aggressive15_raw.yaml"),
        benchmark_seed=11,
        algorithm_seed=1011,
        population_size=40,
        num_generations=32,
        evaluation_workers=16,
    )


def test_leaf_env_defaults_disable_nested_threading() -> None:
    assert LEAF_ENV_DEFAULTS["PYTHONUNBUFFERED"] == "1"
    assert LEAF_ENV_DEFAULTS["OMP_NUM_THREADS"] == "1"
    assert LEAF_ENV_DEFAULTS["MKL_NUM_THREADS"] == "1"
    assert LEAF_ENV_DEFAULTS["OPENBLAS_NUM_THREADS"] == "1"
    assert LEAF_ENV_DEFAULTS["NUMEXPR_NUM_THREADS"] == "1"
    assert LEAF_ENV_DEFAULTS["MPLBACKEND"] == "Agg"
    assert LEAF_ENV_DEFAULTS["CUDA_VISIBLE_DEVICES"] == ""


def test_build_leaf_command_uses_internal_entrypoint(tmp_path: Path) -> None:
    cmd = build_leaf_command(_leaf(), output_root=tmp_path / "seed-11")

    assert cmd[:3] == ["python", "-m", "optimizers.benchmark_runner.leaf_entrypoint"]
    assert "--optimization-spec" in cmd
    assert "--benchmark-seed" in cmd
    assert "--algorithm-seed" in cmd
    assert "--output-root" in cmd


def test_supervisor_writes_index_without_forking_pool(tmp_path: Path, monkeypatch) -> None:
    calls: list[dict] = []

    class FakeProcess:
        def __init__(self, cmd, env, cwd):
            calls.append({"cmd": cmd, "env": env, "cwd": cwd})
            self.returncode = 0

        def poll(self):
            return self.returncode

        def wait(self):
            return self.returncode

    monkeypatch.setattr("optimizers.benchmark_runner.supervisor.subprocess.Popen", FakeProcess)

    campaign = CampaignSpec(
        campaign_id="s5_budgeted_main",
        scenario_id="s5_aggressive15",
        scenario_runs_root=tmp_path / "scenario_runs",
        leaves=(_leaf(),),
        resource_policy=ResourcePolicy(max_concurrent_leaves=1, leaf_evaluation_workers=16),
    )

    run_root = run_campaign_supervisor(campaign, run_id="0508_2300__raw")

    assert run_root == tmp_path / "scenario_runs" / "s5_aggressive15" / "0508_2300__raw"
    assert len(calls) == 1
    assert calls[0]["env"]["OMP_NUM_THREADS"] == "1"
    rows = list(csv.DictReader((run_root / "run_index.csv").open(encoding="utf-8")))
    assert rows[0]["status"] == "completed"
    assert rows[0]["method_id"] == "nsga2_raw"
    assert rows[0]["benchmark_seed"] == "11"
```

- [ ] **Step 2: Run supervisor tests and verify they fail**

Run:

```bash
conda run -n msfenicsx pytest -v tests/optimizers/test_benchmark_runner_supervisor.py
```

Expected: FAIL with missing `supervisor.py`.

- [ ] **Step 3: Implement supervisor without multiprocessing fork**

Create `optimizers/benchmark_runner/supervisor.py`:

```python
"""Subprocess supervisor for benchmark leaves."""

from __future__ import annotations

import csv
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml

from optimizers.benchmark_runner.specs import BenchmarkLeaf, CampaignSpec


LEAF_ENV_DEFAULTS = {
    "PYTHONUNBUFFERED": "1",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
    "MPLBACKEND": "Agg",
    "CUDA_VISIBLE_DEVICES": "",
}

RUN_INDEX_FIELDS = [
    "campaign_id",
    "scenario_id",
    "method_id",
    "method_slug",
    "mode",
    "llm_profile",
    "benchmark_seed",
    "algorithm_seed",
    "population_size",
    "num_generations",
    "evaluation_workers",
    "status",
    "started_at",
    "finished_at",
    "wall_seconds",
    "output_root",
    "failure_reason",
]


@dataclass(frozen=True)
class LeafExecution:
    leaf: BenchmarkLeaf
    output_root: Path
    process: subprocess.Popen
    started_at: datetime
    monotonic_start: float


def build_leaf_command(leaf: BenchmarkLeaf, *, output_root: Path) -> list[str]:
    cmd = [
        "python",
        "-m",
        "optimizers.benchmark_runner.leaf_entrypoint",
        "--optimization-spec",
        str(leaf.optimization_spec),
        "--mode",
        leaf.mode,
        "--benchmark-seed",
        str(leaf.benchmark_seed),
        "--algorithm-seed",
        str(leaf.algorithm_seed),
        "--population-size",
        str(leaf.population_size),
        "--num-generations",
        str(leaf.num_generations),
        "--evaluation-workers",
        str(leaf.evaluation_workers),
        "--output-root",
        str(output_root),
        "--method-id",
        leaf.method_id,
    ]
    if leaf.llm_profile:
        cmd.extend(["--llm-profile", leaf.llm_profile])
    return cmd


def run_campaign_supervisor(campaign: CampaignSpec, *, run_id: str | None = None) -> Path:
    effective_run_id = run_id or _build_run_id(campaign)
    run_root = campaign.scenario_runs_root / campaign.scenario_id / effective_run_id
    run_root.mkdir(parents=True, exist_ok=True)
    _write_campaign_manifest(campaign, run_root)
    run_index_path = run_root / "run_index.csv"
    _write_run_index_header(run_index_path)

    pending = list(campaign.leaves)
    active: list[LeafExecution] = []
    completed = 0
    while pending or active:
        while pending and len(active) < campaign.resource_policy.max_concurrent_leaves:
            leaf = pending.pop(0)
            output_root = run_root / leaf.method_slug / "seeds" / f"seed-{leaf.benchmark_seed}"
            output_root.mkdir(parents=True, exist_ok=True)
            env = dict(os.environ)
            env.update(LEAF_ENV_DEFAULTS)
            process = subprocess.Popen(build_leaf_command(leaf, output_root=output_root), env=env, cwd=Path.cwd())
            active.append(
                LeafExecution(
                    leaf=leaf,
                    output_root=output_root,
                    process=process,
                    started_at=datetime.now(),
                    monotonic_start=time.monotonic(),
                )
            )
        still_active: list[LeafExecution] = []
        for execution in active:
            return_code = execution.process.poll()
            if return_code is None:
                still_active.append(execution)
                continue
            _append_run_index_row(
                run_index_path,
                campaign=campaign,
                execution=execution,
                status="completed" if return_code == 0 else "failed",
                failure_reason="" if return_code == 0 else f"exit_code={return_code}",
            )
            completed += 1
        active = still_active
        if active:
            time.sleep(0.2)
    return run_root


def _build_run_id(campaign: CampaignSpec) -> str:
    slug = "_".join(_ordered_unique(_run_slug_for_leaf(leaf) for leaf in campaign.leaves))
    return f"{datetime.now():%m%d_%H%M}__{slug}"


def _run_slug_for_leaf(leaf: BenchmarkLeaf) -> str:
    if leaf.method_id == "nsga2_raw":
        return "raw"
    if leaf.method_id == "nsga2_union":
        return "union"
    if leaf.mode == "llm":
        return f"llm-{leaf.llm_profile or 'default'}"
    return leaf.method_slug


def _ordered_unique(values) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value)
        if text not in result:
            result.append(text)
    return result


def _write_campaign_manifest(campaign: CampaignSpec, run_root: Path) -> None:
    payload = {
        "campaign_id": campaign.campaign_id,
        "scenario_id": campaign.scenario_id,
        "resource_policy": {
            "max_concurrent_leaves": campaign.resource_policy.max_concurrent_leaves,
            "leaf_evaluation_workers": campaign.resource_policy.leaf_evaluation_workers,
        },
        "comparison_policy": {
            "by_seed": campaign.comparison_policy.by_seed,
            "aggregate": campaign.comparison_policy.aggregate,
        },
        "compare_with": [str(path) for path in campaign.compare_with],
        "leaf_count": len(campaign.leaves),
    }
    (run_root / "campaign.yaml").write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _write_run_index_header(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        csv.DictWriter(handle, fieldnames=RUN_INDEX_FIELDS).writeheader()


def _append_run_index_row(
    path: Path,
    *,
    campaign: CampaignSpec,
    execution: LeafExecution,
    status: str,
    failure_reason: str,
) -> None:
    wall_seconds = time.monotonic() - execution.monotonic_start
    leaf = execution.leaf
    row = {
        "campaign_id": campaign.campaign_id,
        "scenario_id": leaf.scenario_id,
        "method_id": leaf.method_id,
        "method_slug": leaf.method_slug,
        "mode": leaf.mode,
        "llm_profile": leaf.llm_profile or "",
        "benchmark_seed": leaf.benchmark_seed,
        "algorithm_seed": leaf.algorithm_seed,
        "population_size": leaf.population_size,
        "num_generations": leaf.num_generations,
        "evaluation_workers": leaf.evaluation_workers,
        "status": status,
        "started_at": execution.started_at.isoformat(),
        "finished_at": datetime.now().isoformat(),
        "wall_seconds": f"{wall_seconds:.3f}",
        "output_root": str(execution.output_root),
        "failure_reason": failure_reason,
    }
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RUN_INDEX_FIELDS)
        writer.writerow(row)
```

- [ ] **Step 4: Run supervisor tests and verify they pass**

Run:

```bash
conda run -n msfenicsx pytest -v tests/optimizers/test_benchmark_runner_supervisor.py
```

Expected: PASS.

- [ ] **Step 5: Commit Task 3**

```bash
git add optimizers/benchmark_runner/supervisor.py tests/optimizers/test_benchmark_runner_supervisor.py
git commit -m "feat: add subprocess benchmark supervisor"
```

---

### Task 4: Leaf Entrypoint And Runtime Summary

**Files:**
- Create: `optimizers/benchmark_runner/leaf_entrypoint.py`
- Create: `optimizers/benchmark_runner/postprocess.py`
- Modify: `optimizers/artifacts.py`
- Modify: `optimizers/run_manifest.py`
- Create: `tests/optimizers/test_benchmark_runner_postprocess.py`

- [ ] **Step 1: Write failing tests for summaries directory and runtime summary**

Create `tests/optimizers/test_benchmark_runner_postprocess.py`:

```python
import json
from pathlib import Path

from optimizers.benchmark_runner.postprocess import (
    build_runtime_summary,
    write_runtime_summary,
)


def test_runtime_summary_counts_history_and_wall_time(tmp_path: Path) -> None:
    history = [
        {"solver_skipped": True, "feasible": False, "timing": {"solve_ms": 0}},
        {"solver_skipped": False, "feasible": True, "timing": {"solve_ms": 1200}},
        {"solver_skipped": False, "feasible": False, "timing": {"solve_ms": 800}},
    ]

    summary = build_runtime_summary(
        scenario_id="s5_aggressive15",
        method_id="nsga2_raw",
        mode="raw",
        seed=11,
        population_size=40,
        num_generations=32,
        run_wall_seconds=10.0,
        optimizer_wall_seconds=8.0,
        baseline_wall_seconds=1.0,
        postprocess_wall_seconds=1.0,
        render_wall_seconds=0.5,
        history=history,
    )

    assert summary["run_wall_seconds"] == 10.0
    assert summary["evaluation_count"] == 3
    assert summary["pde_attempt_count"] == 2
    assert summary["cheap_skip_count"] == 1
    assert summary["feasible_count"] == 1
    assert summary["pde_wall_seconds_total"] == 2.0


def test_write_runtime_summary_writes_summaries_dir_and_run_event(tmp_path: Path) -> None:
    seed_root = tmp_path / "seed-11"
    summary = {"scenario_id": "s5_aggressive15", "method_id": "nsga2_raw", "mode": "raw", "seed": 11}

    write_runtime_summary(seed_root, summary)

    assert (seed_root / "summaries" / "runtime_summary.json").exists()
    assert (seed_root / "traces" / "run_events.jsonl").exists()
    payload = json.loads((seed_root / "summaries" / "runtime_summary.json").read_text(encoding="utf-8"))
    assert payload["method_id"] == "nsga2_raw"
```

- [ ] **Step 2: Run postprocess tests and verify they fail**

Run:

```bash
conda run -n msfenicsx pytest -v tests/optimizers/test_benchmark_runner_postprocess.py
```

Expected: FAIL with missing `postprocess.py`.

- [ ] **Step 3: Add `summaries/` to optimizer seed bundle directories**

Modify `optimizers/artifacts.py`:

```python
def _seed_bundle_directories() -> dict[str, str]:
    return {
        "analytics": "analytics",
        "figures": "figures",
        "representatives": "representatives",
        "summaries": "summaries",
        "tables": "tables",
        "traces": "traces",
    }
```

- [ ] **Step 4: Extend `run_manifest.write_run_manifest` without breaking callers**

Modify `optimizers/run_manifest.py` signature and payload:

```python
def write_run_manifest(
    path: Path,
    *,
    mode: str,
    algorithm_family: str | None = None,
    algorithm_backbone: str | None = None,
    benchmark_seed: int,
    algorithm_seed: int,
    optimization_spec_path: str,
    evaluation_spec_path: str,
    population_size: int,
    num_generations: int,
    wall_seconds: float,
    legality_policy_id: str,
    method_id: str | None = None,
    llm_profile: str | None = None,
    status: str = "completed",
    postprocess_wall_seconds: float | None = None,
) -> None:
    ...
    payload = {
        "mode": mode,
        "method_id": method_id or mode,
        "llm_profile": llm_profile,
        "status": status,
        ...
        "timing": {
            "wall_seconds": float(wall_seconds),
            "postprocess_wall_seconds": None if postprocess_wall_seconds is None else float(postprocess_wall_seconds),
        },
    }
```

Keep existing positional and keyword callers valid by appending only optional keyword parameters.

- [ ] **Step 5: Implement runtime summary helpers**

Create `optimizers/benchmark_runner/postprocess.py`:

```python
"""Post-run rendering, diagnostics, and summary helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from optimizers.benchmark_runner.run_events import append_summary_event


def build_runtime_summary(
    *,
    scenario_id: str,
    method_id: str,
    mode: str,
    seed: int,
    population_size: int,
    num_generations: int,
    run_wall_seconds: float,
    optimizer_wall_seconds: float,
    baseline_wall_seconds: float,
    postprocess_wall_seconds: float,
    render_wall_seconds: float,
    history: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    pde_attempt_count = 0
    cheap_skip_count = 0
    feasible_count = 0
    pde_wall_seconds_total = 0.0
    for row in history:
        solver_skipped = bool(row.get("solver_skipped", False))
        if solver_skipped:
            cheap_skip_count += 1
        else:
            pde_attempt_count += 1
        if bool(row.get("feasible", False)):
            feasible_count += 1
        timing = dict(row.get("timing", {}))
        solve_ms = timing.get("solve_ms") or timing.get("pde_ms") or 0.0
        pde_wall_seconds_total += float(solve_ms) / 1000.0
    return {
        "scenario_id": scenario_id,
        "method_id": method_id,
        "mode": mode,
        "seed": int(seed),
        "population_size": int(population_size),
        "num_generations": int(num_generations),
        "nominal_budget": int(population_size) * int(num_generations),
        "run_wall_seconds": float(run_wall_seconds),
        "optimizer_wall_seconds": float(optimizer_wall_seconds),
        "baseline_wall_seconds": float(baseline_wall_seconds),
        "postprocess_wall_seconds": float(postprocess_wall_seconds),
        "render_wall_seconds": float(render_wall_seconds),
        "pde_wall_seconds_total": float(pde_wall_seconds_total),
        "evaluation_count": int(len(history)),
        "pde_attempt_count": int(pde_attempt_count),
        "cheap_skip_count": int(cheap_skip_count),
        "feasible_count": int(feasible_count),
        "failed_evaluation_count": int(sum(1 for row in history if row.get("failure_reason"))),
    }


def write_runtime_summary(seed_root: str | Path, summary: Mapping[str, Any]) -> Path:
    root = Path(seed_root)
    output = root / "summaries" / "runtime_summary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(dict(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    append_summary_event(
        root / "traces" / "run_events.jsonl",
        event="runtime_summary",
        scenario_id=str(summary["scenario_id"]),
        method_id=str(summary["method_id"]),
        mode=str(summary["mode"]),
        llm_profile=summary.get("llm_profile"),
        seed=int(summary["seed"]),
        summary=dict(summary),
    )
    return output
```

- [ ] **Step 6: Implement leaf entrypoint**

Create `optimizers/benchmark_runner/leaf_entrypoint.py` with these responsibilities:

```python
"""Internal subprocess entrypoint for one benchmark leaf."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from evaluation.io import load_spec
from llm.openai_compatible.profile_loader import load_provider_profile_overlay
from optimizers.artifacts import write_optimization_artifacts
from optimizers.benchmark_runner.postprocess import build_runtime_summary, write_runtime_summary
from optimizers.benchmark_runner.run_events import RunEventWriter
from optimizers.cli import apply_algorithm_overrides, _temporary_env_overlay
from optimizers.drivers.raw_driver import run_raw_optimization
from optimizers.drivers.union_driver import run_union_optimization
from optimizers.io import generate_benchmark_case, load_optimization_spec, resolve_evaluation_spec_path
from optimizers.run_manifest import write_run_manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="benchmark-leaf")
    parser.add_argument("--optimization-spec", required=True)
    parser.add_argument("--mode", required=True, choices=["raw", "union", "llm"])
    parser.add_argument("--benchmark-seed", type=int, required=True)
    parser.add_argument("--algorithm-seed", type=int, required=True)
    parser.add_argument("--population-size", type=int, required=True)
    parser.add_argument("--num-generations", type=int, required=True)
    parser.add_argument("--evaluation-workers", type=int, required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--method-id", required=True)
    parser.add_argument("--llm-profile", default=None)
    return parser
```

Inside `main()`, load the optimization spec, override seeds and budgets, write `leaf_started`, run the driver, call `write_optimization_artifacts`, `write_run_manifest`, and `write_runtime_summary`. Task 6 will extend this entrypoint with render and LLM diagnostics. Use `_temporary_env_overlay(load_provider_profile_overlay(profile))` only when `--llm-profile` is set.

The dispatch block must be:

```python
if args.mode == "raw":
    run = run_raw_optimization(
        base_case,
        optimization_spec,
        evaluation_spec,
        spec_path=spec_path,
        evaluation_workers=args.evaluation_workers,
    )
else:
    run = run_union_optimization(
        base_case,
        optimization_spec,
        evaluation_spec,
        spec_path=spec_path,
        evaluation_workers=args.evaluation_workers,
        trace_output_root=output_root,
    )
```

- [ ] **Step 7: Run focused postprocess tests**

Run:

```bash
conda run -n msfenicsx pytest -v tests/optimizers/test_benchmark_runner_postprocess.py tests/optimizers/test_run_manifest.py tests/optimizers/test_artifacts.py
```

Expected: PASS.

- [ ] **Step 8: Commit Task 4**

```bash
git add optimizers/benchmark_runner/leaf_entrypoint.py optimizers/benchmark_runner/postprocess.py optimizers/artifacts.py optimizers/run_manifest.py tests/optimizers/test_benchmark_runner_postprocess.py
git commit -m "feat: add benchmark leaf execution summaries"
```

---

### Task 5: Seed-Level LLM Runtime Summary

**Files:**
- Modify: `optimizers/llm_summary.py`
- Modify: `optimizers/benchmark_runner/postprocess.py`
- Create: `tests/optimizers/test_benchmark_runner_llm_summary.py`

- [ ] **Step 1: Write failing tests for latency and token totals**

Create `tests/optimizers/test_benchmark_runner_llm_summary.py`:

```python
import json
from pathlib import Path

from optimizers.llm_summary import build_seed_llm_runtime_summary


def test_seed_llm_runtime_summary_reports_latency_and_tokens(tmp_path: Path) -> None:
    traces = tmp_path / "traces"
    traces.mkdir()
    (traces / "llm_request_trace.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"decision_id": "d1", "provider": "openai_compatible", "model": "gpt-5.4"}),
                json.dumps({"decision_id": "d2", "provider": "openai_compatible", "model": "gpt-5.4"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (traces / "llm_response_trace.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "decision_id": "d1",
                        "provider": "openai_compatible",
                        "model": "gpt-5.4",
                        "latency_ms": 1000,
                        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                    }
                ),
                json.dumps(
                    {
                        "decision_id": "d2",
                        "provider": "openai_compatible",
                        "model": "gpt-5.4",
                        "latency_ms": 3000,
                        "usage": {"prompt_tokens": 20, "completion_tokens": 7, "total_tokens": 27},
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (traces / "controller_trace.jsonl").write_text(
        json.dumps({"decision_id": "d1", "fallback_used": True}) + "\n",
        encoding="utf-8",
    )

    summary = build_seed_llm_runtime_summary(
        tmp_path,
        scenario_id="s5_aggressive15",
        method_id="llm:gpt",
        mode="llm",
        llm_profile="gpt",
        run_wall_seconds=12.0,
        optimizer_wall_seconds=10.0,
    )

    assert summary["llm_request_count"] == 2
    assert summary["llm_response_count"] == 2
    assert summary["llm_fallback_count"] == 1
    assert summary["llm_latency_seconds_total"] == 4.0
    assert summary["llm_latency_seconds_mean"] == 2.0
    assert summary["llm_latency_seconds_median"] == 2.0
    assert summary["llm_latency_seconds_p95"] == 2.9
    assert summary["llm_latency_seconds_max"] == 3.0
    assert summary["tokens_prompt_total"] == 30
    assert summary["tokens_completion_total"] == 12
    assert summary["tokens_total"] == 42
```

- [ ] **Step 2: Run LLM summary test and verify it fails**

Run:

```bash
conda run -n msfenicsx pytest -v tests/optimizers/test_benchmark_runner_llm_summary.py
```

Expected: FAIL with missing `build_seed_llm_runtime_summary`.

- [ ] **Step 3: Implement `build_seed_llm_runtime_summary`**

Append to `optimizers/llm_summary.py`:

```python
def build_seed_llm_runtime_summary(
    seed_root: str | Path,
    *,
    scenario_id: str,
    method_id: str,
    mode: str,
    llm_profile: str,
    run_wall_seconds: float,
    optimizer_wall_seconds: float,
) -> dict[str, Any]:
    root = Path(seed_root)
    seed = _seed_from_root(root)
    request_rows = load_jsonl_rows(root / "traces" / "llm_request_trace.jsonl")
    response_rows = load_jsonl_rows(root / "traces" / "llm_response_trace.jsonl")
    controller_rows = _load_controller_rows(root)
    latencies = [
        float(row["latency_ms"]) / 1000.0
        for row in response_rows
        if row.get("latency_ms") is not None
    ]
    prompt_total = sum(_usage_int(row, "prompt_tokens") for row in response_rows)
    completion_total = sum(_usage_int(row, "completion_tokens") for row in response_rows)
    total_total = sum(_usage_int(row, "total_tokens") for row in response_rows)
    return {
        "scenario_id": scenario_id,
        "method_id": method_id,
        "mode": mode,
        "llm_profile": llm_profile,
        "seed": seed,
        "provider": _single_or_list(_sorted_unique(list(_values(request_rows, "provider")) + list(_values(response_rows, "provider")))),
        "model": _single_or_list(_sorted_unique(list(_values(request_rows, "model")) + list(_values(response_rows, "model")))),
        "remote_endpoint_label": _remote_endpoint_label(llm_profile),
        "run_wall_seconds": float(run_wall_seconds),
        "optimizer_wall_seconds": float(optimizer_wall_seconds),
        "llm_request_count": len(request_rows),
        "llm_response_count": len(response_rows),
        "llm_retry_count": int(sum(int(row.get("retries", 0)) for row in response_rows)),
        "llm_fallback_count": int(sum(1 for row in controller_rows if row.get("fallback_used") or dict(row.get("metadata", {})).get("fallback_used"))),
        "llm_latency_seconds_total": float(sum(latencies)),
        "llm_latency_seconds_mean": _mean(latencies),
        "llm_latency_seconds_median": _percentile(latencies, 50),
        "llm_latency_seconds_p95": _percentile(latencies, 95),
        "llm_latency_seconds_max": max(latencies) if latencies else 0.0,
        "tokens_prompt_total": int(prompt_total),
        "tokens_completion_total": int(completion_total),
        "tokens_total": int(total_total),
        "tokens_total_per_request_mean": float(total_total / max(1, len(response_rows))),
    }


def _usage_int(row: Mapping[str, Any], key: str) -> int:
    usage = row.get("usage")
    if isinstance(usage, Mapping) and usage.get(key) is not None:
        return int(usage[key])
    if row.get(key) is not None:
        return int(row[key])
    return 0


def _seed_from_root(root: Path) -> int:
    name = root.name
    if name.startswith("seed-"):
        return int(name.split("-", 1)[1])
    return 0
```

Also add `_percentile`, `_mean`, `_single_or_list`, and `_remote_endpoint_label` helpers. `_remote_endpoint_label("gpt")` returns `"GPT_PROXY_BASE_URL"`, `"gemma4"` returns `"GEMMA4_BASE_URL"`, unknown profiles return `"<profile>_profile"`.

- [ ] **Step 4: Wire LLM summary into postprocess**

Add to `optimizers/benchmark_runner/postprocess.py`:

```python
def write_llm_runtime_summary(seed_root: str | Path, summary: Mapping[str, Any]) -> Path:
    root = Path(seed_root)
    output = root / "summaries" / "llm_runtime_summary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(dict(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    append_summary_event(
        root / "traces" / "run_events.jsonl",
        event="llm_runtime_summary",
        scenario_id=str(summary["scenario_id"]),
        method_id=str(summary["method_id"]),
        mode=str(summary["mode"]),
        llm_profile=str(summary.get("llm_profile") or ""),
        seed=int(summary.get("seed", 0) or 0),
        summary=dict(summary),
    )
    return output
```

- [ ] **Step 5: Run LLM summary tests**

Run:

```bash
conda run -n msfenicsx pytest -v tests/optimizers/test_benchmark_runner_llm_summary.py tests/optimizers/test_benchmark_runner_postprocess.py tests/optimizers/test_llm_trace_io.py
```

Expected: PASS.

- [ ] **Step 6: Commit Task 5**

```bash
git add optimizers/llm_summary.py optimizers/benchmark_runner/postprocess.py tests/optimizers/test_benchmark_runner_llm_summary.py
git commit -m "feat: summarize llm latency and tokens per seed"
```

---

### Task 6: Post-Run Render And LLM Diagnostics

**Files:**
- Modify: `optimizers/benchmark_runner/postprocess.py`
- Create: `tests/optimizers/test_benchmark_runner_postprocess_pipeline.py`

- [ ] **Step 1: Write failing test for post-run pipeline call order**

Create `tests/optimizers/test_benchmark_runner_postprocess_pipeline.py`:

```python
from pathlib import Path

from optimizers.benchmark_runner.postprocess import run_leaf_postprocess


def test_leaf_postprocess_renders_and_runs_llm_diagnostics(tmp_path: Path, monkeypatch) -> None:
    seed_root = tmp_path / "llm-gpt" / "seeds" / "seed-11"
    (seed_root / "traces").mkdir(parents=True)
    (seed_root / "traces" / "llm_request_trace.jsonl").write_text("", encoding="utf-8")
    (seed_root / "traces" / "llm_response_trace.jsonl").write_text("", encoding="utf-8")
    (seed_root / "traces" / "controller_trace.jsonl").write_text("", encoding="utf-8")

    calls: list[str] = []
    monkeypatch.setattr("optimizers.render_assets.render_assets", lambda path, hires=False: calls.append(f"render:{Path(path).name}") or [Path(path)])
    monkeypatch.setattr("llm.openai_compatible.replay.replay_request_trace_file", lambda *args, **kwargs: {"rows": 0})
    monkeypatch.setattr("llm.openai_compatible.replay.save_replay_summary", lambda output, summary: calls.append(f"replay:{Path(output).name}"))
    monkeypatch.setattr("optimizers.operator_pool.diagnostics.analyze_controller_trace", lambda *args, **kwargs: {"decisions": 0})
    monkeypatch.setattr("optimizers.operator_pool.diagnostics.save_controller_trace_summary", lambda output, summary: calls.append(f"controller:{Path(output).name}"))

    run_leaf_postprocess(
        seed_root,
        mode="llm",
        llm_profile="gpt",
        optimization_spec_path=Path("scenarios/optimization/s5_aggressive15_llm.yaml"),
    )

    assert calls == ["render:seed-11", "replay:llm_replay_summary.json", "controller:controller_trace_summary.json"]
```

- [ ] **Step 2: Run pipeline test and verify it fails**

Run:

```bash
conda run -n msfenicsx pytest -v tests/optimizers/test_benchmark_runner_postprocess_pipeline.py
```

Expected: FAIL with missing `run_leaf_postprocess`.

- [ ] **Step 3: Implement `run_leaf_postprocess`**

Add to `optimizers/benchmark_runner/postprocess.py`:

```python
def run_leaf_postprocess(
    seed_root: str | Path,
    *,
    mode: str,
    llm_profile: str | None,
    optimization_spec_path: Path,
) -> None:
    root = Path(seed_root)
    from optimizers.render_assets import render_assets

    render_assets(root, hires=False)
    if mode != "llm":
        return

    from llm.openai_compatible.replay import replay_request_trace_file, save_replay_summary
    from optimizers.io import load_optimization_spec
    from optimizers.operator_pool.diagnostics import analyze_controller_trace, save_controller_trace_summary

    optimization_spec = load_optimization_spec(optimization_spec_path)
    operator_control = optimization_spec.operator_control or {}
    controller_parameters = dict(operator_control.get("controller_parameters", {}))
    replay_summary = replay_request_trace_file(
        root / "traces" / "llm_request_trace.jsonl",
        controller_parameters,
        limit=None,
    )
    save_replay_summary(root / "summaries" / "llm_replay_summary.json", replay_summary)
    controller_summary = analyze_controller_trace(
        root / "traces" / "controller_trace.jsonl",
        optimization_result_path=root / "optimization_result.json",
        operator_trace_path=root / "traces" / "operator_trace.jsonl",
        llm_request_trace_path=root / "traces" / "llm_request_trace.jsonl",
        llm_response_trace_path=root / "traces" / "llm_response_trace.jsonl",
    )
    save_controller_trace_summary(root / "summaries" / "controller_trace_summary.json", controller_summary)
```

- [ ] **Step 4: Call postprocess from leaf entrypoint**

In `optimizers/benchmark_runner/leaf_entrypoint.py`, after runtime and optional LLM summaries are written:

```python
postprocess_start = time.monotonic()
try:
    run_leaf_postprocess(
        output_root,
        mode=args.mode,
        llm_profile=args.llm_profile,
        optimization_spec_path=spec_path,
    )
except Exception as exc:
    event_writer.write(
        "leaf_failed",
        scenario_id=scenario_id,
        method_id=args.method_id,
        mode=args.mode,
        llm_profile=args.llm_profile,
        seed=args.benchmark_seed,
        message=f"postprocess failed: {exc}",
        metrics={"postprocess_error": str(exc)},
    )
    raise
postprocess_wall_seconds = time.monotonic() - postprocess_start
```

The final manifest status remains `completed` only when optimizer and postprocess both succeed.

- [ ] **Step 5: Run pipeline tests**

Run:

```bash
conda run -n msfenicsx pytest -v tests/optimizers/test_benchmark_runner_postprocess_pipeline.py tests/visualization/test_render_assets_fixtures.py
```

Expected: PASS.

- [ ] **Step 6: Commit Task 6**

```bash
git add optimizers/benchmark_runner/postprocess.py optimizers/benchmark_runner/leaf_entrypoint.py tests/optimizers/test_benchmark_runner_postprocess_pipeline.py
git commit -m "feat: run postprocess after benchmark leaves"
```

---

### Task 7: IGD Metric

**Files:**
- Create: `optimizers/benchmark_runner/igd.py`
- Modify: `optimizers/analytics/pareto.py`
- Create: `tests/optimizers/test_benchmark_runner_igd.py`

- [ ] **Step 1: Write failing IGD tests**

Create `tests/optimizers/test_benchmark_runner_igd.py`:

```python
from optimizers.benchmark_runner.igd import empirical_reference_front, igd_2d


def test_empirical_reference_front_keeps_nondominated_points() -> None:
    points = [(1.0, 5.0), (2.0, 4.0), (3.0, 7.0), (1.5, 4.5)]

    front = empirical_reference_front(points)

    assert front == [(1.0, 5.0), (1.5, 4.5), (2.0, 4.0)]


def test_igd_2d_is_zero_when_candidate_matches_reference() -> None:
    reference = [(1.0, 5.0), (2.0, 4.0)]

    assert igd_2d(reference, reference) == 0.0


def test_igd_2d_is_average_nearest_reference_distance_after_normalization() -> None:
    reference = [(0.0, 0.0), (10.0, 0.0)]
    candidate = [(0.0, 0.0)]

    value = igd_2d(candidate, reference)

    assert value == 0.5
```

- [ ] **Step 2: Run IGD tests and verify they fail**

Run:

```bash
conda run -n msfenicsx pytest -v tests/optimizers/test_benchmark_runner_igd.py
```

Expected: FAIL with missing `igd.py`.

- [ ] **Step 3: Implement 2D IGD**

Create `optimizers/benchmark_runner/igd.py`:

```python
"""IGD helpers for 2D minimization comparison contexts."""

from __future__ import annotations

import math
from collections.abc import Sequence

from optimizers.analytics.pareto import pareto_front_indices


Point = tuple[float, float]


def empirical_reference_front(points: Sequence[Point]) -> list[Point]:
    ordered = [(float(x), float(y)) for x, y in points]
    indices = pareto_front_indices(ordered)
    return sorted((ordered[index] for index in indices), key=lambda point: (point[0], point[1]))


def igd_2d(candidate_points: Sequence[Point], reference_points: Sequence[Point]) -> float | None:
    if not candidate_points or not reference_points:
        return None
    normalized_candidates, normalized_reference = _normalize_together(candidate_points, reference_points)
    distances = [
        min(_euclidean(ref, candidate) for candidate in normalized_candidates)
        for ref in normalized_reference
    ]
    return float(sum(distances) / len(distances))


def _normalize_together(candidate_points: Sequence[Point], reference_points: Sequence[Point]) -> tuple[list[Point], list[Point]]:
    all_points = [(float(x), float(y)) for x, y in list(candidate_points) + list(reference_points)]
    min_x = min(point[0] for point in all_points)
    max_x = max(point[0] for point in all_points)
    min_y = min(point[1] for point in all_points)
    max_y = max(point[1] for point in all_points)
    span_x = max(max_x - min_x, 1.0e-12)
    span_y = max(max_y - min_y, 1.0e-12)

    def normalize(points: Sequence[Point]) -> list[Point]:
        return [((float(x) - min_x) / span_x, (float(y) - min_y) / span_y) for x, y in points]

    return normalize(candidate_points), normalize(reference_points)


def _euclidean(left: Point, right: Point) -> float:
    return math.sqrt((left[0] - right[0]) ** 2 + (left[1] - right[1]) ** 2)
```

- [ ] **Step 4: Re-export from pareto analytics for existing imports**

Add to `optimizers/analytics/pareto.py`:

```python
def empirical_reference_front_2d(points: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
    from optimizers.benchmark_runner.igd import empirical_reference_front

    return empirical_reference_front(points)


def igd_2d(
    candidate_points: Sequence[tuple[float, float]],
    reference_points: Sequence[tuple[float, float]],
) -> float | None:
    from optimizers.benchmark_runner.igd import igd_2d as _igd_2d

    return _igd_2d(candidate_points, reference_points)
```

- [ ] **Step 5: Run IGD tests**

Run:

```bash
conda run -n msfenicsx pytest -v tests/optimizers/test_benchmark_runner_igd.py tests/optimizers/test_analytics_pareto.py
```

Expected: PASS.

- [ ] **Step 6: Commit Task 7**

```bash
git add optimizers/benchmark_runner/igd.py optimizers/analytics/pareto.py tests/optimizers/test_benchmark_runner_igd.py
git commit -m "feat: add igd metric for benchmark comparisons"
```

---

### Task 8: Campaign Comparison Planner

**Files:**
- Create: `optimizers/benchmark_runner/comparisons.py`
- Modify: `optimizers/comparison_artifacts.py`
- Create: `tests/optimizers/test_benchmark_runner_comparisons.py`

- [ ] **Step 1: Write failing tests for raw+union five seeds and single LLM补跑**

Create `tests/optimizers/test_benchmark_runner_comparisons.py`:

```python
from pathlib import Path

from tests.optimizers.experiment_fixtures import create_mixed_run_root
from optimizers.benchmark_runner.comparisons import plan_campaign_comparisons


def test_raw_union_five_seeds_gets_by_seed_and_aggregate(tmp_path: Path, monkeypatch) -> None:
    run_root = create_mixed_run_root(tmp_path, modes=("raw", "union"), seeds=(11, 17, 23, 29, 31))
    calls: list[tuple[tuple[str, ...], str]] = []
    monkeypatch.setattr(
        "optimizers.comparison_artifacts.build_comparison_bundle",
        lambda runs, output, **kwargs: calls.append((tuple(Path(run).parent.parent.name for run in runs), str(output.relative_to(run_root)))) or {"manifest": {}},
    )
    monkeypatch.setattr(
        "optimizers.benchmark_runner.comparisons.build_campaign_aggregate_bundle",
        lambda payloads, output, method_ids, benchmark_seeds: calls.append((tuple(method_ids), str(output.relative_to(run_root)))) or {},
    )

    manifest = plan_campaign_comparisons(run_root)

    assert len(manifest["by_seed_paths"]) == 5
    assert manifest["aggregate_path"] == "comparisons/aggregate/raw_vs_union"
    assert any(path == "comparisons/by_seed/seed-11/raw_vs_union" for _, path in calls)
    assert any(path == "comparisons/aggregate/raw_vs_union" for _, path in calls)


def test_single_llm_seed_only_refreshes_three_mode_by_seed(tmp_path: Path, monkeypatch) -> None:
    raw_union_root = create_mixed_run_root(tmp_path, modes=("raw", "union"), seeds=(11, 17, 23, 29, 31))
    llm_root = create_mixed_run_root(tmp_path, modes=("llm-gpt",), seeds=(11,))
    calls: list[str] = []
    monkeypatch.setattr(
        "optimizers.comparison_artifacts.build_comparison_bundle",
        lambda runs, output, **kwargs: calls.append(str(output)) or {"manifest": {}},
    )

    manifest = plan_campaign_comparisons(llm_root, compare_with=[raw_union_root])

    assert any("seed-11/raw_vs_union_vs_llm-gpt" in path for path in calls)
    assert not any("aggregate/raw_vs_union_vs_llm-gpt" in path for path in calls)
    assert manifest["aggregate_path"] is None
```

- [ ] **Step 2: Run comparison planner tests and verify they fail**

Run:

```bash
conda run -n msfenicsx pytest -v tests/optimizers/test_benchmark_runner_comparisons.py
```

Expected: FAIL with missing `comparisons.py`.

- [ ] **Step 3: Implement comparison planner**

Create `optimizers/benchmark_runner/comparisons.py`:

```python
"""Campaign-local comparison planning."""

from __future__ import annotations

import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

from optimizers.comparison_artifacts import build_comparison_bundle, _collect_run_payload


def plan_campaign_comparisons(run_root: str | Path, *, compare_with: list[Path] | tuple[Path, ...] = ()) -> dict[str, Any]:
    root = Path(run_root)
    all_roots = [root, *[Path(path) for path in compare_with]]
    seed_runs = _collect_seed_runs(all_roots)
    comparisons_root = root / "comparisons"
    by_seed_paths: dict[str, str] = {}
    for seed, runs_by_method in sorted(seed_runs.items()):
        if len(runs_by_method) < 2:
            continue
        method_ids = _ordered_methods(runs_by_method)
        output = comparisons_root / "by_seed" / f"seed-{seed}" / _comparison_slug(method_ids)
        build_comparison_bundle(
            runs=[runs_by_method[method] for method in method_ids],
            output=output,
            comparison_kind="by_seed",
            suite_root=root,
            benchmark_seed=seed,
        )
        by_seed_paths[f"seed-{seed}:{_comparison_slug(method_ids)}"] = str(output.relative_to(root).as_posix())

    aggregate_path = _maybe_build_aggregate(root, seed_runs)
    manifest = {
        "run_root": str(root),
        "compare_with": [str(path) for path in compare_with],
        "by_seed_paths": by_seed_paths,
        "aggregate_path": aggregate_path,
    }
    comparisons_root.mkdir(parents=True, exist_ok=True)
    (comparisons_root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
```

Implement helpers:

- `_collect_seed_runs(roots)` scans `<method_slug>/seeds/seed-*`.
- `_method_id(seed_root)` reads `run.yaml.method_id`; fallback to method directory name.
- `_ordered_methods(runs_by_method)` returns raw first, union second, then sorted LLM/profile methods.
- `_comparison_slug(method_ids)` converts `["raw", "union", "llm-gpt"]` to `raw_vs_union_vs_llm-gpt`.
- `_maybe_build_aggregate` groups method sets by common seed intersection and builds aggregate only when every method in the set has at least two shared seeds for multi-seed aggregate; raw+union five seeds produces aggregate, raw+union+llm-gpt one seed does not.

Use this concrete helper implementation:

```python
def _collect_seed_runs(roots: list[Path]) -> dict[int, dict[str, Path]]:
    rows: dict[int, dict[str, Path]] = defaultdict(dict)
    for root in roots:
        for method_root in sorted(path for path in root.iterdir() if path.is_dir()):
            seeds_root = method_root / "seeds"
            if not seeds_root.is_dir():
                continue
            for seed_root in sorted(seeds_root.glob("seed-*")):
                seed = int(seed_root.name.split("-", 1)[1])
                rows[seed][_method_id(seed_root)] = seed_root
    return dict(rows)


def _method_id(seed_root: Path) -> str:
    import yaml

    run_yaml = seed_root / "run.yaml"
    if run_yaml.exists():
        payload = yaml.safe_load(run_yaml.read_text(encoding="utf-8")) or {}
        explicit = payload.get("method_id")
        if explicit:
            return str(explicit).replace(":", "-")
        mode = payload.get("mode")
        if mode:
            return str(mode).replace(":", "-")
    return seed_root.parent.parent.name


def _ordered_methods(runs_by_method: dict[str, Path]) -> list[str]:
    return sorted(runs_by_method, key=_method_sort_key)


def _method_sort_key(method: str) -> tuple[int, str]:
    if method in {"raw", "nsga2_raw", "nsga2-raw"}:
        return (0, method)
    if method in {"union", "nsga2_union", "nsga2-union"}:
        return (1, method)
    if method.startswith("llm"):
        return (2, method)
    return (3, method)


def _comparison_slug(method_ids: list[str]) -> str:
    normalized = [
        "raw" if method in {"nsga2_raw", "nsga2-raw"} else "union" if method in {"nsga2_union", "nsga2-union"} else method
        for method in method_ids
    ]
    return "_vs_".join(normalized)


def _maybe_build_aggregate(root: Path, seed_runs: dict[int, dict[str, Path]]) -> str | None:
    if not seed_runs:
        return None
    all_methods = sorted({method for runs in seed_runs.values() for method in runs}, key=_method_sort_key)
    best_methods: list[str] = []
    best_shared_seeds: list[int] = []
    for width in range(len(all_methods), 1, -1):
        for methods in combinations(all_methods, width):
            shared_seeds = [
                seed
                for seed, runs in sorted(seed_runs.items())
                if all(method in runs for method in methods)
            ]
            if len(shared_seeds) >= 2:
                best_methods = list(methods)
                best_shared_seeds = shared_seeds
                break
        if best_methods:
            break
    if not best_methods:
        return None
    output = root / "comparisons" / "aggregate" / _comparison_slug(best_methods)
    payloads = [
        _collect_run_payload(seed_runs[seed][method])
        for seed in best_shared_seeds
        for method in best_methods
    ]
    build_campaign_aggregate_bundle(
        payloads=payloads,
        output=output,
        method_ids=best_methods,
        benchmark_seeds=best_shared_seeds,
    )
    return str(output.relative_to(root).as_posix())


def build_campaign_aggregate_bundle(
    *,
    payloads: list[dict[str, Any]],
    output: Path,
    method_ids: list[str],
    benchmark_seeds: list[int],
) -> dict[str, Any]:
    from optimizers.comparison_artifacts import (
        _apply_shared_hypervolume_reference,
        _build_aggregate_suite_bundle,
    )

    reference_point = _apply_shared_hypervolume_reference(payloads)
    _build_aggregate_suite_bundle(
        payloads=payloads,
        output=output,
        hypervolume_reference_point=reference_point,
        hires=False,
    )
    return {
        "method_ids": list(method_ids),
        "benchmark_seeds": list(benchmark_seeds),
        "output": str(output),
    }
```

- [ ] **Step 4: Add IGD fields to comparison summary rows**

Modify `optimizers/comparison_artifacts.py`:

1. Import:

```python
from optimizers.benchmark_runner.igd import empirical_reference_front, igd_2d
```

2. After `_apply_shared_hypervolume_reference(payloads)` in `build_comparison_bundle`, add:

```python
_apply_shared_igd_reference(payloads)
```

3. Implement:

```python
def _apply_shared_igd_reference(payloads: Sequence[Mapping[str, Any]]) -> None:
    reference = empirical_reference_front(
        [
            point
            for payload in payloads
            for point in payload.get("front", [])
        ]
    )
    for payload in payloads:
        summary = payload.get("summary_row")
        if isinstance(summary, dict):
            summary["final_igd"] = igd_2d(payload.get("front", []), reference)
            summary["igd_direction"] = "lower_is_better"
```

4. Add `final_igd` and `igd_direction` to `_summary_table_rows()`.

- [ ] **Step 5: Run comparison tests**

Run:

```bash
conda run -n msfenicsx pytest -v tests/optimizers/test_benchmark_runner_comparisons.py tests/optimizers/test_compare_runs.py
```

Expected: PASS.

- [ ] **Step 6: Commit Task 8**

```bash
git add optimizers/benchmark_runner/comparisons.py optimizers/comparison_artifacts.py tests/optimizers/test_benchmark_runner_comparisons.py
git commit -m "feat: plan seed-aware benchmark comparisons"
```

---

### Task 9: Public `run-benchmark` CLI

**Files:**
- Modify: `optimizers/cli.py`
- Create: `tests/optimizers/test_benchmark_runner_cli.py`

- [ ] **Step 1: Write failing tests for CLI command surface**

Create `tests/optimizers/test_benchmark_runner_cli.py`:

```python
from pathlib import Path

from optimizers.cli import build_parser, main


def test_cli_exposes_only_run_benchmark_for_optimizer_runs() -> None:
    parser = build_parser()
    help_text = parser.format_help()

    assert "run-benchmark" in help_text
    assert "optimize-benchmark" not in help_text
    assert "run-llm" not in help_text
    assert "run-benchmark-suite" not in help_text
    assert "run-benchmark-matrix" not in help_text
    assert "aggregate-benchmark-matrix" not in help_text
    assert "render-assets" not in help_text
    assert "compare-runs" not in help_text


def test_run_benchmark_dispatches_batch_spec(tmp_path: Path, monkeypatch) -> None:
    batch_path = tmp_path / "batch.yaml"
    batch_path.write_text("campaign_id: c\nscenario_id: s\nmethods: []\npopulation_size: 1\nnum_generations: 1\n", encoding="utf-8")
    calls: list[str] = []

    monkeypatch.setattr("optimizers.cli.load_campaigns_from_batch_spec", lambda path: calls.append(str(path)) or [])

    assert main(["run-benchmark", "--batch-spec", str(batch_path)]) == 0
    assert calls == [str(batch_path)]


def test_run_benchmark_dispatches_single_leaf(tmp_path: Path, monkeypatch) -> None:
    calls: list[dict] = []

    def fake_build_single_leaf_campaign(**kwargs):
        calls.append(kwargs)
        return object()

    monkeypatch.setattr("optimizers.cli.build_single_leaf_campaign", fake_build_single_leaf_campaign)
    monkeypatch.setattr("optimizers.cli.run_campaign_supervisor", lambda campaign: tmp_path)
    monkeypatch.setattr("optimizers.cli.plan_campaign_comparisons", lambda run_root, compare_with=(): {})

    assert main(
        [
            "run-benchmark",
            "--optimization-spec",
            "scenarios/optimization/s5_aggressive15_llm.yaml",
            "--mode",
            "llm",
            "--llm-profile",
            "gpt",
            "--benchmark-seed",
            "11",
            "--algorithm-seed",
            "1011",
            "--population-size",
            "40",
            "--num-generations",
            "32",
            "--evaluation-workers",
            "16",
            "--scenario-runs-root",
            str(tmp_path / "scenario_runs"),
        ]
    ) == 0
    assert calls[0]["llm_profile"] == "gpt"
```

- [ ] **Step 2: Run CLI tests and verify they fail**

Run:

```bash
conda run -n msfenicsx pytest -v tests/optimizers/test_benchmark_runner_cli.py
```

Expected: FAIL because `run-benchmark` does not exist and old commands are still exposed.

- [ ] **Step 3: Rewrite `optimizers/cli.py` imports**

Remove these imports from `optimizers/cli.py`:

```python
from evaluation.io import load_spec
from llm.openai_compatible.replay import replay_request_trace_file, save_replay_summary
from optimizers.artifacts import write_optimization_artifacts
from optimizers.drivers.raw_driver import run_raw_optimization
from optimizers.drivers.union_driver import run_union_optimization
from optimizers.matrix.aggregate import aggregate_matrix
from optimizers.matrix.config import build_s5_s7_budgeted_matrix
from optimizers.matrix.runner import run_matrix_block
from optimizers.operator_pool.diagnostics import analyze_controller_trace, save_controller_trace_summary
from optimizers.run_manifest import write_run_manifest
from optimizers.run_suite import resolve_suite_mode_id, run_benchmark_suite
```

Keep `apply_algorithm_overrides`, `_temporary_env_overlay`, `_llm_env_overlay_for_spec`, and `_resolve_llm_provider_profile` if leaf entrypoint imports them. Add:

```python
from optimizers.benchmark_runner.comparisons import plan_campaign_comparisons
from optimizers.benchmark_runner.specs import build_single_leaf_campaign, load_campaigns_from_batch_spec
from optimizers.benchmark_runner.supervisor import run_campaign_supervisor
```

- [ ] **Step 4: Replace parser subcommands with `run-benchmark`**

In `build_parser()`, remove every old subparser and add:

```python
run_parser = subparsers.add_parser("run-benchmark")
run_parser.add_argument("--batch-spec")
run_parser.add_argument("--optimization-spec")
run_parser.add_argument("--mode", choices=["raw", "union", "llm"])
run_parser.add_argument("--llm-profile")
run_parser.add_argument("--benchmark-seed", type=int)
run_parser.add_argument("--algorithm-seed", type=int)
run_parser.add_argument("--population-size", type=_positive_int)
run_parser.add_argument("--num-generations", type=_positive_int)
run_parser.add_argument("--evaluation-workers", type=_positive_int, default=16)
run_parser.add_argument("--scenario-runs-root", default="./scenario_runs")
run_parser.add_argument("--campaign-id")
run_parser.add_argument("--compare-with", action="append", default=[])
```

- [ ] **Step 5: Replace `main()` dispatch**

In `main()`:

```python
if args.command == "run-benchmark":
    if args.batch_spec:
        campaigns = load_campaigns_from_batch_spec(args.batch_spec)
    else:
        required = {
            "--optimization-spec": args.optimization_spec,
            "--mode": args.mode,
            "--benchmark-seed": args.benchmark_seed,
            "--algorithm-seed": args.algorithm_seed,
            "--population-size": args.population_size,
            "--num-generations": args.num_generations,
        }
        missing = [name for name, value in required.items() if value is None]
        if missing:
            parser.error("run-benchmark single leaf missing: " + ", ".join(missing))
        campaigns = [
            build_single_leaf_campaign(
                optimization_spec=Path(args.optimization_spec),
                mode=args.mode,
                llm_profile=args.llm_profile,
                benchmark_seed=args.benchmark_seed,
                algorithm_seed=args.algorithm_seed,
                population_size=args.population_size,
                num_generations=args.num_generations,
                evaluation_workers=args.evaluation_workers,
                scenario_runs_root=Path(args.scenario_runs_root),
                campaign_id=args.campaign_id,
                compare_with=[Path(path) for path in args.compare_with],
            )
        ]
    for campaign in campaigns:
        run_root = run_campaign_supervisor(campaign)
        plan_campaign_comparisons(run_root, compare_with=list(campaign.compare_with))
    return 0
```

- [ ] **Step 6: Run CLI tests**

Run:

```bash
conda run -n msfenicsx pytest -v tests/optimizers/test_benchmark_runner_cli.py tests/cli/test_module_entrypoints.py
```

Expected: PASS.

- [ ] **Step 7: Commit Task 9**

```bash
git add optimizers/cli.py tests/optimizers/test_benchmark_runner_cli.py
git commit -m "feat: expose unified run-benchmark cli"
```

---

### Task 10: Formal Batch Specs For S5/S6 Raw+Union

**Files:**
- Create: `scenarios/batches/s5_raw_union_budgeted.yaml`
- Create: `scenarios/batches/s6_raw_union_budgeted.yaml`
- Create: `scenarios/batches/s5_s6_raw_union_budgeted.yaml`
- Create: `tests/optimizers/test_benchmark_runner_batch_specs.py`

- [ ] **Step 1: Write failing tests for checked-in batch specs**

Create `tests/optimizers/test_benchmark_runner_batch_specs.py`:

```python
from optimizers.benchmark_runner.specs import load_campaigns_from_batch_spec


def test_s5_raw_union_budgeted_batch_spec() -> None:
    campaign = load_campaigns_from_batch_spec("scenarios/batches/s5_raw_union_budgeted.yaml")[0]
    assert campaign.scenario_id == "s5_aggressive15"
    assert len(campaign.leaves) == 10
    assert {leaf.population_size for leaf in campaign.leaves} == {40}
    assert {leaf.num_generations for leaf in campaign.leaves} == {32}
    assert {leaf.evaluation_workers for leaf in campaign.leaves} == {16}


def test_s6_raw_union_budgeted_batch_spec() -> None:
    campaign = load_campaigns_from_batch_spec("scenarios/batches/s6_raw_union_budgeted.yaml")[0]
    assert campaign.scenario_id == "s6_aggressive20"
    assert len(campaign.leaves) == 10
    assert {leaf.population_size for leaf in campaign.leaves} == {56}
    assert {leaf.num_generations for leaf in campaign.leaves} == {36}


def test_s5_s6_combined_batch_spec() -> None:
    campaigns = load_campaigns_from_batch_spec("scenarios/batches/s5_s6_raw_union_budgeted.yaml")
    assert [campaign.scenario_id for campaign in campaigns] == ["s5_aggressive15", "s6_aggressive20"]
    assert [len(campaign.leaves) for campaign in campaigns] == [10, 10]
```

- [ ] **Step 2: Run batch spec tests and verify they fail**

Run:

```bash
conda run -n msfenicsx pytest -v tests/optimizers/test_benchmark_runner_batch_specs.py
```

Expected: FAIL because `scenarios/batches/*.yaml` do not exist.

- [ ] **Step 3: Add S5 batch spec**

Create `scenarios/batches/s5_raw_union_budgeted.yaml`:

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
  leaf_evaluation_workers: 16
comparison_policy:
  by_seed: true
  aggregate: true
```

- [ ] **Step 4: Add S6 batch spec**

Create `scenarios/batches/s6_raw_union_budgeted.yaml`:

```yaml
campaign_id: s6_budgeted_main
scenario_runs_root: ./scenario_runs
scenario_id: s6_aggressive20
methods:
  - method_id: nsga2_raw
    mode: raw
    optimization_spec: scenarios/optimization/s6_aggressive20_raw.yaml
  - method_id: nsga2_union
    mode: union
    optimization_spec: scenarios/optimization/s6_aggressive20_union.yaml
replicate_seeds: [11, 17, 23, 29, 31]
algorithm_seed_offset: 1000
population_size: 56
num_generations: 36
resource_policy:
  max_concurrent_leaves: 4
  leaf_evaluation_workers: 16
comparison_policy:
  by_seed: true
  aggregate: true
```

- [ ] **Step 5: Add combined S5/S6 batch spec**

Create `scenarios/batches/s5_s6_raw_union_budgeted.yaml`:

```yaml
campaigns:
  - campaign_id: s5_budgeted_main
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
      leaf_evaluation_workers: 16
    comparison_policy:
      by_seed: true
      aggregate: true
  - campaign_id: s6_budgeted_main
    scenario_runs_root: ./scenario_runs
    scenario_id: s6_aggressive20
    methods:
      - method_id: nsga2_raw
        mode: raw
        optimization_spec: scenarios/optimization/s6_aggressive20_raw.yaml
      - method_id: nsga2_union
        mode: union
        optimization_spec: scenarios/optimization/s6_aggressive20_union.yaml
    replicate_seeds: [11, 17, 23, 29, 31]
    algorithm_seed_offset: 1000
    population_size: 56
    num_generations: 36
    resource_policy:
      max_concurrent_leaves: 4
      leaf_evaluation_workers: 16
    comparison_policy:
      by_seed: true
      aggregate: true
```

- [ ] **Step 6: Run batch spec tests**

Run:

```bash
conda run -n msfenicsx pytest -v tests/optimizers/test_benchmark_runner_batch_specs.py
```

Expected: PASS.

- [ ] **Step 7: Commit Task 10**

```bash
git add scenarios/batches/s5_raw_union_budgeted.yaml scenarios/batches/s6_raw_union_budgeted.yaml scenarios/batches/s5_s6_raw_union_budgeted.yaml tests/optimizers/test_benchmark_runner_batch_specs.py
git commit -m "feat: add s5 s6 raw union batch specs"
```

---

### Task 11: Delete Old Suite And Matrix Code Paths

**Files:**
- Delete: `optimizers/run_suite.py`
- Delete: `optimizers/suite_parallel.py`
- Delete: `optimizers/matrix/`
- Delete: old suite/matrix tests listed in File Structure
- Modify: `tests/optimizers/test_optimizer_cli.py`
- Modify: `tests/optimizers/test_cli_pop_gen_overrides.py`
- Modify: `tests/optimizers/test_cli_writes_run_manifest.py`

- [ ] **Step 1: Remove old command tests from `test_optimizer_cli.py`**

Edit `tests/optimizers/test_optimizer_cli.py`:

- Remove tests that invoke `optimize-benchmark`, `run-llm`, `run-benchmark-suite`, `run-benchmark-matrix`, `aggregate-benchmark-matrix`, `render-assets`, `compare-runs`, `replay-llm-trace`, and `analyze-controller-trace` as CLI commands.
- Keep helper functions that build synthetic artifacts only if still imported by other tests.
- Move LLM diagnostics behavior coverage to internal-module tests rather than CLI tests.

Concrete command to identify old references:

```bash
rg -n "\"optimize-benchmark\"|\"run-llm\"|\"run-benchmark-suite\"|\"run-benchmark-matrix\"|\"aggregate-benchmark-matrix\"|\"render-assets\"|\"compare-runs\"|\"replay-llm-trace\"|\"analyze-controller-trace\"" tests/optimizers/test_optimizer_cli.py tests/optimizers/test_cli_pop_gen_overrides.py tests/optimizers/test_cli_writes_run_manifest.py
```

Expected after edits: the command returns no matches in those three files.

- [ ] **Step 2: Delete old suite/matrix files**

Run:

```bash
git rm -r optimizers/matrix
git rm optimizers/run_suite.py optimizers/suite_parallel.py
git rm tests/optimizers/test_run_suite.py tests/optimizers/test_suite_parallel.py tests/optimizers/test_suite_comparisons.py
git rm tests/optimizers/test_matrix_config.py tests/optimizers/test_matrix_figures.py tests/optimizers/test_matrix_index.py
git rm tests/optimizers/test_matrix_representatives.py tests/optimizers/test_matrix_runner.py tests/optimizers/test_matrix_spec_snapshots.py tests/optimizers/test_matrix_aggregate.py
```

- [ ] **Step 3: Verify no active imports remain**

Run:

```bash
rg -n "optimizers\\.run_suite|optimizers\\.suite_parallel|optimizers\\.matrix|run_benchmark_suite|run_leaves_parallel|run_matrix_block|aggregate_matrix" optimizers tests
```

Expected: no matches.

- [ ] **Step 4: Run optimizer focused tests**

Run:

```bash
conda run -n msfenicsx pytest -v tests/optimizers/test_benchmark_runner_cli.py tests/optimizers/test_benchmark_runner_specs.py tests/optimizers/test_benchmark_runner_supervisor.py tests/optimizers/test_benchmark_runner_comparisons.py
```

Expected: PASS.

- [ ] **Step 5: Commit Task 11**

```bash
git add -A optimizers tests/optimizers
git commit -m "refactor: remove legacy benchmark suite and matrix paths"
```

---

### Task 12: Documentation And Repository Guidance

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: active docs that present current commands under `docs/superpowers/specs/` and `docs/superpowers/plans/`

- [ ] **Step 1: Replace active command examples in README**

Use:

```bash
rg -n "optimize-benchmark|run-llm|run-benchmark-suite|run-benchmark-matrix|aggregate-benchmark-matrix|render-assets|compare-runs|replay-llm-trace|analyze-controller-trace" README.md
```

Replace current run examples with:

```bash
conda run -n msfenicsx python -m optimizers.cli run-benchmark \
  --batch-spec scenarios/batches/s5_raw_union_budgeted.yaml
```

and:

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

- [ ] **Step 2: Update AGENTS.md as authoritative guidance**

In `AGENTS.md`:

- Remove old preferred optimizer commands.
- State `run-benchmark` is the only daily optimizer run entry.
- State render/replay/analyze/compare are internal post-run phases.
- State `scenario_runs/logs/` is not created by runner.
- State default server policy is `max_concurrent_leaves=4`, `leaf_evaluation_workers=16`.
- State S5/S6 formal raw+union uses `scenarios/batches/s5_s6_raw_union_budgeted.yaml`.

- [ ] **Step 3: Mark old active specs/plans as superseded**

Edit these files near the top:

- `docs/superpowers/specs/2026-05-08-suite-parallel-execution-design.md`
- `docs/superpowers/plans/2026-05-08-suite-parallel-execution.md`
- `docs/superpowers/specs/2026-04-29-s5-s7-512eval-benchmark-matrix-design.md`
- `docs/superpowers/plans/2026-04-29-s5-s7-512eval-benchmark-matrix.md`

Add:

```markdown
> Superseded on 2026-05-08 by `docs/superpowers/specs/2026-05-08-unified-benchmark-runner-design.md` and `docs/superpowers/plans/2026-05-08-unified-benchmark-runner.md`. Do not use this document as active implementation guidance.
```

- [ ] **Step 4: Verify no active guidance still recommends old commands**

Run:

```bash
rg -n "optimize-benchmark|run-llm|run-benchmark-suite|run-benchmark-matrix|aggregate-benchmark-matrix|render-assets|compare-runs|replay-llm-trace|analyze-controller-trace" README.md AGENTS.md docs/superpowers/specs docs/superpowers/plans
```

Expected: matches only in historical/superseded sections or in the new design/plan where old commands are explicitly listed as removed.

- [ ] **Step 5: Commit Task 12**

```bash
git add README.md AGENTS.md docs/superpowers/specs docs/superpowers/plans
git commit -m "docs: document unified benchmark runner workflow"
```

---

### Task 13: End-To-End Smoke Verification

**Files:**
- Modify: `tests/cli/test_cli_smoke.py` if it references old commands
- Modify: `tests/cli/test_cli_end_to_end.py` if it references old commands

- [ ] **Step 1: Update CLI smoke tests to `run-benchmark`**

Use:

```bash
rg -n "optimize-benchmark|run-llm|run-benchmark-suite|render-assets|compare-runs" tests/cli
```

Replace old smoke command expectations with:

```python
result = subprocess.run(
    [
        sys.executable,
        "-m",
        "optimizers.cli",
        "run-benchmark",
        "--help",
    ],
    check=True,
    capture_output=True,
    text=True,
)
assert "run-benchmark" in result.stdout
```

- [ ] **Step 2: Run focused runner and CLI suite**

Run:

```bash
conda run -n msfenicsx pytest -v \
  tests/optimizers/test_benchmark_runner_specs.py \
  tests/optimizers/test_benchmark_runner_supervisor.py \
  tests/optimizers/test_benchmark_runner_run_events.py \
  tests/optimizers/test_benchmark_runner_postprocess.py \
  tests/optimizers/test_benchmark_runner_llm_summary.py \
  tests/optimizers/test_benchmark_runner_comparisons.py \
  tests/optimizers/test_benchmark_runner_igd.py \
  tests/optimizers/test_benchmark_runner_cli.py \
  tests/optimizers/test_benchmark_runner_batch_specs.py \
  tests/cli/test_module_entrypoints.py \
  tests/cli/test_cli_smoke.py
```

Expected: PASS.

- [ ] **Step 3: Run visualization and comparison regression tests**

Run:

```bash
conda run -n msfenicsx pytest -v tests/optimizers/test_compare_runs.py tests/visualization/test_render_assets_fixtures.py
```

Expected: PASS.

- [ ] **Step 4: Run broader optimizer tests**

Run:

```bash
conda run -n msfenicsx pytest -v tests/optimizers
```

Expected: PASS.

- [ ] **Step 5: Confirm no `scenario_runs/logs` is created by tests**

Run:

```bash
test ! -d scenario_runs/logs
```

Expected: exit code 0.

- [ ] **Step 6: Commit final smoke updates**

```bash
git add -A tests/cli tests/optimizers tests/visualization
git commit -m "test: verify unified benchmark runner workflow"
```

---

## Self-Review

- Spec coverage: Tasks 1, 3, 4, 5, 6, 8, 9, 10, 11, and 12 cover the unified command, subprocess no-fork scheduler, server resource policy, per-seed logs, no global logs directory, automatic render/LLM diagnostics, seed-aware comparison, single LLM补跑语义, IGD, old command deletion, batch specs, and docs cleanup.
- Placeholder scan: this plan contains concrete file paths, test commands, expected outcomes, and implementation snippets for every task.
- Type consistency: `CampaignSpec`, `BenchmarkLeaf`, `ResourcePolicy`, and `ComparisonPolicy` are introduced in Task 1 and reused by supervisor, CLI, and comparison tasks with the same field names.
