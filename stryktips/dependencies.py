"""Injected I/O, clock, and diagnostic boundaries for the CLI services.

The callable aliases and the ``Dependencies`` object are the contracts that
bound resolution and Period collection depend on. Concrete collaborators — the
network client, the system clock, and stderr — are wired only by
``create_dependencies`` in the CLI composition root.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from stryktips.models import DatepickerEntry, Draw

FetchDraw = Callable[[int], Draw]
FetchMonthEntries = Callable[[int, int], list[DatepickerEntry]]
Clock = Callable[[], date]
Diagnostic = Callable[[str], None]


@dataclass(frozen=True)
class Dependencies:
    """The injected I/O, clock, and diagnostics for the CLI services.

    ``fetch_draw`` fetches one Draw, ``fetch_month_entries`` looks up a
    datepicker month, ``clock`` supplies today's date, and ``diagnostic``
    receives user-facing warning and fallback lines. Resolution and collection
    never reach for a global network client, clock, or output stream.
    """

    fetch_draw: FetchDraw
    fetch_month_entries: FetchMonthEntries
    clock: Clock
    diagnostic: Diagnostic
