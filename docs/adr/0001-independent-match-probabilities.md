# ADR 0001: Independent Match Probabilities

Both `svenskaFolket` distributions and outcome probabilities (derived from odds) are modeled as independent across matches within a Draw. This means the probability of a specific Row is the simple product of per-Match probabilities, and the `svenskaFolket` share of a Row is the product of per-Match shares.

This keeps the valuation space at 3^13 ≈ 1.6 million Rows, making brute-force computation feasible. Modeling match-level correlations would require Monte Carlo sampling or a more complex joint distribution with uncertain accuracy gains.

The assumption is a deliberate simplification. If future analysis shows systematic correlation (e.g. league-wide trends affecting multiple matches), this ADR should be revisited.
