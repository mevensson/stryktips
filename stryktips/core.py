import argparse
import sys


def create_parser() -> argparse.ArgumentParser:
    """Create and return the argument parser for the stryktips CLI."""
    parser = argparse.ArgumentParser(
        prog="stryktips.py",
        description="Stryktips command line interface.",
    )
    return parser


def main(argv=None) -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    parser.parse_args(argv)
    return 0
