# stryktips

A CLI tool that fetches and displays Swedish Stryktipset match data from the
Svenska Spel API.

## Prerequisites

- Python 3.14+
- [requests](https://pypi.org/project/requests/)

## Running

With Nix/direnv:

```bash
direnv allow   # or: nix develop
python stryktips.py --draw 4900
python stryktips.py --date 2025-05-10
```

Without Nix:

```bash
pip install requests
python stryktips.py --draw 4900
python stryktips.py --date 2025-05-10
```

## Arguments

| Argument   | Required | Type | Description                                        |
| ---------- | -------- | ---- | -------------------------------------------------- |
| `--draw`   | Yes*     | int  | Draw number for Stryktipset data                   |
| `--date`   | Yes*     | str  | Calendar date (YYYY-MM-DD) to find the draw on or after |

*Exactly one of `--draw` or `--date` is required.

## Behavior

- `--date` resolves the closest draw on or after the given date. The anchor
  month is searched first; if no match is found, the search advances
  month-by-month for up to 12 months.
- When the match is inexact (no draw on the exact date), a note is printed
  to stderr: `Note: No draw found for 2025-01-01, using 2025-01-04 (draw 4882)`.
- When no draw is found within 12 months, the program exits with code 1 and
  prints a message to stderr.

## Output

The header line shows the draw comment and number:

```
Stryktipset v. 2025-1 (draw 4882)
```

Each match is printed on one line:

```
1. Brighton - Arsenal | X | 16% - 24% - 60% | 4.60 - 4.00 - 1.79 | 21% - 24% - 54%
```

The pipe-separated fields are:

1. Event number, home team, away team
2. Outcome (`1`/`X`/`2` or `?` if the match hasn't been played)
3. Svenska Folket public betting percentages (1 - X - 2)
4. Decimal odds (1 - X - 2) — omitted when unavailable
5. Estimated true probabilities (1 - X - 2) — derived by removing overround; omitted when unavailable

## Development

- **Tests:** `pytest`
- **Linting/formatting:** `ruff`
- **Type checking:** `mypy`