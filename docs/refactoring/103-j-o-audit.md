# #103 J–O audit

Durable audit of findings **J–O** from the #98 review session across the merged
#99–#102 slices plus the current `issue-103-period-collection` branch (#103 is
not yet merged). It records the evidence behind each finding, the behavior/test
coverage map, and the residuals that still need explicit user triage.

> **Status of the residuals below:** they are *proposed* triage items, **not**
> approved deferrals. The user has not accepted any residual, and this audit
> does not close #98. #98 remains open pending user triage of the residuals and
> merge of all five subissues.

## Scope and evidence base

Behavior-preserving refactoring only. Correctness findings A–I and the
#79/#80/#81 bound-policy work (separate issues, not all merged) are outside this
refactor; this audit preserves the currently merged baseline and proposes no
scope changes.

Slices (merged unless noted):

- #99 `d29cb4d` — strengthen display absence assertions (O).
- #100 `667f44b`, `0a2688e`, `169f8e3`, `b0eeb58`, `04f488a` — fixture names,
  shared Match/Draw builders, small-unit standardization (N, part of L).
- #101 `6be9f1e` — public orchestration boundaries and migrated tests (K, J/L).
- #102 `95fcbc1`, `c11d005`, `683d520`, `ba56f6c` — bound-resolution extraction
  (J, M).
- #103 `db9e800`, `e31e755`, `6e78650` — Period collection extraction and CLI
  simplification (remaining J/L/M). Current branch, unmerged.

Verification at the time of writing: 189 unit + 79 e2e = 268 tests, all green;
`ruff format --check .`, `ruff check .`, and `mypy .` clean.

## Findings J–O

### J — architecture: fixed

`stryktips/core.py` shrank from 588 lines at the #98 baseline (`2bd4e75`) to
282. Responsibilities moved to dedicated modules:

| Module | Lines | Owns |
| --- | ---: | --- |
| `stryktips/core.py` | 282 | parse/validate, compose, invoke services, render, stderr, exit codes |
| `stryktips/collection.py` | 85 | `collect_period` and anchor/interior/month-walk algorithms |
| `stryktips/resolution.py` | 416 | typed selectors, `resolve_draw`/`resolve_end`, bound policies |
| `stryktips/dependencies.py` | 34 | `FetchDraw`, `FetchMonthEntries`, `Clock`, `Diagnostic`, `Dependencies` |
| `stryktips/months.py` | 27 | `advance_month`, `previous_month`, `MAX_SCAN_MONTHS = 12` |

The three production `PLR0915` suppressions present at the baseline
(`create_parser`, `_resolve_completed_indexed_end_week`, `_resolve_draw_by_week`)
are all gone: #102 removed two by extracting/simplifying resolution, #103 removed
the third by splitting parser construction into `_add_display_arguments`,
`_add_start_arguments`, and `_add_end_arguments`. None was relocated, and no
collector wrapper or transitional façade remains — `core` imports
`collect_period` directly. `create_dependencies` selects the imported
`api_fetch_draw`/`api_fetch_month_entries` aliases, `date.today`, and
`_diagnostic_to_stderr` as call-time defaults so a caller can override one seam.

Preserved collection behavior is covered by public-contract tests (see the
coverage map): eager full-month scan before interior fetches, success-only dedup
with missing-draw retries, missing anchor → empty Period while other failures
propagate, anchor close-time rejection, and the truncation warning when the
12-month window is exhausted (still owned by #81). `main`/`create_parser` and
the script/package entry points are unchanged.

### K — test coupling: fixed

No test imports or patches a private `stryktips` helper. The flexmock seams are
`stryktips.core.create_dependencies` (via `tests/cli_harness.py` and
`tests/e2e/report_support.py`) and `requests.get` at the API adapter boundary;
resolution/collection tests construct `Dependencies` directly and call the
public `resolve_draw`/`resolve_end`/`collect_period`. `tests/builders.py`
provides deterministic `make_dependencies`, whose `fetch_draw` raises `KeyError`
for an unregistered number rather than synthesising a Draw.

### L — test quality: implemented cleanup, residual triage

The post-characterization modules were split by behavior, and shared builders
removed the repeated Match/Draw setup. Collected counts:

| Pre-split module (`db9e800`) | Tests | Split into | Tests |
| --- | ---: | --- | ---: |
| `tests/unit/test_core.py` | 28 | `test_cli_behavior.py` | 20 |
| | | `test_cli_validation.py` | 8 |
| `tests/unit/test_period_collection.py` | 16 | `test_period_collection.py` | 7 |
| | | `test_period_collection_failures.py` | 9 |
| `tests/e2e/test_cli_report_end_bounds.py` | 35 | `test_cli_report_end_date.py` | 12 |
| | | `test_cli_report_end_week_current.py` | 10 |
| | | `test_cli_report_end_week_completed.py` | 13 |

The two new `make_dependencies` contract tests (`test_builders.py`) bring the
unit count to 189. `cli_harness.py` exposes only the public
`create_dependencies` seam; `report_support.py` keeps the real API adapter and
parser while mocking `requests` and fixing the clock.

### M — ordering: fixed

Public/high-level definitions now precede the helpers they call: `core.py` has
`create_dependencies`, `main`, `create_parser`, then the private helpers;
`resolution.py` and `collection.py` put their public services first. Callers
such as `_run`/`_display_report_if_start` appear before the helpers they invoke.

### N — vocabulary: fixed

All eight Draw JSON fixtures were renamed from `week_*` to `draw_*`
(`draw_4641`, `draw_4642`, `draw_4880`–`draw_4884`, `draw_4900`); no `week_*`
fixture remains and callers were updated.

### O — assertions: fixed

#99 replaced the two absence-only display tests
(`test_format_matches_omits_odds_when_absent` and
`test_format_matches_omits_outcome_probabilities_when_odds_absent`). The first
became a complete expected-output assertion
(`test_format_matches_omits_odds_and_probabilities_when_both_absent`), and the
second was removed because
`test_format_matches_shows_outcome_probabilities_without_odds` already covers
that path. Two secondary `not in` checks remain in `test_display.py`, each
paired with a positive assertion, so they are not absence-only.

## Behavior and test coverage map

| Preserved behavior | Coverage |
| --- | --- |
| Single-Draw shortcut, no datepicker walk | `test_period_collection.py::test_collect_period_single_draw_skips_datepicker`, `..._without_close_time_skips_datepicker`; `test_cli_behavior.py::test_main_draw_flag_does_not_consult_datepicker` |
| Inclusive bounds, gaps, month walk | `test_period_collection.py::test_collect_period_spanning_includes_both_bounds_in_order`, `..._walks_across_drawless_months`; `test_cli_report_collection.py` |
| Success-only dedup | `test_period_collection.py::test_collect_period_deduplicates_repeated_month_entries` |
| Missing interior draw skipped + warning | `test_period_collection_failures.py::test_collect_period_missing_interior_draw_is_skipped_and_reported` |
| Missing draw retried and re-warned | `test_period_collection_failures.py::test_collect_period_retries_and_rewarns_a_missing_interior_draw` |
| Missing anchor → empty Period | `...::test_collect_period_missing_anchor_returns_empty`; `test_cli_report_collection.py` |
| Non-404 request failures propagate | `...::test_collect_period_non_not_found_failure_propagates`, `..._anchor_request_failure_propagates`, `..._month_lookup_failure_propagates_before_interior_fetch` |
| Anchor close-time rejection | `...::test_collect_period_spanning_requires_anchor_close_time`; `test_cli_behavior.py::test_main_spanning_report_errors_when_anchor_has_no_close_time` |
| Truncation warning only when the scan window is exhausted, and its ordering | `...::test_collect_period_warns_when_end_not_reached_within_scan_window`, `..._emits_truncation_warning_before_skip_warnings` |
| Eager scan before interior fetches | `test_period_collection.py::test_collect_period_walks_all_months_before_fetching_interior_draws` |
| Stop once an entry exceeds the end | `test_period_collection.py::test_collect_period_stops_when_an_entry_exceeds_end_without_warning` |
| CLI parse/validate/exit codes | `test_cli_behavior.py` (20), `test_cli_validation.py` (8), `test_cli_report_validation.py` (16), `test_cli_help.py` (2) |
| Resolution policies | `test_bound_resolution.py` (37), `test_cli_report_end_date.py` (12), `test_cli_report_end_week_current.py` (10), `test_cli_report_end_week_completed.py` (13) |
| Builders | `test_builders.py` (15) |

## Residuals needing explicit user triage

Each item is a **proposal**, not an approved deferral.

1. **E — probability fixtures the real adapter cannot produce (correctness,
   separate).** `tests/unit/test_report.py` builds matches with `odds=None` but
   an explicit `outcome_probability` (12 `odds=None` sites, seven carrying a
   non-`None` probability), and
   `test_display.py::test_format_matches_shows_outcome_probabilities_without_odds`
   does the same. It also supplies `Odds` together with an explicit
   `OutcomeProbability` that is not the overround-free derivation of those odds:
   `home_win` pairs odds `2.0/3.4/3.6` with `0.75/0.20/0.05`, while
   `remove_overround` derives `0.4665/0.2744/0.2591`; `away_win` and
   `draw_match` mismatch similarly. The real adapter
   (`api._compute_outcome_probability`) derives probabilities from odds and
   yields neither the odds-less nor the non-derived state, so these fixtures
   cannot arise from parsing. Both are pre-existing: at the #98 baseline the
   odds-less states came from a local `make_match` that omitted `odds`, while
   the odds-carrying states were built with explicit probabilities that were
   never derived. They were intentionally left untouched by #99–#103. #98
   classifies E as separate correctness work; propose triaging the odds-less and
   the non-derived explicit-probability fixtures with that work rather than
   folding them into this refactor.

2. **Test-only `PLR0915` suppressions — 36, all in fixture-heavy E2E tests.**
   Per module: `test_cli_date.py` 2, `test_cli_draw.py` 1,
   `test_cli_report_collection.py` 5, `test_cli_report_end_date.py` 10,
   `test_cli_report_end_week_completed.py` 8,
   `test_cli_report_end_week_current.py` 5, `test_cli_week.py` 5. **None is one
   of the three original production suppressions**, which are gone. The split of
   `test_cli_report_end_bounds.py` raised the test-only count from 21 to 23, so
   the current total is 36 rather than the pre-#103 test count of 34. Propose
   triaging whether shared request-stub helpers should shrink these functions;
   not approved.

3. **Test-only `PLR0913` suppressions — 4.** `tests/builders.py` `make_match`
   and `make_dependencies`, plus `test_cli_report_end_week_completed.py:429` and
   `test_cli_week.py:192`. The `make_dependencies` suppression has a documented
   rationale (it mirrors each overridable dependency seam); the others are
   pre-existing parametrized/fixture-heavy tests. Propose triage, not an
   approved deferral.

4. **Large-but-coherent modules.** `test_cli_report_end_week_completed.py`
   (505 lines), `test_bound_resolution.py` (526),
   `test_cli_report_end_date.py` (408), `test_cli_behavior.py` (406),
   `resolution.py` (416), and `core.py` (282) are large, but size follows from
   fixture/setup density and the breadth of the end-week policy rather than
   mixed responsibilities. Propose triage only; size alone is not declared a
   defect here.

5. **Adapter-defined `DrawNotFoundError` contract (structural design follow-up,
   proposal).** `stryktips/collection.py` imports `DrawNotFoundError` from
   `stryktips.api` to preserve the missing-anchor/missing-interior vs
   other-request-failure distinction with unchanged error identity. This is a
   deliberate reuse of the adapter's exception contract, not hidden I/O and not
   a behavior bug. A future structural follow-up could relocate the exception
   into adapter-neutral contracts (alongside `Dependencies`); that is a design
   proposal for triage only, and this docs step does not move it or change
   behavior.

## User-facing docs audit

`README.md` and `CONTEXT.md` were audited against the merged behavior. #103 is a
pure refactoring with no interface change, so neither required an edit:
`README.md` documents CLI arguments, behavior, and output (all preserved), and
`CONTEXT.md` is a glossary of unchanged domain terms (the `Period` definition
already matches inclusive `collect_period`). No new domain vocabulary was
introduced by the extraction.

## Verification

```text
pytest tests/unit          # 189 passed
pytest tests/e2e           # 79 passed
ruff format --check .      # clean
ruff check .               # clean
mypy .                     # clean
```
