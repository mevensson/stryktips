"""Unit tests for domain models."""

from decimal import Decimal

from stryktips.models import Match, Odds, OutcomeProbability


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


def test_outcome_probability_stores_home_draw_away():
    """OutcomeProbability stores all three probability values."""
    # Act
    probs = OutcomeProbability(
        home=Decimal("0.3893"),
        draw=Decimal("0.2631"),
        away=Decimal("0.3476"),
    )

    # Assert
    assert probs.home == Decimal("0.3893")
    assert probs.draw == Decimal("0.2631")
    assert probs.away == Decimal("0.3476")


def test_match_holds_outcome_probability_when_provided():
    """Match stores the OutcomeProbability passed to it."""
    # Arrange
    probs = OutcomeProbability(
        home=Decimal("0.3893"),
        draw=Decimal("0.2631"),
        away=Decimal("0.3476"),
    )

    # Act
    match = Match(
        event_number=1,
        home_team="Home",
        away_team="Away",
        home_score=1,
        away_score=0,
        svenska_folket=None,
        odds=Odds(home=Decimal("2.50"), draw=Decimal("3.70"), away=Decimal("2.80")),
        outcome_probability=probs,
    )

    # Assert
    assert match.outcome_probability == probs


def test_match_defaults_outcome_probability_to_none():
    """Match can exist without outcome probability."""
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
    assert match.outcome_probability is None
