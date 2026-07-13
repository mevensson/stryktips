"""End-to-end tests for the --date CLI flag."""

import json
from pathlib import Path
from typing import Any

import requests
from flexmock import flexmock

from stryktips import main


def test_date_2025_05_10_finds_draw_4900(capsys):  # noqa: PLR0915
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
    assert captured.err == ""


def test_date_2020_04_01_forward_scans_to_june(capsys):  # noqa: PLR0915
    """--date 2020-04-01 forward-scans through empty months to find draw 4642."""
    empty_data: dict[str, list[Any]] = {"datepicker": []}
    for month in [4, 5]:
        flexmock(requests).should_receive("get").with_args(
            "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
            f"?product=stryktipset&year=2020&month={month}",
            timeout=30,
        ).and_return(_mock_response(empty_data))

    june_data = {
        "datepicker": [
            {"date": "2020-06-20", "drawNumber": 4642},
            {"date": "2020-06-27", "drawNumber": 4643},
        ]
    }
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

    exit_code = main(["--date", "2020-04-01"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (
        "Note: No draw found for 2020-04-01, using 2020-06-20 (draw 4642)"
        in captured.err
    )
    assert "Stryktips v. 2020-25 (draw 4642)" in captured.out


def test_date_2000_01_01_no_draw_12_months(capsys):
    """--date 2000-01-01 with no draws in 12 months exits with 1 and stderr."""
    import pytest

    empty_data: dict[str, list[Any]] = {"datepicker": []}
    for month in range(1, 13):
        flexmock(requests).should_receive("get").with_args(
            "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
            f"?product=stryktipset&year=2000&month={month}",
            timeout=30,
        ).and_return(_mock_response(empty_data))

    with pytest.raises(SystemExit) as exc:
        main(["--date", "2000-01-01"])
    captured = capsys.readouterr()

    assert exc.value.code == 1
    assert "No draw found within 12 months of 2000-01-01" in captured.err


def test_date_invalid_date_returns_exit_code_1(capsys):
    """--date with an unparseable string exits with 1."""
    exit_code = main(["--date", "not-a-date"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Invalid date" in captured.out


def test_date_no_match_returns_exit_code_1(capsys):
    """--date for 12 months with no matching draw exits with SystemExit(1)."""
    import pytest

    datepicker_data: dict[str, list[Any]] = {"datepicker": []}
    for month in range(1, 13):
        flexmock(requests).should_receive("get").with_args(
            "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
            f"?product=stryktipset&year=2099&month={month}",
            timeout=30,
        ).and_return(_mock_response(datepicker_data))

    with pytest.raises(SystemExit) as exc:
        main(["--date", "2099-01-01"])
    captured = capsys.readouterr()

    assert exc.value.code == 1
    assert "No draw found within 12 months of 2099-01-01" in captured.err


def _mock_response(data: Any, status_code: int = 200) -> Any:
    mock = flexmock(status_code=status_code)
    mock.should_receive("json").and_return(data)
    mock.should_receive("raise_for_status").and_return(None)
    return mock
