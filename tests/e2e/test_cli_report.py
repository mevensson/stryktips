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
    assert lines[1:] == [
        "0-10: 1 | 8% | 0% | -8%",
        "10-20: 4 | 17% | 25% | 8%",
        "20-30: 15 | 25% | 33% | 8%",
        "30-40: 10 | 36% | 30% | -6%",
        "40-50: 3 | 42% | 33% | -9%",
        "50-60: 5 | 56% | 60% | 4%",
        "70-80: 1 | 79% | 0% | -79%",
    ]


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
        "0-10: 1 | 8% | 100% | 92%",
        "10-20: 24 | 16% | 8% | -8%",
        "20-30: 57 | 26% | 30% | 4%",
        "30-40: 19 | 35% | 37% | 2%",
        "40-50: 14 | 44% | 50% | 6%",
        "50-60: 14 | 55% | 36% | -19%",
        "60-70: 9 | 65% | 67% | 2%",
        "70-80: 3 | 74% | 67% | -7%",
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


def test_start_end_skips_absent_draw_number(mock_response, capsys):  # noqa: PLR0915
    """--start 4882 --end 4884 skips the interior draw absent from the datepicker.

    Draw 4883 is a hole in the range: it appears in no datepicker month, so the walk
    must not collect or fetch it. Only 4882 and 4884 are aggregated into the report.
    """
    draw_url = "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/{n}"
    for draw_number in (4882, 4884):
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
    # Synthetic Jan 2025 datepicker: 4883 is omitted entirely from the month's data.
    datepicker_data: dict[str, Any] = {
        "resultDates": [
            {"date": "2025-01-04T00:00:00+01:00", "drawNumber": 4882},
            {"date": "2025-01-18T00:00:00+01:00", "drawNumber": 4884},
        ]
    }
    flexmock(requests).should_receive("get").with_args(
        datepicker_url.format(year=2025, month=1), timeout=30
    ).once().and_return(mock_response(datepicker_data))

    # The absent interior draw must never be fetched.
    flexmock(requests).should_receive("get").with_args(
        draw_url.format(n=4883), timeout=30
    ).never()

    exit_code = main(["--start", "4882", "--end", "4884"])
    captured = capsys.readouterr()

    assert exit_code == 0
    lines = captured.out.strip().split("\n")
    assert lines == [
        "eligible: 26, excluded: 0",
        "10-20: 11 | 16% | 9% | -7%",
        "20-30: 34 | 26% | 26% | 0%",
        "30-40: 12 | 35% | 42% | 7%",
        "40-50: 8 | 44% | 75% | 31%",
        "50-60: 8 | 55% | 25% | -30%",
        "60-70: 3 | 64% | 33% | -31%",
        "70-80: 2 | 73% | 100% | 27%",
    ]


def test_start_end_reports_and_skips_fetch_failure(mock_response, capsys):  # noqa: PLR0915
    """--start 4882 --end 4884 warns and skips an interior draw that 404s.

    Draw 4883 is present in the datepicker but its individual fetch 404s. The
    walk must print a warning to stderr, skip it, and still aggregate the rest
    of the range (4882 + 4884) into the report.
    """
    draw_url = "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/{n}"
    for draw_number in (4882, 4884):
        draw_data: dict[str, Any] = json.loads(
            Path(f"tests/fixtures/week_{draw_number}.json").read_text()
        )
        flexmock(requests).should_receive("get").with_args(
            draw_url.format(n=draw_number), timeout=30
        ).once().and_return(mock_response(draw_data))

    # The interior draw is present in the datepicker but its fetch returns 404.
    not_found = flexmock(status_code=404)
    not_found.should_receive("raise_for_status").and_raise(
        requests.HTTPError("404 Client Error")
    )
    flexmock(requests).should_receive("get").with_args(
        draw_url.format(n=4883), timeout=30
    ).once().and_return(not_found)

    datepicker_url = (
        "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
        "?product=stryktipset&year={year}&month={month}"
    )
    datepicker_data: dict[str, Any] = json.loads(
        Path("tests/fixtures/datepicker_2025_01.json").read_text()
    )
    flexmock(requests).should_receive("get").with_args(
        datepicker_url.format(year=2025, month=1), timeout=30
    ).once().and_return(mock_response(datepicker_data))

    # No draw outside the range may be fetched, on either side of the range.
    for out_of_range in (4885, 4886):
        flexmock(requests).should_receive("get").with_args(
            draw_url.format(n=out_of_range), timeout=30
        ).never()

    exit_code = main(["--start", "4882", "--end", "4884"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Warning: could not fetch draw 4883, skipping." in captured.err
    assert "404 Client Error" not in captured.err
    lines = captured.out.strip().split("\n")
    assert lines == [
        "eligible: 26, excluded: 0",
        "10-20: 11 | 16% | 9% | -7%",
        "20-30: 34 | 26% | 26% | 0%",
        "30-40: 12 | 35% | 42% | 7%",
        "40-50: 8 | 44% | 75% | 31%",
        "50-60: 8 | 55% | 25% | -30%",
        "60-70: 3 | 64% | 33% | -31%",
        "70-80: 2 | 73% | 100% | 27%",
    ]


def test_start_end_empty_range_prints_empty_report(capsys):
    """--start/--end over a range with no collectible draw prints an empty report."""
    not_found = flexmock(status_code=404)
    not_found.should_receive("raise_for_status").and_raise(
        requests.HTTPError("404 Client Error")
    )
    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/4900",
        timeout=30,
    ).and_return(not_found)

    exit_code = main(["--start", "4900", "--end", "4900"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.strip() == "eligible: 0, excluded: 0"
