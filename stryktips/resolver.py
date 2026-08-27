"""Draw number resolution from CLI arguments."""

from datetime import date, timedelta
from typing import NamedTuple

from stryktips.models import DatepickerEntry


class ResolveResult(NamedTuple):
    draw_number: int
    exact_match: bool
    match_date: date | None


class DrawNotFound(Exception):
    """Raised when no draw is found within the scan window.

    The constructor argument carries the CLI value that failed to resolve
    (a date string or ISO week string) so the caller can format a message.
    """

    def __init__(self, value: str) -> None:
        super().__init__(value)
        self.value = value


def resolve_draw_by_date(target: date, entries: list[DatepickerEntry]) -> ResolveResult:
    """Resolve the first entry on or after the target date."""
    for entry in entries:
        if entry.date >= target:
            return ResolveResult(
                draw_number=entry.draw_number,
                exact_match=(entry.date == target),
                match_date=entry.date,
            )
    return ResolveResult(draw_number=0, exact_match=False, match_date=None)


def resolve_draw_by_week(monday: date, entries: list[DatepickerEntry]) -> ResolveResult:
    """Resolve a draw dated inside the ISO week, else the next entry after Monday."""
    sunday = monday + timedelta(days=6)
    for entry in entries:
        if monday <= entry.date <= sunday:
            return ResolveResult(
                draw_number=entry.draw_number,
                exact_match=True,
                match_date=entry.date,
            )
    for entry in entries:
        if entry.date >= monday:
            return ResolveResult(
                draw_number=entry.draw_number,
                exact_match=False,
                match_date=entry.date,
            )
    return ResolveResult(draw_number=0, exact_match=False, match_date=None)


def week_monday(week_str: str) -> date:
    """Return the Monday of the ISO week described by ``week_str`` (YYYY.WW)."""
    year, week = parse_week_value(week_str)
    return date.fromisocalendar(year, week, 1)


def parse_week_value(value: str) -> tuple[int, int]:
    parts = value.split(".")
    if len(parts) not in (2, 3) or not all(p.isdigit() for p in parts):  # noqa: PLR2004
        raise ValueError(f"Invalid week: {value}")
    year, week, *draw = (int(p) for p in parts)
    if draw and draw[0] < 1:
        raise ValueError(f"Invalid week: {value}")
    try:
        date.fromisocalendar(year, week, 1)
    except ValueError:
        raise ValueError(f"Invalid week: {value}") from None
    return year, week
