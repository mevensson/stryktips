"""Display formatting for Stryktipset matches."""

from stryktips.models import Match


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
    return (
        f"{match.event_number}. {match.home_team} - {match.away_team}"
        f" | {outcome} | {one}% - {x}% - {two}%"
    )


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
