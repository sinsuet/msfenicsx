from __future__ import annotations

import pytest

from optimizers.cli import build_parser


def test_optimizer_cli_exposes_unified_command_only() -> None:
    parser = build_parser()
    command_names = set(parser._subparsers._group_actions[0].choices)

    assert command_names == {"run-benchmark"}


def test_optimizer_cli_rejects_non_positive_evaluation_workers() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "run-benchmark",
                "--optimization-spec",
                "spec.yaml",
                "--mode",
                "raw",
                "--benchmark-seed",
                "11",
                "--algorithm-seed",
                "1011",
                "--population-size",
                "40",
                "--num-generations",
                "32",
                "--evaluation-workers",
                "0",
            ]
        )
