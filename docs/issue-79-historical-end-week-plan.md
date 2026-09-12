# Issue #79: historical two-Draw end week

Part of https://github.com/mevensson/stryktips/issues/79.

## Goal

Expand `test_end_week_resolves_to_draw` to a historical two-Draw week.
An omitted index and `.2` include both Draws; `.1` includes only the first.
Pin today, assert report contents, stderr and exit codes, and forbid excluded
Draw requests. Exercise `main(...)` with mocked HTTP requests.

## Delivery

1. Commit this plan and open a draft PR.
2. Commit the focused E2E change without implementation, after confirming its
   expected failure.
3. Use `/tdd-workflow`: delegate a failing unit test, delegate implementation
   until all unit tests pass, and perform the mandatory independent review.
   Repeat as needed until the E2E scenario passes.
4. Update user-facing documentation and run unit tests, E2E tests, Ruff format
   and lint checks, and strict Mypy inside the Nix development shell.
5. Ask the user to review and merge. Wait for merge before checking off the
   completed E2E task and fully satisfied acceptance criteria in #79.
6. Start the next slice from updated `main` only after that merge.

For later slices whose requested behavior already works, a test-only green PR
is allowed; record the passing baseline rather than manufacturing a failure.
