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


def test_collect_period_collects_complete_multi_year_period():
    """All Draws are collected across two year boundaries, including late Draws."""
    draw_dates = {
        4800: date(2023, 1, 7),
        4801: date(2023, 6, 3),
        4802: date(2024, 1, 6),
        4803: date(2025, 1, 4),
    }
    available_draws = {
        number: make_draw(
            draw_number=number,
            reg_close_time=datetime.combine(draw_date, datetime.min.time()),
        )
        for number, draw_date in draw_dates.items()
    }
    months = {
        (draw_date.year, draw_date.month): [
            DatepickerEntry(date=draw_date, draw_number=number)
        ]
        for number, draw_date in draw_dates.items()
    }

    def fetch_month_entries(year: int, month: int) -> list[DatepickerEntry]:
        assert (2023, 1) <= (year, month) <= (2025, 1), (
            "collection must not walk beyond the terminal month"
        )
        return list(months.get((year, month), []))

    dependencies = Dependencies(
        fetch_draw=available_draws.__getitem__,
        fetch_month_entries=fetch_month_entries,
        clock=lambda: date(2025, 1, 4),
        diagnostic=lambda message: None,
    )

    draws = collect_period(4800, 4803, dependencies)

    assert [draw.draw_number for draw in draws] == [4800, 4801, 4802, 4803]


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


def test_collect_period_multi_year_gap_includes_eligible_unsorted_terminal_entry():  # noqa: PLR0915 (keeps strict IO callbacks with their fixture)
    """A missing numeric end still includes eligible entries after an overshoot."""
    expected_months = [
        (year, month)
        for year in range(2023, 2026)
        for month in range(1, 13)
        if (year, month) <= (2025, 1)
    ]
    calls: list[tuple[int, int]] = []
    months = {
        (2023, 1): [DatepickerEntry(date=date(2023, 1, 7), draw_number=4800)],
        (2024, 1): [DatepickerEntry(date=date(2024, 1, 6), draw_number=4801)],
        (2025, 1): [
            DatepickerEntry(date=date(2025, 1, 18), draw_number=4804),
            DatepickerEntry(date=date(2025, 1, 4), draw_number=4802),
        ],
    }
    available_draws = {
        number: make_draw(
            draw_number=number, reg_close_time=datetime(2023, 1, 7, 15, 59)
        )
        for number in (4800, 4801, 4802)
    }

    def fetch_month_entries(year: int, month: int) -> list[DatepickerEntry]:
        assert len(calls) < len(expected_months), "walk exceeded the terminal month"
        assert (year, month) == expected_months[len(calls)]
        calls.append((year, month))
        return list(months.get((year, month), []))

    dependencies = Dependencies(
        fetch_draw=available_draws.__getitem__,
        fetch_month_entries=fetch_month_entries,
        clock=lambda: date(2025, 1, 18),
        diagnostic=lambda message: None,
    )

    draws = collect_period(4800, 4803, dependencies)

    assert [draw.draw_number for draw in draws] == [4800, 4801, 4802]


def test_collect_period_multi_year_overlapping_entries_fetches_each_draw_once():  # noqa: PLR0915 (keeps strict IO callbacks with their fixture)
    """Overlapping responses across a year boundary never refetch a Draw."""
    fetched: list[int] = []
    months = {
        (2023, 1): [DatepickerEntry(date=date(2023, 1, 7), draw_number=4800)],
        (2023, 12): [
            DatepickerEntry(date=date(2023, 12, 30), draw_number=4801),
            DatepickerEntry(date=date(2024, 1, 6), draw_number=4802),
        ],
        (2024, 1): [
            DatepickerEntry(date=date(2023, 12, 30), draw_number=4801),
            DatepickerEntry(date=date(2024, 1, 6), draw_number=4802),
        ],
        (2025, 1): [DatepickerEntry(date=date(2025, 1, 4), draw_number=4803)],
    }
    available_draws = {
        number: make_draw(
            draw_number=number, reg_close_time=datetime(2023, 1, 7, 15, 59)
        )
        for number in (4800, 4801, 4802, 4803)
    }

    def fetch_draw(number: int) -> Draw:
        fetched.append(number)
        return available_draws[number]

    def fetch_month_entries(year: int, month: int) -> list[DatepickerEntry]:
        assert (2023, 1) <= (year, month) <= (2025, 1), (
            "collection must not walk beyond the terminal month"
        )
        return list(months.get((year, month), []))

    dependencies = Dependencies(
        fetch_draw=fetch_draw,
        fetch_month_entries=fetch_month_entries,
        clock=lambda: date(2025, 1, 4),
        diagnostic=lambda message: None,
    )

    collect_period(4800, 4803, dependencies)

    assert fetched == [4800, 4801, 4802, 4803]


def test_collect_period_deduplicates_repeated_month_entries():
    """A draw repeated within and across month responses is reported once."""
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

    dependencies = make_dependencies(
        months=months,
        draws={
            number: make_draw(
                draw_number=number, reg_close_time=datetime(2025, 1, 4, 15, 59)
            )
            for number in (4882, 4883, 4884)
        },
        today=date(2025, 1, 4),
    )

    draws = collect_period(4882, 4884, dependencies)

    assert [draw.draw_number for draw in draws] == [4882, 4883, 4884]


def test_collect_period_fetches_repeated_month_entries_once():
    """A draw repeated within and across month responses is fetched once."""
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
    dependencies = make_dependencies(
        months=months,
        draws={
            number: make_draw(
                draw_number=number, reg_close_time=datetime(2025, 1, 4, 15, 59)
            )
            for number in (4882, 4883, 4884)
        },
        today=date(2025, 1, 4),
        fetched=fetched,
    )

    collect_period(4882, 4884, dependencies)

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
