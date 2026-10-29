"""Shared support for the end-to-end prediction-quality report tests.

Fixture loading, the concrete request URLs, and the clock-injection seam are
shared by the report end-bound test modules. Requests are mocked by the caller
so the real API adapter and parser run against JSON fixtures.
"""

import json
from collections import Counter
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import requests
from flexmock import flexmock

import stryktips.core as stryktips_core
from stryktips.core import create_dependencies

FIXTURES = Path(__file__).parent.parent / "fixtures"

DRAW_URL = "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/{n}"
DATEPICKER_URL = (
    "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
    "?product=stryktipset&year={year}&month={month}"
)

# Literal expectations shared by tests selecting the same fixture draws.
DRAWS_4881_TO_4884_REPORT = [
    "eligible: 47, excluded: 0",
    "0-10: 1 | 8% | 100% | 92%",
    "10-20: 24 | 16% | 8% | -8%",
    "20-30: 57 | 26% | 30% | 4%",
    "30-40: 19 | 35% | 37% | 2%",
    "40-50: 14 | 44% | 50% | 6%",
    "50-60: 14 | 55% | 36% | -19%",
    "60-70: 9 | 65% | 67% | 2%",
    "70-80: 3 | 74% | 67% | -7%",
]

DRAW_4900_REPORT = [
    "eligible: 13, excluded: 0",
    "0-10: 1 | 8% | 0% | -8%",
    "10-20: 4 | 17% | 25% | 8%",
    "20-30: 15 | 25% | 33% | 8%",
    "30-40: 10 | 36% | 30% | -6%",
    "40-50: 3 | 42% | 33% | -9%",
    "50-60: 5 | 56% | 60% | 4%",
    "70-80: 1 | 79% | 0% | -79%",
]

DRAW_4880_REPORT = [
    "eligible: 13, excluded: 0",
    "0-10: 2 | 7% | 0% | -7%",
    "10-20: 1 | 15% | 100% | 85%",
    "20-30: 18 | 26% | 22% | -4%",
    "30-40: 8 | 35% | 38% | 3%",
    "40-50: 6 | 43% | 50% | 7%",
    "50-60: 2 | 54% | 50% | -4%",
    "60-70: 1 | 65% | 0% | -65%",
    "80-90: 1 | 86% | 100% | 14%",
]

DRAWS_4880_TO_4881_REPORT = [
    "eligible: 26, excluded: 0",
    "0-10: 2 | 7% | 0% | -7%",
    "10-20: 7 | 16% | 29% | 13%",
    "20-30: 34 | 26% | 26% | 0%",
    "30-40: 14 | 34% | 29% | -5%",
    "40-50: 10 | 43% | 40% | -3%",
    "50-60: 5 | 53% | 60% | 7%",
    "60-70: 5 | 64% | 60% | -4%",
    "80-90: 1 | 86% | 100% | 14%",
]

# A 12-month backward window anchored on May 2025, crossing the year boundary.
BACKWARD_MONTHS_FROM_MAY_2025 = [
    (2025, 5),
    (2025, 4),
    (2025, 3),
    (2025, 2),
    (2025, 1),
    (2024, 12),
    (2024, 11),
    (2024, 10),
    (2024, 9),
    (2024, 8),
    (2024, 7),
    (2024, 6),
]


def load_fixture(name: str) -> dict[str, Any]:
    """Load a JSON fixture by file name."""
    data: dict[str, Any] = json.loads((FIXTURES / name).read_text())
    return data


def inject_clock(today: date) -> None:
    """Fix the clock through the composition seam while keeping the real API I/O."""
    flexmock(
        stryktips_core,
        create_dependencies=lambda: create_dependencies(clock=lambda: today),
    )


def mock_multi_year_requests(  # noqa: PLR0915
    monkeypatch: pytest.MonkeyPatch,
    mock_response: Callable[..., Any],
    draw_dates: dict[int, date],
    monthly_numbers: dict[tuple[int, int], tuple[int, ...]],
    fetched_draws: tuple[int, ...],
) -> None:
    """Serve only a finite Jan 2023–Jan 2025 walk and the allowed Draws.

    Month lookups may repeat for endpoint resolution and collection independently.
    Any out-of-range Draw or month past the terminal response fails immediately.
    """
    responses = {}
    for year, month in [
        *((2023, month) for month in range(1, 13)),
        *((2024, month) for month in range(1, 13)),
        (2025, 1),
    ]:
        responses[DATEPICKER_URL.format(year=year, month=month)] = mock_response(
            {
                "resultDates": [
                    {"date": draw_dates[number].isoformat(), "drawNumber": number}
                    for number in monthly_numbers.get((year, month), ())
                ]
            }
        )
    draw_urls = {DRAW_URL.format(n=number) for number in fetched_draws}
    for number in fetched_draws:
        responses[DRAW_URL.format(n=number)] = mock_response(
            multi_year_draw_payload(number, draw_dates[number])
        )
    requested: Counter[str] = Counter()

    def get(url: str, *, timeout: int) -> Any:
        assert timeout == 30
        assert url in responses, f"Unexpected API request: {url}"
        requested[url] += 1
        if url in draw_urls:
            assert requested[url] == 1, f"Duplicate Draw fetch: {url}"
        return responses[url]

    monkeypatch.setattr(requests, "get", get)


def multi_year_draw_payload(number: int, close_date: date) -> dict[str, Any]:
    """Build a 13-Match Draw: two eligible, one odds-less played, ten unplayed.

    Odds 2/4/4 give probabilities 50/25/25. One home win and one draw give
    four quarter-probability samples (one observed), and two half-probability
    samples (one observed) per Draw, so both buckets have zero calibration delta.
    """
    events = []
    for event_number in range(1, 14):
        match: dict[str, Any] = {
            "participants": [{"mediumName": "Home"}, {"mediumName": "Away"}],
        }
        if event_number <= 3:
            match["result"] = [
                {"type": 2, "home": "0" if event_number == 2 else "1", "away": "0"}
            ]
        event: dict[str, Any] = {"eventNumber": event_number, "match": match}
        if event_number <= 2:
            event["startOdds"] = {"one": "2", "x": "4", "two": "4"}
        events.append(event)
    return {
        "draw": {
            "drawNumber": number,
            "regCloseTime": f"{close_date.isoformat()}T15:59:00+01:00",
            "drawEvents": events,
        }
    }
