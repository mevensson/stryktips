"""Unit tests for stryktips.core orchestration logic."""

import argparse
from datetime import date, datetime
from decimal import Decimal

import pytest
from flexmock import flexmock
from requests import RequestException

import stryktips.core
from stryktips.models import DatepickerEntry, Draw, Match, Odds, OutcomeProbability
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


def test_fetch_draw_from_args_routes_draw():
    """A --draw argument fetches the draw via fetch_draw."""
    flexmock(stryktips.core, fetch_draw=lambda dn: Draw(draw_number=dn, matches=[]))

    args = argparse.Namespace(date=None, week=None, draw=4900)

    draw = stryktips.core._fetch_draw_from_args(args)

    assert draw.draw_number == 4900


def test_main_start_end_prints_report(capsys):
    """--start/--end together print the bucket report for the fetched draw."""
    match = Match(
        event_number=1,
        home_team="Brynäs",
        away_team="Leksand",
        home_score=3,
        away_score=1,
        odds=Odds(home=Decimal("2.0"), draw=Decimal("3.4"), away=Decimal("3.6")),
        outcome_probability=OutcomeProbability(
            home=Decimal("0.75"), draw=Decimal("0.20"), away=Decimal("0.05")
        ),
    )
    flexmock(
        stryktips.core,
        fetch_draw=lambda dn: Draw(draw_number=dn, matches=[match]),
    )

    exit_code = stryktips.core.main(["--start", "4900", "--end", "4900"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "eligible: 1, excluded: 0" in captured.out
    assert "70-80: 1" in captured.out


def test_main_start_end_prints_single_aggregated_report(capsys):  # noqa: PLR0915
    """--start/--end across a multi-draw range prints one merged report."""
    match_high = Match(
        event_number=1,
        home_team="Brynäs",
        away_team="Leksand",
        home_score=3,
        away_score=1,
        odds=Odds(home=Decimal("2.0"), draw=Decimal("3.4"), away=Decimal("3.6")),
        outcome_probability=OutcomeProbability(
            home=Decimal("0.75"), draw=Decimal("0.20"), away=Decimal("0.05")
        ),
    )
    match_low = Match(
        event_number=1,
        home_team="Brynäs",
        away_team="Leksand",
        home_score=3,
        away_score=1,
        odds=Odds(home=Decimal("2.0"), draw=Decimal("3.4"), away=Decimal("3.6")),
        outcome_probability=OutcomeProbability(
            home=Decimal("0.25"), draw=Decimal("0.30"), away=Decimal("0.35")
        ),
    )

    def fetch(draw_number: int) -> Draw:
        if draw_number == 4901:
            return Draw(draw_number=draw_number, matches=[match_high])
        return Draw(draw_number=draw_number, matches=[match_low])

    flexmock(stryktips.core, fetch_draw=fetch)

    exit_code = stryktips.core.main(["--start", "4901", "--end", "4902"])
    captured = capsys.readouterr()

    expected = "eligible: 2, excluded: 0\n20-30: 1\n70-80: 1"
    assert exit_code == 0
    assert captured.out.splitlines() == expected.splitlines()


def test_main_start_end_reports_network_error_to_stderr(capsys):
    """A requests failure in the report path exits 1 and prints to stderr."""

    def raise_network(_dn: int) -> Draw:
        raise RequestException("connection refused")

    flexmock(stryktips.core, fetch_draw=raise_network)

    exit_code = stryktips.core.main(["--start", "4900", "--end", "4900"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "connection refused" in captured.err
    assert captured.out == ""


def test_main_start_without_end_rejected(capsys):
    """--start without --end is a parser error with exit code 2."""
    with pytest.raises(SystemExit) as exc:
        stryktips.core.main(["--start", "4900"])

    assert exc.value.code == 2


def test_main_start_greater_than_end_rejected(capsys):
    """--start greater than --end is a parser error with exit code 2."""
    with pytest.raises(SystemExit) as exc:
        stryktips.core.main(["--start", "4901", "--end", "4900"])

    assert exc.value.code == 2


def test_draw_numbers_in_range_walks_across_drawless_months():  # noqa: PLR0915
    """Walk month-by-month collecting in-range draw numbers, skipping 404 months."""
    calls: list[tuple[int, int]] = []

    def mock_fetch_draws_by_month(year: int, month: int) -> list[DatepickerEntry]:
        calls.append((year, month))
        if month == 3:
            return [
                DatepickerEntry(date=date(2020, 3, 7), draw_number=4639),
                DatepickerEntry(date=date(2020, 3, 14), draw_number=4640),
                DatepickerEntry(date=date(2020, 3, 21), draw_number=4641),
            ]
        if month in (4, 5):
            return []
        if month == 6:
            return [
                DatepickerEntry(date=date(2020, 6, 6), draw_number=4642),
                DatepickerEntry(date=date(2020, 6, 13), draw_number=4643),
            ]
        raise AssertionError("unexpected month")

    flexmock(stryktips.core, fetch_draws_by_month=mock_fetch_draws_by_month)

    result = stryktips.core._draw_numbers_in_range(4641, 4642, (2020, 3))

    assert result == [4641, 4642]
    assert calls == [(2020, 3), (2020, 4), (2020, 5), (2020, 6)]


def test_fetch_report_draws_spanning_walks_datepicker_and_filters():  # noqa: PLR0915
    """Spanning range walks the datepicker and returns only the in-range draws."""
    calls: list[tuple[int, int]] = []

    def mock_fetch_draws_by_month(year: int, month: int) -> list[DatepickerEntry]:
        calls.append((year, month))
        if (year, month) == (2025, 5):
            return [
                DatepickerEntry(date=date(2025, 5, 3), draw_number=4880),
                DatepickerEntry(date=date(2025, 5, 10), draw_number=4901),
                DatepickerEntry(date=date(2025, 5, 17), draw_number=4902),
                DatepickerEntry(date=date(2025, 5, 24), draw_number=4903),
            ]
        raise AssertionError("unexpected month")

    flexmock(stryktips.core, fetch_draws_by_month=mock_fetch_draws_by_month)
    flexmock(
        stryktips.core,
        fetch_draw=lambda dn: Draw(
            draw_number=dn,
            matches=[],
            reg_close_time=datetime(2025, 5, 10, 15, 59),
        ),
    )

    draws = stryktips.core._fetch_report_draws(4901, 4902)

    assert [d.draw_number for d in draws] == [4901, 4902]
    assert calls == [(2025, 5)]


def test_fetch_report_draws_single_does_not_touch_datepicker():
    """A single-draw range returns exactly that draw without walking the datepicker."""
    calls: list[tuple[int, int]] = []

    def mock_fetch_draws_by_month(year: int, month: int) -> list[DatepickerEntry]:
        calls.append((year, month))
        return []

    flexmock(stryktips.core, fetch_draws_by_month=mock_fetch_draws_by_month)
    flexmock(
        stryktips.core,
        fetch_draw=lambda dn: Draw(draw_number=dn, matches=[]),
    )

    draws = stryktips.core._fetch_report_draws(4900, 4900)

    assert [d.draw_number for d in draws] == [4900]
    assert calls == []


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
