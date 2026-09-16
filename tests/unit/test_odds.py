"""Unit tests for odds probability calculations."""

from decimal import Decimal

import pytest

from stryktips.odds import remove_overround


@pytest.mark.parametrize(
    ("home_odds", "draw_odds", "away_odds"),
    [
        (Decimal("2.50"), Decimal("3.70"), Decimal("2.80")),
        (Decimal("1.10"), Decimal("8.00"), Decimal("15.00")),
        (Decimal("3.00"), Decimal("3.00"), Decimal("3.00")),
    ],
    ids=["balanced", "heavy-favourite", "equal"],
)
def test_remove_overround_normalizes_probabilities_to_one(
    home_odds, draw_odds, away_odds
):
    """Removing the overround yields probabilities summing to 1.0."""
    # Act
    probabilities = remove_overround(home_odds, draw_odds, away_odds)

    # Assert
    assert sum(probabilities) == pytest.approx(Decimal("1.0000"), abs=Decimal("0.0001"))


def test_remove_overround_computes_known_probabilities():
    """Odds 2.50-3.70-2.80 produce the expected normalized probabilities."""
    # Act
    probabilities = remove_overround(
        Decimal("2.50"),
        Decimal("3.70"),
        Decimal("2.80"),
    )

    # Assert
    assert probabilities == pytest.approx(
        (Decimal("0.3893"), Decimal("0.2631"), Decimal("0.3476")),
        abs=Decimal("0.0001"),
    )


def test_remove_overround_gives_equal_thirds_for_equal_odds():
    """Equal odds (3.00 each) produce exactly equal probabilities of 1/3."""
    # Act
    probabilities = remove_overround(
        Decimal("3.00"),
        Decimal("3.00"),
        Decimal("3.00"),
    )

    # Assert
    third = Decimal(1) / Decimal(3)
    assert probabilities == (third, third, third)


def test_remove_overround_gives_favourite_near_certain_probability():
    """Heavy favourite odds produce a near-certain home probability."""
    # Act
    home_probability, _, _ = remove_overround(
        Decimal("1.10"),
        Decimal("8.00"),
        Decimal("15.00"),
    )

    # Assert
    assert home_probability > Decimal("0.8")


@pytest.mark.parametrize(
    ("home_odds", "draw_odds", "away_odds"),
    [
        (Decimal("0"), Decimal("3.70"), Decimal("2.80")),
        (Decimal("2.50"), Decimal("3.70"), Decimal("0")),
        (Decimal("-1.00"), Decimal("3.70"), Decimal("2.80")),
        (Decimal("2.50"), Decimal("-3.70"), Decimal("2.80")),
    ],
    ids=["home-zero", "away-zero", "home-negative", "draw-negative"],
)
def test_remove_overround_rejects_non_positive_odds(home_odds, draw_odds, away_odds):
    """Zero or negative odds (e.g. a missing field parsed as 0) raise ValueError."""
    with pytest.raises(ValueError, match="Odds must be positive"):
        remove_overround(home_odds, draw_odds, away_odds)
