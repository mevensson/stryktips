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
    resolve_draw_by_date,
    resolve_draw_by_week,
    week_draw_index,
    week_monday,
)

MAX_SCAN_MONTHS = 12
MONTHS_IN_YEAR = 12


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
    return _forward_scan(
        monday,
        lambda entries: resolve_draw_by_week(monday, entries, n),
        week_str,
    )


def _forward_scan(  # noqa: PLR0915
    anchor: date,
    resolve: Callable[[list[DatepickerEntry]], ResolveResult],
    display_str: str,
) -> Draw:
    all_entries: list[DatepickerEntry] = []
    year, month = anchor.year, anchor.month

    for _ in range(MAX_SCAN_MONTHS):
        all_entries.extend(fetch_draws_by_month(year, month))
        result = resolve(all_entries)
        if result.draw_number != 0:
            if not result.exact_match:
                print(  # noqa: T201
                    f"Note: No draw found for {display_str},"
                    f" using {result.match_date} (draw {result.draw_number})",
                    file=sys.stderr,
                )
            return fetch_draw(result.draw_number)
        month += 1
        if month > MONTHS_IN_YEAR:
            month = 1
            year += 1

    raise DrawNotFound(display_str)
