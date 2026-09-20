"""End-to-end start-week bound tests for the report CLI.

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
    DATEPICKER_URL,
    DRAW_URL,
    inject_clock,
    load_fixture,
)

# ISO week 2025.01 runs Mon 2024-12-30 to Sun 2025-01-05 and holds two distinct
# Draws: 4881 (2024-12-30) and 4882 (2025-01-04). No fixture contains two Draws
# in a cross-year week, so the December 2024 and January 2025 datepicker
# responses are synthetic, unsorted and overlapping: December 2024 lists only
# the later 4882, while January 2025 repeats 4882 and lists the earlier 4881
# twice. Both monthly responses must therefore be gathered before the start
# bound can be selected. The real draw_4881 Draw fixture is reused with its
# in-memory ``regCloseTime`` moved from 2024-12-29 to 2024-12-30 so it is dated
# inside the week.
_DECEMBER_2024_WEEK_2025_01: dict[str, Any] = {
    "resultDates": [
        {"date": "2025-01-04T00:00:00+01:00", "drawNumber": 4882},
    ]
}
_JANUARY_2025_WEEK_2025_01: dict[str, Any] = {
    "resultDates": [
        {"date": "2025-01-04T00:00:00+01:00", "drawNumber": 4882},
        {"date": "2024-12-30T00:00:00+01:00", "drawNumber": 4881},
        {"date": "2024-12-30T00:00:00+01:00", "drawNumber": 4881},
    ]
}

# The fixed --end-draw 4882 caps every variant, so the start index alone decides
# whether the report folds in the first draw 4881.
_FIRST_AND_SECOND_DRAW_REPORT = [
    "eligible: 26, excluded: 0",
    "10-20: 12 | 16% | 8% | -8%",
    "20-30: 33 | 25% | 33% | 8%",
    "30-40: 10 | 34% | 20% | -14%",
    "40-50: 8 | 43% | 50% | 7%",
    "50-60: 8 | 54% | 38% | -16%",
    "60-70: 5 | 63% | 60% | -3%",
    "70-80: 2 | 73% | 100% | 27%",
]
_SECOND_DRAW_ONLY_REPORT = [
    "eligible: 13, excluded: 0",
    "10-20: 6 | 15% | 0% | -15%",
    "20-30: 17 | 25% | 35% | 10%",
    "30-40: 4 | 34% | 25% | -9%",
    "40-50: 4 | 43% | 75% | 32%",
    "50-60: 5 | 55% | 20% | -35%",
    "60-70: 1 | 61% | 0% | -61%",
    "70-80: 2 | 73% | 100% | 27%",
]
_EXCESSIVE_START_WEEK_ERROR = (
    "Error: Week 2025.1 has 2 draws (dates: 2024-12-30, 2025-01-04). "
    "Use --week 2025.1.1 or --week 2025.1.2."
)


@pytest.mark.parametrize(
    ("start_week", "expected_draws", "expected_report", "expected_error"),
    [
        pytest.param(
            "2025.01",
            (4881, 4882),
            _FIRST_AND_SECOND_DRAW_REPORT,
            None,
            id="omitted-index-starts-first",
        ),
        pytest.param(
            "2025.01.1",
            (4881, 4882),
            _FIRST_AND_SECOND_DRAW_REPORT,
            None,
            id="first-index-starts-first",
        ),
        pytest.param(
            "2025.01.2",
            (4882,),
            _SECOND_DRAW_ONLY_REPORT,
            None,
            id="second-index-starts-second",
        ),
        pytest.param(
            "2025.01.3",
            (),
            None,
            _EXCESSIVE_START_WEEK_ERROR,
            id="excessive-index-rejected",
        ),
    ],
)
def test_start_week_2025_01_selects_report_start(  # noqa: PLR0913, PLR0915
    mock_response, capsys, start_week, expected_draws, expected_report, expected_error
):
    """A start week spanning a year boundary indexes distinct Draws chronologically.

    The start bound reuses the ``--week`` resolver over ISO week 2025.01, whose
    two Draws 4881 (2024-12-30) and 4882 (2025-01-04) are split across unsorted,
    overlapping monthly responses. Omitted ``.N`` and ``.1`` start the fixed
    ``--end-draw 4882`` report at 4881, folding both Draws into one aggregate;
    ``.2`` starts at 4882, excluding 4881 from the report; and the excessive
    ``.3`` exits 1 naming the two distinct Draws without fetching any Draw.
    Duplicate and overlapping entries must not advance the index, inflate the
    available count, or duplicate a Draw's report contribution. Today is pinned
    even though the fixed end bound never consults it.
    """
    inject_clock(date(2025, 3, 1))

    first_draw = load_fixture("draw_4881.json")
    first_draw["draw"]["regCloseTime"] = "2024-12-30T15:59:00+01:00"
    second_draw = load_fixture("draw_4882.json")

    for number, payload in {4881: first_draw, 4882: second_draw}.items():
        expectation = (
            flexmock(requests)
            .should_receive("get")
            .with_args(DRAW_URL.format(n=number), timeout=30)
        )
        if number in expected_draws:
            expectation.once().and_return(mock_response(payload))
        else:
            expectation.never()
    for out_of_range in (4879, 4880, 4883, 4884):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=out_of_range), timeout=30
        ).never()

    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2024, month=12), timeout=30
    ).at_least().once().and_return(mock_response(_DECEMBER_2024_WEEK_2025_01))
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=1), timeout=30
    ).at_least().once().and_return(mock_response(_JANUARY_2025_WEEK_2025_01))

    # Neither an unrelated month nor the today month (March 2025) may be looked up.
    for year, month in ((2024, 11), (2025, 2), (2025, 3)):
        flexmock(requests).should_receive("get").with_args(
            DATEPICKER_URL.format(year=year, month=month), timeout=30
        ).never()

    exit_code = main(["--start-week", start_week, "--end-draw", "4882"])
    captured = capsys.readouterr()

    if expected_error is None:
        assert exit_code == 0
        assert captured.err == ""
        assert captured.out.splitlines() == expected_report
    else:
        assert exit_code == 1
        assert captured.err.splitlines() == [expected_error]
        assert captured.out == ""
