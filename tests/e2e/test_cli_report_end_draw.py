"""End-to-end end-draw clamping through the real CLI and API adapter."""

from datetime import date

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
