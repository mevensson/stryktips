import subprocess
import sys


def test_week_argument_required():
    result = subprocess.run(
        [sys.executable, "stryktips.py"],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "--week" in result.stdout or "--week" in result.stderr


def test_week_4900_displays_13_matches():
    result = subprocess.run(
        [sys.executable, "stryktips.py", "--week", "4900"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "4900" in result.stdout
    matches = result.stdout.strip().split("\n")
    assert len(matches) == 14, f"Expected 14 lines (header + 13 matches), got {len(matches)}"
    assert "Bournemou" in result.stdout
    assert "Aston V" in result.stdout


def test_invalid_week_number_catches_error():
    result = subprocess.run(
        [sys.executable, "stryktips.py", "--week", "invalid"],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "invalid" in result.stderr or "invalid" in result.stdout


def test_help_shows_week_usage():
    result = subprocess.run(
        [sys.executable, "stryktips.py", "--help"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "--week" in result.stdout
