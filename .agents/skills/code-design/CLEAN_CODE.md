# Clean Code

The gist, not the canon. Rules a review actually applies.

## Naming

- **Names reveal intent** — state *what* and *why*, not *how*. Prefer intent to implementation detail.

## Functions

- **Small. Shorter than you think.** The linter may not push hard enough — an agent tends to suppress a length rule rather than shrink the function. So say it plainly and follow it.
- **Do one thing.** One level of abstraction per function.

## Structure

- **Code reads top-to-bottom** — callers before their helpers; the "newspaper" ordering.

## Objects & data

- **Hide internals** — let callers command, and ask questions. Don't ask-then-act.
- **Don't reach through** — no `a.b.c.d.foo` message chains.

## Comments

- **Only where they clarify *why***. If a comment explains *what* the code does, the name is wrong.