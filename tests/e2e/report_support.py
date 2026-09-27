"""Shared support for the end-to-end prediction-quality report tests.

Fixture loading, the concrete request URLs, and the clock-injection seam are
shared by the report end-bound test modules. Requests are mocked by the caller
so the real API adapter and parser run against JSON fixtures.
"""

import json
from datetime import date
from pathlib import Path
from typing import Any

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
