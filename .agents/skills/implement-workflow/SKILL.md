---
name: implement-workflow
disable-model-invocation: true
---

Implement a single ticket using the `tdd-workflow` skill.

## Process

### 1. Gather context

The argument is the GitHub issue number. Fetch its body, acceptance criteria, labels, and blocking edges. Derive a short slug from the issue title for the branch name.

### 2. Sanity-check the ticket

Before starting, verify two things:

- **Label check**: the issue must carry the `ready-for-agent` label. If it doesn't, flag it to the user — the ticket may need triage first.
- **Blockers check**: parse the "Blocked by" section in the issue body. For each referenced issue, check if it's closed. If any blockers are still open, list them and ask the user whether to proceed or wait.

Flag all problems at once, then wait for the user's decision. Do not proceed if blockers remain unresolved unless the user explicitly confirms.

### 3. Branch from latest main

Create a feature branch: `git checkout -b <slug>-<ticket>`. The slug is a short kebab-case descriptor from the issue title.

Push the branch to origin so the PR targets main.

### 4. Explore

Identify where the changes will go. Use the project's domain glossary vocabulary.

### 5. Decompose into e2e scenarios

From the ticket, enumerate the distinct end-to-end behaviors (scenarios) you need. Each scenario is one vertical slice.

### 6. Implement each scenario via sub-agent

For each scenario, spawn a sub-agent that runs two-level TDD for one scenario only.

Spawn sub-agents **sequentially** — each subsequent scenario builds on the previous implementation.

**Sub-agent prompt** — include:
- The scenario description (from the ticket)
- The current codebase state
- The ticket number for commit messages
- The pre-commit checks from the `tdd-workflow` skill
- Brief: "Implement this one scenario using two-level TDD: write a failing e2e test → commit `Red (e2e): <description> (#<ticket>)`. Then run the inner loop (Red unit → Green → Refactor) until the e2e test passes, delegating each inner-loop iteration to a sub-agent. Do not add any other scenarios."

### 7. Final verification

Run `ruff format --check .` and `ruff check .` and `mypy .` and `pytest` one last time as a safety net. Fix any issues.

### 8. Audit documentation

Check README.md, CONTEXT.md, and any other user-facing docs for references to interfaces this ticket changed. Update them if stale.

### 9. Push and create a PR

Push the branch and create a PR targeting main. The PR description must reference the issue (e.g. `Closes #<ticket>` or `Implements #<ticket>`). Include a brief summary of the changes.

### 10. Tell the user

Say the PR is ready for review. Provide the PR URL. Tell them to run `/code-review main` in a clean context on this branch to review the changes.
