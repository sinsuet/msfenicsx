# Archived s1_typical Multi-Scenario Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `s1_typical` into a 3 × 3 × 3 (scenario × optimizer-seed × mode) validation matrix, with initial layouts injected into each NSGA-II initial population so that scenario variation actually reaches the optimizer; permanently shrink the paper-facing budget to `pop=20 × gen=10`; and produce a unified `comparison/` tree with HV, win-rate, and per-scenario breakdowns.

**Architecture:** Three reviewable PRs land sequentially. PR-A lifts the single-seed guardrail, adds `--algorithm-seeds` to `run-benchmark-suite`, adds the `seeds/seed-<N>/opt-<M>/` sublayer, and syncs policy docs. PR-B adds a new `InjectedLayoutSampling` under `optimizers/initial_population.py`, wires it into both drivers, adds a repo-wide `initial_population.jitter_scale` default, and flips all three paper specs to `pop=20 × gen=10`. PR-C adds a new `optimizers/comparison/` package that consumes per-run artifacts and writes `summary.json`, `per_mode_aggregate.json`, `per_scenario_table.md`, `win_rate_table.md`, HV figures, and an HTML index, invoked at the end of `run_benchmark_suite`.

**Tech Stack:** Python 3, pymoo (`pymoo.core.sampling.Sampling`, `pymoo.indicators.hv.Hypervolume`, `pymoo.optimize.minimize`), numpy, yaml, pytest, scipy (for Wilcoxon signed-rank), existing `optimizers/` and `visualization/` packages.

**Reference spec:** [docs/superpowers/specs/2026-04-16-s1-typical-multi-scenario-validation-design.md](../specs/2026-04-16-s1-typical-multi-scenario-validation-design.md).

---

## File Structure

| File | Responsibility | Phase |
|---|---|---|
| `optimizers/cli.py` | Expose `--algorithm-seeds` on `run-benchmark-suite` | PR-A |
| `optimizers/run_suite.py` | Drop single-seed guardrail, add algorithm-seed loop, adopt `seed-<N>/opt-<M>/` layout | PR-A |
| `optimizers/run_layout.py` | Helper for `opt-<aseed>` subdirectory naming | PR-A |
| `optimizers/mode_summary.py` | Walk two-level `seeds/seed-<N>/opt-<M>/` tree | PR-A |
| `optimizers/comparison_summary.py` | Read per-run artifacts from the two-level tree | PR-A |
| `visualization/mode_pages.py` | Render links through the new path layout | PR-A |
| `visualization/comparison_pages.py` | Render links and aligned fields through the new path layout | PR-A |
| `CLAUDE.md`, `AGENTS.md`, `README.md` | Policy text synchronized with new multi-scenario stance | PR-A |
| `tests/optimizers/test_run_suite_multi_seed.py` | Directory-layout and manifest tests for new inner loop (new) | PR-A |
| `optimizers/initial_population.py` | `InjectedLayoutSampling` class (new) | PR-B |
| `optimizers/algorithm_config.py` | Add `initial_population.jitter_scale: 0.05` default | PR-B |
| `optimizers/drivers/raw_driver.py` | Wire `InjectedLayoutSampling` into raw algorithm | PR-B |
| `optimizers/drivers/union_driver.py` | Wire `InjectedLayoutSampling` into union adapter's algorithm | PR-B |
| `scenarios/optimization/s1_typical_raw.yaml` | Budget to `pop=20 × gen=10` | PR-B |
| `scenarios/optimization/s1_typical_union.yaml` | Budget to `pop=20 × gen=10` | PR-B |
| `scenarios/optimization/s1_typical_llm.yaml` | Budget to `pop=20 × gen=10` | PR-B |
| `tests/optimizers/test_initial_population.py` | Unit tests for `InjectedLayoutSampling` (new) | PR-B |
| `optimizers/comparison/__init__.py` | Package marker (new) | PR-C |
| `optimizers/comparison/validation_summary.py` | Build `summary.json` + `per_mode_aggregate.json` (new) | PR-C |
| `optimizers/comparison/tables.py` | Build `per_scenario_table.md` + `win_rate_table.md` (new) | PR-C |
| `optimizers/comparison/figures.py` | Build `hv_bar.svg` + `pareto_overlay.svg` (new) | PR-C |
| `optimizers/comparison/pages.py` | Build `comparison/pages/index.html` stitching tables and figures (new) | PR-C |
| `optimizers/run_suite.py` | Invoke validation comparison builder at end of `run_benchmark_suite` | PR-C |
| `tests/optimizers/test_comparison_validation.py` | Unit tests for the comparison package (new) | PR-C |

---

## Phase 1 — PR-A: Suite driver and documentation

This phase is dependency-free for the rest of the plan; once it lands, the run directory layout accepts the new `opt-<M>/` sublayer, and all existing tests still pass.

### Task A1: Remove single-seed guardrail and update docs

**Files:**
- Modify: `optimizers/run_suite.py:180-183`
- Modify: `CLAUDE.md:166`
- Modify: `AGENTS.md:129`
- Modify: `README.md:182`
- Test: `tests/optimizers/test_run_suite_multi_seed.py` (new)

- [ ] **Step 1: Create the failing test stub for multi-seed acceptance**

Create `tests/optimizers/test_run_suite_multi_seed.py` with this content:

```python
"""Directory-layout tests for multi-scenario-seed × multi-algorithm-seed suite runs."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from optimizers.run_suite import _validate_benchmark_seed_policy


def test_validate_benchmark_seed_policy_accepts_multiple_seeds_on_s1_typical():
    _validate_benchmark_seed_policy(
        scenario_template_id="s1_typical",
        benchmark_seeds=[11, 42, 123],
    )


def test_validate_benchmark_seed_policy_rejects_empty_seeds():
    with pytest.raises(ValueError):
        _validate_benchmark_seed_policy(scenario_template_id="s1_typical", benchmark_seeds=[])


def test_validate_benchmark_seed_policy_rejects_duplicate_seeds():
    with pytest.raises(ValueError):
        _validate_benchmark_seed_policy(
            scenario_template_id="s1_typical",
            benchmark_seeds=[11, 11, 42],
        )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_run_suite_multi_seed.py -v`
Expected: FAIL — the first test raises `ValueError("s1_typical is a fixed single benchmark_seed case...")`, the empty and duplicate cases are not yet checked.

- [ ] **Step 3: Replace the guardrail with neutral validation**

In [optimizers/run_suite.py:180-183](../../../optimizers/run_suite.py#L180-L183), replace:

```python
def _validate_benchmark_seed_policy(*, scenario_template_id: str, benchmark_seeds: Sequence[int]) -> None:
    unique_seeds = {int(seed) for seed in benchmark_seeds}
    if scenario_template_id == "s1_typical" and len(unique_seeds) > 1:
        raise ValueError("s1_typical is a fixed single benchmark_seed case; pass exactly one benchmark_seed.")
```

with:

```python
def _validate_benchmark_seed_policy(*, scenario_template_id: str, benchmark_seeds: Sequence[int]) -> None:
    del scenario_template_id
    seeds = [int(seed) for seed in benchmark_seeds]
    if not seeds:
        raise ValueError("run_benchmark_suite requires at least one benchmark_seed.")
    if len(seeds) != len({seed for seed in seeds}):
        raise ValueError(f"benchmark_seeds must be unique, got {seeds}.")
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_run_suite_multi_seed.py -v`
Expected: PASS for all three.

- [ ] **Step 5: Update CLAUDE.md policy text**

In [CLAUDE.md:166](../../../CLAUDE.md#L166), replace:

```
- `s1_typical` is a fixed single-case benchmark; do not use multiple benchmark seeds to simulate multiple problem instances.
```

with:

```
- `s1_typical` has fixed physics (15 components, per-component power, geometry, boundary conditions); multiple `benchmark_seed` values are permitted specifically to produce different initial component layouts for cross-layout robustness validation.
```

- [ ] **Step 6: Update AGENTS.md policy text**

In [AGENTS.md:129](../../../AGENTS.md#L129), apply the same replacement text as in step 5.

- [ ] **Step 7: Update README.md**

In [README.md:182](../../../README.md#L182), replace:

```
`s1_typical` is a fixed single-case benchmark. Repeat experiments by varying `algorithm.seed`, not by passing multiple `benchmark_seed` values.
```

with:

```
`s1_typical` has fixed physics (15 components, per-component power, geometry, boundary conditions). Cross-layout robustness is validated by passing multiple `--benchmark-seed` values to `run-benchmark-suite`; search stability is validated by combining them with multiple `--algorithm-seeds` values.
```

- [ ] **Step 8: Commit**

```bash
git add optimizers/run_suite.py CLAUDE.md AGENTS.md README.md tests/optimizers/test_run_suite_multi_seed.py
git commit -m "$(cat <<'EOF'
feat(optimizers): accept multiple s1_typical benchmark_seeds

Remove the s1_typical single-seed guardrail so the suite driver can
vary initial layouts across scenarios. Tighten the validator to still
reject empty and duplicate seed lists. Sync CLAUDE.md, AGENTS.md, and
README.md to match the new multi-scenario policy.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

### Task A2: Add `--algorithm-seeds` CLI flag

**Files:**
- Modify: `optimizers/cli.py:35-40`, `optimizers/cli.py:98-106`
- Test: `tests/optimizers/test_optimizer_cli.py` (existing; add one test) — if the file does not exist, create `tests/optimizers/test_cli_algorithm_seeds.py` instead with the test below.

- [ ] **Step 1: Write the failing test for the new flag**

Add to `tests/optimizers/test_optimizer_cli.py` (or create `tests/optimizers/test_cli_algorithm_seeds.py`):

```python
"""Argument-parser coverage for the new --algorithm-seeds flag."""

from __future__ import annotations

from optimizers.cli import build_parser


def test_run_benchmark_suite_parses_repeatable_algorithm_seeds():
    parser = build_parser()
    args = parser.parse_args(
        [
            "run-benchmark-suite",
            "--optimization-spec",
            "scenarios/optimization/s1_typical_raw.yaml",
            "--scenario-runs-root",
            "./scenario_runs",
            "--benchmark-seed",
            "11",
            "--algorithm-seeds",
            "7",
            "--algorithm-seeds",
            "13",
            "--algorithm-seeds",
            "29",
        ]
    )
    assert args.algorithm_seeds == [7, 13, 29]


def test_run_benchmark_suite_algorithm_seeds_defaults_empty():
    parser = build_parser()
    args = parser.parse_args(
        [
            "run-benchmark-suite",
            "--optimization-spec",
            "scenarios/optimization/s1_typical_raw.yaml",
            "--scenario-runs-root",
            "./scenario_runs",
            "--benchmark-seed",
            "11",
        ]
    )
    assert args.algorithm_seeds == []
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_optimizer_cli.py::test_run_benchmark_suite_parses_repeatable_algorithm_seeds -v`
Expected: FAIL — `argparse` raises `unrecognized arguments: --algorithm-seeds 7 ...`.

- [ ] **Step 3: Register the flag in the parser**

In [optimizers/cli.py:35-40](../../../optimizers/cli.py#L35-L40), change the `run-benchmark-suite` block from:

```python
    suite_parser = subparsers.add_parser("run-benchmark-suite")
    suite_parser.add_argument("--optimization-spec", required=True, action="append")
    suite_parser.add_argument("--mode", action="append", default=[])
    suite_parser.add_argument("--scenario-runs-root", required=True)
    suite_parser.add_argument("--benchmark-seed", type=int, action="append", default=[])
    suite_parser.add_argument("--evaluation-workers", type=_positive_int, default=None)
```

to:

```python
    suite_parser = subparsers.add_parser("run-benchmark-suite")
    suite_parser.add_argument("--optimization-spec", required=True, action="append")
    suite_parser.add_argument("--mode", action="append", default=[])
    suite_parser.add_argument("--scenario-runs-root", required=True)
    suite_parser.add_argument("--benchmark-seed", type=int, action="append", default=[])
    suite_parser.add_argument("--algorithm-seeds", type=int, action="append", default=[], dest="algorithm_seeds")
    suite_parser.add_argument("--evaluation-workers", type=_positive_int, default=None)
```

- [ ] **Step 4: Forward the flag to `run_benchmark_suite`**

In [optimizers/cli.py:98-106](../../../optimizers/cli.py#L98-L106), change the call from:

```python
    if args.command == "run-benchmark-suite":
        run_benchmark_suite(
            optimization_spec_paths=[Path(path) for path in args.optimization_spec],
            benchmark_seeds=list(args.benchmark_seed),
            scenario_runs_root=Path(args.scenario_runs_root),
            modes=list(args.mode),
            evaluation_workers=args.evaluation_workers,
        )
        return 0
```

to:

```python
    if args.command == "run-benchmark-suite":
        run_benchmark_suite(
            optimization_spec_paths=[Path(path) for path in args.optimization_spec],
            benchmark_seeds=list(args.benchmark_seed),
            scenario_runs_root=Path(args.scenario_runs_root),
            modes=list(args.mode),
            evaluation_workers=args.evaluation_workers,
            algorithm_seeds=list(args.algorithm_seeds),
        )
        return 0
```

(The `algorithm_seeds` parameter is added to `run_benchmark_suite` in Task A3.)

- [ ] **Step 5: Commit**

```bash
git add optimizers/cli.py tests/optimizers/test_optimizer_cli.py
git commit -m "$(cat <<'EOF'
feat(optimizers): add --algorithm-seeds to run-benchmark-suite

Repeatable integer flag; if omitted, each spec's algorithm.seed is
used, preserving backward compatibility.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

### Task A3: Inner algorithm-seed loop and `opt-<M>/` sublayer in run_suite

**Files:**
- Modify: `optimizers/run_suite.py` (signature, inner loop, artifact path, new helper)
- Test: `tests/optimizers/test_run_suite_multi_seed.py` (extend existing file)

- [ ] **Step 1: Write the failing layout test**

Append to `tests/optimizers/test_run_suite_multi_seed.py`:

```python
from unittest.mock import MagicMock, patch

from optimizers.run_suite import _with_algorithm_seed


def test_with_algorithm_seed_overrides_seed_without_mutating_source():
    spec = MagicMock()
    spec.to_dict.return_value = {
        "schema_version": "1.0",
        "spec_meta": {"spec_id": "dummy"},
        "benchmark_source": {"seed": 11},
        "algorithm": {"family": "genetic", "backbone": "nsga2", "mode": "raw", "seed": 7},
        "design_variables": [],
    }
    with patch("optimizers.run_suite.OptimizationSpec") as optimization_spec_cls:
        new_spec = MagicMock()
        optimization_spec_cls.from_dict.return_value = new_spec

        result = _with_algorithm_seed(spec, 29)

        assert result is new_spec
        forwarded = optimization_spec_cls.from_dict.call_args.args[0]
        assert forwarded["algorithm"]["seed"] == 29
        # source spec untouched
        assert spec.to_dict()["algorithm"]["seed"] == 7
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_run_suite_multi_seed.py::test_with_algorithm_seed_overrides_seed_without_mutating_source -v`
Expected: FAIL — `ImportError: cannot import name '_with_algorithm_seed'`.

- [ ] **Step 3: Add `_with_algorithm_seed` helper in run_suite**

Append to [optimizers/run_suite.py](../../../optimizers/run_suite.py) (below the existing `_with_benchmark_seed` at line 242):

```python
def _with_algorithm_seed(spec: OptimizationSpec, algorithm_seed: int) -> OptimizationSpec:
    payload = deepcopy(spec.to_dict())
    payload["algorithm"]["seed"] = int(algorithm_seed)
    return OptimizationSpec.from_dict(payload)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_run_suite_multi_seed.py::test_with_algorithm_seed_overrides_seed_without_mutating_source -v`
Expected: PASS.

- [ ] **Step 5: Wire `algorithm_seeds` parameter into `run_benchmark_suite`**

In [optimizers/run_suite.py:37-45](../../../optimizers/run_suite.py#L37-L45), change the signature from:

```python
def run_benchmark_suite(
    *,
    optimization_spec_paths: Sequence[Path],
    benchmark_seeds: Sequence[int],
    scenario_runs_root: Path,
    modes: Sequence[str] | None = None,
    evaluation_workers: int | None = None,
    started_at: datetime | None = None,
) -> Path:
```

to:

```python
def run_benchmark_suite(
    *,
    optimization_spec_paths: Sequence[Path],
    benchmark_seeds: Sequence[int],
    scenario_runs_root: Path,
    modes: Sequence[str] | None = None,
    evaluation_workers: int | None = None,
    started_at: datetime | None = None,
    algorithm_seeds: Sequence[int] | None = None,
) -> Path:
```

- [ ] **Step 6: Add inner algorithm-seed loop and `opt-<M>/` artifact path**

In [optimizers/run_suite.py:117-135](../../../optimizers/run_suite.py#L117-L135), replace the inner `for seed in effective_seeds:` block:

```python
        for seed in effective_seeds:
            seeded_spec = _with_benchmark_seed(optimization_spec, seed)
            base_case = generate_benchmark_case(spec_path, seeded_spec)
            evaluation_spec = load_spec(resolve_evaluation_spec_path(spec_path, seeded_spec))
            run = _dispatch_run(
                base_case,
                seeded_spec,
                evaluation_spec,
                spec_path,
                evaluation_workers=evaluation_workers,
            )
            evaluation_payload = evaluation_spec.to_dict() if hasattr(evaluation_spec, "to_dict") else dict(evaluation_spec)
            write_optimization_artifacts(
                mode_root / "seeds" / f"seed-{seed}",
                run,
                mode_id=mode,
                seed=seed,
                objective_definitions=list(evaluation_payload["objectives"]),
            )
```

with:

```python
        default_algorithm_seed = int(optimization_spec.algorithm["seed"])
        effective_algorithm_seeds = (
            [int(aseed) for aseed in algorithm_seeds]
            if algorithm_seeds
            else [default_algorithm_seed]
        )
        for seed in effective_seeds:
            for aseed in effective_algorithm_seeds:
                seeded_spec = _with_algorithm_seed(
                    _with_benchmark_seed(optimization_spec, seed),
                    aseed,
                )
                base_case = generate_benchmark_case(spec_path, seeded_spec)
                evaluation_spec = load_spec(resolve_evaluation_spec_path(spec_path, seeded_spec))
                run = _dispatch_run(
                    base_case,
                    seeded_spec,
                    evaluation_spec,
                    spec_path,
                    evaluation_workers=evaluation_workers,
                )
                evaluation_payload = evaluation_spec.to_dict() if hasattr(evaluation_spec, "to_dict") else dict(evaluation_spec)
                write_optimization_artifacts(
                    mode_root / "seeds" / f"seed-{seed}" / f"opt-{aseed}",
                    run,
                    mode_id=mode,
                    seed=seed,
                    objective_definitions=list(evaluation_payload["objectives"]),
                )
```

- [ ] **Step 7: Extend the top-level manifest to record algorithm seeds**

In [optimizers/run_suite.py:82-96](../../../optimizers/run_suite.py#L82-L96), extend the top-level manifest payload to include both seed lists. Replace:

```python
    write_manifest(
        run_root / "manifest.json",
        {
            "scenario_template_id": scenario_template_id,
            "run_id": run_id,
            "mode_ids": list(selected_modes),
            "benchmark_seeds": list(effective_seeds),
            "created_at": effective_started_at.isoformat(),
            "directories": {
                "shared": "shared",
                **{mode: mode for mode in selected_modes},
                **({"comparison": "comparison"} if len(selected_modes) > 1 else {}),
            },
        },
    )
```

with:

```python
    global_algorithm_seeds = (
        [int(aseed) for aseed in algorithm_seeds] if algorithm_seeds else None
    )
    write_manifest(
        run_root / "manifest.json",
        {
            "scenario_template_id": scenario_template_id,
            "run_id": run_id,
            "mode_ids": list(selected_modes),
            "benchmark_seeds": list(effective_seeds),
            "algorithm_seeds": global_algorithm_seeds,
            "created_at": effective_started_at.isoformat(),
            "directories": {
                "shared": "shared",
                **{mode: mode for mode in selected_modes},
                **({"comparison": "comparison"} if len(selected_modes) > 1 else {}),
            },
        },
    )
```

Also extend the per-mode manifest at [optimizers/run_suite.py:101-116](../../../optimizers/run_suite.py#L101-L116) to record the effective algorithm seeds for that mode. Add `"algorithm_seeds": effective_algorithm_seeds,` inside the per-mode `write_manifest` payload (needs to be written after `effective_algorithm_seeds` has been computed, so move the `write_manifest` call inside the loop after the per-mode seed list is known, or compute the effective list at the top of the `for mode` body before the per-mode manifest call — the latter is simpler):

```python
    for mode in selected_modes:
        spec_path, optimization_spec = spec_by_mode[mode]
        mode_root = initialize_mode_root(run_root, mode=mode)
        default_algorithm_seed = int(optimization_spec.algorithm["seed"])
        effective_algorithm_seeds = (
            [int(aseed) for aseed in algorithm_seeds]
            if algorithm_seeds
            else [default_algorithm_seed]
        )
        write_manifest(
            mode_root / "manifest.json",
            {
                "mode_id": mode,
                "optimization_spec_path": str(spec_path),
                "benchmark_seeds": list(effective_seeds),
                "algorithm_seeds": list(effective_algorithm_seeds),
                "directories": {
                    "logs": "logs",
                    "summaries": "summaries",
                    "pages": "pages",
                    "figures": "figures",
                    "reports": "reports",
                    "seeds": "seeds",
                },
            },
        )
        for seed in effective_seeds:
            for aseed in effective_algorithm_seeds:
                seeded_spec = _with_algorithm_seed(
                    _with_benchmark_seed(optimization_spec, seed),
                    aseed,
                )
                base_case = generate_benchmark_case(spec_path, seeded_spec)
                evaluation_spec = load_spec(resolve_evaluation_spec_path(spec_path, seeded_spec))
                run = _dispatch_run(
                    base_case,
                    seeded_spec,
                    evaluation_spec,
                    spec_path,
                    evaluation_workers=evaluation_workers,
                )
                evaluation_payload = evaluation_spec.to_dict() if hasattr(evaluation_spec, "to_dict") else dict(evaluation_spec)
                write_optimization_artifacts(
                    mode_root / "seeds" / f"seed-{seed}" / f"opt-{aseed}",
                    run,
                    mode_id=mode,
                    seed=seed,
                    objective_definitions=list(evaluation_payload["objectives"]),
                )
```

Make sure the `default_algorithm_seed / effective_algorithm_seeds` computation lives only at the top of this `for mode` body — do not duplicate it inside the scenario loop from Step 6.

- [ ] **Step 8: Write the directory-layout integration test**

Append to `tests/optimizers/test_run_suite_multi_seed.py`:

```python
from datetime import datetime
import json


def test_run_benchmark_suite_writes_opt_sublayer_for_each_seed_combo(tmp_path):
    pytest.importorskip("pymoo")
    from optimizers.run_suite import run_benchmark_suite

    scenario_runs_root = tmp_path / "runs"
    run_root = run_benchmark_suite(
        optimization_spec_paths=[Path("scenarios/optimization/s1_typical_raw.yaml")],
        benchmark_seeds=[11, 42],
        algorithm_seeds=[7, 13],
        scenario_runs_root=scenario_runs_root,
        modes=["raw"],
        evaluation_workers=1,
        started_at=datetime(2026, 4, 16, 12, 0),
    )
    raw_seeds_root = run_root / "raw" / "seeds"
    for bseed in (11, 42):
        for aseed in (7, 13):
            opt_root = raw_seeds_root / f"seed-{bseed}" / f"opt-{aseed}"
            assert opt_root.is_dir(), f"missing {opt_root}"
            assert (opt_root / "optimization_result.json").is_file()
            assert (opt_root / "manifest.json").is_file()
    top_manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    assert top_manifest["benchmark_seeds"] == [11, 42]
    assert top_manifest["algorithm_seeds"] == [7, 13]
```

Mark the test with `@pytest.mark.slow` only if a corresponding marker is already registered in the repo; otherwise leave it unmarked and it will run in the full suite. This test takes roughly 30 seconds at `pop=20 × gen=10`; if that is too slow, gate it with `@pytest.mark.skipif(os.environ.get("FAST") == "1", reason="runs real pymoo loop")`.

- [ ] **Step 9: Run the layout test to verify it passes**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_run_suite_multi_seed.py -v`
Expected: PASS (4 layout directories + 4 opt-sublayers created, top manifest lists both seed axes).

- [ ] **Step 10: Commit**

```bash
git add optimizers/run_suite.py tests/optimizers/test_run_suite_multi_seed.py
git commit -m "$(cat <<'EOF'
feat(optimizers): add algorithm-seed loop and opt-<M>/ sublayer

run_benchmark_suite gains an algorithm_seeds parameter; every
(benchmark_seed, algorithm_seed) pair now lands under
seeds/seed-<N>/opt-<M>/. Per-mode and top-level manifests record
both seed axes.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

### Task A4: Update mode_summary and comparison_summary consumers

**Files:**
- Modify: `optimizers/mode_summary.py:19-47`, `_iter_seed_roots` at line 87-94
- Modify: `optimizers/comparison_summary.py:45-113` (consumes `seeds/seed-<N>/...` paths)
- Test: extend `tests/optimizers/test_run_suite_multi_seed.py`

- [ ] **Step 1: Write the failing consumer test**

Append to `tests/optimizers/test_run_suite_multi_seed.py`:

```python
from optimizers.mode_summary import build_mode_summaries


def test_build_mode_summaries_reads_opt_sublayer(tmp_path):
    pytest.importorskip("pymoo")
    from datetime import datetime
    from optimizers.run_suite import run_benchmark_suite

    run_root = run_benchmark_suite(
        optimization_spec_paths=[Path("scenarios/optimization/s1_typical_raw.yaml")],
        benchmark_seeds=[11],
        algorithm_seeds=[7, 13],
        scenario_runs_root=tmp_path / "runs",
        modes=["raw"],
        evaluation_workers=1,
        started_at=datetime(2026, 4, 16, 12, 0),
    )
    written = build_mode_summaries(run_root / "raw")
    # one progress timeline per (bseed, aseed)
    timeline_keys = [key for key in written if key.startswith("progress_timeline__")]
    assert {"progress_timeline__seed-11__opt-7", "progress_timeline__seed-11__opt-13"} <= set(timeline_keys)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_run_suite_multi_seed.py::test_build_mode_summaries_reads_opt_sublayer -v`
Expected: FAIL — existing `_iter_seed_roots` only yields `seed-*/` directories; there are no `evaluation_events.jsonl` at that level and no per-(seed, opt) output keys.

- [ ] **Step 3: Refactor `_iter_seed_roots` to yield (bseed, aseed, path)**

In [optimizers/mode_summary.py:87-94](../../../optimizers/mode_summary.py#L87-L94), replace the existing helper:

```python
def _iter_seed_roots(mode_root: Path) -> list[Path]:
    seeds_root = mode_root / "seeds"
    if not seeds_root.exists():
        return []
    return sorted(
        [path for path in seeds_root.iterdir() if path.is_dir() and path.name.startswith("seed-")],
        key=lambda path: int(path.name.removeprefix("seed-")),
    )
```

with:

```python
def _iter_seed_roots(mode_root: Path) -> list[tuple[int, int, Path]]:
    seeds_root = mode_root / "seeds"
    if not seeds_root.exists():
        return []
    entries: list[tuple[int, int, Path]] = []
    for seed_dir in sorted(
        [path for path in seeds_root.iterdir() if path.is_dir() and path.name.startswith("seed-")],
        key=lambda path: int(path.name.removeprefix("seed-")),
    ):
        benchmark_seed = int(seed_dir.name.removeprefix("seed-"))
        opt_dirs = sorted(
            [path for path in seed_dir.iterdir() if path.is_dir() and path.name.startswith("opt-")],
            key=lambda path: int(path.name.removeprefix("opt-")),
        )
        for opt_dir in opt_dirs:
            algorithm_seed = int(opt_dir.name.removeprefix("opt-"))
            entries.append((benchmark_seed, algorithm_seed, opt_dir))
    return entries
```

- [ ] **Step 4: Update `build_mode_summaries` to iterate the triplet**

In [optimizers/mode_summary.py:19-47](../../../optimizers/mode_summary.py#L19-L47), replace the loop body:

```python
    for seed_root in _iter_seed_roots(root):
        seed_name = seed_root.name
        evaluation_rows = load_jsonl_rows(seed_root / "evaluation_events.jsonl")
        timeline = build_progress_timeline(evaluation_rows)
        milestones = build_progress_milestones(timeline)
        timeline_path = summaries_root / f"progress_timeline__{seed_name}.jsonl"
        milestones_path = summaries_root / f"milestones__{seed_name}.json"
        _write_jsonl(timeline_path, timeline)
        _write_json(milestones_path, milestones)
        written[f"progress_timeline__{seed_name}"] = str(timeline_path.relative_to(root).as_posix())
        written[f"milestones__{seed_name}"] = str(milestones_path.relative_to(root).as_posix())
        result_payload = _load_json(seed_root / "optimization_result.json")
        seed_rows.append(
            {
                "seed": int(seed_name.removeprefix("seed-")),
                "run_id": str(result_payload["run_meta"]["run_id"]),
                ...
            }
        )
```

with:

```python
    for benchmark_seed, algorithm_seed, opt_root in _iter_seed_roots(root):
        label = f"seed-{benchmark_seed}__opt-{algorithm_seed}"
        evaluation_rows = load_jsonl_rows(opt_root / "evaluation_events.jsonl")
        timeline = build_progress_timeline(evaluation_rows)
        milestones = build_progress_milestones(timeline)
        timeline_path = summaries_root / f"progress_timeline__{label}.jsonl"
        milestones_path = summaries_root / f"milestones__{label}.json"
        _write_jsonl(timeline_path, timeline)
        _write_json(milestones_path, milestones)
        written[f"progress_timeline__{label}"] = str(timeline_path.relative_to(root).as_posix())
        written[f"milestones__{label}"] = str(milestones_path.relative_to(root).as_posix())
        result_payload = _load_json(opt_root / "optimization_result.json")
        seed_rows.append(
            {
                "seed": benchmark_seed,
                "algorithm_seed": algorithm_seed,
                "run_id": str(result_payload["run_meta"]["run_id"]),
                "progress_timeline": str(timeline_path.relative_to(root).as_posix()),
                "milestones": str(milestones_path.relative_to(root).as_posix()),
                "baseline_feasible": bool(result_payload["aggregate_metrics"].get("baseline_feasible", False)),
                "first_feasible_eval": result_payload["aggregate_metrics"].get("first_feasible_eval"),
                "optimizer_feasible_rate": result_payload["aggregate_metrics"].get(
                    "optimizer_feasible_rate",
                    result_payload["aggregate_metrics"].get("feasible_rate"),
                ),
                "pareto_size": int(result_payload["aggregate_metrics"].get("pareto_size", 0)),
                "final_timeline": timeline[-1] if timeline else {},
                "representatives": _discover_representatives(opt_root),
            }
        )
```

Also update the final sort and seed-list derivation:

```python
    seed_rows.sort(key=lambda row: (int(row["seed"]), int(row["algorithm_seed"])))
```

And in the `mode_summary_payload`, change `"seeds": [int(row["seed"]) for row in seed_rows]` to also include the pair:

```python
        "seed_pairs": [
            {"benchmark_seed": int(row["seed"]), "algorithm_seed": int(row["algorithm_seed"])}
            for row in seed_rows
        ],
```

Keep the legacy `"seeds"` key as an alias so existing readers still resolve; populate it as a unique ordered list of benchmark seeds:

```python
        "seeds": sorted({int(row["seed"]) for row in seed_rows}),
```

- [ ] **Step 5: Update `comparison_summary.py` to consume the sublayer**

In [optimizers/comparison_summary.py:45-113](../../../optimizers/comparison_summary.py#L45-L113), the `for seed_row in seed_summary.get("rows", []):` loop needs `algorithm_seed` plumbed into the row. Change each `seed = int(seed_row["seed"])` block to also read `algorithm_seed = int(seed_row["algorithm_seed"])`, and replace every path `mode_root / "seeds" / f"seed-{seed}" / ...` with `mode_root / "seeds" / f"seed-{seed}" / f"opt-{algorithm_seed}" / ...`. Also add `"algorithm_seed": algorithm_seed,` into the `seed_delta_rows`, `progress_rows`, `pareto_rows`, `field_rows`, and `controller_rows` dict literals.

Concretely:

```python
        for seed_row in seed_summary.get("rows", []):
            seed = int(seed_row["seed"])
            algorithm_seed = int(seed_row["algorithm_seed"])
            opt_root = mode_root / "seeds" / f"seed-{seed}" / f"opt-{algorithm_seed}"
            timeline = load_jsonl_rows(mode_root / seed_row["progress_timeline"])
            progress_rows.append(
                {"mode_id": mode, "seed": seed, "algorithm_seed": algorithm_seed, "timeline": timeline}
            )
            final_timeline = dict(seed_row.get("final_timeline", {}))
            seed_delta_rows.append(
                {
                    "mode_id": mode,
                    "seed": seed,
                    "algorithm_seed": algorithm_seed,
                    "baseline_feasible": bool(seed_row.get("baseline_feasible", False)),
                    "first_feasible_eval": seed_row.get("first_feasible_eval"),
                    "optimizer_feasible_rate": seed_row.get("optimizer_feasible_rate"),
                    "pareto_size": seed_row.get("pareto_size"),
                    "best_temperature_max": final_timeline.get("best_temperature_max_so_far"),
                    "best_gradient_rms": final_timeline.get("best_gradient_rms_so_far"),
                }
            )
            pareto_rows.append(
                {
                    "mode_id": mode,
                    "seed": seed,
                    "algorithm_seed": algorithm_seed,
                    "pareto_size": seed_row.get("pareto_size"),
                }
            )
            representative_root = _resolve_field_representative_root(opt_root / "representatives")
            if representative_root is not None and (representative_root / "summaries" / "field_view.json").exists():
                field_view = _load_json(representative_root / "summaries" / "field_view.json")
                field_rows.append(
                    {
                        "mode_id": mode,
                        "seed": seed,
                        "algorithm_seed": algorithm_seed,
                        "representative_id": representative_root.name,
                        "representative_root": str(representative_root.relative_to(root).as_posix()),
                        "field_view_path": str(
                            (representative_root / "summaries" / "field_view.json").relative_to(root).as_posix()
                        ),
                        "temperature_grid_path": str(
                            (representative_root / "fields" / "temperature_grid.npz").relative_to(root).as_posix()
                        ),
                        "gradient_grid_path": str(
                            (representative_root / "fields" / "gradient_magnitude_grid.npz").relative_to(root).as_posix()
                        ),
                        "panel_domain": field_view.get("panel_domain", {}),
                        "layout": field_view.get("layout", {}),
                        "temperature_grid_shape": field_view.get("temperature", {}).get("grid_shape"),
                        "gradient_grid_shape": field_view.get("gradient_magnitude", {}).get("grid_shape"),
                        "temperature_min": field_view.get("temperature", {}).get("min"),
                        "temperature_max": field_view.get("temperature", {}).get("max"),
                        "gradient_min": field_view.get("gradient_magnitude", {}).get("min"),
                        "gradient_max": field_view.get("gradient_magnitude", {}).get("max"),
                        "hotspot": field_view.get("temperature", {}).get("hotspot"),
                    }
                )
            controller_trace_path = opt_root / "controller_trace.json"
            if controller_trace_path.exists():
                controller_rows.append(
                    {
                        "mode_id": mode,
                        "seed": seed,
                        "algorithm_seed": algorithm_seed,
                        "selected_operator_counts": dict(
                            Counter(
                                str(row.get("selected_operator_id", ""))
                                for row in _load_json(controller_trace_path)
                                if row.get("selected_operator_id")
                            )
                        ),
                    }
                )
```

- [ ] **Step 6: Run the consumer test to verify it passes**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_run_suite_multi_seed.py -v`
Expected: PASS (three tests including the new consumer test).

- [ ] **Step 7: Commit**

```bash
git add optimizers/mode_summary.py optimizers/comparison_summary.py tests/optimizers/test_run_suite_multi_seed.py
git commit -m "$(cat <<'EOF'
feat(optimizers): mode and comparison summaries read opt-<M>/ sublayer

_iter_seed_roots now yields (benchmark_seed, algorithm_seed, opt_root).
mode_summary writes per-(bseed, aseed) progress timelines and
milestones. comparison_summary threads algorithm_seed through seed
delta, progress, pareto, field, and controller rows.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

### Task A5: Update visualization consumers (mode_pages, comparison_pages)

**Files:**
- Modify: `visualization/mode_pages.py:52, 91, 97, 101, 235`
- Modify: `visualization/comparison_pages.py:286, 342, 359, 418, 423`
- Test: run existing `tests/visualization/` tests

- [ ] **Step 1: Update `mode_pages.py` path composition**

In [visualization/mode_pages.py](../../../visualization/mode_pages.py), every existing construction of `seed-<N>/representatives/...` must pass through `opt-<aseed>/` too. For each seed row the page renderer reads, use the `algorithm_seed` now present on each row (plumbed in Task A4). Update lines 52, 91, 97, and 101 to embed `opt-{int(row['algorithm_seed'])}` after the `seed-{...}` segment, and update the seed bullet copy at line 235 to mention both seeds:

```python
        f"- seed-{int(row['seed'])}/opt-{int(row['algorithm_seed'])}: first feasible "
        f"{row.get('first_feasible_eval', 'n/a')}, "
```

- [ ] **Step 2: Update `comparison_pages.py` path composition**

In [visualization/comparison_pages.py](../../../visualization/comparison_pages.py):

- Line 286: extend `seed_text` to account for multiple `(benchmark_seed, algorithm_seed)` combinations, e.g. use `"aligned representatives"` whenever the set contains more than one `(seed, algorithm_seed)` pair.
- Lines 342, 359: build the subtitle as `f"seed-{int(row.get('seed', 0))}/opt-{int(row.get('algorithm_seed', 0))} / {str(row.get('representative_id', 'rep'))}"`.
- Lines 418, 423: include the `algorithm_seed` in the bullet, mirroring the mode page update.

- [ ] **Step 3: Run visualization tests**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/visualization/ -v`
Expected: PASS (existing tests cover page generation; if any test hard-codes `seed-11/...` without an `opt-<M>` layer, update the fixture and the corresponding expected string to use `seed-11/opt-7`).

- [ ] **Step 4: Commit**

```bash
git add visualization/mode_pages.py visualization/comparison_pages.py tests/visualization/
git commit -m "$(cat <<'EOF'
feat(visualization): mode and comparison pages link through opt-<M>/

Embed the algorithm seed in representative page URLs and bullet copy
so multi-scenario × multi-optimizer-seed runs resolve correctly.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

### Task A6: Full test sweep for Phase 1

- [ ] **Step 1: Run the full suite**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v`
Expected: PASS. Any failures here indicate another consumer of `seeds/seed-<N>/` that was missed; fix it in place and commit as a follow-up under this task rather than opening the PR with red CI.

- [ ] **Step 2: Open PR-A for review**

Push the branch, open a PR titled `feat(optimizers): suite driver accepts multi-scenario × multi-algorithm seeds`, summary referencing §7.1 of the spec.

---

## Phase 2 — PR-B: Initial layout injection and budget update

This phase depends on PR-A only for the path layout. Code paths touched here are driver-internal.

### Task B1: Implement `InjectedLayoutSampling`

**Files:**
- Create: `optimizers/initial_population.py`
- Create: `tests/optimizers/test_initial_population.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/optimizers/test_initial_population.py`:

```python
"""Unit tests for InjectedLayoutSampling."""

from __future__ import annotations

import numpy as np
import pytest

from core.schema.io import load_case
from optimizers.codec import extract_decision_vector
from optimizers.initial_population import InjectedLayoutSampling
from optimizers.io import generate_benchmark_case, load_optimization_spec
from optimizers.problem import ThermalOptimizationProblem
from evaluation.io import load_spec
from optimizers.io import resolve_evaluation_spec_path


RAW_SPEC_PATH = "scenarios/optimization/s1_typical_raw.yaml"


@pytest.fixture(scope="module")
def problem_and_anchor():
    optimization_spec = load_optimization_spec(RAW_SPEC_PATH)
    base_case = generate_benchmark_case(RAW_SPEC_PATH, optimization_spec)
    evaluation_spec = load_spec(resolve_evaluation_spec_path(RAW_SPEC_PATH, optimization_spec))
    problem = ThermalOptimizationProblem(base_case, optimization_spec, evaluation_spec, evaluation_workers=1)
    try:
        anchor = extract_decision_vector(base_case, optimization_spec)
        yield problem, anchor
    finally:
        problem.close()


def _sample(problem, anchor, *, n_samples: int, jitter_scale: float = 0.05, algorithm_seed: int = 7, scenario_seed: int = 11):
    sampler = InjectedLayoutSampling(
        anchor_vector=anchor,
        jitter_scale=jitter_scale,
        algorithm_seed=algorithm_seed,
        scenario_seed=scenario_seed,
    )
    return sampler._do(problem, n_samples)


def test_first_sample_equals_anchor(problem_and_anchor):
    problem, anchor = problem_and_anchor
    samples = _sample(problem, anchor, n_samples=20)
    assert np.allclose(samples[0], anchor)


def test_samples_respect_bounds(problem_and_anchor):
    problem, anchor = problem_and_anchor
    samples = _sample(problem, anchor, n_samples=20)
    assert np.all(samples >= problem.xl - 1e-12)
    assert np.all(samples <= problem.xu + 1e-12)


def test_reproducibility(problem_and_anchor):
    problem, anchor = problem_and_anchor
    a = _sample(problem, anchor, n_samples=20)
    b = _sample(problem, anchor, n_samples=20)
    assert np.array_equal(a, b)


def test_different_scenario_seeds_produce_different_samples(problem_and_anchor):
    problem, anchor = problem_and_anchor
    a = _sample(problem, anchor, n_samples=20, scenario_seed=11)
    b = _sample(problem, anchor, n_samples=20, scenario_seed=42)
    # anchors match; jittered tail differs
    assert np.allclose(a[0], b[0])
    assert not np.array_equal(a[1:], b[1:])


def test_jitter_statistics(problem_and_anchor):
    problem, anchor = problem_and_anchor
    jitter_scale = 0.05
    samples = _sample(problem, anchor, n_samples=2000, jitter_scale=jitter_scale)
    span = problem.xu - problem.xl
    unbounded_deltas = (samples[1:] - anchor) / span
    empirical_std = float(np.std(unbounded_deltas))
    # clipping shrinks std relative to the unclipped N(0, jitter_scale); require
    # that the empirical std is within 50% of the configured target.
    assert empirical_std <= jitter_scale * 1.05
    assert empirical_std >= jitter_scale * 0.50
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_initial_population.py -v`
Expected: FAIL — `ImportError: cannot import name 'InjectedLayoutSampling' from 'optimizers.initial_population'`.

- [ ] **Step 3: Implement the sampling class**

Create `optimizers/initial_population.py`:

```python
"""Initial population construction for NSGA-II: inject the scenario layout plus jitter."""

from __future__ import annotations

from typing import Any

import numpy as np
from pymoo.core.sampling import Sampling


class InjectedLayoutSampling(Sampling):
    """Seed the initial population with the scenario's decision vector plus Gaussian jitter.

    Sample 0 is exactly ``anchor_vector``. Samples 1..n-1 are drawn as
    ``anchor_vector + N(0, jitter_scale * span)`` and clipped to the problem bounds,
    where ``span = problem.xu - problem.xl``. The sampling RNG is seeded deterministically
    as ``algorithm_seed * 7919 + scenario_seed`` so the initial population is reproducible
    given the two seeds, independently of pymoo's internal RNG.
    """

    def __init__(
        self,
        *,
        anchor_vector: np.ndarray,
        jitter_scale: float,
        algorithm_seed: int,
        scenario_seed: int,
    ) -> None:
        super().__init__()
        self.anchor_vector = np.asarray(anchor_vector, dtype=np.float64)
        self.jitter_scale = float(jitter_scale)
        self.algorithm_seed = int(algorithm_seed)
        self.scenario_seed = int(scenario_seed)

    def _do(self, problem: Any, n_samples: int, **kwargs: Any) -> np.ndarray:
        del kwargs
        n_samples = int(n_samples)
        if n_samples <= 0:
            return np.empty((0, self.anchor_vector.size), dtype=np.float64)
        xl = np.asarray(problem.xl, dtype=np.float64)
        xu = np.asarray(problem.xu, dtype=np.float64)
        span = xu - xl
        rng = np.random.default_rng(self.algorithm_seed * 7919 + self.scenario_seed)
        samples = np.empty((n_samples, self.anchor_vector.size), dtype=np.float64)
        samples[0] = np.clip(self.anchor_vector, xl, xu)
        if n_samples > 1:
            noise = rng.normal(loc=0.0, scale=self.jitter_scale * span, size=(n_samples - 1, self.anchor_vector.size))
            jittered = self.anchor_vector + noise
            samples[1:] = np.clip(jittered, xl, xu)
        return samples
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_initial_population.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add optimizers/initial_population.py tests/optimizers/test_initial_population.py
git commit -m "$(cat <<'EOF'
feat(optimizers): add InjectedLayoutSampling for NSGA-II initial population

Seeds sample 0 with the scenario's decision vector and draws the rest
as anchor + N(0, jitter_scale * span), clipped to problem bounds.
Sampling RNG derived deterministically from (algorithm_seed,
scenario_seed) so runs are reproducible.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

### Task B2: Add jitter_scale default in algorithm_config

**Files:**
- Modify: `optimizers/algorithm_config.py:14-63`
- Test: extend `tests/optimizers/test_algorithm_config.py` if it exists; otherwise add an inline test below.

- [ ] **Step 1: Write the failing test**

Create or extend `tests/optimizers/test_algorithm_config.py`:

```python
"""Defaults for the initial population configuration."""

from __future__ import annotations

from optimizers.algorithm_config import resolve_algorithm_config


def test_initial_population_jitter_scale_default_for_nsga2_raw():
    spec = {
        "algorithm": {
            "family": "genetic",
            "backbone": "nsga2",
            "mode": "raw",
            "seed": 7,
            "population_size": 20,
            "num_generations": 10,
        },
    }
    config = resolve_algorithm_config(None, spec)
    assert config["parameters"]["initial_population"]["jitter_scale"] == 0.05


def test_initial_population_jitter_scale_default_for_nsga2_union():
    spec = {
        "algorithm": {
            "family": "genetic",
            "backbone": "nsga2",
            "mode": "union",
            "seed": 7,
            "population_size": 20,
            "num_generations": 10,
        },
    }
    config = resolve_algorithm_config(None, spec)
    assert config["parameters"]["initial_population"]["jitter_scale"] == 0.05
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_algorithm_config.py -v`
Expected: FAIL — `KeyError: 'initial_population'`.

- [ ] **Step 3: Add the default**

In [optimizers/algorithm_config.py:14-22](../../../optimizers/algorithm_config.py#L14-L22), update the `("genetic", "nsga2", "raw")` and `("genetic", "nsga2", "union")` entries:

```python
    ("genetic", "nsga2", "raw"): {
        "crossover": {"operator": "sbx", "eta": 15, "prob": 0.9},
        "mutation": {"operator": "pm", "eta": 20},
        "initial_population": {"jitter_scale": 0.05},
    },
    ("genetic", "nsga2", "union"): {
        "crossover": {"operator": "sbx", "eta": 15, "prob": 0.9},
        "mutation": {"operator": "pm", "eta": 20},
        "initial_population": {"jitter_scale": 0.05},
    },
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_algorithm_config.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add optimizers/algorithm_config.py tests/optimizers/test_algorithm_config.py
git commit -m "$(cat <<'EOF'
feat(optimizers): default initial_population.jitter_scale=0.05 for nsga2

Repo-wide default applied to both raw and union NSGA-II modes.
Overridable via algorithm.parameters.initial_population.jitter_scale.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

### Task B3: Wire `InjectedLayoutSampling` into raw driver

**Files:**
- Modify: `optimizers/drivers/raw_driver.py:50-61`
- Test: extend `tests/optimizers/test_raw_driver_matrix.py` or add a focused new test

- [ ] **Step 1: Write the failing integration test**

Create `tests/optimizers/test_initial_population_integration.py`:

```python
"""Check that the raw driver attaches InjectedLayoutSampling before minimize()."""

from __future__ import annotations

import numpy as np

from optimizers.drivers.raw_driver import run_raw_optimization
from optimizers.initial_population import InjectedLayoutSampling
from optimizers.io import generate_benchmark_case, load_optimization_spec, resolve_evaluation_spec_path
from evaluation.io import load_spec


RAW_SPEC_PATH = "scenarios/optimization/s1_typical_raw.yaml"


def test_raw_driver_attaches_injected_layout_sampling(monkeypatch):
    optimization_spec = load_optimization_spec(RAW_SPEC_PATH)
    base_case = generate_benchmark_case(RAW_SPEC_PATH, optimization_spec)
    evaluation_spec = load_spec(resolve_evaluation_spec_path(RAW_SPEC_PATH, optimization_spec))

    captured: dict[str, object] = {}
    from pymoo import optimize as pymoo_optimize

    original_minimize = pymoo_optimize.minimize

    def spy(problem, algorithm, *args, **kwargs):
        captured["sampling"] = getattr(algorithm, "sampling", None)
        captured["n_var"] = problem.n_var
        # Stop the run cheaply — raise after capture. The driver handles exceptions via problem.close().
        raise RuntimeError("sampled")

    monkeypatch.setattr("optimizers.drivers.raw_driver.minimize", spy)

    import pytest

    with pytest.raises(RuntimeError):
        run_raw_optimization(base_case, optimization_spec, evaluation_spec, spec_path=RAW_SPEC_PATH, evaluation_workers=1)

    assert isinstance(captured["sampling"], InjectedLayoutSampling)
    assert captured["sampling"].anchor_vector.shape == (captured["n_var"],)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_initial_population_integration.py::test_raw_driver_attaches_injected_layout_sampling -v`
Expected: FAIL — `assert None is InjectedLayoutSampling` (no sampling attached yet).

- [ ] **Step 3: Attach the sampling in the raw driver**

In [optimizers/drivers/raw_driver.py:8-19](../../../optimizers/drivers/raw_driver.py#L8-L19), add the imports:

```python
from optimizers.codec import extract_decision_vector
from optimizers.initial_population import InjectedLayoutSampling
```

In [optimizers/drivers/raw_driver.py:43-62](../../../optimizers/drivers/raw_driver.py#L43-L62), change the block:

```python
    loaded_case, problem, baseline_record = _initialize_single_case_problem(
        base_case,
        spec_payload,
        evaluation_payload,
        evaluation_workers=evaluation_workers,
    )

    algorithm = build_raw_algorithm(problem, algorithm_config)
    generation_callback = GenerationSummaryCallback(objective_definitions=evaluation_payload["objectives"])
    try:
        minimize(
            problem,
            algorithm,
            termination=("n_gen", int(algorithm_config["num_generations"])),
            seed=int(algorithm_config["seed"]),
            verbose=False,
            callback=generation_callback,
            copy_algorithm=False,
        )
```

to:

```python
    loaded_case, problem, baseline_record = _initialize_single_case_problem(
        base_case,
        spec_payload,
        evaluation_payload,
        evaluation_workers=evaluation_workers,
    )

    algorithm = build_raw_algorithm(problem, algorithm_config)
    algorithm.sampling = _build_initial_sampling(
        loaded_case=loaded_case,
        spec_payload=spec_payload,
        algorithm_config=algorithm_config,
    )
    generation_callback = GenerationSummaryCallback(objective_definitions=evaluation_payload["objectives"])
    try:
        minimize(
            problem,
            algorithm,
            termination=("n_gen", int(algorithm_config["num_generations"])),
            seed=int(algorithm_config["seed"]),
            verbose=False,
            callback=generation_callback,
            copy_algorithm=False,
        )
```

At the end of the file (after `_counts_toward_optimizer_progress`), add:

```python
def _build_initial_sampling(
    *,
    loaded_case: Any,
    spec_payload: dict[str, Any],
    algorithm_config: dict[str, Any],
) -> InjectedLayoutSampling:
    anchor = extract_decision_vector(loaded_case, spec_payload)
    jitter_scale = float(
        algorithm_config.get("parameters", {})
        .get("initial_population", {})
        .get("jitter_scale", 0.05)
    )
    return InjectedLayoutSampling(
        anchor_vector=anchor,
        jitter_scale=jitter_scale,
        algorithm_seed=int(algorithm_config["seed"]),
        scenario_seed=int(spec_payload["benchmark_source"]["seed"]),
    )
```

- [ ] **Step 4: Run the integration test to verify it passes**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_initial_population_integration.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add optimizers/drivers/raw_driver.py tests/optimizers/test_initial_population_integration.py
git commit -m "$(cat <<'EOF'
feat(optimizers): raw driver attaches InjectedLayoutSampling

Seed anchor_vector from the scenario's case.yaml via
extract_decision_vector; jitter_scale resolves from
algorithm.parameters.initial_population (default 0.05).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

### Task B4: Wire `InjectedLayoutSampling` into union driver

**Files:**
- Modify: `optimizers/drivers/union_driver.py:71-89`
- Test: extend `tests/optimizers/test_initial_population_integration.py`

- [ ] **Step 1: Add the failing integration test for union**

Append to `tests/optimizers/test_initial_population_integration.py`:

```python
UNION_SPEC_PATH = "scenarios/optimization/s1_typical_union.yaml"


def test_union_driver_attaches_injected_layout_sampling(monkeypatch):
    from optimizers.drivers.union_driver import run_union_optimization

    optimization_spec = load_optimization_spec(UNION_SPEC_PATH)
    base_case = generate_benchmark_case(UNION_SPEC_PATH, optimization_spec)
    evaluation_spec = load_spec(resolve_evaluation_spec_path(UNION_SPEC_PATH, optimization_spec))

    captured: dict[str, object] = {}

    def spy(problem, algorithm, *args, **kwargs):
        captured["sampling"] = getattr(algorithm, "sampling", None)
        captured["n_var"] = problem.n_var
        raise RuntimeError("sampled")

    monkeypatch.setattr("optimizers.drivers.union_driver.minimize", spy)

    import pytest

    with pytest.raises(RuntimeError):
        run_union_optimization(
            base_case,
            optimization_spec,
            evaluation_spec,
            spec_path=UNION_SPEC_PATH,
            evaluation_workers=1,
        )

    assert isinstance(captured["sampling"], InjectedLayoutSampling)
    assert captured["sampling"].anchor_vector.shape == (captured["n_var"],)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_initial_population_integration.py::test_union_driver_attaches_injected_layout_sampling -v`
Expected: FAIL.

- [ ] **Step 3: Attach the sampling in the union driver**

In [optimizers/drivers/union_driver.py:1-32](../../../optimizers/drivers/union_driver.py#L1-L32), add:

```python
from optimizers.codec import extract_decision_vector
from optimizers.initial_population import InjectedLayoutSampling
```

In [optimizers/drivers/union_driver.py:63-89](../../../optimizers/drivers/union_driver.py#L63-L89), change:

```python
    loaded_case, problem, baseline_record = _initialize_single_case_problem(
        base_case,
        spec_payload,
        evaluation_payload,
        evaluation_workers=evaluation_workers,
    )

    family = str(algorithm_config["family"])
    if family == "genetic":
        adapter = build_genetic_union_algorithm(problem, spec_payload, algorithm_config)
    elif family == "decomposition":
        adapter = build_decomposition_union_algorithm(problem, spec_payload, algorithm_config)
    elif family == "swarm":
        adapter = build_swarm_union_algorithm(problem, spec_payload, algorithm_config)
    else:
        raise ValueError(f"Unsupported union-driver family {family!r}.")
    generation_callback = GenerationSummaryCallback(objective_definitions=evaluation_payload["objectives"])
    try:
        minimize(
            problem,
            adapter.algorithm,
            termination=("n_gen", int(algorithm_config["num_generations"])),
            seed=int(algorithm_config["seed"]),
            verbose=False,
            callback=generation_callback,
            copy_algorithm=False,
        )
```

to:

```python
    loaded_case, problem, baseline_record = _initialize_single_case_problem(
        base_case,
        spec_payload,
        evaluation_payload,
        evaluation_workers=evaluation_workers,
    )

    family = str(algorithm_config["family"])
    if family == "genetic":
        adapter = build_genetic_union_algorithm(problem, spec_payload, algorithm_config)
    elif family == "decomposition":
        adapter = build_decomposition_union_algorithm(problem, spec_payload, algorithm_config)
    elif family == "swarm":
        adapter = build_swarm_union_algorithm(problem, spec_payload, algorithm_config)
    else:
        raise ValueError(f"Unsupported union-driver family {family!r}.")
    adapter.algorithm.sampling = InjectedLayoutSampling(
        anchor_vector=extract_decision_vector(loaded_case, spec_payload),
        jitter_scale=float(
            algorithm_config.get("parameters", {})
            .get("initial_population", {})
            .get("jitter_scale", 0.05)
        ),
        algorithm_seed=int(algorithm_config["seed"]),
        scenario_seed=int(spec_payload["benchmark_source"]["seed"]),
    )
    generation_callback = GenerationSummaryCallback(objective_definitions=evaluation_payload["objectives"])
    try:
        minimize(
            problem,
            adapter.algorithm,
            termination=("n_gen", int(algorithm_config["num_generations"])),
            seed=int(algorithm_config["seed"]),
            verbose=False,
            callback=generation_callback,
            copy_algorithm=False,
        )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_initial_population_integration.py -v`
Expected: PASS (both raw and union).

- [ ] **Step 5: Commit**

```bash
git add optimizers/drivers/union_driver.py tests/optimizers/test_initial_population_integration.py
git commit -m "$(cat <<'EOF'
feat(optimizers): union driver attaches InjectedLayoutSampling

Applied to the adapter.algorithm, so both nsga2_union and
nsga2_llm (which reuses the union driver) inherit the same
initial-population construction.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

### Task B5: Update paper-facing specs to pop=20, gen=10

**Files:**
- Modify: `scenarios/optimization/s1_typical_raw.yaml:141-142`
- Modify: `scenarios/optimization/s1_typical_union.yaml:141-142`
- Modify: `scenarios/optimization/s1_typical_llm.yaml:141-142`

- [ ] **Step 1: Update each spec**

In each of the three spec files, change:

```yaml
  population_size: 32
  num_generations: 16
```

to:

```yaml
  population_size: 20
  num_generations: 10
```

Leave `seed: 7` unchanged.

- [ ] **Step 2: Validate all three specs**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main validate-scenario-template --template scenarios/templates/s1_typical.yaml
```

Expected: passes (the template is unchanged).

- [ ] **Step 3: Run a smoke optimization against the raw spec**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli optimize-benchmark \
  --optimization-spec scenarios/optimization/s1_typical_raw.yaml \
  --evaluation-workers 2 \
  --output-root ./scenario_runs/s1_typical/phaseB-smoke
```

Expected: completes in a few minutes; `./scenario_runs/s1_typical/phaseB-smoke/manifest.json` exists. Delete the smoke directory after verifying:

```bash
rm -rf ./scenario_runs/s1_typical/phaseB-smoke
```

- [ ] **Step 4: Commit**

```bash
git add scenarios/optimization/s1_typical_raw.yaml scenarios/optimization/s1_typical_union.yaml scenarios/optimization/s1_typical_llm.yaml
git commit -m "$(cat <<'EOF'
chore(scenarios): s1_typical budget to pop=20 × gen=10

Permanent paper-facing default. Inter-mode comparisons remain fair
because all three modes adopt the same budget.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

### Task B6: Full test sweep and PR-B open

- [ ] **Step 1: Run the full suite**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v`
Expected: PASS. Any failures here indicate sampling was not wired through correctly or an existing determinism test locked pop=32; diagnose before opening the PR.

- [ ] **Step 2: Open PR-B**

Title: `feat(optimizers): inject scenario layout into NSGA-II initial population`, summary referencing §6 of the spec.

---

## Phase 3 — PR-C: Comparison artifacts

This phase depends on PR-A (directory layout) and PR-B (jitter default). It builds the paper-facing comparison tree.

### Task C1: Scaffold the `optimizers.comparison` package

**Files:**
- Create: `optimizers/comparison/__init__.py`
- Create: `optimizers/comparison/validation_summary.py`
- Create: `tests/optimizers/test_comparison_validation.py`

- [ ] **Step 1: Write the failing test**

Create `tests/optimizers/test_comparison_validation.py`:

```python
"""Unit tests for the validation-comparison builder."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from optimizers.comparison.validation_summary import build_validation_summary


def _write_optimization_result(
    path: Path,
    *,
    mode_id: str,
    benchmark_seed: int,
    algorithm_seed: int,
    baseline_T_max: float,
    baseline_grad: float,
    pareto_points: list[tuple[float, float]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_meta": {
            "run_id": f"{mode_id}-b{benchmark_seed}-a{algorithm_seed}-run",
            "benchmark_seed": benchmark_seed,
            "algorithm_seed": algorithm_seed,
        },
        "baseline_candidates": [
            {
                "feasible": True,
                "objective_values": {
                    "minimize_summary.temperature_max": baseline_T_max,
                    "minimize_summary.temperature_gradient_rms": baseline_grad,
                },
            }
        ],
        "pareto_front": [
            {
                "objective_values": {
                    "minimize_summary.temperature_max": t_max,
                    "minimize_summary.temperature_gradient_rms": grad,
                },
            }
            for t_max, grad in pareto_points
        ],
        "aggregate_metrics": {"pareto_size": len(pareto_points)},
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _build_mini_matrix(run_root: Path) -> None:
    for mode, base_t in (("raw", 310.0), ("union", 305.0), ("llm", 300.0)):
        for bseed in (11, 42):
            for aseed in (7, 13):
                opt_root = run_root / mode / "seeds" / f"seed-{bseed}" / f"opt-{aseed}"
                # LLM fronts are smaller numbers → better on both axes
                pareto = [
                    (base_t + aseed * 0.1, 5.0 - (10.0 if mode == "llm" else 0.0) * 0.01),
                    (base_t + 1.0 + aseed * 0.1, 4.5 - (10.0 if mode == "llm" else 0.0) * 0.01),
                ]
                _write_optimization_result(
                    opt_root / "optimization_result.json",
                    mode_id=mode,
                    benchmark_seed=bseed,
                    algorithm_seed=aseed,
                    baseline_T_max=315.0,
                    baseline_grad=6.0,
                    pareto_points=pareto,
                )


def test_build_validation_summary_emits_expected_files(tmp_path):
    run_root = tmp_path / "0416_1200__raw_union_llm"
    _build_mini_matrix(run_root)
    (run_root / "comparison").mkdir(parents=True, exist_ok=True)

    objective_definitions = [
        {"objective_id": "minimize_summary.temperature_max", "sense": "minimize"},
        {"objective_id": "minimize_summary.temperature_gradient_rms", "sense": "minimize"},
    ]
    build_validation_summary(
        run_root=run_root,
        modes=["raw", "union", "llm"],
        benchmark_seeds=[11, 42],
        algorithm_seeds=[7, 13],
        objective_definitions=objective_definitions,
    )

    summary_path = run_root / "comparison" / "summary.json"
    aggregate_path = run_root / "comparison" / "per_mode_aggregate.json"

    assert summary_path.is_file()
    assert aggregate_path.is_file()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert len(summary["rows"]) == 12  # 3 modes × 2 bseeds × 2 aseeds
    for row in summary["rows"]:
        assert row["HV"] >= 0.0
        assert row["n_pareto_points"] >= 1
        assert {"mode", "scenario_seed", "opt_seed"} <= row.keys()
    assert "hv_reference_point" in summary
    assert len(summary["hv_reference_point"]) == 2

    aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
    llm = next(entry for entry in aggregate["modes"] if entry["mode"] == "llm")
    raw = next(entry for entry in aggregate["modes"] if entry["mode"] == "raw")
    # llm is seeded to dominate; its mean HV must exceed raw's
    assert llm["hv_mean"] > raw["hv_mean"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_comparison_validation.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'optimizers.comparison'`.

- [ ] **Step 3: Scaffold the package**

Create `optimizers/comparison/__init__.py`:

```python
"""Validation-comparison builders for s1_typical multi-scenario runs."""

from optimizers.comparison.validation_summary import build_validation_summary

__all__ = ["build_validation_summary"]
```

Create `optimizers/comparison/validation_summary.py`:

```python
"""Emit comparison/summary.json and comparison/per_mode_aggregate.json."""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from pymoo.indicators.hv import HV

try:
    from scipy.stats import wilcoxon
except ImportError:  # scipy is a hard dependency in msfenicsx; this is just a safety net
    wilcoxon = None


def build_validation_summary(
    *,
    run_root: Path,
    modes: Sequence[str],
    benchmark_seeds: Sequence[int],
    algorithm_seeds: Sequence[int],
    objective_definitions: list[dict[str, Any]],
) -> dict[str, Any]:
    run_root = Path(run_root)
    comparison_root = run_root / "comparison"
    comparison_root.mkdir(parents=True, exist_ok=True)

    objective_ids = [str(item["objective_id"]) for item in objective_definitions]
    if len(objective_ids) != 2:
        raise ValueError(
            f"build_validation_summary requires exactly 2 objectives, got {len(objective_ids)}."
        )

    hv_reference_point = _compute_hv_reference_point(
        run_root=run_root,
        modes=modes,
        benchmark_seeds=benchmark_seeds,
        algorithm_seeds=algorithm_seeds,
        objective_ids=objective_ids,
    )
    hv_indicator = HV(ref_point=np.asarray(hv_reference_point, dtype=np.float64))

    rows: list[dict[str, Any]] = []
    for mode in modes:
        for bseed in benchmark_seeds:
            for aseed in algorithm_seeds:
                opt_root = run_root / mode / "seeds" / f"seed-{bseed}" / f"opt-{aseed}"
                result = _load_result(opt_root / "optimization_result.json")
                pareto_points = [
                    [float(entry["objective_values"][objective_ids[0]]),
                     float(entry["objective_values"][objective_ids[1]])]
                    for entry in result.get("pareto_front", [])
                ]
                if pareto_points:
                    hv_value = float(hv_indicator(np.asarray(pareto_points, dtype=np.float64)))
                    best_obj0 = min(point[0] for point in pareto_points)
                    best_obj1 = min(point[1] for point in pareto_points)
                else:
                    hv_value = 0.0
                    best_obj0 = float("nan")
                    best_obj1 = float("nan")
                rows.append(
                    {
                        "mode": mode,
                        "scenario_seed": int(bseed),
                        "opt_seed": int(aseed),
                        "HV": hv_value,
                        "best_T_max": best_obj0,
                        "best_grad_rms": best_obj1,
                        "n_pareto_points": len(pareto_points),
                        "run_id": result["run_meta"].get("run_id"),
                    }
                )

    summary_payload = {
        "hv_reference_point": list(hv_reference_point),
        "objectives": [
            {"id": objective_ids[0], "role": "T_max"},
            {"id": objective_ids[1], "role": "grad_rms"},
        ],
        "rows": rows,
    }
    (comparison_root / "summary.json").write_text(json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8")

    aggregate_payload = {
        "modes": _per_mode_aggregate(rows, modes=modes),
        "pairwise": _pairwise_wilcoxon(rows, modes=modes),
    }
    (comparison_root / "per_mode_aggregate.json").write_text(
        json.dumps(aggregate_payload, indent=2) + "\n", encoding="utf-8"
    )

    return {
        "summary": str((comparison_root / "summary.json").relative_to(run_root).as_posix()),
        "per_mode_aggregate": str(
            (comparison_root / "per_mode_aggregate.json").relative_to(run_root).as_posix()
        ),
    }


def _compute_hv_reference_point(
    *,
    run_root: Path,
    modes: Sequence[str],
    benchmark_seeds: Sequence[int],
    algorithm_seeds: Sequence[int],
    objective_ids: list[str],
) -> tuple[float, float]:
    max_obj0 = 0.0
    max_obj1 = 0.0
    seen = False
    for mode in modes:
        for bseed in benchmark_seeds:
            # Each scenario's baseline is the same across algorithm seeds, so one read is enough
            aseed = algorithm_seeds[0]
            opt_root = run_root / mode / "seeds" / f"seed-{bseed}" / f"opt-{aseed}"
            result_path = opt_root / "optimization_result.json"
            if not result_path.exists():
                continue
            result = _load_result(result_path)
            for baseline in result.get("baseline_candidates", []):
                values = baseline.get("objective_values", {})
                obj0 = float(values.get(objective_ids[0], 0.0))
                obj1 = float(values.get(objective_ids[1], 0.0))
                max_obj0 = obj0 if not seen else max(max_obj0, obj0)
                max_obj1 = obj1 if not seen else max(max_obj1, obj1)
                seen = True
    if not seen:
        raise RuntimeError("No baseline_candidates found for HV reference point computation.")
    return (max_obj0 * 1.10, max_obj1 * 1.10)


def _per_mode_aggregate(rows: list[dict[str, Any]], *, modes: Sequence[str]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for mode in modes:
        mode_rows = [row for row in rows if row["mode"] == mode]
        hv_values = [row["HV"] for row in mode_rows]
        tmax_values = [row["best_T_max"] for row in mode_rows if not _isnan(row["best_T_max"])]
        grad_values = [row["best_grad_rms"] for row in mode_rows if not _isnan(row["best_grad_rms"])]
        output.append(
            {
                "mode": mode,
                "n_samples": len(mode_rows),
                "hv_mean": _mean(hv_values),
                "hv_median": _median(hv_values),
                "hv_std": _std(hv_values),
                "best_T_max_mean": _mean(tmax_values),
                "best_T_max_std": _std(tmax_values),
                "best_grad_rms_mean": _mean(grad_values),
                "best_grad_rms_std": _std(grad_values),
            }
        )
    return output


def _pairwise_wilcoxon(rows: list[dict[str, Any]], *, modes: Sequence[str]) -> list[dict[str, Any]]:
    if wilcoxon is None:
        return []
    if "llm" not in modes:
        return []
    llm_rows = sorted(
        (row for row in rows if row["mode"] == "llm"),
        key=lambda row: (row["scenario_seed"], row["opt_seed"]),
    )
    pairwise: list[dict[str, Any]] = []
    for opponent in modes:
        if opponent == "llm":
            continue
        opponent_rows = sorted(
            (row for row in rows if row["mode"] == opponent),
            key=lambda row: (row["scenario_seed"], row["opt_seed"]),
        )
        differences = [
            llm["HV"] - opponent_row["HV"]
            for llm, opponent_row in zip(llm_rows, opponent_rows, strict=True)
        ]
        try:
            stat = wilcoxon(differences, zero_method="wilcox", alternative="greater")
            p_value = float(stat.pvalue)
        except ValueError:
            p_value = float("nan")
        pairwise.append(
            {
                "llm_vs": opponent,
                "n_pairs": len(differences),
                "mean_hv_delta": _mean(differences),
                "wilcoxon_p_greater": p_value,
            }
        )
    return pairwise


def _load_result(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _isnan(value: Any) -> bool:
    try:
        return bool(np.isnan(float(value)))
    except (TypeError, ValueError):
        return True


def _mean(values: list[float]) -> float | None:
    return float(statistics.fmean(values)) if values else None


def _median(values: list[float]) -> float | None:
    return float(statistics.median(values)) if values else None


def _std(values: list[float]) -> float | None:
    return float(statistics.pstdev(values)) if len(values) >= 1 else None
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_comparison_validation.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add optimizers/comparison/__init__.py optimizers/comparison/validation_summary.py tests/optimizers/test_comparison_validation.py
git commit -m "$(cat <<'EOF'
feat(optimizers): add comparison/summary.json and per_mode_aggregate.json

New optimizers.comparison package builds the validation HV table,
per-mode aggregates (mean, median, std), and pairwise
Wilcoxon-signed-rank p-values for llm vs raw/union. HV reference
point derives from the union of baseline candidates with a 10%
margin.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

### Task C2: Build markdown tables (per_scenario_table.md, win_rate_table.md)

**Files:**
- Create: `optimizers/comparison/tables.py`
- Modify: `optimizers/comparison/__init__.py`
- Modify: `tests/optimizers/test_comparison_validation.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/optimizers/test_comparison_validation.py`:

```python
def test_build_tables_writes_markdown_files(tmp_path):
    run_root = tmp_path / "0416_1200__raw_union_llm"
    _build_mini_matrix(run_root)
    (run_root / "comparison").mkdir(parents=True, exist_ok=True)

    from optimizers.comparison import build_validation_summary
    from optimizers.comparison.tables import build_validation_tables

    objective_definitions = [
        {"objective_id": "minimize_summary.temperature_max", "sense": "minimize"},
        {"objective_id": "minimize_summary.temperature_gradient_rms", "sense": "minimize"},
    ]
    build_validation_summary(
        run_root=run_root,
        modes=["raw", "union", "llm"],
        benchmark_seeds=[11, 42],
        algorithm_seeds=[7, 13],
        objective_definitions=objective_definitions,
    )
    build_validation_tables(
        run_root=run_root,
        modes=["raw", "union", "llm"],
        benchmark_seeds=[11, 42],
        algorithm_seeds=[7, 13],
    )

    per_scenario = (run_root / "comparison" / "per_scenario_table.md").read_text(encoding="utf-8")
    win_rate = (run_root / "comparison" / "win_rate_table.md").read_text(encoding="utf-8")
    assert "| scenario | raw | union | llm |" in per_scenario
    assert "## Win rate against raw" in win_rate
    assert "## Win rate against union" in win_rate
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_comparison_validation.py::test_build_tables_writes_markdown_files -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'optimizers.comparison.tables'`.

- [ ] **Step 3: Implement the tables module**

Create `optimizers/comparison/tables.py`:

```python
"""Markdown tables for comparison/per_scenario_table.md and comparison/win_rate_table.md."""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Sequence


def build_validation_tables(
    *,
    run_root: Path,
    modes: Sequence[str],
    benchmark_seeds: Sequence[int],
    algorithm_seeds: Sequence[int],
) -> dict[str, str]:
    run_root = Path(run_root)
    comparison_root = run_root / "comparison"
    summary_payload = json.loads((comparison_root / "summary.json").read_text(encoding="utf-8"))
    rows = summary_payload["rows"]

    per_scenario_path = comparison_root / "per_scenario_table.md"
    per_scenario_path.write_text(
        _render_per_scenario_table(rows, modes=modes, benchmark_seeds=benchmark_seeds),
        encoding="utf-8",
    )

    win_rate_path = comparison_root / "win_rate_table.md"
    win_rate_path.write_text(
        _render_win_rate_table(rows, modes=modes, benchmark_seeds=benchmark_seeds, algorithm_seeds=algorithm_seeds),
        encoding="utf-8",
    )

    return {
        "per_scenario_table": str(per_scenario_path.relative_to(run_root).as_posix()),
        "win_rate_table": str(win_rate_path.relative_to(run_root).as_posix()),
    }


def _render_per_scenario_table(rows, *, modes: Sequence[str], benchmark_seeds: Sequence[int]) -> str:
    header = "| scenario | " + " | ".join(modes) + " |\n"
    divider = "| --- | " + " | ".join(["---"] * len(modes)) + " |\n"
    lines = [header, divider]
    for bseed in benchmark_seeds:
        cells = [f"seed-{bseed}"]
        for mode in modes:
            hv_values = [row["HV"] for row in rows if row["mode"] == mode and row["scenario_seed"] == bseed]
            if not hv_values:
                cells.append("n/a")
                continue
            mean_hv = float(statistics.fmean(hv_values))
            std_hv = float(statistics.pstdev(hv_values)) if len(hv_values) > 1 else 0.0
            cells.append(f"{mean_hv:.3f} ± {std_hv:.3f}")
        lines.append("| " + " | ".join(cells) + " |\n")
    return "# Per-scenario HV table (mean ± std over optimizer seeds)\n\n" + "".join(lines)


def _render_win_rate_table(
    rows,
    *,
    modes: Sequence[str],
    benchmark_seeds: Sequence[int],
    algorithm_seeds: Sequence[int],
) -> str:
    if "llm" not in modes:
        return "# Win rate table\n\n(llm mode not present.)\n"
    by_cell: dict[tuple[int, int, str], dict[str, float]] = {
        (row["scenario_seed"], row["opt_seed"], row["mode"]): row for row in rows
    }
    output = ["# Win rate: llm vs opponent\n"]
    for opponent in modes:
        if opponent == "llm":
            continue
        output.append(f"\n## Win rate against {opponent}\n\n")
        output.append("| metric | wins / cells |\n| --- | --- |\n")
        total_cells = len(benchmark_seeds) * len(algorithm_seeds)
        for metric_key, label, sign in (
            ("HV", "HV (higher is better)", +1),
            ("best_T_max", "best T_max (lower is better)", -1),
            ("best_grad_rms", "best grad_rms (lower is better)", -1),
        ):
            wins = 0
            for bseed in benchmark_seeds:
                for aseed in algorithm_seeds:
                    llm_value = by_cell[(bseed, aseed, "llm")][metric_key]
                    opponent_value = by_cell[(bseed, aseed, opponent)][metric_key]
                    if sign * (llm_value - opponent_value) > 0:
                        wins += 1
            output.append(f"| {label} | {wins} / {total_cells} |\n")
    return "".join(output)
```

Extend `optimizers/comparison/__init__.py`:

```python
"""Validation-comparison builders for s1_typical multi-scenario runs."""

from optimizers.comparison.tables import build_validation_tables
from optimizers.comparison.validation_summary import build_validation_summary

__all__ = ["build_validation_summary", "build_validation_tables"]
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_comparison_validation.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add optimizers/comparison/__init__.py optimizers/comparison/tables.py tests/optimizers/test_comparison_validation.py
git commit -m "$(cat <<'EOF'
feat(optimizers): add per_scenario and win_rate markdown tables

per_scenario_table.md renders HV mean ± std per (scenario, mode) cell.
win_rate_table.md counts llm wins vs each opponent on HV, best T_max,
and best grad_rms across all (scenario_seed, opt_seed) cells.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

### Task C3: Build SVG figures (hv_bar, pareto_overlay)

**Files:**
- Create: `optimizers/comparison/figures.py`
- Modify: `optimizers/comparison/__init__.py`
- Modify: `tests/optimizers/test_comparison_validation.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/optimizers/test_comparison_validation.py`:

```python
def test_build_figures_writes_svg_files(tmp_path):
    run_root = tmp_path / "0416_1200__raw_union_llm"
    _build_mini_matrix(run_root)
    (run_root / "comparison").mkdir(parents=True, exist_ok=True)

    from optimizers.comparison import build_validation_summary
    from optimizers.comparison.figures import build_validation_figures

    objective_definitions = [
        {"objective_id": "minimize_summary.temperature_max", "sense": "minimize"},
        {"objective_id": "minimize_summary.temperature_gradient_rms", "sense": "minimize"},
    ]
    build_validation_summary(
        run_root=run_root,
        modes=["raw", "union", "llm"],
        benchmark_seeds=[11, 42],
        algorithm_seeds=[7, 13],
        objective_definitions=objective_definitions,
    )
    build_validation_figures(
        run_root=run_root,
        modes=["raw", "union", "llm"],
        benchmark_seeds=[11, 42],
        algorithm_seeds=[7, 13],
    )

    hv_bar = (run_root / "comparison" / "figures" / "hv_bar.svg")
    pareto_overlay = (run_root / "comparison" / "figures" / "pareto_overlay.svg")
    assert hv_bar.is_file() and hv_bar.stat().st_size > 0
    assert pareto_overlay.is_file() and pareto_overlay.stat().st_size > 0
    assert hv_bar.read_text(encoding="utf-8").startswith("<?xml") or hv_bar.read_text(encoding="utf-8").startswith("<svg")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_comparison_validation.py::test_build_figures_writes_svg_files -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'optimizers.comparison.figures'`.

- [ ] **Step 3: Implement the figures module**

Create `optimizers/comparison/figures.py`:

```python
"""SVG figure rendering for comparison/figures/{hv_bar,pareto_overlay}.svg."""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


MODE_COLORS = {"raw": "#888888", "union": "#1f77b4", "llm": "#2ca02c"}


def build_validation_figures(
    *,
    run_root: Path,
    modes: Sequence[str],
    benchmark_seeds: Sequence[int],
    algorithm_seeds: Sequence[int],
) -> dict[str, str]:
    run_root = Path(run_root)
    figures_root = run_root / "comparison" / "figures"
    figures_root.mkdir(parents=True, exist_ok=True)
    summary_payload = json.loads((run_root / "comparison" / "summary.json").read_text(encoding="utf-8"))
    rows = summary_payload["rows"]

    hv_bar_path = figures_root / "hv_bar.svg"
    _render_hv_bar(rows, modes=modes, benchmark_seeds=benchmark_seeds, output_path=hv_bar_path)

    overlay_path = figures_root / "pareto_overlay.svg"
    _render_pareto_overlay(
        run_root=run_root,
        modes=modes,
        benchmark_seeds=benchmark_seeds,
        algorithm_seeds=algorithm_seeds,
        objective_ids=[entry["id"] for entry in summary_payload["objectives"]],
        output_path=overlay_path,
    )
    return {
        "hv_bar": str(hv_bar_path.relative_to(run_root).as_posix()),
        "pareto_overlay": str(overlay_path.relative_to(run_root).as_posix()),
    }


def _render_hv_bar(rows, *, modes: Sequence[str], benchmark_seeds: Sequence[int], output_path: Path) -> None:
    fig, axes = plt.subplots(1, len(benchmark_seeds), figsize=(4 * len(benchmark_seeds), 3.2), sharey=True)
    if len(benchmark_seeds) == 1:
        axes = [axes]
    for ax, bseed in zip(axes, benchmark_seeds, strict=True):
        means = []
        stds = []
        for mode in modes:
            hv_values = [row["HV"] for row in rows if row["mode"] == mode and row["scenario_seed"] == bseed]
            means.append(float(statistics.fmean(hv_values)) if hv_values else 0.0)
            stds.append(float(statistics.pstdev(hv_values)) if len(hv_values) > 1 else 0.0)
        colors = [MODE_COLORS.get(mode, "#cccccc") for mode in modes]
        ax.bar(list(modes), means, yerr=stds, color=colors, capsize=4)
        ax.set_title(f"scenario seed-{bseed}")
        ax.set_ylabel("HV")
    fig.tight_layout()
    fig.savefig(output_path, format="svg")
    plt.close(fig)


def _render_pareto_overlay(
    *,
    run_root: Path,
    modes: Sequence[str],
    benchmark_seeds: Sequence[int],
    algorithm_seeds: Sequence[int],
    objective_ids: list[str],
    output_path: Path,
) -> None:
    fig, axes = plt.subplots(1, len(benchmark_seeds), figsize=(4 * len(benchmark_seeds), 3.2), sharey=True)
    if len(benchmark_seeds) == 1:
        axes = [axes]
    for ax, bseed in zip(axes, benchmark_seeds, strict=True):
        for mode in modes:
            color = MODE_COLORS.get(mode, "#cccccc")
            for aseed in algorithm_seeds:
                opt_root = run_root / mode / "seeds" / f"seed-{bseed}" / f"opt-{aseed}"
                result_path = opt_root / "optimization_result.json"
                if not result_path.exists():
                    continue
                payload = json.loads(result_path.read_text(encoding="utf-8"))
                points = [
                    (
                        float(entry["objective_values"][objective_ids[0]]),
                        float(entry["objective_values"][objective_ids[1]]),
                    )
                    for entry in payload.get("pareto_front", [])
                ]
                if points:
                    xs, ys = zip(*points, strict=True)
                    ax.scatter(xs, ys, s=16, color=color, alpha=0.7, label=mode if aseed == algorithm_seeds[0] else None)
        ax.set_title(f"scenario seed-{bseed}")
        ax.set_xlabel(objective_ids[0])
        ax.set_ylabel(objective_ids[1])
        ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, format="svg")
    plt.close(fig)
```

Extend `optimizers/comparison/__init__.py`:

```python
from optimizers.comparison.figures import build_validation_figures
from optimizers.comparison.tables import build_validation_tables
from optimizers.comparison.validation_summary import build_validation_summary

__all__ = [
    "build_validation_figures",
    "build_validation_summary",
    "build_validation_tables",
]
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_comparison_validation.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add optimizers/comparison/__init__.py optimizers/comparison/figures.py tests/optimizers/test_comparison_validation.py
git commit -m "$(cat <<'EOF'
feat(optimizers): add HV bar and pareto overlay SVG figures

Three-subplot figures (one per scenario) showing HV mean ± std per
mode and the pooled Pareto points per mode. Matplotlib renders to
SVG so artifacts embed cleanly into the HTML index.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

### Task C4: Build HTML index page

**Files:**
- Create: `optimizers/comparison/pages.py`
- Modify: `optimizers/comparison/__init__.py`
- Modify: `tests/optimizers/test_comparison_validation.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/optimizers/test_comparison_validation.py`:

```python
def test_build_pages_writes_html_index(tmp_path):
    run_root = tmp_path / "0416_1200__raw_union_llm"
    _build_mini_matrix(run_root)
    (run_root / "comparison" / "figures").mkdir(parents=True, exist_ok=True)

    from optimizers.comparison import (
        build_validation_figures,
        build_validation_summary,
        build_validation_tables,
    )
    from optimizers.comparison.pages import build_validation_pages

    objective_definitions = [
        {"objective_id": "minimize_summary.temperature_max", "sense": "minimize"},
        {"objective_id": "minimize_summary.temperature_gradient_rms", "sense": "minimize"},
    ]
    build_validation_summary(
        run_root=run_root,
        modes=["raw", "union", "llm"],
        benchmark_seeds=[11, 42],
        algorithm_seeds=[7, 13],
        objective_definitions=objective_definitions,
    )
    build_validation_tables(
        run_root=run_root,
        modes=["raw", "union", "llm"],
        benchmark_seeds=[11, 42],
        algorithm_seeds=[7, 13],
    )
    build_validation_figures(
        run_root=run_root,
        modes=["raw", "union", "llm"],
        benchmark_seeds=[11, 42],
        algorithm_seeds=[7, 13],
    )
    build_validation_pages(run_root=run_root)

    index_html = (run_root / "comparison" / "pages" / "index.html").read_text(encoding="utf-8")
    assert "<h1>" in index_html
    assert "hv_bar.svg" in index_html
    assert "pareto_overlay.svg" in index_html
    assert "per-scenario" in index_html.lower()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_comparison_validation.py::test_build_pages_writes_html_index -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'optimizers.comparison.pages'`.

- [ ] **Step 3: Implement the pages module**

Create `optimizers/comparison/pages.py`:

```python
"""HTML stitching for comparison/pages/index.html."""

from __future__ import annotations

import json
from pathlib import Path


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>s1_typical validation — {run_id}</title>
<style>
body {{ font-family: sans-serif; max-width: 960px; margin: 2rem auto; padding: 0 1rem; }}
table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
th, td {{ border: 1px solid #ccc; padding: 0.4rem 0.6rem; text-align: right; }}
th {{ background: #f4f4f4; }}
figure {{ margin: 1rem 0; }}
figcaption {{ font-size: 0.9rem; color: #666; }}
pre {{ background: #f7f7f7; padding: 0.6rem; overflow-x: auto; }}
</style>
</head>
<body>
<h1>s1_typical validation — {run_id}</h1>
<p>Reference point: <code>{hv_reference_point}</code></p>
<h2>HV per scenario</h2>
<figure>
<img src="../figures/hv_bar.svg" alt="HV bar per scenario">
<figcaption>HV mean ± std across optimizer seeds per scenario.</figcaption>
</figure>
<h2>Pareto overlay</h2>
<figure>
<img src="../figures/pareto_overlay.svg" alt="Pareto overlay per scenario">
<figcaption>Pooled Pareto points per mode across optimizer seeds.</figcaption>
</figure>
<h2>Per-scenario table</h2>
<pre>{per_scenario}</pre>
<h2>Win-rate table</h2>
<pre>{win_rate}</pre>
<h2>Aggregate</h2>
<pre>{aggregate}</pre>
</body>
</html>
"""


def build_validation_pages(*, run_root: Path) -> dict[str, str]:
    run_root = Path(run_root)
    comparison_root = run_root / "comparison"
    pages_root = comparison_root / "pages"
    pages_root.mkdir(parents=True, exist_ok=True)

    summary_payload = json.loads((comparison_root / "summary.json").read_text(encoding="utf-8"))
    aggregate_payload = json.loads((comparison_root / "per_mode_aggregate.json").read_text(encoding="utf-8"))

    per_scenario = (comparison_root / "per_scenario_table.md").read_text(encoding="utf-8")
    win_rate = (comparison_root / "win_rate_table.md").read_text(encoding="utf-8")
    page_html = PAGE_TEMPLATE.format(
        run_id=run_root.name,
        hv_reference_point=summary_payload["hv_reference_point"],
        per_scenario=per_scenario,
        win_rate=win_rate,
        aggregate=json.dumps(aggregate_payload, indent=2),
    )
    index_path = pages_root / "index.html"
    index_path.write_text(page_html, encoding="utf-8")
    return {"index": str(index_path.relative_to(run_root).as_posix())}
```

Extend `optimizers/comparison/__init__.py` to export `build_validation_pages`.

- [ ] **Step 4: Run the test to verify it passes**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_comparison_validation.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add optimizers/comparison/__init__.py optimizers/comparison/pages.py tests/optimizers/test_comparison_validation.py
git commit -m "$(cat <<'EOF'
feat(optimizers): add comparison/pages/index.html stitching

Stitches HV bar figure, pareto overlay, per-scenario table,
win-rate table, and per-mode aggregate into a single HTML index.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

### Task C5: Invoke comparison builder at end of `run_benchmark_suite`

**Files:**
- Modify: `optimizers/run_suite.py:145-148`
- Modify: `tests/optimizers/test_run_suite_multi_seed.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/optimizers/test_run_suite_multi_seed.py`:

```python
def test_run_benchmark_suite_emits_validation_comparison(tmp_path):
    pytest.importorskip("pymoo")
    from datetime import datetime
    from optimizers.run_suite import run_benchmark_suite

    run_root = run_benchmark_suite(
        optimization_spec_paths=[
            Path("scenarios/optimization/s1_typical_raw.yaml"),
            Path("scenarios/optimization/s1_typical_union.yaml"),
        ],
        benchmark_seeds=[11, 42],
        algorithm_seeds=[7, 13],
        scenario_runs_root=tmp_path / "runs",
        modes=["raw", "union"],
        evaluation_workers=1,
        started_at=datetime(2026, 4, 16, 12, 0),
    )
    comparison_root = run_root / "comparison"
    assert (comparison_root / "summary.json").is_file()
    assert (comparison_root / "per_mode_aggregate.json").is_file()
    assert (comparison_root / "per_scenario_table.md").is_file()
    assert (comparison_root / "win_rate_table.md").is_file()
    assert (comparison_root / "figures" / "hv_bar.svg").is_file()
    assert (comparison_root / "pages" / "index.html").is_file()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_run_suite_multi_seed.py::test_run_benchmark_suite_emits_validation_comparison -v`
Expected: FAIL — `AssertionError` on `summary.json`.

- [ ] **Step 3: Wire the validation builder into `run_benchmark_suite`**

In [optimizers/run_suite.py:145-148](../../../optimizers/run_suite.py#L145-L148), change:

```python
    if len(selected_modes) > 1:
        build_comparison_summaries(run_root)
        render_comparison_pages(run_root)
    return run_root
```

to:

```python
    if len(selected_modes) > 1:
        build_comparison_summaries(run_root)
        render_comparison_pages(run_root)

    # Validation comparison (HV, tables, figures, HTML index) — always produced.
    primary_evaluation_path = resolve_evaluation_spec_path(primary_spec_path, primary_spec)
    primary_evaluation_spec = load_spec(primary_evaluation_path)
    primary_evaluation_payload = (
        primary_evaluation_spec.to_dict()
        if hasattr(primary_evaluation_spec, "to_dict")
        else dict(primary_evaluation_spec)
    )
    _build_validation_comparison(
        run_root=run_root,
        modes=selected_modes,
        benchmark_seeds=list(effective_seeds),
        algorithm_seeds_by_mode={
            mode: _effective_algorithm_seeds(spec_by_mode[mode][1], algorithm_seeds)
            for mode in selected_modes
        },
        objective_definitions=list(primary_evaluation_payload["objectives"]),
    )
    return run_root
```

Add the two helpers at the end of the file:

```python
def _effective_algorithm_seeds(spec: OptimizationSpec, overrides: Sequence[int] | None) -> list[int]:
    if overrides:
        return [int(value) for value in overrides]
    return [int(spec.algorithm["seed"])]


def _build_validation_comparison(
    *,
    run_root: Path,
    modes: Sequence[str],
    benchmark_seeds: Sequence[int],
    algorithm_seeds_by_mode: dict[str, list[int]],
    objective_definitions: list[dict[str, Any]],
) -> None:
    from optimizers.comparison import (
        build_validation_figures,
        build_validation_pages,
        build_validation_summary,
        build_validation_tables,
    )

    shared_algorithm_seeds = next(iter(algorithm_seeds_by_mode.values()))
    if not all(seeds == shared_algorithm_seeds for seeds in algorithm_seeds_by_mode.values()):
        raise ValueError(
            "Validation comparison requires identical algorithm_seeds across modes; "
            f"got {algorithm_seeds_by_mode!r}."
        )
    build_validation_summary(
        run_root=run_root,
        modes=modes,
        benchmark_seeds=benchmark_seeds,
        algorithm_seeds=shared_algorithm_seeds,
        objective_definitions=objective_definitions,
    )
    build_validation_tables(
        run_root=run_root,
        modes=modes,
        benchmark_seeds=benchmark_seeds,
        algorithm_seeds=shared_algorithm_seeds,
    )
    build_validation_figures(
        run_root=run_root,
        modes=modes,
        benchmark_seeds=benchmark_seeds,
        algorithm_seeds=shared_algorithm_seeds,
    )
    build_validation_pages(run_root=run_root)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/optimizers/test_run_suite_multi_seed.py::test_run_benchmark_suite_emits_validation_comparison -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add optimizers/run_suite.py tests/optimizers/test_run_suite_multi_seed.py
git commit -m "$(cat <<'EOF'
feat(optimizers): run_benchmark_suite emits comparison/ validation tree

At end of suite, build summary.json, per_mode_aggregate.json,
per_scenario_table.md, win_rate_table.md, hv_bar.svg,
pareto_overlay.svg, and pages/index.html. Pre-existing
comparison_summaries and comparison_pages renderers remain in place
and continue to emit their original artifacts alongside the new
validation ones.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

### Task C6: Full test sweep and PR-C open

- [ ] **Step 1: Run the full suite**

Run: `/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest -v`
Expected: PASS.

- [ ] **Step 2: Run a small end-to-end smoke with raw + union only**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli run-benchmark-suite \
  --optimization-spec scenarios/optimization/s1_typical_raw.yaml \
  --optimization-spec scenarios/optimization/s1_typical_union.yaml \
  --mode raw --mode union \
  --benchmark-seed 11 --benchmark-seed 42 \
  --algorithm-seeds 7 --algorithm-seeds 13 \
  --evaluation-workers 2 \
  --scenario-runs-root ./scenario_runs
```

Inspect the resulting `scenario_runs/s1_typical/<MMDD_HHMM>__raw_union/comparison/`:

- `summary.json` has 8 rows (2 modes × 2 bseeds × 2 aseeds)
- `per_scenario_table.md` lists `raw` and `union` columns for `seed-11` and `seed-42`
- `figures/hv_bar.svg` and `figures/pareto_overlay.svg` non-empty
- `pages/index.html` renders in a browser

Delete the smoke run after inspecting:

```bash
rm -rf scenario_runs/s1_typical/*__raw_union
```

- [ ] **Step 3: Open PR-C**

Title: `feat(optimizers): validation comparison artifacts (HV, win-rate, figures, HTML index)`, summary referencing §8 of the spec.

---

## Phase 4 — Full 27-run execution

After PR-A/B/C land on `main` and the provider-profile-switching work has merged so the `gpt` profile is usable:

- [ ] **Step 1: Run the full 27-run suite**

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m optimizers.cli run-benchmark-suite \
  --optimization-spec scenarios/optimization/s1_typical_raw.yaml \
  --optimization-spec scenarios/optimization/s1_typical_union.yaml \
  --optimization-spec scenarios/optimization/s1_typical_llm.yaml \
  --mode raw --mode union --mode llm \
  --benchmark-seed 11 --benchmark-seed 42 --benchmark-seed 123 \
  --algorithm-seeds 7 --algorithm-seeds 13 --algorithm-seeds 29 \
  --evaluation-workers 2 \
  --scenario-runs-root ./scenario_runs
```

Run `raw` and `union` first without the `--mode llm` flag if the provider-profile-switching path is not yet merged; then run `llm` alone once credentials are available.

- [ ] **Step 2: Inspect `<run_id>/comparison/`**

Look at `summary.json`, `per_scenario_table.md`, `win_rate_table.md`, and `pages/index.html`. Cross-check against the four Claim thresholds in §13 of the spec; record each claim's pass/fail verdict.

- [ ] **Step 3: Write the progress report entry**

Record the run path, absolute HV numbers, per-claim verdicts, and any failed claim with per-scenario breakdown in `docs/reports/2026-04-16-s1-typical-multi-scenario-validation.md` (or the equivalent chosen path). The report must explicitly call out failed claims rather than cherry-picking the successful axes.

---

## Verification

| Verification | When |
|---|---|
| `pytest -v` green | End of each phase |
| Directory layout: `seeds/seed-<N>/opt-<M>/optimization_result.json` exists for every `(bseed, aseed, mode)` | End of PR-A |
| Raw driver attaches `InjectedLayoutSampling`; sample 0 == anchor | End of PR-B |
| `comparison/{summary.json, per_mode_aggregate.json, per_scenario_table.md, win_rate_table.md, figures/hv_bar.svg, figures/pareto_overlay.svg, pages/index.html}` all present after a multi-mode suite run | End of PR-C |
| Four Claim verdicts documented post full 27-run | Phase 4 |
