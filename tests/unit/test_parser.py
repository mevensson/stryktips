import argparse

from stryktips import create_parser


def test_create_parser_returns_argparse_parser():
    parser = create_parser()

    assert isinstance(parser, argparse.ArgumentParser)
    assert parser.prog == "stryktips.py"
    assert parser.description is not None
    assert any(action.dest == "help" for action in parser._actions)
