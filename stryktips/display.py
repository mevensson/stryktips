"""Display formatting for Stryktipset matches."""

from stryktips.models import Match
from stryktips.odds import remove_overround


def format_matches(matches: list[Match]) -> list[str]:
    """Format matches into display strings.

    Args:
        matches: List of Match domain models.

    Returns:
        List of formatted match strings.
    """
    return [_format_match(m) for m in matches]


def _format_match(match: Match) -> str:
    outcome = _outcome(match)
    one, x, two = _percentages(match)
    odds_str = _format_odds(match)
    probs_str = _format_outcome_probabilities(match)
    return (
        f"{match.event_number}. {match.home_team} - {match.away_team}"
        f" | {outcome} | {one}% - {x}% - {two}%{odds_str}{probs_str}"
    )


def _format_odds(match: Match) -> str:
    if match.odds is None:
        return ""
    return f" | {match.odds.home:.2f} - {match.odds.draw:.2f} - {match.odds.away:.2f}"


def _format_outcome_probabilities(match: Match) -> str:
    if match.odds is None:
        return ""
    home_p, draw_p, away_p = remove_overround(
        match.odds.home, match.odds.draw, match.odds.away,
    )
    home_pct = int(round(home_p * 100))
    draw_pct = int(round(draw_p * 100))
    away_pct = int(round(away_p * 100))
    return f" | {home_pct}% - {draw_pct}% - {away_pct}%"


def _outcome(match: Match) -> str:
    if match.home_score is not None and match.away_score is not None:
        if match.home_score > match.away_score:
            return "1"
        if match.home_score < match.away_score:
            return "2"
        return "X"
    return "?"


def _percentages(match: Match) -> tuple[str, str, str]:
    if match.svenska_folket:
        return (
            match.svenska_folket.one,
            match.svenska_folket.x,
            match.svenska_folket.two,
        )
    return ("0", "0", "0")
