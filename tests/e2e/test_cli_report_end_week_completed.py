"""End-to-end completed and cross-year end-week bound tests for the report CLI.

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

_CROSS_YEAR_FIRST_DRAW_REPORT = [
    "eligible: 13, excluded: 0",
    "10-20: 6 | 17% | 17% | 0%",
    "20-30: 16 | 26% | 31% | 5%",
    "30-40: 6 | 34% | 17% | -17%",
    "40-50: 4 | 43% | 25% | -18%",
    "50-60: 3 | 53% | 67% | 14%",
    "60-70: 4 | 64% | 75% | 11%",
]

_CROSS_YEAR_BOTH_DRAWS_REPORT = [
    "eligible: 26, excluded: 0",
    "10-20: 12 | 16% | 8% | -8%",
    "20-30: 33 | 25% | 33% | 8%",
    "30-40: 10 | 34% | 20% | -14%",
    "40-50: 8 | 43% | 50% | 7%",
    "50-60: 8 | 54% | 38% | -16%",
    "60-70: 5 | 63% | 60% | -3%",
    "70-80: 2 | 73% | 100% | 27%",
]

_DRAW_4881_ONLY_REPORT = [
    "eligible: 13, excluded: 0",
    "10-20: 6 | 17% | 17% | 0%",
    "20-30: 16 | 26% | 31% | 5%",
    "30-40: 6 | 34% | 17% | -17%",
    "40-50: 4 | 43% | 25% | -18%",
    "50-60: 3 | 53% | 67% | 14%",
    "60-70: 4 | 64% | 75% | 11%",
]

_FIRST_DRAW_AFTER_START_ERROR = (
    "--start bound resolved to draw 4881, which must not be"
    " greater than --end bound (draw 4880)"
)


@pytest.mark.parametrize("end_week", ["2024.52", "2024.52.1", "2024.52.2"])
def test_end_week_resolves_to_draw(mock_response, capsys, end_week):  # noqa: PLR0915
    """A historical end week includes both Draws unless index .1 is explicit.

    Draws 4880 (December 26) and 4881 (December 29) are in ISO week 2024.52.
    The 4880 fixture is trimmed from the API response, retaining all 13 matches.
    With today pinned to January 20, only the historical month is needed.
    """
    inject_clock(date(2025, 1, 20))
    first_only = end_week == "2024.52.1"
    included_draws = (4880,) if first_only else (4880, 4881)
    excluded_draws = (4879, 4881, 4882) if first_only else (4879, 4882)
    for draw_number in included_draws:
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=draw_number), timeout=30
        ).and_return(mock_response(load_fixture(f"draw_{draw_number}.json")))
    for draw_number in excluded_draws:
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=draw_number), timeout=30
        ).never()

    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2024, month=12), timeout=30
    ).and_return(mock_response(load_fixture("datepicker_2024_12.json")))
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=1), timeout=30
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
    mock_response, capsys
):
    """Historical week 2025.20 (May 12–18) ends at Draw 4900 without a warning.

    The synthetic May datepicker omits Draw 4901, leaving the week empty.
    Draw 4900 (May 10) is the latest preceding Draw; 4902 (May 25) is next.
    Both are in the bound month, so no multi-month backward search is needed.
    """
    inject_clock(date(2025, 6, 1))
    datepicker_data = load_fixture("datepicker_2025_05.json")
    datepicker_data["resultDates"] = [
        entry for entry in datepicker_data["resultDates"] if entry["drawNumber"] != 4901
    ]
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=5), timeout=30
    ).and_return(mock_response(datepicker_data))
    flexmock(requests).should_receive("get").with_args(
        DRAW_URL.format(n=4900), timeout=30
    ).and_return(mock_response(load_fixture("draw_4900.json")))
    for draw_number in (4899, 4901, 4902, 4903):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=draw_number), timeout=30
        ).never()
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=6), timeout=30
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


def test_indexed_empty_completed_end_week_resolves_to_preceding_draw(  # noqa: PLR0915
    mock_response, capsys
):
    """--end-week 2025.20.1 on an emptied completed week ends at Draw 4900.

    The synthetic May datepicker omits Draw 4901, leaving ISO week 2025.20
    (May 12-18) with no draws. Because the week has completed, the indexed end
    falls back to the latest preceding Draw 4900 (May 10), not the later 4902
    (May 25). A warning names the requested indexed week and the fallback draw
    and date. Both are in the bound month, so no multi-month backward search is
    needed.
    """
    inject_clock(date(2025, 6, 1))
    datepicker_data = load_fixture("datepicker_2025_05.json")
    datepicker_data["resultDates"] = [
        entry for entry in datepicker_data["resultDates"] if entry["drawNumber"] != 4901
    ]
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=5), timeout=30
    ).and_return(mock_response(datepicker_data))
    flexmock(requests).should_receive("get").with_args(
        DRAW_URL.format(n=4900), timeout=30
    ).and_return(mock_response(load_fixture("draw_4900.json")))
    for draw_number in (4899, 4901, 4902, 4903):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=draw_number), timeout=30
        ).never()
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=6), timeout=30
    ).never()

    exit_code = main(["--start-draw", "4900", "--end-week", "2025.20.1"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Warning" in captured.err
    assert "2025.20.1" in captured.err
    assert "4900" in captured.err
    assert "2025-05-10" in captured.err
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


def test_historical_end_week_searches_back_across_empty_months(  # noqa: PLR0915
    mock_response, capsys
):
    """A May 2020 unindexed-week end resolves back to Draw 4641.

    With today pinned to 2020-06-01, --end-week 2020.20 (Sunday 2020-05-17)
    bounds the report in May 2020. May returns an empty 200, April 2020 returns
    404, and March 2020 holds the latest preceding Draw 4641 (2020-03-14). The
    backward search must query the bound and intervening months in order, never
    the today month (June), and fetch only Draw 4641.
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

    exit_code = main(["--start-draw", "4641", "--end-week", "2020.20"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    assert captured.out.splitlines() == ["eligible: 0, excluded: 7"]


@pytest.mark.parametrize(
    ("end_args", "expected_months", "expected_error"),
    [
        (
            ["--end-week", "2025.20"],
            BACKWARD_MONTHS_FROM_MAY_2025,
            "No draw found within 12 months of 2025-05-18",
        ),
        (
            ["--end-week", "2025.20.1"],
            [(2025, 5), *BACKWARD_MONTHS_FROM_MAY_2025],
            "No draw found within 12 months of 2025-05-11",
        ),
    ],
)
def test_end_week_without_preceding_draw_errors_after_backward_window(  # noqa: PLR0915
    mock_response, capsys, end_args, expected_months, expected_error
):
    """An unindexed or indexed week end with no predecessor fails within the window.

    With "today" pinned to 2025-06-01, a May 2025 week bound searches the bound
    month and 11 earlier months (May 2025 back to June 2024) across the year
    boundary. Every month is empty or absent, so resolution fails within 12
    months rather than reaching the 13th older month (May 2024) or the today
    month (June 2025). The indexed empty completed-week bound first inspects the
    requested month and repeats it as the first month of the backward window.
    Exit is 1 with a bounded-search message on stderr, no fallback warning,
    empty stdout, and no report Draw fetch.
    """
    inject_clock(date(2025, 6, 1))
    for year, month in expected_months:
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

    exit_code = main(["--start-draw", "4884", *end_args])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert expected_error in captured.err
    assert "Warning" not in captured.err
    assert captured.out == ""


def test_mixed_start_date_end_week_aggregates(mock_response, capsys):  # noqa: PLR0915
    """--start-date 2025-01-04 --end-week 2025.02 mixes formats and aggregates.

    With today pinned to January 20, week 2025.02 (Mon 2025-01-06 to Sun
    2025-01-12) is a historical completed week. The start date resolves to draw
    4882 (dated 2025-01-04) and the week end resolves to the latest draw no
    later than Sunday 2025-01-12, draw 4883 (dated 2025-01-11). No fallback note
    is printed. The report folds draws 4882 + 4883 into a single aggregate and
    fetches nothing outside the range.
    """
    inject_clock(date(2025, 1, 20))
    for draw_number in (4882, 4883):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=draw_number), timeout=30
        ).and_return(mock_response(load_fixture(f"draw_{draw_number}.json")))

    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=1), timeout=30
    ).and_return(mock_response(load_fixture("datepicker_2025_01.json")))

    # No draw outside [4882, 4883] may be fetched, on either side of the range.
    for out_of_range in (4881, 4884, 4885):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=out_of_range), timeout=30
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


def test_excessive_end_week_index_resolves_to_final_draw(  # noqa: PLR0915
    mock_response, capsys
):
    """--end-week 2024.52.3 falls back to the week's final Draw 4881.

    ISO week 2024.52 holds two Draws: 4880 (December 26) and 4881 (December 29).
    The out-of-range index .3 selects no third Draw, so resolution falls back to
    the week's final Draw 4881. Starting at 4880, the report still spans the whole
    week, and the warning names the requested indexed week plus the fallback Draw
    and date. With today pinned to January 20, only the historical month is used.
    """
    inject_clock(date(2025, 1, 20))
    for draw_number in (4880, 4881):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=draw_number), timeout=30
        ).and_return(mock_response(load_fixture(f"draw_{draw_number}.json")))
    for draw_number in (4879, 4882):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=draw_number), timeout=30
        ).never()

    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2024, month=12), timeout=30
    ).and_return(mock_response(load_fixture("datepicker_2024_12.json")))
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=1), timeout=30
    ).never()

    exit_code = main(["--start-draw", "4880", "--end-week", "2024.52.3"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Warning" in captured.err
    assert "2024.52.3" in captured.err
    assert "4881" in captured.err
    assert "2024-12-29" in captured.err
    assert captured.out.splitlines() == [
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


@pytest.mark.parametrize(
    ("end_week", "expected_report", "expects_warning"),
    [
        pytest.param(
            "2025.01.1",
            _CROSS_YEAR_FIRST_DRAW_REPORT,
            False,
            id="first-distinct-draw",
        ),
        pytest.param(
            "2025.01.2",
            _CROSS_YEAR_BOTH_DRAWS_REPORT,
            False,
            id="second-distinct-draw",
        ),
        pytest.param(
            "2025.01.3",
            _CROSS_YEAR_BOTH_DRAWS_REPORT,
            True,
            id="excessive-index-fallback",
        ),
    ],
)
def test_cross_year_end_week_selects_distinct_draws(  # noqa: PLR0913, PLR0915
    mock_response, capsys, end_week, expected_report, expects_warning
):
    """An end week spanning a year boundary indexes distinct Draws chronologically.

    ISO week 2025.01 runs Mon 2024-12-30 to Sun 2025-01-05 and holds two distinct
    Draws: 4881 (2024-12-30) and 4882 (2025-01-04). No fixture contains two Draws
    in a cross-year week, so the real draw_4881 Draw is reused with its in-memory
    ``regCloseTime`` moved from 2024-12-29 to 2024-12-30. The monthly datepicker
    responses are synthetic, unsorted and overlapping: December 2024 is
    incomplete (it omits the 2024-12-30 Draw and lists only the later 2025-01-04
    Draw), so the resolver must fetch January 2025 before it can identify the
    first Draw. January 2025 repeats the 2024-12-30 Draw and also lists the
    2025-01-04 Draw already present in December.

    ``.1`` selects only Draw 4881, ``.2`` folds both Draws into one aggregate,
    and the excessive ``.3`` falls back to the week's final Draw 4882 with a
    warning naming the request and fallback. Duplicate and overlapping entries
    must neither advance the index nor duplicate a Draw's report contribution.
    """
    inject_clock(date(2025, 3, 1))

    first_draw = load_fixture("draw_4881.json")
    first_draw["draw"]["regCloseTime"] = "2024-12-30T15:59:00+01:00"
    second_draw = load_fixture("draw_4882.json")

    flexmock(requests).should_receive("get").with_args(
        DRAW_URL.format(n=4881), timeout=30
    ).at_least().once().and_return(mock_response(first_draw))
    # Draw 4882 may be resolved (``.2``/``.3``) but must not be fetched for ``.1``;
    # a lenient expectation keeps a wrongly resolved ``.1`` from hitting the network
    # while the aggregate assertion still proves it contributes nothing.
    flexmock(requests).should_receive("get").with_args(
        DRAW_URL.format(n=4882), timeout=30
    ).and_return(mock_response(second_draw))
    for out_of_range in (4879, 4880, 4883, 4884):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=out_of_range), timeout=30
        ).never()

    december_entries: dict[str, Any] = {
        "resultDates": [
            {"date": "2025-01-04T00:00:00+01:00", "drawNumber": 4882},
        ]
    }
    january_entries: dict[str, Any] = {
        "resultDates": [
            {"date": "2025-01-04T00:00:00+01:00", "drawNumber": 4882},
            {"date": "2024-12-30T00:00:00+01:00", "drawNumber": 4881},
            {"date": "2024-12-30T00:00:00+01:00", "drawNumber": 4881},
        ]
    }
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2024, month=12), timeout=30
    ).at_least().once().and_return(mock_response(december_entries))
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=1), timeout=30
    ).at_least().once().and_return(mock_response(january_entries))

    # Neither an unrelated month nor the today month (March 2025) may be looked up.
    for year, month in ((2024, 11), (2025, 2), (2025, 3)):
        flexmock(requests).should_receive("get").with_args(
            DATEPICKER_URL.format(year=year, month=month), timeout=30
        ).never()

    exit_code = main(["--start-draw", "4881", "--end-week", end_week])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.splitlines() == expected_report
    if expects_warning:
        assert captured.err.splitlines() == [
            "Warning: --end-week 2025.01.3 exceeds the draws in the week;"
            " using final draw 4882 (2025-01-04)."
        ]
    else:
        assert captured.err == ""


@pytest.mark.parametrize(
    ("end_week", "expected_error"),
    [
        pytest.param("2024.52", None, id="omitted-index"),
        pytest.param("2024.52.2", None, id="second-index"),
        pytest.param(
            "2024.52.1", _FIRST_DRAW_AFTER_START_ERROR, id="first-index-before-start"
        ),
    ],
)
def test_second_draw_start_bounds_completed_end_week(  # noqa: PLR0915
    mock_response, capsys, end_week, expected_error
):
    """Starting at the second Draw of completed week 2024.52 bounds the report.

    ISO week 2024.52 holds two Draws: 4880 (December 26) and 4881 (December 29).
    With today pinned to January 20, the week is wholly historical. Starting at
    the second Draw 4881, both ``--end-week 2024.52`` (index omitted) and
    ``2024.52.2`` resolve the end to 4881, so the report covers only that Draw
    and fetches no first or outside Draw. The explicit ``2024.52.1`` resolves
    the end to 4880, before the start, so the tool exits 1 with an ordering error
    naming both resolved numbers and fetches no report Draw at all.
    """
    inject_clock(date(2025, 1, 20))

    start_draw = (
        flexmock(requests)
        .should_receive("get")
        .with_args(DRAW_URL.format(n=4881), timeout=30)
    )
    if expected_error is None:
        start_draw.once().and_return(mock_response(load_fixture("draw_4881.json")))
    else:
        start_draw.never()

    # The week's first Draw 4880 and any Draw outside it must not be fetched.
    for draw_number in (4879, 4880, 4882, 4883):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=draw_number), timeout=30
        ).never()

    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2024, month=12), timeout=30
    ).at_least().once().and_return(
        mock_response(load_fixture("datepicker_2024_12.json"))
    )

    # The today month (January 2025) is never needed for the historical week.
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=1), timeout=30
    ).never()

    exit_code = main(["--start-draw", "4881", "--end-week", end_week])
    captured = capsys.readouterr()

    if expected_error is None:
        assert exit_code == 0
        assert captured.err == ""
        assert captured.out.splitlines() == _DRAW_4881_ONLY_REPORT
    else:
        assert exit_code == 1
        assert captured.err.splitlines() == [expected_error]
        assert captured.out == ""
