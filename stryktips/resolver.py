"""Draw number resolution from CLI arguments."""

from datetime import date, timedelta
from typing import NamedTuple

from stryktips.models import DatepickerEntry


class ResolveResult(NamedTuple):
    draw_number: int
    exact_match: bool
    match_date: date | None


def resolve_draw_number(
    value: str | int | date,
    arg_type: str,
    datepicker_data: list[DatepickerEntry],
) -> ResolveResult:
    """Resolve a CLI argument value to a draw number.

    Args:
        value: The argument value to resolve. A date string (``YYYY-MM-DD``)
            or ``date`` object for ``"date"``; an ISO week string (``YYYY.WW``)
            for ``"week"``.
        arg_type: The type of resolution (``"date"`` or ``"week"``).
        datepicker_data: List of available datepicker entries.

    Returns:
        A ResolveResult with the resolved draw number and match metadata.

    Raises:
        ValueError: If the value cannot be parsed for the given arg_type,
            including ISO week numbers that are outside a valid range for
            their year (1-52, or 53 for years that have an ISO 53rd week).
    """
    if arg_type == "date":
        target = _parse_date_value(value)
        return _resolve_by_date(target, datepicker_data)
    if arg_type == "week":
        return _resolve_by_week(_week_monday(value), datepicker_data)
    msg = f"Unknown arg_type: {arg_type}"
    raise ValueError(msg)


def _parse_date_value(value: str | int | date) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        msg = f"Invalid date: {value}"
        raise ValueError(msg) from None


def _resolve_by_date(target: date, entries: list[DatepickerEntry]) -> ResolveResult:
    for entry in entries:
        if entry.date >= target:
            return ResolveResult(
                draw_number=entry.draw_number,
                exact_match=(entry.date == target),
                match_date=entry.date,
            )

    return ResolveResult(draw_number=0, exact_match=False, match_date=None)


def _parse_week_value(value: str | int | date) -> tuple[int, int]:
    parts = str(value).split(".")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):  # noqa: PLR2004
        msg = f"Invalid week: {value}"
        raise ValueError(msg)
    year, week = (int(part) for part in parts)
    try:
        date.fromisocalendar(year, week, 1)
    except ValueError:
        raise ValueError(f"Invalid week: {value}") from None
    return year, week


def _week_monday(value: str | int | date) -> date:
    if isinstance(value, date):
        return value
    return date.fromisocalendar(*_parse_week_value(value), 1)


def _resolve_by_week(monday: date, entries: list[DatepickerEntry]) -> ResolveResult:
    sunday = monday + timedelta(days=6)
    for entry in entries:
        if monday <= entry.date <= sunday:
            return ResolveResult(
                draw_number=entry.draw_number,
                exact_match=True,
                match_date=entry.date,
            )

    return ResolveResult(draw_number=0, exact_match=False, match_date=None)
