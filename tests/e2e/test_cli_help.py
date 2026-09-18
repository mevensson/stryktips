import subprocess
import sys

_EXPECTED_OPTIONS = """\
  -h, --help            show this help message and exit
  --draw DRAW           Draw number for Stryktipset data
  --date DATE           Calendar date (YYYY-MM-DD) of the draw
  --week WEEK           ISO week (YYYY.WW[.N]) of the draw
  --start-draw START_DRAW
                        Start draw number for the prediction-quality report
  --start-date START_DATE
                        Calendar date (YYYY-MM-DD) of the report start draw
  --start-week START_WEEK
                        ISO week (YYYY.WW[.N]) of the report start draw
  --end-draw END_DRAW   End draw number for the prediction-quality report
  --end-date END_DATE   Calendar date (YYYY-MM-DD) of the report end draw
  --end-week END_WEEK   ISO week (YYYY.WW[.N]) of the report end draw
"""


def test_cli_help_shows_usage_and_exits_zero():
    result = subprocess.run(
        [sys.executable, "stryktips.py", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.returncode == 0, (
        f"Expected CLI help to exit with code 0; got {result.returncode}."
    )
    assert "usage:" in result.stdout.lower(), "Help output should include usage text."
    assert "--help" in result.stdout, "Help output should mention the --help option."


def test_cli_help_lists_options_in_exact_declared_order():
    result = subprocess.run(
        [sys.executable, "stryktips.py", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )

    options_section = result.stdout.split("options:\n", 1)[1]

    assert options_section == _EXPECTED_OPTIONS
