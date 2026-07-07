import argparse

from stryktips.api import fetch_week
from stryktips.display import format_matches


def create_parser() -> argparse.ArgumentParser:
    """Create and return the argument parser for the stryktips CLI."""
    parser = argparse.ArgumentParser(
        prog="stryktips.py",
        description="Stryktips command line interface.",
    )
    parser.add_argument(
        "--week",
        type=int,
        required=True,
        help="Week number for Stryktipset data",
    )
    return parser


def main(argv=None) -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    draw = fetch_week(args.week)
    lines = format_matches(draw.matches)

    print(f"Stryktipset Draw {draw.draw_number}")
    for line in lines:
        print(line)

    return 0
