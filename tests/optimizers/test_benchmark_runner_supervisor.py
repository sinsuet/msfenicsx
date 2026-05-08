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
        method_slug="raw",
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
