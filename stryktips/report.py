"""Report formatting helpers."""

from decimal import Decimal


def bucket_index(probability: Decimal) -> int:
    """Dummy: assign every probability to bucket 0."""
    return 0