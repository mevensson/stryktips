"""End-to-end tests for the --week CLI flag."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import requests
from flexmock import flexmock

from stryktips import main

_FIXTURES = Path(__file__).parent.parent / "fixtures"


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
    datepicker_data = json.loads((_FIXTURES / "datepicker_2025_05.json").read_text())
    draw_data = json.loads((_FIXTURES / "week_4900.json").read_text())

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


def test_week_2024_52_2_selects_second_draw(mock_response, capsys):  # noqa: PLR0915
    """--week 2024.52.2 resolves to the second draw of ISO week 52 of 2024."""
    datepicker_data = json.loads((_FIXTURES / "datepicker_2024_12.json").read_text())
    draw_data = json.loads((_FIXTURES / "week_4881.json").read_text())

    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
        "?product=stryktipset&year=2024&month=12",
        timeout=30,
    ).and_return(mock_response(datepicker_data))

    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/4881",
        timeout=30,
    ).and_return(mock_response(draw_data))

    exit_code = main(["--week", "2024.52.2"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Stryktipset v. 2024-52 (draw 4881)" in captured.out
    assert "West Ham" in captured.out
    assert captured.err == ""


def test_week_2024_52_3_exceeds_draw_count(mock_response, capsys):  # noqa: PLR0915
    """--week 2024.52.3 (only 2 draws that week) exits 1 with an error message."""
    datepicker_data = json.loads((_FIXTURES / "datepicker_2024_12.json").read_text())

    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
        "?product=stryktipset&year=2024&month=12",
        timeout=30,
    ).and_return(mock_response(datepicker_data))

    exit_code = main(["--week", "2024.52.3"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert (
        "Error: Week 2024.52 has 2 draws "
        "(dates: 2024-12-26, 2024-12-29). "
        "Use --week 2024.52.1 or --week 2024.52.2." in captured.err
    )
    assert captured.out == ""


def test_week_2020_15_forward_scans_to_june(mock_response, capsys):  # noqa: PLR0915
    """--week 2020.15 with no draw that week forward-scans from Monday."""
    empty_data: dict[str, list[Any]] = {"resultDates": []}
    for month in [4, 5]:
        flexmock(requests).should_receive("get").with_args(
            "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
            f"?product=stryktipset&year=2020&month={month}",
            timeout=30,
        ).and_return(mock_response(empty_data))

    june_data = json.loads((_FIXTURES / "datepicker_2020_06.json").read_text())
    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
        "?product=stryktipset&year=2020&month=6",
        timeout=30,
    ).and_return(mock_response(june_data))

    draw_data = json.loads((_FIXTURES / "week_4642.json").read_text())
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


# ISO week 2025.01 spans the 2024/2025 boundary. December 2024 is synthetic and
# incomplete (it lists only the later 2025-01-04 draw 4882); January 2025 is
# synthetic, unsorted and overlapping: it repeats 4882, then lists the earlier
# 2024-12-30 draw 4881 twice. Both draws are therefore only known once both
# month responses have been gathered.
_DECEMBER_2024_WEEK_2025_01: dict[str, Any] = {
    "resultDates": [
        {"date": "2025-01-04T00:00:00+01:00", "drawNumber": 4882},
    ]
}
_JANUARY_2025_WEEK_2025_01: dict[str, Any] = {
    "resultDates": [
        {"date": "2025-01-04T00:00:00+01:00", "drawNumber": 4882},
        {"date": "2024-12-30T00:00:00+01:00", "drawNumber": 4881},
        {"date": "2024-12-30T00:00:00+01:00", "drawNumber": 4881},
    ]
}
_WEEK_2025_01_EXCESSIVE_ERROR = (
    "Error: Week 2025.1 has 2 draws (dates: 2024-12-30, 2025-01-04). "
    "Use --week 2025.1.1 or --week 2025.1.2."
)


@pytest.mark.parametrize(
    ("week", "expected_draw", "expected_header", "expected_match"),
    [
        pytest.param(
            "2025.01",
            4881,
            "Stryktipset v. 2024-52 (draw 4881)",
            "West Ham",
            id="omitted-index-selects-first",
        ),
        pytest.param(
            "2025.01.1",
            4881,
            "Stryktipset v. 2024-52 (draw 4881)",
            "West Ham",
            id="first-index-selects-first",
        ),
        pytest.param(
            "2025.01.2",
            4882,
            "Stryktipset v. 2025-1 (draw 4882)",
            "Brighton",
            id="second-index-selects-second",
        ),
        pytest.param(
            "2025.01.3",
            None,
            None,
            None,
            id="excessive-index-rejected",
        ),
    ],
)
def test_week_2025_01_shared_across_months(  # noqa: PLR0913, PLR0915
    mock_response, capsys, week, expected_draw, expected_header, expected_match
):
    """``--week 2025.01`` selects distinct draws shared by two month responses.

    ISO week 2025.01 runs Mon 2024-12-30 to Sun 2025-01-05 and holds two distinct
    Draws: 4881 (2024-12-30) and 4882 (2025-01-04). No datepicker fixture holds
    both, so the monthly responses are synthetic, unsorted and overlapping:
    December 2024 lists only the later 4882, while January 2025 repeats 4882 and
    adds the earlier 4881 twice. The real week_4881 Draw fixture is reused with
    its in-memory ``regCloseTime`` moved to 2024-12-30 so it is dated inside the
    week. Both monthly responses must be gathered before selecting: omitted
    ``.N`` and ``.1`` select 4881, ``.2`` selects 4882, and the excessive ``.3``
    exits 1 naming the two distinct draws without fetching any Draw. Duplicate
    and overlapping entries must not inflate the distinct count.
    """
    first_draw: dict[str, Any] = json.loads((_FIXTURES / "week_4881.json").read_text())
    first_draw["draw"]["regCloseTime"] = "2024-12-30T15:59:00+01:00"
    second_draw: dict[str, Any] = json.loads((_FIXTURES / "week_4882.json").read_text())

    draw_url = "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/{n}"
    for number, payload in {4881: first_draw, 4882: second_draw}.items():
        expectation = (
            flexmock(requests)
            .should_receive("get")
            .with_args(draw_url.format(n=number), timeout=30)
        )
        if number == expected_draw:
            expectation.at_least().once().and_return(mock_response(payload))
        else:
            expectation.never()
    for out_of_range in (4879, 4880, 4883, 4884):
        flexmock(requests).should_receive("get").with_args(
            draw_url.format(n=out_of_range), timeout=30
        ).never()

    datepicker_url = (
        "https://api.spela.svenskaspel.se/draw/1/results/datepicker/"
        "?product=stryktipset&year={year}&month={month}"
    )
    flexmock(requests).should_receive("get").with_args(
        datepicker_url.format(year=2024, month=12), timeout=30
    ).at_least().once().and_return(mock_response(_DECEMBER_2024_WEEK_2025_01))
    flexmock(requests).should_receive("get").with_args(
        datepicker_url.format(year=2025, month=1), timeout=30
    ).at_least().once().and_return(mock_response(_JANUARY_2025_WEEK_2025_01))
    for year, month in ((2024, 11), (2025, 2), (2025, 3)):
        flexmock(requests).should_receive("get").with_args(
            datepicker_url.format(year=year, month=month), timeout=30
        ).never()

    exit_code = main(["--week", week])
    captured = capsys.readouterr()

    if expected_draw is None:
        assert exit_code == 1
        assert captured.err.splitlines() == [_WEEK_2025_01_EXCESSIVE_ERROR]
        assert captured.out == ""
    else:
        assert exit_code == 0
        assert expected_header in captured.out
        assert expected_match in captured.out
        assert captured.err == ""
