"""Unit tests for stryktipset API client."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import requests
from flexmock import flexmock

from stryktips.api import DrawNotFoundError, fetch_draw, fetch_draws_by_month
from stryktips.models import DatepickerEntry, Odds, SvenskaFolket

_API_URL = "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/"
_FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def mock_api_response():
    """Load the real API response for draw 4900."""
    return json.loads((_FIXTURES / "draw_4900.json").read_text())


@pytest.fixture
def mock_draw_4900(mock_api_response, mock_response):
    """Arrange a mocked API response for draw 4900."""
    flexmock(requests).should_receive("get").with_args(
        f"{_API_URL}4900",
        timeout=30,
    ).and_return(mock_response(mock_api_response))


def test_fetch_draw_returns_all_13_matches(mock_draw_4900):
    """Fetching draw 4900 returns a draw with 13 matches."""
    # Act
    draw = fetch_draw(4900)

    # Assert
    assert len(draw.matches) == 13


def test_fetch_draw_parses_draw_number(mock_draw_4900):
    """The API draw number is stored on the Draw."""
    # Act
    draw = fetch_draw(4900)

    # Assert
    assert draw.draw_number == 4900


def test_fetch_draw_parses_draw_comment(mock_draw_4900):
    """drawComment from the API response is stored in Draw.draw_comment."""
    # Act
    draw = fetch_draw(4900)

    # Assert
    assert draw.draw_comment == "Stryktipset v. 2025-19"


def test_fetch_draw_parses_reg_close_time(mock_draw_4900):
    """regCloseTime from the API response is stored as a datetime."""
    # Act
    draw = fetch_draw(4900)

    # Assert
    close_time = draw.reg_close_time
    assert close_time is not None
    assert close_time.isoformat() == "2025-05-10T15:59:00+02:00"


def test_fetch_draw_parses_start_odds_for_first_match(mock_draw_4900):
    """First match's startOdds are parsed into an Odds object."""
    # Act
    draw = fetch_draw(4900)

    # Assert
    assert draw.matches[0].odds == Odds(
        home=Decimal("2.50"),
        draw=Decimal("3.70"),
        away=Decimal("2.80"),
    )


def test_fetch_draw_parses_outcome_probabilities(mock_draw_4900):
    """First match's outcome probability is computed from startOdds."""
    # Act
    draw = fetch_draw(4900)

    # Assert
    probabilities = draw.matches[0].outcome_probability
    assert probabilities is not None
    assert (
        probabilities.home,
        probabilities.draw,
        probabilities.away,
    ) == pytest.approx(
        (Decimal("0.3893"), Decimal("0.2631"), Decimal("0.3476")),
        abs=Decimal("0.0001"),
    )


def test_fetch_draw_parses_odds_for_all_matches(mock_draw_4900):
    """Every match in the draw has parsed odds and outcome probabilities."""
    # Act
    draw = fetch_draw(4900)

    # Assert
    for match in draw.matches:
        assert match.odds is not None, f"Match {match.event_number} has no odds"
        assert match.outcome_probability is not None, (
            f"Match {match.event_number} has no outcome probability"
        )


def test_fetch_draw_parses_svenska_folket_as_decimal(mock_draw_4900):
    """svenskaFolket percentages are parsed into Decimal values."""
    # Act
    draw = fetch_draw(4900)

    # Assert
    assert draw.matches[0].svenska_folket == SvenskaFolket(
        one=Decimal("35"),
        x=Decimal("24"),
        two=Decimal("41"),
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
    assert draw.matches == []


def test_fetch_draw_omits_outcome_probability_for_zero_odds(mock_response):
    """A match whose startOdds carry a zero/missing field gets no probability."""
    # Arrange
    zero_odds_event: dict[str, Any] = {
        "draw": {
            "drawEvents": [
                {
                    "eventNumber": 1,
                    "match": {
                        "participants": [
                            {"mediumName": "Home"},
                            {"mediumName": "Away"},
                        ],
                        "result": [{"type": 2, "home": 1, "away": 0}],
                    },
                    "startOdds": {"one": "2.50", "x": "3.70", "two": "0"},
                },
            ]
        }
    }
    flexmock(requests).should_receive("get").with_args(
        f"{_API_URL}5001",
        timeout=30,
    ).and_return(mock_response(zero_odds_event))

    # Act
    draw = fetch_draw(5001)

    # Assert
    match = draw.matches[0]
    assert match.odds == Odds(
        home=Decimal("2.50"),
        draw=Decimal("3.70"),
        away=Decimal("0"),
    )
    assert match.outcome_probability is None


@pytest.mark.parametrize(
    "participants",
    [
        [],
        [{"mediumName": "Home"}],
    ],
    ids=["no-participants", "one-participant"],
)
def test_fetch_draw_raises_on_missing_participants(mock_response, participants):
    """A match without home/away participants raises ValueError."""
    # Arrange
    bad_event: dict[str, Any] = {
        "draw": {
            "drawEvents": [
                {"eventNumber": 1, "match": {"participants": participants}},
            ]
        }
    }
    flexmock(requests).should_receive("get").with_args(
        f"{_API_URL}5000",
        timeout=30,
    ).and_return(mock_response(bad_event))

    with pytest.raises(ValueError, match="participants"):
        fetch_draw(5000)


def test_fetch_draw_raises_draw_not_found_on_404(mock_response):
    """A 404 response raises DrawNotFoundError."""
    # Arrange
    flexmock(requests).should_receive("get").with_args(
        f"{_API_URL}4900",
        timeout=30,
    ).and_return(mock_response({}, status_code=404))

    with pytest.raises(DrawNotFoundError):
        fetch_draw(4900)


def test_fetch_draw_raises_draw_not_found_on_null_draw(mock_response):
    """A 200 response with a null draw raises DrawNotFoundError."""
    # Arrange
    flexmock(requests).should_receive("get").with_args(
        f"{_API_URL}4971",
        timeout=30,
    ).and_return(mock_response({"draw": None}))

    with pytest.raises(DrawNotFoundError):
        fetch_draw(4971)


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
