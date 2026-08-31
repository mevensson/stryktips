# ADR 0002: Probability-Bucket Report

The prediction-quality report buckets each played, odds-bearing match by the predicted probability of the outcome that actually happened. Each eligible match contributes exactly one probability value — P(home) for a home win, P(draw) for a draw, P(away) for an away win — and that value is placed into a 10%-wide bucket.

Buckets use the `[low, high)` convention: a value of exactly 0.50 lands in the 40–50 bucket, and 1.0 is clamped to the 90–100 bucket. This guarantees every value lands in exactly one bucket, with no boundary double-counting.

Played-but-odds-less matches (no `startOdds`, hence no outcome probability) are counted in an "excluded" summary line rather than dropped, so under-covered periods are visible in the report. Unplayed matches are silently ignored.

This slice deliberately stops at counts; mean/observed/gap columns land in a later ticket. The `[low, high)` convention and realized-outcome selection should be revisited if the report ever aggregates continuous values or changes how outcomes are resolved.