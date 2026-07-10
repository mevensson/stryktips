"""Unit tests for display module."""

from decimal import Decimal

from stryktips.display import format_matches
from stryktips.models import Match, Odds, OutcomeProbability, SvenskaFolket


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
    """Formatting one match yields one output line."""
    # Act
    lines = format_matches([sample_match()])

    # Assert
    assert len(lines) == 1


def test_format_matches_contains_team_names():
    """Both team names appear in the output."""
    # Act
    lines = format_matches([sample_match()])

    # Assert
    assert "Bournemou" in lines[0]
    assert "Aston V" in lines[0]


def test_format_matches_extracts_result():
    """Away win shows as '2'."""
    # Act
    lines = format_matches([sample_match()])

    # Assert
    assert "| 2 |" in lines[0]


def test_format_matches_extracts_percentages():
    """Svenska folket percentages are formatted."""
    # Act
    lines = format_matches([sample_match()])

    # Assert
    assert "35% - 24% - 41%" in lines[0]


def test_format_matches_empty_list_returns_empty():
    """Empty input yields empty output list."""
    # Act
    result = format_matches([])

    # Assert
    assert result == []


def test_format_matches_shows_home_win():
    """Home win result shows as '1'."""
    # Arrange
    match = Match(
        event_number=1,
        home_team="Home",
        away_team="Away",
        home_score=2,
        away_score=1,
        svenska_folket=SvenskaFolket(one="50", x="20", two="30"),
    )

    # Act
    lines = format_matches([match])

    # Assert
    assert "| 1 |" in lines[0]


def test_format_matches_shows_draw():
    """Draw result shows as 'X'."""
    # Arrange
    match = Match(
        event_number=1,
        home_team="Home",
        away_team="Away",
        home_score=1,
        away_score=1,
        svenska_folket=SvenskaFolket(one="30", x="40", two="30"),
    )

    # Act
    lines = format_matches([match])

    # Assert
    assert "| X |" in lines[0]


def test_format_matches_shows_odds_when_present():
    """Odds are included in the output when the match carries them."""
    # Arrange
    odds = Odds(home=Decimal("2.50"), draw=Decimal("3.70"), away=Decimal("2.80"))
    match = Match(
        event_number=1,
        home_team="Home",
        away_team="Away",
        home_score=1,
        away_score=0,
        svenska_folket=SvenskaFolket(one="50", x="20", two="30"),
        odds=odds,
    )

    # Act
    lines = format_matches([match])

    # Assert
    assert "2.50 - 3.70 - 2.80" in lines[0]


def test_format_matches_omits_odds_when_absent():
    """No odds shown when the match has none."""
    # Arrange
    match = Match(
        event_number=1,
        home_team="Home",
        away_team="Away",
        home_score=1,
        away_score=0,
        svenska_folket=SvenskaFolket(one="50", x="20", two="30"),
    )

    # Act
    lines = format_matches([match])

    # Assert
    assert "2.50" not in lines[0]


def test_format_matches_shows_outcome_probabilities_when_odds_present():
    """Rounded outcome probabilities are shown when the match has odds."""
    # Arrange
    probs = OutcomeProbability(
        home=Decimal("0.3893"),
        draw=Decimal("0.2631"),
        away=Decimal("0.3476"),
    )
    match = Match(
        event_number=1,
        home_team="Home",
        away_team="Away",
        home_score=1,
        away_score=0,
        svenska_folket=SvenskaFolket(one="50", x="20", two="30"),
        odds=Odds(home=Decimal("2.50"), draw=Decimal("3.70"), away=Decimal("2.80")),
        outcome_probability=probs,
    )

    # Act
    lines = format_matches([match])

    # Assert
    assert "39% - 26% - 35%" in lines[0]


def test_format_matches_omits_outcome_probabilities_when_odds_absent():
    """No outcome probabilities shown when the match has no odds."""
    # Arrange
    match = Match(
        event_number=1,
        home_team="Home",
        away_team="Away",
        home_score=1,
        away_score=0,
        svenska_folket=SvenskaFolket(one="50", x="20", two="30"),
    )

    # Act
    lines = format_matches([match])

    # Assert
    assert "39%" not in lines[0]
