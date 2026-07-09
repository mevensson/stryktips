"""Unit tests for stryktipset API client."""

import json
from decimal import Decimal
from pathlib import Path

import pytest
import requests
from flexmock import flexmock

from stryktips.api import fetch_week


@pytest.fixture
def mock_api_response():
    """Load real API response for week 4900."""
    return json.loads(Path("tests/fixtures/week_4900.json").read_text())


def test_fetch_week_returns_draw_with_13_matches(mock_api_response):
    mock_response = flexmock(status_code=200)
    mock_response.should_receive("json").and_return(mock_api_response)
    mock_response.should_receive("raise_for_status").and_return(None)

    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/4900",
        timeout=30,
    ).and_return(mock_response)

    draw = fetch_week(4900)

    assert len(draw.matches) == 13
    assert draw.draw_number == 4900


def test_parsed_odds_from_start_odds(mock_api_response):
    """Test that startOdds are parsed into Odds objects."""
    mock_response = flexmock(status_code=200)
    mock_response.should_receive("json").and_return(mock_api_response)
    mock_response.should_receive("raise_for_status").and_return(None)

    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/4900",
        timeout=30,
    ).and_return(mock_response)

    draw = fetch_week(4900)

    match1 = draw.matches[0]
    assert match1.odds is not None
    assert match1.odds.home == Decimal("2.50")
    assert match1.odds.draw == Decimal("3.70")
    assert match1.odds.away == Decimal("2.80")


def test_all_matches_have_odds(mock_api_response):
    """Test that every match in a draw has parsed odds."""
    mock_response = flexmock(status_code=200)
    mock_response.should_receive("json").and_return(mock_api_response)
    mock_response.should_receive("raise_for_status").and_return(None)

    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/4900",
        timeout=30,
    ).and_return(mock_response)

    draw = fetch_week(4900)

    for match in draw.matches:
        assert match.odds is not None, f"Match {match.event_number} has no odds"


def test_fetch_week_handles_empty_response():
    mock_response = flexmock(status_code=200)
    mock_response.should_receive("json").and_return({"draw": {"drawEvents": []}})
    mock_response.should_receive("raise_for_status").and_return(None)

    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/99999",
        timeout=30,
    ).and_return(mock_response)

    draw = fetch_week(99999)

    assert len(draw.matches) == 0
