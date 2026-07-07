"""API client for fetching Stryktipset data."""

import requests

from stryktips.models import Draw, Match, SvenskaFolket


def _parse_match(event: dict) -> Match:
    match = event["match"]
    home_team = match["participants"][0]["mediumName"]
    away_team = match["participants"][1]["mediumName"]
    event_number = event["eventNumber"]

    fulltime = next((r for r in match["result"] if r["type"] == 2), None)
    if fulltime:
        home_score = int(fulltime["home"])
        away_score = int(fulltime["away"])
    else:
        home_score = None
        away_score = None

    sf = event.get("svenskaFolket")
    if sf:
        svenska_folket = SvenskaFolket(
            one=sf.get("one", "0"), x=sf.get("x", "0"), two=sf.get("two", "0")
        )
    else:
        svenska_folket = None

    return Match(
        event_number=event_number,
        home_team=home_team,
        away_team=away_team,
        home_score=home_score,
        away_score=away_score,
        svenska_folket=svenska_folket,
    )


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
