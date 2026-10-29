## BTC 1h

26278 bars, 2023-10-30 05:00 to 2026-10-29 04:00 UTC. Costs 0.079% per side (+funding). 1579 configs searched. Min stop 0.25%.

| segment | from | to | buy & hold |
|---|---|---|---|
| dev | 2023-11-11 17:00 | 2025-04-29 17:00 | 156.22% |
| val | 2025-04-29 18:00 | 2026-01-28 10:00 | -6.12% |
| test | 2026-01-28 11:00 | 2026-10-29 04:00 | -10.24% |

Search vs luck: best DEV t-stat (no filters) = 2.1; it beats 100% of 20 random-entry searches of the same size.

| side | config | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | TEST max DD | gross exp R | 1.5x cost exp R | WF OOS sum R (pos folds) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | candle_momo [adx_trend+htf1h] sl 1.5ATR rr 3.0 48h | 66 / 0.4301 | 28 / 0.5843 | 27 | 37 | 0.2017 | 1.278 | 5.45 | 8.41% | 0.4265 | 0.0973 | 6.4 (67%) | **INCONCLUSIVE (too few test trades)** |
| LONG | ema_pullback [weekend] sl 4.0ATR rr 3.0 48h | 55 / 0.133 | 22 / 0.4584 | 25 | 36 | -0.1476 | 0.721 | -3.69 | 5.51% | -0.0256 | -0.1947 | -1.73 (47%) | **INCONCLUSIVE (too few test trades)** |
| LONG | donchian_bo20 [vol_low] sl 4.0ATR rr 3.0 48h | 57 / 0.1814 | 35 / 0.1818 | 33 | 36 | -0.1886 | 0.73 | -6.22 | 10.77% | -0.0417 | -0.2473 | -2.06 (53%) | **NO EDGE PROVEN** |
| SHORT | candle_momo [asia_00_07] sl 4.0ATR rr 3.0 12h | 46 / 0.1348 | 26 / 0.1113 | 26 | 46 | -0.1052 | 0.688 | -2.74 | 4.39% | -0.0181 | -0.1452 | 1.64 (54%) | **INCONCLUSIVE (too few test trades)** |
| SHORT | ema_pullback [weekend+bb_squeeze] sl 1.5ATR rr 2.0 48h | 51 / 0.1024 | 31 / 0.023 | 33 | 30 | -0.3724 | 0.583 | -12.29 | 15.37% | -0.0909 | -0.5029 | -13.89 (33%) | **NO EDGE PROVEN** |
| SHORT | donchian_bo20 [-] sl 2.5ATR rr 3.0 48h | 191 / -0.0211 | 99 / 0.0359 | 105 | 34 | -0.1651 | 0.755 | -17.34 | 26.59% | -0.0249 | -0.224 | -32.91 (33%) | **NO EDGE PROVEN** |

Baseline (enter every bar, exit picked on DEV): LONG TEST n=174 exp R=-0.0921; SHORT TEST n=200 exp R=-0.0732
