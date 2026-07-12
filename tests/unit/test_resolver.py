"""Unit tests for the draw number resolver."""

from datetime import date

import pytest


def test_resolve_result_is_named_tuple():
    """ResolveResult is a NamedTuple with the expected fields."""
    from stryktips.resolver import ResolveResult

    result = ResolveResult(
        draw_number=4900, exact_match=True, match_date=date(2025, 5, 10)
    )

    assert result.draw_number == 4900
    assert result.exact_match is True
    assert result.match_date == date(2025, 5, 10)


def test_resolve_draw_number_finds_exact_date_match():
    """When the target date matches a datepicker entry exactly, return it."""
    from stryktips.resolver import ResolveResult, resolve_draw_number

    from stryktips.models import DatepickerEntry

    entries = [
        DatepickerEntry(date=date(2025, 5, 5), draw_number=4898),
        DatepickerEntry(date=date(2025, 5, 10), draw_number=4900),
    ]

    result = resolve_draw_number("2025-05-10", "date", entries)

    assert result == ResolveResult(
        draw_number=4900, exact_match=True, match_date=date(2025, 5, 10)
    )


def test_resolve_draw_number_finds_next_available_draw():
    """When no entry matches the target date exactly, return the next available."""
    from stryktips.resolver import ResolveResult, resolve_draw_number

    from stryktips.models import DatepickerEntry

    entries = [
        DatepickerEntry(date=date(2025, 5, 5), draw_number=4898),
        DatepickerEntry(date=date(2025, 5, 10), draw_number=4900),
    ]

    result = resolve_draw_number("2025-05-09", "date", entries)

    assert result == ResolveResult(
        draw_number=4900, exact_match=False, match_date=date(2025, 5, 10)
    )


def test_resolve_draw_number_returns_zero_when_no_match():
    """When no entry has date >= target, return draw_number=0 and match_date=None."""
    from stryktips.resolver import ResolveResult, resolve_draw_number

    from stryktips.models import DatepickerEntry

    entries = [
        DatepickerEntry(date=date(2025, 5, 5), draw_number=4898),
    ]

    result = resolve_draw_number("2025-06-01", "date", entries)

    assert result == ResolveResult(draw_number=0, exact_match=False, match_date=None)


def test_resolve_draw_number_returns_zero_for_empty_data():
    """An empty datepicker list returns draw_number=0."""
    from stryktips.resolver import ResolveResult, resolve_draw_number

    result = resolve_draw_number("2025-05-10", "date", [])

    assert result == ResolveResult(draw_number=0, exact_match=False, match_date=None)


def test_resolve_draw_number_raises_on_invalid_date_string():
    """An unparseable date string raises ValueError."""
    from stryktips.resolver import resolve_draw_number

    from stryktips.models import DatepickerEntry

    entries = [DatepickerEntry(date=date(2025, 5, 10), draw_number=4900)]

    with pytest.raises(ValueError, match="Invalid date"):
        resolve_draw_number("not-a-date", "date", entries)
