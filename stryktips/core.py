import argparse
import sys
from collections.abc import Callable
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
    parse_week,
    resolve_draw_by_date,
    resolve_draw_by_week,
    week_monday,
)

MONTHS_IN_YEAR = 12
MAX_SCAN_MONTHS = 12

_START_BOUND_FLAGS = ("--start-draw", "--start-date", "--start-week")
_END_BOUND_FLAGS = ("--end-draw", "--end-date", "--end-week")


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
        return _run(args)
    except DrawNotFound as e:
        return _report_draw_not_found(e)
    except (ValueError, RequestException) as e:
        return _report_error(e)


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


def _run(args: argparse.Namespace) -> int:
    if _display_report_if_start(args):
        return 0
    draw = _fetch_draw_from_args(args)
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


def _parse_week(value: str) -> str:
    try:
        week_monday(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None
    return value


def _display_report_if_start(args: argparse.Namespace) -> bool:
    if not _has_start_bound(args):
        return False
    start = _resolve_start_bound(args)
    end = _resolve_end_bound(args)
    if start > end:
        if _has_end_bound(args):
            raise ValueError(
                f"--start bound resolved to draw {start}, which must not be"
                f" greater than --end bound (draw {end})"
            )
        _display_report([])
        return True
    _display_report(_fetch_report_draws(start, end))
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


def _resolve_start_bound(args: argparse.Namespace) -> int:
    resolved = _resolve_date_or_week_bound(
        cast(str | None, args.start_date), cast(str | None, args.start_week)
    )
    if resolved is not None:
        return resolved
    return cast(int, args.start_draw)


def _resolve_end_bound(args: argparse.Namespace) -> int:
    resolved = _resolve_date_or_week_bound(
        cast(str | None, args.end_date), cast(str | None, args.end_week)
    )
    if resolved is not None:
        return resolved
    end_draw = cast(int | None, args.end_draw)
    if end_draw is not None:
        return end_draw
    return _resolve_default_end(date.today())


def _resolve_date_or_week_bound(
    date_str: str | None, week_str: str | None
) -> int | None:
    """Resolve an explicit --*-date or --*-week bound to a draw number, if given."""
    if date_str is not None:
        return _require_draw_number(_resolve_draw_by_date(date_str))
    if week_str is not None:
        return _require_draw_number(_resolve_draw_by_week(week_str))
    return None


def _fetch_report_draws(start: int, end: int) -> list[Draw]:
    """Fetch every draw in [start, end] by walking the datepicker month-by-month."""
    try:
        anchor = fetch_draw(start)
    except DrawNotFoundError:
        return []
    draws = [anchor]
    if start != end:
        draws.extend(_interior_draws(start, end, _draw_month(anchor)))
    return draws


def _interior_draws(start: int, end: int, anchor_month: tuple[int, int]) -> list[Draw]:
    """Fetch the non-anchor draws in [start, end], skipping draws that fail."""
    draws: list[Draw] = []
    seen = {start}
    for number in _draw_numbers_in_range(start, end, anchor_month):
        if number not in seen:
            try:
                draws.append(fetch_draw(number))
                seen.add(number)
            except DrawNotFoundError:
                _warn_skipped_draw(number)
    return draws


def _draw_month(draw: Draw) -> tuple[int, int]:
    """Return the (year, month) of a draw's registration close time."""
    if draw.reg_close_time is None:
        raise ValueError(f"Draw {draw.draw_number} has no close time")
    return draw.reg_close_time.year, draw.reg_close_time.month


def _display_report(draws: list[Draw]) -> None:
    print(format_aggregate_report(draws))  # noqa: T201


def _resolve_default_end(today: date) -> int:
    """Return the draw number of the most recent draw on or before today."""
    year, month = today.year, today.month
    for _ in range(MAX_SCAN_MONTHS):
        entries = [
            entry for entry in fetch_draws_by_month(year, month) if entry.date <= today
        ]
        if entries:
            return max(entries, key=lambda entry: entry.date).draw_number
        year, month = _previous_month(year, month)
    raise DrawNotFound(today.isoformat())


def _fetch_draw_from_args(args: argparse.Namespace) -> Draw:
    if args.date is not None:
        return fetch_draw(_require_draw_number(_resolve_draw_by_date(args.date)))
    if args.week is not None:
        return fetch_draw(_require_draw_number(_resolve_draw_by_week(args.week)))
    return fetch_draw(args.draw)


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


def _resolve_draw_by_date(date_str: str) -> ResolveResult:
    try:
        target = date.fromisoformat(date_str)
    except ValueError:
        raise ValueError(f"Invalid date: {date_str}") from None

    return _forward_scan(
        target,
        lambda entries: resolve_draw_by_date(target, entries),
        date_str,
    )


def _resolve_draw_by_week(week_str: str) -> ResolveResult:  # noqa: PLR0915
    """Resolve a draw from an ISO week string (YYYY.WW[.N])."""
    year, week, n = parse_week(week_str)
    monday = date.fromisocalendar(year, week, 1)
    sunday = monday + timedelta(days=6)
    all_entries: list[DatepickerEntry] = []
    scan_year, scan_month = monday.year, monday.month

    for _ in range(MAX_SCAN_MONTHS):
        all_entries.extend(fetch_draws_by_month(scan_year, scan_month))
        try:
            result = resolve_draw_by_week(monday, all_entries, n)
        except WeekDrawIndexError as exc:
            if (scan_year, scan_month) >= (sunday.year, sunday.month):
                raise ValueError(_week_draw_index_message(exc)) from None
        else:
            if result.draw_number is not None:
                _print_fallback_note(result, week_str)
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
) -> ResolveResult:
    all_entries: list[DatepickerEntry] = []
    year, month = anchor.year, anchor.month

    for _ in range(MAX_SCAN_MONTHS):
        all_entries.extend(fetch_draws_by_month(year, month))
        result = resolve(all_entries)
        if result.draw_number is not None:
            _print_fallback_note(result, display_str)
            return result
        year, month = _advance_month(year, month)

    raise DrawNotFound(display_str)


def _draw_numbers_in_range(
    start: int, end: int, anchor_month: tuple[int, int]
) -> list[int]:
    """Walk the datepicker month-by-month, collecting draw numbers in [start, end]."""
    numbers: list[int] = []
    year, month = anchor_month
    for _ in range(MAX_SCAN_MONTHS):
        entries = fetch_draws_by_month(year, month)
        numbers.extend(
            entry.draw_number for entry in entries if start <= entry.draw_number <= end
        )
        if any(entry.draw_number >= end for entry in entries):
            break
        year, month = _advance_month(year, month)
    else:
        _warn_truncated_range(start, end)
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


def _warn_truncated_range(start: int, end: int) -> None:
    """Warn that the end draw was not reached, so the report may be truncated."""
    print(  # noqa: T201
        f"Warning: could not reach draw {end} within {MAX_SCAN_MONTHS} months"
        f" of {start}, report may be truncated.",
        file=sys.stderr,
    )


def _warn_skipped_draw(number: int) -> None:
    """Print a warning that a draw could not be fetched and was skipped."""
    print(  # noqa: T201
        f"Warning: could not fetch draw {number}, skipping.",
        file=sys.stderr,
    )


def _print_fallback_note(result: ResolveResult, display_str: str) -> None:
    """Print a note to stderr when resolution fell back to the next draw."""
    if result.exact_match:
        return
    print(  # noqa: T201
        f"Note: No draw found for {display_str},"
        f" using {result.match_date} (draw {result.draw_number})",
        file=sys.stderr,
    )
