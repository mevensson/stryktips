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
python stryktips.py --week 2025.19
```

Without Nix:

```bash
pip install requests
python stryktips.py --draw 4900
python stryktips.py --date 2025-05-10
python stryktips.py --week 2025.19
```

## Arguments

| Argument   | Required | Type | Description                                        |
| ---------- | -------- | ---- | -------------------------------------------------- |
| `--draw`   | Yes*     | int  | Draw number for Stryktipset data                   |
| `--date`   | Yes*     | str  | Calendar date (YYYY-MM-DD) to find the draw on or after |
| `--week`   | Yes*     | str  | ISO week (YYYY.WW[.N]) to find the draw on or after its Monday; `.N` selects the N-th draw dated within that week (1-indexed) |
| `--start`  | Yes*     | int  | Start draw number for the prediction-quality report |
| `--end`    | Yes*     | int  | End draw number for the prediction-quality report |

*Exactly one of `--draw`, `--date`, `--week`, or the `--start`/`--end` pair is
required. `--start` requires `--end` and vice versa; the pair is mutually
exclusive with the other selectors.

## Behavior

- `--date` resolves the closest draw on or after the given date. The anchor
  month is searched first; if no match is found, the search advances
  month-by-month for up to 12 months.
- `--week` resolves the draw in the given ISO week (YYYY.WW[.N]): the week's
  Monday is used as the anchor and the draw dated within that ISO week
  (Monday-Sunday) is returned. An optional `.N` suffix selects the N-th draw
  dated within that week (1-indexed). The same month-by-month forward scan
  applies when no entry is found in the anchor month.
- When the match is inexact (no draw on the exact date), a note is printed
  to stderr: `Note: No draw found for 2025-01-01, using 2025-01-04 (draw 4882)`.
- When no draw is found within 12 months, the program exits with code 1 and
  prints a message to stderr.
- `--start`/`--end` print a prediction-quality report to stdout: a summary line
  with the eligible/excluded match counts, then one row per 10%-wide bucket of
  the predicted probability of the outcome that actually happened. A match is
  eligible iff it has a final score and `startOdds`; played-but-odds-less
  matches count toward the excluded total, and unplayed matches are ignored.

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

### Prediction-quality report

`--start`/`--end` print one report per draw, e.g. for `--start 4900 --end 4900`:

```
eligible: 13, excluded: 0
10-20: 1
20-30: 5
30-40: 3
40-50: 1
50-60: 3
```

Buckets with a zero count are omitted.

## Development

- **Tests:** `pytest`
- **Linting/formatting:** `ruff`
- **Type checking:** `mypy`