"""Unit tests for the stryktips argument parser."""

import argparse

import pytest

from stryktips import create_parser


def test_create_parser_returns_configured_argparse_parser():
    """create_parser returns a configured argparse parser."""
    # Act
    parser = create_parser()

    # Assert
    assert isinstance(parser, argparse.ArgumentParser)
    assert parser.prog == "stryktips.py"
    assert parser.description is not None


def test_create_parser_has_draw_argument():
    """--draw parses to an integer draw number."""
    # Arrange
    parser = create_parser()

    # Act
    args = parser.parse_args(["--draw", "1"])

    # Assert
    assert args.draw == 1


def test_create_parser_accepts_integer_draw():
    """--draw parses multi-digit integers without loss."""
    # Arrange
    parser = create_parser()

    # Act
    args = parser.parse_args(["--draw", "4900"])

    # Assert
    assert args.draw == 4900


def test_create_parser_draw_is_required():
    """Invoking the parser with no arguments exits with an error."""
    parser = create_parser()

    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_create_parser_has_date_argument():
    """--date parses to a string date value."""
    # Arrange
    parser = create_parser()

    # Act
    args = parser.parse_args(["--date", "2025-05-10"])

    # Assert
    assert args.date == "2025-05-10"


def test_create_parser_has_week_argument():
    """--week parses to a string week value."""
    # Arrange
    parser = create_parser()

    # Act
    args = parser.parse_args(["--week", "2025.19"])

    # Assert
    assert args.week == "2025.19"


@pytest.mark.parametrize(
    "argv",
    [
        ["--week", "abc"],
        ["--week", "2025"],
        ["--week", "2025.99"],
        ["--week", "2025.19.0"],
        ["--start-week", "abc", "--end-draw", "4900"],
        ["--start-draw", "4900", "--end-week", "abc"],
    ],
    ids=[
        "draw-week-non-numeric",
        "draw-week-no-index",
        "draw-week-invalid-week-number",
        "draw-week-zero-index",
        "start-week-invalid",
        "end-week-invalid",
    ],
)
def test_create_parser_rejects_invalid_week(argv):
    """--week, --start-week, and --end-week reject malformed values."""
    parser = create_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(argv)


@pytest.mark.parametrize(
    "argv",
    [
        ["--draw", "4900", "--date", "2025-05-10"],
        ["--start-date", "2025-05-10", "--start-draw", "4900"],
        ["--start-week", "2025.19", "--start-draw", "4900"],
    ],
    ids=["draw-with-date", "start-date-with-start-draw", "start-week-with-start-draw"],
)
def test_create_parser_rejects_conflicting_bounds(argv, capsys):
    """Combining mutually exclusive bound flags exits with an error."""
    parser = create_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(argv)
    captured = capsys.readouterr()

    assert "not allowed with" in captured.err


def test_create_parser_accepts_start_draw_and_end_draw_together():
    """--start-draw and --end-draw parse together into a report range."""
    # Arrange
    parser = create_parser()

    # Act
    args = parser.parse_args(["--start-draw", "4900", "--end-draw", "4900"])

    # Assert
    assert args.start_draw == 4900
    assert args.end_draw == 4900


def test_create_parser_accepts_start_date_and_end_draw_together():
    """--start-date and --end-draw parse together into a report range."""
    # Arrange
    parser = create_parser()

    # Act
    args = parser.parse_args(["--start-date", "2025-05-10", "--end-draw", "4900"])

    # Assert
    assert args.start_date == "2025-05-10"
    assert args.end_draw == 4900


def test_create_parser_accepts_start_draw_and_end_date_together():
    """--start-draw and --end-date parse together into a report range."""
    # Arrange
    parser = create_parser()

    # Act
    args = parser.parse_args(["--start-draw", "4900", "--end-date", "2025-05-10"])

    # Assert
    assert args.start_draw == 4900
    assert args.end_date == "2025-05-10"


def test_create_parser_accepts_start_week_and_end_draw_together():
    """--start-week and --end-draw parse together into a report range."""
    # Arrange
    parser = create_parser()

    # Act
    args = parser.parse_args(["--start-week", "2025.19", "--end-draw", "4900"])

    # Assert
    assert args.start_week == "2025.19"
    assert args.end_draw == 4900


def test_create_parser_accepts_start_draw_and_end_week_together():
    """--start-draw and --end-week parse together into a report range."""
    # Arrange
    parser = create_parser()

    # Act
    args = parser.parse_args(["--start-draw", "4900", "--end-week", "2025.19"])

    # Assert
    assert args.start_draw == 4900
    assert args.end_week == "2025.19"


@pytest.mark.parametrize(
    ("first_flag", "second_flag"),
    [
        ("--start-draw", "--end-draw"),
        ("--start-date", "--end-date"),
        ("--start-week", "--end-week"),
    ],
    ids=["draw-bounds", "date-bounds", "week-bounds"],
)
def test_create_parser_help_lists_report_bounds(first_flag, second_flag):
    """Help text documents both flags of each report bound pair."""
    # Arrange
    parser = create_parser()

    # Act
    help_text = parser.format_help()

    # Assert
    assert first_flag in help_text
    assert second_flag in help_text
