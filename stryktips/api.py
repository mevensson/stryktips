"""API client for fetching Stryktipset data."""

import requests


def fetch_week(week_num: int) -> list[dict]:
    """Fetch Stryktipset draw data for a specific week.

    Args:
        week_num: The week number to fetch.

    Returns:
        List of draw events from the API.
    """
    if not isinstance(week_num, int):
        raise ValueError("Week number must be an integer")

    url = f"https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/{week_num}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    data = response.json()
    return data.get("draw", {}).get("drawEvents", [])
