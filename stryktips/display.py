"""Display formatting for Stryktipset matches."""

from stryktips.models import Match


def format_matches(matches: list[Match]) -> list[str]:
    """Format matches into display strings.

    Args:
        matches: List of Match domain models.

    Returns:
        List of formatted match strings.
    """
    result = []
    for match in matches:
        if match.home_score is not None and match.away_score is not None:
            if match.home_score > match.away_score:
                outcome = "1"
            elif match.home_score < match.away_score:
                outcome = "2"
            else:
                outcome = "X"
        else:
            outcome = "?"

        if match.svenska_folket:
            one = match.svenska_folket.one
            x = match.svenska_folket.x
            two = match.svenska_folket.two
        else:
            one = x = two = "0"

        formatted = f"{match.event_number}. {match.home_team} - {match.away_team} | {outcome} | {one}% - {x}% - {two}%"
        result.append(formatted)

    return result
