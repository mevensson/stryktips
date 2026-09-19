"""Failure and diagnostic contract tests for Period collection.

Collection is exercised through ``collect_period`` with directly constructed
``Dependencies``, so failures point at the collector rather than CLI wiring.
These tests cover skipped/missing draws, propagated request failures, empty
anchors, close-time rejection, and warning ordering.
"""

from datetime import date, datetime

import pytest
from requests import RequestException

from stryktips.api import DrawNotFoundError
from stryktips.collection import collect_period
from stryktips.dependencies import Dependencies, FetchDraw, FetchMonthEntries
from stryktips.models import DatepickerEntry, Draw
from tests.builders import make_draw


def test_collect_period_missing_interior_draw_is_skipped_and_reported():
    """An interior draw that 404s is skipped with a diagnostic instead of failing."""
    months = {
        (2025, 1): [
            DatepickerEntry(date=date(2025, 1, 4), draw_number=4882),
            DatepickerEntry(date=date(2025, 1, 11), draw_number=4883),
            DatepickerEntry(date=date(2025, 1, 18), draw_number=4884),
        ]
    }
    diagnostics: list[str] = []

    def fetch_draw(number: int) -> Draw:
        if number == 4883:
            raise DrawNotFoundError("Draw 4883 not found")
        return make_draw(
            draw_number=number, reg_close_time=datetime(2025, 1, 4, 15, 59)
        )

    dependencies = Dependencies(
        fetch_draw=fetch_draw,
        fetch_month_entries=lambda year, month: list(months.get((year, month), [])),
        clock=lambda: date(2025, 1, 4),
        diagnostic=diagnostics.append,
    )

    draws = collect_period(4882, 4884, dependencies)

    assert [draw.draw_number for draw in draws] == [4882, 4884]
    assert diagnostics == ["Warning: could not fetch draw 4883, skipping."]


def test_collect_period_non_not_found_failure_propagates():
    """A non-404 request failure on an interior draw fails the collection."""

    def fetch_draw(number: int) -> Draw:
        if number == 4883:
            raise RequestException("connection refused")
        return make_draw(
            draw_number=number, reg_close_time=datetime(2025, 1, 4, 15, 59)
        )

    dependencies = Dependencies(
        fetch_draw=fetch_draw,
        fetch_month_entries=lambda year, month: [
            DatepickerEntry(date=date(2025, 1, 4), draw_number=4882),
            DatepickerEntry(date=date(2025, 1, 11), draw_number=4883),
            DatepickerEntry(date=date(2025, 1, 18), draw_number=4884),
        ],
        clock=lambda: date(2025, 1, 4),
        diagnostic=lambda message: None,
    )

    with pytest.raises(RequestException, match="connection refused"):
        collect_period(4882, 4884, dependencies)


def test_collect_period_missing_anchor_returns_empty():
    """An absent anchor draw yields an empty Period rather than an error."""

    def fetch_draw(number: int) -> Draw:
        raise DrawNotFoundError(f"Draw {number} not found")

    dependencies = Dependencies(
        fetch_draw=fetch_draw,
        fetch_month_entries=lambda year, month: [],
        clock=lambda: date(2025, 1, 1),
        diagnostic=lambda message: None,
    )

    draws = collect_period(4900, 4901, dependencies)

    assert draws == []


def test_collect_period_warns_when_end_not_reached_within_scan_window():
    """An end draw never seen within the scan window is reported as truncation."""
    month_entry = DatepickerEntry(date=date(2020, 3, 7), draw_number=4641)
    diagnostics: list[str] = []
    dependencies = Dependencies(
        fetch_draw=lambda number: make_draw(
            draw_number=number, reg_close_time=datetime(2020, 3, 7, 15, 59)
        ),
        fetch_month_entries=lambda year, month: [month_entry],
        clock=lambda: date(2020, 3, 7),
        diagnostic=diagnostics.append,
    )

    draws = collect_period(4641, 4642, dependencies)

    assert [draw.draw_number for draw in draws] == [4641]
    assert diagnostics == [
        "Warning: could not reach draw 4642 within 12 months of 4641,"
        " report may be truncated."
    ]


def test_collect_period_spanning_requires_anchor_close_time():
    """A spanning Period without an anchor close time fails before walking months."""
    dependencies = Dependencies(
        fetch_draw=lambda number: make_draw(draw_number=number, reg_close_time=None),
        fetch_month_entries=lambda year, month: [],
        clock=lambda: date(2025, 1, 1),
        diagnostic=lambda message: None,
    )

    with pytest.raises(ValueError, match="Draw 4900 has no close time"):
        collect_period(4900, 4901, dependencies)


def test_collect_period_retries_and_rewarns_a_missing_interior_draw():
    """A missing draw seen in two months is retried and warned about each time."""
    months = {
        (2025, 5): [
            DatepickerEntry(date=date(2025, 5, 3), draw_number=4882),
            DatepickerEntry(date=date(2025, 5, 10), draw_number=4883),
        ],
        (2025, 6): [
            DatepickerEntry(date=date(2025, 6, 7), draw_number=4883),
            DatepickerEntry(date=date(2025, 6, 14), draw_number=4885),
        ],
    }
    diagnostics: list[str] = []
    fetched: list[int] = []
    dependencies = Dependencies(
        fetch_draw=_draw_fetcher(
            {4882: make_draw(draw_number=4882), 4885: make_draw(draw_number=4885)},
            fetched,
            missing={4883},
        ),
        fetch_month_entries=lambda year, month: list(months.get((year, month), [])),
        clock=lambda: date(2025, 5, 3),
        diagnostic=diagnostics.append,
    )

    draws = collect_period(4882, 4885, dependencies)

    assert [draw.draw_number for draw in draws] == [4882, 4885]
    assert fetched == [4882, 4883, 4883, 4885]
    assert diagnostics == [
        "Warning: could not fetch draw 4883, skipping.",
        "Warning: could not fetch draw 4883, skipping.",
    ]


def test_collect_period_month_lookup_failure_propagates_before_interior_fetch():
    """A later datepicker failure aborts the walk before any interior fetch."""
    fetched: list[int] = []
    month_lookups: list[tuple[int, int]] = []
    months = {
        (2025, 5): [
            DatepickerEntry(date=date(2025, 5, 3), draw_number=4882),
            DatepickerEntry(date=date(2025, 5, 10), draw_number=4883),
        ]
    }
    dependencies = Dependencies(
        fetch_draw=_draw_fetcher({4882: make_draw(draw_number=4882)}, fetched),
        fetch_month_entries=_month_fetcher(months, month_lookups),
        clock=lambda: date(2025, 5, 3),
        diagnostic=lambda message: None,
    )

    with pytest.raises(RequestException, match="datepicker unavailable"):
        collect_period(4882, 4885, dependencies)

    assert month_lookups == [(2025, 5), (2025, 6)]
    assert fetched == [4882]


def test_collect_period_anchor_request_failure_propagates():
    """A non-404 failure fetching the anchor draw fails the collection."""
    month_lookups: list[tuple[int, int]] = []

    def fetch_draw(number: int) -> Draw:
        raise RequestException("connection refused")

    def fetch_month_entries(year: int, month: int) -> list[DatepickerEntry]:
        month_lookups.append((year, month))
        return []

    dependencies = Dependencies(
        fetch_draw=fetch_draw,
        fetch_month_entries=fetch_month_entries,
        clock=lambda: date(2025, 5, 3),
        diagnostic=lambda message: None,
    )

    with pytest.raises(RequestException, match="connection refused"):
        collect_period(4882, 4885, dependencies)

    assert month_lookups == []


def test_collect_period_emits_truncation_warning_before_skip_warnings():
    """The traversal truncation warning precedes warnings from interior fetches."""
    diagnostics: list[str] = []

    def fetch_month_entries(year: int, month: int) -> list[DatepickerEntry]:
        return (
            [
                DatepickerEntry(date=date(2025, 5, 3), draw_number=4882),
                DatepickerEntry(date=date(2025, 5, 10), draw_number=4883),
            ]
            if (year, month) == (2025, 5)
            else []
        )

    dependencies = Dependencies(
        fetch_draw=_draw_fetcher(
            {4882: make_draw(draw_number=4882)}, [], missing={4883}
        ),
        fetch_month_entries=fetch_month_entries,
        clock=lambda: date(2025, 5, 3),
        diagnostic=diagnostics.append,
    )

    draws = collect_period(4882, 4890, dependencies)

    assert [draw.draw_number for draw in draws] == [4882]
    assert diagnostics == [
        "Warning: could not reach draw 4890 within 12 months of 4882,"
        " report may be truncated.",
        "Warning: could not fetch draw 4883, skipping.",
    ]


def _draw_fetcher(
    draws: dict[int, Draw],
    fetched: list[int],
    *,
    missing: set[int] | None = None,
) -> FetchDraw:
    """Return a fetcher that records draw numbers and 404s the missing ones."""
    missing_numbers = missing or set()

    def fetch(number: int) -> Draw:
        fetched.append(number)
        if number in missing_numbers:
            raise DrawNotFoundError(f"Draw {number} not found")
        return draws[number]

    return fetch


def _month_fetcher(
    months: dict[tuple[int, int], list[DatepickerEntry]],
    lookups: list[tuple[int, int]],
) -> FetchMonthEntries:
    """Return a datepicker lookup that records months and fails unknown ones."""

    def fetch(year: int, month: int) -> list[DatepickerEntry]:
        lookups.append((year, month))
        if (year, month) not in months:
            raise RequestException("datepicker unavailable")
        return list(months[(year, month)])

    return fetch
