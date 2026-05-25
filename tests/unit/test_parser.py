import argparse

from stryktips import create_parser


def test_create_parser_returns_argparse_parser():
    parser = create_parser()

    assert isinstance(parser, argparse.ArgumentParser)
    assert parser.prog == "stryktips.py"
    assert parser.description is not None
    assert any(action.dest == "help" for action in parser._actions)


def test_parser_has_week_argument():
    parser = create_parser()

    week_action = None
    for action in parser._actions:
        if action.dest == "week":
            week_action = action
            break

    assert week_action is not None, "Parser should have a 'week' argument"


def test_parser_week_required():
    parser = create_parser()

    week_action = None
    for action in parser._actions:
        if action.dest == "week":
            week_action = action
            break

    assert week_action is not None, "Parser should have a 'week' argument"
    assert week_action.required is True, "--week argument should be required"


def test_parser_week_accepts_integer():
    parser = create_parser()

    args = parser.parse_args(["--week", "4900"])
    assert args.week == 4900
    assert isinstance(args.week, int)
