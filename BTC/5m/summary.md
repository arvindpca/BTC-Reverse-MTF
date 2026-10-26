## BTC 5m

51840 bars, 2026-04-29 19:25 to 2026-10-26 19:20 UTC. Costs 0.079% per side (+funding). 1608 configs searched.

| segment | from | to | buy & hold |
|---|---|---|---|
| dev | 2026-04-30 20:25 | 2026-07-28 19:20 | -16.59% |
| val | 2026-07-28 19:25 | 2026-09-11 19:20 | 21.17% |
| test | 2026-09-11 19:25 | 2026-10-26 19:20 | 3.63% |

Search vs luck: best DEV t-stat (no filters) = -1.34; it beats 100% of 20 random-entry searches of the same size.

| side | config | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | TEST max DD | gross exp R | 1.5x cost exp R | WF OOS sum R (pos folds) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | rsi_rev25 [htf1h] sl 3.0ATR rr 3.0 8h | 46 / 0.1233 | 28 / -0.1988 | 27 | 26 | -0.6762 | 0.281 | -18.26 | 16.89% | -0.2842 | -0.866 | -9.14 (60%) | **INCONCLUSIVE (too few test trades)** |
| LONG | vwap_rev2.5 [us_13_21+vol_high] sl 3.0ATR rr 3.0 8h | 77 / -0.1858 | 34 / -0.311 | 38 | 34 | -0.4264 | 0.459 | -16.2 | 17.05% | -0.1413 | -0.5644 | -11.88 (40%) | **NO EDGE PROVEN** |
| LONG | sweep_rev48 [-] sl 3.0ATR rr 3.0 8h | 254 / -0.3913 | 129 / -0.5887 | 140 | 27 | -0.6011 | 0.405 | -84.15 | 57.6% | -0.1564 | -0.8182 | -146.25 (0%) | **NO EDGE PROVEN** |
| SHORT | rsi_rev30 [weekday+htf1h] sl 3.0ATR rr 3.0 8h | 58 / -0.1392 | 35 / -0.0552 | 34 | 41 | 0.0764 | 1.108 | 2.6 | 6.04% | 0.4242 | -0.0936 | -5.14 (40%) | **NO EDGE PROVEN** |
| SHORT | candle_momo [weekday+europe_07_13] sl 3.0ATR rr 3.0 8h | 73 / -0.0488 | 38 / -0.2155 | 38 | 32 | -0.2094 | 0.78 | -7.96 | 16.69% | 0.1889 | -0.4047 | -29.26 (0%) | **NO EDGE PROVEN** |
| SHORT | rsi_rev25 [rvol_spike+atr_expand] sl 2.0ATR rr 3.0 8h | 46 / -0.219 | 21 / -0.2382 | 18 | 17 | -0.9773 | 0.304 | -17.59 | 16.41% | -0.3333 | -1.2976 | -33.62 (20%) | **INCONCLUSIVE (too few test trades)** |

Baseline (enter every bar, exit picked on DEV): LONG TEST n=302 exp R=-0.5242; SHORT TEST n=302 exp R=-0.5317
