"""CLI tests for stryktips.core, exercised through main().

Every test drives the CLI through ``main`` with dependencies injected through
the public ``create_dependencies`` seam, so no private helper is called or
mocked.
"""

from datetime import date

import pytest
from flexmock import flexmock
from requests import RequestException

import stryktips.core
from stryktips.core import Dependencies
from stryktips.models import DatepickerEntry, Draw
from tests.builders import make_draw

_FIXED_TODAY = date(2025, 1, 1)


def test_main_draw_flag_displays_the_draw(capsys):
    """--draw fetches that draw directly and renders its header."""
    fetched: list[int] = []
    dependencies = _dependencies(
        draws={
            4900: make_draw(draw_number=4900, draw_comment="Stryktipset v. 2025-19")
        },
        fetched=fetched,
    )

    exit_code = _main_with(dependencies, ["--draw", "4900"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Stryktipset v. 2025-19 (draw 4900)" in captured.out
    assert fetched == [4900]


def test_main_draw_flag_does_not_consult_datepicker(capsys):
    """--draw resolves to the given number without a datepicker lookup."""

    def unexpected_lookup(year: int, month: int) -> list[DatepickerEntry]:
        raise AssertionError("--draw must not consult the datepicker")

    dependencies = Dependencies(
        fetch_draw=lambda number: make_draw(draw_number=number),
        fetch_month_entries=unexpected_lookup,
        clock=lambda: _FIXED_TODAY,
        diagnostic=lambda message: None,
    )

    exit_code = _main_with(dependencies, ["--draw", "4900"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Stryktipset Draw 4900" in captured.out


def test_main_date_flag_resolves_and_displays_the_draw(capsys):
    """--date resolves through the datepicker and displays the resolved draw."""
    dependencies = _dependencies(
        {(2025, 5): [DatepickerEntry(date=date(2025, 5, 10), draw_number=4900)]},
        draws={4900: make_draw(draw_number=4900)},
    )

    exit_code = _main_with(dependencies, ["--date", "2025-05-10"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Stryktipset Draw 4900" in captured.out
    assert captured.err == ""


def test_main_week_flag_resolves_and_displays_the_draw(capsys):
    """--week resolves through the week resolver and displays the resolved draw."""
    dependencies = _dependencies(
        {(2025, 5): [DatepickerEntry(date=date(2025, 5, 10), draw_number=4900)]},
        draws={4900: make_draw(draw_number=4900)},
    )

    exit_code = _main_with(dependencies, ["--week", "2025.19"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Stryktipset Draw 4900" in captured.out
    assert captured.err == ""


def test_main_start_draw_end_draw_prints_bucket_report(capsys):
    """--start-draw/--end-draw prints the bucket report for the single draw."""
    dependencies = _dependencies(
        draws={4900: make_draw(draw_number=4900)},
    )

    exit_code = _main_with(dependencies, ["--start-draw", "4900", "--end-draw", "4900"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.splitlines()[0] == "eligible: 13, excluded: 0"


def test_main_start_draw_end_draw_prints_single_aggregated_report(capsys):
    """A spanning range folds both draws into one aggregated report."""
    fetched: list[int] = []
    dependencies = _dependencies(
        {
            (2025, 5): [
                DatepickerEntry(date=date(2025, 5, 10), draw_number=4901),
                DatepickerEntry(date=date(2025, 5, 17), draw_number=4902),
            ]
        },
        draws={
            4901: make_draw(draw_number=4901),
            4902: make_draw(draw_number=4902),
        },
        fetched=fetched,
    )

    exit_code = _main_with(dependencies, ["--start-draw", "4901", "--end-draw", "4902"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.splitlines()[0] == "eligible: 26, excluded: 0"
    assert captured.out.count("eligible:") == 1
    assert fetched == [4901, 4902]


def test_main_start_draw_end_draw_reports_network_error_to_stderr(capsys):
    """A request failure while collecting the report maps to exit 1 and stderr."""

    def raise_network(number: int) -> Draw:
        raise RequestException("connection refused")

    dependencies = Dependencies(
        fetch_draw=raise_network,
        fetch_month_entries=lambda year, month: [],
        clock=lambda: _FIXED_TODAY,
        diagnostic=lambda message: None,
    )

    exit_code = _main_with(dependencies, ["--start-draw", "4900", "--end-draw", "4900"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "connection refused" in captured.err
    assert captured.out == ""


def test_main_start_draw_without_end_draw_uses_default_end(capsys):
    """--start-draw without an end defaults to the latest draw on or before today."""
    dependencies = _dependencies(
        {
            (2025, 5): [
                DatepickerEntry(date=date(2025, 5, 10), draw_number=4900),
                DatepickerEntry(date=date(2025, 5, 17), draw_number=4901),
            ]
        },
        draws={4900: make_draw(draw_number=4900)},
        today=date(2025, 5, 12),
    )

    exit_code = _main_with(dependencies, ["--start-draw", "4900"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.splitlines()[0] == "eligible: 13, excluded: 0"


def test_main_start_draw_after_default_end_prints_empty_report_without_fetch(capsys):
    """A start after the default end prints an empty report and never fetches."""
    fetched: list[int] = []
    dependencies = _dependencies(
        {(2025, 1): [DatepickerEntry(date=date(2025, 1, 18), draw_number=4884)]},
        today=date(2025, 1, 20),
        fetched=fetched,
    )

    exit_code = _main_with(dependencies, ["--start-draw", "4900"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.strip() == "eligible: 0, excluded: 0"
    assert fetched == []


def test_main_start_draw_greater_than_end_draw_rejected(capsys):
    """An explicit start greater than the explicit end is a parser error."""
    with pytest.raises(SystemExit) as exc:
        stryktips.core.main(["--start-draw", "4901", "--end-draw", "4900"])
    captured = capsys.readouterr()

    assert exc.value.code == 2
    assert "--start-draw must not be greater than --end-draw" in captured.err


def test_main_start_date_end_draw_prints_report(capsys):
    """--start-date/--end-draw prints the report for the resolved start draw."""
    dependencies = _dependencies(
        {(2025, 5): [DatepickerEntry(date=date(2025, 5, 10), draw_number=4900)]},
        draws={4900: make_draw(draw_number=4900)},
        today=date(2025, 6, 1),
    )

    exit_code = _main_with(
        dependencies, ["--start-date", "2025-05-10", "--end-draw", "4900"]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.splitlines()[0] == "eligible: 13, excluded: 0"


def test_main_start_date_resolved_after_end_draw_fails_without_fetching(capsys):
    """A resolved start after an explicit end errors before any draw is fetched."""
    fetched: list[int] = []
    dependencies = _dependencies(
        {(2025, 5): [DatepickerEntry(date=date(2025, 5, 10), draw_number=4900)]},
        today=date(2025, 6, 1),
        fetched=fetched,
    )

    exit_code = _main_with(
        dependencies, ["--start-date", "2025-05-10", "--end-draw", "4884"]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "must not be greater than" in captured.err
    assert "4900" in captured.err
    assert "4884" in captured.err
    assert fetched == []


def test_main_start_draw_end_date_prints_report(capsys):
    """--start-draw/--end-date prints the report for the resolved end draw."""
    dependencies = _dependencies(
        {(2025, 5): [DatepickerEntry(date=date(2025, 5, 10), draw_number=4900)]},
        draws={4900: make_draw(draw_number=4900)},
        today=date(2025, 6, 1),
    )

    exit_code = _main_with(
        dependencies, ["--start-draw", "4900", "--end-date", "2025-05-10"]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.splitlines()[0] == "eligible: 13, excluded: 0"


def test_main_end_date_without_start_rejected(capsys):
    """--end-date without any --start-* bound is a parser error."""
    with pytest.raises(SystemExit) as exc:
        stryktips.core.main(["--end-date", "2025-05-10"])
    captured = capsys.readouterr()

    assert exc.value.code == 2
    assert "--end-date requires --start" in captured.err


def test_main_start_week_end_draw_prints_report(capsys):
    """--start-week/--end-draw prints the report for the resolved start draw."""
    dependencies = _dependencies(
        {(2025, 5): [DatepickerEntry(date=date(2025, 5, 10), draw_number=4900)]},
        draws={4900: make_draw(draw_number=4900)},
    )

    exit_code = _main_with(
        dependencies, ["--start-week", "2025.19", "--end-draw", "4900"]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.splitlines()[0] == "eligible: 13, excluded: 0"


def test_main_start_draw_end_week_prints_report(capsys):
    """--start-draw/--end-week resolves the historical week and prints its report."""
    dependencies = _dependencies(
        {
            (2025, 5): [
                DatepickerEntry(date=date(2025, 5, 10), draw_number=4900),
                DatepickerEntry(date=date(2025, 5, 17), draw_number=4901),
            ]
        },
        draws={4900: make_draw(draw_number=4900)},
        today=date(2025, 6, 1),
    )

    exit_code = _main_with(
        dependencies, ["--start-draw", "4900", "--end-week", "2025.19"]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.splitlines()[0] == "eligible: 13, excluded: 0"


def test_main_end_week_without_start_rejected(capsys):
    """--end-week without any --start-* bound is a parser error."""
    with pytest.raises(SystemExit) as exc:
        stryktips.core.main(["--end-week", "2025.19"])
    captured = capsys.readouterr()

    assert exc.value.code == 2
    assert "--end-week requires --start" in captured.err


def test_main_reports_draw_not_found(capsys):
    """Exhausted forward resolution maps DrawNotFound to exit 1 and stderr."""
    dependencies = _dependencies(today=_FIXED_TODAY)

    exit_code = _main_with(dependencies, ["--date", "2000-01-01"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "No draw found within 12 months of 2000-01-01" in captured.err
    assert captured.out == ""


def test_main_returns_network_error_to_stderr(capsys):
    """A request failure in the display path maps to exit 1 and stderr."""

    def raise_network(number: int) -> Draw:
        raise RequestException("connection refused")

    dependencies = Dependencies(
        fetch_draw=raise_network,
        fetch_month_entries=lambda year, month: [],
        clock=lambda: _FIXED_TODAY,
        diagnostic=lambda message: None,
    )

    exit_code = _main_with(dependencies, ["--draw", "4900"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "connection refused" in captured.err
    assert captured.out == ""


def test_main_invalid_date_reports_error(capsys):
    """An unparseable --date maps to exit 1 and a stderr message."""
    dependencies = _dependencies()

    exit_code = _main_with(dependencies, ["--date", "not-a-date"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Invalid date" in captured.err
    assert captured.out == ""


def test_main_spanning_report_errors_when_anchor_has_no_close_time(capsys):
    """A spanning report whose anchor has no close time exits 1 with stderr."""
    fetched: list[int] = []
    dependencies = _dependencies(
        draws={4900: make_draw(draw_number=4900, reg_close_time=None)},
        fetched=fetched,
    )

    exit_code = _main_with(dependencies, ["--start-draw", "4900", "--end-draw", "4901"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Draw 4900 has no close time" in captured.err
    assert captured.out == ""
    assert fetched == [4900]


def _dependencies(
    months: dict[tuple[int, int], list[DatepickerEntry]] | None = None,
    *,
    draws: dict[int, Draw] | None = None,
    today: date = _FIXED_TODAY,
    diagnostics: list[str] | None = None,
    fetched: list[int] | None = None,
) -> Dependencies:
    """Build CLI dependencies over fixed month/draw maps, clock, and diagnostics."""
    month_entries = months or {}
    draw_by_number = draws or {}
    fetched_numbers = [] if fetched is None else fetched

    def fetch_draw(number: int) -> Draw:
        fetched_numbers.append(number)
        return draw_by_number[number]

    return Dependencies(
        fetch_draw=fetch_draw,
        fetch_month_entries=lambda year, month: list(
            month_entries.get((year, month), [])
        ),
        clock=lambda: today,
        diagnostic=(diagnostics.append if diagnostics is not None else lambda _m: None),
    )


def _main_with(dependencies: Dependencies, argv: list[str]) -> int:
    """Run main with dependencies injected through the public composition seam."""
    flexmock(stryktips.core, create_dependencies=lambda: dependencies)
    return stryktips.core.main(argv)
