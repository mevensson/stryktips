"""Report formatting helpers."""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from itertools import chain

from stryktips.models import (
    Draw,
    Match,
    MatchOutcome,
    OutcomeProbability,
    match_outcome,
)


def bucket_index(probability: Decimal) -> int:
    """Map a probability in [0.0, 1.0] to a decade bucket 0..9 via [low, high)."""
    return min(int(probability * 10), 9)


@dataclass
class BucketStats:
    """Per-bucket accumulation of probability values and observed outcomes."""

    count: int = 0
    total: Decimal = Decimal("0")
    observed: int = 0


class _Tally(Enum):
    """How a match is classified for the report."""

    UNPLAYED = "unplayed"
    ELIGIBLE = "eligible"
    EXCLUDED = "excluded"


def format_report(draw: Draw) -> str:
    """Return a probability-bucket report of eligible and excluded matches in a draw."""
    buckets, eligible, excluded = _aggregate(draw.matches)
    return _format_bucket_report(buckets, eligible, excluded)


def format_aggregate_report(draws: list[Draw]) -> str:
    """Return a merged probability-bucket report across multiple draws."""
    matches = chain.from_iterable(draw.matches for draw in draws)
    buckets, eligible, excluded = _aggregate(matches)
    return _format_bucket_report(buckets, eligible, excluded)


def _aggregate(matches: Iterable[Match]) -> tuple[list[BucketStats], int, int]:
    """Return per-bucket stats and eligible/excluded counts for the given matches."""
    buckets = [BucketStats() for _ in range(10)]
    eligible = excluded = 0
    for match in matches:
        status = _tally_match(buckets, match)
        if status is _Tally.ELIGIBLE:
            eligible += 1
        elif status is _Tally.EXCLUDED:
            excluded += 1
    return buckets, eligible, excluded


def _tally_match(buckets: list[BucketStats], match: Match) -> _Tally:
    """Accumulate an eligible match's probabilities or classify it as excluded."""
    outcome = match_outcome(match.home_score, match.away_score)
    if outcome is None:
        return _Tally.UNPLAYED
    if match.outcome_probability is None:
        return _Tally.EXCLUDED
    _accumulate_probabilities(buckets, match.outcome_probability, outcome)
    return _Tally.ELIGIBLE


def _accumulate_probabilities(
    buckets: list[BucketStats],
    probabilities: OutcomeProbability,
    outcome: MatchOutcome,
) -> None:
    """Bucket each of the three probabilities, counting observed outcomes."""
    for probability, is_observed in (
        (probabilities.home, outcome is MatchOutcome.HOME),
        (probabilities.draw, outcome is MatchOutcome.DRAW),
        (probabilities.away, outcome is MatchOutcome.AWAY),
    ):
        stats = buckets[bucket_index(probability)]
        stats.count += 1
        stats.total += probability
        if is_observed:
            stats.observed += 1


def _format_bucket_report(
    buckets: list[BucketStats], eligible: int, excluded: int
) -> str:
    """Return a report string of the summary line and non-empty probability buckets."""
    lines = [f"eligible: {eligible}, excluded: {excluded}"]
    for index, stats in enumerate(buckets):
        if not stats.count:
            continue
        mean = round(stats.total / stats.count * 100)
        observed = round(stats.observed / stats.count * 100)
        gap = observed - mean
        lines.append(
            f"{index * 10}-{(index + 1) * 10}: {stats.count} | "
            f"{mean}% | {observed}% | {gap}%"
        )
    return "\n".join(lines)
