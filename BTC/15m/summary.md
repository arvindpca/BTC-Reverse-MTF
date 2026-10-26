## BTC 15m

17280 bars, 2026-04-29 19:15 to 2026-10-26 19:00 UTC. Costs 0.079% per side (+funding). 1461 configs searched.

| segment | from | to | buy & hold |
|---|---|---|---|
| dev | 2026-05-02 22:15 | 2026-07-28 19:00 | -19.06% |
| val | 2026-07-28 19:15 | 2026-09-11 19:00 | 21.08% |
| test | 2026-09-11 19:15 | 2026-10-26 19:00 | 3.75% |

Search vs luck: best DEV t-stat (no filters) = 0.62; it beats 100% of 20 random-entry searches of the same size.

| side | config | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | TEST max DD | gross exp R | 1.5x cost exp R | WF OOS sum R (pos folds) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | rsi_rev30 [rvol_spike] sl 3.0ATR rr 3.0 8h | 42 / 0.0538 | 21 / 0.0974 | 22 | 36 | -0.1466 | 0.749 | -3.22 | 5.4% | 0.0733 | -0.2519 | -1.1 (60%) | **INCONCLUSIVE (too few test trades)** |
| LONG | sweep_rev48 [-] sl 3.0ATR rr 3.0 3h | 106 / -0.2251 | 52 / -0.1397 | 61 | 43 | -0.1976 | 0.557 | -12.06 | 11.92% | 0.041 | -0.3143 | -30.2 (20%) | **NO EDGE PROVEN** |
| LONG | ema_pullback [-] sl 3.0ATR rr 1.5 8h | 128 / -0.2337 | 74 / -0.261 | 63 | 41 | -0.3142 | 0.525 | -19.8 | 20.08% | -0.0151 | -0.4582 | -32.86 (20%) | **NO EDGE PROVEN** |
| SHORT | vwap_rev2.5 [close_loc] sl 3.0ATR rr 1.5 8h | 57 / 0.0234 | 37 / -0.0867 | 38 | 37 | -0.3477 | 0.503 | -13.21 | 13.9% | -0.0565 | -0.4888 | -21.49 (0%) | **NO EDGE PROVEN** |
| SHORT | ema_pullback [adx_range] sl 3.0ATR rr 2.0 8h | 67 / -0.0793 | 33 / -0.1052 | 40 | 25 | -0.4057 | 0.461 | -16.23 | 17.51% | -0.1188 | -0.5436 | -17.78 (0%) | **NO EDGE PROVEN** |
| SHORT | rsi_rev30 [-] sl 3.0ATR rr 2.0 8h | 71 / -0.1492 | 46 / -0.2088 | 39 | 31 | -0.4949 | 0.344 | -19.3 | 17.76% | -0.2308 | -0.6221 | -39.28 (0%) | **NO EDGE PROVEN** |

Baseline (enter every bar, exit picked on DEV): LONG TEST n=190 exp R=-0.2868; SHORT TEST n=188 exp R=-0.3054
