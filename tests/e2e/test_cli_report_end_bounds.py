"""End-to-end bound-resolution tests for the prediction-quality report CLI.

Requests are mocked so the concrete API adapter and parser run for real against
JSON fixtures. The clock is fixed through the public ``create_dependencies``
composition seam instead of patching ``date``.
"""

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import requests
from flexmock import flexmock

import stryktips.core as stryktips_core
from stryktips import main
from stryktips.core import create_dependencies

_FIXTURES = Path(__file__).parent.parent / "fixtures"
_DRAW_URL = "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/{n}"
_DATEPICKER_URL = (
    "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
    "?product=stryktipset&year={year}&month={month}"
)

# A 12-month backward window anchored on May 2025, crossing the year boundary.
_BACKWARD_MONTHS_FROM_MAY_2025 = [
    (2025, 5),
    (2025, 4),
    (2025, 3),
    (2025, 2),
    (2025, 1),
    (2024, 12),
    (2024, 11),
    (2024, 10),
    (2024, 9),
    (2024, 8),
    (2024, 7),
    (2024, 6),
]

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


def test_start_draw_without_end_draw_defaults_to_most_recent_draw(  # noqa: PLR0915
    mock_response, capsys
):
    """--start-draw 4881 (no --end-draw) runs up to the most recent draw before today.

    With "today" pinned to 2025-01-20, the defaulted end resolves to draw 4884
    (the latest datepicker entry on or before that date; the Feb 1 entry 4886 is
    after it). The report aggregates draws 4881-4884 exactly like an explicit
    --end-draw 4884, and no draw outside that range is fetched.
    """
    _inject_clock(date(2025, 1, 20))
    for draw_number in (4881, 4882, 4883, 4884):
        flexmock(requests).should_receive("get").with_args(
            _DRAW_URL.format(n=draw_number), timeout=30
        ).and_return(mock_response(_load(f"draw_{draw_number}.json")))

    for year, month in ((2024, 12), (2025, 1)):
        flexmock(requests).should_receive("get").with_args(
            _DATEPICKER_URL.format(year=year, month=month), timeout=30
        ).and_return(mock_response(_load(f"datepicker_{year}_{month:02d}.json")))

    # No draw outside the range may be fetched, on either side of the boundary.
    for out_of_range in (4880, 4885, 4886):
        flexmock(requests).should_receive("get").with_args(
            _DRAW_URL.format(n=out_of_range), timeout=30
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
    _inject_clock(date(2025, 1, 20))
    flexmock(requests).should_receive("get").with_args(
        _DRAW_URL.format(n=4900), timeout=30
    ).never()

    for year, month in ((2024, 12), (2025, 1)):
        flexmock(requests).should_receive("get").with_args(
            _DATEPICKER_URL.format(year=year, month=month), timeout=30
        ).and_return(mock_response(_load(f"datepicker_{year}_{month:02d}.json")))

    exit_code = main(["--start-draw", "4900"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.strip() == "eligible: 0, excluded: 0"


def test_start_date_resolves_to_draw(mock_response, capsys):  # noqa: PLR0915
    """--start-date 2025-05-10 --end-draw 4900 reuses the date resolver."""
    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2025, month=5), timeout=30
    ).and_return(mock_response(_load("datepicker_2025_05.json")))

    flexmock(requests).should_receive("get").with_args(
        _DRAW_URL.format(n=4900), timeout=30
    ).and_return(mock_response(_load("draw_4900.json")))

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
    _inject_clock(date(2025, 6, 1))
    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2025, month=5), timeout=30
    ).and_return(mock_response(_load("datepicker_2025_05.json")))

    flexmock(requests).should_receive("get").with_args(
        _DRAW_URL.format(n=4900), timeout=30
    ).and_return(mock_response(_load("draw_4900.json")))

    # The draw after the bound and the today-month datepicker are never fetched.
    flexmock(requests).should_receive("get").with_args(
        _DRAW_URL.format(n=4901), timeout=30
    ).never()
    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2025, month=6), timeout=30
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
    _inject_clock(date(2025, 5, 10))
    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2025, month=5), timeout=30
    ).and_return(mock_response(_load("datepicker_2025_05.json")))

    flexmock(requests).should_receive("get").with_args(
        _DRAW_URL.format(n=4900), timeout=30
    ).and_return(mock_response(_load("draw_4900.json")))

    # The later published draws and the future (June) bound month are never fetched.
    for later_draw in (4901, 4902, 4903):
        flexmock(requests).should_receive("get").with_args(
            _DRAW_URL.format(n=later_draw), timeout=30
        ).never()
    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2025, month=6), timeout=30
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


@pytest.mark.parametrize("end_week", ["2025.23", "2025.23.1", "2025.23.3"])
def test_future_end_week_clamps_to_today(  # noqa: PLR0915
    mock_response, capsys, end_week
):
    """A wholly future end week clamps to Draw 4900 (2025-05-10) without a warning.

    With "today" pinned to 2025-05-10, ISO week 2025.23 (June 2-8) is wholly in
    the future. Whether the week is unindexed or carries an explicit .1/.3
    index, it must end at the latest draw on or before today, 4900, without an
    index warning. The later published May draws 4901-4903 are excluded and the
    future June month is never looked up, because future draws need not be
    published.
    """
    _inject_clock(date(2025, 5, 10))
    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2025, month=5), timeout=30
    ).and_return(mock_response(_load("datepicker_2025_05.json")))

    flexmock(requests).should_receive("get").with_args(
        _DRAW_URL.format(n=4900), timeout=30
    ).and_return(mock_response(_load("draw_4900.json")))

    # The later published May draws and the future June month are never fetched.
    for later_draw in (4901, 4902, 4903):
        flexmock(requests).should_receive("get").with_args(
            _DRAW_URL.format(n=later_draw), timeout=30
        ).never()
    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2025, month=6), timeout=30
    ).never()

    exit_code = main(["--start-draw", "4900", "--end-week", end_week])
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


def test_start_week_resolves_to_draw(mock_response, capsys):  # noqa: PLR0915
    """--start-week 2025.19 --end-draw 4900 reuses the week resolver."""
    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2025, month=5), timeout=30
    ).and_return(mock_response(_load("datepicker_2025_05.json")))

    flexmock(requests).should_receive("get").with_args(
        _DRAW_URL.format(n=4900), timeout=30
    ).and_return(mock_response(_load("draw_4900.json")))

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
def test_end_week_resolves_to_draw(mock_response, capsys, end_week):  # noqa: PLR0915
    """A historical end week includes both Draws unless index .1 is explicit.

    Draws 4880 (December 26) and 4881 (December 29) are in ISO week 2024.52.
    The 4880 fixture is trimmed from the API response, retaining all 13 matches.
    With today pinned to January 20, only the historical month is needed.
    """
    _inject_clock(date(2025, 1, 20))
    first_only = end_week == "2024.52.1"
    included_draws = (4880,) if first_only else (4880, 4881)
    excluded_draws = (4879, 4881, 4882) if first_only else (4879, 4882)
    for draw_number in included_draws:
        flexmock(requests).should_receive("get").with_args(
            _DRAW_URL.format(n=draw_number), timeout=30
        ).and_return(mock_response(_load(f"draw_{draw_number}.json")))
    for draw_number in excluded_draws:
        flexmock(requests).should_receive("get").with_args(
            _DRAW_URL.format(n=draw_number), timeout=30
        ).never()

    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2024, month=12), timeout=30
    ).and_return(mock_response(_load("datepicker_2024_12.json")))
    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2025, month=1), timeout=30
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


def test_current_week_indexed_end_selects_first_draw(  # noqa: PLR0915
    mock_response, capsys
):
    """--start-draw 4880 --end-week 2024.52.1 on Sunday 2024-12-29 ends at 4880.

    ISO week 2024.52 holds draws 4880 (December 26) and 4881 (December 29).
    With "today" pinned to Sunday 2024-12-29, both draws are dated on or before
    today, so the week is current but already available. The explicit index .1
    must still select only 4880 as the report end without a warning, even though
    a later draw in the same week is also available. Draws 4881 and every other
    draw outside [4880, 4880] must not be fetched.
    """
    _inject_clock(date(2024, 12, 29))
    flexmock(requests).should_receive("get").with_args(
        _DRAW_URL.format(n=4880), timeout=30
    ).and_return(mock_response(_load("draw_4880.json")))
    for draw_number in (4879, 4881, 4882):
        flexmock(requests).should_receive("get").with_args(
            _DRAW_URL.format(n=draw_number), timeout=30
        ).never()

    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2024, month=12), timeout=30
    ).and_return(mock_response(_load("datepicker_2024_12.json")))
    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2025, month=1), timeout=30
    ).never()

    exit_code = main(["--start-draw", "4880", "--end-week", "2024.52.1"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    assert captured.out.splitlines() == [
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


@pytest.mark.parametrize(
    ("today", "expects_warning"),
    [
        pytest.param(date(2024, 12, 29), False, id="sunday-current-week"),
        pytest.param(date(2024, 12, 30), True, id="monday-completed-week"),
    ],
)
def test_excessive_end_week_index_clamps_silently_only_while_week_is_current(  # noqa: PLR0915
    mock_response, capsys, today, expects_warning
):
    """--end-week 2024.52.3 falls back to Draw 4881 on the Sunday and Monday.

    ISO week 2024.52 holds Draws 4880 (December 26) and 4881 (December 29).
    On Sunday 2024-12-29 the week is current, so the excessive index .3 clamps
    silently to the latest Draw on or before today (4881). On Monday
    2024-12-30 the week has completed, so the same request warns that it
    exceeds the draws in the week and falls back to final Draw 4881
    (2024-12-29). Both aggregate the full [4880, 4881] report, and Draws
    outside the range and the future January datepicker month are never
    fetched.
    """
    _inject_clock(today)
    for draw_number in (4880, 4881):
        flexmock(requests).should_receive("get").with_args(
            _DRAW_URL.format(n=draw_number), timeout=30
        ).and_return(mock_response(_load(f"draw_{draw_number}.json")))
    for draw_number in (4879, 4882):
        flexmock(requests).should_receive("get").with_args(
            _DRAW_URL.format(n=draw_number), timeout=30
        ).never()

    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2024, month=12), timeout=30
    ).and_return(mock_response(_load("datepicker_2024_12.json")))
    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2025, month=1), timeout=30
    ).never()

    exit_code = main(["--start-draw", "4880", "--end-week", "2024.52.3"])
    captured = capsys.readouterr()

    assert exit_code == 0
    if not expects_warning:
        assert captured.err == ""
    else:
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
    ("end_week", "unpublished_draw"),
    [
        pytest.param("2025.20.1", None, id="published-draw-after-today"),
        pytest.param("2025.20.2", None, id="unavailable-index"),
        pytest.param("2025.20.1", 4901, id="no-draw-yet-this-week"),
    ],
)
def test_current_week_later_or_missing_index_clamps_to_latest_draw(  # noqa: PLR0915
    mock_response, capsys, end_week, unpublished_draw
):
    """A current-week end index past today clamps to Draw 4900 (2025-05-10).

    With "today" pinned to Monday 2025-05-12, ISO week 2025.20 is current and
    its only Draw 4901 (May 17) is later in the week. An index selecting that
    later Draw, an index that is not yet available, and an unpublished week
    with no Draw yet all end at the latest Draw on or before today (4900),
    without an index warning or fallback note. Draws 4901-4903 and the June
    datepicker month are never fetched.
    """
    _inject_clock(date(2025, 5, 12))
    datepicker_data = _load("datepicker_2025_05.json")
    if unpublished_draw is not None:
        datepicker_data["resultDates"] = [
            entry
            for entry in datepicker_data["resultDates"]
            if entry["drawNumber"] != unpublished_draw
        ]
    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2025, month=5), timeout=30
    ).and_return(mock_response(datepicker_data))

    flexmock(requests).should_receive("get").with_args(
        _DRAW_URL.format(n=4900), timeout=30
    ).and_return(mock_response(_load("draw_4900.json")))
    for later_draw in (4901, 4902, 4903):
        flexmock(requests).should_receive("get").with_args(
            _DRAW_URL.format(n=later_draw), timeout=30
        ).never()
    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2025, month=6), timeout=30
    ).never()

    exit_code = main(["--start-draw", "4900", "--end-week", end_week])
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


def test_unindexed_current_end_week_clamps_to_latest_draw(  # noqa: PLR0915
    mock_response, capsys
):
    """An unindexed end week containing today ends at the latest Draw on/before today.

    With "today" pinned to Wednesday 2025-05-14, ISO week 2025.20 (May 12-18)
    is current and its Sunday is still in the future. The unindexed end must
    clamp to the latest Draw on or before today, 4900 (May 10), without a
    warning. The later published May draws 4901-4903 are excluded and the
    future June month is never looked up.
    """
    _inject_clock(date(2025, 5, 14))
    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2025, month=5), timeout=30
    ).and_return(mock_response(_load("datepicker_2025_05.json")))

    flexmock(requests).should_receive("get").with_args(
        _DRAW_URL.format(n=4900), timeout=30
    ).and_return(mock_response(_load("draw_4900.json")))

    for later_draw in (4901, 4902, 4903):
        flexmock(requests).should_receive("get").with_args(
            _DRAW_URL.format(n=later_draw), timeout=30
        ).never()
    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2025, month=6), timeout=30
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


def test_unindexed_drawless_end_week_resolves_to_latest_preceding_draw(  # noqa: PLR0915
    mock_response, capsys
):
    """Historical week 2025.20 (May 12–18) ends at Draw 4900 without a warning.

    The synthetic May datepicker omits Draw 4901, leaving the week empty.
    Draw 4900 (May 10) is the latest preceding Draw; 4902 (May 25) is next.
    Both are in the bound month, so no multi-month backward search is needed.
    """
    _inject_clock(date(2025, 6, 1))
    datepicker_data = _load("datepicker_2025_05.json")
    datepicker_data["resultDates"] = [
        entry for entry in datepicker_data["resultDates"] if entry["drawNumber"] != 4901
    ]
    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2025, month=5), timeout=30
    ).and_return(mock_response(datepicker_data))
    flexmock(requests).should_receive("get").with_args(
        _DRAW_URL.format(n=4900), timeout=30
    ).and_return(mock_response(_load("draw_4900.json")))
    for draw_number in (4899, 4901, 4902, 4903):
        flexmock(requests).should_receive("get").with_args(
            _DRAW_URL.format(n=draw_number), timeout=30
        ).never()
    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2025, month=6), timeout=30
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
    _inject_clock(date(2025, 6, 1))
    datepicker_data = _load("datepicker_2025_05.json")
    datepicker_data["resultDates"] = [
        entry for entry in datepicker_data["resultDates"] if entry["drawNumber"] != 4901
    ]
    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2025, month=5), timeout=30
    ).and_return(mock_response(datepicker_data))
    flexmock(requests).should_receive("get").with_args(
        _DRAW_URL.format(n=4900), timeout=30
    ).and_return(mock_response(_load("draw_4900.json")))
    for draw_number in (4899, 4901, 4902, 4903):
        flexmock(requests).should_receive("get").with_args(
            _DRAW_URL.format(n=draw_number), timeout=30
        ).never()
    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2025, month=6), timeout=30
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


@pytest.mark.parametrize(
    "end_bound",
    [
        ["--end-date", "2020-05-15"],
        ["--end-week", "2020.20"],
    ],
)
def test_historical_end_bound_searches_back_across_empty_months(  # noqa: PLR0915
    mock_response, capsys, end_bound
):
    """A May 2020 date/unindexed-week end resolves back to Draw 4641.

    With today pinned to 2020-06-01, both --end-date 2020-05-15 and
    --end-week 2020.20 (Sunday 2020-05-17) bound the report in May 2020. May
    returns an empty 200, April 2020 returns 404, and March 2020 holds the
    latest preceding Draw 4641 (2020-03-14). The backward search must query the
    bound and intervening months in order, never the today month (June), and
    fetch only Draw 4641.
    """
    _inject_clock(date(2020, 6, 1))

    empty_data: dict[str, list[Any]] = {"resultDates": []}
    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2020, month=5), timeout=30
    ).once().ordered().and_return(mock_response(empty_data))
    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2020, month=4), timeout=30
    ).once().ordered().and_return(
        mock_response({"error": "not_found"}, status_code=404)
    )
    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2020, month=3), timeout=30
    ).once().ordered().and_return(mock_response(_load("datepicker_2020_03.json")))

    flexmock(requests).should_receive("get").with_args(
        _DRAW_URL.format(n=4641), timeout=30
    ).once().and_return(mock_response(_load("draw_4641.json")))

    # Neither the today month nor any Draw outside the resolved end is fetched.
    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2020, month=6), timeout=30
    ).never()
    for draw_number in (4639, 4640, 4642, 4643, 4644):
        flexmock(requests).should_receive("get").with_args(
            _DRAW_URL.format(n=draw_number), timeout=30
        ).never()

    exit_code = main(["--start-draw", "4641", *end_bound])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    assert captured.out.splitlines() == ["eligible: 0, excluded: 7"]


@pytest.mark.parametrize(
    ("end_args", "expected_months", "expected_error"),
    [
        (
            ["--end-date", "2025-05-15"],
            _BACKWARD_MONTHS_FROM_MAY_2025,
            "No draw found within 12 months of 2025-05-15",
        ),
        (
            ["--end-week", "2025.20"],
            _BACKWARD_MONTHS_FROM_MAY_2025,
            "No draw found within 12 months of 2025-05-18",
        ),
        (
            ["--end-week", "2025.20.1"],
            [(2025, 5), *_BACKWARD_MONTHS_FROM_MAY_2025],
            "No draw found within 12 months of 2025-05-11",
        ),
    ],
)
def test_end_bound_without_preceding_draw_errors_after_backward_window(  # noqa: PLR0913, PLR0915
    mock_response, capsys, end_args, expected_months, expected_error
):
    """A date or week end with no predecessor fails within the 12-month window.

    With "today" pinned to 2025-06-01, a May 2025 date or week bound searches
    the bound month and 11 earlier months (May 2025 back to June 2024) across
    the year boundary. Every month is empty or absent, so resolution fails
    within 12 months rather than reaching the 13th older month (May 2024) or the
    today month (June 2025). The indexed empty completed-week bound first
    inspects the requested month and repeats it as the first month of the
    backward window. Exit is 1 with a bounded-search message on stderr, no
    fallback warning, empty stdout, and no report Draw fetch.
    """
    _inject_clock(date(2025, 6, 1))
    for year, month in expected_months:
        if (year, month) == (2025, 5):
            payload: dict[str, Any] = {"resultDates": []}
            status_code = 200
        else:
            payload = {"error": "not_found"}
            status_code = 404
        flexmock(requests).should_receive("get").with_args(
            _DATEPICKER_URL.format(year=year, month=month), timeout=30
        ).once().ordered().and_return(mock_response(payload, status_code=status_code))

    # The 13th older month and the today month are never looked up.
    for year, month in ((2024, 5), (2025, 6)):
        flexmock(requests).should_receive("get").with_args(
            _DATEPICKER_URL.format(year=year, month=month), timeout=30
        ).never()

    # No report Draw may be fetched when the end bound fails to resolve.
    flexmock(requests).should_receive("get").with_args(
        _DRAW_URL.format(n=4884), timeout=30
    ).never()

    exit_code = main(["--start-draw", "4884", *end_args])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert expected_error in captured.err
    assert "Warning" not in captured.err
    assert captured.out == ""


def test_mixed_start_date_end_week_aggregates(mock_response, capsys):  # noqa: PLR0915
    """--start-date 2025-01-04 --end-week 2025.02 mixes formats and aggregates.

    The start date resolves to draw 4882 (dated 2025-01-04) and the end week
    resolves to draw 4883 (dated 2025-01-11, inside ISO week 2025.02). Both
    resolutions are exact matches, so no fallback note is printed. The report
    folds draws 4882 + 4883 into a single aggregate and fetches nothing outside
    the range.
    """
    for draw_number in (4882, 4883):
        flexmock(requests).should_receive("get").with_args(
            _DRAW_URL.format(n=draw_number), timeout=30
        ).and_return(mock_response(_load(f"draw_{draw_number}.json")))

    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2025, month=1), timeout=30
    ).and_return(mock_response(_load("datepicker_2025_01.json")))

    # No draw outside [4882, 4883] may be fetched, on either side of the range.
    for out_of_range in (4881, 4884, 4885):
        flexmock(requests).should_receive("get").with_args(
            _DRAW_URL.format(n=out_of_range), timeout=30
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
    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2025, month=5), timeout=30
    ).and_return(mock_response(_load("datepicker_2025_05.json")))

    for draw_number in (4884, 4900):
        flexmock(requests).should_receive("get").with_args(
            _DRAW_URL.format(n=draw_number), timeout=30
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
    for year, month in ((2020, 4), (2020, 5)):
        flexmock(requests).should_receive("get").with_args(
            _DATEPICKER_URL.format(year=year, month=month), timeout=30
        ).and_return(mock_response(empty_data))

    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2020, month=6), timeout=30
    ).and_return(mock_response(_load("datepicker_2020_06.json")))

    flexmock(requests).should_receive("get").with_args(
        _DRAW_URL.format(n=4642), timeout=30
    ).and_return(mock_response(_load("draw_4642.json")))

    # No draw after the resolved end may be fetched.
    for out_of_range in (4643, 4644):
        flexmock(requests).should_receive("get").with_args(
            _DRAW_URL.format(n=out_of_range), timeout=30
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
    _inject_clock(date(2025, 1, 20))
    for draw_number in (4880, 4881):
        flexmock(requests).should_receive("get").with_args(
            _DRAW_URL.format(n=draw_number), timeout=30
        ).and_return(mock_response(_load(f"draw_{draw_number}.json")))
    for draw_number in (4879, 4882):
        flexmock(requests).should_receive("get").with_args(
            _DRAW_URL.format(n=draw_number), timeout=30
        ).never()

    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2024, month=12), timeout=30
    ).and_return(mock_response(_load("datepicker_2024_12.json")))
    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2025, month=1), timeout=30
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
    _inject_clock(date(2025, 3, 1))

    first_draw = _load("draw_4881.json")
    first_draw["draw"]["regCloseTime"] = "2024-12-30T15:59:00+01:00"
    second_draw = _load("draw_4882.json")

    flexmock(requests).should_receive("get").with_args(
        _DRAW_URL.format(n=4881), timeout=30
    ).at_least().once().and_return(mock_response(first_draw))
    # Draw 4882 may be resolved (``.2``/``.3``) but must not be fetched for ``.1``;
    # a lenient expectation keeps a wrongly resolved ``.1`` from hitting the network
    # while the aggregate assertion still proves it contributes nothing.
    flexmock(requests).should_receive("get").with_args(
        _DRAW_URL.format(n=4882), timeout=30
    ).and_return(mock_response(second_draw))
    for out_of_range in (4879, 4880, 4883, 4884):
        flexmock(requests).should_receive("get").with_args(
            _DRAW_URL.format(n=out_of_range), timeout=30
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
        _DATEPICKER_URL.format(year=2024, month=12), timeout=30
    ).at_least().once().and_return(mock_response(december_entries))
    flexmock(requests).should_receive("get").with_args(
        _DATEPICKER_URL.format(year=2025, month=1), timeout=30
    ).at_least().once().and_return(mock_response(january_entries))

    # Neither an unrelated month nor the today month (March 2025) may be looked up.
    for year, month in ((2024, 11), (2025, 2), (2025, 3)):
        flexmock(requests).should_receive("get").with_args(
            _DATEPICKER_URL.format(year=year, month=month), timeout=30
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


def _load(name: str) -> dict[str, Any]:
    """Load a JSON fixture by file name."""
    data: dict[str, Any] = json.loads((_FIXTURES / name).read_text())
    return data


def _inject_clock(today: date) -> None:
    """Fix the clock through the composition seam while keeping the real API I/O."""
    flexmock(
        stryktips_core,
        create_dependencies=lambda: create_dependencies(clock=lambda: today),
    )
