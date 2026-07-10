"""Unit tests for domain models."""

from decimal import Decimal

from stryktips.models import Match, Odds


def test_odds_stores_home_draw_away():
    """Odds stores all three outcome values."""
    # Act
    odds = Odds(home=Decimal("2.50"), draw=Decimal("3.70"), away=Decimal("2.80"))

    # Assert
    assert odds.home == Decimal("2.50")
    assert odds.draw == Decimal("3.70")
    assert odds.away == Decimal("2.80")


def test_match_holds_odds_when_provided():
    """Match stores the odds object passed to it."""
    # Arrange
    odds = Odds(home=Decimal("2.50"), draw=Decimal("3.70"), away=Decimal("2.80"))

    # Act
    match = Match(
        event_number=1,
        home_team="Home",
        away_team="Away",
        home_score=1,
        away_score=0,
        svenska_folket=None,
        odds=odds,
    )

    # Assert
    assert match.odds == odds


def test_match_defaults_odds_to_none():
    """Match can exist without odds for backward compatibility."""
    # Act
    match = Match(
        event_number=1,
        home_team="Home",
        away_team="Away",
        home_score=None,
        away_score=None,
        svenska_folket=None,
    )

    # Assert
    assert match.odds is None
