"""Unit tests for stryktipset API client."""

import json
import pytest
from unittest.mock import patch

from stryktips.api import fetch_week


@pytest.fixture
def mock_api_response():
    """Load real API response for week 4900."""
    with open("tests/fixtures/week_4900.json", "r") as f:
        return json.load(f)


@patch("stryktips.api.requests.get")
def test_fetch_week_success(mock_get, mock_api_response):
    """Test successful API fetch returns 13 matches."""
    mock_get.return_value.json.return_value = mock_api_response
    mock_get.return_value.status_code = 200

    result = fetch_week(4900)
    assert len(result) == 13
    assert mock_get.call_count == 1
    mock_get.assert_called_once_with(
        "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/4900", timeout=30
    )


@patch("stryktips.api.requests.get")
def test_fetch_week_empty_response(mock_get):
    """Test that empty API response is handled."""
    mock_get.return_value.json.return_value = {"draw": {"drawEvents": []}}
    result = fetch_week(99999)
    assert len(result) == 0
