"""Report formatting helpers."""

from decimal import Decimal

from stryktips.models import Match


def bucket_index(probability: Decimal) -> int:
    """Map a probability in [0.0, 1.0] to a decade bucket 0..9 via [low, high)."""
    return min(int(probability * 10), 9)


def realized_probability(match: Match) -> Decimal | None:
    """Return the predicted probability of the outcome that actually happened."""
    return None
