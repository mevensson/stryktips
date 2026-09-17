"""End-to-end validation tests for the prediction-quality report CLI."""

import subprocess
import sys

import pytest


def test_help_shows_start_draw_end_draw_usage():
    result = subprocess.run(
        [sys.executable, "stryktips.py", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.returncode == 0
    assert "--start-draw" in result.stdout
    assert "--end-draw" in result.stdout


def test_start_draw_argument_required():
    result = subprocess.run(
        [sys.executable, "stryktips.py"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "--start-draw" in result.stdout or "--start-draw" in result.stderr
    assert "--end-draw" in result.stdout or "--end-draw" in result.stderr


@pytest.mark.parametrize(
    "args",
    [
        ["--start-draw", "4900", "--draw", "4900"],
        ["--start-draw", "4900", "--date", "2025-05-09"],
        ["--start-draw", "4900", "--week", "2025.19"],
        ["--draw", "4900", "--end-draw", "4900"],
        ["--date", "2025-05-09", "--end-draw", "4900"],
        ["--week", "2025.19", "--end-draw", "4900"],
    ],
)
def test_start_draw_end_draw_mutually_exclusive(args):
    result = subprocess.run(
        [sys.executable, "stryktips.py", *args],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2


def test_start_draw_after_end_draw_errors():
    """--start-draw 4900 --end-draw 4884 errors clearly and exits non-zero.

    An explicit --start-draw later than an explicit --end-draw is a mistake, so the
    CLI must explain it on stderr and exit non-zero instead of producing a
    confusing report.
    """
    result = subprocess.run(
        [sys.executable, "stryktips.py", "--start-draw", "4900", "--end-draw", "4884"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "--start-draw must not be greater than --end-draw" in result.stderr


@pytest.mark.parametrize(
    "args",
    [
        ["--start-draw", "abc"],
        ["--start-draw", "abc", "--end-draw", "4900"],
        ["--end-draw", "abc"],
        ["--start-draw", "4900", "--end-draw", "abc"],
    ],
)
def test_invalid_start_draw_or_end_draw_rejected(args):
    result = subprocess.run(
        [sys.executable, "stryktips.py", *args],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2


@pytest.mark.parametrize(
    "args",
    [
        ["--end-draw", "4900"],
        ["--end-date", "2025-05-10"],
        ["--end-week", "2025.19"],
    ],
)
def test_end_without_start_rejected(args):
    """--end-* without any --start-* bound is rejected (exit 2)."""
    result = subprocess.run(
        [sys.executable, "stryktips.py", *args],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "requires --start-draw" in result.stderr
