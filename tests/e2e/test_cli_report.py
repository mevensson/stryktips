import subprocess
import sys


def test_help_shows_start_end_usage():
    result = subprocess.run(
        [sys.executable, "stryktips.py", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.returncode == 0
    assert "--start" in result.stdout
    assert "--end" in result.stdout


def test_start_argument_required():
    result = subprocess.run(
        [sys.executable, "stryktips.py"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "--start" in result.stdout or "--start" in result.stderr
    assert "--end" in result.stdout or "--end" in result.stderr