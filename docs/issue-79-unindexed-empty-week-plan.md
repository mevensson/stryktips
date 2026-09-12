# Issue #79: unindexed drawless end week

Part of https://github.com/mevensson/stryktips/issues/79.

## Goal

Add one E2E scenario in `tests/e2e/test_cli_report.py`: an unindexed historical
end week containing no Draws resolves to the latest preceding Draw without a
warning. Pin today, call `main(...)`, mock `requests.get`, and assert the report,
stderr and exit code. Forbid later Draw requests and an unnecessary today-month
lookup. Use real Draw fixtures and a datepicker response consistent with them.

## Delivery

1. Commit this plan and open a draft PR before adding the test.
2. Run the new E2E scenario against the existing implementation. If already
   green, commit test-only coverage and record that result, as agreed.
3. If it fails because behavior is missing, commit the failing E2E test and use
   `/tdd-workflow` with delegated unit red/green steps and mandatory review.
4. Run unit/E2E tests, Ruff format/lint checks, Mypy, and diff checks in Nix.
5. Ask the user to review and merge. After confirmed merge, check off the
   completed scenario in #79 and continue from updated `main`.

README already documents this fallback without a warning. This slice verifies
that existing documented behavior.
