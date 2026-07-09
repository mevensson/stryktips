"""Unit tests for domain models."""

from decimal import Decimal

from stryktips.models import Match, Odds


def test_odds_dataclass():
    """Test that Odds dataclass stores values correctly."""
    odds = Odds(home=Decimal("2.50"), draw=Decimal("3.70"), away=Decimal("2.80"))

    assert odds.home == Decimal("2.50")
    assert odds.draw == Decimal("3.70")
    assert odds.away == Decimal("2.80")


def test_match_with_odds():
    """Test that a Match can carry Odds."""
    odds = Odds(home=Decimal("2.50"), draw=Decimal("3.70"), away=Decimal("2.80"))
    match = Match(
        event_number=1,
        home_team="Home",
        away_team="Away",
        home_score=1,
        away_score=0,
        svenska_folket=None,
        odds=odds,
    )

    assert match.odds == odds
    assert match.odds.home == Decimal("2.50")


def test_match_without_odds():
    """Test that a Match can exist without Odds (backward compat)."""
    match = Match(
        event_number=1,
        home_team="Home",
        away_team="Away",
        home_score=None,
        away_score=None,
        svenska_folket=None,
    )

    assert match.odds is None
