"""Unit tests for the draw number resolver."""

from datetime import date

import pytest

from stryktips.models import DatepickerEntry
from stryktips.resolver import (
    ResolveResult,
    WeekDrawIndexError,
    resolve_draw_by_date,
    resolve_draw_by_week,
    week_monday,
)


def test_resolve_result_is_named_tuple():
    """ResolveResult is a NamedTuple with the expected fields."""
    # Act
    result = ResolveResult(
        draw_number=4900, exact_match=True, match_date=date(2025, 5, 10)
    )

    # Assert
    assert isinstance(result, tuple)
    assert (result.draw_number, result.exact_match, result.match_date) == (
        4900,
        True,
        date(2025, 5, 10),
    )


def test_resolve_draw_by_date_finds_exact_date_match():
    """When the target date matches a datepicker entry exactly, return it."""
    # Arrange
    entries = [
        DatepickerEntry(date=date(2025, 5, 5), draw_number=4898),
        DatepickerEntry(date=date(2025, 5, 10), draw_number=4900),
    ]

    # Act
    result = resolve_draw_by_date(date(2025, 5, 10), entries)

    # Assert
    assert result == ResolveResult(
        draw_number=4900, exact_match=True, match_date=date(2025, 5, 10)
    )


def test_resolve_draw_by_date_finds_next_available_draw():
    """When no entry matches the target date exactly, return the next available."""
    # Arrange
    entries = [
        DatepickerEntry(date=date(2025, 5, 5), draw_number=4898),
        DatepickerEntry(date=date(2025, 5, 10), draw_number=4900),
    ]

    # Act
    result = resolve_draw_by_date(date(2025, 5, 9), entries)

    # Assert
    assert result == ResolveResult(
        draw_number=4900, exact_match=False, match_date=date(2025, 5, 10)
    )


@pytest.mark.parametrize(
    ("target", "entries"),
    [
        (date(2025, 6, 1), [DatepickerEntry(date=date(2025, 5, 5), draw_number=4898)]),
        (date(2025, 5, 10), []),
    ],
    ids=["no-entry-on-or-after", "empty-datepicker"],
)
def test_resolve_draw_by_date_returns_not_found(target, entries):
    """Without an entry on or after the target, return the not-found result."""
    # Act
    result = resolve_draw_by_date(target, entries)

    # Assert
    assert result == ResolveResult(draw_number=None, exact_match=False, match_date=None)


def test_resolve_draw_by_week_finds_draw_in_iso_week():
    """A week arg resolves to the first draw dated inside that ISO week."""
    # Arrange
    entries = [
        DatepickerEntry(date=date(2025, 5, 3), draw_number=4899),
        DatepickerEntry(date=date(2025, 5, 10), draw_number=4900),
    ]

    # Act
    result = resolve_draw_by_week(date(2025, 5, 5), entries)

    # Assert
    assert result == ResolveResult(
        draw_number=4900, exact_match=True, match_date=date(2025, 5, 10)
    )


def test_resolve_draw_by_week_selects_nth_draw():
    """An n arg returns the N-th draw dated inside that ISO week."""
    # Arrange
    entries = [
        DatepickerEntry(date=date(2024, 12, 26), draw_number=4880),
        DatepickerEntry(date=date(2024, 12, 29), draw_number=4881),
    ]

    # Act
    result = resolve_draw_by_week(date(2024, 12, 23), entries, n=2)

    # Assert
    assert result == ResolveResult(
        draw_number=4881, exact_match=True, match_date=date(2024, 12, 29)
    )


def test_resolve_draw_by_week_selects_nth_distinct_draw_from_duplicates():
    """An n arg counts distinct draws once when entries repeat and are unsorted."""
    # Arrange
    entries = [
        DatepickerEntry(date=date(2025, 1, 4), draw_number=4882),
        DatepickerEntry(date=date(2024, 12, 30), draw_number=4881),
        DatepickerEntry(date=date(2024, 12, 30), draw_number=4881),
        DatepickerEntry(date=date(2025, 1, 4), draw_number=4882),
    ]

    # Act
    result = resolve_draw_by_week(date(2024, 12, 30), entries, n=2)

    # Assert
    assert result == ResolveResult(
        draw_number=4882, exact_match=True, match_date=date(2025, 1, 4)
    )


def test_resolve_draw_by_week_raises_when_n_exceeds_in_week_draws():
    """When n exceeds the number of in-week draws, raise a descriptive ValueError."""
    # Arrange
    entries = [
        DatepickerEntry(date=date(2024, 12, 26), draw_number=4880),
        DatepickerEntry(date=date(2024, 12, 29), draw_number=4881),
    ]

    with pytest.raises(
        WeekDrawIndexError,
        match="Week 2024.52 has 2 draws",
    ):
        resolve_draw_by_week(date(2024, 12, 23), entries, n=3)


def test_resolve_draw_by_week_raises_on_non_positive_n():
    """A non-positive n argument raises ValueError."""
    # Arrange
    entries = [
        DatepickerEntry(date=date(2025, 5, 10), draw_number=4900),
    ]

    with pytest.raises(ValueError, match="Draw number must be a positive integer"):
        resolve_draw_by_week(date(2025, 5, 5), entries, n=0)


def test_resolve_draw_by_week_finds_next_draw_when_week_is_empty():
    """When no entry is inside the ISO week, return the first entry after Monday."""
    # Arrange
    entries = [
        DatepickerEntry(date=date(2020, 6, 20), draw_number=4642),
    ]

    # Act
    result = resolve_draw_by_week(date(2020, 4, 6), entries)

    # Assert
    assert result == ResolveResult(
        draw_number=4642, exact_match=False, match_date=date(2020, 6, 20)
    )


def test_week_monday_returns_iso_monday():
    """week_monday returns the Monday of the given ISO week."""
    # Act
    result = week_monday("2025.19")

    # Assert
    assert result == date(2025, 5, 5)
