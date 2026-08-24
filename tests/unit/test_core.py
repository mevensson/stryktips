"""Unit tests for stryktips.core orchestration logic."""

import argparse
from datetime import date

import pytest
from flexmock import flexmock

import stryktips.core
from stryktips.models import DatepickerEntry, Draw


def test_resolve_draw_by_date_forward_scans_when_anchor_empty(capsys):  # noqa: PLR0915
    """When anchor month has no entries, advance month-by-month until a match."""
    may_entries = [DatepickerEntry(date=date(2020, 5, 2), draw_number=4701)]
    calls: list[tuple[int, int]] = []

    def mock_fetch_draws_by_month(year: int, month: int) -> list[DatepickerEntry]:
        calls.append((year, month))
        if month == 4:
            return []
        return may_entries

    flexmock(stryktips.core, fetch_draws_by_month=mock_fetch_draws_by_month)
    flexmock(
        stryktips.core,
        fetch_draw=lambda dn: Draw(draw_number=dn, matches=[]),
    )

    draw = stryktips.core._resolve_draw_by_date("2020-04-01")
    captured = capsys.readouterr()

    assert draw.draw_number == 4701
    assert calls == [(2020, 4), (2020, 5)]
    assert (
        "Note: No draw found for 2020-04-01, using 2020-05-02 (draw 4701)"
        in captured.err
    )


def test_resolve_draw_by_week_finds_draw_in_iso_week(capsys):  # noqa: PLR0915
    """Draw whose date falls inside the ISO week resolves as an exact match."""
    calls: list[tuple[int, int]] = []

    def mock_fetch_draws_by_month(year: int, month: int) -> list[DatepickerEntry]:
        calls.append((year, month))
        return [DatepickerEntry(date=date(2025, 5, 10), draw_number=4900)]

    flexmock(stryktips.core, fetch_draws_by_month=mock_fetch_draws_by_month)
    flexmock(
        stryktips.core,
        fetch_draw=lambda dn: Draw(draw_number=dn, matches=[]),
    )

    draw = stryktips.core._resolve_draw_by_week("2025.19")
    captured = capsys.readouterr()

    assert draw.draw_number == 4900
    assert calls == [(2025, 5)]
    assert captured.err == ""


def test_fetch_draw_from_args_routes_week():
    """A --week argument routes through _resolve_draw_by_week."""
    flexmock(
        stryktips.core,
        _resolve_draw_by_week=lambda w: Draw(draw_number=4900, matches=[]),
    )
    flexmock(stryktips.core, fetch_draw=lambda dn: Draw(draw_number=1234, matches=[]))

    args = argparse.Namespace(date=None, week="2025.19", draw=None)

    draw = stryktips.core._fetch_draw_from_args(args)

    assert draw.draw_number == 4900


def test_resolve_draw_by_date_exits_after_12_empty_months(capsys):
    """When 12 months have no entries, print stderr and sys.exit(1)."""
    flexmock(
        stryktips.core,
        fetch_draws_by_month=lambda y, m: [],
    )

    with pytest.raises(SystemExit) as exc:
        stryktips.core._resolve_draw_by_date("2000-01-01")
    captured = capsys.readouterr()

    assert exc.value.code == 1
    assert "No draw found within 12 months of 2000-01-01" in captured.err


def test_main_returns_network_error_to_stderr(capsys):
    """A requests failure in the fetch path exits 1 and prints to stderr."""
    from requests import RequestException

    def raise_network(_args: argparse.Namespace) -> Draw:
        raise RequestException("connection refused")

    flexmock(stryktips.core, _fetch_draw_from_args=raise_network)

    exit_code = stryktips.core.main(["--draw", "4900"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "connection refused" in captured.err
    assert captured.out == ""
