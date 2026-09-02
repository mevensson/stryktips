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


def test_start_end_spanning_months_aggregates(mock_response, capsys):  # noqa: PLR0915
    """--start 4881 --end 4884 folds every draw in range into one report.

    Draws 4881-4884 span the Dec 2024/Jan 2025 month boundary. The result is a
    single aggregated summary (eligible/excluded summed) plus merged bucket rows;
    no draw outside [4881, 4884] is fetched.
    """
    draw_url = "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/{n}"
    for draw_number in (4881, 4882, 4883, 4884):
        draw_data: dict[str, Any] = json.loads(
            Path(f"tests/fixtures/week_{draw_number}.json").read_text()
        )
        flexmock(requests).should_receive("get").with_args(
            draw_url.format(n=draw_number), timeout=30
        ).and_return(mock_response(draw_data))

    datepicker_url = (
        "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
        "?product=stryktipset&year={year}&month={month}"
    )
    for year, month in ((2024, 12), (2025, 1)):
        datepicker_data: dict[str, Any] = json.loads(
            Path(f"tests/fixtures/datepicker_{year}_{month:02d}.json").read_text()
        )
        flexmock(requests).should_receive("get").with_args(
            datepicker_url.format(year=year, month=month), timeout=30
        ).and_return(mock_response(datepicker_data))

    # No draw outside the range may be fetched, on either side of the boundary.
    for out_of_range in (4880, 4885, 4886):
        flexmock(requests).should_receive("get").with_args(
            draw_url.format(n=out_of_range), timeout=30
        ).never()

    exit_code = main(["--start", "4881", "--end", "4884"])
    captured = capsys.readouterr()

    assert exit_code == 0
    lines = captured.out.strip().split("\n")
    assert "eligible: 47, excluded: 0" in lines[0]
    assert len(lines) == 9
    assert lines[1:] == [
        "0-10: 1",
        "10-20: 2",
        "20-30: 17",
        "30-40: 7",
        "40-50: 7",
        "50-60: 5",
        "60-70: 6",
        "70-80: 2",
    ]


def test_start_end_walks_datepicker_across_drawless_months(  # noqa: PLR0915
    mock_response, capsys
):
    """--start 4641 --end 4642 walks the datepicker across the Apr/May 2020 gap.

    Draw 4641 (Mar 2020) and draw 4642 (Jun 2020) straddle April and May 2020,
    which have no draws and so return 404 from the datepicker. The walk must query
    every month in between and collect only the draws in [4641, 4642], fetching
    nothing outside that range.
    """
    draw_url = "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/{n}"
    for draw_number in (4641, 4642):
        draw_data: dict[str, Any] = json.loads(
            Path(f"tests/fixtures/week_{draw_number}.json").read_text()
        )
        flexmock(requests).should_receive("get").with_args(
            draw_url.format(n=draw_number), timeout=30
        ).and_return(mock_response(draw_data))

    datepicker_url = (
        "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
        "?product=stryktipset&year={year}&month={month}"
    )
    # Months with draws return 200; the drawless Apr/May 2020 months return 404.
    for year, month in ((2020, 3), (2020, 6)):
        datepicker_data: dict[str, Any] = json.loads(
            Path(f"tests/fixtures/datepicker_{year}_{month:02d}.json").read_text()
        )
        flexmock(requests).should_receive("get").with_args(
            datepicker_url.format(year=year, month=month), timeout=30
        ).once().and_return(mock_response(datepicker_data))
    for year, month in ((2020, 4), (2020, 5)):
        flexmock(requests).should_receive("get").with_args(
            datepicker_url.format(year=year, month=month), timeout=30
        ).once().and_return(mock_response({"error": "not_found"}, status_code=404))

    # No draw outside [4641, 4642] may be fetched, on either side of the gap.
    for out_of_range in (4639, 4640, 4643, 4644):
        flexmock(requests).should_receive("get").with_args(
            draw_url.format(n=out_of_range), timeout=30
        ).never()

    exit_code = main(["--start", "4641", "--end", "4642"])
    captured = capsys.readouterr()

    assert exit_code == 0
    lines = captured.out.strip().split("\n")
    assert lines == ["eligible: 0, excluded: 20"]
