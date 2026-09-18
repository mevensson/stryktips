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
