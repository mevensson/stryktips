# Scenario-to-Replacement Coverage Map (issue #101)

This map inventories the behavioral scenarios currently locked down by the
orchestration tests touched by #101 and records where each scenario will live
after the split. It exists so old tests can be removed during migration without
losing a behavior. It is a working refactoring artifact, not an ADR; the
implemented design is recorded in `docs/adr/0003-orchestration-boundaries.md`.

## Baseline

Planning baseline for this work: `main` at `e2f71dd` with a clean tree.

```text
pytest tests/unit   -> 149 passed
pytest tests/e2e    ->  77 passed
ruff format --check . -> 28 files already formatted
ruff check .        -> All checks passed
mypy .              -> Success: no issues found in 27 source files
```

The collection scan limit is `MAX_SCAN_MONTHS = 12` (unchanged; #81 owns
changing it).

After the batch-1 characterization additions the suites are:

```text
pytest tests/unit   -> 150 passed
pytest tests/e2e    ->  78 passed
```

After the batch-2 public contracts and contract tests:

```text
pytest tests/unit   -> 176 passed
pytest tests/e2e    ->  78 passed
mypy .              -> Success: no issues found in 29 source files
```

After the batch-3 unit migration (consolidated, no private calls) and the
batch-4 E2E split:

```text
pytest tests/unit   -> 169 passed
pytest tests/e2e    ->  78 passed
ruff format --check . -> 32 files already formatted
ruff check .        -> All checks passed
mypy .              -> Success: no issues found in 31 source files
```

The final batch also made `DrawByWeek` take only the raw week text (parsed
fields derived in `__post_init__`), removing the possibility of contradictory
selector state, and added selector-derivation/invalid-input contract tests.

## Target layout

| New target | Responsibility | Status |
| --- | --- | --- |
| `tests/unit/test_core.py` | CLI parsing/validation, argument routing, exit-code and stderr/output mapping, concrete wiring | migrated in batch 3; 21 CLI-only tests |
| `tests/unit/test_bound_resolution.py` | Date/week/start/end bound resolution over injected datepicker I/O and clock | complete; 33 contract tests |
| `tests/unit/test_period_collection.py` | Inclusive `[start, end]` Period collection over injected fetch I/O and diagnostics | complete; 9 contract tests |
| `tests/e2e/test_cli_report_validation.py` | Report-bound argument validation and help through real `main`/subprocess | split in batch 4; 16 with params |
| `tests/e2e/test_cli_report_collection.py` | Report aggregation and collection failures through the real API adapter/parser | split in batch 4; 8 |
| `tests/e2e/test_cli_report_end_bounds.py` | Start/end bound resolution policies through the real API adapter/parser | split in batch 4; 35 with params |

`tests/e2e/test_cli_report.py` was deleted after the split. `tests/e2e/test_cli_date.py`
and `tests/e2e/test_cli_week.py` stay in place: they are already HTTP-level E2E
over the real adapter/parser and did not patch the clock.

## Unit migration result (batch 3, exact new names)

The per-test tables below are the pre-migration inventory. This table records
the exact post-migration home for each behavior; `test_core` now contains only
CLI tests through `main`, and the services are tested through
`resolve_draw`/`resolve_end`/`collect_period`.

### `tests/unit/test_bound_resolution.py` (27 with params)

| Test | Behavior |
| --- | --- |
| `test_resolve_draw_by_number_does_not_consult_datepicker` | Draw-number selector resolves directly |
| `test_draw_by_week_unindexed_derives_fields_and_keeps_spelling` | Single-input selector derives year/week, index None, preserves text |
| `test_draw_by_week_explicit_index_derives_fields_and_keeps_spelling` | Single-input selector derives explicit index, preserves text |
| `test_draw_by_week_rejects_invalid_value[4]` | Invalid week value raises before resolution |
| `test_resolve_draw_does_not_fetch_the_draw[date, week]` | Resolution never fetches a Draw (parametrized selectors) |
| `test_resolve_draw_by_date_returns_exact_match` | Exact date match, no note |
| `test_resolve_draw_by_date_forward_scans_empty_months` | Forward scan across empty months, note, month order |
| `test_resolve_draw_by_week_selects_explicit_index` | Explicit `.N` selects the N-th distinct Draw, no note |
| `test_resolve_draw_by_week_omitted_index_selects_first_distinct` | Omitted index counts distinct Draws once from unsorted duplicates |
| `test_resolve_draw_by_week_gathers_both_months_before_selecting` | Cross-year week gathers both months before selection |
| `test_resolve_draw_by_week_excessive_index_reports_options` | Excessive forward index names the options |
| `test_resolve_draw_by_date_raises_after_scan_window` | Forward scan window exhaustion raises |
| `test_resolve_end_explicit_draw_returns_it_verbatim` | Explicit end draw used without datepicker |
| `test_resolve_end_date_returns_latest_draw_on_or_before_bound` | End date resolves to latest on/before |
| `test_resolve_end_date_clamps_future_bound_to_today` | Future end date clamps to today |
| `test_resolve_end_defaults_to_latest_draw_on_or_before_today` | Default end is latest on/before today |
| `test_resolve_end_default_scans_back_across_year_boundary` | Default end backward search crosses the year |
| `test_resolve_end_default_stops_scanning_once_entry_found` | Default end stops at first eligible month |
| `test_resolve_end_default_raises_after_scan_window` | Default end backward window exhausts and raises |
| `test_resolve_end_unindexed_week_clamps_future_sunday_to_today` | Unindexed current week clamps to today |
| `test_resolve_end_unindexed_week_uses_latest_draw_on_or_before_sunday` | Completed unindexed week uses Sunday |
| `test_resolve_end_explicit_index_selects_first_draw_in_current_week` | Explicit `.1` on current week selects first Draw |
| `test_resolve_end_current_week_index_after_today_clamps_to_latest_draw` | Current-week later index clamps, no warning |
| `test_resolve_end_future_indexed_week_clamps_to_latest_draw` | Wholly future indexed week clamps |
| `test_resolve_end_completed_excessive_index_warns_and_returns_final_draw` | Completed excessive index fallback + warning |
| `test_resolve_end_excessive_index_tie_breaks_same_date_draws_by_number` | Excessive fallback same-date tie-break by number |
| `test_resolve_end_empty_completed_indexed_week_warns_and_returns_predecessor` | Empty completed indexed week falls back + warns |
| `test_resolve_end_indexed_week_gathers_both_months_before_selecting` | Cross-year indexed end gathers both months |
| `test_resolve_end_without_preceding_draw_raises_after_scan_window` | End bound backward window exhaustion raises |

### `tests/unit/test_period_collection.py` (9)

| Test | Behavior |
| --- | --- |
| `test_collect_period_single_draw_skips_datepicker` | Single-Draw Period skips the month walk |
| `test_collect_period_spanning_includes_both_bounds_in_order` | Inclusive bounds, out-of-range filtered |
| `test_collect_period_walks_across_drawless_months` | Empty months walked, inclusive end reached |
| `test_collect_period_deduplicates_repeated_month_entries` | Repeated Draw fetched/reported once |
| `test_collect_period_missing_interior_draw_is_skipped_and_reported` | Missing interior Draw skipped + warned |
| `test_collect_period_non_not_found_failure_propagates` | Non-404 failure propagates |
| `test_collect_period_missing_anchor_returns_empty` | Missing anchor yields empty Period |
| `test_collect_period_warns_when_end_not_reached_within_scan_window` | Truncation warning at scan limit |
| `test_collect_period_spanning_requires_anchor_close_time` | Missing anchor close time fails clearly |

### `tests/unit/test_core.py` (20, all through `main`)

| Test | Behavior |
| --- | --- |
| `test_main_draw_flag_displays_the_draw` | `--draw` fetches and renders |
| `test_main_draw_flag_does_not_consult_datepicker` | `--draw` needs no month lookup |
| `test_main_date_flag_resolves_and_displays_the_draw` | `--date` resolves and renders |
| `test_main_week_flag_resolves_and_displays_the_draw` | `--week` resolves and renders |
| `test_main_start_draw_end_draw_prints_bucket_report` | Single-Draw report wiring |
| `test_main_start_draw_end_draw_prints_single_aggregated_report` | Spanning range one aggregated report, fetched once each |
| `test_main_start_draw_end_draw_reports_network_error_to_stderr` | Report-path request failure maps to exit 1 |
| `test_main_start_draw_without_end_draw_uses_default_end` | Default end wiring |
| `test_main_start_draw_after_default_end_prints_empty_report_without_fetch` | Reversed start vs default empty, no fetch |
| `test_main_start_draw_greater_than_end_draw_rejected` | Explicit start > end parser error |
| `test_main_start_date_end_draw_prints_report` | Resolved start-date report wiring |
| `test_main_start_date_resolved_after_end_draw_fails_without_fetching` | Reversed resolved start, exit 1, no fetch |
| `test_main_start_draw_end_date_prints_report` | Resolved end-date report wiring |
| `test_main_end_date_without_start_rejected` | `--end-date` without start rejected |
| `test_main_start_week_end_draw_prints_report` | Resolved start-week report wiring |
| `test_main_start_draw_end_week_prints_report` | Historical end-week report wiring |
| `test_main_end_week_without_start_rejected` | `--end-week` without start rejected |
| `test_main_reports_draw_not_found` | `DrawNotFound` maps to exit 1 + stderr |
| `test_main_returns_network_error_to_stderr` | Display-path request failure maps to exit 1 |
| `test_main_invalid_date_reports_error` | Unparseable date maps to exit 1 |
| `test_main_spanning_report_errors_when_anchor_has_no_close_time` | Spanning report anchor without close time exits 1 + stderr |

## E2E migration result (batch 4, exact new names)

`tests/e2e/test_cli_report.py` was split into three files. All weather-level
tests keep requests-level mocking and JSON fixtures, so the concrete API
adapter/parser runs. Clock-dependent tests fix the clock through
``_inject_clock(today)``, which replaces ``create_dependencies`` with
``create_dependencies(clock=lambda: today)`` rather than patching ``date``.

### `tests/e2e/test_cli_report_validation.py` (16 with params)

`test_help_shows_start_draw_end_draw_usage`,
`test_start_draw_argument_required`,
`test_start_draw_end_draw_mutually_exclusive[6]`,
`test_start_draw_after_end_draw_errors`,
`test_invalid_start_draw_or_end_draw_rejected[4]`,
`test_end_without_start_rejected[3]`.

### `tests/e2e/test_cli_report_collection.py` (8)

`test_start_draw_end_draw_4900_reports_buckets`,
`test_start_draw_end_draw_excludes_played_without_odds`,
`test_start_draw_end_draw_spanning_months_aggregates`,
`test_start_draw_end_draw_walks_datepicker_across_drawless_months`,
`test_start_draw_end_draw_skips_absent_draw_number`,
`test_start_draw_end_draw_reports_and_skips_fetch_failure`,
`test_start_draw_end_draw_empty_range_prints_empty_report`,
`test_start_draw_end_draw_anchor_returns_null_draw_prints_empty_report`.

### `tests/e2e/test_cli_report_end_bounds.py` (35 with params)

`test_start_draw_without_end_draw_defaults_to_most_recent_draw`,
`test_start_draw_after_most_recent_draw_prints_empty_report`,
`test_start_date_resolves_to_draw`,
`test_end_date_resolves_to_draw[2]`,
`test_future_end_date_clamps_to_today`,
`test_future_end_week_clamps_to_today[3]`,
`test_start_week_resolves_to_draw`,
`test_end_week_resolves_to_draw[3]`,
`test_current_week_indexed_end_selects_first_draw`,
`test_excessive_end_week_index_clamps_silently_only_while_week_is_current[2]`,
`test_current_week_later_or_missing_index_clamps_to_latest_draw[3]`,
`test_unindexed_current_end_week_clamps_to_latest_draw`,
`test_unindexed_drawless_end_week_resolves_to_latest_preceding_draw`,
`test_indexed_empty_completed_end_week_resolves_to_preceding_draw`,
`test_historical_end_bound_searches_back_across_empty_months[2]`,
`test_end_bound_without_preceding_draw_errors_after_backward_window[3]`,
`test_mixed_start_date_end_week_aggregates`,
`test_resolved_start_after_end_errors[2]`,
`test_start_date_forward_scans_across_empty_months`,
`test_excessive_end_week_index_resolves_to_final_draw`,
`test_cross_year_end_week_selects_distinct_draws[3]`.

### Pre-migration inventory

The sections below are the original pre-migration inventory from batch 1,
retained to show that every scenario has a replacement. Their "Replacement
target" columns name the final files above.

## tests/unit/test_core.py

| Existing test | Behavior protected | Replacement target |
| --- | --- | --- |
| `test_resolve_draw_by_date_forward_scans_when_anchor_empty` | Date forward scan skips empty month; fallback note; month sequence | `test_bound_resolution` |
| `test_resolve_draw_by_date_returns_draw_number_without_fetching_draw` | Date resolution consults datepicker only, never fetches the Draw | `test_bound_resolution` |
| `test_resolve_draw_by_week_finds_draw_in_iso_week` | Exact in-week match resolves with no note | `test_bound_resolution` |
| `test_resolve_draw_by_week_uses_n_suffix_index` | `.N` selects the N-th distinct in-week Draw | `test_bound_resolution` |
| `test_resolve_draw_by_week_returns_draw_number_without_fetching_draw` | Week resolution consults datepicker only | `test_bound_resolution` |
| `test_main_week_2025_01_gathers_both_months_before_selecting_earliest` | Cross-year week gathers both months before omitted-index selection; fetches chosen Draw only | `test_bound_resolution` |
| `test_fetch_draw_from_args_routes_week` | `--week` routes to week resolution | `test_core` |
| `test_fetch_draw_from_args_routes_draw` | `--draw` routes to draw fetch | `test_core` |
| `test_main_start_draw_end_draw_prints_report` | `--start-draw/--end-draw` single-Draw report wiring | `test_core` |
| `test_main_start_draw_end_draw_prints_single_aggregated_report` | Spanning range renders one aggregated report | `test_core` |
| `test_main_start_draw_end_draw_reports_network_error_to_stderr` | Report-path request failure maps to exit 1 + stderr | `test_core` |
| `test_main_start_draw_without_end_draw_resolves_default_end_and_prints_report` | Default end is used and report printed | `test_core` |
| `test_main_start_draw_after_most_recent_prints_empty_report_without_fetch` | Reversed start vs default empty: empty report, no fetch | `test_core` |
| `test_main_start_draw_greater_than_end_draw_rejected` | Explicit `--start-draw > --end-draw` parser error, exit 2 | `test_core` |
| `test_main_start_date_end_draw_prints_report` | `--start-date` resolved start with explicit end prints report | `test_core` |
| `test_main_start_date_resolved_after_end_draw_fails_without_fetching` | Resolved start after explicit end: exit 1, no fetch | `test_core` |
| `test_main_start_draw_end_date_prints_report` | `--end-date` resolved end prints report | `test_core` |
| `test_resolve_end_bound_end_date_returns_latest_draw_on_or_before_bound` | End date resolves to latest Draw on/before bound | `test_bound_resolution` |
| `test_main_end_date_without_start_rejected` | `--end-date` without start rejected, exit 2 | `test_core` |
| `test_main_start_week_end_draw_prints_report` | `--start-week` resolved start prints report | `test_core` |
| `test_main_start_draw_end_week_prints_report` | Historical unindexed `--end-week` resolves to Sunday draw | `test_bound_resolution` |
| `test_resolve_end_bound_unindexed_historical_week_returns_latest_draw` | Unindexed end week is latest Draw on/before ISO Sunday | `test_bound_resolution` |
| `test_main_excessive_end_week_index_falls_back_to_final_draw` | Completed excessive end index falls back to final in-week Draw + warning | `test_bound_resolution` |
| `test_main_cross_year_indexed_end_first_draw_requires_both_months` | Cross-year indexed end gathers both week months before `.1` selection | `test_bound_resolution` |
| `test_main_excessive_end_week_same_date_draws_tie_break_by_number` | Duplicate/unsorted entries collapse; same-date tie-break by draw number | `test_bound_resolution` |
| `test_main_indexed_empty_completed_end_week_selects_predecessor_draw` | Empty completed indexed end falls back to preceding Draw + warning | `test_bound_resolution` |
| `test_main_current_week_indexed_end_after_today_clamps_to_latest_draw` | Current-week indexed end after today clamps silently | `test_bound_resolution` |
| `test_main_future_indexed_end_week_clamps_to_latest_draw` | Wholly future indexed end clamps without future-month lookup | `test_bound_resolution` |
| `test_main_end_week_without_start_rejected` | `--end-week` without start rejected, exit 2 | `test_core` |
| `test_draw_numbers_in_range_walks_across_drawless_months` | Inclusive `[start, end]` draw-number walk across drawless months | `test_period_collection` |
| `test_draw_numbers_in_range_warns_when_end_unreached` | End unreached within scan window warns (truncation) | `test_period_collection` |
| `test_fetch_report_draws_spanning_walks_datepicker_and_filters` | Spanning collection filters to in-range Draws | `test_period_collection` |
| `test_fetch_report_draws_single_does_not_touch_datepicker` | Single-Draw range skips the datepicker walk | `test_period_collection` |
| `test_fetch_report_draws_returns_empty_when_start_draw_absent` | Missing anchor Draw yields empty Period | `test_period_collection` |
| `test_fetch_report_draws_skips_missing_draw_fetch_failure` | Missing interior Draw (404) is skipped + warned | `test_period_collection` |
| `test_fetch_report_draws_propagates_network_failure` | Non-404 interior request failure propagates | `test_period_collection` |
| `test_resolve_draw_by_date_raises_after_12_empty_months` | Forward scan exhausts 12 months and raises | `test_bound_resolution` |
| `test_main_reports_draw_not_found` | `main` maps `DrawNotFound` to exit 1 + stderr | `test_core` |
| `test_resolve_default_end_returns_latest_entry_on_or_before_today` | Default end picks latest entry on/before today | `test_bound_resolution` |
| `test_resolve_default_end_falls_back_one_month_when_none_eligible` | Backward scan crosses the year boundary when today's month is empty | `test_bound_resolution` |
| `test_resolve_default_end_stops_scanning_once_entry_found` | Backward scan stops at first month with an eligible entry | `test_bound_resolution` |
| `test_resolve_default_end_raises_when_no_entry_in_scan_window` | Backward scan exhausts 12 months and raises | `test_bound_resolution` |
| `test_main_returns_network_error_to_stderr` | Display-path request failure maps to exit 1 + stderr | `test_core` |
| `test_main_spanning_report_errors_when_anchor_has_no_close_time` (new) | Anchor Draw without `reg_close_time` fails a spanning collection with exit 1 | `test_period_collection` |

## tests/e2e/test_cli_report.py

### Validation -> `test_cli_report_validation.py`

| Existing test / parameter group | Behavior protected |
| --- | --- |
| `test_help_shows_start_draw_end_draw_usage` | Report bound flags appear in help |
| `test_start_draw_argument_required` | No arguments exits non-zero naming a start bound |
| `test_start_draw_end_draw_mutually_exclusive[args0..5]` | Start bounds mutually exclusive with `--draw/--date/--week`; end requires start |
| `test_start_draw_after_end_draw_errors` | Explicit start greater than end errors on stderr |
| `test_invalid_start_draw_or_end_draw_rejected[args0..3]` | Non-integer draw bounds rejected, exit 2 |
| `test_end_without_start_rejected[args0..2]` | `--end-draw/--end-date/--end-week` without a start bound rejected, exit 2 |

### Collection -> `test_cli_report_collection.py`

| Existing test | Behavior protected |
| --- | --- |
| `test_start_draw_end_draw_4900_reports_buckets` | Single-Draw report buckets and exact percentages |
| `test_start_draw_end_draw_excludes_played_without_odds` | Played odds-less matches counted as excluded |
| `test_start_draw_end_draw_spanning_months_aggregates` | Cross-month inclusive aggregation, nothing outside range fetched |
| `test_start_draw_end_draw_walks_datepicker_across_drawless_months` | Collection walks 404 drawless months, inclusive bounds |
| `test_start_draw_end_draw_skips_absent_draw_number` | Draw absent from datepicker is never fetched or counted |
| `test_start_draw_end_draw_reports_and_skips_fetch_failure` | Interior Draw 404 warns and is skipped; rest aggregated |
| `test_start_draw_end_draw_empty_range_prints_empty_report` | Absent anchor prints empty report, exit 0 |
| `test_start_draw_end_draw_anchor_returns_null_draw_prints_empty_report` | API `"draw": null` treated as absent anchor, no traceback |

### End bounds -> `test_cli_report_end_bounds.py`

| Existing test / parameter group | Behavior protected |
| --- | --- |
| `test_start_draw_without_end_draw_defaults_to_most_recent_draw` | Default end = latest entry on/before today; cross-month aggregation |
| `test_start_draw_after_most_recent_draw_prints_empty_report` | Start after default end: empty report, anchor never fetched |
| `test_start_date_resolves_to_draw` | Start date resolves via datepicker and reuses resolver |
| `test_end_date_resolves_to_draw[2025-05-10, 2025-05-11]` | Exact and non-draw end date resolve to latest on/before; today month untouched |
| `test_future_end_date_clamps_to_today` | Future end date clamps to today; future month never looked up |
| `test_future_end_week_clamps_to_today[2025.23, .1, .3]` | Wholly future end week clamps silently, indexed or not |
| `test_start_week_resolves_to_draw` | Start week reuses the week resolver |
| `test_end_week_resolves_to_draw[2024.52, .1, .2]` | Historical end week includes both Draws unless `.1` explicit |
| `test_current_week_indexed_end_selects_first_draw` | Current-week explicit index selects only that Draw, no warning |
| `test_excessive_end_week_index_clamps_silently_only_while_week_is_current[sunday-current-week, monday-completed-week]` | Excessive index clamps silently while current; warns once completed |
| `test_current_week_later_or_missing_index_clamps_to_latest_draw[published-draw-after-today, unavailable-index, no-draw-yet-this-week]` | Current-week index at/past today clamps to latest on/before today |
| `test_unindexed_drawless_end_week_resolves_to_latest_preceding_draw` | Empty historical unindexed end week ends at latest preceding Draw, no warning |
| `test_indexed_empty_completed_end_week_resolves_to_preceding_draw` | Indexed empty completed week falls back to preceding Draw + warning |
| `test_historical_end_bound_searches_back_across_empty_months[date, week]` | Backward search crosses empty/404 months to latest predecessor |
| `test_end_bound_without_preceding_draw_errors_after_backward_window[3]` | Backward window is exactly 12 months; bounded error, no warning |
| `test_mixed_start_date_end_week_aggregates` | Mixed start-date/end-week exact resolutions aggregate |
| `test_resolved_start_after_end_errors[date, week]` | Resolved start after explicit end errors before any Draw fetch |
| `test_start_date_forward_scans_across_empty_months` | Start date forward-scans; fallback note; no Draw after resolved end |
| `test_excessive_end_week_index_resolves_to_final_draw` | Completed excessive end index falls back to final Draw + warning |
| `test_cross_year_end_week_selects_distinct_draws[.1, .2, .3]` | Cross-year duplicate/unsorted entries: indexing, aggregation, excessive fallback |
| `test_unindexed_current_end_week_clamps_to_latest_draw` (new) | Unindexed end week that contains today clamps to latest Draw on/before today, no warning, no future month |

## tests/e2e/test_cli_date.py and tests/e2e/test_cli_week.py

These remain HTTP-level E2E over the real adapter/parser and only need clock
adaptation to the injection seam:

| Existing test / group | Behavior protected |
| --- | --- |
| `test_date.py::test_date_2025_05_10_finds_draw_4900` | `--date` exact match through adapter |
| `test_date.py::test_date_2020_04_01_forward_scans_to_june` | `--date` forward scan + fallback note |
| `test_date.py::test_date_2000_01_01_no_draw_12_months` | `--date` scan limit error |
| `test_date.py::test_date_invalid_date_returns_exit_code_1` | Invalid date exit 1 |
| `test_date.py::test_date_no_match_returns_exit_code_1` | No match within window exit 1 |
| `test_week.py::test_invalid_week_is_rejected_by_argparse` | Malformed `--week` rejected by argparse |
| `test_week.py::test_week_2025_19_finds_draw_4900` | `--week` exact match through adapter |
| `test_week.py::test_week_2024_52_2_selects_second_draw` | `--week .N` index through adapter |
| `test_week.py::test_week_2024_52_3_exceeds_draw_count` | Excessive `--week` index error message |
| `test_week.py::test_week_2020_15_forward_scans_to_june` | Empty `--week` forward scan + fallback note |
| `test_week.py::test_week_2025_01_shared_across_months[...]` | Cross-year duplicate/unsorted responses gathered before indexing |

## Coverage gaps closed in batch 1

- **Close-time error**: no test forced a spanning collection to consume an anchor
  Draw with `reg_close_time = None`, which `_draw_month` rejects. Added to
  `tests/unit/test_core.py` (moves to `test_period_collection.py`).
- **Unindexed current end week**: only wholly future and completed unindexed end
  weeks were covered; a week containing today was not. Added to
  `tests/e2e/test_cli_report.py` (moves to `test_cli_report_end_bounds.py`).

All other listed behaviors already have coverage; no further characterization
tests were manufactured.

## Implemented boundary contract (batch 2)

The public contracts live in `stryktips/core.py` for now, to avoid a circular
import between the CLI and the services; #102/#103 may relocate them. No
imports or `main(argv=None)` / `create_parser()` signatures changed. Production
actually invokes these contracts; the CLI still owns parsing/validation, stdout
rendering, stderr and exit-code mapping.

```python
FetchDraw = Callable[[int], Draw]
FetchMonthEntries = Callable[[int, int], list[DatepickerEntry]]
Clock = Callable[[], date]
Diagnostic = Callable[[str], None]


@dataclass(frozen=True)
class DrawByNumber:
    number: int


@dataclass(frozen=True)
class DrawByDate:
    value: str


@dataclass(frozen=True)
class DrawByWeek:
    value: str          # single constructor input, original spelling
    year: int           # derived from value in __post_init__
    week: int           # derived from value in __post_init__
    index: int | None   # derived; None when the text omitted .N


DrawSelector = DrawByNumber | DrawByDate | DrawByWeek


@dataclass(frozen=True)
class Dependencies:
    fetch_draw: FetchDraw
    fetch_month_entries: FetchMonthEntries
    clock: Clock
    diagnostic: Diagnostic


def create_dependencies(
    *,
    fetch_draw: FetchDraw | None = None,
    fetch_month_entries: FetchMonthEntries | None = None,
    clock: Clock | None = None,
    diagnostic: Diagnostic | None = None,
) -> Dependencies: ...


def resolve_draw(selector: DrawSelector, dependencies: Dependencies) -> int: ...
def resolve_end(selector: DrawSelector | None, dependencies: Dependencies) -> int: ...
def collect_period(start: int, end: int, dependencies: Dependencies) -> list[Draw]: ...
```

Decisions taken versus the earlier proposal:

- **Typed selectors, not six optional flags.** The CLI builds one
  `DrawSelector` from the parsed arguments and passes it to the services.
  `DrawByWeek` takes only the raw week text; `year`, `week`, and `index` are
  derived from it, so the selector cannot hold contradictory state. The raw
  spelling is kept so diagnostics are byte-identical, and `index is None`
  preserves the unindexed-week policy distinct from an explicit `.1`.
- **Forward resolution is shared; the end policy is separate.**
  `resolve_draw` serves both the single-Draw CLI path and the report start
  bound. `resolve_end` applies the end policy for a single selector; the CLI's
  date-before-week-before-draw flag precedence lives in `_end_selector`, which
  builds that selector.
- **`collect_period` takes resolved inclusive ints** and returns the Draws in
  `[start, end]`.
- **One small dependency object instead of long parameter lists.**
  Resolution, collection, and diagnostics all take `dependencies`; the private
  helpers were threaded explicitly with it. There is no global mutation or
  context lookup on the call path.
- **`create_dependencies()` is the composition seam.** `main` calls it with no
  arguments; its concrete defaults (`fetch_draw`, `fetch_draws_by_month`,
  `date.today`, a stderr diagnostic) are read from the module at call time, so
  existing monkeypatching still works and tests can inject fakes and a fixed
  clock without changing `main`'s signature. `tests/unit/test_core.py` proves
  the seam by replacing `create_dependencies` with a `Dependencies` instance.
- **Existing pure selection collaborators stay real** (`resolve_draw_by_date`,
  `resolve_draw_by_week`, `entries_in_week`, `parse_week`), and exact
  user-facing wording, validation timing, exit codes, and
  `MAX_SCAN_MONTHS = 12` are unchanged.
- **No substantive extraction or parser decomposition**; `_resolve_draw_by_week`
  and `_resolve_completed_indexed_end_week` keep their statement-limit
  suppressions for #102/#103 to remove by simplification.

## Public contract tests added in batch 2

- `tests/unit/test_bound_resolution.py` — 18 tests over `resolve_draw` and
  `resolve_end`: number/date/week selectors, exact vs fallback and its note,
  cross-year month gathering, duplicate/unsorted indexing, excessive indices,
  scan-window exhaustion, end precedence/defaults, unindexed vs explicit `.1`,
  future/current/completed end weeks, and the backward-window limit.
- `tests/unit/test_period_collection.py` — 7 tests over `collect_period`:
  single-draw shortcut, inclusive spanning bounds, skipped/reported missing
  draws, propagated request failures, empty anchor, truncation warning, and the
  anchor close-time error.
