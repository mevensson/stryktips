---
name: tdd-workflow
description: >-
  Use when the user asks you to implement a new feature, add functionality, or
  develop something new. Also use when the user asks you to fix a bug or defect.
---

# tdd-workflow

**Before every commit**, run the following checks. Fix issues automatically where
possible; otherwise fix them manually. If you are unable to resolve an issue,
flag the user.

1. `ruff format .` (fixes formatting automatically)
2. `ruff check --fix .` (auto-fixes what it can); if `ruff check .` still reports
   issues, fix them manually
3. `mypy .` — fix any type errors manually
4. `pytest` — verify expected results per phase:
   - **Red (unit / e2e):** the new test(s) must fail; all existing tests must
     pass. If an existing test fails unexpectedly, fix the implementation to keep
     it passing. If you can't resolve it, flag the user.
   - **Green:** all tests must pass. If any test fails, fix the implementation.
     If you can't resolve it, flag the user.
   - **Refactor:** all tests must pass. If any test fails, fix the
     implementation. If you can't resolve it, flag the user.

1. If the task is purely informational (no code change needed), exit this skill and proceed normally.

2. Determine the branch:
   - **New feature** → Two-Level TDD (step 3)
   - **Bug fix** → One-Level TDD (step 4)

3. **New Feature (Two-Level TDD):**
   1. Write a failing end-to-end test → commit `Red (e2e): <feature description>`
   2. Inner loop — repeat until the e2e test passes:
      1. Write a failing unit test → commit `Red (unit): <sub-component description>`
      2. Add the minimal code to make it pass → commit `Green: <sub-component description>`
      3. Refactor → commit `Refactor: <sub-component description>`

4. **Bug Fix (One-Level TDD):**
   1. Write a failing unit test that reproduces the bug → commit `Red: <bug description>`
   2. Add the minimal code to make it pass → commit `Green: <bug description>`
   3. Refactor → commit `Refactor: <bug description>`