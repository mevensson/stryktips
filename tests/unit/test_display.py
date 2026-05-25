"""Unit tests for display module."""

import pytest

from stryktips.display import format_matches


@pytest.fixture
def sample_event():
    """Sample draw event for testing."""
    return {
        "eventNumber": 1,
        "match": {
            "participants": [
                {"mediumName": "Bournemou"},
                {"mediumName": "Aston V"},
            ],
            "result": [
                {"type": 2, "home": "0", "away": "1"},  # Fulltime
            ],
        },
        "svenskaFolket": {"one": "35", "x": "24", "two": "41"},
    }


def test_format_matches_returns_correct_count(sample_event):
    """Test that format_matches processes all events."""
    events = [sample_event]
    result = format_matches(events)
    assert len(result) == 1
    assert "Bournemou" in result[0]
    assert "Aston V" in result[0]


def test_format_matches_extracts_result(sample_event):
    """Test that result (2 = away win) is correctly extracted."""
    events = [sample_event]
    result = format_matches(events)
    assert "| 2 |" in result[0]


def test_format_matches_extracts_percentages(sample_event):
    """Test that svenska folket percentages are formatted."""
    events = [sample_event]
    result = format_matches(events)
    assert "35%" in result[0]
    assert "24%" in result[0]
    assert "41%" in result[0]


def test_format_matches_empty_list():
    """Test that empty input returns empty list."""
    result = format_matches([])
    assert result == []


def test_format_matches_home_win():
    """Test home win result."""
    event = {
        "eventNumber": 1,
        "match": {
            "participants": [
                {"mediumName": "Home"},
                {"mediumName": "Away"},
            ],
            "result": [
                {"type": 2, "home": "2", "away": "1"},
            ],
        },
        "svenskaFolket": {"one": "50", "x": "20", "two": "30"},
    }
    result = format_matches([event])
    assert "| 1 |" in result[0]


def test_format_matches_draw():
    """Test draw result."""
    event = {
        "eventNumber": 1,
        "match": {
            "participants": [
                {"mediumName": "Home"},
                {"mediumName": "Away"},
            ],
            "result": [
                {"type": 2, "home": "1", "away": "1"},
            ],
        },
        "svenskaFolket": {"one": "30", "x": "40", "two": "30"},
    }
    result = format_matches([event])
    assert "| X |" in result[0]