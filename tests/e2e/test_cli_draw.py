import subprocess
import sys


def test_draw_argument_required():
    result = subprocess.run(
        [sys.executable, "stryktips.py"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "--draw" in result.stdout or "--draw" in result.stderr


def test_draw_4900_displays_13_matches():  # noqa: PLR0915
    result = subprocess.run(
        [sys.executable, "stryktips.py", "--draw", "4900"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.returncode == 0
    assert "4900" in result.stdout
    matches = result.stdout.strip().split("\n")
    assert len(matches) == 14, (
        f"Expected 14 lines (header + 13 matches), got {len(matches)}"
    )
    assert "Bournemou" in result.stdout
    assert "Aston V" in result.stdout
    assert "2.50" in result.stdout
    assert "3.70" in result.stdout
    assert "2.80" in result.stdout
    assert "39% - 26% - 35%" in result.stdout


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
