# Findings (verified runs)

## Round 1 - 2026-10-26, branch `intraday-results-round1`

* Data: CoinDCX futures `B-BTC_USDT` and `B-PAXG_USDT` are listed (504 active USDT futures). 180 days of 5m and 15m
  candles, 2026-04-29 to 2026-10-26, **0 missing bars, 0 duplicates**, a few extreme-return bars flagged (kept).
* ~1,500 configs per asset x timeframe. **No CANDIDATE.** Every finalist failed on TEST or VAL.
* Cause found: stops were too tight for the costs. PAXG 5m median stop 0.22% vs 0.158% round-trip cost
  (fee 0.05% + 18% GST + 0.02% slippage, per side); in quiet hours the stop was even smaller, so cost alone was several R.

## Round 2 - min stop 0.25%, stops 2-5 ATR, holds 4/12h

Rule chosen from cost arithmetic, not from TEST. Round-1 TEST had already been seen, so this TEST is not pristine.

* Still **no CANDIDATE** on BTC or PAXG, 5m or 15m, LONG or SHORT.
* Best DEV results are no better than random-entry searches of the same size (null percentile 0-75%, needs 95%).
* "Enter every bar" baselines lose 0.13-0.56 R per trade on TEST after costs.

## Conclusion

At 5m / 15m on CoinDCX futures, the tested indicator, price-action and SMC rules show no edge that survives costs and
out-of-sample checks in this 180-day window. Searching harder on the same data would mostly find luck.
The existing 1h PAXG candidate (paper-trading job) is a different, slower strategy and is not affected.

Next experiments worth doing (each with its own untouched data): 1h / 4h bars where cost is a small share of the move,
maker (limit) entries if fees are lower, and re-running frozen finalists on data after 2026-10-26 as a forward test.
