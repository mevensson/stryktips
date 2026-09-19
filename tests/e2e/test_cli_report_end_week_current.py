"""End-to-end future and current end-week bound tests for the report CLI.

Requests are mocked so the concrete API adapter and parser run for real against
JSON fixtures. The clock is fixed through the public ``create_dependencies``
composition seam instead of patching ``date``.
"""

from datetime import date

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
    inject_clock(date(2025, 5, 10))
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=5), timeout=30
    ).and_return(mock_response(load_fixture("datepicker_2025_05.json")))

    flexmock(requests).should_receive("get").with_args(
        DRAW_URL.format(n=4900), timeout=30
    ).and_return(mock_response(load_fixture("draw_4900.json")))

    # The later published May draws and the future June month are never fetched.
    for later_draw in (4901, 4902, 4903):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=later_draw), timeout=30
        ).never()
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=6), timeout=30
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
    inject_clock(date(2024, 12, 29))
    flexmock(requests).should_receive("get").with_args(
        DRAW_URL.format(n=4880), timeout=30
    ).and_return(mock_response(load_fixture("draw_4880.json")))
    for draw_number in (4879, 4881, 4882):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=draw_number), timeout=30
        ).never()

    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2024, month=12), timeout=30
    ).and_return(mock_response(load_fixture("datepicker_2024_12.json")))
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=1), timeout=30
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
    inject_clock(today)
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
    inject_clock(date(2025, 5, 12))
    datepicker_data = load_fixture("datepicker_2025_05.json")
    if unpublished_draw is not None:
        datepicker_data["resultDates"] = [
            entry
            for entry in datepicker_data["resultDates"]
            if entry["drawNumber"] != unpublished_draw
        ]
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=5), timeout=30
    ).and_return(mock_response(datepicker_data))

    flexmock(requests).should_receive("get").with_args(
        DRAW_URL.format(n=4900), timeout=30
    ).and_return(mock_response(load_fixture("draw_4900.json")))
    for later_draw in (4901, 4902, 4903):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=later_draw), timeout=30
        ).never()
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=6), timeout=30
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
    inject_clock(date(2025, 5, 14))
    flexmock(requests).should_receive("get").with_args(
        DATEPICKER_URL.format(year=2025, month=5), timeout=30
    ).and_return(mock_response(load_fixture("datepicker_2025_05.json")))

    flexmock(requests).should_receive("get").with_args(
        DRAW_URL.format(n=4900), timeout=30
    ).and_return(mock_response(load_fixture("draw_4900.json")))

    for later_draw in (4901, 4902, 4903):
        flexmock(requests).should_receive("get").with_args(
            DRAW_URL.format(n=later_draw), timeout=30
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
