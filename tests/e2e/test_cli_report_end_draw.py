"""End-to-end end-draw clamping through the real CLI and API adapter."""

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


def test_end_draw_below_latest_stops_spanning_report_inclusively(  # noqa: PLR0915
    mock_response, capsys
):
    """An explicit end at 4883 includes it but excludes eligible draw 4884."""
    inject_clock(date(2025, 1, 20))
    for draw_number in (4881, 4882, 4883):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=draw_number), timeout=30
        ).and_return(mock_response(load_fixture(f"draw_{draw_number}.json")))

    for year, month in ((2024, 12), (2025, 1)):
        flexmock(requests).should_receive("get").with_args(
            DATEPICKER_URL.format(year=year, month=month), timeout=30
        ).and_return(mock_response(load_fixture(f"datepicker_{year}_{month:02d}.json")))

    # Neither the latest eligible draw nor published future draws belong here.
    for out_of_range in (4884, 4885, 4886):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=out_of_range), timeout=30
        ).never()

    exit_code = main(["--start-draw", "4881", "--end-draw", "4883"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    # Fixture full-time results and normalized inverse start odds: 34 matches,
    # 102 outcome samples; deltas subtract the displayed rounded percentages.
    assert captured.out.splitlines() == [
        "eligible: 34, excluded: 0",
        "0-10: 1 | 8% | 100% | 92%",
        "10-20: 19 | 16% | 5% | -11%",
        "20-30: 40 | 25% | 35% | 10%",
        "30-40: 11 | 34% | 27% | -7%",
        "40-50: 10 | 43% | 40% | -3%",
        "50-60: 11 | 55% | 36% | -19%",
        "60-70: 7 | 64% | 71% | 7%",
        "70-80: 3 | 74% | 67% | -7%",
    ]


def test_missing_end_draw_below_latest_remains_numeric_upper_bound(  # noqa: PLR0915
    mock_response, capsys
):
    """A missing 4883 ends the short period before available draw 4884."""
    inject_clock(date(2025, 1, 20))
    flexmock(requests).should_receive("get").with_args(
        DRAW_URL.format(n=4882), timeout=30
    ).and_return(mock_response(load_fixture("draw_4882.json")))

    # Synthetic January: the requested end is absent, but a later draw exists.
    datepicker_data: dict[str, Any] = {
        "resultDates": [
            {"date": "2025-01-04T00:00:00+01:00", "drawNumber": 4882},
            {"date": "2025-01-18T00:00:00+01:00", "drawNumber": 4884},
        ]
    }
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=1), timeout=30
    ).at_least().once().and_return(mock_response(datepicker_data))

    for out_of_range in (4883, 4884):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=out_of_range), timeout=30
        ).never()

    # Seeing the first draw above the bound must stop the month walk here.
    # Any other unconfigured request also fails at the requests boundary.
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=2), timeout=30
    ).never()

    exit_code = main(["--start-draw", "4882", "--end-draw", "4883"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    # Independently calculated from fixture 4882's full-time scores and
    # normalized inverse start odds: 13 matches, 39 outcome samples.
    assert captured.out.splitlines() == [
        "eligible: 13, excluded: 0",
        "10-20: 6 | 15% | 0% | -15%",
        "20-30: 17 | 25% | 35% | 10%",
        "30-40: 4 | 34% | 25% | -9%",
        "40-50: 4 | 43% | 75% | 32%",
        "50-60: 5 | 55% | 20% | -35%",
        "60-70: 1 | 61% | 0% | -61%",
        "70-80: 2 | 73% | 100% | 27%",
    ]


def test_end_draw_clamped_below_start_errors_before_fetching_draws(
    mock_response, capsys
):
    """Valid raw bounds become an ordering error after the end clamps to 4884."""
    inject_clock(date(2025, 1, 20))
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=1), timeout=30
    ).at_least().once().and_return(
        mock_response(load_fixture("datepicker_2025_01.json"))
    )

    # No anchor, resolved end, published future draw, or requested end is fetched.
    # Any other unconfigured request also fails at the requests boundary.
    for draw_number in (4900, 4884, 4885, 4886, 4999):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=draw_number), timeout=30
        ).never()

    exit_code = main(["--start-draw", "4900", "--end-draw", "4999"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert captured.err == (
        "--start bound resolved to draw 4900, which must not be"
        " greater than --end bound (draw 4884)\n"
    )


def test_future_end_draw_clamps_to_latest_available_draw(  # noqa: PLR0915
    mock_response, capsys
):
    """A future numeric end silently aggregates through draw 4884 on January 20."""
    inject_clock(date(2025, 1, 20))
    for draw_number in (4881, 4882, 4883, 4884):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=draw_number), timeout=30
        ).and_return(mock_response(load_fixture(f"draw_{draw_number}.json")))

    for year, month in ((2024, 12), (2025, 1)):
        flexmock(requests).should_receive("get").with_args(
            DATEPICKER_URL.format(year=year, month=month), timeout=30
        ).and_return(mock_response(load_fixture(f"datepicker_{year}_{month:02d}.json")))

    # January's published draws after today must not enter the report.
    for future_draw in (4885, 4886):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=future_draw), timeout=30
        ).never()

    # Clamping to January's latest available draw must stop the month walk here.
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=2), timeout=30
    ).never()

    exit_code = main(["--start-draw", "4881", "--end-draw", "4999"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    assert captured.out.splitlines() == DRAWS_4881_TO_4884_REPORT
