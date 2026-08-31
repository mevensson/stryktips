import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import requests
from flexmock import flexmock

from stryktips import main


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


def test_start_end_4900_reports_buckets(mock_response, capsys):  # noqa: PLR0915
    """--start 4900 --end 4900 prints the bucket report for draw 4900."""
    draw_data: dict[str, Any] = json.loads(
        Path("tests/fixtures/week_4900.json").read_text()
    )
    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/4900",
        timeout=30,
    ).and_return(mock_response(draw_data))

    exit_code = main(["--start", "4900", "--end", "4900"])
    captured = capsys.readouterr()

    assert exit_code == 0
    lines = captured.out.strip().split("\n")
    assert "eligible: 13, excluded: 0" in lines[0]
    assert "10-20: 1" in lines
    assert "20-30: 5" in lines
    assert "30-40: 3" in lines
    assert "40-50: 1" in lines
    assert "50-60: 3" in lines


def test_start_end_excludes_played_without_odds(mock_response, capsys):
    """--start 4642 --end 4642 counts played-but-odds-less matches as excluded."""
    draw_data: dict[str, Any] = json.loads(
        Path("tests/fixtures/week_4642.json").read_text()
    )
    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/4642",
        timeout=30,
    ).and_return(mock_response(draw_data))

    exit_code = main(["--start", "4642", "--end", "4642"])
    captured = capsys.readouterr()

    assert exit_code == 0
    lines = captured.out.strip().split("\n")
    assert "eligible: 0, excluded: 13" in lines[0]
    assert len(lines) == 1  # no bucket rows for an all-excluded draw
