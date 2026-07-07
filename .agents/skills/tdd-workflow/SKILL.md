---
name: tdd-workflow
description: >-
  Use when the user asks you to implement a new feature, add functionality, or
  develop something new. Also use when the user asks you to fix a bug or defect.
---

# tdd-workflow

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
   3. If the e2e test hasn't turned green after 3 inner cycles, flag to the user and ask for guidance.

4. **Bug Fix (One-Level TDD):**
   1. Write a failing unit test that reproduces the bug → commit `Red: <bug description>`
   2. Add the minimal code to make it pass → commit `Green: <bug description>`
   3. Refactor → commit `Refactor: <bug description>`