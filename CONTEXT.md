# Stryktips

A CLI tool that fetches and displays Swedish Stryktipset match data, with a planned valuation engine to compute expected values of betting rows.

## Language

**Draw**:
A weekly Stryktipset betting event comprising exactly 13 matches, identified by a `drawNumber`.
_Avoid_: Week, coupon

**Match**:
A single football fixture within a Draw, with home/away participants, a result (1/X/2), a `svenskaFolket` distribution, and a set of Odds.
_Avoid_: Game, event

**Odds**:
Decimal odds (1, X, 2) for a Match as set by a bookmaker. Currently sourced from Svenska Spel's `startOdds`.
_Avoid_: Betting line, price

**Overround**:
The bookmaker's margin baked into odds, visible as the sum of implied probabilities exceeding 100%.
_Avoid_: Juice, vig

**Row**:
A 13-element prediction vector with one 1/X/2 choice per Match.
_Avoid_: Rad, ticket, coupon

**PrizeTier**:
A payout bucket for Rows achieving exactly N correct predictions (10, 11, 12, or 13).
_Avoid_: Prize pool, vinstgrupp

**RowValuation**:
The expected value of a Row, computed from outcome probabilities, PrizeTier shares, and `svenskaFolket` market share.
_Avoid_: EV, expected return

**svenskaFolket**:
The public betting distribution for a Match, expressed as percentages for 1, X, and 2.
_Avoid_: Public distribution, folkets rad

**Outcome Probability**:
The estimated true probability of a Match finishing as 1, X, or 2, derived from Odds by removing the Overround.
_Avoid_: Odds probability
