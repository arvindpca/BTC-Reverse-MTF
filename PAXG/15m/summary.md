## PAXG 15m

17280 bars, 2026-04-29 19:30 to 2026-10-26 19:15 UTC. Costs 0.079% per side (+funding). 1483 configs searched. Min stop 0.25%.

| segment | from | to | buy & hold |
|---|---|---|---|
| dev | 2026-05-02 22:30 | 2026-07-28 19:15 | -12.51% |
| val | 2026-07-28 19:30 | 2026-09-11 19:15 | 8.26% |
| test | 2026-09-11 19:30 | 2026-10-26 19:15 | -7.51% |

Search vs luck: best DEV t-stat (no filters) = -0.04; it beats 0% of 20 random-entry searches of the same size.

| side | config | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | TEST max DD | gross exp R | 1.5x cost exp R | WF OOS sum R (pos folds) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | candle_momo [vwap_side+vol_high] sl 3.0ATR rr 3.0 12h | 40 / 0.0982 | 30 / -0.0285 | 18 | 28 | -0.6443 | 0.234 | -11.6 | 12.36% | -0.3141 | -0.7996 | -9.41 (20%) | **INCONCLUSIVE (too few test trades)** |
| LONG | donchian_bo48 [weekday] sl 5.0ATR rr 2.0 12h | 45 / -0.0442 | 32 / 0.0017 | 26 | 35 | -0.46 | 0.232 | -11.96 | 11.95% | -0.2262 | -0.5706 | -13.51 (20%) | **INCONCLUSIVE (too few test trades)** |
| LONG | donchian_bo20 [vol_high+ema200_side] sl 3.0ATR rr 3.0 12h | 42 / -0.1146 | 27 / 0.2694 | 18 | 33 | -0.6345 | 0.241 | -11.42 | 12.05% | -0.3182 | -0.7863 | -2.88 (20%) | **INCONCLUSIVE (too few test trades)** |
| SHORT | ema_pullback [weekday+body_strong] sl 5.0ATR rr 1.5 12h | 65 / 0.0528 | 26 / 0.0121 | 34 | 32 | -0.2609 | 0.511 | -8.87 | 9.84% | -0.0204 | -0.3723 | -10.11 (40%) | **NO EDGE PROVEN** |
| SHORT | sweep_rev48 [close_loc] sl 5.0ATR rr 3.0 12h | 50 / -0.0053 | 28 / -0.0082 | 28 | 46 | 0.0378 | 1.106 | 1.06 | 4.32% | 0.2758 | -0.0716 | -11.61 (20%) | **INCONCLUSIVE (too few test trades)** |
| SHORT | donchian_bo48 [rsi_momo] sl 5.0ATR rr 3.0 12h | 61 / -0.0056 | 29 / -0.0071 | 31 | 32 | -0.2433 | 0.562 | -7.54 | 7.43% | 0.0379 | -0.3739 | -7.41 (20%) | **NO EDGE PROVEN** |

Baseline (enter every bar, exit picked on DEV): LONG TEST n=91 exp R=-0.4591; SHORT TEST n=81 exp R=-0.1466
