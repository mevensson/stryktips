"""API client for fetching Stryktipset data."""

from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import requests

from stryktips.models import (
    DatepickerEntry,
    Draw,
    Match,
    Odds,
    OutcomeProbability,
    SvenskaFolket,
)
from stryktips.odds import remove_overround

_RESULT_TYPE_FULLTIME = 2
_NOT_FOUND = 404
_MIN_PARTICIPANTS = 2
_API_DRAWS = "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws"
_API_DATEPICKER = "https://api.spela.svenskaspel.se/draw/1/results/datepicker"


def fetch_draw(draw_number: int) -> Draw:
    """Fetch Stryktipset draw data for a specific draw.

    Args:
        draw_number: The draw number to fetch.

    Returns:
        A Draw containing parsed match data.
    """
    url = f"{_API_DRAWS}/{draw_number}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    data = response.json()
    draw_data = data.get("draw", {})
    events = draw_data.get("drawEvents", [])
    matches = [_parse_match(event) for event in events]

    return Draw(
        draw_number=draw_data.get("drawNumber", 0),
        matches=matches,
        draw_comment=draw_data.get("drawComment"),
        reg_close_time=_parse_datetime(draw_data.get("regCloseTime")),
    )


def fetch_draws_by_month(year: int, month: int) -> list[DatepickerEntry]:
    """Fetch datepicker entries for a given month.

    Args:
        year: The year to query.
        month: The month to query (1-12).

    Returns:
        A list of DatepickerEntry for draws in that month.
    """
    url = f"{_API_DATEPICKER}/?product=stryktipset&year={year}&month={month}"
    response = requests.get(url, timeout=30)
    if response.status_code == _NOT_FOUND:
        return []
    response.raise_for_status()

    data = response.json()
    entries = data.get("resultDates") or data.get("datepicker") or []
    return [_parse_datepicker_entry(e) for e in entries]


def _parse_datepicker_entry(entry: dict[str, Any]) -> DatepickerEntry:
    raw_date = entry["date"]
    if "T" in raw_date:
        raw_date = raw_date.split("T")[0]
    return DatepickerEntry(
        date=date.fromisoformat(raw_date),
        draw_number=entry["drawNumber"],
    )


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _parse_match(event: dict[str, Any]) -> Match:
    match = event["match"]
    home_team, away_team = _parse_participants(match)
    home_score, away_score = _parse_scores(match)
    svenska_folket = _parse_svenska_folket(event)
    odds = _parse_odds(event)
    outcome_probability = _compute_outcome_probability(odds)

    return Match(
        event_number=event["eventNumber"],
        home_team=home_team,
        away_team=away_team,
        home_score=home_score,
        away_score=away_score,
        svenska_folket=svenska_folket,
        odds=odds,
        outcome_probability=outcome_probability,
    )


def _parse_participants(match: dict[str, Any]) -> tuple[str, str]:
    participants = match.get("participants") or []
    if len(participants) < _MIN_PARTICIPANTS:
        msg = "Match is missing home/away participants"
        raise ValueError(msg)
    return participants[0]["mediumName"], participants[1]["mediumName"]


def _compute_outcome_probability(odds: Odds | None) -> OutcomeProbability | None:
    if odds is None:
        return None
    home_p, draw_p, away_p = remove_overround(odds.home, odds.draw, odds.away)
    return OutcomeProbability(home=home_p, draw=draw_p, away=away_p)


def _parse_scores(match: dict[str, Any]) -> tuple[int | None, int | None]:
    for r in match.get("result", []):
        if r["type"] == _RESULT_TYPE_FULLTIME:
            return int(r["home"]), int(r["away"])
    return None, None


def _parse_svenska_folket(event: dict[str, Any]) -> SvenskaFolket | None:
    sf = event.get("svenskaFolket")
    if sf:
        one, x, two = _parse_three_decimal(sf)
        return SvenskaFolket(one=one, x=x, two=two)
    return None


def _parse_odds(event: dict[str, Any]) -> Odds | None:
    start_odds = event.get("startOdds")
    if start_odds:
        home, draw, away = _parse_three_decimal(start_odds)
        return Odds(home=home, draw=draw, away=away)
    return None


def _parse_three_decimal(source: Mapping[str, Any]) -> tuple[Decimal, Decimal, Decimal]:
    """Parse the one/x/two decimal fields shared by odds and svenskaFolket."""
    return (
        _parse_swedish_decimal(source.get("one", "0")),
        _parse_swedish_decimal(source.get("x", "0")),
        _parse_swedish_decimal(source.get("two", "0")),
    )


def _parse_swedish_decimal(value: object) -> Decimal:
    if value is None:
        return Decimal(0)
    return Decimal(str(value).replace(",", "."))
