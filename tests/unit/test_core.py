"""Unit tests for stryktips.core orchestration logic."""

import argparse
from datetime import date

import pytest
from flexmock import flexmock
from requests import RequestException

import stryktips.core
from stryktips.models import DatepickerEntry, Draw
from stryktips.resolver import DrawNotFound


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


def test_resolve_draw_by_week_uses_n_suffix_index(capsys):  # noqa: PLR0915
    """A .N suffix selects the N-th draw within the ISO week."""
    calls: list[tuple[int, int]] = []

    def mock_fetch_draws_by_month(year: int, month: int) -> list[DatepickerEntry]:
        calls.append((year, month))
        return [
            DatepickerEntry(date=date(2024, 12, 26), draw_number=4880),
            DatepickerEntry(date=date(2024, 12, 29), draw_number=4881),
        ]

    flexmock(stryktips.core, fetch_draws_by_month=mock_fetch_draws_by_month)
    flexmock(
        stryktips.core,
        fetch_draw=lambda dn: Draw(draw_number=dn, matches=[]),
    )

    draw = stryktips.core._resolve_draw_by_week("2024.52.2")
    captured = capsys.readouterr()

    assert draw.draw_number == 4881
    assert calls == [(2024, 12)]
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


def test_fetch_draw_from_args_rejects_unimplemented_report():
    """--start/--end alone never reach fetch_draw; raise a clear error instead."""
    flexmock(stryktips.core, fetch_draw=lambda dn: Draw(draw_number=dn, matches=[]))

    args = argparse.Namespace(date=None, week=None, draw=None)

    with pytest.raises(ValueError, match="not yet implemented"):
        stryktips.core._fetch_draw_from_args(args)


def test_resolve_draw_by_date_raises_after_12_empty_months(capsys):
    """When 12 months have no entries, raise DrawNotFound."""
    flexmock(
        stryktips.core,
        fetch_draws_by_month=lambda y, m: [],
    )

    with pytest.raises(DrawNotFound) as exc:
        stryktips.core._resolve_draw_by_date("2000-01-01")

    assert exc.value.value == "2000-01-01"


def test_main_reports_draw_not_found(capsys):
    """main maps DrawNotFound to exit 1 with a stderr message."""

    def raise_not_found(_args: argparse.Namespace) -> Draw:
        raise DrawNotFound("2000-01-01")

    flexmock(stryktips.core, _fetch_draw_from_args=raise_not_found)

    exit_code = stryktips.core.main(["--date", "2000-01-01"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "No draw found within 12 months of 2000-01-01" in captured.err
    assert captured.out == ""


def test_main_returns_network_error_to_stderr(capsys):
    """A requests failure in the fetch path exits 1 and prints to stderr."""

    def raise_network(_args: argparse.Namespace) -> Draw:
        raise RequestException("connection refused")

    flexmock(stryktips.core, _fetch_draw_from_args=raise_network)

    exit_code = stryktips.core.main(["--draw", "4900"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "connection refused" in captured.err
    assert captured.out == ""
