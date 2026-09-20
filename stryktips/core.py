import argparse
import sys
from collections.abc import Callable
from datetime import date
from typing import cast

from requests import RequestException

from stryktips.api import (
    fetch_draw as api_fetch_draw,
)
from stryktips.api import (
    fetch_draws_by_month as api_fetch_month_entries,
)
from stryktips.collection import collect_period
from stryktips.dependencies import (
    Clock,
    Dependencies,
    Diagnostic,
    FetchDraw,
    FetchMonthEntries,
)
from stryktips.display import format_header, format_matches
from stryktips.models import Draw
from stryktips.months import MAX_SCAN_MONTHS
from stryktips.report import format_aggregate_report
from stryktips.resolution import (
    DrawByDate,
    DrawByNumber,
    DrawByWeek,
    DrawSelector,
    resolve_draw,
    resolve_end,
)
from stryktips.resolver import DrawNotFound, week_monday

_START_BOUND_FLAGS = ("--start-draw", "--start-date", "--start-week")
_END_BOUND_FLAGS = ("--end-draw", "--end-date", "--end-week")

_SELECTOR_FACTORIES: dict[str, Callable[[object], DrawSelector]] = {
    "draw": lambda value: DrawByNumber(cast(int, value)),
    "date": lambda value: DrawByDate(cast(str, value)),
    "week": lambda value: DrawByWeek(cast(str, value)),
}
_FORWARD_SELECTOR_ORDER = ("draw", "date", "week")
_END_SELECTOR_ORDER = ("date", "week", "draw")


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
        fetch_draw=api_fetch_draw if fetch_draw is None else fetch_draw,
        fetch_month_entries=(
            api_fetch_month_entries
            if fetch_month_entries is None
            else fetch_month_entries
        ),
        clock=date.today if clock is None else clock,
        diagnostic=_diagnostic_to_stderr if diagnostic is None else diagnostic,
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


def create_parser() -> argparse.ArgumentParser:
    """Create and return the argument parser for the stryktips CLI."""
    parser = argparse.ArgumentParser(
        prog="stryktips.py",
        description="Stryktips command line interface.",
    )
    display_or_start = parser.add_mutually_exclusive_group(required=True)
    _add_display_arguments(display_or_start)
    _add_start_arguments(display_or_start)
    _add_end_arguments(parser)
    return parser


def _add_display_arguments(group: argparse._MutuallyExclusiveGroup) -> None:
    """Add the single-draw ``--draw``/``--date``/``--week`` options."""
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


def _add_start_arguments(group: argparse._MutuallyExclusiveGroup) -> None:
    """Add the report-start ``--start-*`` options to the shared exclusive group."""
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


def _add_end_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the separately accepted report-end ``--end-*`` options."""
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


def _parse_week(value: str) -> str:
    try:
        week_monday(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None
    return value


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


def _start_selector(args: argparse.Namespace) -> DrawSelector:
    """Build the report start selector from parsed arguments."""
    return _required_selector(args, "start_", _FORWARD_SELECTOR_ORDER)


def _end_selector(args: argparse.Namespace) -> DrawSelector | None:
    """Build the report end selector, honouring date, week, then draw order."""
    return _optional_selector(args, "end_", _END_SELECTOR_ORDER)


def _display_report(draws: list[Draw]) -> None:
    print(format_aggregate_report(draws))  # noqa: T201


def _fetch_draw_from_args(args: argparse.Namespace, dependencies: Dependencies) -> Draw:
    return dependencies.fetch_draw(resolve_draw(_display_selector(args), dependencies))


def _display_selector(args: argparse.Namespace) -> DrawSelector:
    """Build the single-Draw selector from parsed arguments."""
    return _required_selector(args, "", _FORWARD_SELECTOR_ORDER)


def _required_selector(
    args: argparse.Namespace, prefix: str, order: tuple[str, ...]
) -> DrawSelector:
    """Build a mandatory selector, raising if no bound in ``order`` is present."""
    selector = _optional_selector(args, prefix, order)
    if selector is None:
        raise ValueError(f"No {prefix.rstrip('_')} bound given")
    return selector


def _optional_selector(
    args: argparse.Namespace, prefix: str, order: tuple[str, ...]
) -> DrawSelector | None:
    """Return the selector for the first bound present in ``order``, else None."""
    for kind in order:
        value = getattr(args, f"{prefix}{kind}")
        if value is not None:
            return _SELECTOR_FACTORIES[kind](value)
    return None


def _display(draw: Draw) -> int:
    header = format_header(draw)
    lines = format_matches(draw.matches)
    joined = "\n".join([header, *lines])
    print(joined)  # noqa: T201
    return 0


def _diagnostic_to_stderr(message: str) -> None:
    """Write a diagnostic message to stderr."""
    print(message, file=sys.stderr)  # noqa: T201


def _report_draw_not_found(exc: DrawNotFound) -> int:
    print(  # noqa: T201
        f"No draw found within {MAX_SCAN_MONTHS} months of {exc.value}",
        file=sys.stderr,
    )
    return 1


def _report_error(exc: Exception) -> int:
    print(exc, file=sys.stderr)  # noqa: T201
    return 1
