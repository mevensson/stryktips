"""Unit tests for the stryktips argument parser."""

import argparse

import pytest

from stryktips import create_parser


def test_create_parser_returns_argparse_parser():
    """create_parser returns a configured argparse parser."""
    parser = create_parser()

    assert isinstance(parser, argparse.ArgumentParser)
    assert parser.prog == "stryktips.py"
    assert parser.description is not None


def test_create_parser_has_draw_argument():
    """--draw parses to an integer draw number."""
    parser = create_parser()

    args = parser.parse_args(["--draw", "1"])

    assert args.draw == 1


def test_create_parser_draw_is_required():
    """Invoking the parser with no arguments exits with an error."""
    parser = create_parser()

    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_create_parser_accepts_integer_draw():
    """--draw parses multi-digit integers without loss."""
    parser = create_parser()

    args = parser.parse_args(["--draw", "4900"])

    assert args.draw == 4900
    assert isinstance(args.draw, int)


def test_create_parser_has_date_argument():
    """--date parses to a string date value."""
    parser = create_parser()

    args = parser.parse_args(["--date", "2025-05-10"])

    assert args.date == "2025-05-10"


def test_create_parser_has_week_argument():
    """--week parses to a string week value."""
    parser = create_parser()

    args = parser.parse_args(["--week", "2025.19"])

    assert args.week == "2025.19"


def test_create_parser_rejects_invalid_week():
    """--week with a malformed value exits with an error."""
    parser = create_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["--week", "abc"])


def test_create_parser_date_and_draw_are_mutually_exclusive():
    """Combining --draw with --date exits with an error."""
    parser = create_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["--draw", "4900", "--date", "2025-05-10"])


def test_create_parser_accepts_start_and_end_together():
    """--start and --end parse together into a report range."""
    parser = create_parser()

    args = parser.parse_args(["--start", "4900", "--end", "4900"])

    assert args.start == 4900
    assert args.end == 4900


def test_create_parser_help_lists_start_and_end():
    """Help text documents both --start and --end flags."""
    parser = create_parser()

    help_text = parser.format_help()

    assert "--start" in help_text
    assert "--end" in help_text
