import subprocess
import sys

import pytest


def test_help_shows_start_end_usage():
    result = subprocess.run(
        [sys.executable, "stryktips.py", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.returncode == 0
    assert "--start" in result.stdout
    assert "--end" in result.stdout


def test_start_argument_required():
    result = subprocess.run(
        [sys.executable, "stryktips.py"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "--start" in result.stdout or "--start" in result.stderr
    assert "--end" in result.stdout or "--end" in result.stderr


@pytest.mark.parametrize(
    "args",
    [
        ["--start", "4900", "--draw", "4900"],
        ["--start", "4900", "--date", "2025-05-09"],
        ["--start", "4900", "--week", "2025.19"],
        ["--draw", "4900", "--end", "4900"],
        ["--date", "2025-05-09", "--end", "4900"],
        ["--week", "2025.19", "--end", "4900"],
    ],
)
def test_start_end_mutually_exclusive(args):
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
        ["--start", "abc"],
        ["--start", "abc", "--end", "4900"],
        ["--end", "abc"],
        ["--start", "4900", "--end", "abc"],
    ],
)
def test_invalid_start_or_end_rejected(args):
    result = subprocess.run(
        [sys.executable, "stryktips.py", *args],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2