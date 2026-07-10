---
name: code-review
disable-model-invocation: true
---

Two-axis review of the diff between `HEAD` and a fixed point the user supplies:

- **Standards** — does the code conform to this repo's documented coding standards?
- **Spec** — does the code faithfully implement the originating issue / PRD / spec?

Both axes run as **parallel sub-agents** so they don't pollute each other's context, then this skill aggregates their findings.

## Process

### 1. Pin the fixed point

The argument is the fixed point — a commit SHA, branch name, tag, `main`, `HEAD~5`, etc. If none is provided, default to `main`.

Capture the diff command: `git diff <fixed-point>...HEAD` (three-dot, so the comparison is against the merge-base). Also note the commits via `git log <fixed-point>..HEAD --oneline`.

Confirm the fixed point resolves (`git rev-parse <fixed-point>`) and the diff is non-empty. Fail here with a clear message if the ref is bad or the diff is empty.

### 2. Identify the spec source

Look for the originating spec, in this order:

1. Issue references in the commit messages (`#123`, `Closes #45`) — fetch via `gh issue view <number>`.
2. A path the user passes as an argument.
3. A PRD/spec file under `docs/`, `specs/`, or `.scratch/` matching the branch name or feature.
4. If nothing found, the Spec sub-agent will skip and report "no spec available".

### 3. Standards source

Anything in the repo that documents how code should be written — `AGENTS.md`, `CONTRIBUTING.md`, etc.

On top of documented standards, carry the **smell baseline** below. Two rules:
- **The repo overrides.** A documented standard always wins; where it endorses something the baseline would flag, suppress the smell.
- **Always a judgement call.** Each smell is a labelled heuristic, never a hard violation. Skip anything tooling already enforces.

Smell baseline (Fowler, _Refactoring_ ch.3):
- **Mysterious Name** — name doesn't reveal what it does. → rename.
- **Duplicated Code** — same logic shape appears in more than one hunk. → extract.
- **Feature Envy** — method reaches into another object's data more than its own. → move it.
- **Data Clumps** — same params keep travelling together. → bundle into one type.
- **Primitive Obsession** — primitive standing in for a domain concept. → give it its own type.
- **Repeated Switches** — same switch/cascade on the same type recurs. → polymorphism or a shared map.
- **Shotgun Surgery** — one logical change forces edits across many files. → gather into one module.
- **Divergent Change** — one file edited for several unrelated reasons. → split.
- **Speculative Generality** — abstraction added for needs the spec doesn't have. → delete it.
- **Message Chains** — long `a.b().c().d()` navigation. → hide behind one method.
- **Middle Man** — mostly delegates onward. → cut it, call the real target.
- **Refused Bequest** — subclass ignores most of what it inherits. → composition over inheritance.

### 4. Spawn both sub-agents in parallel

Use a single message with two sub-agent calls.

**Standards sub-agent prompt** — include:
- The full diff command and commit list.
- The standards-source files found in step 3, **plus the smell baseline from step 3** pasted in full.
- Brief: "Report — per file/hunk — (a) every violation of a documented standard (cite the rule); (b) any baseline smell (name it and quote the hunk). Distinguish hard violations from judgement calls. Skip anything tooling enforces. Under 400 words."

**Spec sub-agent prompt** — include:
- The diff command and commit list.
- The fetched spec contents.
- Brief: "Report: (a) requirements missing or partial; (b) behaviour not asked for (scope creep); (c) requirements that look implemented but wrong. Quote the spec. Under 400 words."

If the spec is missing, skip the Spec sub-agent and note it in the report.

### 5. Aggregate

Present the two reports under `## Standards` and `## Spec` headings, verbatim or lightly cleaned. Each axis stands alone — do not merge or rerank findings across axes.

End with a one-line summary: total findings per axis and the worst issue within each axis.
