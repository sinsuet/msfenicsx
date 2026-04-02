from pathlib import Path

from core.cli.main import build_parser, main
from evaluation.cli import build_parser as build_evaluation_parser


def test_generate_case_then_solve_cli_smoke(tmp_path: Path) -> None:
    generated_cases = tmp_path / "generated_case"
    run_root = tmp_path / "scenario_runs"

    generate_code = main(
        [
            "generate-case",
            "--template",
            "scenarios/templates/s1_typical.yaml",
            "--seed",
            "11",
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


def test_generate_case_is_the_only_mainline_generation_command() -> None:
    parser = build_parser()
    command_names = set(parser._subparsers._group_actions[0].choices)

    assert "generate-operating-case-pair" not in command_names


def test_evaluate_case_is_the_only_public_evaluation_command() -> None:
    parser = build_evaluation_parser()
    command_names = set(parser._subparsers._group_actions[0].choices)

    assert "evaluate-operating-cases" not in command_names
