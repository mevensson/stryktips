"""Report formatting helpers."""

from decimal import Decimal


def bucket_index(probability: Decimal) -> int:
    """Map a probability in [0.0, 1.0] to a decade bucket 0..9 via [low, high)."""
    return min(int(probability * 10), 9)
