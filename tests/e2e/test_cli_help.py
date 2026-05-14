import subprocess
import sys


def test_cli_help_shows_usage_and_exits_zero():
    result = subprocess.run(
        [sys.executable, "stryktips.py", "--help"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        "Expected CLI help to exit with code 0; got {}."
        .format(result.returncode)
    )
    assert "usage:" in result.stdout.lower(), "Help output should include usage text."
    assert "--help" in result.stdout, "Help output should mention the --help option."
