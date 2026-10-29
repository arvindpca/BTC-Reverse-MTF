## BTC 4h

6571 bars, 2023-10-30 04:00 to 2026-10-29 04:00 UTC. Costs 0.079% per side (+funding). 1395 configs searched. Min stop 0.25%.

| segment | from | to | buy & hold |
|---|---|---|---|
| dev | 2023-12-10 20:00 | 2025-04-29 12:00 | 116.32% |
| val | 2025-04-29 16:00 | 2026-01-28 08:00 | -5.01% |
| test | 2026-01-28 12:00 | 2026-10-29 04:00 | -10.9% |

Search vs luck: best DEV t-stat (no filters) = 2.19; it beats 55% of 20 random-entry searches of the same size.

| side | config | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | TEST max DD | gross exp R | 1.5x cost exp R | WF OOS sum R (pos folds) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | donchian_bo48 [-] sl 4.0ATR rr 1.0 24h | 60 / 0.0558 | 28 / 0.0768 | 29 | 45 | -0.0749 | 0.648 | -2.17 | 2.73% | -0.0373 | -0.0907 | -5.29 (14%) | **NO EDGE PROVEN** |
| LONG | fvg [-] sl 1.5ATR rr 1.5 24h | 155 / 0.0379 | 80 / 0.0596 | 79 | 47 | -0.0325 | 0.91 | -2.57 | 10.51% | 0.0729 | -0.0782 | -6.47 (29%) | **NO EDGE PROVEN** |
| LONG | donchian_bo20 [europe_07_13] sl 1.5ATR rr 1.5 96h | 48 / 0.1552 | 26 / 0.116 | 27 | 30 | -0.3761 | 0.52 | -10.15 | 10.79% | -0.2593 | -0.4222 | -9.16 (43%) | **NO EDGE PROVEN** |
| SHORT | bos [bb_squeeze+rvol_spike] sl 2.5ATR rr 3.0 96h | 36 / 0.1798 | 22 / 0.3101 | 24 | 38 | -0.2041 | 0.643 | -4.9 | 5.94% | -0.1103 | -0.234 | 0.98 (29%) | **NO EDGE PROVEN** |
| SHORT | rsi_rev30 [vwap_side] sl 2.5ATR rr 2.0 96h | 33 / 0.1422 | 15 / 0.2038 | 14 | 36 | -0.3826 | 0.327 | -5.36 | 5.47% | -0.3026 | -0.4092 | 0.25 (29%) | **INCONCLUSIVE (too few test trades)** |
| SHORT | sweep_rev48 [weekday] sl 1.5ATR rr 3.0 96h | 49 / 0.1265 | 22 / 0.1783 | 25 | 32 | -0.2612 | 0.636 | -6.53 | 10.77% | -0.1488 | -0.3016 | -0.68 (29%) | **NO EDGE PROVEN** |

Baseline (enter every bar, exit picked on DEV): LONG TEST n=81 exp R=-0.0897; SHORT TEST n=87 exp R=-0.0681
