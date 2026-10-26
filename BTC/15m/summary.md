## BTC 15m

17280 bars, 2026-04-29 19:30 to 2026-10-26 19:15 UTC. Costs 0.079% per side (+funding). 1520 configs searched. Min stop 0.25%.

| segment | from | to | buy & hold |
|---|---|---|---|
| dev | 2026-05-02 22:30 | 2026-07-28 19:15 | -18.91% |
| val | 2026-07-28 19:30 | 2026-09-11 19:15 | 21.13% |
| test | 2026-09-11 19:30 | 2026-10-26 19:15 | 3.55% |

Search vs luck: best DEV t-stat (no filters) = 0.37; it beats 40% of 20 random-entry searches of the same size.

| side | config | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | TEST max DD | gross exp R | 1.5x cost exp R | WF OOS sum R (pos folds) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | rsi_rev30 [atr_expand] sl 5.0ATR rr 3.0 12h | 42 / 0.071 | 20 / 0.1144 | 23 | 48 | 0.0844 | 1.296 | 1.94 | 2.78% | 0.2112 | 0.0265 | 7.88 (60%) | **INCONCLUSIVE (too few test trades)** |
| LONG | ema_pullback [europe_07_13+vwap_side] sl 5.0ATR rr 2.0 12h | 41 / -0.0449 | 23 / -0.0561 | 25 | 48 | -0.06 | 0.886 | -1.5 | 6.22% | 0.1456 | -0.1568 | 4.91 (80%) | **INCONCLUSIVE (too few test trades)** |
| LONG | sweep_rev48 [-] sl 5.0ATR rr 1.0 12h | 77 / -0.1164 | 38 / -0.0301 | 48 | 48 | -0.1057 | 0.735 | -5.07 | 8.32% | 0.0447 | -0.1769 | -3.74 (40%) | **NO EDGE PROVEN** |
| SHORT | vwap_rev2.5 [stoch_room] sl 5.0ATR rr 1.5 12h | 58 / -0.0115 | 36 / 0.0129 | 32 | 44 | -0.2462 | 0.527 | -7.88 | 9.81% | -0.0699 | -0.3281 | -13.66 (0%) | **NO EDGE PROVEN** |
| SHORT | ema_pullback [adx_range] sl 3.0ATR rr 2.0 12h | 55 / -0.0312 | 25 / -0.072 | 35 | 26 | -0.3917 | 0.499 | -13.71 | 14.39% | -0.1255 | -0.5195 | -15.19 (20%) | **NO EDGE PROVEN** |
| SHORT | rsi_rev30 [-] sl 5.0ATR rr 2.0 12h | 55 / -0.0896 | 37 / -0.0027 | 31 | 42 | -0.256 | 0.469 | -7.93 | 8.69% | -0.0965 | -0.3302 | -19.33 (20%) | **NO EDGE PROVEN** |

Baseline (enter every bar, exit picked on DEV): LONG TEST n=117 exp R=-0.1317; SHORT TEST n=130 exp R=-0.1278
