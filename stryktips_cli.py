#!/usr/bin/env python3
"""Stryktips CLI.

This CLI currently provides only help text.
"""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="stryktips",
        description="Stryktips command line interface.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="stryktips 0.1.0",
        help="Show program version and exit.",
    )

    args = parser.parse_args()
    if not vars(args):
        parser.print_help()


if __name__ == "__main__":
    main()
