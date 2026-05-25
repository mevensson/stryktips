"""Display formatting for Stryktipset matches."""


def format_matches(events: list[dict]) -> list[str]:
    """Format draw events into display strings.

    Args:
        events: List of draw event dictionaries from API.

    Returns:
        List of formatted match strings.
    """
    result = []
    for event in events:
        match = event["match"]
        home = match["participants"][0]["mediumName"]
        away = match["participants"][1]["mediumName"]
        event_num = event["eventNumber"]

        # Find fulltime result (type 2)
        fulltime = next((r for r in match["result"] if r["type"] == 2), None)
        if fulltime:
            home_score = int(fulltime["home"])
            away_score = int(fulltime["away"])
            if home_score > away_score:
                outcome = "1"
            elif home_score < away_score:
                outcome = "2"
            else:
                outcome = "X"
        else:
            outcome = "?"

        # Get svenska folket percentages
        sf = event.get("svenskaFolket", {})
        one = sf.get("one", "0")
        x = sf.get("x", "0")
        two = sf.get("two", "0")

        formatted = f"{event_num}. {home} - {away} | {outcome} | {one}% - {x}% - {two}%"
        result.append(formatted)

    return result