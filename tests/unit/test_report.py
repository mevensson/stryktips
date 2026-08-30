"""Unit tests for report probability bucket assignment."""

from decimal import Decimal

import pytest

from stryktips.models import Draw, Match, Odds, OutcomeProbability
from stryktips.report import bucket_index, format_report, realized_probability


def make_match(
    *,
    home_score: int | None,
    away_score: int | None,
    outcome_probability: OutcomeProbability | None,
) -> Match:
    """Construct a Match with only the fields realized_probability reads."""
    return Match(
        event_number=1,
        home_team="Home",
        away_team="Away",
        home_score=home_score,
        away_score=away_score,
        outcome_probability=outcome_probability,
    )


def make_draw(matches: list[Match]) -> Draw:
    """Construct a Draw wrapping the given matches."""
    return Draw(draw_number=1, matches=matches)


@pytest.mark.parametrize(
    ("probability", "expected"),
    [
        (Decimal("0.0"), 0),
        (Decimal("0.49"), 4),
        (Decimal("0.50"), 5),
        (Decimal("0.75"), 7),
        (Decimal("0.99"), 9),
    ],
)
def test_bucket_index_assigns_to_low_high_decade_bucket(probability, expected):
    """Probability maps to the decade bucket containing it via [low, high)."""
    # Act
    result = bucket_index(probability)

    # Assert
    assert result == expected


def test_bucket_index_clamps_upper_bound_to_bucket_nine():
    """Probability 1.0 clamps into the top bucket rather than bucket 10."""
    # Act
    result = bucket_index(Decimal("1.0"))

    # Assert
    assert result == 9


def test_realized_probability_home_win_returns_home_probability():
    """Home win picks the home outcome probability."""
    # Arrange
    probs = OutcomeProbability(
        home=Decimal("0.7"), draw=Decimal("0.2"), away=Decimal("0.1")
    )
    match = make_match(home_score=2, away_score=0, outcome_probability=probs)

    # Act
    result = realized_probability(match)

    # Assert
    assert result == Decimal("0.7")


def test_realized_probability_away_win_returns_away_probability():
    """Away win picks the away outcome probability."""
    # Arrange
    probs = OutcomeProbability(
        home=Decimal("0.1"), draw=Decimal("0.2"), away=Decimal("0.7")
    )
    match = make_match(home_score=0, away_score=2, outcome_probability=probs)

    # Act
    result = realized_probability(match)

    # Assert
    assert result == Decimal("0.7")


def test_realized_probability_draw_returns_draw_probability():
    """Draw picks the draw outcome probability."""
    # Arrange
    probs = OutcomeProbability(
        home=Decimal("0.1"), draw=Decimal("0.7"), away=Decimal("0.2")
    )
    match = make_match(home_score=1, away_score=1, outcome_probability=probs)

    # Act
    result = realized_probability(match)

    # Assert
    assert result == Decimal("0.7")


def test_realized_probability_unplayed_match_returns_none():
    """Unplayed match with no scores yields None."""
    # Arrange
    match = make_match(
        home_score=None,
        away_score=None,
        outcome_probability=OutcomeProbability(
            home=Decimal("0.7"), draw=Decimal("0.2"), away=Decimal("0.1")
        ),
    )

    # Act
    result = realized_probability(match)

    # Assert
    assert result is None


def test_realized_probability_without_outcome_probability_returns_none():
    """Played match with no outcome probability yields None."""
    # Arrange
    match = make_match(home_score=2, away_score=0, outcome_probability=None)

    # Act
    result = realized_probability(match)

    # Assert
    assert result is None


def test_format_report_aggregates_eligible_and_excluded_matches():
    """Eligible matches fill buckets and played-but-odds-less matches are excluded."""
    # Arrange
    home_win = Match(
        event_number=1,
        home_team="Brynäs",
        away_team="Leksand",
        home_score=3,
        away_score=1,
        odds=Odds(home=Decimal("2.0"), draw=Decimal("3.4"), away=Decimal("3.6")),
        outcome_probability=OutcomeProbability(
            home=Decimal("0.75"), draw=Decimal("0.20"), away=Decimal("0.05")
        ),
    )
    away_win = Match(
        event_number=2,
        home_team="AIK",
        away_team="Djurgården",
        home_score=0,
        away_score=2,
        odds=Odds(home=Decimal("3.0"), draw=Decimal("3.2"), away=Decimal("2.4")),
        outcome_probability=OutcomeProbability(
            home=Decimal("0.05"), draw=Decimal("0.20"), away=Decimal("0.15")
        ),
    )
    draw_match = Match(
        event_number=3,
        home_team="Frölunda",
        away_team="Färjestad",
        home_score=1,
        away_score=1,
        odds=Odds(home=Decimal("2.6"), draw=Decimal("3.1"), away=Decimal("2.8")),
        outcome_probability=OutcomeProbability(
            home=Decimal("0.20"), draw=Decimal("0.55"), away=Decimal("0.25")
        ),
    )
    odds_less = make_match(home_score=1, away_score=0, outcome_probability=None)
    unplayed = make_match(home_score=None, away_score=None, outcome_probability=None)

    # Act
    result = format_report(make_draw([home_win, away_win, draw_match, odds_less, unplayed]))

    # Assert
    assert result == "eligible: 3, excluded: 1\n10-20: 1\n50-60: 1\n70-80: 1"


def test_format_report_with_only_unplayed_matches_is_empty_report():
    """Unplayed matches are ignored, leaving a zero summary and no buckets."""
    # Arrange
    unplayed = make_match(home_score=None, away_score=None, outcome_probability=None)

    # Act
    result = format_report(make_draw([unplayed]))

    # Assert
    assert result == "eligible: 0, excluded: 0"
