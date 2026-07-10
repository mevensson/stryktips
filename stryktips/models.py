from dataclasses import dataclass
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
class Match:
    event_number: int
    home_team: str
    away_team: str
    home_score: int | None
    away_score: int | None
    svenska_folket: SvenskaFolket | None
    odds: Odds | None = None


@dataclass
class Draw:
    draw_number: int
    matches: list[Match]
