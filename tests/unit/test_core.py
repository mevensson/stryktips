"""Unit tests for stryktips.core orchestration logic."""

import argparse
from datetime import date, datetime
from decimal import Decimal

import pytest
from flexmock import flexmock
from requests import RequestException

import stryktips.core
from stryktips.api import DrawNotFoundError
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


def test_resolve_draw_by_date_returns_draw_number_without_fetching_draw():
    """Resolving by date scans the datepicker and does not fetch the draw itself."""
    flexmock(
        stryktips.core,
        fetch_draws_by_month=lambda y, m: [
            DatepickerEntry(date=date(2025, 5, 10), draw_number=4900)
        ],
    )
    flexmock(stryktips.core).should_receive("fetch_draw").never()

    result = stryktips.core._resolve_draw_by_date("2025-05-10")

    assert result.draw_number == 4900


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


def test_resolve_draw_by_week_returns_draw_number_without_fetching_draw():
    """Resolving by week scans the datepicker and does not fetch the draw itself."""
    flexmock(
        stryktips.core,
        fetch_draws_by_month=lambda y, m: [
            DatepickerEntry(date=date(2025, 5, 10), draw_number=4900)
        ],
    )
    flexmock(stryktips.core).should_receive("fetch_draw").never()

    result = stryktips.core._resolve_draw_by_week("2025.19")

    assert result.draw_number == 4900


def test_fetch_draw_from_args_routes_week():
    """A --week argument routes through _resolve_draw_by_week."""
    flexmock(
        stryktips.core,
        _resolve_draw_by_week=lambda w: Draw(draw_number=4900, matches=[]),
    )
    flexmock(stryktips.core, fetch_draw=lambda dn: Draw(draw_number=dn, matches=[]))

    args = argparse.Namespace(date=None, week="2025.19", draw=None)

    draw = stryktips.core._fetch_draw_from_args(args)

    assert draw.draw_number == 4900


def test_fetch_draw_from_args_routes_draw():
    """A --draw argument fetches the draw via fetch_draw."""
    flexmock(stryktips.core, fetch_draw=lambda dn: Draw(draw_number=dn, matches=[]))

    args = argparse.Namespace(date=None, week=None, draw=4900)

    draw = stryktips.core._fetch_draw_from_args(args)

    assert draw.draw_number == 4900


def test_main_start_draw_end_draw_prints_report(capsys):
    """--start-draw/--end-draw together print the bucket report for the fetched draw."""
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

    exit_code = stryktips.core.main(["--start-draw", "4900", "--end-draw", "4900"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "eligible: 1, excluded: 0" in captured.out
    assert "70-80: 1" in captured.out


def test_main_start_draw_end_draw_prints_single_aggregated_report(capsys):  # noqa: PLR0915
    """--start-draw/--end-draw across a multi-draw range prints one merged report."""
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
            return Draw(
                draw_number=draw_number,
                matches=[match_high],
                reg_close_time=datetime(2025, 5, 10, 15, 59),
            )
        return Draw(draw_number=draw_number, matches=[match_low])

    flexmock(stryktips.core, fetch_draw=fetch)
    flexmock(
        stryktips.core,
        fetch_draws_by_month=lambda year, month: [
            DatepickerEntry(date=date(2025, 5, 10), draw_number=4901),
            DatepickerEntry(date=date(2025, 5, 17), draw_number=4902),
        ],
    )

    exit_code = stryktips.core.main(["--start-draw", "4901", "--end-draw", "4902"])
    captured = capsys.readouterr()

    expected = (
        "eligible: 2, excluded: 0\n"
        "0-10: 1 | 5% | 0% | -5%\n"
        "20-30: 2 | 22% | 50% | 28%\n"
        "30-40: 2 | 32% | 0% | -32%\n"
        "70-80: 1 | 75% | 100% | 25%"
    )
    assert exit_code == 0
    assert captured.out.splitlines() == expected.splitlines()


def test_main_start_draw_end_draw_reports_network_error_to_stderr(capsys):
    """A requests failure in the report path exits 1 and prints to stderr."""

    def raise_network(_dn: int) -> Draw:
        raise RequestException("connection refused")

    flexmock(stryktips.core, fetch_draw=raise_network)

    exit_code = stryktips.core.main(["--start-draw", "4900", "--end-draw", "4900"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "connection refused" in captured.err
    assert captured.out == ""


def test_main_start_draw_without_end_draw_resolves_default_end_and_prints_report(  # noqa: PLR0915
    capsys, monkeypatch
):
    """--start-draw without --end-draw defaults the end to the latest draw."""

    class _FakeDate(date):
        @classmethod
        def today(cls):
            return date(2025, 5, 10)

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
    monkeypatch.setattr(stryktips.core, "date", _FakeDate)
    flexmock(
        stryktips.core,
        fetch_draw=lambda dn: Draw(draw_number=dn, matches=[match]),
    )
    flexmock(stryktips.core).should_receive("_resolve_default_end").with_args(
        date(2025, 5, 10)
    ).and_return(4900)

    exit_code = stryktips.core.main(["--start-draw", "4900"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "eligible: 1, excluded: 0" in captured.out


def test_main_start_draw_after_most_recent_prints_empty_report_without_fetch(
    capsys, monkeypatch
):
    """--start-draw after the latest draw prints empty and never fetches."""

    class _FakeDate(date):
        @classmethod
        def today(cls):
            return date(2025, 1, 20)

    monkeypatch.setattr(stryktips.core, "date", _FakeDate)
    flexmock(stryktips.core).should_receive("_resolve_default_end").with_args(
        date(2025, 1, 20)
    ).and_return(4884)
    flexmock(stryktips.core).should_receive("fetch_draw").with_args(4900).never()

    exit_code = stryktips.core.main(["--start-draw", "4900"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.strip() == "eligible: 0, excluded: 0"


def test_main_start_draw_greater_than_end_draw_rejected(capsys):
    """--start-draw greater than --end-draw is a parser error with exit code 2."""
    with pytest.raises(SystemExit) as exc:
        stryktips.core.main(["--start-draw", "4901", "--end-draw", "4900"])

    assert exc.value.code == 2


def test_main_start_date_end_draw_prints_report(capsys):
    """--start-date/--end-draw together print the report for the resolved draw."""
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
        _resolve_draw_by_date=lambda d: Draw(draw_number=4900, matches=[match]),
    )
    flexmock(
        stryktips.core,
        fetch_draw=lambda dn: Draw(draw_number=dn, matches=[match]),
    )

    exit_code = stryktips.core.main(
        ["--start-date", "2025-05-10", "--end-draw", "4900"]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "eligible: 1, excluded: 0" in captured.out


def test_main_start_date_resolved_after_end_draw_fails_without_fetching(capsys):
    """A date-resolved start after the explicit end draw exits 1 without fetching."""
    flexmock(
        stryktips.core,
        fetch_draws_by_month=lambda y, m: [
            DatepickerEntry(date=date(2025, 5, 10), draw_number=4900)
        ],
    )
    flexmock(stryktips.core).should_receive("fetch_draw").never()

    exit_code = stryktips.core.main(
        ["--start-date", "2025-05-10", "--end-draw", "4884"]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "must not be greater than" in captured.err
    assert "4900" in captured.err
    assert "4884" in captured.err


def test_main_start_draw_end_date_prints_report(capsys):
    """--start-draw/--end-date together print the report for the resolved draw."""
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
        fetch_draws_by_month=lambda y, m: [
            DatepickerEntry(date=date(2025, 5, 10), draw_number=4900)
        ],
    )
    flexmock(
        stryktips.core,
        fetch_draw=lambda dn: Draw(draw_number=dn, matches=[match]),
    )

    exit_code = stryktips.core.main(
        ["--start-draw", "4900", "--end-date", "2025-05-10"]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "eligible: 1, excluded: 0" in captured.out


def test_resolve_end_bound_end_date_returns_latest_draw_on_or_before_bound(monkeypatch):
    """--end-date resolves to the latest draw dated on or before the given date."""

    class _FakeDate(date):
        @classmethod
        def today(cls):
            return date(2025, 6, 1)

    monkeypatch.setattr(stryktips.core, "date", _FakeDate)
    flexmock(
        stryktips.core,
        fetch_draws_by_month=lambda y, m: [
            DatepickerEntry(date=date(2025, 5, 3), draw_number=4899),
            DatepickerEntry(date=date(2025, 5, 10), draw_number=4900),
            DatepickerEntry(date=date(2025, 5, 17), draw_number=4901),
        ],
    )
    args = stryktips.core.create_parser().parse_args(
        ["--start-draw", "4900", "--end-date", "2025-05-11"]
    )

    result = stryktips.core._resolve_end_bound(args)

    assert result == 4900


def test_main_end_date_without_start_rejected(capsys):
    """--end-date without a --start-* is a parser error with exit code 2."""
    with pytest.raises(SystemExit) as exc:
        stryktips.core.main(["--end-date", "2025-05-10"])
    captured = capsys.readouterr()

    assert exc.value.code == 2
    assert "--end-date requires --start" in captured.err


def test_main_start_week_end_draw_prints_report(capsys):
    """--start-week/--end-draw together print the report for the resolved draw."""
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
        _resolve_draw_by_week=lambda w: Draw(draw_number=4900, matches=[match]),
    )
    flexmock(
        stryktips.core,
        fetch_draw=lambda dn: Draw(draw_number=dn, matches=[match]),
    )

    exit_code = stryktips.core.main(["--start-week", "2025.19", "--end-draw", "4900"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "eligible: 1, excluded: 0" in captured.out


def test_main_start_draw_end_week_prints_report(capsys):
    """--start-draw/--end-week together print the report for the resolved draw."""
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
        _resolve_draw_by_week=lambda w: Draw(draw_number=4900, matches=[match]),
    )
    flexmock(
        stryktips.core,
        fetch_draw=lambda dn: Draw(draw_number=dn, matches=[match]),
    )

    exit_code = stryktips.core.main(["--start-draw", "4900", "--end-week", "2025.19"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "eligible: 1, excluded: 0" in captured.out


def test_resolve_end_bound_unindexed_historical_week_returns_latest_draw(monkeypatch):
    """An omitted end-week index selects the latest draw on or before ISO Sunday."""

    class _FakeDate(date):
        @classmethod
        def today(cls):
            return date(2025, 1, 20)

    monkeypatch.setattr(stryktips.core, "date", _FakeDate)
    flexmock(stryktips.core).should_receive("fetch_draws_by_month").with_args(
        2024, 12
    ).and_return(
        [
            DatepickerEntry(date=date(2024, 12, 21), draw_number=4879),
            DatepickerEntry(date=date(2024, 12, 26), draw_number=4880),
            DatepickerEntry(date=date(2024, 12, 29), draw_number=4881),
        ]
    )
    args = stryktips.core.create_parser().parse_args(
        ["--start-draw", "4880", "--end-week", "2024.52"]
    )

    result = stryktips.core._resolve_end_bound(args)

    assert result == 4881


def test_main_end_week_without_start_rejected(capsys):
    """--end-week without a --start-* is a parser error with exit code 2."""
    with pytest.raises(SystemExit) as exc:
        stryktips.core.main(["--end-week", "2025.19"])
    captured = capsys.readouterr()

    assert exc.value.code == 2
    assert "--end-week requires --start" in captured.err


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


def test_draw_numbers_in_range_warns_when_end_unreached(capsys):  # noqa: PLR0915
    """When the end draw is never seen within the scan window, warn on stderr."""

    def mock_fetch_draws_by_month(year: int, month: int) -> list[DatepickerEntry]:
        return [DatepickerEntry(date=date(2020, month, 7), draw_number=4641)]

    flexmock(stryktips.core, fetch_draws_by_month=mock_fetch_draws_by_month)

    result = stryktips.core._draw_numbers_in_range(4641, 4642, (2020, 3))
    captured = capsys.readouterr()

    assert result == [4641] * stryktips.core.MAX_SCAN_MONTHS
    assert "Warning: could not reach draw 4642" in captured.err


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


def test_fetch_report_draws_returns_empty_when_start_draw_absent():
    """An absent start draw (DrawNotFoundError) yields an empty report list."""

    def raise_not_found(_dn: int) -> Draw:
        raise DrawNotFoundError("Draw 4900 not found")

    flexmock(stryktips.core, fetch_draw=raise_not_found)

    draws = stryktips.core._fetch_report_draws(4900, 4900)

    assert draws == []


def test_fetch_report_draws_skips_missing_draw_fetch_failure(capsys):  # noqa: PLR0915
    """An interior draw whose fetch 404s (DrawNotFoundError) is skipped, warning."""
    date_entries = [
        DatepickerEntry(date=date(2025, 1, 4), draw_number=4882),
        DatepickerEntry(date=date(2025, 1, 11), draw_number=4883),
        DatepickerEntry(date=date(2025, 1, 18), draw_number=4884),
    ]

    def fetch(draw_number: int) -> Draw:
        if draw_number == 4883:
            raise DrawNotFoundError("Draw 4883 not found")
        return Draw(
            draw_number=draw_number,
            matches=[],
            reg_close_time=datetime(2025, 1, 4, 15, 59),
        )

    flexmock(stryktips.core, fetch_draws_by_month=lambda y, m: date_entries)
    flexmock(stryktips.core, fetch_draw=fetch)

    draws = stryktips.core._fetch_report_draws(4882, 4884)
    captured = capsys.readouterr()

    assert [d.draw_number for d in draws] == [4882, 4884]
    assert "Warning: could not fetch draw 4883, skipping." in captured.err
    assert "Draw 4883 not found" not in captured.err


def test_fetch_report_draws_propagates_network_failure():
    """A non-404 network failure on an interior draw fails the run, not skip."""
    date_entries = [
        DatepickerEntry(date=date(2025, 1, 4), draw_number=4882),
        DatepickerEntry(date=date(2025, 1, 11), draw_number=4883),
        DatepickerEntry(date=date(2025, 1, 18), draw_number=4884),
    ]

    def fetch(draw_number: int) -> Draw:
        if draw_number == 4883:
            raise RequestException("connection refused")
        return Draw(
            draw_number=draw_number,
            matches=[],
            reg_close_time=datetime(2025, 1, 4, 15, 59),
        )

    flexmock(stryktips.core, fetch_draws_by_month=lambda y, m: date_entries)
    flexmock(stryktips.core, fetch_draw=fetch)

    with pytest.raises(RequestException, match="connection refused"):
        stryktips.core._fetch_report_draws(4882, 4884)


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


def test_resolve_default_end_returns_latest_entry_on_or_before_today():
    """When today's month has an entry on or before today, return its draw_number."""
    entries = [
        DatepickerEntry(date=date(2025, 1, 4), draw_number=4882),
        DatepickerEntry(date=date(2025, 1, 11), draw_number=4883),
        DatepickerEntry(date=date(2025, 1, 18), draw_number=4884),
        DatepickerEntry(date=date(2025, 1, 25), draw_number=4885),
        DatepickerEntry(date=date(2025, 2, 1), draw_number=4886),
    ]
    flexmock(stryktips.core, fetch_draws_by_month=lambda y, m: entries)

    result = stryktips.core._resolve_default_end(date(2025, 1, 20))

    assert result == 4884


def test_resolve_default_end_falls_back_one_month_when_none_eligible():
    """When today's month has no eligible entry, use the previous month's latest."""
    calls: list[tuple[int, int]] = []

    def mock_fetch_draws_by_month(year: int, month: int) -> list[DatepickerEntry]:
        calls.append((year, month))
        if (year, month) == (2025, 1):
            return [DatepickerEntry(date=date(2025, 1, 4), draw_number=4882)]
        return [DatepickerEntry(date=date(2024, 12, 29), draw_number=4881)]

    flexmock(stryktips.core, fetch_draws_by_month=mock_fetch_draws_by_month)

    result = stryktips.core._resolve_default_end(date(2025, 1, 1))

    assert result == 4881


def test_resolve_default_end_stops_scanning_once_entry_found():
    """Stop querying months as soon as an eligible entry is found."""
    calls: list[tuple[int, int]] = []

    def mock_fetch_draws_by_month(year: int, month: int) -> list[DatepickerEntry]:
        calls.append((year, month))
        return [DatepickerEntry(date=date(year, month, 10), draw_number=1000)]

    flexmock(stryktips.core, fetch_draws_by_month=mock_fetch_draws_by_month)

    result = stryktips.core._resolve_default_end(date(2025, 1, 20))

    assert result == 1000
    assert calls == [(2025, 1)]


def test_resolve_default_end_raises_when_no_entry_in_scan_window():
    """When no month in the scan window has an eligible entry, raise DrawNotFound."""
    flexmock(
        stryktips.core,
        fetch_draws_by_month=lambda y, m: [],
    )

    with pytest.raises(DrawNotFound) as exc:
        stryktips.core._resolve_default_end(date(2000, 1, 1))

    assert exc.value.value == "2000-01-01"


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
