from dataclasses import dataclass


@dataclass
class SvenskaFolket:
    one: str
    x: str
    two: str


@dataclass
class Match:
    event_number: int
    home_team: str
    away_team: str
    home_score: int | None
    away_score: int | None
    svenska_folket: SvenskaFolket | None


@dataclass
class Draw:
    draw_number: int
    matches: list[Match]
