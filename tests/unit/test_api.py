"""Unit tests for stryktipset API client."""

import json

import pytest
import requests
from flexmock import flexmock  # type: ignore[import-not-found]

from stryktips.api import fetch_week


@pytest.fixture
def mock_api_response():
    """Load real API response for week 4900."""
    with open("tests/fixtures/week_4900.json") as f:
        return json.load(f)


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
