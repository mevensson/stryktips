from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


@dataclass
class SvenskaFolket:
    one: Decimal
    x: Decimal
    two: Decimal


@dataclass
class Odds:
    home: Decimal
    draw: Decimal
    away: Decimal


@dataclass
class OutcomeProbability:
    home: Decimal
    draw: Decimal
    away: Decimal


@dataclass
class Match:
    event_number: int
    home_team: str
    away_team: str
    home_score: int | None
    away_score: int | None
    svenska_folket: SvenskaFolket | None = None
    odds: Odds | None = None
    outcome_probability: OutcomeProbability | None = None


@dataclass
class Draw:
    draw_number: int
    matches: list[Match]
    draw_comment: str | None = None
    reg_close_time: datetime | None = None


@dataclass
class DatepickerEntry:
    date: date
    draw_number: int


class MatchOutcome(Enum):
    """The realized outcome of a match: home win, draw, or away win."""

    HOME = "1"
    DRAW = "X"
    AWAY = "2"


def match_outcome(
    home_score: int | None, away_score: int | None
) -> MatchOutcome | None:
    """Classify the full-time score into a MatchOutcome, or None when unplayed."""
    if home_score is None or away_score is None:
        return None
    if home_score > away_score:
        return MatchOutcome.HOME
    if home_score < away_score:
        return MatchOutcome.AWAY
    return MatchOutcome.DRAW
