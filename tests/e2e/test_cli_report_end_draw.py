"""End-to-end end-draw clamping through the real CLI and API adapter."""

from datetime import date

import requests
from flexmock import flexmock

from stryktips import main
from tests.e2e.report_support import (
    DATEPICKER_URL,
    DRAW_URL,
    inject_clock,
    load_fixture,
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
    assert captured.out.splitlines() == [
        "eligible: 47, excluded: 0",
        "0-10: 1 | 8% | 100% | 92%",
        "10-20: 24 | 16% | 8% | -8%",
        "20-30: 57 | 26% | 30% | 4%",
        "30-40: 19 | 35% | 37% | 2%",
        "40-50: 14 | 44% | 50% | 6%",
        "50-60: 14 | 55% | 36% | -19%",
        "60-70: 9 | 65% | 67% | 2%",
        "70-80: 3 | 74% | 67% | -7%",
    ]
