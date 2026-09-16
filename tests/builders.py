"""Typed constructor-style builders for domain objects used across tests."""

from datetime import datetime
from decimal import Decimal

from stryktips.models import Draw, Match, Odds, OutcomeProbability, SvenskaFolket
from stryktips.odds import remove_overround


class _Unset:
    """Sentinel type marking a builder keyword as omitted rather than ``None``."""


_UNSET = _Unset()

_DEFAULT_CLOSE_TIME = datetime(2025, 5, 10, 15, 59)


def make_match(  # noqa: PLR0913 (mirrors every Match field as an override)
    *,
    event_number: int = 1,
    home_team: str = "Home",
    away_team: str = "Away",
    home_score: int | None = 1,
    away_score: int | None = 0,
    svenska_folket: SvenskaFolket | None = None,
    odds: Odds | None | _Unset = _UNSET,
    outcome_probability: OutcomeProbability | None | _Unset = _UNSET,
) -> Match:
    """Construct a Match, overriding the given fields.

    Defaults describe a played home win with fresh odds and matching outcome
    probabilities. Pass ``odds=None`` for an odds-less state, or
    ``outcome_probability=None`` to drop the probability while keeping odds.

    When ``outcome_probability`` is omitted it is derived from the effective
    odds by removing the overround. The derivation is skipped when the odds
    are ``None`` or not positive, leaving the probability ``None``. An
    explicit ``outcome_probability`` (including ``None``) is used verbatim and
    never normalised.
    """
    if isinstance(odds, _Unset):
        resolved_odds: Odds | None = _default_odds()
    else:
        resolved_odds = odds

    resolved_probability: OutcomeProbability | None
    if isinstance(outcome_probability, _Unset):
        resolved_probability = _derive_probability(resolved_odds)
    else:
        resolved_probability = outcome_probability

    return Match(
        event_number=event_number,
        home_team=home_team,
        away_team=away_team,
        home_score=home_score,
        away_score=away_score,
        svenska_folket=svenska_folket,
        odds=resolved_odds,
        outcome_probability=resolved_probability,
    )


def make_draw(
    *,
    draw_number: int = 1,
    matches: list[Match] | None = None,
    draw_comment: str | None = None,
    reg_close_time: datetime | None = _DEFAULT_CLOSE_TIME,
) -> Draw:
    """Construct a Draw, overriding the given fields.

    The default Draw is a minimal renderable sample: one fully populated
    played Match and a fixed close time. ``matches=None`` selects that default;
    pass ``matches=[]`` for an empty Draw or ``reg_close_time=None`` to drop
    the close time.

    A supplied ``matches`` list is copied, so the Draw never aliases the
    caller's list, and each default Match is freshly constructed.
    """
    resolved_matches = [make_match()] if matches is None else list(matches)
    return Draw(
        draw_number=draw_number,
        matches=resolved_matches,
        draw_comment=draw_comment,
        reg_close_time=reg_close_time,
    )


def _default_odds() -> Odds:
    """Return fresh default odds that remove to (0.5, 0.25, 0.25)."""
    return Odds(home=Decimal("2.0"), draw=Decimal("4.0"), away=Decimal("4.0"))


def _derive_probability(odds: Odds | None) -> OutcomeProbability | None:
    """Derive outcome probabilities from odds, or None when unusable."""
    if odds is None:
        return None
    try:
        home, draw, away = remove_overround(odds.home, odds.draw, odds.away)
    except ValueError:
        return None
    return OutcomeProbability(home=home, draw=draw, away=away)
