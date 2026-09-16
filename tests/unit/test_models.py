"""Unit tests for domain models."""

from datetime import date
from decimal import Decimal

from stryktips.models import DatepickerEntry, Match, Odds, OutcomeProbability


def test_odds_stores_home_draw_away():
    """Odds stores all three outcome values."""
    # Act
    odds = Odds(home=Decimal("2.50"), draw=Decimal("3.70"), away=Decimal("2.80"))

    # Assert
    assert (odds.home, odds.draw, odds.away) == (
        Decimal("2.50"),
        Decimal("3.70"),
        Decimal("2.80"),
    )


def test_outcome_probability_stores_home_draw_away():
    """OutcomeProbability stores all three probability values."""
    # Act
    probabilities = OutcomeProbability(
        home=Decimal("0.3893"),
        draw=Decimal("0.2631"),
        away=Decimal("0.3476"),
    )

    # Assert
    assert (probabilities.home, probabilities.draw, probabilities.away) == (
        Decimal("0.3893"),
        Decimal("0.2631"),
        Decimal("0.3476"),
    )


def test_datepicker_entry_stores_date_and_draw_number():
    """DatepickerEntry stores a date and a draw number."""
    # Act
    entry = DatepickerEntry(date=date(2025, 5, 10), draw_number=4900)

    # Assert
    assert (entry.date, entry.draw_number) == (date(2025, 5, 10), 4900)


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


def test_match_holds_outcome_probability_when_provided():
    """Match stores the OutcomeProbability passed to it."""
    # Arrange
    probabilities = OutcomeProbability(
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
        outcome_probability=probabilities,
    )

    # Assert
    assert match.outcome_probability == probabilities


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
