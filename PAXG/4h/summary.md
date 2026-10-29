## PAXG 4h

3486 bars, 2025-03-27 08:00 to 2026-10-29 04:00 UTC. Costs 0.079% per side (+funding). 1331 configs searched. Min stop 0.25%.

| segment | from | to | buy & hold |
|---|---|---|---|
| dev | 2025-05-08 00:00 | 2026-01-11 16:00 | 33.37% |
| val | 2026-01-11 20:00 | 2026-06-05 20:00 | -4.23% |
| test | 2026-06-06 00:00 | 2026-10-29 04:00 | -6.49% |

Search vs luck: best DEV t-stat (no filters) = 2.25; it beats 95% of 20 random-entry searches of the same size.

| side | config | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | TEST max DD | gross exp R | 1.5x cost exp R | WF OOS sum R (pos folds) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | fvg [structure+ema200_side] sl 4.0ATR rr 1.5 96h | 35 / 0.4115 | 15 / 0.3587 | 9 | 33 | -0.1915 | 0.603 | -1.72 | 2.97% | -0.0858 | -0.225 | -0.6 (0%) | **INCONCLUSIVE (too few test trades)** |
| LONG | donchian_bo20 [-] sl 4.0ATR rr 2.0 96h | 32 / 0.3463 | 18 / 0.2438 | 12 | 50 | 0.0477 | 1.1 | 0.57 | 2.49% | 0.1544 | 0.0131 | -4.03 (0%) | **INCONCLUSIVE (too few test trades)** |
| LONG | bos [-] sl 4.0ATR rr 1.5 96h | 43 / 0.2176 | 23 / 0.1255 | 21 | 38 | -0.2629 | 0.483 | -5.52 | 5.45% | -0.1556 | -0.2978 | -7.04 (0%) | **NO EDGE PROVEN** |
| SHORT | bos [body_strong+close_loc] sl 1.5ATR rr 2.0 96h | 31 / -0.1162 | 22 / 0.2139 | 22 | 45 | 0.1734 | 1.283 | 3.82 | 4.93% | 0.4132 | 0.0789 | 2.52 (100%) | **NO EDGE PROVEN** |
| SHORT | ema_pullback [-] sl 1.5ATR rr 3.0 24h | 35 / -0.2163 | 26 / 0.1408 | 33 | 27 | -0.1091 | 0.78 | -3.6 | 10.32% | 0.0995 | -0.1989 | -0.41 (0%) | **NO EDGE PROVEN** |
| SHORT | rsi_rev30 [-] sl 2.5ATR rr 1.0 24h | 37 / -0.1029 | 15 / -0.2438 | 7 | 14 | -0.5859 | 0.013 | -4.1 | 4.04% | -0.4686 | -0.636 | -0.24 (0%) | **INCONCLUSIVE (too few test trades)** |

Baseline (enter every bar, exit picked on DEV): LONG TEST n=41 exp R=-0.1513; SHORT TEST n=49 exp R=-0.0704
