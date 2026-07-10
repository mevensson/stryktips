"""Unit tests for odds probability calculations."""

from decimal import Decimal

import pytest

from stryktips.odds import remove_overround


def test_remove_overround_returns_normalized_probabilities():
    """Odds 2.50-3.70-2.80 produce probabilities summing to 1.0."""
    # Act
    home_p, draw_p, away_p = remove_overround(
        Decimal("2.50"),
        Decimal("3.70"),
        Decimal("2.80"),
    )

    # Assert
    assert home_p == pytest.approx(Decimal("0.3893"), abs=Decimal("0.0001"))
    assert draw_p == pytest.approx(Decimal("0.2631"), abs=Decimal("0.0001"))
    assert away_p == pytest.approx(Decimal("0.3476"), abs=Decimal("0.0001"))
    assert home_p + draw_p + away_p == pytest.approx(
        Decimal("1.0000"), abs=Decimal("0.0001"),
    )


def test_remove_overround_handles_equal_odds():
    """Equal odds (3.00 each) produce equal probabilities of 1/3."""
    # Act
    home_p, draw_p, away_p = remove_overround(
        Decimal("3.00"),
        Decimal("3.00"),
        Decimal("3.00"),
    )

    # Assert
    third = Decimal(1) / Decimal(3)
    assert home_p == third
    assert draw_p == third
    assert away_p == third


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
    assert home_p + draw_p + away_p == pytest.approx(
        Decimal("1.0000"), abs=Decimal("0.0001"),
    )
