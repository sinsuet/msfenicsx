import json
from pathlib import Path

from optimizers.cli import main


def test_optimizer_cli_writes_result_and_pareto_artifacts(tmp_path: Path) -> None:
    output_root = tmp_path / "optimizer_run"

    exit_code = main(
        [
            "optimize-operating-cases",
            "--case",
            "hot=scenarios/manual/reference_case_hot.yaml",
            "--case",
            "cold=scenarios/manual/reference_case_cold.yaml",
            "--optimization-spec",
            "scenarios/optimization/reference_hot_cold_nsga2.yaml",
            "--output-root",
            str(output_root),
        ]
    )

    assert exit_code == 0
    assert (output_root / "optimization_result.json").exists()
    assert (output_root / "pareto_front.json").exists()
    assert (output_root / "representatives" / "min-hot-peak" / "case_hot.yaml").exists()
    assert (output_root / "representatives" / "min-hot-peak" / "case_cold.yaml").exists()
    assert (output_root / "representatives" / "min-hot-peak" / "evaluation.yaml").exists()

    result_payload = json.loads((output_root / "optimization_result.json").read_text(encoding="utf-8"))
    assert result_payload["pareto_front"]
