# ADR 0002: Probability-Bucket Report

The prediction-quality report buckets the predicted probabilities of each eligible match — played with odds (`startOdds`) — into 10%-wide buckets. Each eligible match contributes **three** probability values, `P(home)`, `P(draw)`, and `P(away)`, and each value is placed into its own bucket. Buckets use the `[low, high)` convention: a value of exactly 0.50 lands in the 40–50 bucket, and 1.0 is clamped to the 90–100 bucket. This guarantees every value lands in exactly one bucket, with no boundary double-counting. Buckets with a zero count are omitted from the report.

For each bucket, the report shows:

- **count** — the number of probability values in the bucket.
- **mean predicted** — the average of those probability values.
- **observed** — the share of those values whose outcome actually occurred.
- **gap** — observed minus mean predicted.

Because each match contributes all three probabilities rather than only the realized one, the observed frequency genuinely varies per bucket, so a 50–60% bucket can come true about half the time and the report is a meaningful calibration.

Played-but-odds-less matches (no `startOdds`, hence no outcome probability) are counted in an "excluded" summary line rather than dropped, so under-covered periods are visible in the report. Unplayed matches are silently ignored. The summary line counts matches, not probability values.
