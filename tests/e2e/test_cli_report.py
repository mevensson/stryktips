import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import requests
from flexmock import flexmock

import stryktips.core as stryktips_core
from stryktips import main

_FIXTURES = Path(__file__).parent.parent / "fixtures"


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


def test_start_draw_end_draw_4900_reports_buckets(mock_response, capsys):  # noqa: PLR0915
    """--start-draw 4900 --end-draw 4900 prints the bucket report for draw 4900."""
    draw_data: dict[str, Any] = json.loads((_FIXTURES / "week_4900.json").read_text())
    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/4900",
        timeout=30,
    ).and_return(mock_response(draw_data))

    exit_code = main(["--start-draw", "4900", "--end-draw", "4900"])
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


def test_start_draw_end_draw_excludes_played_without_odds(mock_response, capsys):
    """--start-draw 4642 --end-draw 4642 counts odds-less played matches as excluded."""
    draw_data: dict[str, Any] = json.loads((_FIXTURES / "week_4642.json").read_text())
    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/4642",
        timeout=30,
    ).and_return(mock_response(draw_data))

    exit_code = main(["--start-draw", "4642", "--end-draw", "4642"])
    captured = capsys.readouterr()

    assert exit_code == 0
    lines = captured.out.strip().split("\n")
    assert "eligible: 0, excluded: 13" in lines[0]
    assert len(lines) == 1  # no bucket rows for an all-excluded draw


def test_start_draw_end_draw_spanning_months_aggregates(mock_response, capsys):  # noqa: PLR0915
    """--start-draw 4881 --end-draw 4884 folds every draw in range into one report.

    Draws 4881-4884 span the Dec 2024/Jan 2025 month boundary. The result is a
    single aggregated summary (eligible/excluded summed) plus merged bucket rows;
    no draw outside [4881, 4884] is fetched.
    """
    draw_url = "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/{n}"
    for draw_number in (4881, 4882, 4883, 4884):
        draw_data: dict[str, Any] = json.loads(
            (_FIXTURES / f"week_{draw_number}.json").read_text()
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
            (_FIXTURES / f"datepicker_{year}_{month:02d}.json").read_text()
        )
        flexmock(requests).should_receive("get").with_args(
            datepicker_url.format(year=year, month=month), timeout=30
        ).and_return(mock_response(datepicker_data))

    # No draw outside the range may be fetched, on either side of the boundary.
    for out_of_range in (4880, 4885, 4886):
        flexmock(requests).should_receive("get").with_args(
            draw_url.format(n=out_of_range), timeout=30
        ).never()

    exit_code = main(["--start-draw", "4881", "--end-draw", "4884"])
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


def test_start_draw_end_draw_walks_datepicker_across_drawless_months(  # noqa: PLR0915
    mock_response, capsys
):
    """--start-draw 4641 --end-draw 4642 walks across the Apr/May 2020 gap.

    Draw 4641 (Mar 2020) and draw 4642 (Jun 2020) straddle April and May 2020,
    which have no draws and so return 404 from the datepicker. The walk must query
    every month in between and collect only the draws in [4641, 4642], fetching
    nothing outside that range.
    """
    draw_url = "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/{n}"
    for draw_number in (4641, 4642):
        draw_data: dict[str, Any] = json.loads(
            (_FIXTURES / f"week_{draw_number}.json").read_text()
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
            (_FIXTURES / f"datepicker_{year}_{month:02d}.json").read_text()
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

    exit_code = main(["--start-draw", "4641", "--end-draw", "4642"])
    captured = capsys.readouterr()

    assert exit_code == 0
    lines = captured.out.strip().split("\n")
    assert lines == ["eligible: 0, excluded: 20"]


def test_start_draw_end_draw_skips_absent_draw_number(mock_response, capsys):  # noqa: PLR0915
    """--start-draw 4882 --end-draw 4884 skips the draw missing from datepicker.

    Draw 4883 is a hole in the range: it appears in no datepicker month, so the walk
    must not collect or fetch it. Only 4882 and 4884 are aggregated into the report.
    """
    draw_url = "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/{n}"
    for draw_number in (4882, 4884):
        draw_data: dict[str, Any] = json.loads(
            (_FIXTURES / f"week_{draw_number}.json").read_text()
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

    exit_code = main(["--start-draw", "4882", "--end-draw", "4884"])
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


def test_start_draw_end_draw_reports_and_skips_fetch_failure(mock_response, capsys):  # noqa: PLR0915
    """--start-draw 4882 --end-draw 4884 warns and skips an interior draw that 404s.

    Draw 4883 is present in the datepicker but its individual fetch 404s. The
    walk must print a warning to stderr, skip it, and still aggregate the rest
    of the range (4882 + 4884) into the report.
    """
    draw_url = "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/{n}"
    for draw_number in (4882, 4884):
        draw_data: dict[str, Any] = json.loads(
            (_FIXTURES / f"week_{draw_number}.json").read_text()
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
        (_FIXTURES / "datepicker_2025_01.json").read_text()
    )
    flexmock(requests).should_receive("get").with_args(
        datepicker_url.format(year=2025, month=1), timeout=30
    ).once().and_return(mock_response(datepicker_data))

    # No draw outside the range may be fetched, on either side of the range.
    for out_of_range in (4885, 4886):
        flexmock(requests).should_receive("get").with_args(
            draw_url.format(n=out_of_range), timeout=30
        ).never()

    exit_code = main(["--start-draw", "4882", "--end-draw", "4884"])
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


def test_start_draw_end_draw_empty_range_prints_empty_report(capsys):
    """--start-draw/--end-draw with no collectible draw prints an empty report."""
    not_found = flexmock(status_code=404)
    not_found.should_receive("raise_for_status").and_raise(
        requests.HTTPError("404 Client Error")
    )
    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/4900",
        timeout=30,
    ).and_return(not_found)

    exit_code = main(["--start-draw", "4900", "--end-draw", "4900"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.strip() == "eligible: 0, excluded: 0"


def test_start_draw_end_draw_anchor_returns_null_draw_prints_empty_report(
    mock_response, capsys
):
    """--start-draw/--end-draw where the anchor draw is a null draw prints empty.

    The API answers 200 with "draw": null (plus an error payload) for a draw
    number that does not exist, instead of a 404. The report path must treat
    this like any other absent draw and print an empty report rather than
    crash with a traceback.
    """
    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/4971",
        timeout=30,
    ).and_return(mock_response({"draw": None, "error": {"code": 404}}))

    exit_code = main(["--start-draw", "4971", "--end-draw", "4999"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.strip() == "eligible: 0, excluded: 0"
    assert "Traceback" not in captured.err


def test_start_draw_without_end_draw_defaults_to_most_recent_draw(  # noqa: PLR0915
    mock_response, monkeypatch, capsys
):
    """--start-draw 4881 (no --end-draw) runs up to the most recent draw before today.

    With "today" pinned to 2025-01-20, the defaulted end resolves to draw 4884
    (the latest datepicker entry on or before that date; the Feb 1 entry 4886 is
    after it). The report aggregates draws 4881-4884 exactly like an explicit
    --end-draw 4884, and no draw outside that range is fetched.
    """

    class _FakeDate(date):
        @classmethod
        def today(cls):
            return date(2025, 1, 20)

    draw_url = "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/{n}"
    for draw_number in (4881, 4882, 4883, 4884):
        draw_data: dict[str, Any] = json.loads(
            (_FIXTURES / f"week_{draw_number}.json").read_text()
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
            (_FIXTURES / f"datepicker_{year}_{month:02d}.json").read_text()
        )
        flexmock(requests).should_receive("get").with_args(
            datepicker_url.format(year=year, month=month), timeout=30
        ).and_return(mock_response(datepicker_data))

    # No draw outside the range may be fetched, on either side of the boundary.
    for out_of_range in (4880, 4885, 4886):
        flexmock(requests).should_receive("get").with_args(
            draw_url.format(n=out_of_range), timeout=30
        ).never()

    monkeypatch.setattr(stryktips_core, "date", _FakeDate)
    exit_code = main(["--start-draw", "4881"])
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


def test_start_draw_after_most_recent_draw_prints_empty_report(  # noqa: PLR0915
    mock_response, monkeypatch, capsys
):
    """--start-draw 4900 (no --end-draw) after the latest draw prints an empty report.

    With "today" pinned to 2025-01-20, the defaulted end resolves to draw 4884
    (the latest datepicker entry on or before that date). The start 4900 is
    after that most recent draw, so the report is empty (exit 0) and the anchor
    draw 4900 is never fetched.
    """

    class _FakeDate(date):
        @classmethod
        def today(cls):
            return date(2025, 1, 20)

    draw_url = "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/{n}"
    flexmock(requests).should_receive("get").with_args(
        draw_url.format(n=4900), timeout=30
    ).never()

    datepicker_url = (
        "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
        "?product=stryktipset&year={year}&month={month}"
    )
    for year, month in ((2024, 12), (2025, 1)):
        datepicker_data: dict[str, Any] = json.loads(
            (_FIXTURES / f"datepicker_{year}_{month:02d}.json").read_text()
        )
        flexmock(requests).should_receive("get").with_args(
            datepicker_url.format(year=year, month=month), timeout=30
        ).and_return(mock_response(datepicker_data))

    monkeypatch.setattr(stryktips_core, "date", _FakeDate)
    exit_code = main(["--start-draw", "4900"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.strip() == "eligible: 0, excluded: 0"


def test_start_date_resolves_to_draw(mock_response, capsys):  # noqa: PLR0915
    """--start-date 2025-05-10 --end-draw 4900 reuses the date resolver."""
    datepicker_data = json.loads((_FIXTURES / "datepicker_2025_05.json").read_text())
    draw_data: dict[str, Any] = json.loads((_FIXTURES / "week_4900.json").read_text())

    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
        "?product=stryktipset&year=2025&month=5",
        timeout=30,
    ).and_return(mock_response(datepicker_data))

    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/4900",
        timeout=30,
    ).and_return(mock_response(draw_data))

    exit_code = main(["--start-date", "2025-05-10", "--end-draw", "4900"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
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


@pytest.mark.parametrize("end_date", ["2025-05-10", "2025-05-11"])
def test_end_date_resolves_to_draw(mock_response, monkeypatch, capsys, end_date):  # noqa: PLR0915
    """--start-draw 4900 --end-date resolves to the latest draw on or before the bound.

    With "today" pinned to 2025-06-01, both an exact-date bound (2025-05-10) and
    a non-draw bound (2025-05-11) resolve to draw 4900. The later draw 4901 is
    excluded, and the bound month (May) is scanned without a today-month (June)
    lookup.
    """

    class _FakeDate(date):
        @classmethod
        def today(cls):
            return date(2025, 6, 1)

    datepicker_data = json.loads((_FIXTURES / "datepicker_2025_05.json").read_text())
    draw_data: dict[str, Any] = json.loads((_FIXTURES / "week_4900.json").read_text())

    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
        "?product=stryktipset&year=2025&month=5",
        timeout=30,
    ).and_return(mock_response(datepicker_data))

    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/4900",
        timeout=30,
    ).and_return(mock_response(draw_data))

    # The draw after the bound and the today-month datepicker are never fetched.
    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/4901",
        timeout=30,
    ).never()
    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
        "?product=stryktipset&year=2025&month=6",
        timeout=30,
    ).never()

    monkeypatch.setattr(stryktips_core, "date", _FakeDate)
    exit_code = main(["--start-draw", "4900", "--end-date", end_date])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
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


def test_start_week_resolves_to_draw(mock_response, capsys):  # noqa: PLR0915
    """--start-week 2025.19 --end-draw 4900 reuses the week resolver."""
    datepicker_data = json.loads((_FIXTURES / "datepicker_2025_05.json").read_text())
    draw_data: dict[str, Any] = json.loads((_FIXTURES / "week_4900.json").read_text())

    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
        "?product=stryktipset&year=2025&month=5",
        timeout=30,
    ).and_return(mock_response(datepicker_data))

    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/4900",
        timeout=30,
    ).and_return(mock_response(draw_data))

    exit_code = main(["--start-week", "2025.19", "--end-draw", "4900"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
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


@pytest.mark.parametrize("end_week", ["2024.52", "2024.52.1", "2024.52.2"])
def test_end_week_resolves_to_draw(  # noqa: PLR0915
    mock_response, monkeypatch, capsys, end_week
):
    """A historical end week includes both Draws unless index .1 is explicit.

    Draws 4880 (December 26) and 4881 (December 29) are in ISO week 2024.52.
    The 4880 fixture is trimmed from the API response, retaining all 13 matches.
    With today pinned to January 20, only the historical month is needed.
    """

    class _FakeDate(date):
        @classmethod
        def today(cls):
            return date(2025, 1, 20)

    monkeypatch.setattr(stryktips_core, "date", _FakeDate)
    first_only = end_week == "2024.52.1"
    included_draws = (4880,) if first_only else (4880, 4881)
    excluded_draws = (4879, 4881, 4882) if first_only else (4879, 4882)
    draw_url = "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/{n}"
    for draw_number in included_draws:
        draw_data = json.loads((_FIXTURES / f"week_{draw_number}.json").read_text())
        flexmock(requests).should_receive("get").with_args(
            draw_url.format(n=draw_number), timeout=30
        ).and_return(mock_response(draw_data))
    for draw_number in excluded_draws:
        flexmock(requests).should_receive("get").with_args(
            draw_url.format(n=draw_number), timeout=30
        ).never()

    datepicker_data = json.loads((_FIXTURES / "datepicker_2024_12.json").read_text())

    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
        "?product=stryktipset&year=2024&month=12",
        timeout=30,
    ).and_return(mock_response(datepicker_data))
    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
        "?product=stryktipset&year=2025&month=1",
        timeout=30,
    ).never()
    expected_lines = (
        [
            "eligible: 13, excluded: 0",
            "0-10: 2 | 7% | 0% | -7%",
            "10-20: 1 | 15% | 100% | 85%",
            "20-30: 18 | 26% | 22% | -4%",
            "30-40: 8 | 35% | 38% | 3%",
            "40-50: 6 | 43% | 50% | 7%",
            "50-60: 2 | 54% | 50% | -4%",
            "60-70: 1 | 65% | 0% | -65%",
            "80-90: 1 | 86% | 100% | 14%",
        ]
        if first_only
        else [
            "eligible: 26, excluded: 0",
            "0-10: 2 | 7% | 0% | -7%",
            "10-20: 7 | 16% | 29% | 13%",
            "20-30: 34 | 26% | 26% | 0%",
            "30-40: 14 | 34% | 29% | -5%",
            "40-50: 10 | 43% | 40% | -3%",
            "50-60: 5 | 53% | 60% | 7%",
            "60-70: 5 | 64% | 60% | -4%",
            "80-90: 1 | 86% | 100% | 14%",
        ]
    )

    exit_code = main(["--start-draw", "4880", "--end-week", end_week])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    assert captured.out.splitlines() == expected_lines


def test_unindexed_drawless_end_week_resolves_to_latest_preceding_draw(  # noqa: PLR0915
    mock_response, monkeypatch, capsys
):
    """Historical week 2025.20 (May 12–18) ends at Draw 4900 without a warning.

    The synthetic May datepicker omits Draw 4901, leaving the week empty.
    Draw 4900 (May 10) is the latest preceding Draw; 4902 (May 25) is next.
    Both are in the bound month, so no multi-month backward search is needed.
    """

    class _FakeDate(date):
        @classmethod
        def today(cls):
            return date(2025, 6, 1)

    monkeypatch.setattr(stryktips_core, "date", _FakeDate)
    datepicker_data = json.loads((_FIXTURES / "datepicker_2025_05.json").read_text())
    datepicker_data["resultDates"] = [
        entry for entry in datepicker_data["resultDates"] if entry["drawNumber"] != 4901
    ]
    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
        "?product=stryktipset&year=2025&month=5",
        timeout=30,
    ).and_return(mock_response(datepicker_data))
    draw_url = "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/{n}"
    draw_data = json.loads((_FIXTURES / "week_4900.json").read_text())
    flexmock(requests).should_receive("get").with_args(
        draw_url.format(n=4900), timeout=30
    ).and_return(mock_response(draw_data))
    for draw_number in (4899, 4901, 4902, 4903):
        flexmock(requests).should_receive("get").with_args(
            draw_url.format(n=draw_number), timeout=30
        ).never()
    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
        "?product=stryktipset&year=2025&month=6",
        timeout=30,
    ).never()

    exit_code = main(["--start-draw", "4900", "--end-week", "2025.20"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    assert captured.out.splitlines() == [
        "eligible: 13, excluded: 0",
        "0-10: 1 | 8% | 0% | -8%",
        "10-20: 4 | 17% | 25% | 8%",
        "20-30: 15 | 25% | 33% | 8%",
        "30-40: 10 | 36% | 30% | -6%",
        "40-50: 3 | 42% | 33% | -9%",
        "50-60: 5 | 56% | 60% | 4%",
        "70-80: 1 | 79% | 0% | -79%",
    ]


def test_mixed_start_date_end_week_aggregates(mock_response, capsys):  # noqa: PLR0915
    """--start-date 2025-01-04 --end-week 2025.02 mixes formats and aggregates.

    The start date resolves to draw 4882 (dated 2025-01-04) and the end week
    resolves to draw 4883 (dated 2025-01-11, inside ISO week 2025.02). Both
    resolutions are exact matches, so no fallback note is printed. The report
    folds draws 4882 + 4883 into a single aggregate and fetches nothing outside
    the range.
    """
    draw_url = "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/{n}"
    for draw_number in (4882, 4883):
        draw_data: dict[str, Any] = json.loads(
            (_FIXTURES / f"week_{draw_number}.json").read_text()
        )
        flexmock(requests).should_receive("get").with_args(
            draw_url.format(n=draw_number), timeout=30
        ).and_return(mock_response(draw_data))

    datepicker_url = (
        "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
        "?product=stryktipset&year={year}&month={month}"
    )
    datepicker_data: dict[str, Any] = json.loads(
        (_FIXTURES / "datepicker_2025_01.json").read_text()
    )
    flexmock(requests).should_receive("get").with_args(
        datepicker_url.format(year=2025, month=1), timeout=30
    ).and_return(mock_response(datepicker_data))

    # No draw outside [4882, 4883] may be fetched, on either side of the range.
    for out_of_range in (4881, 4884, 4885):
        flexmock(requests).should_receive("get").with_args(
            draw_url.format(n=out_of_range), timeout=30
        ).never()

    exit_code = main(["--start-date", "2025-01-04", "--end-week", "2025.02"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    lines = captured.out.strip().split("\n")
    assert "eligible: 21, excluded: 0" in lines[0]
    assert lines[1:] == [
        "0-10: 1 | 8% | 100% | 92%",
        "10-20: 13 | 15% | 0% | -15%",
        "20-30: 24 | 25% | 38% | 13%",
        "30-40: 5 | 33% | 40% | 7%",
        "40-50: 6 | 44% | 50% | 6%",
        "50-60: 8 | 56% | 25% | -31%",
        "60-70: 3 | 65% | 67% | 2%",
        "70-80: 3 | 74% | 67% | -7%",
    ]


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


@pytest.mark.parametrize(
    "start_args",
    [
        ["--start-date", "2025-05-10"],
        ["--start-week", "2025.19"],
    ],
)
def test_resolved_start_after_end_errors(  # noqa: PLR0915
    mock_response, capsys, start_args
):
    """A date/week start resolving after the end errors (exit 1), no draws fetched.

    Both --start-date 2025-05-10 and --start-week 2025.19 resolve to draw 4900,
    which is later than --end-draw 4884. The bounds must resolve via the
    datepicker only; no draw may be fetched before the runtime error is raised.
    """
    datepicker_data = json.loads((_FIXTURES / "datepicker_2025_05.json").read_text())
    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
        "?product=stryktipset&year=2025&month=5",
        timeout=30,
    ).and_return(mock_response(datepicker_data))

    draw_url = "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/{n}"
    for draw_number in (4884, 4900):
        flexmock(requests).should_receive("get").with_args(
            draw_url.format(n=draw_number), timeout=30
        ).never()

    exit_code = main([*start_args, "--end-draw", "4884"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "must not be greater than" in captured.err
    assert "4900" in captured.err
    assert "4884" in captured.err


def test_start_date_forward_scans_across_empty_months(  # noqa: PLR0915
    mock_response, capsys
):
    """--start-date 2020-04-01 --end-draw 4642 forward-scans empty months.

    April and May 2020 have no draws, so the date resolver forward-scans to
    June, resolving draw 4642 (dated 2020-06-20). A fallback note is printed on
    stderr and the report aggregates the single resolved draw, fetching nothing
    after the resolved end.
    """
    empty_data: dict[str, list[Any]] = {"resultDates": []}
    datepicker_url = (
        "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
        "?product=stryktipset&year={year}&month={month}"
    )
    for year, month in ((2020, 4), (2020, 5)):
        flexmock(requests).should_receive("get").with_args(
            datepicker_url.format(year=year, month=month), timeout=30
        ).and_return(mock_response(empty_data))

    june_data = json.loads((_FIXTURES / "datepicker_2020_06.json").read_text())
    flexmock(requests).should_receive("get").with_args(
        datepicker_url.format(year=2020, month=6), timeout=30
    ).and_return(mock_response(june_data))

    draw_url = "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/{n}"
    draw_data: dict[str, Any] = json.loads((_FIXTURES / "week_4642.json").read_text())
    flexmock(requests).should_receive("get").with_args(
        draw_url.format(n=4642), timeout=30
    ).and_return(mock_response(draw_data))

    # No draw after the resolved end may be fetched.
    for out_of_range in (4643, 4644):
        flexmock(requests).should_receive("get").with_args(
            draw_url.format(n=out_of_range), timeout=30
        ).never()

    exit_code = main(["--start-date", "2020-04-01", "--end-draw", "4642"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (
        "Note: No draw found for 2020-04-01, using 2020-06-20 (draw 4642)"
        in captured.err
    )
    lines = captured.out.strip().split("\n")
    assert lines == ["eligible: 0, excluded: 13"]
