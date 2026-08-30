"""Report formatting helpers."""

from decimal import Decimal

from stryktips.models import Draw, Match


def bucket_index(probability: Decimal) -> int:
    """Map a probability in [0.0, 1.0] to a decade bucket 0..9 via [low, high)."""
    return min(int(probability * 10), 9)


def realized_probability(match: Match) -> Decimal | None:
    """Return the predicted probability of the realized outcome, or None if unknown."""
    if match.home_score is None or match.away_score is None:
        return None
    if match.outcome_probability is None:
        return None
    if match.home_score > match.away_score:
        return match.outcome_probability.home
    if match.home_score < match.away_score:
        return match.outcome_probability.away
    return match.outcome_probability.draw


def format_report(draws: list[Draw]) -> str:
    """Return a bucket report of eligible and excluded matches (not implemented)."""
    return ""
