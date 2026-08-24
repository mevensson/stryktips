import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import requests
from flexmock import flexmock

from stryktips import main


def test_draw_argument_required():
    result = subprocess.run(
        [sys.executable, "stryktips.py"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "--draw" in result.stdout or "--draw" in result.stderr


def test_draw_4900_displays_13_matches(mock_response, capsys):  # noqa: PLR0915
    """--draw 4900 displays the header and all 13 matches."""
    draw_data: dict[str, Any] = json.loads(
        Path("tests/fixtures/week_4900.json").read_text()
    )
    flexmock(requests).should_receive("get").with_args(
        "https://api.spela.svenskaspel.se/draw/1/stryktipset/draws/4900",
        timeout=30,
    ).and_return(mock_response(draw_data))

    exit_code = main(["--draw", "4900"])
    captured = capsys.readouterr()

    assert exit_code == 0
    lines = captured.out.strip().split("\n")
    assert "Stryktipset v. 2025-19 (draw 4900)" in lines[0]
    assert len(lines) == 14, (
        f"Expected 14 lines (header + 13 matches), got {len(lines)}"
    )
    assert "Bournemou" in captured.out
    assert "Aston V" in captured.out
    assert "2.50" in captured.out
    assert "3.70" in captured.out
    assert "2.80" in captured.out
    assert "39% - 26% - 35%" in captured.out


def test_invalid_draw_number_catches_error():
    result = subprocess.run(
        [sys.executable, "stryktips.py", "--draw", "invalid"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "invalid" in result.stderr or "invalid" in result.stdout


def test_help_shows_draw_usage():
    result = subprocess.run(
        [sys.executable, "stryktips.py", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.returncode == 0
    assert "--draw" in result.stdout
