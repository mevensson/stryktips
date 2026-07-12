from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass
class SvenskaFolket:
    one: str
    x: str
    two: str


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
    svenska_folket: SvenskaFolket | None
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
