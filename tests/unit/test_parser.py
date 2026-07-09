import argparse

import pytest

from stryktips import create_parser


def test_create_parser_returns_argparse_parser():
    parser = create_parser()

    assert isinstance(parser, argparse.ArgumentParser)
    assert parser.prog == "stryktips.py"
    assert parser.description is not None


def test_create_parser_has_week_argument():
    parser = create_parser()

    args = parser.parse_args(["--week", "1"])

    assert args.week == 1


def test_create_parser_week_is_required():
    parser = create_parser()

    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_create_parser_accepts_integer_week():
    parser = create_parser()

    args = parser.parse_args(["--week", "4900"])

    assert args.week == 4900
    assert isinstance(args.week, int)
