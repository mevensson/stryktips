# Issue #79: future end-date clamping

Part of https://github.com/mevensson/stryktips/issues/79.

## Goal

Add one focused E2E scenario in `tests/e2e/test_cli_report.py`: a future
`--end-date` resolves to the latest Draw dated on or before today. Include a
Draw dated exactly today and exclude later Draws already published in the
datepicker response.

Call `main(...)`, mock `requests.get`, and pin today using the existing fake
date pattern. Use real fixtures with consistent dates. Assert the full report,
empty stderr and exit code 0, and forbid later Draw requests. Use a future
bound in another month to verify resolution does not request that future month.

## Delivery

1. Commit this plan and open a draft PR before adding the E2E test.
2. Delegate the test-only change to `implementer`. If it passes immediately,
   commit `Test: ...` and record the passing baseline under the agreed exception.
3. If missing behavior makes it fail, commit `Red: ...` and use `/tdd-workflow`:
   `implementer` for unit red/green, `reviewer` for independent whole-project
   review, and `implementer` for applicable refactoring findings.
4. Verify unit/E2E tests, Ruff format/lint checks, Mypy and diff checks in Nix.
5. Ask the user to review and merge. After confirmed merge, check off the Future
   end date scenario in #79 and start the next slice from updated `main`.

README already documents end-date clamping to today; this scenario verifies
that contract. Update user-facing documentation if the interface changes.
