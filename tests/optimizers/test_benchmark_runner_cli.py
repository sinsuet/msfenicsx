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
