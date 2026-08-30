"""Draw number resolution from CLI arguments."""

from datetime import date, timedelta
from typing import NamedTuple

from stryktips.models import DatepickerEntry

_WEEK_PARTS = 2
_WEEK_PARTS_WITH_INDEX = 3


class ResolveResult(NamedTuple):
    draw_number: int | None
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
    result = _first_on_or_after(target, entries)
    if result is None:
        return _not_found()
    return result


def resolve_draw_by_week(
    monday: date, entries: list[DatepickerEntry], n: int = 1
) -> ResolveResult:
    """Resolve the N-th draw dated inside the ISO week, else the next after Monday."""
    if n < 1:
        raise ValueError("Draw number must be a positive integer")
    sunday = monday + timedelta(days=6)
    in_week = sorted(
        (e for e in entries if monday <= e.date <= sunday), key=lambda e: e.date
    )
    if in_week:
        if n > len(in_week):
            raise WeekDrawIndexError(monday, in_week)
        nth = in_week[n - 1]
        return ResolveResult(
            draw_number=nth.draw_number,
            exact_match=True,
            match_date=nth.date,
        )
    result = _first_on_or_after(monday, entries)
    return result if result is not None else _not_found()


class WeekDrawIndexError(ValueError):
    """Raised when the draw index ``.N`` exceeds the draws in an ISO week.

    Carries the ISO week label, draw count, and draw dates so the CLI layer
    can format a user-facing message.
    """

    def __init__(self, monday: date, in_week: list[DatepickerEntry]) -> None:
        iso = monday.isocalendar()
        self.week_label = f"{iso.year}.{iso.week}"
        self.count = len(in_week)
        self.dates = ", ".join(e.date.isoformat() for e in in_week)
        super().__init__(
            f"Week {self.week_label} has {self.count} draws (dates: {self.dates})."
        )


def _first_on_or_after(
    target: date, entries: list[DatepickerEntry]
) -> ResolveResult | None:
    """Return the first entry on or after ``target``, or None if there is none."""
    for entry in entries:
        if entry.date >= target:
            return ResolveResult(
                draw_number=entry.draw_number,
                exact_match=(entry.date == target),
                match_date=entry.date,
            )
    return None


def _not_found() -> ResolveResult:
    """Return the ResolveResult shape used when no entry satisfies the query."""
    return ResolveResult(draw_number=None, exact_match=False, match_date=None)


def week_monday(week_str: str) -> date:
    """Return the Monday of the ISO week described by ``week_str`` (YYYY.WW)."""
    year, week = parse_week_value(week_str)
    return date.fromisocalendar(year, week, 1)


def week_draw_index(week_str: str) -> int:
    """Return the draw index from ``week_str`` (YYYY.WW[.N]), defaulting to 1.

    ``parse_week_value`` has already validated that any trailing ``.N`` suffix
    is a positive integer, so its presence can be relied on here.
    """
    parts = week_str.split(".")
    if len(parts) == _WEEK_PARTS_WITH_INDEX:
        return int(parts[2])
    return 1


def parse_week_value(value: str) -> tuple[int, int]:
    parts = value.split(".")
    if len(parts) not in (_WEEK_PARTS, _WEEK_PARTS_WITH_INDEX) or not all(
        p.isdigit() for p in parts
    ):
        raise ValueError(f"Invalid week: {value}")
    year, week, *draw = (int(p) for p in parts)
    if draw and draw[0] < 1:
        raise ValueError(f"Invalid week: {value}")
    try:
        date.fromisocalendar(year, week, 1)
    except ValueError:
        raise ValueError(f"Invalid week: {value}") from None
    return year, week
