---
name: to-spec
disable-model-invocation: true
---

Synthesize the current conversation into a spec and publish it to the GitHub issue tracker. Do NOT interview the user — just synthesise what you already know. Use the project's domain glossary vocabulary throughout.

## Process

1. **Explore the codebase** to understand the current state. Respect any ADRs in the area you're touching.

2. **Sketch test seams** at which the feature will be tested. Prefer existing seams over new ones; use the highest seam possible. The fewer seams the better — ideally one. Check with the user that the seams match their expectations.

3. **Write the spec** using the template below.

4. **Publish** to GitHub Issues. Apply the `ready-for-agent` triage label.

<spec-template>

## Problem Statement

The problem the user is facing, from the user's perspective.

## Solution

The solution to the problem, from the user's perspective.

## User Stories

A numbered list of user stories in the format:
1. As an <actor>, I want a <feature>, so that <benefit>

Be extensive — cover all aspects of the feature.

## Implementation Decisions

- The modules that will be built or modified
- Their interfaces
- Technical clarifications
- Architectural decisions
- Schema changes
- API contracts
- Specific interactions

Do NOT include specific file paths or code snippets (they go stale fast). Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it and note it came from a prototype.

## Testing Decisions

- What makes a good test (test external behaviour, not implementation details)
- Which modules will be tested
- Prior art — similar tests in the codebase

## Out of Scope

What is explicitly out of scope.

## Further Notes

Any additional notes.

</spec-template>
