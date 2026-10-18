"""End-to-end collection tests for the prediction-quality report CLI.

These tests mock at the requests boundary so the concrete API adapter and
parser run for real against JSON fixtures.
"""

from datetime import date
from typing import Any

import requests
from flexmock import flexmock

from stryktips import main
from tests.e2e.report_support import (
    DATEPICKER_URL,
    DRAW_URL,
    DRAWS_4881_TO_4884_REPORT,
    inject_clock,
    load_fixture,
)


def test_start_draw_end_draw_4900_reports_buckets(mock_response, capsys):  # noqa: PLR0915
    """--start-draw 4900 --end-draw 4900 prints the bucket report for draw 4900."""
    inject_clock(date(2025, 5, 20))
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=5), timeout=30
    ).and_return(mock_response(load_fixture("datepicker_2025_05.json")))
    flexmock(requests).should_receive("get").with_args(
        DRAW_URL.format(n=4900), timeout=30
    ).and_return(mock_response(load_fixture("draw_4900.json")))

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
    inject_clock(date(2020, 6, 20))
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2020, month=6), timeout=30
    ).and_return(mock_response(load_fixture("datepicker_2020_06.json")))
    flexmock(requests).should_receive("get").with_args(
        DRAW_URL.format(n=4642), timeout=30
    ).and_return(mock_response(load_fixture("draw_4642.json")))

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
    inject_clock(date(2025, 1, 20))
    for draw_number in (4881, 4882, 4883, 4884):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=draw_number), timeout=30
        ).and_return(mock_response(load_fixture(f"draw_{draw_number}.json")))

    for year, month in ((2024, 12), (2025, 1)):
        flexmock(requests).should_receive("get").with_args(
            DATEPICKER_URL.format(year=year, month=month), timeout=30
        ).and_return(mock_response(load_fixture(f"datepicker_{year}_{month:02d}.json")))

    # No draw outside the range may be fetched, on either side of the boundary.
    for out_of_range in (4880, 4885, 4886):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=out_of_range), timeout=30
        ).never()

    exit_code = main(["--start-draw", "4881", "--end-draw", "4884"])
    captured = capsys.readouterr()

    assert exit_code == 0
    lines = captured.out.strip().split("\n")
    assert "eligible: 47, excluded: 0" in lines[0]
    assert len(lines) == 9
    assert lines[1:] == DRAWS_4881_TO_4884_REPORT[1:]


def test_start_draw_end_draw_walks_datepicker_across_drawless_months(  # noqa: PLR0915
    mock_response, capsys
):
    """--start-draw 4641 --end-draw 4642 walks across the Apr/May 2020 gap.

    Draw 4641 (Mar 2020) and draw 4642 (Jun 2020) straddle April and May 2020,
    which have no draws and so return 404 from the datepicker. The walk must query
    every month in between and collect only the draws in [4641, 4642], fetching
    nothing outside that range.
    """
    inject_clock(date(2020, 6, 20))
    for draw_number in (4641, 4642):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=draw_number), timeout=30
        ).and_return(mock_response(load_fixture(f"draw_{draw_number}.json")))

    # Months with draws return 200; the drawless Apr/May 2020 months return 404.
    for year, month in ((2020, 3), (2020, 6)):
        flexmock(requests).should_receive("get").with_args(
            DATEPICKER_URL.format(year=year, month=month), timeout=30
        ).at_least().once().and_return(
            mock_response(load_fixture(f"datepicker_{year}_{month:02d}.json"))
        )
    for year, month in ((2020, 4), (2020, 5)):
        flexmock(requests).should_receive("get").with_args(
            DATEPICKER_URL.format(year=year, month=month), timeout=30
        ).once().and_return(mock_response({"error": "not_found"}, status_code=404))

    # No draw outside [4641, 4642] may be fetched, on either side of the gap.
    for out_of_range in (4639, 4640, 4643, 4644):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=out_of_range), timeout=30
        ).never()

    exit_code = main(["--start-draw", "4641", "--end-draw", "4642"])
    captured = capsys.readouterr()

    assert exit_code == 0
    lines = captured.out.strip().split("\n")
    assert lines == ["eligible: 0, excluded: 20"]


def test_start_draw_end_draw_spanning_25_months_aggregates_every_draw(  # noqa: PLR0915
    mock_response, capsys
):
    """Collect all 25 months, including draws beyond the current traversal cap."""
    inject_clock(date(2025, 1, 20))
    draws = (
        (4881, "2023-01-07", ("3", "3", "3"), ("1", "0")),
        (4882, "2024-02-03", ("2", "4", "4"), ("1", "0")),
        (4883, "2025-01-04", ("10", "10", "1,25"), ("0", "1")),
    )
    for draw_number, draw_date, odds, score in draws:
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=draw_number), timeout=30
        ).once().and_return(
            mock_response(_two_played_events_draw(draw_number, draw_date, odds, score))
        )

    for month_offset in range(25):
        year, month_index = divmod(month_offset, 12)
        year += 2023
        month = month_index + 1
        result_dates = [
            {"date": f"{draw_date}T00:00:00+01:00", "drawNumber": draw_number}
            for draw_number, draw_date, _, _ in draws
            if draw_date.startswith(f"{year}-{month:02d}-")
        ]
        expectation = (
            flexmock(requests)
            .should_receive("get")
            .with_args(DATEPICKER_URL.format(year=year, month=month), timeout=30)
        )
        # January 2025 also serves the latest-available endpoint lookup (#80).
        if (year, month) == (2025, 1):
            expectation = expectation.at_least()
        expectation.once().and_return(mock_response({"resultDates": result_dates}))
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=2), timeout=30
    ).never()

    exit_code = main(["--start-draw", "4881", "--end-draw", "4883"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    assert captured.out.splitlines() == [
        "eligible: 3, excluded: 3",
        "10-20: 2 | 10% | 0% | -10%",
        "20-30: 2 | 25% | 0% | -25%",
        "30-40: 3 | 33% | 33% | 0%",
        "50-60: 1 | 50% | 100% | 50%",
        "80-90: 1 | 80% | 100% | 20%",
    ]


def _two_played_events_draw(
    draw_number: int,
    draw_date: str,
    odds: tuple[str, str, str],
    score: tuple[str, str],
) -> dict[str, Any]:
    data = load_fixture(f"draw_{draw_number}.json")
    draw = data["draw"]
    draw["drawNumber"] = draw_number
    draw["regCloseTime"] = f"{draw_date}T15:59:00+01:00"
    draw["drawEvents"] = draw["drawEvents"][:2]
    for event in draw["drawEvents"]:
        event["match"]["result"] = [
            {
                "type": 2,
                "sportEventResultType": "Fulltime",
                "home": score[0],
                "away": score[1],
            }
        ]
    draw["drawEvents"][0]["startOdds"] = dict(
        zip(("one", "x", "two"), odds, strict=True)
    )
    draw["drawEvents"][1]["startOdds"] = None
    return data


def test_start_draw_end_draw_skips_absent_draw_number(mock_response, capsys):  # noqa: PLR0915
    """--start-draw 4882 --end-draw 4884 skips the draw missing from datepicker.

    Draw 4883 is a hole in the range: it appears in no datepicker month, so the walk
    must not collect or fetch it. Only 4882 and 4884 are aggregated into the report.
    """
    inject_clock(date(2025, 1, 20))
    for draw_number in (4882, 4884):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=draw_number), timeout=30
        ).and_return(mock_response(load_fixture(f"draw_{draw_number}.json")))

    # Synthetic Jan 2025 datepicker: 4883 is omitted entirely from the month's data.
    datepicker_data: dict[str, Any] = {
        "resultDates": [
            {"date": "2025-01-04T00:00:00+01:00", "drawNumber": 4882},
            {"date": "2025-01-18T00:00:00+01:00", "drawNumber": 4884},
        ]
    }
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=1), timeout=30
    ).at_least().once().and_return(mock_response(datepicker_data))

    # The absent interior draw must never be fetched.
    flexmock(requests).should_receive("get").with_args(
        DRAW_URL.format(n=4883), timeout=30
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
    inject_clock(date(2025, 1, 20))
    for draw_number in (4882, 4884):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=draw_number), timeout=30
        ).once().and_return(mock_response(load_fixture(f"draw_{draw_number}.json")))

    # The interior draw is present in the datepicker but its fetch returns 404.
    not_found = flexmock(status_code=404)
    not_found.should_receive("raise_for_status").and_raise(
        requests.HTTPError("404 Client Error")
    )
    flexmock(requests).should_receive("get").with_args(
        DRAW_URL.format(n=4883), timeout=30
    ).once().and_return(not_found)

    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=1), timeout=30
    ).at_least().once().and_return(
        mock_response(load_fixture("datepicker_2025_01.json"))
    )

    # No draw outside the range may be fetched, on either side of the range.
    for out_of_range in (4885, 4886):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=out_of_range), timeout=30
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


def test_start_draw_end_draw_empty_range_prints_empty_report(mock_response, capsys):
    """--start-draw/--end-draw with no collectible draw prints an empty report."""
    inject_clock(date(2025, 5, 20))
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=5), timeout=30
    ).and_return(mock_response(load_fixture("datepicker_2025_05.json")))
    not_found = flexmock(status_code=404)
    not_found.should_receive("raise_for_status").and_raise(
        requests.HTTPError("404 Client Error")
    )
    flexmock(requests).should_receive("get").with_args(
        DRAW_URL.format(n=4900), timeout=30
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
    crash with a traceback. The numeric end remains within the available data.
    """
    inject_clock(date(2025, 5, 20))
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=5), timeout=30
    ).and_return(mock_response(load_fixture("datepicker_2025_05.json")))
    flexmock(requests).should_receive("get").with_args(
        DRAW_URL.format(n=4900), timeout=30
    ).and_return(mock_response({"draw": None, "error": {"code": 404}}))

    exit_code = main(["--start-draw", "4900", "--end-draw", "4901"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.strip() == "eligible: 0, excluded: 0"
    assert "Traceback" not in captured.err
