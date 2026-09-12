# Issue #79: backward end-bound search across empty months

Part of https://github.com/mevensson/stryktips/issues/79.

## Goal

Add one parameterized E2E test in `tests/e2e/test_cli_report.py` covering
`--end-date` and unindexed `--end-week` bounds. Resolve backward from the
historical bound month through empty monthly responses, including datepicker
404s, to the latest preceding Draw.

Call `main(...)`, mock `requests.get`, and pin today. Assert the complete report,
empty stderr and exit code 0. Require the backward monthly requests and forbid
later Draw requests and an unnecessary today-month lookup. Use real Draw
fixtures and consistent datepicker responses.

## Delivery

1. Commit this plan and open a draft PR before changing E2E tests.
2. Delegate the focused E2E change to `implementer`, with no implementation.
   Run it against existing code; commit the expected failure as `Red: ...`, or
   record an immediately passing test-only slice as `Test: ...`.
3. If red, use `/tdd-workflow`: `implementer` for separate unit red/green steps,
   `reviewer` for mandatory independent whole-project review, and `implementer`
   for applicable refactoring findings. Repeat until the E2E test is green.
4. Run unit/E2E tests, Ruff format/lint checks, Mypy and diff checks in Nix.
5. Ask the user to review and merge. Confirm merge before checking off the
   backward-search scenario in #79 and starting another slice.

README already documents bounded backward date/unindexed-week resolution.
Update user-facing documentation if implementation changes alter that contract.
