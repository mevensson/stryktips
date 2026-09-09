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


def test_create_parser_accepts_start_draw_and_end_draw_together():
    """--start-draw and --end-draw parse together into a report range."""
    parser = create_parser()

    args = parser.parse_args(["--start-draw", "4900", "--end-draw", "4900"])

    assert args.start_draw == 4900
    assert args.end_draw == 4900


def test_create_parser_help_lists_start_draw_and_end_draw():
    """Help text documents both --start-draw and --end-draw flags."""
    parser = create_parser()

    help_text = parser.format_help()

    assert "--start-draw" in help_text
    assert "--end-draw" in help_text


def test_create_parser_accepts_start_date_and_end_draw_together():
    """--start-date and --end-draw parse together into a report range."""
    parser = create_parser()

    args = parser.parse_args(["--start-date", "2025-05-10", "--end-draw", "4900"])

    assert args.start_date == "2025-05-10"
    assert args.end_draw == 4900


def test_create_parser_start_date_and_start_draw_mutually_exclusive(capsys):
    """Combining --start-date with --start-draw exits with an error."""
    parser = create_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["--start-date", "2025-05-10", "--start-draw", "4900"])
    captured = capsys.readouterr()

    assert "not allowed with" in captured.err


def test_create_parser_accepts_start_draw_and_end_date_together():
    """--start-draw and --end-date parse together into a report range."""
    parser = create_parser()

    args = parser.parse_args(["--start-draw", "4900", "--end-date", "2025-05-10"])

    assert args.start_draw == 4900
    assert args.end_date == "2025-05-10"


def test_create_parser_help_lists_start_date_and_end_date():
    """Help text documents both --start-date and --end-date flags."""
    parser = create_parser()

    help_text = parser.format_help()

    assert "--start-date" in help_text
    assert "--end-date" in help_text


def test_create_parser_accepts_start_week_and_end_draw_together():
    """--start-week and --end-draw parse together into a report range."""
    parser = create_parser()

    args = parser.parse_args(["--start-week", "2025.19", "--end-draw", "4900"])

    assert args.start_week == "2025.19"
    assert args.end_draw == 4900


def test_create_parser_accepts_start_draw_and_end_week_together():
    """--start-draw and --end-week parse together into a report range."""
    parser = create_parser()

    args = parser.parse_args(["--start-draw", "4900", "--end-week", "2025.19"])

    assert args.start_draw == 4900
    assert args.end_week == "2025.19"


def test_create_parser_start_week_and_start_draw_mutually_exclusive(capsys):
    """Combining --start-week with --start-draw exits with an error."""
    parser = create_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["--start-week", "2025.19", "--start-draw", "4900"])
    captured = capsys.readouterr()

    assert "not allowed with" in captured.err


def test_create_parser_help_lists_start_week_and_end_week():
    """Help text documents both --start-week and --end-week flags."""
    parser = create_parser()

    help_text = parser.format_help()

    assert "--start-week" in help_text
    assert "--end-week" in help_text
