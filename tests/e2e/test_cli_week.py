"""End-to-end tests for the --week CLI flag."""

import json
from pathlib import Path
from typing import Any

import requests
from flexmock import flexmock

from stryktips import main


def test_week_2025_19_finds_draw_4900(capsys):  # noqa: PLR0915
    """--week 2025.19 resolves to the draw for ISO week 19 of 2025."""
    datepicker_data = json.loads(
        Path("tests/fixtures/datepicker_2025_05.json").read_text()
    )
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

    exit_code = main(["--week", "2025.19"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Stryktipset v. 2025-19 (draw 4900)" in captured.out
    assert "Bournemou" in captured.out
    assert captured.err == ""


def test_week_2020_15_forward_scans_to_june(capsys):  # noqa: PLR0915
    """--week 2020.15 with no draw that week forward-scans from Monday."""
    empty_data: dict[str, list[Any]] = {"resultDates": []}
    for month in [4, 5]:
        flexmock(requests).should_receive("get").with_args(
            "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
            f"?product=stryktipset&year=2020&month={month}",
            timeout=30,
        ).and_return(_mock_response(empty_data))

    june_data = json.loads(Path("tests/fixtures/datepicker_2020_06.json").read_text())
    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
        "?product=stryktipset&year=2020&month=6",
        timeout=30,
    ).and_return(_mock_response(june_data))

    draw_data = json.loads(Path("tests/fixtures/draw_4642.json").read_text())
    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/4642",
        timeout=30,
    ).and_return(_mock_response(draw_data))

    exit_code = main(["--week", "2020.15"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (
        "Note: No draw found for 2020.15, using 2020-06-20 (draw 4642)"
        in captured.err
    )
    assert "Stryktips v. 2020-25 (draw 4642)" in captured.out


def _mock_response(data: Any, status_code: int = 200) -> Any:
    mock = flexmock(status_code=status_code)
    mock.should_receive("json").and_return(data)
    mock.should_receive("raise_for_status").and_return(None)
    return mock
