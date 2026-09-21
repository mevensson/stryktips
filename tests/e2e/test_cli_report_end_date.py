"""End-to-end default and end-date bound tests for the report CLI.

Requests are mocked so the concrete API adapter and parser run for real against
JSON fixtures. The clock is fixed through the public ``create_dependencies``
composition seam instead of patching ``date``.
"""

from datetime import date
from typing import Any

import pytest
import requests
from flexmock import flexmock

from stryktips import main
from tests.e2e.report_support import (
    BACKWARD_MONTHS_FROM_MAY_2025,
    DATEPICKER_URL,
    DRAW_URL,
    inject_clock,
    load_fixture,
)


def test_start_draw_without_end_draw_defaults_to_most_recent_draw(  # noqa: PLR0915
    mock_response, capsys
):
    """--start-draw 4881 (no --end-draw) runs up to the most recent draw before today.

    With "today" pinned to 2025-01-20, the defaulted end resolves to draw 4884
    (the latest datepicker entry on or before that date; the Feb 1 entry 4886 is
    after it). The report aggregates draws 4881-4884 exactly like an explicit
    --end-draw 4884, and no draw outside that range is fetched.
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
    mock_response, capsys
):
    """--start-draw 4900 (no --end-draw) after the latest draw prints an empty report.

    With "today" pinned to 2025-01-20, the defaulted end resolves to draw 4884
    (the latest datepicker entry on or before that date). The start 4900 is
    after that most recent draw, so the report is empty (exit 0) and the anchor
    draw 4900 is never fetched.
    """
    inject_clock(date(2025, 1, 20))
    flexmock(requests).should_receive("get").with_args(
        DRAW_URL.format(n=4900), timeout=30
    ).never()

    for year, month in ((2024, 12), (2025, 1)):
        flexmock(requests).should_receive("get").with_args(
            DATEPICKER_URL.format(year=year, month=month), timeout=30
        ).and_return(mock_response(load_fixture(f"datepicker_{year}_{month:02d}.json")))

    exit_code = main(["--start-draw", "4900"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.strip() == "eligible: 0, excluded: 0"


def test_start_date_resolves_to_draw(mock_response, capsys):  # noqa: PLR0915
    """--start-date 2025-05-10 --end-draw 4900 reuses the date resolver."""
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=5), timeout=30
    ).and_return(mock_response(load_fixture("datepicker_2025_05.json")))

    flexmock(requests).should_receive("get").with_args(
        DRAW_URL.format(n=4900), timeout=30
    ).and_return(mock_response(load_fixture("draw_4900.json")))

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
def test_end_date_resolves_to_draw(mock_response, capsys, end_date):  # noqa: PLR0915
    """--start-draw 4900 --end-date resolves to the latest draw on or before the bound.

    With "today" pinned to 2025-06-01, both an exact-date bound (2025-05-10) and
    a non-draw bound (2025-05-11) resolve to draw 4900. The later draw 4901 is
    excluded, and the bound month (May) is scanned without a today-month (June)
    lookup.
    """
    inject_clock(date(2025, 6, 1))
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=5), timeout=30
    ).and_return(mock_response(load_fixture("datepicker_2025_05.json")))

    flexmock(requests).should_receive("get").with_args(
        DRAW_URL.format(n=4900), timeout=30
    ).and_return(mock_response(load_fixture("draw_4900.json")))

    # The draw after the bound and the today-month datepicker are never fetched.
    flexmock(requests).should_receive("get").with_args(
        DRAW_URL.format(n=4901), timeout=30
    ).never()
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=6), timeout=30
    ).never()

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


def test_future_end_date_clamps_to_today(mock_response, capsys):  # noqa: PLR0915
    """--start-draw 4900 --end-date 2025-06-01 clamps a future bound to today.

    With "today" pinned to 2025-05-10, the June bound is capped at today and
    resolves to draw 4900, the draw dated exactly today. The later draws already
    published in the May datepicker (4901, 4902, 4903) are excluded, and the
    future bound month (June) is never looked up.
    """
    inject_clock(date(2025, 5, 10))
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=5), timeout=30
    ).and_return(mock_response(load_fixture("datepicker_2025_05.json")))

    flexmock(requests).should_receive("get").with_args(
        DRAW_URL.format(n=4900), timeout=30
    ).and_return(mock_response(load_fixture("draw_4900.json")))

    # The later published draws and the future (June) bound month are never fetched.
    for later_draw in (4901, 4902, 4903):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=later_draw), timeout=30
        ).never()
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=6), timeout=30
    ).never()

    exit_code = main(["--start-draw", "4900", "--end-date", "2025-06-01"])
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
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=5), timeout=30
    ).and_return(mock_response(load_fixture("datepicker_2025_05.json")))

    flexmock(requests).should_receive("get").with_args(
        DRAW_URL.format(n=4900), timeout=30
    ).and_return(mock_response(load_fixture("draw_4900.json")))

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


def test_historical_end_date_searches_back_across_empty_months(  # noqa: PLR0915
    mock_response, capsys
):
    """A May 2020 date end resolves back to Draw 4641.

    With today pinned to 2020-06-01, --end-date 2020-05-15 bounds the report in
    May 2020. May returns an empty 200, April 2020 returns 404, and March 2020
    holds the latest preceding Draw 4641 (2020-03-14). The backward search must
    query the bound and intervening months in order, never the today month
    (June), and fetch only Draw 4641.
    """
    inject_clock(date(2020, 6, 1))

    empty_data: dict[str, list[Any]] = {"resultDates": []}
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2020, month=5), timeout=30
    ).once().ordered().and_return(mock_response(empty_data))
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2020, month=4), timeout=30
    ).once().ordered().and_return(
        mock_response({"error": "not_found"}, status_code=404)
    )
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2020, month=3), timeout=30
    ).once().ordered().and_return(
        mock_response(load_fixture("datepicker_2020_03.json"))
    )

    flexmock(requests).should_receive("get").with_args(
        DRAW_URL.format(n=4641), timeout=30
    ).once().and_return(mock_response(load_fixture("draw_4641.json")))

    # Neither the today month nor any Draw outside the resolved end is fetched.
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2020, month=6), timeout=30
    ).never()
    for draw_number in (4639, 4640, 4642, 4643, 4644):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=draw_number), timeout=30
        ).never()

    exit_code = main(["--start-draw", "4641", "--end-date", "2020-05-15"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    assert captured.out.splitlines() == ["eligible: 0, excluded: 7"]


def test_end_date_without_preceding_draw_errors_after_backward_window(  # noqa: PLR0915
    mock_response, capsys
):
    """A date end with no predecessor fails within the 12-month window.

    With "today" pinned to 2025-06-01, --end-date 2025-05-15 searches the bound
    month and 11 earlier months (May 2025 back to June 2024) across the year
    boundary. Every month is empty or absent, so resolution fails within 12
    months rather than reaching the 13th older month (May 2024) or the today
    month (June 2025). Exit is 1 with a bounded-search message on stderr, no
    fallback warning, empty stdout, and no report Draw fetch.
    """
    inject_clock(date(2025, 6, 1))
    for year, month in BACKWARD_MONTHS_FROM_MAY_2025:
        if (year, month) == (2025, 5):
            payload: dict[str, Any] = {"resultDates": []}
            status_code = 200
        else:
            payload = {"error": "not_found"}
            status_code = 404
        flexmock(requests).should_receive("get").with_args(
            DATEPICKER_URL.format(year=year, month=month), timeout=30
        ).once().ordered().and_return(mock_response(payload, status_code=status_code))

    # The 13th older month and the today month are never looked up.
    for year, month in ((2024, 5), (2025, 6)):
        flexmock(requests).should_receive("get").with_args(
            DATEPICKER_URL.format(year=year, month=month), timeout=30
        ).never()

    # No report Draw may be fetched when the end bound fails to resolve.
    flexmock(requests).should_receive("get").with_args(
        DRAW_URL.format(n=4884), timeout=30
    ).never()

    exit_code = main(["--start-draw", "4884", "--end-date", "2025-05-15"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "No draw found within 12 months of 2025-05-15" in captured.err
    assert "Warning" not in captured.err
    assert captured.out == ""


_UNFETCHED_REPORT_DRAWS = (4884, 4899, 4900, 4901, 4902, 4903)


@pytest.mark.parametrize(
    (
        "clock",
        "start_args",
        "end_args",
        "expected_start",
        "expected_end",
        "ends_empty_week",
    ),
    [
        pytest.param(
            date(2025, 6, 1),
            ["--start-date", "2025-05-10"],
            ["--end-draw", "4884"],
            4900,
            4884,
            False,
            id="start-date-before-draw-end",
        ),
        pytest.param(
            date(2025, 6, 1),
            ["--start-week", "2025.19"],
            ["--end-draw", "4884"],
            4900,
            4884,
            False,
            id="start-week-before-draw-end",
        ),
        pytest.param(
            date(2025, 6, 1),
            ["--start-draw", "4901"],
            ["--end-date", "2025-05-11"],
            4901,
            4900,
            False,
            id="date-end-falls-back-to-previous-draw",
        ),
        pytest.param(
            date(2025, 6, 1),
            ["--start-draw", "4902"],
            ["--end-week", "2025.20"],
            4902,
            4900,
            True,
            id="unindexed-empty-week-falls-back",
        ),
        pytest.param(
            date(2025, 5, 10),
            ["--start-draw", "4902"],
            ["--end-date", "2025-06-01"],
            4902,
            4900,
            False,
            id="future-date-end-clamps-to-today",
        ),
        pytest.param(
            date(2025, 5, 10),
            ["--start-draw", "4902"],
            ["--end-week", "2025.23"],
            4902,
            4900,
            False,
            id="future-week-end-clamps-to-today",
        ),
        pytest.param(
            date(2025, 6, 1),
            ["--start-draw", "4902"],
            ["--end-week", "2025.20.1"],
            4902,
            4900,
            True,
            id="indexed-empty-week-warns-then-errors",
        ),
    ],
)
def test_resolved_start_after_end_errors(  # noqa: PLR0913, PLR0915
    mock_response,
    capsys,
    clock,
    start_args,
    end_args,
    expected_start,
    expected_end,
    ends_empty_week,
):
    """A resolved start after a resolved explicit end errors (exit 1), no draws fetched.

    Both start selectors (--start-date 2025-05-10, --start-week 2025.19) resolve
    to draw 4900, later than --end-draw 4884. Explicit date and week ends are
    covered too: a non-draw date falls back to previous draw 4900, and a
    historical week whose synthetic datepicker drops draw 4901 falls back to
    4900. A future date or week end clamps to the pinned today, and an indexed
    end week that has completed but holds no draws warns before the ordering
    error. Every bound resolves against real datepicker fixtures (no resolver
    mocks), the clock is pinned through the composition seam, and no report draw
    is fetched because ordering fails before collection.
    """
    inject_clock(clock)

    datepicker_data = load_fixture("datepicker_2025_05.json")
    if ends_empty_week:
        datepicker_data["resultDates"] = [
            entry
            for entry in datepicker_data["resultDates"]
            if entry["drawNumber"] != 4901
        ]
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=5), timeout=30
    ).and_return(mock_response(datepicker_data))

    # The today month (June) is never looked up, even for a future bound.
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=6), timeout=30
    ).never()

    # No report Draw may be fetched before the ordering error is raised.
    for draw_number in _UNFETCHED_REPORT_DRAWS:
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=draw_number), timeout=30
        ).never()

    exit_code = main([*start_args, *end_args])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.err.splitlines()[-1] == (
        f"--start bound resolved to draw {expected_start}, which must not be"
        f" greater than --end bound (draw {expected_end})"
    )
    assert captured.out == ""


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
    for year, month in ((2020, 4), (2020, 5)):
        flexmock(requests).should_receive("get").with_args(
            DATEPICKER_URL.format(year=year, month=month), timeout=30
        ).and_return(mock_response(empty_data))

    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2020, month=6), timeout=30
    ).and_return(mock_response(load_fixture("datepicker_2020_06.json")))

    flexmock(requests).should_receive("get").with_args(
        DRAW_URL.format(n=4642), timeout=30
    ).and_return(mock_response(load_fixture("draw_4642.json")))

    # No draw after the resolved end may be fetched.
    for out_of_range in (4643, 4644):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=out_of_range), timeout=30
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
