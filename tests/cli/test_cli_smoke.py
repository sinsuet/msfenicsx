from core.cli.main import build_parser


def test_build_parser_exposes_command_argument() -> None:
    parser = build_parser()
    actions = [action.dest for action in parser._actions]
    assert "command" in actions
