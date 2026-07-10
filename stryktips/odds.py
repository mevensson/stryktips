"""Odds probability calculations."""

from decimal import Decimal


def remove_overround(
    home_odds: Decimal,
    draw_odds: Decimal,
    away_odds: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    """Derive outcome probabilities by removing the bookmaker's overround.

    Converts decimal odds to implied probabilities and normalises so they
    sum to exactly 1.0.
    """
    implied_home = Decimal(1) / home_odds
    implied_draw = Decimal(1) / draw_odds
    implied_away = Decimal(1) / away_odds
    total = implied_home + implied_draw + implied_away

    return (
        implied_home / total,
        implied_draw / total,
        implied_away / total,
    )
