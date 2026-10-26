## PAXG 15m

17280 bars, 2026-04-29 19:15 to 2026-10-26 19:00 UTC. Costs 0.079% per side (+funding). 1510 configs searched.

| segment | from | to | buy & hold |
|---|---|---|---|
| dev | 2026-05-02 22:15 | 2026-07-28 19:00 | -12.48% |
| val | 2026-07-28 19:15 | 2026-09-11 19:00 | 8.3% |
| test | 2026-09-11 19:15 | 2026-10-26 19:00 | -7.65% |

Search vs luck: best DEV t-stat (no filters) = -3.94; it beats 0% of 20 random-entry searches of the same size.

| side | config | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | TEST max DD | gross exp R | 1.5x cost exp R | WF OOS sum R (pos folds) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | donchian_bo48 [weekday+rvol_spike] sl 3.0ATR rr 3.0 8h | 46 / -0.2007 | 37 / -0.173 | 26 | 12 | -0.9474 | 0.171 | -24.63 | 23.17% | -0.5559 | -1.1377 | -26.28 (0%) | **INCONCLUSIVE (too few test trades)** |
| LONG | sweep_rev48 [-] sl 3.0ATR rr 3.0 8h | 114 / -0.6777 | 45 / -0.7952 | 62 | 27 | -0.9437 | 0.181 | -58.51 | 45.39% | -0.1504 | -1.3287 | -107.74 (0%) | **NO EDGE PROVEN** |
| LONG | candle_momo [-] sl 3.0ATR rr 3.0 8h | 153 / -0.7814 | 88 / -0.8433 | 96 | 16 | -2.0539 | 0.061 | -197.17 | 86.78% | -0.2024 | -2.9507 | -220.76 (0%) | **NO EDGE PROVEN** |
| SHORT | ema_pullback [weekday+rvol_quiet] sl 3.0ATR rr 3.0 8h | 71 / -0.0422 | 30 / -0.0828 | 35 | 20 | -0.4842 | 0.306 | -16.95 | 15.78% | -0.1191 | -0.659 | -24.06 (20%) | **NO EDGE PROVEN** |
| SHORT | sweep_rev48 [atr_expand+close_loc] sl 3.0ATR rr 3.0 8h | 40 / -0.1637 | 20 / -0.2387 | 17 | 41 | 0.049 | 1.091 | 0.83 | 4.11% | 0.5805 | -0.2069 | -3.66 (20%) | **INCONCLUSIVE (too few test trades)** |
| SHORT | donchian_bo48 [weekday+ema_stack] sl 3.0ATR rr 3.0 8h | 56 / -0.1255 | 20 / -0.2241 | 31 | 29 | -0.3005 | 0.609 | -9.31 | 12.58% | 0.0923 | -0.4908 | -21.71 (0%) | **NO EDGE PROVEN** |

Baseline (enter every bar, exit picked on DEV): LONG TEST n=224 exp R=-1.8115; SHORT TEST n=211 exp R=-1.5389
