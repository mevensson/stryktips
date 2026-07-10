"""Unit tests for odds probability calculations."""

from decimal import Decimal

from stryktips.odds import remove_overround


def test_remove_overround_returns_normalized_probabilities():
    """Odds 2.50-3.70-2.80 produce probabilities summing to 100%."""
    # Act
    home_p, draw_p, away_p = remove_overround(
        Decimal("2.50"),
        Decimal("3.70"),
        Decimal("2.80"),
    )

    # Assert
    assert home_p == Decimal("0.3893")
    assert draw_p == Decimal("0.2631")
    assert away_p == Decimal("0.3476")
    assert home_p + draw_p + away_p == Decimal("1.0000")


def test_remove_overround_handles_equal_odds():
    """Equal odds (3.00 each) produce equal probabilities."""
    # Act
    home_p, draw_p, away_p = remove_overround(
        Decimal("3.00"),
        Decimal("3.00"),
        Decimal("3.00"),
    )

    # Assert
    expected = Decimal("0.3333")
    assert home_p == expected
    assert draw_p == expected
    assert away_p == expected


def test_remove_overround_handles_heavy_favourite():
    """Heavy favourite odds produce near-certain probability."""
    # Act
    home_p, draw_p, away_p = remove_overround(
        Decimal("1.10"),
        Decimal("8.00"),
        Decimal("15.00"),
    )

    # Assert
    assert home_p > Decimal("0.8")
    assert home_p + draw_p + away_p == Decimal("1.0000")
