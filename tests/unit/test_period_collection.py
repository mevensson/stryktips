"""Public contract tests for Period collection in stryktips.collection.

Collection is exercised through ``collect_period`` with directly constructed
``Dependencies``, so failures point at the collector rather than CLI wiring.
These tests cover successful collection and traversal only; failure and
diagnostic behavior lives in ``test_period_collection_failures.py``.
"""

from datetime import date, datetime

from stryktips.collection import collect_period
from stryktips.dependencies import Dependencies
from stryktips.models import DatepickerEntry, Draw
from tests.builders import make_dependencies, make_draw


def test_collect_period_single_draw_skips_datepicker():
    """A single-draw Period fetches only that draw, never walking the datepicker."""

    def unexpected_lookup(year: int, month: int) -> list[DatepickerEntry]:
        raise AssertionError("a single-draw Period must not walk the datepicker")

    dependencies = Dependencies(
        fetch_draw=lambda number: make_draw(draw_number=number),
        fetch_month_entries=unexpected_lookup,
        clock=lambda: date(2025, 1, 1),
        diagnostic=lambda message: None,
    )

    draws = collect_period(4900, 4900, dependencies)

    assert [draw.draw_number for draw in draws] == [4900]


def test_collect_period_spanning_includes_both_bounds_in_order():
    """A spanning Period includes both resolved bounds and no out-of-range draw."""
    months = {
        (2025, 5): [
            DatepickerEntry(date=date(2025, 5, 3), draw_number=4880),
            DatepickerEntry(date=date(2025, 5, 10), draw_number=4900),
            DatepickerEntry(date=date(2025, 5, 17), draw_number=4901),
        ]
    }
    dependencies = make_dependencies(
        draws={4900: make_draw(draw_number=4900), 4901: make_draw(draw_number=4901)},
        months=months,
    )

    draws = collect_period(4900, 4901, dependencies)

    assert [draw.draw_number for draw in draws] == [4900, 4901]


def test_collect_period_walks_across_drawless_months():
    """The month walk skips empty months and still reaches the inclusive end."""
    calls: list[tuple[int, int]] = []
    months = {
        (2020, 3): [
            DatepickerEntry(date=date(2020, 3, 7), draw_number=4639),
            DatepickerEntry(date=date(2020, 3, 14), draw_number=4641),
        ],
        (2020, 6): [DatepickerEntry(date=date(2020, 6, 20), draw_number=4642)],
    }

    def fetch_month_entries(year: int, month: int) -> list[DatepickerEntry]:
        calls.append((year, month))
        return list(months.get((year, month), []))

    dependencies = Dependencies(
        fetch_draw=lambda number: make_draw(
            draw_number=number, reg_close_time=datetime(2020, 3, 14, 15, 59)
        ),
        fetch_month_entries=fetch_month_entries,
        clock=lambda: date(2020, 3, 14),
        diagnostic=lambda message: None,
    )

    draws = collect_period(4641, 4642, dependencies)

    assert [draw.draw_number for draw in draws] == [4641, 4642]
    assert calls == [(2020, 3), (2020, 4), (2020, 5), (2020, 6)]


def test_collect_period_deduplicates_repeated_month_entries():
    """A draw repeated across month responses is fetched and reported once."""
    fetched: list[int] = []
    months = {
        (2025, 1): [
            DatepickerEntry(date=date(2025, 1, 4), draw_number=4882),
            DatepickerEntry(date=date(2025, 1, 11), draw_number=4883),
            DatepickerEntry(date=date(2025, 1, 11), draw_number=4883),
        ],
        (2025, 2): [
            DatepickerEntry(date=date(2025, 2, 1), draw_number=4884),
            DatepickerEntry(date=date(2025, 1, 11), draw_number=4883),
        ],
    }

    def fetch_draw(number: int) -> Draw:
        fetched.append(number)
        return make_draw(
            draw_number=number, reg_close_time=datetime(2025, 1, 4, 15, 59)
        )

    dependencies = Dependencies(
        fetch_draw=fetch_draw,
        fetch_month_entries=lambda year, month: list(months.get((year, month), [])),
        clock=lambda: date(2025, 1, 4),
        diagnostic=lambda message: None,
    )

    draws = collect_period(4882, 4884, dependencies)

    assert [draw.draw_number for draw in draws] == [4882, 4883, 4884]
    assert fetched == [4882, 4883, 4884]


def test_collect_period_single_draw_without_close_time_skips_datepicker():
    """A single-draw Period needs no close time and never walks the datepicker."""

    def unexpected_lookup(year: int, month: int) -> list[DatepickerEntry]:
        raise AssertionError("a single-draw Period must not walk the datepicker")

    dependencies = Dependencies(
        fetch_draw=lambda number: make_draw(draw_number=number, reg_close_time=None),
        fetch_month_entries=unexpected_lookup,
        clock=lambda: date(2025, 1, 1),
        diagnostic=lambda message: None,
    )

    draws = collect_period(4900, 4900, dependencies)

    assert [draw.draw_number for draw in draws] == [4900]


def test_collect_period_walks_all_months_before_fetching_interior_draws():
    """The full month walk completes before any interior draw is fetched."""
    events: list[str] = []

    def fetch_draw(number: int) -> Draw:
        events.append(f"draw {number}")
        return make_draw(draw_number=number)

    def fetch_month_entries(year: int, month: int) -> list[DatepickerEntry]:
        events.append(f"month {year}-{month:02d}")
        return (
            [DatepickerEntry(date=date(2025, 5, 3), draw_number=4882)]
            if (year, month) == (2025, 5)
            else [DatepickerEntry(date=date(2025, 6, 14), draw_number=4885)]
        )

    dependencies = Dependencies(
        fetch_draw=fetch_draw,
        fetch_month_entries=fetch_month_entries,
        clock=lambda: date(2025, 5, 3),
        diagnostic=lambda message: None,
    )

    draws = collect_period(4882, 4885, dependencies)

    assert [draw.draw_number for draw in draws] == [4882, 4885]
    assert events == ["draw 4882", "month 2025-05", "month 2025-06", "draw 4885"]


def test_collect_period_stops_when_an_entry_exceeds_end_without_warning():
    """An entry past the end ends the walk even when the exact end is absent."""
    calls: list[tuple[int, int]] = []
    diagnostics: list[str] = []

    def fetch_month_entries(year: int, month: int) -> list[DatepickerEntry]:
        calls.append((year, month))
        return [
            DatepickerEntry(date=date(2025, 5, 3), draw_number=4882),
            DatepickerEntry(date=date(2025, 5, 10), draw_number=4883),
            DatepickerEntry(date=date(2025, 5, 17), draw_number=4885),
        ]

    dependencies = Dependencies(
        fetch_draw=lambda number: make_draw(draw_number=number),
        fetch_month_entries=fetch_month_entries,
        clock=lambda: date(2025, 5, 3),
        diagnostic=diagnostics.append,
    )

    draws = collect_period(4882, 4884, dependencies)

    assert [draw.draw_number for draw in draws] == [4882, 4883]
    assert calls == [(2025, 5)]
    assert diagnostics == []
