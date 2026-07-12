import argparse

import pytest

from stryktips import create_parser


def test_create_parser_returns_argparse_parser():
    parser = create_parser()

    assert isinstance(parser, argparse.ArgumentParser)
    assert parser.prog == "stryktips.py"
    assert parser.description is not None


def test_create_parser_has_draw_argument():
    parser = create_parser()

    args = parser.parse_args(["--draw", "1"])

    assert args.draw == 1


def test_create_parser_draw_is_required():
    parser = create_parser()

    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_create_parser_accepts_integer_draw():
    parser = create_parser()

    args = parser.parse_args(["--draw", "4900"])

    assert args.draw == 4900
    assert isinstance(args.draw, int)
