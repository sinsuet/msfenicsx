from pathlib import Path

import pytest

from core.cli.main import main


def test_generate_operating_case_pair_then_solve_cli_smoke(tmp_path: Path) -> None:
    generated_cases = tmp_path / "generated_cases"
    run_root = tmp_path / "scenario_runs"

    generate_code = main(
        [
            "generate-operating-case-pair",
            "--template",
            "scenarios/templates/panel_four_component_hot_cold_benchmark.yaml",
            "--seed",
            "11",
            "--output-root",
            str(generated_cases),
        ]
    )

    assert generate_code == 0
    case_files = sorted(generated_cases.glob("*.yaml"))
    assert len(case_files) == 2

    solve_code = main(
        [
            "solve-case",
            "--case",
            str(case_files[0]),
            "--output-root",
            str(run_root),
        ]
    )

    assert solve_code == 0
    assert any(run_root.rglob("case.yaml"))
    assert any(run_root.rglob("solution.yaml"))
    assert any(run_root.rglob("manifest.json"))


def test_generate_case_cli_rejects_paired_benchmark_template(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="generate-operating-case-pair"):
        main(
            [
                "generate-case",
                "--template",
                "scenarios/templates/panel_four_component_hot_cold_benchmark.yaml",
                "--seed",
                "3",
                "--output-root",
                str(tmp_path / "generated_cases"),
            ]
        )


def test_generate_operating_case_pair_cli_writes_hot_and_cold_cases(tmp_path: Path) -> None:
    generated_cases = tmp_path / "paired_cases"

    generate_code = main(
        [
            "generate-operating-case-pair",
            "--template",
            "scenarios/templates/panel_four_component_hot_cold_benchmark.yaml",
            "--seed",
            "11",
            "--output-root",
            str(generated_cases),
        ]
    )

    assert generate_code == 0
    case_files = sorted(generated_cases.glob("*.yaml"))
    assert len(case_files) == 2
    assert any(path.name.endswith("-hot.yaml") for path in case_files)
    assert any(path.name.endswith("-cold.yaml") for path in case_files)
