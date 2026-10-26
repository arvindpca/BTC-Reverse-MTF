## PAXG 5m

51840 bars, 2026-04-29 19:25 to 2026-10-26 19:20 UTC. Costs 0.079% per side (+funding). 1608 configs searched.

| segment | from | to | buy & hold |
|---|---|---|---|
| dev | 2026-04-30 20:25 | 2026-07-28 19:20 | -12.78% |
| val | 2026-07-28 19:25 | 2026-09-11 19:20 | 8.35% |
| test | 2026-09-11 19:25 | 2026-10-26 19:20 | -7.59% |

Search vs luck: best DEV t-stat (no filters) = -4.78; it beats 95% of 20 random-entry searches of the same size.

| side | config | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | TEST max DD | gross exp R | 1.5x cost exp R | WF OOS sum R (pos folds) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | rsi_rev25 [htf4h] sl 3.0ATR rr 1.0 3h | 46 / -4.8235 | 27 / -2.4179 | 17 | 6 | -10.8675 | 0.001 | -184.75 | 90.8% | 0.1984 | -16.3635 | -285.13 (0%) | **INCONCLUSIVE (too few test trades)** |
| LONG | rsi_rev30 [-] sl 3.0ATR rr 3.0 8h | 286 / -2.6605 | 129 / -2.1173 | 172 | 19 | -4.04 | 0.051 | -694.87 | 99.98% | 0.2222 | -6.1442 | -1081.92 (0%) | **NO EDGE PROVEN** |
| LONG | vwap_rev2.5 [-] sl 3.0ATR rr 3.0 3h | 424 / -3.1495 | 207 / -2.6107 | 251 | 15 | -4.8537 | 0.03 | -1218.28 | 100.0% | 0.1405 | -7.3209 | -1958.22 (0%) | **NO EDGE PROVEN** |
| SHORT | sweep_rev48 [vol_high+body_strong] sl 3.0ATR rr 3.0 8h | 42 / 0.0335 | 26 / -0.5581 | 20 | 35 | -0.7846 | 0.408 | -15.69 | 17.8% | 0.5966 | -1.4595 | -31.38 (20%) | **INCONCLUSIVE (too few test trades)** |
| SHORT | ema_pullback [htf1h+vol_high] sl 3.0ATR rr 3.0 8h | 84 / -0.3464 | 34 / -0.2567 | 63 | 27 | -1.247 | 0.25 | -78.56 | 56.01% | 0.1003 | -1.9073 | -84.18 (0%) | **NO EDGE PROVEN** |
| SHORT | donchian_bo48 [europe_07_13+htf1h] sl 3.0ATR rr 3.0 3h | 48 / -4.1639 | 22 / -2.4515 | 32 | 16 | -4.6966 | 0.027 | -150.29 | 79.89% | -0.0081 | -7.0264 | -348.1 (0%) | **NO EDGE PROVEN** |

Baseline (enter every bar, exit picked on DEV): LONG TEST n=668 exp R=-4.7854; SHORT TEST n=426 exp R=-4.5199
