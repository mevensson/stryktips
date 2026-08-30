import argparse
import sys
from collections.abc import Callable
from datetime import date

from requests import RequestException

from stryktips.api import fetch_draw, fetch_draws_by_month
from stryktips.display import format_header, format_matches
from stryktips.models import DatepickerEntry, Draw
from stryktips.resolver import (
    DrawNotFound,
    ResolveResult,
    WeekDrawIndexError,
    resolve_draw_by_date,
    resolve_draw_by_week,
    week_draw_index,
    week_monday,
)

MONTHS_IN_YEAR = 12
MAX_SCAN_MONTHS = MONTHS_IN_YEAR


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    try:
        draw = _fetch_draw_from_args(args)
    except DrawNotFound as e:
        return _report_draw_not_found(e)
    except (ValueError, RequestException) as e:
        return _report_error(e)

    _display(draw)
    return 0


def _report_draw_not_found(exc: DrawNotFound) -> int:
    print(  # noqa: T201
        f"No draw found within {MAX_SCAN_MONTHS} months of {exc.value}",
        file=sys.stderr,
    )
    return 1


def _report_error(error: Exception) -> int:
    print(error, file=sys.stderr)  # noqa: T201
    return 1


def create_parser() -> argparse.ArgumentParser:
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
        "--start",
        type=int,
        help="Start draw number for the prediction-quality report",
    )
    group.add_argument(
        "--end",
        type=int,
        help="End draw number for the prediction-quality report",
    )
    return parser


def _parse_week(value: str) -> str:
    try:
        week_monday(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None
    return value


def _fetch_draw_from_args(args: argparse.Namespace) -> Draw:
    if args.date is not None:
        return _resolve_draw_by_date(args.date)
    if args.week is not None:
        return _resolve_draw_by_week(args.week)
    if args.draw is None:
        raise ValueError(
            "The prediction-quality report (--start/--end) is not yet implemented"
        )
    return fetch_draw(args.draw)


def _display(draw: Draw) -> None:
    header = format_header(draw)
    lines = format_matches(draw.matches)
    joined = "\n".join([header, *lines])
    print(joined)  # noqa: T201


def _resolve_draw_by_date(date_str: str) -> Draw:
    try:
        target = date.fromisoformat(date_str)
    except ValueError:
        raise ValueError(f"Invalid date: {date_str}") from None

    return _forward_scan(
        target,
        lambda entries: resolve_draw_by_date(target, entries),
        date_str,
    )


def _resolve_draw_by_week(week_str: str) -> Draw:
    """Resolve a draw from an ISO week string (YYYY.WW[.N])."""
    monday = week_monday(week_str)
    n = week_draw_index(week_str)
    try:
        return _forward_scan(
            monday,
            lambda entries: resolve_draw_by_week(monday, entries, n),
            week_str,
        )
    except WeekDrawIndexError as exc:
        raise ValueError(_week_draw_index_message(exc)) from None


def _week_draw_index_message(exc: WeekDrawIndexError) -> str:
    options = " or ".join(
        f"--week {exc.week_label}.{i}" for i in range(1, exc.count + 1)
    )
    return f"Error: {exc} Use {options}."


def _forward_scan(
    anchor: date,
    resolve: Callable[[list[DatepickerEntry]], ResolveResult],
    display_str: str,
) -> Draw:
    all_entries: list[DatepickerEntry] = []
    year, month = anchor.year, anchor.month

    for _ in range(MAX_SCAN_MONTHS):
        all_entries.extend(fetch_draws_by_month(year, month))
        result = resolve(all_entries)
        if result.draw_number is not None:
            _print_fallback_note(result, display_str)
            return fetch_draw(result.draw_number)
        year, month = _advance_month(year, month)

    raise DrawNotFound(display_str)


def _advance_month(year: int, month: int) -> tuple[int, int]:
    """Advance to the next month, rolling the year over after December."""
    month += 1
    if month > MONTHS_IN_YEAR:
        month = 1
        year += 1
    return year, month


def _print_fallback_note(result: ResolveResult, display_str: str) -> None:
    """Print a note to stderr when resolution fell back to the next draw."""
    if result.exact_match:
        return
    print(  # noqa: T201
        f"Note: No draw found for {display_str},"
        f" using {result.match_date} (draw {result.draw_number})",
        file=sys.stderr,
    )
