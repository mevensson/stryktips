"""Draw number resolution from CLI arguments."""

from datetime import date
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
        value: The argument value (string for ``"date"``, int for ``"draw"``).
        arg_type: The type of resolution (``"date"`` or ``"draw"``).
        datepicker_data: List of available datepicker entries.

    Returns:
        A ResolveResult with the resolved draw number and match metadata.

    Raises:
        ValueError: If the value cannot be parsed for the given arg_type.
    """
    if arg_type == "date":
        target = _parse_date_value(value)
        return _resolve_by_date(target, datepicker_data)
    if arg_type == "week":
        year, week = _parse_week_value(value)
        return _resolve_by_week(year, week, datepicker_data)
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
    year = int(parts[0])
    week = int(parts[1])
    if not 1 <= week <= 53:  # noqa: PLR2004
        msg = f"Invalid week: {value}"
        raise ValueError(msg)
    return year, week


def _resolve_by_week(
    year: int, week: int, entries: list[DatepickerEntry]
) -> ResolveResult:
    monday = date.fromisocalendar(year, week, 1)
    sunday = date.fromisocalendar(year, week, 7)
    for entry in entries:
        if monday <= entry.date <= sunday:
            return ResolveResult(
                draw_number=entry.draw_number,
                exact_match=True,
                match_date=entry.date,
            )

    return ResolveResult(draw_number=0, exact_match=False, match_date=None)
