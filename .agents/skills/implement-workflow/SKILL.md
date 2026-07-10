---
name: implement-workflow
disable-model-invocation: true
---

Implement a single ticket using the `tdd-workflow` skill.

## Process

### 1. Gather context

The argument is the GitHub issue number. Fetch its body, acceptance criteria, labels, and blocking edges.

### 2. Sanity-check the ticket

Before starting, verify two things:

- **Label check**: the issue must carry the `ready-for-agent` label. If it doesn't, flag it to the user — the ticket may need triage first.
- **Blockers check**: parse the "Blocked by" section in the issue body. For each referenced issue, check if it's closed. If any blockers are still open, list them and ask the user whether to proceed or wait.

Flag all problems at once, then wait for the user's decision. Do not proceed if blockers remain unresolved unless the user explicitly confirms.

### 3. Explore

Explore the codebase to understand the current state. Use the project's domain glossary vocabulary. Identify where the changes will go.

### 4. Implement with tdd-workflow

Drive the `tdd-workflow` skill. This is a **new feature** (two-level TDD):

1. Write a failing end-to-end test → commit `Red (e2e): <feature description>`
2. Inner loop — repeat until the e2e test passes:
   1. Write a failing unit test → commit `Red (unit): <sub-component description>`
   2. Add the minimal code to make it pass → commit `Green: <sub-component description>`
   3. Refactor → commit `Refactor: <sub-component description>`
3. If the e2e test hasn't turned green after 3 inner cycles, flag to the user and ask for guidance.

### 5. Verify

Run `ruff format --check .` and `ruff check .` and `mypy .` and `pytest`. Fix any issues.

### 6. Tell the user

Say the work is complete and ready for review. Tell them to run `/code-review main` to review the changes in a clean context.
