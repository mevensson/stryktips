import argparse
from datetime import date

from stryktips.api import fetch_draw, fetch_draws_by_month
from stryktips.models import Draw
from stryktips.display import format_header, format_matches
from stryktips.resolver import resolve_draw_number


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


def _resolve_draw_by_date(date_str: str) -> Draw:
    target = date.fromisoformat(date_str)
    entries = fetch_draws_by_month(target.year, target.month)
    result = resolve_draw_number(date_str, "date", entries)
    if result.draw_number == 0:
        msg = f"No draw found for {date_str}"
        raise ValueError(msg)
    return fetch_draw(result.draw_number)


def _display(draw: Draw) -> None:
    header = format_header(draw)
    lines = format_matches(draw.matches)
    joined = "\n".join([header, *lines])
    print(joined)  # noqa: T201


def _fetch_draw_from_args(args: argparse.Namespace) -> Draw:
    if args.date is not None:
        return _resolve_draw_by_date(args.date)
    return fetch_draw(args.draw)


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
