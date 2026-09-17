import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import cast

from requests import RequestException

from stryktips.api import DrawNotFoundError, fetch_draw, fetch_draws_by_month
from stryktips.display import format_header, format_matches
from stryktips.models import DatepickerEntry, Draw
from stryktips.report import format_aggregate_report
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

MONTHS_IN_YEAR = 12
MAX_SCAN_MONTHS = 12

_START_BOUND_FLAGS = ("--start-draw", "--start-date", "--start-week")
_END_BOUND_FLAGS = ("--end-draw", "--end-date", "--end-week")
_INDEXED_WEEK_DOTS = 2

# Narrow I/O seams: fetch one draw, look up a datepicker month, read the clock,
# and report a diagnostic line. ``create_dependencies`` wires the concrete
# production collaborators.
FetchDraw = Callable[[int], Draw]
FetchMonthEntries = Callable[[int, int], list[DatepickerEntry]]
Clock = Callable[[], date]
Diagnostic = Callable[[str], None]


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


@dataclass(frozen=True)
class Dependencies:
    """The injected I/O, clock, and diagnostics for the CLI services.

    ``fetch_draw`` fetches one Draw, ``fetch_month_entries`` looks up a
    datepicker month, ``clock`` supplies today's date, and ``diagnostic``
    receives user-facing warning and fallback lines. Resolution and collection
    never reach for a global network client, clock, or output stream.
    """

    fetch_draw: FetchDraw
    fetch_month_entries: FetchMonthEntries
    clock: Clock
    diagnostic: Diagnostic


def create_dependencies(
    *,
    fetch_draw: FetchDraw | None = None,
    fetch_month_entries: FetchMonthEntries | None = None,
    clock: Clock | None = None,
    diagnostic: Diagnostic | None = None,
) -> Dependencies:
    """Compose the dependencies, applying any overrides.

    ``main`` calls this with no arguments. Any keyword left out falls back to
    the concrete production collaborator, resolved at call time so a caller can
    override exactly the seam it needs.
    """
    return Dependencies(
        fetch_draw=fetch_draw if fetch_draw is not None else _default_fetch_draw(),
        fetch_month_entries=(
            fetch_month_entries
            if fetch_month_entries is not None
            else _default_fetch_month_entries()
        ),
        clock=clock if clock is not None else _default_clock(),
        diagnostic=diagnostic if diagnostic is not None else _diagnostic_to_stderr,
    )


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    if (end_bound := _end_bound_without_start(argv)) is not None:
        parser.error(
            f"{end_bound} requires --start-draw, --start-date, or --start-week"
        )
    args = parser.parse_args(argv)
    _validate_report_args(parser, args)

    try:
        return _run(args, create_dependencies())
    except DrawNotFound as e:
        return _report_draw_not_found(e)
    except (ValueError, RequestException) as e:
        return _report_error(e)


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


def collect_period(start: int, end: int, dependencies: Dependencies) -> list[Draw]:
    """Collect every Draw in the inclusive ``[start, end]`` Period.

    A single-draw Period fetches only that Draw. A spanning Period walks the
    datepicker by month, skips Draws that return not-found (reported through
    ``dependencies.diagnostic``), and warns when the end is not reached within
    the scan window. A missing anchor yields an empty Period.
    """
    return _fetch_report_draws(start, end, dependencies)


def create_parser() -> argparse.ArgumentParser:  # noqa: PLR0915
    """Create and return the argument parser for the stryktips CLI."""
    parser = argparse.ArgumentParser(
        prog="stryktips.py",
        description="Stryktips command line interface.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--draw",
        type=int,
        help="Draw number for Stryktipset data",
    )
    group.add_argument(
        "--date",
        type=str,
        help="Calendar date (YYYY-MM-DD) of the draw",
    )
    group.add_argument(
        "--week",
        type=_parse_week,
        help="ISO week (YYYY.WW[.N]) of the draw",
    )
    group.add_argument(
        "--start-draw",
        type=int,
        help="Start draw number for the prediction-quality report",
    )
    group.add_argument(
        "--start-date",
        type=str,
        help="Calendar date (YYYY-MM-DD) of the report start draw",
    )
    group.add_argument(
        "--start-week",
        type=_parse_week,
        help="ISO week (YYYY.WW[.N]) of the report start draw",
    )
    parser.add_argument(
        "--end-draw",
        type=int,
        help="End draw number for the prediction-quality report",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="Calendar date (YYYY-MM-DD) of the report end draw",
    )
    parser.add_argument(
        "--end-week",
        type=_parse_week,
        help="ISO week (YYYY.WW[.N]) of the report end draw",
    )
    return parser


def _default_fetch_draw() -> FetchDraw:
    """Return the module's concrete draw fetch, resolved at call time."""
    return fetch_draw


def _default_fetch_month_entries() -> FetchMonthEntries:
    """Return the module's concrete month lookup, resolved at call time."""
    return fetch_draws_by_month


def _default_clock() -> Clock:
    """Return the module's date source, resolved at call time."""
    return date.today


def _diagnostic_to_stderr(message: str) -> None:
    """Write a diagnostic message to stderr."""
    print(message, file=sys.stderr)  # noqa: T201


def _end_bound_without_start(argv: list[str] | None) -> str | None:
    """Return the --end-* flag given without any --start-* bound, else None."""
    flags = sys.argv[1:] if argv is None else argv
    normalized = {token.split("=", 1)[0] for token in flags}
    if not any(flag in normalized for flag in _START_BOUND_FLAGS):
        return next((flag for flag in _END_BOUND_FLAGS if flag in normalized), None)
    return None


def _validate_report_args(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> None:
    if (
        args.end_draw is not None
        and args.start_draw is not None
        and args.start_draw > args.end_draw
    ):
        parser.error("--start-draw must not be greater than --end-draw")


def _run(args: argparse.Namespace, dependencies: Dependencies) -> int:
    if _display_report_if_start(args, dependencies):
        return 0
    draw = _fetch_draw_from_args(args, dependencies)
    return _display(draw)


def _report_draw_not_found(exc: DrawNotFound) -> int:
    print(  # noqa: T201
        f"No draw found within {MAX_SCAN_MONTHS} months of {exc.value}",
        file=sys.stderr,
    )
    return 1


def _report_error(exc: Exception) -> int:
    print(exc, file=sys.stderr)  # noqa: T201
    return 1


def _parse_week(value: str) -> str:
    try:
        week_monday(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None
    return value


def _display_report_if_start(
    args: argparse.Namespace, dependencies: Dependencies
) -> bool:
    if not _has_start_bound(args):
        return False
    start = resolve_draw(_start_selector(args), dependencies)
    end = resolve_end(_end_selector(args), dependencies)
    if start > end:
        if _has_end_bound(args):
            raise ValueError(
                f"--start bound resolved to draw {start}, which must not be"
                f" greater than --end bound (draw {end})"
            )
        _display_report([])
        return True
    _display_report(collect_period(start, end, dependencies))
    return True


def _has_start_bound(args: argparse.Namespace) -> bool:
    return (
        args.start_draw is not None
        or args.start_date is not None
        or args.start_week is not None
    )


def _has_end_bound(args: argparse.Namespace) -> bool:
    return (
        args.end_draw is not None
        or args.end_date is not None
        or args.end_week is not None
    )


def _display_selector(args: argparse.Namespace) -> DrawSelector:
    """Build the single-Draw selector from parsed arguments."""
    if args.draw is not None:
        return DrawByNumber(args.draw)
    if args.date is not None:
        return DrawByDate(args.date)
    return DrawByWeek(cast(str, args.week))


def _start_selector(args: argparse.Namespace) -> DrawSelector:
    """Build the report start selector from parsed arguments."""
    if args.start_draw is not None:
        return DrawByNumber(args.start_draw)
    if args.start_date is not None:
        return DrawByDate(args.start_date)
    return DrawByWeek(cast(str, args.start_week))


def _end_selector(args: argparse.Namespace) -> DrawSelector | None:
    """Build the report end selector, honouring date, week, then draw order."""
    if args.end_date is not None:
        return DrawByDate(args.end_date)
    if args.end_week is not None:
        return DrawByWeek(args.end_week)
    if args.end_draw is not None:
        return DrawByNumber(args.end_draw)
    return None


def _resolve_end_week(selector: DrawByWeek, dependencies: Dependencies) -> int:
    """Resolve an --end-week, indexed or not, to a draw number."""
    if selector.index is None:
        sunday = week_monday(selector.value) + timedelta(days=6)
        return _resolve_default_end(min(sunday, dependencies.clock()), dependencies)
    return _resolve_indexed_end_week(selector, dependencies)


@dataclass(frozen=True)
class _WeekContext:
    """Resolved ISO-week boundaries and index for the report end policy."""

    n: int
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
        n=cast(int, selector.index),
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
        result = resolve_draw_by_week(context.monday, entries, context.n)
    except WeekDrawIndexError:
        return _latest_draw_number_on_or_before(context.today, entries, dependencies)
    if result.match_date is not None and result.match_date <= context.today:
        return _require_draw_number(result)
    return _latest_draw_number_on_or_before(context.today, entries, dependencies)


def _resolve_completed_indexed_end_week(  # noqa: PLR0915
    selector: DrawByWeek,
    context: _WeekContext,
    dependencies: Dependencies,
) -> int:
    """Resolve an indexed --end-week for a week that has already completed.

    Every month the week spans (Monday's through Sunday's) is gathered before
    the index is selected, so a draw listed only in the week's later month still
    participates. When the requested index exceeds the draws held by the
    completed week (its Sunday is before today), the week's final draw is used
    and a warning is printed. A completed week holding no draws at all instead
    falls back to the latest draw before the week and warns. Otherwise the
    excessive-index error is raised, as it is for ``--week`` and
    ``--start-week``. A non-positive index is still rejected by
    ``resolve_draw_by_week``.
    """
    all_entries: list[DatepickerEntry] = []
    scan_year, scan_month = context.monday.year, context.monday.month

    for _ in range(MAX_SCAN_MONTHS):
        all_entries.extend(dependencies.fetch_month_entries(scan_year, scan_month))
        relevant_months_collected = (scan_year, scan_month) >= (
            context.sunday.year,
            context.sunday.month,
        )
        if (
            relevant_months_collected
            and context.sunday < context.today
            and not entries_in_week(context.monday, all_entries)
        ):
            return _warn_empty_end_week(selector.value, context.monday, dependencies)
        try:
            result = resolve_draw_by_week(context.monday, all_entries, context.n)
        except WeekDrawIndexError as exc:
            if relevant_months_collected:
                if context.sunday < context.today:
                    return _warn_excessive_end_week(
                        selector.value, context.monday, all_entries, dependencies
                    )
                raise ValueError(_week_draw_index_message(exc)) from None
        else:
            if relevant_months_collected and result.draw_number is not None:
                _print_fallback_note(result, selector.value, dependencies.diagnostic)
                return _require_draw_number(result)
        scan_year, scan_month = _advance_month(scan_year, scan_month)

    raise DrawNotFound(selector.value)


def _entries_from_month_to_month(
    start: date, end: date, dependencies: Dependencies
) -> list[DatepickerEntry]:
    """Fetch every month from ``start`` through ``end``, newest month first."""
    entries: list[DatepickerEntry] = []
    year, month = end.year, end.month
    while (year, month) >= (start.year, start.month):
        entries.extend(dependencies.fetch_month_entries(year, month))
        year, month = _previous_month(year, month)
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


def _fetch_report_draws(start: int, end: int, dependencies: Dependencies) -> list[Draw]:
    """Fetch every draw in [start, end] by walking the datepicker month-by-month."""
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


def _display_report(draws: list[Draw]) -> None:
    print(format_aggregate_report(draws))  # noqa: T201


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
        year, month = _previous_month(year, month)
    raise DrawNotFound(limit.isoformat())


def _fetch_draw_from_args(args: argparse.Namespace, dependencies: Dependencies) -> Draw:
    return dependencies.fetch_draw(resolve_draw(_display_selector(args), dependencies))


def _display(draw: Draw) -> int:
    header = format_header(draw)
    lines = format_matches(draw.matches)
    joined = "\n".join([header, *lines])
    print(joined)  # noqa: T201
    return 0


def _require_draw_number(result: ResolveResult) -> int:
    """Return the resolved draw number, raising if resolution produced none."""
    if result.draw_number is None:
        raise ValueError("Resolved draw has no draw number")
    return result.draw_number


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


def _resolve_draw_by_week(  # noqa: PLR0915
    week_str: str, dependencies: Dependencies
) -> ResolveResult:
    """Resolve a draw from an ISO week string (YYYY.WW[.N]).

    Every month the week spans (Monday's through Sunday's) is gathered before
    the index is selected, so a draw listed only in the week's later month
    still participates. An empty week still forward-scans for the next draw,
    and an index exceeding the gathered in-week draws raises.
    """
    year, week, n = parse_week(week_str)
    monday = date.fromisocalendar(year, week, 1)
    sunday = monday + timedelta(days=6)
    all_entries: list[DatepickerEntry] = []
    scan_year, scan_month = monday.year, monday.month

    for _ in range(MAX_SCAN_MONTHS):
        all_entries.extend(dependencies.fetch_month_entries(scan_year, scan_month))
        relevant_months_collected = (scan_year, scan_month) >= (
            sunday.year,
            sunday.month,
        )
        try:
            result = resolve_draw_by_week(monday, all_entries, n)
        except WeekDrawIndexError as exc:
            if relevant_months_collected:
                raise ValueError(_week_draw_index_message(exc)) from None
        else:
            if relevant_months_collected and result.draw_number is not None:
                _print_fallback_note(result, week_str, dependencies.diagnostic)
                return result
        scan_year, scan_month = _advance_month(scan_year, scan_month)

    raise DrawNotFound(week_str)


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
        year, month = _advance_month(year, month)

    raise DrawNotFound(display_str)


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
        year, month = _advance_month(year, month)
    else:
        _warn_truncated_range(start, end, dependencies.diagnostic)
    return numbers


def _advance_month(year: int, month: int) -> tuple[int, int]:
    """Advance to the next month, rolling the year over after December."""
    month += 1
    if month > MONTHS_IN_YEAR:
        month = 1
        year += 1
    return year, month


def _previous_month(year: int, month: int) -> tuple[int, int]:
    """Step to the previous month, rolling the year back after January."""
    month -= 1
    if month < 1:
        month = MONTHS_IN_YEAR
        year -= 1
    return year, month


def _warn_truncated_range(start: int, end: int, diagnostic: Diagnostic) -> None:
    """Warn that the end draw was not reached, so the report may be truncated."""
    diagnostic(
        f"Warning: could not reach draw {end} within {MAX_SCAN_MONTHS} months"
        f" of {start}, report may be truncated."
    )


def _warn_skipped_draw(number: int, diagnostic: Diagnostic) -> None:
    """Print a warning that a draw could not be fetched and was skipped."""
    diagnostic(f"Warning: could not fetch draw {number}, skipping.")


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
