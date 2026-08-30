"""Unit tests for stryktipset API client."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import requests
from flexmock import flexmock

from stryktips.api import fetch_draw, fetch_draws_by_month
from stryktips.models import DatepickerEntry, SvenskaFolket

_API_URL = "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/"


@pytest.fixture
def mock_api_response():
    """Load real API response for week 4900."""
    return json.loads(Path("tests/fixtures/week_4900.json").read_text())


def _mock_fetch_draw_4900(mock_api_response: dict[str, Any], mock_response: Any) -> Any:
    flexmock(requests).should_receive("get").with_args(
        f"{_API_URL}4900",
        timeout=30,
    ).and_return(mock_response(mock_api_response))
    return fetch_draw(4900)


def test_fetch_draw_returns_draw_with_13_matches(mock_api_response, mock_response):
    """Fetching week 4900 returns a draw with 13 matches."""
    # Act
    draw = _mock_fetch_draw_4900(mock_api_response, mock_response)

    # Assert
    assert len(draw.matches) == 13
    assert draw.draw_number == 4900


def test_fetch_draw_parses_draw_comment(mock_api_response, mock_response):
    """drawComment from the API response is stored in Draw.draw_comment."""
    # Act
    draw = _mock_fetch_draw_4900(mock_api_response, mock_response)

    # Assert
    assert draw.draw_comment == "Stryktipset v. 2025-19"


def test_fetch_draw_parses_reg_close_time(mock_api_response, mock_response):
    """regCloseTime from the API response is stored as a datetime."""
    # Act
    draw = _mock_fetch_draw_4900(mock_api_response, mock_response)

    # Assert
    assert draw.reg_close_time.isoformat() == "2025-05-10T15:59:00+02:00"


def test_fetch_draw_parses_start_odds_for_first_match(mock_api_response, mock_response):
    """First match's startOdds are parsed into an Odds object."""
    # Act
    draw = _mock_fetch_draw_4900(mock_api_response, mock_response)

    # Assert
    match1 = draw.matches[0]
    assert match1.odds is not None
    assert match1.odds.home == Decimal("2.50")
    assert match1.odds.draw == Decimal("3.70")
    assert match1.odds.away == Decimal("2.80")


def test_fetch_draw_parses_outcome_probabilities(mock_api_response, mock_response):
    """First match's outcome probability is computed from startOdds."""
    # Act
    draw = _mock_fetch_draw_4900(mock_api_response, mock_response)

    # Assert
    match1 = draw.matches[0]
    assert match1.outcome_probability is not None
    assert match1.outcome_probability.home == pytest.approx(
        Decimal("0.3893"),
        abs=Decimal("0.0001"),
    )
    assert match1.outcome_probability.draw == pytest.approx(
        Decimal("0.2631"),
        abs=Decimal("0.0001"),
    )
    assert match1.outcome_probability.away == pytest.approx(
        Decimal("0.3476"),
        abs=Decimal("0.0001"),
    )


def test_fetch_draw_parses_odds_for_all_matches(mock_api_response, mock_response):
    """Every match in the draw has parsed odds and outcome probabilities."""
    # Act
    draw = _mock_fetch_draw_4900(mock_api_response, mock_response)

    # Assert
    for match in draw.matches:
        assert match.odds is not None, f"Match {match.event_number} has no odds"
        assert match.outcome_probability is not None, (
            f"Match {match.event_number} has no outcome probability"
        )


def test_fetch_draw_handles_empty_response(mock_response):
    """Empty events list yields a draw with zero matches."""
    # Arrange
    empty: dict[str, Any] = {"draw": {"drawEvents": []}}
    flexmock(requests).should_receive("get").with_args(
        f"{_API_URL}99999",
        timeout=30,
    ).and_return(mock_response(empty))

    # Act
    draw = fetch_draw(99999)

    # Assert
    assert len(draw.matches) == 0


def test_fetch_draw_parses_svenska_folket_as_decimal(mock_api_response, mock_response):
    """svenskaFolket percentages are parsed into Decimal values."""
    # Act
    draw = _mock_fetch_draw_4900(mock_api_response, mock_response)

    # Assert
    match1 = draw.matches[0]
    assert match1.svenska_folket == SvenskaFolket(
        one=Decimal("35"),
        x=Decimal("24"),
        two=Decimal("41"),
    )


def test_fetch_draw_raises_on_missing_participants(mock_response):
    """A match without home/away participants raises ValueError."""
    bad_event: dict[str, Any] = {
        "draw": {
            "drawEvents": [
                {"eventNumber": 1, "match": {"participants": []}},
            ]
        }
    }
    flexmock(requests).should_receive("get").with_args(
        f"{_API_URL}5000",
        timeout=30,
    ).and_return(mock_response(bad_event))

    with pytest.raises(ValueError, match="participants"):
        fetch_draw(5000)


def test_fetch_draws_by_month_returns_parsed_entries(mock_response):
    """fetch_draws_by_month returns DatepickerEntry list from the API."""
    # Arrange
    api_response = {
        "datepicker": [
            {"date": "2025-05-05", "drawNumber": 4898},
            {"date": "2025-05-10", "drawNumber": 4900},
        ]
    }
    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
        "?product=stryktipset&year=2025&month=5",
        timeout=30,
    ).and_return(mock_response(api_response))

    # Act
    entries = fetch_draws_by_month(2025, 5)

    # Assert
    assert len(entries) == 2
    assert entries == [
        DatepickerEntry(date=date(2025, 5, 5), draw_number=4898),
        DatepickerEntry(date=date(2025, 5, 10), draw_number=4900),
    ]


def test_fetch_draws_by_month_returns_empty_on_404(mock_response):
    """fetch_draws_by_month returns [] when the API answers 404."""
    # Arrange
    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
        "?product=stryktipset&year=2025&month=5",
        timeout=30,
    ).and_return(mock_response({}, status_code=404))

    # Act
    entries = fetch_draws_by_month(2025, 5)

    # Assert
    assert entries == []
