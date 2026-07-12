"""Draw number resolution from CLI arguments."""

from datetime import date
from typing import NamedTuple

from stryktips.models import DatepickerEntry


class ResolveResult(NamedTuple):
    draw_number: int
    exact_match: bool
    match_date: date | None


def resolve_draw_number(
    value: str | int,
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
        return _resolve_by_date(str(value), datepicker_data)
    msg = f"Unknown arg_type: {arg_type}"
    raise ValueError(msg)


def _resolve_by_date(value: str, entries: list[DatepickerEntry]) -> ResolveResult:
    try:
        target = date.fromisoformat(value)
    except ValueError:
        msg = f"Invalid date: {value}"
        raise ValueError(msg) from None

    for entry in entries:
        if entry.date >= target:
            return ResolveResult(
                draw_number=entry.draw_number,
                exact_match=(entry.date == target),
                match_date=entry.date,
            )

    return ResolveResult(draw_number=0, exact_match=False, match_date=None)
