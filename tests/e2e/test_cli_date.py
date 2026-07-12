"""End-to-end tests for the --date CLI flag."""

import json
from pathlib import Path
from typing import Any

import requests
from flexmock import flexmock

from stryktips import main


def test_date_2025_05_10_finds_draw_4900(capsys):
    """--date 2025-05-10 finds draw 4900 and displays it."""
    datepicker_data = {
        "datepicker": [
            {"date": "2025-05-05", "drawNumber": 4898},
            {"date": "2025-05-10", "drawNumber": 4900},
        ]
    }
    draw_data = json.loads(Path("tests/fixtures/week_4900.json").read_text())

    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
        "?product=stryktipset&year=2025&month=5",
        timeout=30,
    ).and_return(_mock_response(datepicker_data))

    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/4900",
        timeout=30,
    ).and_return(_mock_response(draw_data))

    exit_code = main(["--date", "2025-05-10"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Stryktipset v. 2025-19 (draw 4900)" in captured.out
    assert "Bournemou" in captured.out


def _mock_response(data: Any, status_code: int = 200) -> Any:
    mock = flexmock(status_code=status_code)
    mock.should_receive("json").and_return(data)
    mock.should_receive("raise_for_status").and_return(None)
    return mock
