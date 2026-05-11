# Stage A Artifact Export Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补齐 Stage A paper experiment database 的 artifact 物化、显式命名和索引，不新增 Stage B 实验，不手改结论数据。

**Architecture:** `scenario_runs/` 和 official archives 仍是 source-of-truth；`paper_database/paper_experiment_db/` 是论文入口层。实现应优先复用 `optimizers.comparison_artifacts.build_comparison_bundle`、`optimizers.benchmark_runner.comparisons.plan_campaign_comparisons` 和现有 renderer；新增代码只负责 Stage A export orchestration、series label override、manifest/table/DuckDB 刷新与完整性校验。

**Tech Stack:** Python, YAML/CSV/JSON artifact manipulation, Matplotlib renderers, DuckDB, existing optimizer comparison builders, focused pytest.

---

## 当前判断

这不是 Stage B 新实验。当前缺口属于 Stage A artifact export 没有完全物化到期望目录结构：

- S6 seed23 机制诊断已有三方指标表和 `llm_normal_seed23` / `llm_feedback_off_seed23` 子目录，但 feedback-off archive 自带 comparison 仍是两方 `raw_vs_feedback_off_llm_seed23`。
- `paper_database/paper_experiment_db/figures/s6_seed23_mechanism_ablation/figures/progress_dashboard.png` 的曲线标签来自 duplicate label fallback，出现含糊的 `llm:seed-23` 风格，不够 paper-facing。
- S5 seed11 raw / union / normal LLM 代表案例没有系统化导出到 `paper_database/paper_experiment_db/` 的独立入口。
- `paper_database/paper_experiment_db/figures/main`、`semantic_ablation`、`model_sensitivity`、`algorithm_baseline` 当前为空目录，现有 claim evidence 主要指向 archive 内部 comparison；需要决定是否补“入口索引/软物化”，但不要复制大量重复 run artifacts。
- `docs/superpowers/specs/2026-05-10-final-experiment-database-design.md` 要求 `tables/llm_diagnostics.csv`，当前 `paper_database/paper_experiment_db/tables/` 未见该表；若无法完整生成，至少要在 completeness/manifest 中显式列为 not_materialized 或补 minimal diagnostic table。

## Source Map

### S6 Seed23 Three-Way Mechanism Diagnostic

- Raw source:
  `paper_database/s6_aggressive20/archives/0511_archive__raw_llm-deepseek_v4_flash_5seed/raw/seeds/seed-23`
- Normal LLM source:
  `paper_database/s6_aggressive20/archives/0511_archive__raw_llm-deepseek_v4_flash_5seed/llm-deepseek-v4-flash/seeds/seed-23`
- Feedback-off LLM source:
  `paper_database/s6_aggressive20/archives/0511_archive__feedback_off_deepseek_seed23_diagnostic/llm-feedback-off-deepseek-v4-flash/seeds/seed-23`
- Current paper-facing export root:
  `paper_database/paper_experiment_db/figures/s6_seed23_mechanism_ablation`

### S5 Seed11 Representative Diagnostic

- Raw source:
  `paper_database/s5_aggressive15/archives/0511_archive__raw_llm-deepseek_v4_flash_top5/raw/seeds/seed-11`
- Union source:
  `scenario_runs/s5_aggressive15/0509_0130__raw_union/union/seeds/seed-11`
- Normal LLM source:
  `paper_database/s5_aggressive15/archives/0511_archive__raw_llm-deepseek_v4_flash_top5/llm-deepseek-v4-flash/seeds/seed-11`
- Target root:
  `paper_database/paper_experiment_db/figures/s5_seed11_raw_union_llm_representatives`

Do not use S5 seed11 representative export as a new main result block. It is a qualitative representative-case artifact for paper figures or appendix inspection.

## Files

- Create: `tools/export_stage_a_artifacts.py`
- Modify: `optimizers/comparison_artifacts.py`
- Modify: `visualization/figures/comparison_panels.py`
- Modify: `tests/optimizers/test_compare_runs.py`
- Create: `tests/optimizers/test_stage_a_artifact_export.py`
- Refresh generated artifacts under:
  - `paper_database/paper_experiment_db/figures/s6_seed23_mechanism_ablation/`
  - `paper_database/paper_experiment_db/figures/s5_seed11_raw_union_llm_representatives/`
  - `paper_database/paper_experiment_db/tables/`
  - `paper_database/paper_experiment_db/msfenicsx_experiments.duckdb`
- Modify docs if outputs or paths change:
  - `paper_database/paper_experiment_db/manifest.yaml`
  - `docs/reports/2026-05-10-stage-a-igd-and-paper-assets.md`
  - `docs/superpowers/specs/2026-05-10-final-experiment-database-design.md`
  - `README.md`, `AGENTS.md`, `CLAUDE.md` only if repository guidance changes.

## Task 1: Add Explicit Series Labels To Comparison Bundles

**Files:**
- Modify: `optimizers/comparison_artifacts.py`
- Modify: `tests/optimizers/test_compare_runs.py`

- [ ] **Step 1: Write failing test for display label override**

Add this test to `tests/optimizers/test_compare_runs.py` after `test_compare_runs_disambiguates_same_mode_strategy_variants`:

```python
def test_comparison_bundle_uses_explicit_series_label_overrides(tmp_path: Path) -> None:
    import csv

    from optimizers.comparison_artifacts import build_comparison_bundle

    run_a = tmp_path / "raw" / "seeds" / "seed-23"
    run_b = tmp_path / "llm-normal" / "seeds" / "seed-23"
    run_c = tmp_path / "llm-feedback-off" / "seeds" / "seed-23"
    _seed_run(run_a, "raw")
    _seed_run(run_b, "llm")
    _seed_run(run_c, "llm")
    for run_root in (run_b, run_c):
        (run_root / "run.yaml").write_text(
            "mode: llm\nalgorithm:\n  backbone: nsga2\n  label: NSGA-II\n",
            encoding="utf-8",
        )

    output = tmp_path / "paper_database" / "paper_experiment_db" / "figures" / "s6_seed23_mechanism_ablation"
    build_comparison_bundle(
        runs=[run_a, run_b, run_c],
        output=output,
        comparison_kind="mechanism_ablation",
        benchmark_seed=23,
        series_label_overrides={
            str(run_a): "raw seed23",
            str(run_b): "normal LLM seed23",
            str(run_c): "feedback-off LLM seed23",
        },
    )

    mode_rows = list(csv.DictReader((output / "tables" / "mode_metrics.csv").open()))
    labels = {row["series_label"] for row in mode_rows}
    assert labels == {"raw seed23", "normal LLM seed23", "feedback-off LLM seed23"}
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["series_labels"] == ["raw seed23", "normal LLM seed23", "feedback-off LLM seed23"]
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
conda run -n msfenicsx pytest -q tests/optimizers/test_compare_runs.py::test_comparison_bundle_uses_explicit_series_label_overrides
```

Expected: `TypeError: build_comparison_bundle() got an unexpected keyword argument 'series_label_overrides'`.

- [ ] **Step 3: Implement label override support**

Update the signature of `build_comparison_bundle` in `optimizers/comparison_artifacts.py`:

```python
def build_comparison_bundle(
    *,
    runs: Sequence[Path],
    output: Path,
    comparison_kind: str = "external",
    suite_root: Path | None = None,
    benchmark_seed: int | None = None,
    hires: bool = False,
    series_label_overrides: Mapping[str, str] | None = None,
) -> dict[str, Any]:
```

Immediately after `payloads = [_collect_run_payload(run_root) for run_root in resolved_runs]`, add:

```python
    _apply_series_label_overrides(payloads, series_label_overrides or {})
```

Add this helper near `_disambiguate_duplicate_series_labels`:

```python
def _apply_series_label_overrides(
    payloads: Sequence[dict[str, Any]],
    overrides: Mapping[str, str],
) -> None:
    if not overrides:
        return
    normalized = {str(Path(key)): str(value) for key, value in overrides.items()}
    resolved = {str(Path(key).resolve()): str(value) for key, value in overrides.items()}
    for payload in payloads:
        run_root = Path(payload["run_root"])
        label = normalized.get(str(run_root)) or resolved.get(str(run_root.resolve()))
        if not label:
            continue
        payload["series_label"] = label
        summary_row = payload.get("summary_row")
        if isinstance(summary_row, dict):
            summary_row["series_label"] = label
        timeline_rollup = payload.get("timeline_rollup")
        if isinstance(timeline_rollup, dict):
            timeline_rollup["series_label"] = label
        representative_panel = payload.get("representative_panel")
        if isinstance(representative_panel, dict):
            representative_panel["series_label"] = label
```

Keep `_disambiguate_duplicate_series_labels(payloads)` after the override call; explicit labels should already be unique and will not be changed.

- [ ] **Step 4: Run focused tests**

Run:

```bash
conda run -n msfenicsx pytest -q tests/optimizers/test_compare_runs.py
```

Expected: all tests in `test_compare_runs.py` pass.

## Task 2: Add Stage A Export Orchestrator

**Files:**
- Create: `tools/export_stage_a_artifacts.py`
- Create: `tests/optimizers/test_stage_a_artifact_export.py`

- [ ] **Step 1: Write failing tests for source map and labels**

Create `tests/optimizers/test_stage_a_artifact_export.py`:

```python
from pathlib import Path

from tools.export_stage_a_artifacts import (
    S5_SEED11_REPRESENTATIVE_SOURCES,
    S6_SEED23_MECHANISM_SOURCES,
    stage_a_series_label_overrides,
)


def test_s6_seed23_mechanism_sources_are_three_way() -> None:
    assert list(S6_SEED23_MECHANISM_SOURCES) == [
        "raw_seed23",
        "llm_normal_seed23",
        "llm_feedback_off_seed23",
    ]
    assert S6_SEED23_MECHANISM_SOURCES["raw_seed23"].as_posix().endswith(
        "raw/seeds/seed-23"
    )
    assert S6_SEED23_MECHANISM_SOURCES["llm_normal_seed23"].as_posix().endswith(
        "llm-deepseek-v4-flash/seeds/seed-23"
    )
    assert S6_SEED23_MECHANISM_SOURCES["llm_feedback_off_seed23"].as_posix().endswith(
        "llm-feedback-off-deepseek-v4-flash/seeds/seed-23"
    )


def test_s5_seed11_representative_sources_include_union() -> None:
    assert list(S5_SEED11_REPRESENTATIVE_SOURCES) == [
        "raw_seed11",
        "union_seed11",
        "llm_normal_seed11",
    ]
    assert S5_SEED11_REPRESENTATIVE_SOURCES["union_seed11"].as_posix().endswith(
        "union/seeds/seed-11"
    )


def test_stage_a_label_overrides_are_paper_facing() -> None:
    labels = stage_a_series_label_overrides(
        {
            "raw_seed23": Path("a/raw/seeds/seed-23"),
            "llm_normal_seed23": Path("b/llm/seeds/seed-23"),
            "llm_feedback_off_seed23": Path("c/llm/seeds/seed-23"),
        },
        {
            "raw_seed23": "Raw seed23",
            "llm_normal_seed23": "Normal LLM seed23",
            "llm_feedback_off_seed23": "Feedback-off LLM seed23",
        },
    )
    assert labels == {
        "a/raw/seeds/seed-23": "Raw seed23",
        "b/llm/seeds/seed-23": "Normal LLM seed23",
        "c/llm/seeds/seed-23": "Feedback-off LLM seed23",
    }
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
conda run -n msfenicsx pytest -q tests/optimizers/test_stage_a_artifact_export.py
```

Expected: import failure because `tools/export_stage_a_artifacts.py` does not exist.

- [ ] **Step 3: Create `tools` package and export script**

Create `tools/export_stage_a_artifacts.py`:

```python
"""Stage A paper database artifact export helpers.

This module materializes paper-facing views from existing official archives.
It must not mutate optimizer conclusions or synthesize new experiment results.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path
from typing import Mapping

import duckdb
import yaml

from optimizers.comparison_artifacts import build_comparison_bundle


PAPER_DB_ROOT = Path("paper_database/paper_experiment_db")

S6_SEED23_MECHANISM_SOURCES: dict[str, Path] = {
    "raw_seed23": Path(
        "paper_database/s6_aggressive20/archives/"
        "0511_archive__raw_llm-deepseek_v4_flash_5seed/raw/seeds/seed-23"
    ),
    "llm_normal_seed23": Path(
        "paper_database/s6_aggressive20/archives/"
        "0511_archive__raw_llm-deepseek_v4_flash_5seed/"
        "llm-deepseek-v4-flash/seeds/seed-23"
    ),
    "llm_feedback_off_seed23": Path(
        "paper_database/s6_aggressive20/archives/"
        "0511_archive__feedback_off_deepseek_seed23_diagnostic/"
        "llm-feedback-off-deepseek-v4-flash/seeds/seed-23"
    ),
}

S5_SEED11_REPRESENTATIVE_SOURCES: dict[str, Path] = {
    "raw_seed11": Path(
        "paper_database/s5_aggressive15/archives/"
        "0511_archive__raw_llm-deepseek_v4_flash_top5/raw/seeds/seed-11"
    ),
    "union_seed11": Path(
        "scenario_runs/s5_aggressive15/0509_0130__raw_union/union/seeds/seed-11"
    ),
    "llm_normal_seed11": Path(
        "paper_database/s5_aggressive15/archives/"
        "0511_archive__raw_llm-deepseek_v4_flash_top5/"
        "llm-deepseek-v4-flash/seeds/seed-11"
    ),
}

S6_LABELS = {
    "raw_seed23": "Raw seed23",
    "llm_normal_seed23": "Normal LLM seed23",
    "llm_feedback_off_seed23": "Feedback-off LLM seed23",
}

S5_LABELS = {
    "raw_seed11": "Raw seed11",
    "union_seed11": "Union seed11",
    "llm_normal_seed11": "Normal LLM seed11",
}


def stage_a_series_label_overrides(
    sources: Mapping[str, Path],
    labels: Mapping[str, str],
) -> dict[str, str]:
    return {sources[key].as_posix(): labels[key] for key in sources}


def export_stage_a_artifacts(*, verify_only: bool = False) -> dict[str, object]:
    _verify_sources(S6_SEED23_MECHANISM_SOURCES)
    _verify_sources(S5_SEED11_REPRESENTATIVE_SOURCES)
    if verify_only:
        return {"verified_sources": True}

    mechanism_root = PAPER_DB_ROOT / "figures" / "s6_seed23_mechanism_ablation"
    representative_root = PAPER_DB_ROOT / "figures" / "s5_seed11_raw_union_llm_representatives"

    mechanism_bundle = build_comparison_bundle(
        runs=list(S6_SEED23_MECHANISM_SOURCES.values()),
        output=mechanism_root,
        comparison_kind="mechanism_ablation",
        benchmark_seed=23,
        series_label_overrides=stage_a_series_label_overrides(S6_SEED23_MECHANISM_SOURCES, S6_LABELS),
    )
    representative_bundle = build_comparison_bundle(
        runs=list(S5_SEED11_REPRESENTATIVE_SOURCES.values()),
        output=representative_root,
        comparison_kind="representative_case",
        benchmark_seed=11,
        series_label_overrides=stage_a_series_label_overrides(S5_SEED11_REPRESENTATIVE_SOURCES, S5_LABELS),
    )

    _copy_seed_figure_shortcuts(mechanism_root, S6_SEED23_MECHANISM_SOURCES)
    _copy_seed_figure_shortcuts(representative_root, S5_SEED11_REPRESENTATIVE_SOURCES)
    _write_export_manifest(mechanism_root, S6_SEED23_MECHANISM_SOURCES, S6_LABELS)
    _write_export_manifest(representative_root, S5_SEED11_REPRESENTATIVE_SOURCES, S5_LABELS)
    _refresh_paper_tables()
    _refresh_duckdb()
    return {
        "mechanism_manifest": mechanism_bundle["manifest"],
        "representative_manifest": representative_bundle["manifest"],
    }


def _verify_sources(sources: Mapping[str, Path]) -> None:
    for key, path in sources.items():
        missing = [
            required
            for required in (
                path / "run.yaml",
                path / "optimization_result.json",
                path / "traces" / "evaluation_events.jsonl",
            )
            if not required.exists()
        ]
        if missing:
            raise FileNotFoundError(f"{key} is missing required artifacts: {missing}")


def _copy_seed_figure_shortcuts(output_root: Path, sources: Mapping[str, Path]) -> None:
    for key, source in sources.items():
        target = output_root / key
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)
        figures = source / "figures"
        for name in (
            "layout_initial.png",
            "layout_final.png",
            "pareto_front.png",
            "hypervolume_progress.png",
            "objective_progress.png",
            "operator_phase_heatmap.png",
            "search_trajectory_network.png",
            "temperature_field_knee-candidate.png",
            "gradient_field_knee-candidate.png",
        ):
            src = figures / name
            if src.exists():
                shutil.copy2(src, target / name)


def _write_export_manifest(output_root: Path, sources: Mapping[str, Path], labels: Mapping[str, str]) -> None:
    payload = {
        "sources": {key: path.as_posix() for key, path in sources.items()},
        "labels": dict(labels),
        "artifact_role": output_root.name,
        "manual_data_edits": False,
    }
    (output_root / "stage_a_export_manifest.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def _refresh_paper_tables() -> None:
    tables_root = PAPER_DB_ROOT / "tables"
    tables_root.mkdir(parents=True, exist_ok=True)
    _append_or_replace_artifact_index_row(
        tables_root / "artifact_index.csv",
        {
            "scenario_id": "s5_aggressive15",
            "method_slug": "raw_union_llm",
            "seed": "11",
            "artifact_name": "s5_seed11_raw_union_llm_representatives",
            "artifact_path": (PAPER_DB_ROOT / "figures" / "s5_seed11_raw_union_llm_representatives").as_posix(),
            "exists": "True",
        },
    )
    _write_llm_diagnostics(tables_root / "llm_diagnostics.csv")


def _append_or_replace_artifact_index_row(path: Path, row: dict[str, str]) -> None:
    fieldnames = ["scenario_id", "method_slug", "seed", "artifact_name", "artifact_path", "exists"]
    rows: list[dict[str, str]] = []
    if path.exists():
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    rows = [
        existing
        for existing in rows
        if existing.get("artifact_name") != row["artifact_name"]
        or existing.get("seed") != row["seed"]
        or existing.get("scenario_id") != row["scenario_id"]
    ]
    rows.append(row)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_llm_diagnostics(path: Path) -> None:
    audit_path = Path(
        "paper_database/s6_aggressive20/archives/"
        "0511_archive__feedback_off_deepseek_seed23_diagnostic/"
        "comparisons/raw_vs_feedback_off_llm_seed23/analytics/operator_feedback_audit.json"
    )
    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else {}
    fieldnames = [
        "block_id",
        "scenario_id",
        "method_slug",
        "seed",
        "diagnostic_name",
        "value",
        "source_path",
    ]
    rows = [
        {
            "block_id": "mechanism_ablation_s6_seed23",
            "scenario_id": "s6_aggressive20",
            "method_slug": "llm-feedback-off-deepseek-v4-flash",
            "seed": "23",
            "diagnostic_name": key,
            "value": value,
            "source_path": audit_path.as_posix(),
        }
        for key, value in sorted(audit.items())
        if isinstance(value, (int, float, str, bool))
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _refresh_duckdb() -> None:
    db_path = PAPER_DB_ROOT / "msfenicsx_experiments.duckdb"
    tables_root = PAPER_DB_ROOT / "tables"
    con = duckdb.connect(str(db_path))
    try:
        for csv_path in sorted(tables_root.glob("*.csv")):
            table_name = csv_path.stem
            con.execute(f'DROP TABLE IF EXISTS "{table_name}"')
            con.execute(
                f'CREATE TABLE "{table_name}" AS '
                f"SELECT * FROM read_csv_auto('{csv_path.as_posix()}', header=True)"
            )
    finally:
        con.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export Stage A paper-facing artifacts.")
    parser.add_argument("--verify-only", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    payload = export_stage_a_artifacts(verify_only=args.verify_only)
    print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
    main()
```

If `tools/` is not importable in pytest, create `tools/__init__.py` as an empty file.

- [ ] **Step 4: Run tests**

Run:

```bash
conda run -n msfenicsx pytest -q tests/optimizers/test_stage_a_artifact_export.py
```

Expected: all tests pass.

## Task 3: Regenerate Stage A Paper-Facing Exports

**Files / Artifacts:**
- Refresh: `paper_database/paper_experiment_db/figures/s6_seed23_mechanism_ablation/`
- Create: `paper_database/paper_experiment_db/figures/s5_seed11_raw_union_llm_representatives/`
- Refresh: `paper_database/paper_experiment_db/tables/artifact_index.csv`
- Create or refresh: `paper_database/paper_experiment_db/tables/llm_diagnostics.csv`
- Refresh: `paper_database/paper_experiment_db/msfenicsx_experiments.duckdb`

- [ ] **Step 1: Verify sources without writing**

Run:

```bash
conda run -n msfenicsx python -m tools.export_stage_a_artifacts --verify-only
```

Expected output includes:

```json
{
  "verified_sources": true
}
```

- [ ] **Step 2: Run export**

Run:

```bash
conda run -n msfenicsx python -m tools.export_stage_a_artifacts
```

Expected:

- S6 mechanism export manifest has series labels exactly:
  - `Raw seed23`
  - `Normal LLM seed23`
  - `Feedback-off LLM seed23`
- S5 seed11 representative export exists under:
  `paper_database/paper_experiment_db/figures/s5_seed11_raw_union_llm_representatives`

- [ ] **Step 3: Check expected files**

Run:

```bash
test -f paper_database/paper_experiment_db/figures/s6_seed23_mechanism_ablation/manifest.json
test -f paper_database/paper_experiment_db/figures/s6_seed23_mechanism_ablation/figures/progress_dashboard.png
test -f paper_database/paper_experiment_db/figures/s6_seed23_mechanism_ablation/tables/mode_metrics.csv
test -f paper_database/paper_experiment_db/figures/s5_seed11_raw_union_llm_representatives/manifest.json
test -f paper_database/paper_experiment_db/figures/s5_seed11_raw_union_llm_representatives/figures/final_layout_comparison.png
test -f paper_database/paper_experiment_db/figures/s5_seed11_raw_union_llm_representatives/figures/temperature_field_comparison.png
test -f paper_database/paper_experiment_db/figures/s5_seed11_raw_union_llm_representatives/figures/gradient_field_comparison.png
test -f paper_database/paper_experiment_db/tables/llm_diagnostics.csv
```

Expected: command exits with status `0`.

- [ ] **Step 4: Verify labels from CSV and manifest**

Run:

```bash
python - <<'PY'
import csv, json
from pathlib import Path
root = Path("paper_database/paper_experiment_db/figures/s6_seed23_mechanism_ablation")
manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
print(manifest["series_labels"])
rows = list(csv.DictReader((root / "tables/mode_metrics.csv").open()))
print([row["series_label"] for row in rows])
PY
```

Expected:

```text
['Raw seed23', 'Normal LLM seed23', 'Feedback-off LLM seed23']
['Raw seed23', 'Normal LLM seed23', 'Feedback-off LLM seed23']
```

If ordering differs but the set is correct, adjust the test expectation only if the figure/table generation order is deterministic elsewhere.

## Task 4: Update Manifest And Docs

**Files:**
- Modify: `paper_database/paper_experiment_db/manifest.yaml`
- Modify: `docs/reports/2026-05-10-stage-a-igd-and-paper-assets.md`
- Modify: `docs/superpowers/specs/2026-05-10-final-experiment-database-design.md`

- [ ] **Step 1: Update manifest with new representative export**

Add under `blocks:`:

```yaml
  representative_case_s5_seed11:
    role: representative_case
    scenario_id: s5_aggressive15
    methods:
    - raw
    - union
    - llm-deepseek-v4-flash
    seeds:
    - 11
    nominal_budget: 1280
    current_root: paper_database/paper_experiment_db/figures/s5_seed11_raw_union_llm_representatives
    raw_root: paper_database/s5_aggressive15/archives/0511_archive__raw_llm-deepseek_v4_flash_top5/raw/seeds/seed-11
    union_root: scenario_runs/s5_aggressive15/0509_0130__raw_union/union/seeds/seed-11
    normal_llm_root: paper_database/s5_aggressive15/archives/0511_archive__raw_llm-deepseek_v4_flash_top5/llm-deepseek-v4-flash/seeds/seed-11
    status: complete_single_seed_representative_case_not_main_statistics
```

Add or update `representative_case` to avoid replacing S6 mechanism diagnostic. Use a list:

```yaml
representative_cases:
- id: s6_seed23_mechanism_ablation
  scenario_id: s6_aggressive20
  benchmark_seed: 23
  algorithm_seed: 1023
  root: paper_database/paper_experiment_db/figures/s6_seed23_mechanism_ablation
  role: single_seed_three_way_mechanism_ablation_not_statistical_evidence
- id: s5_seed11_raw_union_llm_representatives
  scenario_id: s5_aggressive15
  benchmark_seed: 11
  root: paper_database/paper_experiment_db/figures/s5_seed11_raw_union_llm_representatives
  role: single_seed_representative_case_not_statistical_evidence
```

Keep the old scalar `representative_case:` only if downstream code still reads it; if kept, point it to S6 and add `representative_cases:` as the new multi-case field.

- [ ] **Step 2: Update Stage A report**

In `docs/reports/2026-05-10-stage-a-igd-and-paper-assets.md`, add a short note under the figure/table usage section:

```markdown
S5 seed11 raw / union / normal DeepSeek LLM representative-case export is materialized at
`paper_database/paper_experiment_db/figures/s5_seed11_raw_union_llm_representatives/`.
It is a single-seed qualitative representative artifact, not a new main statistical block.
```

Also replace any wording implying the feedback-off archive comparison is only two-way paper evidence with:

```markdown
The feedback-off archive keeps a two-way audit comparison for masked-feedback verification, while the paper-facing mechanism figure root uses the three-way raw / normal LLM / feedback-off LLM export.
```

- [ ] **Step 3: Update final database design**

In `docs/superpowers/specs/2026-05-10-final-experiment-database-design.md`, update the required output list so `tables/llm_diagnostics.csv` is no longer aspirational. If the table is generated, write:

```markdown
- `tables/llm_diagnostics.csv` generated from feedback-off prompt/operator audit metadata
```

Add:

```markdown
The S5 seed11 representative-case export is a paper-facing qualitative artifact root under
`paper_database/paper_experiment_db/figures/s5_seed11_raw_union_llm_representatives/`.
It does not define a new performance block and must not be pooled into `main_s5`.
```

## Task 5: Verification

**Files:**
- Verify generated CSV, JSON, PNG/PDF, DuckDB, and docs.

- [ ] **Step 1: Run focused tests**

Run:

```bash
conda run -n msfenicsx pytest -q \
  tests/optimizers/test_compare_runs.py \
  tests/optimizers/test_stage_a_artifact_export.py \
  tests/optimizers/test_benchmark_runner_comparisons.py
```

Expected: all selected tests pass.

- [ ] **Step 2: Verify DuckDB tables include refreshed CSVs**

Run:

```bash
conda run -n msfenicsx python - <<'PY'
import duckdb
db = "paper_database/paper_experiment_db/msfenicsx_experiments.duckdb"
con = duckdb.connect(db, read_only=True)
try:
    tables = {row[0] for row in con.execute("SHOW TABLES").fetchall()}
    print(sorted(tables))
    assert "artifact_index" in tables
    assert "llm_diagnostics" in tables
finally:
    con.close()
PY
```

Expected: assertions pass.

- [ ] **Step 3: Verify no Stage B experiment claims were introduced**

Run:

```bash
rg -n "Stage B|new experiment|new baseline|pooled into main|main_s5.*representative|main_s6.*feedback-off" \
  README.md AGENTS.md CLAUDE.md docs/reports docs/superpowers/specs docs/superpowers/plans paper -S
```

Expected: no new wording claims S5 representative export or S6 feedback-off diagnostic is main statistical evidence. Existing mentions of Stage B in unrelated planning docs are acceptable only if not tied to this export.

- [ ] **Step 4: Check generated figure labels manually from CSV**

Run:

```bash
python - <<'PY'
import csv
for path in [
    "paper_database/paper_experiment_db/figures/s6_seed23_mechanism_ablation/tables/mode_metrics.csv",
    "paper_database/paper_experiment_db/figures/s5_seed11_raw_union_llm_representatives/tables/mode_metrics.csv",
]:
    rows = list(csv.DictReader(open(path, newline="", encoding="utf-8")))
    print(path)
    for row in rows:
        print("  ", row["series_label"], row["mode"], row.get("model"))
PY
```

Expected S6 labels:

- `Raw seed23`
- `Normal LLM seed23`
- `Feedback-off LLM seed23`

Expected S5 labels:

- `Raw seed11`
- `Union seed11`
- `Normal LLM seed11`

## Handoff Prompt For A New Session

Use this prompt in the next conversation:

```text
你在 `/home/xie/msfenicsx` 继续 Stage A 论文整理。先阅读并遵守 `AGENTS.md`、`CLAUDE.md` 和技能要求；文档输出默认用简体中文。不要启动 Stage B 新实验，不要手改实验结论数据。

当前任务是执行计划：
`docs/superpowers/plans/2026-05-11-stage-a-artifact-export-completion.md`

背景判断：
- 这不是 Stage B 新实验，而是 Stage A artifact export 没有完全物化到 paper-facing 目录结构。
- S6 seed23 已有三方机制诊断数据和 `paper_database/paper_experiment_db/figures/s6_seed23_mechanism_ablation/`，但 feedback-off archive 内 comparison 仍是两方 audit comparison，paper-facing 三方 comparison/dashboard 需要显式 label。
- `progress_dashboard.png` 不应显示含糊的 `llm:seed-23`，要通过 renderer/compare bundle 的 series label override 重新生成，标签应为 `Raw seed23`、`Normal LLM seed23`、`Feedback-off LLM seed23`。
- S5 seed11 raw / union / normal DeepSeek LLM 代表案例需要系统化导出到 `paper_database/paper_experiment_db/figures/s5_seed11_raw_union_llm_representatives/`，作为 qualitative representative artifact，不进入 main_s5 统计。
- 优先复用 `optimizers.comparison_artifacts.build_comparison_bundle`、现有 renderers 和 archive 中已有 run artifacts。不要手工编辑 PNG/CSV 来改变结论。

关键 source roots：
- S6 raw seed23:
  `paper_database/s6_aggressive20/archives/0511_archive__raw_llm-deepseek_v4_flash_5seed/raw/seeds/seed-23`
- S6 normal LLM seed23:
  `paper_database/s6_aggressive20/archives/0511_archive__raw_llm-deepseek_v4_flash_5seed/llm-deepseek-v4-flash/seeds/seed-23`
- S6 feedback-off LLM seed23:
  `paper_database/s6_aggressive20/archives/0511_archive__feedback_off_deepseek_seed23_diagnostic/llm-feedback-off-deepseek-v4-flash/seeds/seed-23`
- S5 raw seed11:
  `paper_database/s5_aggressive15/archives/0511_archive__raw_llm-deepseek_v4_flash_top5/raw/seeds/seed-11`
- S5 union seed11:
  `scenario_runs/s5_aggressive15/0509_0130__raw_union/union/seeds/seed-11`
- S5 normal LLM seed11:
  `paper_database/s5_aggressive15/archives/0511_archive__raw_llm-deepseek_v4_flash_top5/llm-deepseek-v4-flash/seeds/seed-11`

执行要求：
1. 按计划 Task 1 先给 `build_comparison_bundle` 增加 `series_label_overrides`，并用 focused tests 验证。
2. 新增 `tools/export_stage_a_artifacts.py`，用已有 source roots 重新生成 S6 三方机制诊断 paper-facing bundle，并导出 S5 seed11 raw/union/LLM representative bundle。
3. 刷新 `paper_database/paper_experiment_db/tables/artifact_index.csv`、补 `tables/llm_diagnostics.csv`，并从 CSV 重建 `paper_database/paper_experiment_db/msfenicsx_experiments.duckdb`。
4. 更新 `paper_database/paper_experiment_db/manifest.yaml` 和相关 Stage A 文档，明确 S5 representative case 和 S6 feedback-off diagnostic 都不是 main statistical evidence。
5. 运行计划中的 focused verification：
   `conda run -n msfenicsx pytest -q tests/optimizers/test_compare_runs.py tests/optimizers/test_stage_a_artifact_export.py tests/optimizers/test_benchmark_runner_comparisons.py`
   以及 DuckDB/table/label 检查。

完成后汇报：
- 改了哪些代码文件和文档文件；
- 重新生成了哪些 artifact roots；
- S6 和 S5 mode_metrics.csv 中的 series labels；
- focused tests 和 DuckDB 检查结果；
- 明确说明没有新增 Stage B 实验、没有把 diagnostic/representative case 纳入 main aggregate。
```

## Self-Review

- Spec coverage: 覆盖 S6 三方机制诊断显式化、feedback-off archive 两方 audit 与 paper-facing 三方 export 的区分、S5 seed11 raw/union/LLM 代表案例导出、`llm_diagnostics.csv` 缺口、manifest/docs/DuckDB 刷新和 focused verification。
- Placeholder scan: 每个任务都有具体文件、代码片段、命令和预期结果；没有 `TBD` 或“适当处理”式占位。
- Type/path consistency: 所有 source roots 来自当前 Stage A archive/source map；新增 paper-facing root 放在 `paper_database/paper_experiment_db/figures/`。
- Evidence boundary: 明确 S6 feedback-off 和 S5 representative case 均为 diagnostic/qualitative artifact，不进入 `main_s5` 或 `main_s6` aggregate。
