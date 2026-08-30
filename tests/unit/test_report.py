"""Unit tests for report probability bucket assignment."""

from decimal import Decimal

import pytest

from stryktips.report import bucket_index


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