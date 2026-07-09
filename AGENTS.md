# Agent Instructions for the stryktips repository

## Overview
You are an AI assistant helping develop and maintain the `stryktips` codebase.

## Environment

Dependencies and tooling are managed via Nix. Enter the dev shell with
`nix develop` (or use `direnv` — `.envrc` handles it automatically).
The shell provides Python 3.14, pytest, ruff, mypy, and gh.
All Python dependencies (including test libraries) must be added to
`flake.nix` — do not use `pip install`.
After adding a dependency, run `nix develop` (or restart `direnv`) to
pick up the change.

## Core Principles
- Focus on concise, readable code and stable logic
- Prefer tests and small, safe changes
- Use repository-specific context when making code suggestions
- Explain assumptions and suggest revisions when requirements are missing

## Python Development Standards

- **Code organization**: Order functions top-down — public/high-level functions first, helpers they call below. This lets the reader trace the flow from top to bottom.
- **Testing**: Use `pytest` for all tests.
  - **Unit Tests**: Located in `tests/unit/` — run `pytest tests/unit`
  - **End-to-End Tests**: Located in `tests/e2e/` — run `pytest tests/e2e`
- **Formatting & Linting**: Use `ruff` for both code formatting and static code analysis.
  - Format check: `ruff format --check .`
  - Lint: `ruff check .`
  - **Suppressions**: Use `# noqa: CODE` inline comments to suppress a rule on a single line when
    following it would make the code worse (e.g., `print("debug")  # noqa: T201`).
- **Type Checking**: Use `mypy` to ensure type safety. Run `mypy .`

## Development Workflow

Follow the `tdd-workflow` skill for all implementation and bug-fix work.

## Agent skills

### Issue tracker

Issues are tracked on GitHub Issues, using the `gh` CLI. External PRs are not a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

All five canonical labels use their default names: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout — one `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Pull Requests

All changes are submitted via GitHub PRs. Use the `gh` CLI for PR operations.
- Do not amend or force-push commits in an open PR; add new commits instead.