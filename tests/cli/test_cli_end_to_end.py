from pathlib import Path

from core.cli.main import main


def test_generate_then_solve_cli_smoke(tmp_path: Path) -> None:
    generated_cases = tmp_path / "generated_cases"
    run_root = tmp_path / "scenario_runs"

    generate_code = main(
        [
            "generate-case",
            "--template",
            "scenarios/templates/panel_radiation_baseline.yaml",
            "--seed",
            "3",
            "--output-root",
            str(generated_cases),
        ]
    )

    assert generate_code == 0
    case_files = sorted(generated_cases.glob("*.yaml"))
    assert len(case_files) == 1

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
