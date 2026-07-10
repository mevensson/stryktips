"""Unit tests for stryktipset API client."""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import requests
from flexmock import flexmock

from stryktips.api import fetch_week

_API_URL = "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/"


@pytest.fixture
def mock_api_response():
    """Load real API response for week 4900."""
    return json.loads(Path("tests/fixtures/week_4900.json").read_text())


def _mock_requests_get(data: dict[str, Any]) -> Any:
    """Stub requests.get to return a given JSON payload."""
    mock = flexmock(status_code=200)
    mock.should_receive("json").and_return(data)
    mock.should_receive("raise_for_status").and_return(None)
    return mock


def test_fetch_week_returns_draw_with_13_matches(mock_api_response):
    """Fetching week 4900 returns a draw with 13 matches."""
    # Arrange
    mock = _mock_requests_get(mock_api_response)
    flexmock(requests).should_receive("get").with_args(
        f"{_API_URL}4900",
        timeout=30,
    ).and_return(mock)

    # Act
    draw = fetch_week(4900)

    # Assert
    assert len(draw.matches) == 13
    assert draw.draw_number == 4900


def test_fetch_week_parses_start_odds_for_first_match(mock_api_response):
    """First match's startOdds are parsed into an Odds object."""
    # Arrange
    mock = _mock_requests_get(mock_api_response)
    flexmock(requests).should_receive("get").with_args(
        f"{_API_URL}4900",
        timeout=30,
    ).and_return(mock)

    # Act
    draw = fetch_week(4900)

    # Assert
    match1 = draw.matches[0]
    assert match1.odds is not None
    assert match1.odds.home == Decimal("2.50")
    assert match1.odds.draw == Decimal("3.70")
    assert match1.odds.away == Decimal("2.80")


def test_fetch_week_parses_odds_for_all_matches(mock_api_response):
    """Every match in the draw has parsed odds."""
    # Arrange
    mock = _mock_requests_get(mock_api_response)
    flexmock(requests).should_receive("get").with_args(
        f"{_API_URL}4900",
        timeout=30,
    ).and_return(mock)

    # Act
    draw = fetch_week(4900)

    # Assert
    for match in draw.matches:
        assert match.odds is not None, f"Match {match.event_number} has no odds"


def test_fetch_week_handles_empty_response():
    """Empty events list yields a draw with zero matches."""
    # Arrange
    empty: dict[str, Any] = {"draw": {"drawEvents": []}}
    mock = _mock_requests_get(empty)
    flexmock(requests).should_receive("get").with_args(
        f"{_API_URL}99999",
        timeout=30,
    ).and_return(mock)

    # Act
    draw = fetch_week(99999)

    # Assert
    assert len(draw.matches) == 0
