"""Inclusive Period collection over injected dependencies.

The public service is ``collect_period``: given inclusive start and end draw
numbers and a ``Dependencies`` object, it returns the ``Draw``s in that Period.
It never reaches for the concrete API, clock, or output stream, and this module
does not import the CLI.
"""

from stryktips.api import DrawNotFoundError
from stryktips.dependencies import Dependencies, Diagnostic
from stryktips.models import Draw
from stryktips.months import MAX_SCAN_MONTHS, advance_month


def collect_period(start: int, end: int, dependencies: Dependencies) -> list[Draw]:
    """Collect every Draw in the inclusive ``[start, end]`` Period.

    A single-draw Period fetches only that Draw. A spanning Period walks the
    datepicker by month, skips Draws that return not-found (reported through
    ``dependencies.diagnostic``), and warns when the end is not reached within
    the scan window. A missing anchor yields an empty Period.
    """
    try:
        anchor = dependencies.fetch_draw(start)
    except DrawNotFoundError:
        return []
    draws = [anchor]
    if start != end:
        draws.extend(_interior_draws(start, end, _draw_month(anchor), dependencies))
    return draws


def _interior_draws(
    start: int, end: int, anchor_month: tuple[int, int], dependencies: Dependencies
) -> list[Draw]:
    """Fetch the non-anchor draws in [start, end], skipping draws that fail."""
    draws: list[Draw] = []
    seen = {start}
    for number in _draw_numbers_in_range(start, end, anchor_month, dependencies):
        if number not in seen:
            try:
                draws.append(dependencies.fetch_draw(number))
                seen.add(number)
            except DrawNotFoundError:
                _warn_skipped_draw(number, dependencies.diagnostic)
    return draws


def _draw_month(draw: Draw) -> tuple[int, int]:
    """Return the (year, month) of a draw's registration close time."""
    if draw.reg_close_time is None:
        raise ValueError(f"Draw {draw.draw_number} has no close time")
    return draw.reg_close_time.year, draw.reg_close_time.month


def _draw_numbers_in_range(
    start: int, end: int, anchor_month: tuple[int, int], dependencies: Dependencies
) -> list[int]:
    """Walk the datepicker month-by-month, collecting draw numbers in [start, end]."""
    numbers: list[int] = []
    year, month = anchor_month
    for _ in range(MAX_SCAN_MONTHS):
        entries = dependencies.fetch_month_entries(year, month)
        numbers.extend(
            entry.draw_number for entry in entries if start <= entry.draw_number <= end
        )
        if any(entry.draw_number >= end for entry in entries):
            break
        year, month = advance_month(year, month)
    else:
        _warn_truncated_range(start, end, dependencies.diagnostic)
    return numbers


def _warn_truncated_range(start: int, end: int, diagnostic: Diagnostic) -> None:
    """Warn that the end draw was not reached, so the report may be truncated."""
    diagnostic(
        f"Warning: could not reach draw {end} within {MAX_SCAN_MONTHS} months"
        f" of {start}, report may be truncated."
    )


def _warn_skipped_draw(number: int, diagnostic: Diagnostic) -> None:
    """Print a warning that a draw could not be fetched and was skipped."""
    diagnostic(f"Warning: could not fetch draw {number}, skipping.")
