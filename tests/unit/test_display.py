"""Unit tests for display module."""

from stryktips.display import format_matches
from stryktips.models import Match, SvenskaFolket


def sample_match() -> Match:
    """Sample match for testing."""
    return Match(
        event_number=1,
        home_team="Bournemou",
        away_team="Aston V",
        home_score=0,
        away_score=1,
        svenska_folket=SvenskaFolket(one="35", x="24", two="41"),
    )


def test_format_matches_returns_correct_count():
    """Test that format_matches processes all matches."""
    lines = format_matches([sample_match()])
    assert len(lines) == 1
    assert "Bournemou" in lines[0]
    assert "Aston V" in lines[0]


def test_format_matches_extracts_result():
    """Test that result (2 = away win) is correctly extracted."""
    lines = format_matches([sample_match()])
    assert "| 2 |" in lines[0]


def test_format_matches_extracts_percentages():
    """Test that svenska folket percentages are formatted."""
    lines = format_matches([sample_match()])
    assert "35%" in lines[0]
    assert "24%" in lines[0]
    assert "41%" in lines[0]


def test_format_matches_empty_list():
    """Test that empty input returns empty list."""
    result = format_matches([])
    assert result == []


def test_format_matches_home_win():
    """Test home win result."""
    match = Match(
        event_number=1,
        home_team="Home",
        away_team="Away",
        home_score=2,
        away_score=1,
        svenska_folket=SvenskaFolket(one="50", x="20", two="30"),
    )
    lines = format_matches([match])
    assert "| 1 |" in lines[0]


def test_format_matches_draw():
    """Test draw result."""
    match = Match(
        event_number=1,
        home_team="Home",
        away_team="Away",
        home_score=1,
        away_score=1,
        svenska_folket=SvenskaFolket(one="30", x="40", two="30"),
    )
    lines = format_matches([match])
    assert "| X |" in lines[0]
