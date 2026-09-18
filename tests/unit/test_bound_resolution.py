"""Public contract tests for bound resolution in stryktips.resolution.

Resolution is exercised through ``resolve_draw`` and ``resolve_end`` with
directly constructed ``Dependencies``, so failures point at the resolver rather
than CLI wiring.
"""

from collections.abc import Callable
from datetime import date

import pytest

from stryktips.dependencies import Dependencies
from stryktips.models import DatepickerEntry, Draw
from stryktips.resolution import (
    DrawByDate,
    DrawByNumber,
    DrawByWeek,
    resolve_draw,
    resolve_end,
)
from stryktips.resolver import DrawNotFound
from tests.builders import make_dependencies


def test_draw_by_week_unindexed_derives_fields_and_keeps_spelling():
    """An unindexed week derives year/week, leaves index None, keeps its spelling."""
    # Act
    selector = DrawByWeek("2025.01")

    # Assert
    assert (selector.value, selector.year, selector.week, selector.index) == (
        "2025.01",
        2025,
        1,
        None,
    )


def test_draw_by_week_explicit_index_derives_fields_and_keeps_spelling():
    """An explicit ``.N`` derives the index while keeping the raw spelling."""
    # Act
    selector = DrawByWeek("2024.52.3")

    # Assert
    assert (selector.value, selector.year, selector.week, selector.index) == (
        "2024.52.3",
        2024,
        52,
        3,
    )


@pytest.mark.parametrize("value", ["abc", "2025", "2025.99", "2025.19.0"])
def test_draw_by_week_rejects_invalid_value(value):
    """An invalid week value raises before any resolution happens."""
    # Act / Assert
    with pytest.raises(ValueError, match="Invalid week"):
        DrawByWeek(value)


def test_resolve_draw_by_number_does_not_consult_datepicker():
    """A draw-number selector resolves directly without a month lookup."""

    def unexpected_lookup(year: int, month: int) -> list[DatepickerEntry]:
        raise AssertionError("draw number must not consult the datepicker")

    dependencies = Dependencies(
        fetch_draw=_no_fetch_draw(),
        fetch_month_entries=unexpected_lookup,
        clock=lambda: date(2025, 1, 1),
        diagnostic=lambda message: None,
    )

    result = resolve_draw(DrawByNumber(4900), dependencies)

    assert result == 4900


@pytest.mark.parametrize(
    ("selector", "months"),
    [
        pytest.param(
            DrawByDate("2025-05-10"),
            {(2025, 5): [DatepickerEntry(date=date(2025, 5, 10), draw_number=4900)]},
            id="date",
        ),
        pytest.param(
            DrawByWeek("2025.19"),
            {(2025, 5): [DatepickerEntry(date=date(2025, 5, 10), draw_number=4900)]},
            id="week",
        ),
    ],
)
def test_resolve_draw_does_not_fetch_the_draw(selector, months):
    """Resolution consults the datepicker only and never fetches a draw."""
    dependencies = Dependencies(
        fetch_draw=_no_fetch_draw(),
        fetch_month_entries=lambda year, month: list(months.get((year, month), [])),
        clock=lambda: date(2025, 1, 1),
        diagnostic=lambda message: None,
    )

    result = resolve_draw(selector, dependencies)

    assert result == 4900


def test_resolve_draw_by_date_returns_exact_match():
    """An entry dated exactly on the target resolves without a fallback note."""
    entries = [DatepickerEntry(date=date(2025, 5, 10), draw_number=4900)]
    diagnostics: list[str] = []
    dependencies = make_dependencies({(2025, 5): entries}, diagnostics=diagnostics)

    result = resolve_draw(DrawByDate("2025-05-10"), dependencies)

    assert result == 4900
    assert diagnostics == []


def test_resolve_draw_by_date_forward_scans_empty_months():
    """An empty anchor month advances until the next draw, reporting a fallback."""
    calls: list[tuple[int, int]] = []
    diagnostics: list[str] = []
    months = {
        (2020, 6): [DatepickerEntry(date=date(2020, 6, 20), draw_number=4642)],
    }
    dependencies = make_dependencies(months, month_calls=calls, diagnostics=diagnostics)

    result = resolve_draw(DrawByDate("2020-04-01"), dependencies)

    assert result == 4642
    assert calls == [(2020, 4), (2020, 5), (2020, 6)]
    assert diagnostics == [
        "Note: No draw found for 2020-04-01, using 2020-06-20 (draw 4642)"
    ]


def test_resolve_draw_by_week_selects_explicit_index():
    """An explicit ``.N`` suffix selects the N-th distinct draw without a note."""
    entries = [
        DatepickerEntry(date=date(2024, 12, 26), draw_number=4880),
        DatepickerEntry(date=date(2024, 12, 29), draw_number=4881),
    ]
    diagnostics: list[str] = []
    dependencies = make_dependencies({(2024, 12): entries}, diagnostics=diagnostics)

    result = resolve_draw(DrawByWeek("2024.52.2"), dependencies)

    assert result == 4881
    assert diagnostics == []


def test_resolve_draw_by_week_omitted_index_selects_first_distinct():
    """An omitted index counts distinct draws once from unsorted duplicate entries."""
    entries = [
        DatepickerEntry(date=date(2024, 12, 29), draw_number=4881),
        DatepickerEntry(date=date(2024, 12, 26), draw_number=4880),
        DatepickerEntry(date=date(2024, 12, 26), draw_number=4880),
    ]
    dependencies = make_dependencies({(2024, 12): entries})

    result = resolve_draw(DrawByWeek("2024.52"), dependencies)

    assert result == 4880


def test_resolve_draw_by_week_gathers_both_months_before_selecting():
    """A cross-year week gathers both months before selecting the first draw."""
    months = {
        (2024, 12): [DatepickerEntry(date=date(2025, 1, 4), draw_number=4882)],
        (2025, 1): [
            DatepickerEntry(date=date(2024, 12, 30), draw_number=4881),
            DatepickerEntry(date=date(2025, 1, 4), draw_number=4882),
        ],
    }
    dependencies = make_dependencies(months)

    result = resolve_draw(DrawByWeek("2025.01"), dependencies)

    assert result == 4881


def test_resolve_draw_by_week_excessive_index_reports_options():
    """An index beyond the week's distinct draws names the available indices."""
    entries = [
        DatepickerEntry(date=date(2024, 12, 26), draw_number=4880),
        DatepickerEntry(date=date(2024, 12, 29), draw_number=4881),
    ]
    dependencies = make_dependencies({(2024, 12): entries})

    with pytest.raises(ValueError) as exc:
        resolve_draw(DrawByWeek("2024.52.3"), dependencies)

    assert str(exc.value) == (
        "Error: Week 2024.52 has 2 draws (dates: 2024-12-26, 2024-12-29). "
        "Use --week 2024.52.1 or --week 2024.52.2."
    )


def test_resolve_draw_by_date_raises_after_scan_window():
    """A forward selector with no entry within the scan window raises not-found."""
    dependencies = make_dependencies()

    with pytest.raises(DrawNotFound) as exc:
        resolve_draw(DrawByDate("2000-01-01"), dependencies)

    assert exc.value.value == "2000-01-01"


def test_resolve_draw_by_week_raises_after_scan_window():
    """A forward week selector with no draw within the window raises not-found."""
    dependencies = make_dependencies()

    with pytest.raises(DrawNotFound) as exc:
        resolve_draw(DrawByWeek("2000.01"), dependencies)

    assert exc.value.value == "2000.01"


def test_resolve_draw_by_week_scan_window_is_twelve_months():
    """The forward week scan consults exactly the twelve-month scan window."""
    calls: list[tuple[int, int]] = []
    dependencies = make_dependencies(month_calls=calls)

    with pytest.raises(DrawNotFound):
        resolve_draw(DrawByWeek("2000.01"), dependencies)

    assert calls == [(2000, month) for month in range(1, 13)]


def test_resolve_end_explicit_draw_returns_it_verbatim():
    """An explicit end draw is used as given, without a datepicker lookup."""

    def unexpected_lookup(year: int, month: int) -> list[DatepickerEntry]:
        raise AssertionError("an explicit end draw must not consult the datepicker")

    dependencies = Dependencies(
        fetch_draw=_no_fetch_draw(),
        fetch_month_entries=unexpected_lookup,
        clock=lambda: date(2025, 1, 1),
        diagnostic=lambda message: None,
    )

    result = resolve_end(DrawByNumber(4884), dependencies)

    assert result == 4884


def test_resolve_end_date_returns_latest_draw_on_or_before_bound():
    """An end date resolves to the latest draw on or before the bound."""
    entries = [
        DatepickerEntry(date=date(2025, 5, 3), draw_number=4899),
        DatepickerEntry(date=date(2025, 5, 10), draw_number=4900),
        DatepickerEntry(date=date(2025, 5, 17), draw_number=4901),
    ]
    dependencies = make_dependencies({(2025, 5): entries}, today=date(2025, 6, 1))

    result = resolve_end(DrawByDate("2025-05-11"), dependencies)

    assert result == 4900


def test_resolve_end_date_clamps_future_bound_to_today():
    """A future end date is clamped to today before resolving."""
    entries = [DatepickerEntry(date=date(2025, 5, 10), draw_number=4900)]
    dependencies = make_dependencies({(2025, 5): entries}, today=date(2025, 5, 10))

    result = resolve_end(DrawByDate("2025-06-01"), dependencies)

    assert result == 4900


def test_resolve_end_defaults_to_latest_draw_on_or_before_today():
    """Without an end selector the latest draw on or before today is used."""
    entries = [DatepickerEntry(date=date(2025, 1, 18), draw_number=4884)]
    dependencies = make_dependencies({(2025, 1): entries}, today=date(2025, 1, 20))

    result = resolve_end(None, dependencies)

    assert result == 4884


def test_resolve_end_default_scans_back_across_year_boundary():
    """An empty today month steps back into the previous year for the default end."""
    calls: list[tuple[int, int]] = []
    months = {
        (2025, 1): [DatepickerEntry(date=date(2025, 1, 4), draw_number=4882)],
        (2024, 12): [DatepickerEntry(date=date(2024, 12, 29), draw_number=4881)],
    }
    dependencies = make_dependencies(months, today=date(2025, 1, 1), month_calls=calls)

    result = resolve_end(None, dependencies)

    assert result == 4881
    assert calls == [(2025, 1), (2024, 12)]


def test_resolve_end_default_stops_scanning_once_entry_found():
    """The default end stops at the first month holding an eligible entry."""
    calls: list[tuple[int, int]] = []

    def fetch_month_entries(year: int, month: int) -> list[DatepickerEntry]:
        calls.append((year, month))
        return [DatepickerEntry(date=date(year, month, 10), draw_number=1000)]

    dependencies = Dependencies(
        fetch_draw=_no_fetch_draw(),
        fetch_month_entries=fetch_month_entries,
        clock=lambda: date(2025, 1, 20),
        diagnostic=lambda message: None,
    )

    result = resolve_end(None, dependencies)

    assert result == 1000
    assert calls == [(2025, 1)]


def test_resolve_end_default_raises_after_scan_window():
    """The default end raises not-found once the backward window is exhausted."""
    dependencies = make_dependencies(today=date(2000, 1, 1))

    with pytest.raises(DrawNotFound) as exc:
        resolve_end(None, dependencies)

    assert exc.value.value == "2000-01-01"


def test_resolve_end_unindexed_week_clamps_future_sunday_to_today():
    """An unindexed week whose Sunday is future clamps to today's latest draw."""
    entries = [
        DatepickerEntry(date=date(2025, 5, 10), draw_number=4900),
        DatepickerEntry(date=date(2025, 5, 17), draw_number=4901),
    ]
    dependencies = make_dependencies({(2025, 5): entries}, today=date(2025, 5, 14))

    result = resolve_end(DrawByWeek("2025.20"), dependencies)

    assert result == 4900


def test_resolve_end_unindexed_week_uses_latest_draw_on_or_before_sunday():
    """A completed unindexed week resolves to the latest draw on or before Sunday."""
    entries = [
        DatepickerEntry(date=date(2024, 12, 26), draw_number=4880),
        DatepickerEntry(date=date(2024, 12, 29), draw_number=4881),
    ]
    dependencies = make_dependencies({(2024, 12): entries}, today=date(2025, 1, 20))

    result = resolve_end(DrawByWeek("2024.52"), dependencies)

    assert result == 4881


def test_resolve_end_unindexed_week_scans_back_from_sunday_month():
    """An unindexed end week starts at the Sunday's month and scans back a year."""
    calls: list[tuple[int, int]] = []
    months = {
        (2024, 12): [DatepickerEntry(date=date(2024, 12, 29), draw_number=4881)],
    }
    dependencies = make_dependencies(months, today=date(2025, 3, 1), month_calls=calls)

    result = resolve_end(DrawByWeek("2025.01"), dependencies)

    assert result == 4881
    assert calls == [(2025, 1), (2024, 12)]


def test_resolve_end_explicit_index_selects_first_draw_in_current_week():
    """An explicit ``.1`` on the current week selects only the first draw."""
    entries = [
        DatepickerEntry(date=date(2024, 12, 26), draw_number=4880),
        DatepickerEntry(date=date(2024, 12, 29), draw_number=4881),
    ]
    dependencies = make_dependencies({(2024, 12): entries}, today=date(2024, 12, 29))

    result = resolve_end(DrawByWeek("2024.52.1"), dependencies)

    assert result == 4880


def test_resolve_end_current_week_index_after_today_clamps_to_latest_draw():
    """A current-week index selecting a draw after today clamps without a warning."""
    entries = [
        DatepickerEntry(date=date(2025, 5, 10), draw_number=4900),
        DatepickerEntry(date=date(2025, 5, 17), draw_number=4901),
    ]
    diagnostics: list[str] = []
    dependencies = make_dependencies(
        {(2025, 5): entries}, today=date(2025, 5, 12), diagnostics=diagnostics
    )

    result = resolve_end(DrawByWeek("2025.20.1"), dependencies)

    assert result == 4900
    assert diagnostics == []


def test_resolve_end_current_indexed_week_spans_months_and_clamps_to_today():
    """A current indexed week gathers both months, then clamps its draw to today."""
    calls: list[tuple[int, int]] = []
    months = {
        (2025, 1): [
            DatepickerEntry(date=date(2024, 12, 30), draw_number=4880),
            DatepickerEntry(date=date(2025, 1, 4), draw_number=4882),
        ],
        (2024, 12): [
            DatepickerEntry(date=date(2025, 1, 4), draw_number=4882),
            DatepickerEntry(date=date(2024, 12, 30), draw_number=4880),
        ],
    }
    dependencies = make_dependencies(months, today=date(2025, 1, 2), month_calls=calls)

    result = resolve_end(DrawByWeek("2025.01.2"), dependencies)

    assert result == 4880
    assert set(calls) == {(2025, 1), (2024, 12)}


def test_resolve_end_future_indexed_week_clamps_to_latest_draw():
    """A wholly future indexed week clamps to the latest draw on or before today."""
    entries = [DatepickerEntry(date=date(2025, 5, 10), draw_number=4900)]
    dependencies = make_dependencies({(2025, 5): entries}, today=date(2025, 5, 10))

    result = resolve_end(DrawByWeek("2025.23.1"), dependencies)

    assert result == 4900


def test_resolve_end_completed_excessive_index_warns_and_returns_final_draw():
    """A completed week's excessive index falls back to its final draw and warns."""
    entries = [
        DatepickerEntry(date=date(2024, 12, 26), draw_number=4880),
        DatepickerEntry(date=date(2024, 12, 29), draw_number=4881),
    ]
    diagnostics: list[str] = []
    dependencies = make_dependencies(
        {(2024, 12): entries}, today=date(2025, 1, 20), diagnostics=diagnostics
    )

    result = resolve_end(DrawByWeek("2024.52.3"), dependencies)

    assert result == 4881
    assert diagnostics == [
        "Warning: --end-week 2024.52.3 exceeds the draws in the week;"
        " using final draw 4881 (2024-12-29)."
    ]


def test_resolve_end_excessive_index_tie_breaks_same_date_draws_by_number():
    """The excessive-index fallback breaks a same-date tie by draw number."""
    months = {
        (2024, 12): [
            DatepickerEntry(date=date(2025, 1, 4), draw_number=4881),
            DatepickerEntry(date=date(2024, 12, 30), draw_number=4880),
            DatepickerEntry(date=date(2025, 1, 4), draw_number=4882),
        ],
        (2025, 1): [DatepickerEntry(date=date(2025, 1, 4), draw_number=4882)],
    }
    diagnostics: list[str] = []
    dependencies = make_dependencies(
        months, today=date(2025, 3, 1), diagnostics=diagnostics
    )

    result = resolve_end(DrawByWeek("2025.01.4"), dependencies)

    assert result == 4882
    assert diagnostics == [
        "Warning: --end-week 2025.01.4 exceeds the draws in the week;"
        " using final draw 4882 (2025-01-04)."
    ]


def test_resolve_end_empty_completed_indexed_week_warns_and_returns_predecessor():
    """An empty completed indexed week falls back to the preceding draw and warns."""
    months = {
        (2025, 5): [
            DatepickerEntry(date=date(2025, 5, 10), draw_number=4900),
            DatepickerEntry(date=date(2025, 5, 25), draw_number=4902),
        ]
    }
    diagnostics: list[str] = []
    dependencies = make_dependencies(
        months, today=date(2025, 6, 1), diagnostics=diagnostics
    )

    result = resolve_end(DrawByWeek("2025.20.1"), dependencies)

    assert result == 4900
    assert diagnostics == [
        "Warning: --end-week 2025.20.1 has no draws;"
        " using preceding draw 4900 (2025-05-10)."
    ]


def test_resolve_end_indexed_week_gathers_both_months_before_selecting():
    """A cross-year indexed end gathers both week months before selecting ``.1``."""
    calls: list[tuple[int, int]] = []
    months = {
        (2024, 12): [DatepickerEntry(date=date(2025, 1, 4), draw_number=4882)],
        (2025, 1): [DatepickerEntry(date=date(2024, 12, 30), draw_number=4881)],
    }
    dependencies = make_dependencies(months, today=date(2025, 3, 1), month_calls=calls)

    result = resolve_end(DrawByWeek("2025.01.1"), dependencies)

    assert result == 4881
    assert calls == [(2024, 12), (2025, 1)]


def test_resolve_end_without_preceding_draw_raises_after_scan_window():
    """An end bound with no predecessor raises within the backward scan window."""
    dependencies = make_dependencies(today=date(2025, 6, 1))

    with pytest.raises(DrawNotFound) as exc:
        resolve_end(DrawByDate("2025-05-15"), dependencies)

    assert exc.value.value == "2025-05-15"


def _no_fetch_draw() -> Callable[[int], Draw]:
    def unexpected_fetch(number: int) -> Draw:
        raise AssertionError("resolution must not fetch a draw")

    return unexpected_fetch
