# ADR 0003: Orchestration Boundaries

The CLI module (`stryktips.core`) had grown to mix argument parsing, bound
resolution policy, month traversal, report collection, and rendering, with
concrete API, clock, and output globals that forced tests to patch module
internals. We separated those responsibilities behind public contracts while
keeping the CLI as the composition root: `main` owns parsing, validation,
concrete dependency wiring, rendering, stderr, and exit-code mapping; a
resolution service (`resolve_draw`, `resolve_end`) turns typed selectors into
draw numbers; and a Period collector (`collect_period`) turns inclusive draw
numbers into `Draw`s. Existing pure entry selectors (`resolve_draw_by_date`,
`resolve_draw_by_week`, `entries_in_week`, `parse_week`) stay real
collaborators rather than being reimplemented. Dependencies flow one way — the
CLI depends on the services, and the services depend only on injected callables
(`FetchDraw`, `FetchMonthEntries`, `Clock`, `Diagnostic`) carried in a small
`Dependencies` object built by `create_dependencies()`. `date.today`, the API
functions, and printing are wired only at that composition point; resolution
and collection are deterministic and side-effect-free except through the
injected diagnostic callback. Selectors are typed (`DrawByNumber`,
`DrawByDate`, `DrawByWeek`) rather than raw `argparse.Namespace`, so the public
contracts never depend on CLI parsing details. `DrawByWeek` takes only the raw
week text and derives its year, week, and index, so a selector cannot hold
contradictory state; the raw spelling is retained for diagnostics and an
omitted index stays distinct from an explicit `.1`.

The contracts now live in dedicated modules. `stryktips/dependencies.py` holds
the `FetchDraw`, `FetchMonthEntries`, `Clock`, and `Diagnostic` aliases plus the
`Dependencies` object; `stryktips/resolution.py` holds the typed selectors, the
`resolve_draw`/`resolve_end` services, and the forward date/week, backward
default-end, and current/completed/future indexed end-week policies.
`stryktips/core.py` remains the composition root: `create_dependencies()` and
its concrete API, `date.today`, and stderr defaults stay there, alongside CLI
parsing/rendering and the Period collector (`collect_period` and its
algorithms), which #103 will extract. `stryktips/months.py` holds the shared
month arithmetic and the scan-window constant so resolution and collection step
months identically, but their policies stay distinct: resolution gathers every
month an ISO week spans before selecting an index, while collection walks
inclusive draw numbers; the two are not blended. The public services reach for
the network, clock, and output only through the injected `Dependencies`, so
resolution is deterministic and side-effect-free apart from the diagnostic
callback. The current scan limits are unchanged (`MAX_SCAN_MONTHS = 12`). The
migration was staged deliberately — public delegating façades first, then test
migration, then algorithm extraction — so behavior and tests were never
rewritten at the same time. Tests target the public contracts through injected
fakes and a fixed clock, so moving a private helper no longer breaks them.
