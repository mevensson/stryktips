# Agent Instructions for the stryktips repository

## Overview
You are an AI assistant helping develop and maintain the `stryktips` codebase.

## Core Principles
- Focus on concise, readable code and stable logic
- Prefer tests and small, safe changes
- Use repository-specific context when making code suggestions
- Explain assumptions and suggest revisions when requirements are missing

## Python Development Standards

- **Testing**: Use `pytest` for all tests.
  - **Unit Tests**: Located in `tests/unit/`
  - **End-to-End Tests**: Located in `tests/e2e/`
- **Formatting & Linting**: Use `ruff` for both code formatting and static code analysis.
- **Type Checking**: Use `mypy` to ensure type safety and catch potential type-related errors.

## Development Workflow

Follow the `tdd-workflow` skill for all implementation and bug-fix work.

## Agent skills

### Issue tracker

Issues are tracked on GitHub Issues, using the `gh` CLI. External PRs are not a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

All five canonical labels use their default names: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout — one `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.