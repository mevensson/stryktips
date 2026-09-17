"""Draw, date, and week bound resolution over injected dependencies.

The public service is ``resolve_draw`` (forward date/week resolution and the
single-Draw CLI path) and ``resolve_end`` (the report end policy). Both take a
typed selector and a ``Dependencies`` object; they never reach for the concrete
API, clock, or output stream, and this module does not import the CLI.
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import cast

from stryktips.dependencies import Dependencies, Diagnostic
from stryktips.models import DatepickerEntry
from stryktips.months import MAX_SCAN_MONTHS, advance_month, previous_month
from stryktips.resolver import (
    DrawNotFound,
    ResolveResult,
    WeekDrawIndexError,
    entries_in_week,
    parse_week,
    resolve_draw_by_date,
    resolve_draw_by_week,
    week_monday,
)

_INDEXED_WEEK_DOTS = 2


@dataclass(frozen=True)
class DrawByNumber:
    """Selector for an explicit draw number."""

    number: int


@dataclass(frozen=True)
class DrawByDate:
    """Selector for a calendar date (YYYY-MM-DD)."""

    value: str


@dataclass(frozen=True)
class DrawByWeek:
    """Selector for an ISO week (YYYY.WW[.N]).

    ``value`` is the single constructor input and keeps the original spelling
    for diagnostics; ``year``, ``week``, and ``index`` are derived from it.
    ``index`` is ``None`` when the text omitted ``.N``, so the report end policy
    can tell an unindexed week apart from an explicit ``.1``. An invalid value
    raises ``ValueError`` before any resolution happens.
    """

    value: str
    year: int = field(init=False)
    week: int = field(init=False)
    index: int | None = field(init=False)

    def __post_init__(self) -> None:
        year, week, index = parse_week(self.value)
        has_index = self.value.count(".") == _INDEXED_WEEK_DOTS
        object.__setattr__(self, "year", year)
        object.__setattr__(self, "week", week)
        object.__setattr__(self, "index", index if has_index else None)


DrawSelector = DrawByNumber | DrawByDate | DrawByWeek


def resolve_draw(selector: DrawSelector, dependencies: Dependencies) -> int:
    """Resolve a forward draw, date, or week selector to a draw number.

    Serves both the single-Draw CLI path and the report start bound. The
    report's end bound has its own policy in ``resolve_end``.
    """
    if isinstance(selector, DrawByNumber):
        return selector.number
    if isinstance(selector, DrawByDate):
        result = _resolve_draw_by_date(selector.value, dependencies)
    else:
        result = _resolve_draw_by_week(selector.value, dependencies)
    return _require_draw_number(result)


def resolve_end(selector: DrawSelector | None, dependencies: Dependencies) -> int:
    """Resolve a report end selector to a draw number.

    A ``DrawByWeek`` with no index is clamped to its ISO Sunday; an explicit
    index follows the current/completed/future week policy. ``None`` (no end
    selector given) resolves the latest draw on or before
    ``dependencies.clock()``. The CLI's date-before-week-before-draw flag
    precedence lives in ``_end_selector``, which builds the single selector.
    """
    if selector is None:
        return _resolve_default_end(dependencies.clock(), dependencies)
    if isinstance(selector, DrawByDate):
        bound = min(_parse_date(selector.value), dependencies.clock())
        return _resolve_default_end(bound, dependencies)
    if isinstance(selector, DrawByWeek):
        return _resolve_end_week(selector, dependencies)
    return selector.number


def _resolve_draw_by_date(date_str: str, dependencies: Dependencies) -> ResolveResult:
    target = _parse_date(date_str)
    return _forward_scan(
        target,
        lambda entries: resolve_draw_by_date(target, entries),
        date_str,
        dependencies,
    )


def _parse_date(date_str: str) -> date:
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        raise ValueError(f"Invalid date: {date_str}") from None


def _resolve_draw_by_week(week_str: str, dependencies: Dependencies) -> ResolveResult:
    """Resolve a draw from an ISO week string (YYYY.WW[.N]).

    Every month the week spans (Monday's through Sunday's) is gathered before
    the index is selected, so a draw listed only in the week's later month
    still participates. An empty week still forward-scans for the next draw,
    and an index exceeding the gathered in-week draws raises.
    """
    year, week, draw_index = parse_week(week_str)
    monday = date.fromisocalendar(year, week, 1)
    sunday = monday + timedelta(days=6)
    for entries, week_months_collected in _week_month_scan(
        monday, sunday, dependencies
    ):
        result = _resolve_week_scan_step(
            monday, entries, draw_index, week_months_collected
        )
        if result is not None:
            _print_fallback_note(result, week_str, dependencies.diagnostic)
            return result
    raise DrawNotFound(week_str)


def _week_month_scan(
    monday: date, sunday: date, dependencies: Dependencies
) -> Iterator[tuple[list[DatepickerEntry], bool]]:
    """Yield accumulated entries month-by-month from Monday's month.

    Each yield carries every entry gathered so far and whether the week's final
    month (Sunday's) has been reached, so a caller can defer week selection
    until both cross-month responses are present. Yields at most
    ``MAX_SCAN_MONTHS`` times, letting an empty week keep scanning forward.
    """
    entries: list[DatepickerEntry] = []
    year, month = monday.year, monday.month
    for _ in range(MAX_SCAN_MONTHS):
        entries.extend(dependencies.fetch_month_entries(year, month))
        week_months_collected = (year, month) >= (sunday.year, sunday.month)
        yield entries, week_months_collected
        year, month = advance_month(year, month)


def _resolve_week_scan_step(
    monday: date,
    entries: list[DatepickerEntry],
    draw_index: int,
    week_months_collected: bool,
) -> ResolveResult | None:
    """Try one forward-scan step, deferring until the whole week is gathered."""
    try:
        result = resolve_draw_by_week(monday, entries, draw_index)
    except WeekDrawIndexError as exc:
        if week_months_collected:
            raise ValueError(_week_draw_index_message(exc)) from None
        return None
    if week_months_collected and result.draw_number is not None:
        return result
    return None


def _week_draw_index_message(exc: WeekDrawIndexError) -> str:
    options = " or ".join(
        f"--week {exc.week_label}.{i}" for i in range(1, exc.count + 1)
    )
    return f"Error: {exc} Use {options}."


def _forward_scan(
    anchor: date,
    resolve: Callable[[list[DatepickerEntry]], ResolveResult],
    display_str: str,
    dependencies: Dependencies,
) -> ResolveResult:
    all_entries: list[DatepickerEntry] = []
    year, month = anchor.year, anchor.month

    for _ in range(MAX_SCAN_MONTHS):
        all_entries.extend(dependencies.fetch_month_entries(year, month))
        result = resolve(all_entries)
        if result.draw_number is not None:
            _print_fallback_note(result, display_str, dependencies.diagnostic)
            return result
        year, month = advance_month(year, month)

    raise DrawNotFound(display_str)


def _resolve_end_week(selector: DrawByWeek, dependencies: Dependencies) -> int:
    """Resolve an --end-week, indexed or not, to a draw number."""
    if selector.index is None:
        sunday = week_monday(selector.value) + timedelta(days=6)
        return _resolve_default_end(min(sunday, dependencies.clock()), dependencies)
    return _resolve_indexed_end_week(selector, dependencies)


@dataclass(frozen=True)
class _WeekContext:
    """Resolved ISO-week boundaries and index for the report end policy."""

    draw_index: int
    monday: date
    sunday: date
    today: date


def _resolve_indexed_end_week(selector: DrawByWeek, dependencies: Dependencies) -> int:
    """Resolve an indexed --end-week according to which part of the week it is.

    A week containing today uses the current-week policy; a wholly future week
    clamps to the latest draw on or before today without a lookup into the
    unpublished future; a wholly past week keeps the completed-week fallback
    behaviour. The index is validated by ``parse_week`` before dispatch.
    """
    monday = date.fromisocalendar(selector.year, selector.week, 1)
    context = _WeekContext(
        draw_index=cast(int, selector.index),
        monday=monday,
        sunday=monday + timedelta(days=6),
        today=dependencies.clock(),
    )
    if context.monday <= context.today <= context.sunday:
        return _resolve_current_week_indexed_end(context, dependencies)
    if context.monday > context.today:
        return _resolve_default_end(context.today, dependencies)
    return _resolve_completed_indexed_end_week(selector, context, dependencies)


def _resolve_current_week_indexed_end(
    context: _WeekContext, dependencies: Dependencies
) -> int:
    """Resolve an indexed --end-week that falls within the current ISO week.

    The index is honored only when its draw is dated on or before today, even
    if a later draw in the same week is also available. A later or
    unavailable index, or a week holding no draws yet, clamps to the latest
    draw on or before today without an index warning.
    """
    entries = _entries_from_month_to_month(context.monday, context.today, dependencies)
    try:
        result = resolve_draw_by_week(context.monday, entries, context.draw_index)
    except WeekDrawIndexError:
        return _latest_draw_number_on_or_before(context.today, entries, dependencies)
    if result.match_date is not None and result.match_date <= context.today:
        return _require_draw_number(result)
    return _latest_draw_number_on_or_before(context.today, entries, dependencies)


def _resolve_completed_indexed_end_week(
    selector: DrawByWeek,
    context: _WeekContext,
    dependencies: Dependencies,
) -> int:
    """Resolve an indexed --end-week for a week that has already completed.

    Reached only when the week's Sunday is before today. Every month the week
    spans (Monday's through Sunday's) is gathered before the index is selected,
    so a draw listed only in the week's later month still participates. When the
    requested index exceeds the draws held by the week, the week's final draw is
    used and a warning is printed; a week holding no draws at all falls back to
    the latest draw before the week and warns.
    """
    for entries, week_months_collected in _week_month_scan(
        context.monday, context.sunday, dependencies
    ):
        if week_months_collected:
            return _select_completed_end_week(selector, context, entries, dependencies)
    raise DrawNotFound(selector.value)


def _select_completed_end_week(
    selector: DrawByWeek,
    context: _WeekContext,
    entries: list[DatepickerEntry],
    dependencies: Dependencies,
) -> int:
    """Select the index or fallback once the completed week's months are gathered."""
    if not entries_in_week(context.monday, entries):
        return _warn_empty_end_week(selector.value, context.monday, dependencies)
    try:
        result = resolve_draw_by_week(context.monday, entries, context.draw_index)
    except WeekDrawIndexError:
        return _warn_excessive_end_week(
            selector.value, context.monday, entries, dependencies
        )
    _print_fallback_note(result, selector.value, dependencies.diagnostic)
    return _require_draw_number(result)


def _entries_from_month_to_month(
    start: date, end: date, dependencies: Dependencies
) -> list[DatepickerEntry]:
    """Fetch every month from ``start`` through ``end``, newest month first."""
    entries: list[DatepickerEntry] = []
    year, month = end.year, end.month
    while (year, month) >= (start.year, start.month):
        entries.extend(dependencies.fetch_month_entries(year, month))
        year, month = previous_month(year, month)
    return entries


def _latest_draw_number_on_or_before(
    today: date, entries: list[DatepickerEntry], dependencies: Dependencies
) -> int:
    """Return the latest entry on or before today, scanning back if needed."""
    latest = max(
        (entry for entry in entries if entry.date <= today),
        key=lambda entry: entry.date,
        default=None,
    )
    if latest is not None:
        return latest.draw_number
    return _resolve_default_end(today, dependencies)


def _warn_empty_end_week(
    week_str: str, monday: date, dependencies: Dependencies
) -> int:
    """Warn that an indexed --end-week holds no draws and return the preceding draw."""
    preceding = _latest_entry_on_or_before(monday - timedelta(days=1), dependencies)
    dependencies.diagnostic(
        f"Warning: --end-week {week_str} has no draws;"
        f" using preceding draw {preceding.draw_number}"
        f" ({preceding.date.isoformat()})."
    )
    return preceding.draw_number


def _warn_excessive_end_week(
    week_str: str,
    monday: date,
    entries: list[DatepickerEntry],
    dependencies: Dependencies,
) -> int:
    """Warn that an --end-week index overran and return the week's final draw."""
    final = _final_week_draw(monday, entries)
    dependencies.diagnostic(
        f"Warning: --end-week {week_str} exceeds the draws in the week;"
        f" using final draw {final.draw_number} ({final.date.isoformat()})."
    )
    return final.draw_number


def _final_week_draw(monday: date, entries: list[DatepickerEntry]) -> DatepickerEntry:
    """Return the last distinct draw dated within the ISO week starting on ``monday``.

    Shares ``entries_in_week`` so the fallback draw is exactly the last draw the
    index counted, regardless of duplicate or unsorted datepicker responses.
    """
    return entries_in_week(monday, entries)[-1]


def _resolve_default_end(today: date, dependencies: Dependencies) -> int:
    """Return the draw number of the most recent draw on or before today."""
    return _latest_entry_on_or_before(today, dependencies).draw_number


def _latest_entry_on_or_before(
    limit: date, dependencies: Dependencies
) -> DatepickerEntry:
    """Return the most recent datepicker entry dated on or before ``limit``.

    Searches backward month-by-month for up to ``MAX_SCAN_MONTHS``, raising
    ``DrawNotFound`` when no entry exists within the scan window.
    """
    year, month = limit.year, limit.month
    for _ in range(MAX_SCAN_MONTHS):
        entries = [
            entry
            for entry in dependencies.fetch_month_entries(year, month)
            if entry.date <= limit
        ]
        if entries:
            return max(entries, key=lambda entry: entry.date)
        year, month = previous_month(year, month)
    raise DrawNotFound(limit.isoformat())


def _require_draw_number(result: ResolveResult) -> int:
    """Return the resolved draw number, raising if resolution produced none."""
    if result.draw_number is None:
        raise ValueError("Resolved draw has no draw number")
    return result.draw_number


def _print_fallback_note(
    result: ResolveResult, display_str: str, diagnostic: Diagnostic
) -> None:
    """Report that resolution fell back to the next draw."""
    if result.exact_match:
        return
    diagnostic(
        f"Note: No draw found for {display_str},"
        f" using {result.match_date} (draw {result.draw_number})"
    )
