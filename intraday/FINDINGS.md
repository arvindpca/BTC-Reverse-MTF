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

## Time-window study - 2026-10-26 (`intraday/time_study.py`, report in `intraday/reports/`)

Only filter = entry time window (4/6/8 hours, any start), chosen on DEV, ranked on VAL, TEST checked once.
Same CoinDCX data, round-2 costs and min stop.

* **0 CANDIDATE** in 24 finalists (BTC/PAXG x 5m/15m x LONG/SHORT). Every finalist lost money on TEST.
* Windows that looked best on DEV changed on VAL and TEST: no stable "best time".
* Some hours drift the same way in all three periods (e.g. BTC 01:30-02:30 IST up, PAXG 13:30-14:30 IST down),
  but the average move is 0.01-0.08% per hour, below the 0.16% round-trip cost. Not tradable alone.
* Busiest hours (biggest moves): BTC 17:30-21:30 IST, PAXG 17:30-19:30 IST (US session open/data releases).

## 1h / 4h study - 2026-10-26 (results branch `intraday-results-1h4h`)

Fresh search on 1h and 4h (4h built from CoinDCX 1h candles). BTC: 3 years (2023-10 to 2026-10, 26,278 1h bars,
0.008% missing). PAXG futures history on CoinDCX only goes back to ~2025-03 (578 days). Stops 1.5-4 ATR, holds 12-96h.

* **0 CANDIDATE.** 23 of 24 finalists fail at least one check.
* Closest: **BTC 1h LONG, strong green momentum candle + ADX > 25 + EMA20 > EMA50, stop 1.5 ATR, target 3R, 48h max.**
  Passes every check except test size (26 trades, needs 30): dev +0.43R (66 trades), val +0.58R (28), test +0.26R
  (PF 1.36), still +0.15R at 1.5x costs, walk-forward +6.4R with 67% positive folds, positive every calendar year,
  search beats 95% of random searches. Median stop 0.98%. About 3 trades a month. -> watchlist / forward paper test only.
* PAXG 1h/4h: nothing stable; the history is short and the test period (Jun-Oct 2026, PAXG -10%) differs from dev.
