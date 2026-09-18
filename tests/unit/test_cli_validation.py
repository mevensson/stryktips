"""CLI argument-validation tests for stryktips.core, exercised through main().

Argument-level validation and its precedence are driven through ``main`` with
the real parser; these tests assert exit codes and stderr.
"""

import pytest

import stryktips.core


def test_main_start_draw_greater_than_end_draw_rejected(capsys):
    """An explicit start greater than the explicit end is a parser error."""
    with pytest.raises(SystemExit) as exc:
        stryktips.core.main(["--start-draw", "4901", "--end-draw", "4900"])
    captured = capsys.readouterr()

    assert exc.value.code == 2
    assert "--start-draw must not be greater than --end-draw" in captured.err


def test_main_end_date_without_start_rejected(capsys):
    """--end-date without any --start-* bound is a parser error."""
    with pytest.raises(SystemExit) as exc:
        stryktips.core.main(["--end-date", "2025-05-10"])
    captured = capsys.readouterr()

    assert exc.value.code == 2
    assert "--end-date requires --start" in captured.err


def test_main_end_week_without_start_rejected(capsys):
    """--end-week without any --start-* bound is a parser error."""
    with pytest.raises(SystemExit) as exc:
        stryktips.core.main(["--end-week", "2025.19"])
    captured = capsys.readouterr()

    assert exc.value.code == 2
    assert "--end-week requires --start" in captured.err


def test_main_end_without_start_precedes_malformed_end_value(capsys):
    """--end-draw without a start rejects before the malformed value is parsed."""
    with pytest.raises(SystemExit) as exc:
        stryktips.core.main(["--end-draw", "abc"])
    captured = capsys.readouterr()

    assert exc.value.code == 2
    assert "--end-draw requires --start-draw" in captured.err
    assert "invalid int value" not in captured.err


def test_main_end_without_start_precedes_help(capsys):
    """--end-draw without a start rejects before --help can print usage."""
    with pytest.raises(SystemExit) as exc:
        stryktips.core.main(["--end-draw", "4900", "--help"])
    captured = capsys.readouterr()

    assert exc.value.code == 2
    assert "--end-draw requires --start-draw" in captured.err
    assert captured.out == ""


@pytest.mark.parametrize(
    "flag",
    ["--end-draw=4900", "--end-date=2025-05-10", "--end-week=2025.19"],
    ids=["draw", "date", "week"],
)
def test_main_end_without_start_detected_in_equals_form(flag, capsys):
    """An --end-* flag in equals form still requires a --start-* bound."""
    with pytest.raises(SystemExit) as exc:
        stryktips.core.main([flag])
    captured = capsys.readouterr()

    assert exc.value.code == 2
    assert "requires --start-draw" in captured.err
