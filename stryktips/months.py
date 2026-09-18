"""Month arithmetic and scan-window constants shared by the services.

Bound resolution and Period collection both walk the calendar month-by-month
and stop after the same bounded scan window, so the arithmetic and the limit
live here rather than in either service.
"""

MONTHS_IN_YEAR = 12
MAX_SCAN_MONTHS = 12


def advance_month(year: int, month: int) -> tuple[int, int]:
    """Advance to the next month, rolling the year over after December."""
    month += 1
    if month > MONTHS_IN_YEAR:
        month = 1
        year += 1
    return year, month


def previous_month(year: int, month: int) -> tuple[int, int]:
    """Step to the previous month, rolling the year back after January."""
    month -= 1
    if month < 1:
        month = MONTHS_IN_YEAR
        year -= 1
    return year, month
