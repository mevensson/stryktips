"""Unit tests for stryktips.core orchestration logic."""

from datetime import date

from flexmock import flexmock

from stryktips.models import DatepickerEntry, Draw


def test_resolve_draw_by_date_forward_scans_when_anchor_empty(capsys):  # noqa: PLR0915
    """When anchor month has no entries, advance month-by-month until a match."""
    import stryktips.core

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
