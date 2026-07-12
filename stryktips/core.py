import argparse

from stryktips.api import fetch_draw
from stryktips.display import format_matches


def create_parser() -> argparse.ArgumentParser:
    """Create and return the argument parser for the stryktips CLI."""
    parser = argparse.ArgumentParser(
        prog="stryktips.py",
        description="Stryktips command line interface.",
    )
    parser.add_argument(
        "--draw",
        type=int,
        required=True,
        help="Draw number for Stryktipset data",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    draw = fetch_draw(args.draw)
    lines = format_matches(draw.matches)

    print(f"Stryktipset Draw {draw.draw_number}")  # noqa: T201
    for line in lines:
        print(line)  # noqa: T201

    return 0
