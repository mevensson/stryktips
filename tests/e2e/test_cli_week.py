"""End-to-end tests for the --week CLI flag."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import requests
from flexmock import flexmock

from stryktips import main


def test_invalid_week_is_rejected_by_argparse():
    result = subprocess.run(
        [sys.executable, "stryktips.py", "--week", "abc"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "usage:" in result.stderr.lower()
    assert "--week" in result.stderr


def test_week_2025_19_finds_draw_4900(mock_response, capsys):  # noqa: PLR0915
    """--week 2025.19 resolves to the draw for ISO week 19 of 2025."""
    datepicker_data = json.loads(
        Path("tests/fixtures/datepicker_2025_05.json").read_text()
    )
    draw_data = json.loads(Path("tests/fixtures/week_4900.json").read_text())

    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
        "?product=stryktipset&year=2025&month=5",
        timeout=30,
    ).and_return(mock_response(datepicker_data))

    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/4900",
        timeout=30,
    ).and_return(mock_response(draw_data))

    exit_code = main(["--week", "2025.19"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Stryktipset v. 2025-19 (draw 4900)" in captured.out
    assert "Bournemou" in captured.out
    assert captured.err == ""


def test_week_2020_15_forward_scans_to_june(mock_response, capsys):  # noqa: PLR0915
    """--week 2020.15 with no draw that week forward-scans from Monday."""
    empty_data: dict[str, list[Any]] = {"resultDates": []}
    for month in [4, 5]:
        flexmock(requests).should_receive("get").with_args(
            "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
            f"?product=stryktipset&year=2020&month={month}",
            timeout=30,
        ).and_return(mock_response(empty_data))

    june_data = json.loads(Path("tests/fixtures/datepicker_2020_06.json").read_text())
    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
        "?product=stryktipset&year=2020&month=6",
        timeout=30,
    ).and_return(mock_response(june_data))

    draw_data = json.loads(Path("tests/fixtures/draw_4642.json").read_text())
    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/4642",
        timeout=30,
    ).and_return(mock_response(draw_data))

    exit_code = main(["--week", "2020.15"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (
        "Note: No draw found for 2020.15, using 2020-06-20 (draw 4642)" in captured.err
    )
    assert "Stryktips v. 2020-25 (draw 4642)" in captured.out
