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


def format_report(draw: Draw) -> str:
    """Return a probability-bucket report of eligible and excluded matches in a draw."""
    buckets, eligible, excluded = _aggregate(draw)
    lines = [f"eligible: {eligible}, excluded: {excluded}"]
    lines.extend(
        f"{i * 10}-{(i + 1) * 10}: {count}" for i, count in enumerate(buckets) if count
    )
    return "\n".join(lines)


def _aggregate(draw: Draw) -> tuple[list[int], int, int]:
    """Return probability buckets and eligible/excluded counts for a draw's matches."""
    buckets = [0] * 10
    eligible = excluded = 0
    for match in draw.matches:
        if (probability := realized_probability(match)) is not None:
            eligible += 1
            buckets[bucket_index(probability)] += 1
        elif match.home_score is not None and match.away_score is not None:
            # Excluded: played but odds-less (unplayed matches are silently dropped).
            excluded += 1
    return buckets, eligible, excluded
