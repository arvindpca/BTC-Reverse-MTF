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

## BTC 1h loss study - 2026-10-26 (`intraday/loss_study.py`, files in `intraday/reports/btc1h_loss_study/`)

Setup: BTC 1h LONG momentum candle + ADX > 25 + EMA20 > EMA50, stop 1.5 ATR, target 3R, 48h.
Losers vs winners compared on DEV only; filters picked on DEV + VAL; 30 random-noise "features" searched the same way.

* DEV losses: 36 stop-outs (-41.7R) vs 23 targets (+65.0R). Entries 18:00-24:00 IST lost (-0.09R avg, 31 trades);
  other hours +0.8 to +1.1R. Losers came after smaller 24h/72h rallies and slightly higher volatility.
* Chosen filter (best on DEV + VAL): skip when volatility is > 1.3x its usual level. DEV +0.43 -> +0.63R,
  VAL +0.58 -> +0.91R, but TEST +0.26 -> +0.14R. It did not help on new data.
* Diagnostic, TEST of other top filters: 3 of 7 better than no filter, 4 worse; average TEST sum below the base.
  "Skip 18:30-24:00 IST" was best on TEST (+0.70R, 17 trades) but worse than base on VAL.
* Noise features reached scores up to 1.92 vs 2.11 for the best real filter: most of the gain is what luck also gives.
* Decision: keep the base setup unfiltered. Track the entry hour during paper trading to re-check the evening effect.

## BTC 1h paper trading

* 2026-10-27: hourly paper log started (3000 + 1000/month, 2% risk). Engine reproduces the 120 backtest trades exactly.
* 2026-10-29: switched to the LIVE method (`intraday/live_btc1h.py`, workflow `btc1h_live.yml`): live-price entry right
  after the signal candle closes, SL/target watched every ~15 s on 1m candles, instant alerts, 6-hour jobs chained.
  State, report and trade log stay on the `btc1h-paper-state` branch (same account, history kept).
