"""API client for fetching Stryktipset data."""

from decimal import Decimal
from typing import Any

import requests

from stryktips.models import Draw, Match, Odds, OutcomeProbability, SvenskaFolket
from stryktips.odds import remove_overround

_RESULT_TYPE_FULLTIME = 2


def fetch_week(week_num: int) -> Draw:
    """Fetch Stryktipset draw data for a specific week.

    Args:
        week_num: The week number to fetch.

    Returns:
        A Draw containing parsed match data.
    """
    url = f"https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/{week_num}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    data = response.json()
    draw_data = data.get("draw", {})
    draw_number = draw_data.get("drawNumber", 0)
    events = draw_data.get("drawEvents", [])
    matches = [_parse_match(event) for event in events]

    return Draw(draw_number=draw_number, matches=matches)


def _parse_match(event: dict[str, Any]) -> Match:
    match = event["match"]
    home_score, away_score = _parse_scores(match)
    svenska_folket = _parse_svenska_folket(event)
    odds = _parse_odds(event)
    outcome_probability = _compute_outcome_probability(odds)

    return Match(
        event_number=event["eventNumber"],
        home_team=match["participants"][0]["mediumName"],
        away_team=match["participants"][1]["mediumName"],
        home_score=home_score,
        away_score=away_score,
        svenska_folket=svenska_folket,
        odds=odds,
        outcome_probability=outcome_probability,
    )


def _compute_outcome_probability(odds: Odds | None) -> OutcomeProbability | None:
    if odds is None:
        return None
    home_p, draw_p, away_p = remove_overround(odds.home, odds.draw, odds.away)
    return OutcomeProbability(home=home_p, draw=draw_p, away=away_p)


def _parse_scores(match: dict[str, Any]) -> tuple[int | None, int | None]:
    for r in match["result"]:
        if r["type"] == _RESULT_TYPE_FULLTIME:
            return int(r["home"]), int(r["away"])
    return None, None


def _parse_svenska_folket(event: dict[str, Any]) -> SvenskaFolket | None:
    sf = event.get("svenskaFolket")
    if sf:
        return SvenskaFolket(
            one=sf.get("one", "0"),
            x=sf.get("x", "0"),
            two=sf.get("two", "0"),
        )
    return None


def _parse_odds(event: dict[str, Any]) -> Odds | None:
    start_odds = event.get("startOdds")
    if start_odds:
        return Odds(
            home=_parse_swedish_decimal(start_odds["one"]),
            draw=_parse_swedish_decimal(start_odds["x"]),
            away=_parse_swedish_decimal(start_odds["two"]),
        )
    return None


def _parse_swedish_decimal(value: str) -> Decimal:
    return Decimal(value.replace(",", "."))
