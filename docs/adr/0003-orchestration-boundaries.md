# ADR 0003: Orchestration Boundaries

Status: accepted. Completed by #103, merged in PR #108.

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
CLI depends on the services, and the services take their I/O, clock, and
diagnostics from the injected callables (`FetchDraw`, `FetchMonthEntries`,
`Clock`, `Diagnostic`) carried in a small `Dependencies` object built by
`create_dependencies()`. The collector additionally imports the adapter-defined
`DrawNotFoundError` from `stryktips.api` so the missing-vs-other-failure
distinction keeps its existing error identity; that is a deliberate exception
contract, not a concrete fetch dependency, and it does not bypass the injected
I/O. `date.today`, the API functions, and printing are wired only at that
composition point; resolution and collection reach for no ambient concrete I/O,
clock, or output dependency (only shared constants such as `MAX_SCAN_MONTHS`).
Selectors are typed (`DrawByNumber`,
`DrawByDate`, `DrawByWeek`) rather than raw `argparse.Namespace`, so the public
contracts never depend on CLI parsing details. `DrawByWeek` takes only the raw
week text and derives its year, week, and index, so a selector cannot hold
contradictory state; the raw spelling is retained for diagnostics and an
omitted index stays distinct from an explicit `.1`.

The contracts now live in dedicated modules. `stryktips/dependencies.py` holds
the `FetchDraw`, `FetchMonthEntries`, `Clock`, and `Diagnostic` aliases plus the
`Dependencies` object; `stryktips/resolution.py` holds the typed selectors, the
`resolve_draw`/`resolve_end` services, and the forward date/week, backward
default-end, and current/completed/future indexed end-week policies;
`stryktips/collection.py` holds `collect_period` and its anchor, interior-draw,
and month-walk algorithms; and `stryktips/months.py` holds the shared month
arithmetic (`advance_month`, `previous_month`) and the scan-window constant so
resolution and collection step months identically while their policies stay
distinct. Resolution gathers every month an ISO week spans before selecting an
index, while collection walks inclusive draw numbers; the two are not blended.
`stryktips/core.py` is now only the composition root: parse/validate,
`create_dependencies()`, service invocation, rendering, stderr diagnostics, and
error-to-exit-code mapping. The migration was staged deliberately — #99 display
assertions, #100 fixtures/builders, #101 public boundaries, #102 resolution,
#103 collection and CLI orchestration — so behavior and tests were never
rewritten at the same time.

Concrete collaborators are injected as runtime defaults: `create_dependencies`
selects the module-level aliases imported into `core` (`api_fetch_draw` and
`api_fetch_month_entries` for the API functions, `date.today`, and
`_diagnostic_to_stderr`) at call time, so a caller can override exactly the seam
it needs. No collector wrapper or transitional façade remains: `core` imports
`collect_period` directly. The three original production statement-limit
suppressions in the pre-split module (`create_parser`,
`_resolve_completed_indexed_end_week`, `_resolve_draw_by_week`) were removed by
splitting and simplification in #102/#103, not relocated.

External inputs and effects are explicit: `fetch_draw` and
`fetch_month_entries` perform network I/O, `clock` supplies the current date
(the real `date.today` varies), and `diagnostic` writes user-facing output. The
boundary guarantees that no ambient concrete I/O, clock, or output dependency
is reached for — not that the services are deterministic: the same injected
callables do not by themselves pin the result, and `clock` is not pure. Tests
become deterministic only by injecting a fixed clock and fakes. This corrects
the earlier draft's "side-effect-free except through the diagnostic callback"
claim.

Preserved behavior is load-bearing. Collection eagerly walks the month range
before fetching any interior Draw, so a datepicker failure aborts before
interior fetches and the truncation warning — emitted only when the scan window
is exhausted without reaching the end — precedes skip warnings. Dedup is
success-only: a Draw is marked seen only after it is fetched, so a Draw that
404s is retried and re-warned if it appears in a later month. A missing anchor
yields an empty Period, while any other request failure propagates. `MAX_SCAN_MONTHS` stays 12, and the scan limit and its
truncation warning remain owned by #81. `main`/`create_parser` and the
`stryktips.py` script/package entry points are unchanged. Tests target the
public contracts through injected fakes and a fixed clock, so moving a private
helper no longer breaks them.
