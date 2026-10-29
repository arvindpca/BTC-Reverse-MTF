## PAXG 1h

13938 bars, 2025-03-27 11:00 to 2026-10-29 04:00 UTC. Costs 0.079% per side (+funding). 1551 configs searched. Min stop 0.25%.

| segment | from | to | buy & hold |
|---|---|---|---|
| dev | 2025-04-08 23:00 | 2026-01-11 19:00 | 50.04% |
| val | 2026-01-11 20:00 | 2026-06-05 23:00 | -4.23% |
| test | 2026-06-06 00:00 | 2026-10-29 04:00 | -6.49% |

Search vs luck: best DEV t-stat (no filters) = 1.91; it beats 45% of 20 random-entry searches of the same size.

| side | config | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | TEST max DD | gross exp R | 1.5x cost exp R | WF OOS sum R (pos folds) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | donchian_bo48 [htf1h+rvol_spike] sl 4.0ATR rr 3.0 48h | 67 / 0.4056 | 24 / 0.6292 | 24 | 38 | -0.3502 | 0.52 | -8.41 | 11.32% | -0.1167 | -0.4514 | 13.39 (50%) | **INCONCLUSIVE (too few test trades)** |
| LONG | donchian_bo20 [asia_00_07+ema200_side] sl 4.0ATR rr 1.5 48h | 60 / 0.3473 | 21 / 0.2457 | 19 | 53 | -0.2512 | 0.538 | -4.77 | 7.0% | -0.0223 | -0.3459 | 15.79 (83%) | **INCONCLUSIVE (too few test trades)** |
| LONG | candle_momo [ema200_side+roc_side] sl 4.0ATR rr 3.0 48h | 75 / 0.4504 | 24 / 0.2688 | 23 | 30 | -0.2931 | 0.604 | -6.74 | 7.64% | -0.0776 | -0.3841 | -1.38 (50%) | **INCONCLUSIVE (too few test trades)** |
| SHORT | ema_pullback [ema200_side+rvol_quiet] sl 4.0ATR rr 1.5 48h | 41 / -0.0282 | 23 / 0.334 | 35 | 40 | -0.1534 | 0.739 | -5.37 | 6.99% | 0.0447 | -0.2362 | 2.3 (67%) | **NO EDGE PROVEN** |
| SHORT | donchian_bo48 [htf1h+body_strong] sl 2.5ATR rr 3.0 48h | 44 / -0.1974 | 33 / -0.1994 | 33 | 27 | -0.3821 | 0.582 | -12.61 | 17.5% | -0.0928 | -0.5079 | -7.07 (50%) | **NO EDGE PROVEN** |
| SHORT | bos [-] sl 4.0ATR rr 3.0 48h | 112 / -0.3157 | 63 / 0.0976 | 63 | 40 | -0.0521 | 0.913 | -3.28 | 12.87% | 0.1717 | -0.1416 | -3.44 (50%) | **NO EDGE PROVEN** |

Baseline (enter every bar, exit picked on DEV): LONG TEST n=109 exp R=-0.3445; SHORT TEST n=97 exp R=-0.1062
