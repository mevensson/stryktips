---
name: to-tickets
disable-model-invocation: true
---

Break a spec (from a GitHub issue) into a set of **tracer-bullet** tickets, each with blocking edges, and publish them as subissues.

## Process

### 1. Gather context

The argument is the GitHub issue number or URL. Fetch its full body. If the spec references other issues, fetch those too.

### 2. Explore the codebase

If you haven't already, explore the current state of the code. Use the project's domain glossary vocabulary throughout, and respect ADRs in the area you're touching.

Look for opportunities to **prefactor** — make the change easy before making the easy change.

### 3. Draft vertical slices

Break the work into **tracer-bullet** tickets.

- Each slice cuts a narrow but COMPLETE path through every layer — vertical, not a horizontal slice of one layer
- A completed slice is demoable or verifiable on its own
- Each slice is sized to fit in a single fresh agent context
- Any prefactoring tickets come first

Give each ticket its **blocking edges** — the other tickets that must complete before it can start. A ticket with no blockers can start immediately.

**Wide refactors** (one mechanical change with a codebase-wide blast radius) are the exception to vertical slicing. Sequence them as **expand–contract**: add the new form beside the old → migrate call sites in batches → delete the old form once no caller remains.

### 4. Quiz the user

Present the proposed breakdown as a numbered list. For each ticket show:
- **Title**: short descriptive name
- **Blocked by**: which other tickets gate it
- **Acceptance criteria**: the end-to-end behaviour this ticket makes work

Ask the user:
- Does the granularity feel right?
- Are the blocking edges correct?
- Should any tickets be merged or split?

Iterate until the user approves.

### 5. Publish as subissues

Publish each approved ticket as a GitHub subissue of the parent spec issue. Use `gh issue create --parent <parent-number> --title "..." --body "..." --label ready-for-agent`. Publish in dependency order (blockers first) so each subissue can reference real identifiers of its blocking issues.

The body of each subissue follows this template:

<issue-template>

## What to build

The end-to-end behaviour this ticket makes work, from the user's perspective — not a layer-by-layer implementation list.

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2

## Blocked by

- A reference to each blocking ticket, or "None — can start immediately"

</issue-template>

Do NOT close or modify the parent issue.
