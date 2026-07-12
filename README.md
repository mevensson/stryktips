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
python stryktips.py --draw <number>
```

Without Nix:

```bash
pip install requests
python stryktips.py --draw <number>
```

## Arguments

| Argument   | Required | Type | Description                          |
| ---------- | -------- | ---- | ------------------------------------ |
| `--draw`   | Yes      | int  | Draw number for Stryktipset data     |

## Output

Each match is printed on one line:

```
1. Malmö - AIK | 1 | 45% - 30% - 25%
```

The fields are: event number, home team, away team, outcome (`1`/`X`/`2` or `?`),
and Svenska Folket percentage split.

## Development

- **Tests:** `pytest`
- **Linting/formatting:** `ruff`
- **Type checking:** `mypy`