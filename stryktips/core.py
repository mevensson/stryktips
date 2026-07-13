import argparse
import sys
from datetime import date

from stryktips.api import fetch_draw, fetch_draws_by_month
from stryktips.display import format_header, format_matches
from stryktips.models import DatepickerEntry, Draw
from stryktips.resolver import resolve_draw_number


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    try:
        draw = _fetch_draw_from_args(args)
    except ValueError as e:
        print(e)  # noqa: T201
        return 1

    _display(draw)
    return 0


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
    return parser


def _fetch_draw_from_args(args: argparse.Namespace) -> Draw:
    if args.date is not None:
        return _resolve_draw_by_date(args.date)
    return fetch_draw(args.draw)


def _display(draw: Draw) -> None:
    header = format_header(draw)
    lines = format_matches(draw.matches)
    joined = "\n".join([header, *lines])
    print(joined)  # noqa: T201


MAX_SCAN_MONTHS = 12


def _parse_date(date_str: str) -> date:
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        raise ValueError(f"Invalid date: {date_str}") from None


def _resolve_draw_by_date(date_str: str) -> Draw:  # noqa: PLR0915
    target = _parse_date(date_str)

    all_entries: list[DatepickerEntry] = []
    year, month = target.year, target.month

    for _ in range(MAX_SCAN_MONTHS):
        all_entries.extend(fetch_draws_by_month(year, month))
        result = resolve_draw_number(target, "date", all_entries)
        if result.draw_number != 0:
            print(  # noqa: T201
                f"Note: No draw found for {date_str},"
                f" using {result.match_date} (draw {result.draw_number})",
                file=sys.stderr,
            )
            return fetch_draw(result.draw_number)
        month += 1
        if month > MAX_SCAN_MONTHS:
            month = 1
            year += 1

    raise ValueError(f"No draw found for {date_str}")
