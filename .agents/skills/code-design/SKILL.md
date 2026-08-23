---
name: code-design
description: Use when adding, changing, or reviewing code.
---

# Code Design

A reference ruleset for shaping and checking code, drawn from Clean Code and SOLID, kept to the review-applicable gist rather than the full canon.

## Rulesets

- **Clean Code** — see [CLEAN_CODE.md](CLEAN_CODE.md): naming, functions, structure, objects & data, comments.
- **SOLID** — see [SOLID.md](SOLID.md): the five principles, one or two lines each.

## Process

1. **While shaping code**, consult the rulesets above and write code that satisfies them.
2. **Review pass** — before finishing, walk every rule in both rulesets against the code you are adding or changing. For each rule, confirm the code complies; where it does not, fix it if cheap, otherwise flag the violation explicitly.
3. **Done only when** every rule in both rulesets has been checked against the touched code and the list of violations (if any) is stated. A rule is a rule even when the linter already covers it — do not suppress a rule and move on; follow it.