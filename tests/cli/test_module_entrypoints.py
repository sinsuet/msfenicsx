from __future__ import annotations

import subprocess
import sys


def test_core_cli_module_entrypoint_prints_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "core.cli.main"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_evaluation_cli_module_entrypoint_prints_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evaluation.cli"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_optimizer_cli_module_entrypoint_prints_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "optimizers.cli"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "usage:" in result.stdout
