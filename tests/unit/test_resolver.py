"""Unit tests for the draw number resolver."""

from datetime import date

import pytest

from stryktips.models import DatepickerEntry
from stryktips.resolver import (
    ResolveResult,
    parse_week_value,
    resolve_draw_by_date,
    resolve_draw_by_week,
    week_monday,
)


def test_resolve_result_is_named_tuple():
    """ResolveResult is a NamedTuple with the expected fields."""
    result = ResolveResult(
        draw_number=4900, exact_match=True, match_date=date(2025, 5, 10)
    )

    assert result.draw_number == 4900
    assert result.exact_match is True
    assert result.match_date == date(2025, 5, 10)


def test_resolve_draw_by_date_finds_exact_date_match():
    """When the target date matches a datepicker entry exactly, return it."""
    entries = [
        DatepickerEntry(date=date(2025, 5, 5), draw_number=4898),
        DatepickerEntry(date=date(2025, 5, 10), draw_number=4900),
    ]

    result = resolve_draw_by_date(date(2025, 5, 10), entries)

    assert result == ResolveResult(
        draw_number=4900, exact_match=True, match_date=date(2025, 5, 10)
    )


def test_resolve_draw_by_date_finds_next_available_draw():
    """When no entry matches the target date exactly, return the next available."""
    entries = [
        DatepickerEntry(date=date(2025, 5, 5), draw_number=4898),
        DatepickerEntry(date=date(2025, 5, 10), draw_number=4900),
    ]

    result = resolve_draw_by_date(date(2025, 5, 9), entries)

    assert result == ResolveResult(
        draw_number=4900, exact_match=False, match_date=date(2025, 5, 10)
    )


def test_resolve_draw_by_date_returns_zero_when_no_match():
    """When no entry has date >= target, return draw_number=0 and match_date=None."""
    entries = [
        DatepickerEntry(date=date(2025, 5, 5), draw_number=4898),
    ]

    result = resolve_draw_by_date(date(2025, 6, 1), entries)

    assert result == ResolveResult(draw_number=0, exact_match=False, match_date=None)


def test_resolve_draw_by_date_returns_zero_for_empty_data():
    """An empty datepicker list returns draw_number=0."""
    result = resolve_draw_by_date(date(2025, 5, 10), [])

    assert result == ResolveResult(draw_number=0, exact_match=False, match_date=None)


def test_resolve_draw_by_week_finds_draw_in_iso_week():
    """A week arg resolves to the first draw dated inside that ISO week."""
    entries = [
        DatepickerEntry(date=date(2025, 5, 3), draw_number=4899),
        DatepickerEntry(date=date(2025, 5, 10), draw_number=4900),
    ]

    result = resolve_draw_by_week(date(2025, 5, 5), entries)

    assert result == ResolveResult(
        draw_number=4900, exact_match=True, match_date=date(2025, 5, 10)
    )


def test_resolve_draw_by_week_finds_next_draw_when_week_is_empty():
    """When no entry is inside the ISO week, return the first entry after Monday."""
    entries = [
        DatepickerEntry(date=date(2020, 5, 9), draw_number=4900),
        DatepickerEntry(date=date(2020, 6, 20), draw_number=4642),
    ]

    result = resolve_draw_by_week(date(2020, 4, 6), entries)

    assert result == ResolveResult(
        draw_number=4900, exact_match=False, match_date=date(2020, 5, 9)
    )


def test_parse_week_value_returns_year_and_week():
    """A valid ISO week string parses to year and week numbers."""
    assert parse_week_value("2025.19") == (2025, 19)


def test_parse_week_value_raises_on_invalid():
    """An unparseable or out-of-range week string raises ValueError."""
    with pytest.raises(ValueError, match="Invalid week"):
        parse_week_value("2025")
    with pytest.raises(ValueError, match="Invalid week"):
        parse_week_value("2025.99")


def test_week_monday_returns_iso_monday():
    """week_monday returns the Monday of the given ISO week."""
    assert week_monday("2025.19") == date(2025, 5, 5)
