"""Report formatting helpers."""

from collections.abc import Iterable
from decimal import Decimal
from itertools import chain

from stryktips.models import Draw, Match, MatchOutcome, match_outcome


def bucket_index(probability: Decimal) -> int:
    """Map a probability in [0.0, 1.0] to a decade bucket 0..9 via [low, high)."""
    return min(int(probability * 10), 9)


def realized_probability(match: Match) -> Decimal | None:
    """Return the predicted probability of the realized outcome, or None if unknown."""
    outcome = match_outcome(match.home_score, match.away_score)
    if outcome is None or match.outcome_probability is None:
        return None
    if outcome is MatchOutcome.HOME:
        return match.outcome_probability.home
    if outcome is MatchOutcome.AWAY:
        return match.outcome_probability.away
    return match.outcome_probability.draw


def format_report(draw: Draw) -> str:
    """Return a probability-bucket report of eligible and excluded matches in a draw."""
    buckets, eligible, excluded = _aggregate(draw.matches)
    return _format_bucket_report(buckets, eligible, excluded)


def format_aggregate_report(draws: list[Draw]) -> str:
    """Return a merged probability-bucket report across multiple draws."""
    matches = chain.from_iterable(draw.matches for draw in draws)
    buckets, eligible, excluded = _aggregate(matches)
    return _format_bucket_report(buckets, eligible, excluded)


def _aggregate(matches: Iterable[Match]) -> tuple[list[int], int, int]:
    """Return probability buckets and eligible/excluded counts for the given matches."""
    buckets = [0] * 10
    eligible = excluded = 0
    for match in matches:
        if (probability := realized_probability(match)) is not None:
            eligible += 1
            buckets[bucket_index(probability)] += 1
        elif match.home_score is not None and match.away_score is not None:
            # Excluded: played but odds-less (unplayed matches are silently dropped).
            excluded += 1
    return buckets, eligible, excluded


def _format_bucket_report(buckets: list[int], eligible: int, excluded: int) -> str:
    """Return a report string of the summary line and non-empty probability buckets."""
    lines = [f"eligible: {eligible}, excluded: {excluded}"]
    lines.extend(
        f"{i * 10}-{(i + 1) * 10}: {count}" for i, count in enumerate(buckets) if count
    )
    return "\n".join(lines)
