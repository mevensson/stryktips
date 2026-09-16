"""Contract tests for the shared Match and Draw test builders."""

from datetime import datetime
from decimal import Decimal

from stryktips.models import Odds, OutcomeProbability
from tests.builders import make_draw, make_match


def test_make_match_defaults_are_fresh_per_call():
    """Each call gets its own nested odds and probability objects."""
    # Act
    first = make_match()
    second = make_match()

    # Assert
    assert first.odds is not second.odds
    assert first.outcome_probability is not second.outcome_probability


def test_make_match_default_odds_and_probability_are_consistent():
    """Default probabilities are the overround-free view of the default odds."""
    # Act
    match = make_match()

    # Assert
    assert match.odds == Odds(
        home=Decimal("2.0"), draw=Decimal("4.0"), away=Decimal("4.0")
    )
    assert match.outcome_probability == OutcomeProbability(
        home=Decimal("0.5"), draw=Decimal("0.25"), away=Decimal("0.25")
    )


def test_make_match_derives_probability_from_supplied_odds():
    """Supplying odds alone derives their overround-free probabilities."""
    # Arrange
    odds = Odds(home=Decimal("2.0"), draw=Decimal("4.0"), away=Decimal("4.0"))

    # Act
    match = make_match(odds=odds)

    # Assert
    assert match.outcome_probability == OutcomeProbability(
        home=Decimal("0.5"), draw=Decimal("0.25"), away=Decimal("0.25")
    )


def test_make_match_explicit_none_odds_yields_no_probability():
    """An explicit odds=None is distinct from omitted odds and drops probability."""
    # Act
    match = make_match(odds=None)

    # Assert
    assert match.odds is None
    assert match.outcome_probability is None


def test_make_match_supplied_odds_that_cannot_be_derived_yield_no_probability():
    """Non-positive odds are kept but leave the derived probability absent."""
    # Arrange
    odds = Odds(home=Decimal("0"), draw=Decimal("4.0"), away=Decimal("4.0"))

    # Act
    match = make_match(odds=odds)

    # Assert
    assert match.odds == odds
    assert match.outcome_probability is None


def test_make_match_explicit_none_probability_suppresses_derivation():
    """An explicit probability=None wins over deriving from the default odds."""
    # Act
    match = make_match(outcome_probability=None)

    # Assert
    assert match.odds is not None
    assert match.outcome_probability is None


def test_make_match_explicit_probability_is_preserved_without_normalising():
    """An explicit probability is used verbatim even when it does not sum to one."""
    # Arrange
    probabilities = OutcomeProbability(
        home=Decimal("0.9"), draw=Decimal("0.9"), away=Decimal("0.9")
    )

    # Act
    match = make_match(
        odds=Odds(home=Decimal("2.0"), draw=Decimal("4.0"), away=Decimal("4.0")),
        outcome_probability=probabilities,
    )

    # Assert
    assert match.outcome_probability == probabilities


def test_make_draw_default_is_a_renderable_played_draw():
    """The default Draw is one played match with odds, probability and close time."""
    # Act
    draw = make_draw()

    # Assert
    assert len(draw.matches) == 1
    match = draw.matches[0]
    assert match.home_score is not None
    assert match.away_score is not None
    assert match.odds is not None
    assert match.outcome_probability is not None
    assert draw.reg_close_time == datetime(2025, 5, 10, 15, 59)


def test_make_draw_default_matches_are_fresh_per_call():
    """Each default Draw gets its own list and its own Match."""
    # Act
    first = make_draw()
    second = make_draw()

    # Assert
    assert first.matches is not second.matches
    assert first.matches[0] is not second.matches[0]


def test_make_draw_copies_supplied_matches():
    """A supplied matches list is copied rather than aliased by the Draw."""
    # Arrange
    supplied = [make_match()]

    # Act
    draw = make_draw(matches=supplied)
    supplied.append(make_match())

    # Assert
    assert draw.matches is not supplied
    assert len(draw.matches) == 1


def test_make_draw_supports_explicit_empty_matches():
    """An explicit empty list is distinct from omitted matches."""
    # Act
    draw = make_draw(matches=[])

    # Assert
    assert draw.matches == []


def test_make_draw_supports_explicit_none_close_time():
    """An explicit reg_close_time=None drops the default close time."""
    # Act
    draw = make_draw(reg_close_time=None)

    # Assert
    assert draw.reg_close_time is None
