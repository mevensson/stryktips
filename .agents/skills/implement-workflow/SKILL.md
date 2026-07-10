---
name: implement-workflow
disable-model-invocation: true
---

Implement a single ticket using the `tdd-workflow` skill.

## Process

### 1. Gather context

The argument is the GitHub issue number. Fetch its body and acceptance criteria.

### 2. Explore

Explore the codebase to understand the current state. Use the project's domain glossary vocabulary. Identify where the changes will go.

### 3. Implement with tdd-workflow

Drive the `tdd-workflow` skill. This is a **new feature** (two-level TDD):

1. Write a failing end-to-end test → commit `Red (e2e): <feature description>`
2. Inner loop — repeat until the e2e test passes:
   1. Write a failing unit test → commit `Red (unit): <sub-component description>`
   2. Add the minimal code to make it pass → commit `Green: <sub-component description>`
   3. Refactor → commit `Refactor: <sub-component description>`
3. If the e2e test hasn't turned green after 3 inner cycles, flag to the user and ask for guidance.

### 4. Verify

Run `ruff format --check .` and `ruff check .` and `mypy .` and `pytest`. Fix any issues.

### 5. Tell the user

Say the work is complete and ready for review. Tell them to run `/code-review main` to review the changes in a clean context.
